"""
Affiliate Tracker — track affiliate links, clicks, and commissions.
Commands: /affiliate add|log|report|list|remove
"""

import os
import json
from datetime import datetime, date


class AffiliateTracker:
    """Track affiliate program performance: links, clicks, and commissions."""

    DATA_FILE = "affiliate_data.json"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"programs": {}, "events": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def add_program(self, name: str, url: str, commission_pct: float = 0.0,
                    commission_flat: float = 0.0, notes: str = "") -> str:
        """Register a new affiliate program."""
        key = name.lower().replace(" ", "_")
        if key in self._data["programs"]:
            return f"⚠️ Program '{name}' already exists. Use /affiliate log to record earnings."
        self._data["programs"][key] = {
            "name": name,
            "url": url,
            "commission_pct": commission_pct,
            "commission_flat": commission_flat,
            "notes": notes,
            "added_at": datetime.now().isoformat(),
            "total_clicks": 0,
            "total_commissions": 0.0
        }
        self._save()
        return (
            f"✅ Affiliate program '{name}' added!\n"
            f"   🔗 URL: {url}\n"
            f"   💰 Commission: {f'{commission_pct}%' if commission_pct else ''}"
            f"{f' + ${commission_flat} flat' if commission_flat else ''}\n"
            f"   Log clicks with: /affiliate click {name}\n"
            f"   Log earnings with: /affiliate log {name} <amount>"
        )

    def log_click(self, name: str) -> str:
        """Log a click event."""
        key = name.lower().replace(" ", "_")
        if key not in self._data["programs"]:
            return f"❌ Program '{name}' not found. Add it with /affiliate add {name} <url>"
        self._data["programs"][key]["total_clicks"] += 1
        self._data["events"].append({
            "type": "click",
            "program": key,
            "amount": 0.0,
            "date": date.today().isoformat()
        })
        self._save()
        clicks = self._data["programs"][key]["total_clicks"]
        return f"👆 Click logged for '{name}'! Total clicks: {clicks}"

    def log_commission(self, name: str, amount: float, note: str = "") -> str:
        """Log a commission/sale event."""
        key = name.lower().replace(" ", "_")
        if key not in self._data["programs"]:
            return f"❌ Program '{name}' not found."
        self._data["programs"][key]["total_commissions"] += amount
        self._data["events"].append({
            "type": "commission",
            "program": key,
            "amount": amount,
            "note": note,
            "date": date.today().isoformat()
        })
        self._save()
        total = self._data["programs"][key]["total_commissions"]
        return (
            f"💰 ${amount:.2f} commission logged for '{name}'!\n"
            f"   📊 Total earned from '{name}': ${total:.2f}"
        )

    def get_report(self) -> str:
        """Full affiliate performance report."""
        if not self._data["programs"]:
            return "No affiliate programs tracked. Add one with /affiliate add <name> <url>"

        total_commissions = sum(p["total_commissions"] for p in self._data["programs"].values())
        total_clicks = sum(p["total_clicks"] for p in self._data["programs"].values())

        lines = [
            "📊 AFFILIATE PERFORMANCE REPORT",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Total Programs: {len(self._data['programs'])}",
            f"Total Clicks: {total_clicks}",
            f"Total Commissions: ${total_commissions:.2f}",
            f"Avg per Click: ${(total_commissions / total_clicks):.4f}" if total_clicks else "Avg per Click: N/A",
            "",
            "BY PROGRAM:",
        ]
        sorted_programs = sorted(
            self._data["programs"].items(),
            key=lambda x: x[1]["total_commissions"],
            reverse=True
        )
        for key, prog in sorted_programs:
            cvr = (prog["total_commissions"] / prog["total_clicks"]) if prog["total_clicks"] else 0
            lines.append(f"\n  🔗 {prog['name']}")
            lines.append(f"     Clicks: {prog['total_clicks']} | Earned: ${prog['total_commissions']:.2f} | CVR: ${cvr:.3f}/click")
            if prog.get("notes"):
                lines.append(f"     Note: {prog['notes']}")
        return "\n".join(lines)

    def list_programs(self) -> str:
        """List all programs."""
        if not self._data["programs"]:
            return "No affiliate programs added. Use /affiliate add <name> <url>"
        lines = ["🔗 AFFILIATE PROGRAMS:\n"]
        for key, prog in self._data["programs"].items():
            commission = f"{prog['commission_pct']}%" if prog["commission_pct"] else f"${prog['commission_flat']}"
            lines.append(f"  {prog['name']} | {commission} commission | {prog['total_clicks']} clicks | ${prog['total_commissions']:.2f} earned")
        return "\n".join(lines)
