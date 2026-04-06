"""
specialization_engine.py - Track agent success rates, elect specialists, route tasks.
"""
import json, sqlite3, time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

_DB_PATH = Path(__file__).parent / "specialization.db"

class SpecializationEngine:
    """Tracks per-agent success rates across task categories and routes tasks to best agent."""

    def __init__(self, db_path=str(_DB_PATH)):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS performance (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id  TEXT NOT NULL,
                category  TEXT NOT NULL,
                success   INTEGER NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agent_cat ON performance(agent_id, category);
            CREATE TABLE IF NOT EXISTS specialists (
                category  TEXT PRIMARY KEY,
                agent_id  TEXT NOT NULL,
                score     REAL NOT NULL,
                elected_at REAL NOT NULL
            );
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def track_success(self, agent_id: str, category: str, success: bool) -> None:
        """Record the outcome of a task for an agent in a category."""
        self._conn.execute(
            "INSERT INTO performance (agent_id,category,success,timestamp) VALUES (?,?,?,?)",
            (agent_id, category, int(success), time.time()),
        )
        self._conn.commit()
        # Re-elect specialist for this category after every update
        self._elect(category)

    def elect_specialist(self, category: str) -> Optional[str]:
        """Return the current elected specialist agent_id for a category."""
        row = self._conn.execute(
            "SELECT agent_id FROM specialists WHERE category=?", (category,)
        ).fetchone()
        return row[0] if row else None

    def route_task(self, task: Dict) -> Dict:
        """
        Given a task dict with at least a 'category' key, return:
        {"agent_id": str, "category": str, "confidence": float}
        Falls back to 'default_agent' if no specialist found.
        """
        category = task.get("category", "general")
        specialist = self.elect_specialist(category)
        if specialist:
            row = self._conn.execute(
                "SELECT score FROM specialists WHERE category=?", (category,)
            ).fetchone()
            confidence = row[0] if row else 0.0
            return {"agent_id": specialist, "category": category, "confidence": round(confidence, 3)}
        return {"agent_id": "default_agent", "category": category, "confidence": 0.0}

    def leaderboard(self, category: Optional[str] = None) -> List[Dict]:
        """Return ranked agents by success rate, optionally filtered by category."""
        query = """
            SELECT agent_id, category,
                   CAST(SUM(success) AS REAL)/COUNT(*) AS rate,
                   COUNT(*) AS attempts
            FROM performance
        """
        params: tuple = ()
        if category:
            query += " WHERE category=?"
            params = (category,)
        query += " GROUP BY agent_id, category ORDER BY rate DESC, attempts DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [{"agent_id":r[0],"category":r[1],"success_rate":round(r[2],3),"attempts":r[3]} for r in rows]

    def categories(self) -> List[str]:
        rows = self._conn.execute("SELECT DISTINCT category FROM performance").fetchall()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _elect(self, category: str) -> None:
        """Pick the agent with the highest success rate for a category (min 3 attempts)."""
        row = self._conn.execute("""
            SELECT agent_id,
                   CAST(SUM(success) AS REAL)/COUNT(*) AS rate
            FROM performance
            WHERE category=?
            GROUP BY agent_id
            HAVING COUNT(*) >= 3
            ORDER BY rate DESC
            LIMIT 1
        """, (category,)).fetchone()
        if row:
            self._conn.execute(
                "INSERT OR REPLACE INTO specialists (category,agent_id,score,elected_at) VALUES (?,?,?,?)",
                (category, row[0], row[1], time.time()),
            )
            self._conn.commit()

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_engine: Optional[SpecializationEngine] = None

def get_engine() -> SpecializationEngine:
    global _engine
    if _engine is None:
        _engine = SpecializationEngine()
    return _engine

def track_success(agent_id, category, success):  get_engine().track_success(agent_id, category, success)
def elect_specialist(category):                  return get_engine().elect_specialist(category)
def route_task(task):                            return get_engine().route_task(task)
def leaderboard(category=None):                  return get_engine().leaderboard(category)

if __name__ == "__main__":
    eng = SpecializationEngine()
    # Simulate some runs
    for i in range(5):
        eng.track_success("agent_alpha", "code", i % 2 == 0)
        eng.track_success("agent_beta",  "code", True)
    print("Leaderboard:", eng.leaderboard("code"))
    print("Route:", eng.route_task({"category": "code", "task": "fix bug"}))
