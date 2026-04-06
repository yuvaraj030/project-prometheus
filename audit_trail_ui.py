"""
Audit Trail UI (Phase 16 — Safety)
=====================================
Reads all audit records from the database and renders an interactive
HTML dashboard (audit_trail.html) showing every decision, action, and outcome.
"""

import os
import json
import webbrowser
from datetime import datetime
from typing import Any, Dict, List, Optional


class AuditTrailUI:
    """
    Audit Trail UI — full explainability dashboard for every agent action.
    Renders to HTML and opens in the browser via /history command.
    """

    def __init__(self, database: Any, output_dir: str = "."):
        self.db = database
        self.output_dir = output_dir
        self.output_path = os.path.join(output_dir, "audit_trail.html")

    def _get_audit_records(self, limit: int = 200) -> List[Dict]:
        """Fetch audit records from database."""
        try:
            # Try common DB method names
            if hasattr(self.db, "get_audit_log"):
                return self.db.get_audit_log(limit=limit) or []
            elif hasattr(self.db, "get_audits"):
                return self.db.get_audits(limit=limit) or []
            elif hasattr(self.db, "get_all_audits"):
                return self.db.get_all_audits() or []
            # Fallback: query directly
            import sqlite3
            conn = sqlite3.connect(getattr(self.db, 'db_path', 'agent_database.db'))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(f"[AuditTrailUI] Could not fetch records: {e}")
            return []

    def _build_html(self, records: List[Dict]) -> str:
        """Build the full auditable HTML dashboard."""
        rows_html = ""
        for i, r in enumerate(records):
            action = str(r.get("action", r.get("event_type", "unknown")))
            detail = str(r.get("detail", r.get("data", r.get("context", ""))))[:200]
            ts = str(r.get("timestamp", r.get("created_at", r.get("ts", "—"))))
            tenant = str(r.get("tenant_id", r.get("user_id", "1")))

            # Color-code by action type
            if any(w in action.lower() for w in ["error", "fail", "block", "veto", "detected"]):
                row_class = "danger"
            elif any(w in action.lower() for w in ["success", "learn", "debate", "oracle"]):
                row_class = "success"
            elif any(w in action.lower() for w in ["red_team", "audit", "security", "integrity"]):
                row_class = "warning"
            else:
                row_class = "normal"

            rows_html += f"""
            <tr class="{row_class}" onclick="toggleDetail(this)">
                <td>{i+1}</td>
                <td><span class="action-badge">{action}</span></td>
                <td class="detail-cell">{detail}</td>
                <td>{tenant}</td>
                <td>{ts[:19] if len(ts) > 19 else ts}</td>
            </tr>
            <tr class="detail-row hidden">
                <td colspan="5">
                    <pre class="detail-full">{json.dumps(r, indent=2, default=str)}</pre>
                </td>
            </tr>"""

        total = len(records)
        generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Count action types for stats
        action_counts: Dict[str, int] = {}
        for r in records:
            action = str(r.get("action", r.get("event_type", "unknown")))
            action_counts[action] = action_counts.get(action, 0) + 1
        top_actions = sorted(action_counts.items(), key=lambda x: -x[1])[:5]
        top_html = "".join(
            f'<div class="stat-chip"><span>{a}</span><span class="cnt">{c}</span></div>'
            for a, c in top_actions
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Audit Trail — Decision History</title>
<style>
  :root {{
    --bg: #0d0d1a; --surface: #161628; --border: #2a2a4a;
    --accent: #7c3aed; --accent2: #06b6d4; --text: #e2e8f0;
    --muted: #94a3b8; --success-c: #22c55e; --danger-c: #ef4444;
    --warn-c: #f59e0b;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:system-ui,sans-serif; min-height:100vh; }}
  .header {{ background:linear-gradient(135deg,#1a1a3e,#2d1b69); padding:32px 40px; border-bottom:1px solid var(--border); }}
  .header h1 {{ font-size:2em; font-weight:800; }}
  .header h1 span {{ color:var(--accent); }}
  .header p {{ color:var(--muted); margin-top:4px; }}
  .stats-bar {{ display:flex; gap:16px; padding:20px 40px; background:var(--surface); border-bottom:1px solid var(--border); flex-wrap:wrap; align-items:center; }}
  .stat {{ text-align:center; }}
  .stat .val {{ font-size:2em; font-weight:900; color:var(--accent2); }}
  .stat .lbl {{ font-size:0.75em; color:var(--muted); text-transform:uppercase; }}
  .stat-chip {{ display:inline-flex; align-items:center; gap:8px; background:var(--bg); border:1px solid var(--border); border-radius:20px; padding:4px 12px; font-size:0.82em; margin:4px; }}
  .stat-chip .cnt {{ background:var(--accent); color:#fff; border-radius:10px; padding:2px 7px; font-weight:700; }}
  .search-bar {{ padding:16px 40px; background:var(--surface); border-bottom:1px solid var(--border); }}
  .search-bar input {{ width:100%; max-width:500px; background:var(--bg); border:1px solid var(--border); color:var(--text); padding:10px 16px; border-radius:8px; font-size:0.95em; outline:none; }}
  .search-bar input:focus {{ border-color:var(--accent); }}
  .table-wrap {{ padding:24px 40px; overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.88em; }}
  th {{ background:var(--surface); padding:12px 14px; text-align:left; font-weight:600; color:var(--muted); text-transform:uppercase; font-size:0.78em; letter-spacing:0.05em; border-bottom:2px solid var(--border); position:sticky; top:0; }}
  td {{ padding:10px 14px; border-bottom:1px solid var(--border); vertical-align:top; }}
  tr.normal:hover, tr.success:hover, tr.danger:hover, tr.warning:hover {{ background:#ffffff08; cursor:pointer; }}
  tr.success td:first-child {{ border-left:3px solid var(--success-c); }}
  tr.danger td:first-child {{ border-left:3px solid var(--danger-c); }}
  tr.warning td:first-child {{ border-left:3px solid var(--warn-c); }}
  tr.normal td:first-child {{ border-left:3px solid var(--accent); }}
  .action-badge {{ background:var(--bg); border:1px solid var(--border); border-radius:4px; padding:2px 8px; font-family:monospace; font-size:0.85em; white-space:nowrap; }}
  .detail-cell {{ max-width:380px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); }}
  .detail-row {{ display:none; background:#0a0a18; }}
  .detail-row.visible {{ display:table-row; }}
  .detail-full {{ padding:16px; font-size:0.82em; color:#a5b4fc; overflow-x:auto; white-space:pre-wrap; }}
  .footer {{ text-align:center; padding:24px; color:var(--muted); font-size:0.8em; border-top:1px solid var(--border); }}
  .export-btn {{ background:var(--accent); color:#fff; border:none; padding:8px 20px; border-radius:6px; cursor:pointer; font-size:0.9em; margin-left:auto; }}
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ Ultimate Agent — <span>Audit Trail</span></h1>
  <p>Complete decision history • Generated {generated} • {total} records</p>
</div>
<div class="stats-bar">
  <div class="stat"><div class="val">{total}</div><div class="lbl">Total Events</div></div>
  <div class="stat"><div class="val">{len(set(str(r.get('tenant_id','1')) for r in records))}</div><div class="lbl">Tenants</div></div>
  <div class="stat"><div class="val">{len(set(str(r.get('action','')) for r in records))}</div><div class="lbl">Action Types</div></div>
  <div style="margin-left:auto;">{top_html}</div>
  <button class="export-btn" onclick="exportCSV()">⬇ Export CSV</button>
</div>
<div class="search-bar">
  <input type="text" id="searchInput" placeholder="🔍  Filter events by action, detail, tenant..." oninput="filterTable()">
</div>
<div class="table-wrap">
<table id="auditTable">
<thead><tr>
  <th>#</th><th>Action</th><th>Detail</th><th>Tenant</th><th>Timestamp</th>
</tr></thead>
<tbody id="tableBody">
{rows_html}
</tbody>
</table>
</div>
<div class="footer">
  Ultimate AI Agent — Full Explainability Audit Trail • {generated}
</div>
<script>
function toggleDetail(row) {{
  const next = row.nextElementSibling;
  if (next && next.classList.contains('detail-row')) {{
    next.classList.toggle('visible');
    next.style.display = next.classList.contains('visible') ? 'table-row' : 'none';
  }}
}}
function filterTable() {{
  const q = document.getElementById('searchInput').value.toLowerCase();
  const rows = document.querySelectorAll('#tableBody tr:not(.detail-row)');
  rows.forEach(row => {{
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
function exportCSV() {{
  const rows = [...document.querySelectorAll('#auditTable tr')];
  const csv = rows.map(r => [...r.querySelectorAll('td,th')].map(c => '"'+c.textContent.replace(/"/g,'""')+'"').join(',')).join('\\n');
  const blob = new Blob([csv], {{type:'text/csv'}});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'audit_trail.csv'; a.click();
}}
</script>
</body>
</html>"""

    def render(self, limit: int = 200, open_browser: bool = True) -> str:
        """Generate and optionally open the audit HTML dashboard."""
        records = self._get_audit_records(limit)
        html = self._build_html(records)
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"📊 Audit Trail rendered: {self.output_path} ({len(records)} records)")
        if open_browser:
            try:
                webbrowser.open(f"file://{os.path.abspath(self.output_path)}")
            except Exception:
                pass
        return self.output_path

    def export_json(self, limit: int = 200) -> str:
        """Export audit log as JSON file."""
        records = self._get_audit_records(limit)
        out_path = os.path.join(self.output_dir, "audit_trail.json")
        with open(out_path, "w") as f:
            json.dump(records, f, indent=2, default=str)
        print(f"✅ Exported {len(records)} audit records to {out_path}")
        return out_path

    def describe(self) -> str:
        return "AuditTrailUI — Full explainability dashboard. Use /history to render."
