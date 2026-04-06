"""
Heartbeat Scheduler — Proactive task runner that checks in periodically.

Two-tier approach:
  1. Cheap checks (no LLM): file timestamps, pending tasks, system health
  2. If anything noteworthy → escalate to LLM for interpretation

Reads HEARTBEAT.md for the checklist of things to monitor.
"""

import os
import time
import asyncio
import logging
import psutil
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger("HeartbeatScheduler")


class HeartbeatScheduler:
    """
    Periodic heartbeat that monitors system state and triggers proactive actions.

    Usage:
        scheduler = HeartbeatScheduler(llm_provider=llm, interval_minutes=30)
        scheduler.start()
    """

    def __init__(self, llm_provider=None, database=None,
                 interval_minutes: int = 30,
                 heartbeat_file: str = "HEARTBEAT.md"):
        self.llm = llm_provider
        self.db = database
        self.interval = interval_minutes * 60  # Convert to seconds
        self.heartbeat_file = heartbeat_file
        self.running = False
        self._last_run: Optional[float] = None
        self._check_results: List[Dict] = []
        self._custom_checks: List[Callable] = []
        self._on_alert: Optional[Callable] = None  # Callback for Gateway WebSocket

    def load_checklist(self) -> List[str]:
        """Load the heartbeat checklist from HEARTBEAT.md."""
        try:
            with open(self.heartbeat_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract checklist items (lines starting with - or *)
            items = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(("- ", "* ", "• ")):
                    item = line.lstrip("-*• ").strip()
                    if item:
                        items.append(item)
            return items
        except FileNotFoundError:
            logger.warning(f"{self.heartbeat_file} not found, using defaults")
            return [
                "Check system health (CPU, memory, disk)",
                "Review pending tasks",
                "Check for important file changes",
            ]

    def add_check(self, check_fn: Callable[[], Dict]):
        """Register a custom cheap check function."""
        self._custom_checks.append(check_fn)

    def set_alert_callback(self, callback: Callable):
        """Set callback for when alerts are generated (e.g., WebSocket broadcast)."""
        self._on_alert = callback

    # --- Cheap Checks (Tier 1: No LLM) ---

    def _check_system_health(self) -> Dict:
        """CPU, memory, disk usage."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            alerts = []
            if cpu > 90:
                alerts.append(f"HIGH CPU: {cpu}%")
            if mem.percent > 85:
                alerts.append(f"HIGH MEMORY: {mem.percent}%")
            if disk.percent > 90:
                alerts.append(f"LOW DISK: {disk.percent}% used")

            return {
                "check": "system_health",
                "status": "warning" if alerts else "ok",
                "data": {
                    "cpu_percent": cpu,
                    "memory_percent": mem.percent,
                    "disk_percent": disk.percent,
                },
                "alerts": alerts,
            }
        except Exception as e:
            return {"check": "system_health", "status": "error", "error": str(e), "alerts": []}

    def _check_pending_tasks(self) -> Dict:
        """Check if there are pending tasks in the database."""
        try:
            if self.db:
                # Check for unseen messages or pending items
                count = 0
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM conversations WHERE role='user' AND timestamp > datetime('now', '-1 hour')")
                    count = cursor.fetchone()[0]
                except Exception:
                    pass
                return {
                    "check": "pending_tasks",
                    "status": "ok",
                    "data": {"recent_messages": count},
                    "alerts": [f"{count} new messages in last hour"] if count > 10 else [],
                }
            return {"check": "pending_tasks", "status": "skipped", "alerts": []}
        except Exception as e:
            return {"check": "pending_tasks", "status": "error", "error": str(e), "alerts": []}

    def _check_file_changes(self) -> Dict:
        """Check for recent modifications to key files."""
        key_files = [
            "ultimate_agent.py",
            "config.py",
            "HEARTBEAT.md",
        ]
        changes = []
        for f in key_files:
            if os.path.exists(f):
                mtime = os.path.getmtime(f)
                age_hours = (time.time() - mtime) / 3600
                if age_hours < 1:
                    changes.append(f"{f} modified {age_hours:.1f}h ago")

        return {
            "check": "file_changes",
            "status": "info" if changes else "ok",
            "data": {"recent_changes": changes},
            "alerts": changes,
        }

    def _check_uptime(self) -> Dict:
        """Report agent uptime."""
        boot_time = psutil.boot_time()
        uptime_hours = (time.time() - boot_time) / 3600
        return {
            "check": "uptime",
            "status": "ok",
            "data": {"system_uptime_hours": round(uptime_hours, 1)},
            "alerts": [],
        }

    def _check_db_health(self) -> Dict:
        """Fix #16: Run SQLite VACUUM weekly and prune oversized tables."""
        MAX_ROWS = 10_000
        alerts = []
        if not self.db:
            return {"check": "db_health", "status": "skipped", "alerts": []}
        try:
            cursor = self.db.conn.cursor()
            # Prune conversations table
            for table in ("conversations", "audit_log"):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    if count > MAX_ROWS:
                        delete_n = count - MAX_ROWS
                        cursor.execute(
                            f"DELETE FROM {table} WHERE rowid IN "
                            f"(SELECT rowid FROM {table} ORDER BY rowid ASC LIMIT {delete_n})"
                        )
                        self.db.conn.commit()
                        alerts.append(f"Pruned {delete_n} old rows from {table}")
                        logger.info(f"[DB] Pruned {delete_n} rows from '{table}'")
                except Exception:
                    pass  # table may not exist
            # VACUUM at most once per 7 days using a flag file
            vacuum_flag = ".last_vacuum"
            should_vacuum = True
            if os.path.exists(vacuum_flag):
                age_days = (time.time() - os.path.getmtime(vacuum_flag)) / 86400
                should_vacuum = age_days >= 7
            if should_vacuum:
                cursor.execute("VACUUM")
                open(vacuum_flag, "w").write(datetime.now().isoformat())
                logger.info("[DB] VACUUM completed.")
            return {"check": "db_health", "status": "ok", "alerts": alerts}
        except Exception as e:
            return {"check": "db_health", "status": "error", "error": str(e), "alerts": []}

    # --- Main Run ---

    def run_checks(self) -> Dict:
        """Run all cheap checks and return aggregated result."""
        start = time.time()
        checklist = self.load_checklist()
        results = []

        # Run built-in cheap checks
        results.append(self._check_system_health())
        results.append(self._check_pending_tasks())
        results.append(self._check_file_changes())
        results.append(self._check_uptime())
        results.append(self._check_db_health())  # Fix #16

        # Run custom checks
        for check_fn in self._custom_checks:
            try:
                results.append(check_fn())
            except Exception as e:
                results.append({"check": "custom", "status": "error", "error": str(e), "alerts": []})

        # Aggregate alerts
        all_alerts = []
        for r in results:
            all_alerts.extend(r.get("alerts", []))

        elapsed = time.time() - start
        self._last_run = time.time()

        status = "HEARTBEAT_OK" if not all_alerts else "HEARTBEAT_ALERT"
        self._check_results = results

        result = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "checks_performed": len(results),
            "checklist_items": len(checklist),
            "alerts": all_alerts,
            "elapsed_ms": int(elapsed * 1000),
            "details": results,
        }

        logger.info(f"Heartbeat: {status} ({len(all_alerts)} alerts, {elapsed*1000:.0f}ms)")

        # Tier 2: Escalate to LLM if there are alerts
        if all_alerts and self.llm:
            self._escalate_to_llm(all_alerts, checklist)

        # Alert callback (for WebSocket broadcast)
        if all_alerts and self._on_alert:
            try:
                self._on_alert(result)
            except Exception:
                pass

        return result

    def _escalate_to_llm(self, alerts: List[str], checklist: List[str]):
        """Escalate alerts to LLM for interpretation and recommended action."""
        prompt = (
            f"HEARTBEAT ALERT — You are the agent's proactive monitoring system.\n\n"
            f"Monitoring checklist:\n"
            + "\n".join(f"  - {item}" for item in checklist)
            + f"\n\nCurrent alerts:\n"
            + "\n".join(f"  ⚠ {a}" for a in alerts)
            + "\n\nProvide a ONE-paragraph summary and recommended actions."
        )
        try:
            interpretation = self.llm.call(prompt, max_tokens=300)
            logger.info(f"LLM Heartbeat Interpretation: {interpretation[:200]}")
        except Exception as e:
            logger.error(f"LLM escalation failed: {e}")

    # --- Async Loop ---

    async def start(self):
        """Start the heartbeat scheduler loop."""
        self.running = True
        logger.info(f"Heartbeat scheduler started (interval: {self.interval}s)")
        while self.running:
            try:
                await asyncio.to_thread(self.run_checks)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the heartbeat scheduler."""
        self.running = False
        logger.info("Heartbeat scheduler stopped")

    @property
    def last_run(self) -> Optional[str]:
        if self._last_run:
            return datetime.fromtimestamp(self._last_run).isoformat()
        return None


# --- Quick test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = HeartbeatScheduler(interval_minutes=1)
    result = scheduler.run_checks()
    print(f"\nHeartbeat Result: {result['status']}")
    print(f"  Checks: {result['checks_performed']}")
    print(f"  Alerts: {result['alerts']}")
    for detail in result["details"]:
        print(f"  • {detail['check']}: {detail['status']}")
