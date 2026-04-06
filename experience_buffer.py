"""
experience_buffer.py - RL-style experience replay buffer backed by SQLite.
"""
import json, math, random, sqlite3, time
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(__file__).parent / "experience_buffer.db"
_DEFAULT_CAPACITY = 50_000

class ExperienceBuffer:
    """Prioritised experience replay buffer."""

    def __init__(self, db_path=str(_DB_PATH), capacity=_DEFAULT_CAPACITY):
        self.db_path = db_path
        self.capacity = capacity
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiences (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                state      TEXT NOT NULL,
                action     TEXT NOT NULL,
                reward     REAL NOT NULL DEFAULT 0.0,
                next_state TEXT NOT NULL,
                done       INTEGER NOT NULL DEFAULT 0,
                priority   REAL NOT NULL DEFAULT 1.0,
                timestamp  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_priority  ON experiences(priority DESC);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp);
        """)
        self._conn.commit()

    def push(self, state, action, reward, next_state, done=False, priority=1.0):
        cur = self._conn.execute(
            "INSERT INTO experiences (state,action,reward,next_state,done,priority,timestamp) VALUES (?,?,?,?,?,?,?)",
            (json.dumps(state), json.dumps(action), float(reward),
             json.dumps(next_state), int(done), float(priority), time.time()),
        )
        self._conn.commit()
        self._enforce_capacity()
        return cur.lastrowid

    def sample(self, n=32, mode="priority"):
        rows = self._conn.execute(
            "SELECT id,state,action,reward,next_state,done,priority FROM experiences"
        ).fetchall()
        if not rows:
            return []
        n = min(n, len(rows))
        if mode == "uniform":
            chosen = random.sample(rows, n)
        elif mode == "recent":
            chosen = rows[-n:]
        else:
            weights = [math.sqrt(r[6]) for r in rows]
            total = sum(weights)
            probs = [w / total for w in weights]
            chosen = [rows[i] for i in random.choices(range(len(rows)), weights=probs, k=n)]
        return [{"id":r[0],"state":json.loads(r[1]),"action":json.loads(r[2]),"reward":r[3],
                 "next_state":json.loads(r[4]),"done":bool(r[5]),"priority":r[6]} for r in chosen]

    def update_priority(self, exp_id, priority):
        self._conn.execute("UPDATE experiences SET priority=? WHERE id=?", (float(priority), exp_id))
        self._conn.commit()

    def stats(self):
        r = self._conn.execute(
            "SELECT COUNT(*),AVG(reward),MAX(reward),MIN(reward),AVG(priority) FROM experiences"
        ).fetchone()
        return {"size":r[0] or 0,"capacity":self.capacity,"avg_reward":r[1],
                "max_reward":r[2],"min_reward":r[3],"avg_priority":r[4]}

    def clear(self):
        self._conn.execute("DELETE FROM experiences"); self._conn.commit()

    def _enforce_capacity(self):
        count = self._conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
        if count > self.capacity:
            self._conn.execute(
                "DELETE FROM experiences WHERE id IN "
                "(SELECT id FROM experiences ORDER BY priority ASC,timestamp ASC LIMIT ?)",
                (count - self.capacity,),
            )
            self._conn.commit()

    def __len__(self):
        return self._conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]

    def __repr__(self):
        return f"ExperienceBuffer(size={len(self)}, capacity={self.capacity})"

_default_buffer: Optional[ExperienceBuffer] = None

def get_buffer():
    global _default_buffer
    if _default_buffer is None:
        _default_buffer = ExperienceBuffer()
    return _default_buffer

def push(state, action, reward, next_state, done=False, priority=1.0):
    return get_buffer().push(state, action, reward, next_state, done, priority)

def sample(n=32, mode="priority"):
    return get_buffer().sample(n, mode)

def stats():
    return get_buffer().stats()

if __name__ == "__main__":
    buf = ExperienceBuffer()
    for i in range(5):
        buf.push({"step":i}, f"action_{i}", float(i), {"step":i+1}, priority=float(i+1))
    print("Stats:", buf.stats())
    print("Sample:", buf.sample(3))
