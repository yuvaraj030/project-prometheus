"""
Autonomous Daemon — Standalone 24/7 Agent Runner
=================================================
Runs the ReAct agent loop WITHOUT a user terminal.

Start it once:
    python daemon.py

The agent will:
  1. Generate goals autonomously via LLM
  2. Execute each goal using the ReAct loop (real tools)
  3. Log every step to logs/daemon.log
  4. Sleep, then repeat forever

Stop it with Ctrl+C or by killing the process.

Windows Task Scheduler:
  Action: python C:\\path\\to\\daemon.py
  Trigger: At startup / On a schedule
"""

import os
import sys
import time
import json
import signal
import logging
import logging.handlers
import random
from datetime import datetime
from pathlib import Path

# ── Bootstrap path ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Logging Setup ──────────────────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "daemon.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("Daemon")

# ── Constants ──────────────────────────────────────────────────────────────────
CYCLE_INTERVAL_SECONDS = 120        # How long to sleep between goal cycles
GOAL_GEN_EVERY_N_CYCLES = 5        # Generate new goals every N cycles
MAX_ACTIVE_GOALS = 8               # Never fill DB with more than this
REACT_MAX_STEPS = 8                # ReAct steps per goal
STATE_FILE = ROOT / "daemon_state.json"

# Fallback seed goals used when LLM goal generation fails
SEED_GOALS = [
    {
        "title": "Research trending AI topics",
        "objective": "Search the web for 3 current AI trends and write a summary to knowledge/ai_trends.md",
        "priority": 7,
        "category": "research",
    },
    {
        "title": "Self-diagnostic check",
        "objective": "List all python files in the project, count them, and write a health report to logs/health.txt",
        "priority": 6,
        "category": "maintenance",
    },
    {
        "title": "Learn about Python best practices",
        "objective": "Search for Python clean code best practices and write the top 5 tips to knowledge/python_tips.md",
        "priority": 5,
        "category": "learning",
    },
    {
        "title": "Write a daily journal entry",
        "objective": "Write a short journal entry about the agent's current state, goals, and any observations to logs/journal.txt (append mode)",
        "priority": 4,
        "category": "creative",
    },
]


class AgentDaemon:
    """
    Standalone autonomous agent daemon.

    Initializes minimal components (LLM, ToolRegistry, ReactAgent),
    then loops forever: pick goal → execute via ReAct → log → sleep.
    """

    def __init__(self):
        self.running = True
        self.cycle = 0
        self.completed_goals = []
        self.active_goals = []
        self._load_state()

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info("=" * 60)
        logger.info("  ULTIMATE AI AGENT — AUTONOMOUS DAEMON STARTED")
        logger.info(f"  PID: {os.getpid()}")
        logger.info(f"  Log: {LOG_FILE}")
        logger.info(f"  Cycle interval: {CYCLE_INTERVAL_SECONDS}s")
        logger.info("=" * 60)

        # ── Initialize components ──────────────────────────────────────────
        self.llm = self._init_llm()
        self.tools = self._init_tools()
        self.react = self._init_react()

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_llm(self):
        """Load LLMProvider from config."""
        logger.info("Initializing LLM provider...")
        try:
            from llm_provider import LLMProvider
            from config import CONFIG

            # Try Groq first (fast, free), then Ollama
            groq_key = os.getenv("GROQ_API_KEY") or getattr(CONFIG, "groq", None) and CONFIG.groq.api_key
            provider = "hybrid" if groq_key else "ollama"

            llm = LLMProvider(provider=provider)
            logger.info(f"LLM: {provider}")
            return llm
        except Exception as e:
            logger.error(f"LLM init failed: {e}")
            return None

    def _init_tools(self):
        """Initialize tool registry with all built-in tools."""
        logger.info("Initializing tool registry...")
        try:
            from tool_registry import ToolRegistry
            registry = ToolRegistry()
            registry.register_builtins()
            logger.info(f"Tools registered: {registry.count}")

            # Ensure knowledge/ dir exists for file writing
            (ROOT / "knowledge").mkdir(exist_ok=True)
            return registry
        except Exception as e:
            logger.error(f"Tool registry init failed: {e}")
            return None

    def _init_react(self):
        """Initialize ReactAgent."""
        if not self.llm or not self.tools:
            logger.error("Cannot init ReactAgent — missing LLM or tools.")
            return None
        try:
            from react_agent import ReactAgent
            agent = ReactAgent(
                llm_provider=self.llm,
                tool_registry=self.tools,
                max_steps=REACT_MAX_STEPS,
                verbose=True,
            )
            logger.info("ReactAgent ready.")
            return agent
        except Exception as e:
            logger.error(f"ReactAgent init failed: {e}")
            return None

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Main daemon loop — runs forever until SIGINT/SIGTERM."""
        if not self.react:
            logger.critical("ReactAgent not available. Cannot run daemon.")
            return

        while self.running:
            self.cycle += 1
            logger.info(f"\n{'─'*50}")
            logger.info(f"CYCLE {self.cycle} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Active goals: {len(self.active_goals)} | Completed: {len(self.completed_goals)}")

            try:
                # ── Generate new goals if needed ──────────────────────
                if self.cycle % GOAL_GEN_EVERY_N_CYCLES == 1 or not self.active_goals:
                    self._generate_goals()

                # ── Pick and execute a goal ────────────────────────────
                goal = self._pick_goal()
                if goal:
                    self._execute_goal(goal)
                else:
                    logger.info("No goals available. Adding a seed goal.")
                    self.active_goals.extend(SEED_GOALS[:2])

                # ── Save state ─────────────────────────────────────────
                self._save_state()

            except Exception as e:
                logger.error(f"Cycle error: {e}", exc_info=True)

            # ── Sleep until next cycle ─────────────────────────────────
            if self.running:
                logger.info(f"Sleeping {CYCLE_INTERVAL_SECONDS}s until next cycle...")
                for _ in range(CYCLE_INTERVAL_SECONDS):
                    if not self.running:
                        break
                    time.sleep(1)

        logger.info("Daemon stopped cleanly.")

    # ── Goal Management ───────────────────────────────────────────────────────

    def _generate_goals(self):
        """Ask LLM to generate 2-3 new goals based on current state."""
        if len(self.active_goals) >= MAX_ACTIVE_GOALS:
            logger.info(f"Goal cap ({MAX_ACTIVE_GOALS}) reached. Skipping generation.")
            return

        logger.info("Generating new goals via LLM...")
        now = datetime.now()
        completed_titles = [g.get("title", "") for g in self.completed_goals[-5:]]
        active_titles = [g.get("title", "") for g in self.active_goals[:5]]

        prompt = f"""You are an autonomous AI agent running 24/7.
Generate 2-3 concrete, executable goals for yourself right now.

Current time: {now.strftime('%Y-%m-%d %H:%M')} (Hour: {now.hour})
Active goals already queued: {active_titles or ['none']}
Recently completed: {completed_titles or ['none']}

Goal ideas: research a topic and write it to a file, run self-diagnostics,
learn something new, write a summary or report, check current events.

IMPORTANT: Goals must be concrete and verifiable — e.g. "Search web for X and write results to Y file".
Return ONLY a JSON array:
[
  {{
    "title": "Short title",
    "objective": "Specific thing to do — which tool to use, what file to write, what to search for",
    "priority": 7,
    "category": "research"
  }}
]
"""
        try:
            resp = self.llm.call(prompt, max_tokens=600, temperature=0.7)
            goals = self._parse_json_goals(resp)
            if goals:
                self.active_goals.extend(goals)
                for g in goals:
                    logger.info(f"  🎯 Generated: [{g.get('category','?')}] {g.get('title','?')} (P{g.get('priority',5)})")
            else:
                logger.warning("LLM goal generation returned no valid goals. Using seed.")
                seed = random.choice(SEED_GOALS).copy()
                self.active_goals.append(seed)
        except Exception as e:
            logger.error(f"Goal generation failed: {e}. Using seed goal.")
            self.active_goals.append(random.choice(SEED_GOALS).copy())

    def _pick_goal(self):
        """Return the highest-priority pending goal."""
        pending = [g for g in self.active_goals
                   if g.get("status", "pending") == "pending"]
        if not pending:
            return None
        pending.sort(key=lambda g: -g.get("priority", 5))
        return pending[0]

    def _execute_goal(self, goal: dict):
        """Run a goal through the ReAct loop and record the result."""
        title = goal.get("title", "Untitled")
        objective = goal.get("objective", title)
        logger.info(f"\n⚡ EXECUTING: {title}")
        logger.info(f"   Objective: {objective}")

        # Mark as running
        goal["status"] = "running"
        goal["started_at"] = datetime.now().isoformat()

        try:
            result = self.react.run(objective)

            if result["success"]:
                goal["status"] = "completed"
                goal["result"] = result["result"]
                goal["completed_at"] = datetime.now().isoformat()
                self.completed_goals.append(goal)
                self.active_goals = [g for g in self.active_goals if g is not goal]
                logger.info(f"✅ COMPLETED in {result['steps']} steps ({result['elapsed_s']}s): {result['result'][:150]}")
            else:
                goal["status"] = "failed"
                goal["result"] = result["result"]
                # Keep failed goals with status=failed so we don't retry forever
                logger.warning(f"❌ FAILED after {result['steps']} steps: {result['result'][:150]}")

            # Write execution transcript to logs
            self._write_transcript(title, result)

        except Exception as e:
            goal["status"] = "error"
            goal["result"] = str(e)
            logger.error(f"Goal execution error: {e}", exc_info=True)

    def _write_transcript(self, title: str, result: dict):
        """Append a goal execution transcript to the log file."""
        try:
            transcript_dir = ROOT / "logs" / "transcripts"
            transcript_dir.mkdir(exist_ok=True)
            safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:40]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = transcript_dir / f"{ts}_{safe_title}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"goal": title, **result}, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not write transcript: {e}")

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_state(self):
        """Save daemon state to JSON for crash recovery."""
        try:
            state = {
                "cycle": self.cycle,
                "active_goals": self.active_goals,
                "completed_goals": self.completed_goals[-20:],  # keep last 20
                "saved_at": datetime.now().isoformat(),
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    def _load_state(self):
        """Restore state from previous run if available."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.cycle = state.get("cycle", 0)
                # Only restore pending goals — don't re-run completed/failed ones
                self.active_goals = [
                    g for g in state.get("active_goals", [])
                    if g.get("status", "pending") == "pending"
                ]
                self.completed_goals = state.get("completed_goals", [])
                logger.info(f"Restored state: cycle={self.cycle}, "
                            f"pending={len(self.active_goals)}, "
                            f"completed={len(self.completed_goals)}")
        except Exception as e:
            logger.warning(f"Could not load state: {e}. Starting fresh.")
            self.cycle = 0
            self.active_goals = []
            self.completed_goals = []

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def _handle_shutdown(self, signum, frame):
        logger.info(f"\nShutdown signal received (signal {signum}). Stopping after current cycle...")
        self.running = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_json_goals(self, text: str) -> list:
        """Extract a JSON array of goals from LLM response."""
        text = text.strip()
        # Try direct parse
        try:
            res = json.loads(text)
            return res if isinstance(res, list) else [res]
        except Exception:
            pass
        # Find first [...] block
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
        return []


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║  ULTIMATE AI AGENT — AUTONOMOUS DAEMON           ║
║  Real ReAct loop.  Real tools.  No babysitting.  ║
╚══════════════════════════════════════════════════╝
""")
    daemon = AgentDaemon()
    daemon.run()
