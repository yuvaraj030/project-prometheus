import sqlite3,json,logging
from datetime import datetime
logger=logging.getLogger("MetaLearner")
_S="CREATE TABLE IF NOT EXISTS ps(strategy TEXT,task_type TEXT,success INT DEFAULT 0,failure INT DEFAULT 0,total_reward REAL DEFAULT 0,avg_reward REAL DEFAULT 0,last_used TEXT,PRIMARY KEY(strategy,task_type));"
class MetaLearner:
    def __init__(self,db="meta_learner.db"):
        self.c=sqlite3.connect(db,check_same_thread=False);self.c.row_factory=sqlite3.Row
        self.c.executescript(_S);self.c.commit()
    def record(self,strategy,task_type,success,reward):
        n=datetime.utcnow().isoformat()
        self.c.execute("INSERT INTO ps VALUES(?,?,?,?,?,?,?) ON CONFLICT(strategy,task_type) DO UPDATE SET success=success+?,failure=failure+?,total_reward=total_reward+?,avg_reward=(total_reward+?)/(success+failure+1),last_used=?",(strategy,task_type,int(success),int(not success),reward,reward,n,int(success),int(not success),reward,reward,n));self.c.commit()
    def best(self,task_type):
        r=self.c.execute("SELECT strategy FROM ps WHERE task_type=? ORDER BY avg_reward DESC LIMIT 1",(task_type,)).fetchone();return r[0] if r else "default"
    def evolve(self):
        rows=self.c.execute("SELECT strategy FROM ps ORDER BY avg_reward DESC LIMIT 3").fetchall()
        return "Strategies: "+", ".join(r[0] for r in rows) if rows else ""
    def all_stats(self):
        return [dict(r) for r in self.c.execute("SELECT * FROM ps ORDER BY avg_reward DESC").fetchall()]
    def close(self):self.c.close()
