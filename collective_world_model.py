import sqlite3,json,logging
from datetime import datetime
from typing import Any,Dict,List
logger=logging.getLogger("CollectiveWorldModel")
_S="""
CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY AUTOINCREMENT,subject TEXT,predicate TEXT,object TEXT,confidence REAL DEFAULT 1.0,agent_id TEXT,votes INT DEFAULT 1,conflicts INT DEFAULT 0,timestamp TEXT);
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY AUTOINCREMENT,fact_a INT,fact_b INT,resolved INT DEFAULT 0,winner INT,detected_at TEXT);
"""
class CollectiveWorldModel:
    """Distributed world model – agents contribute facts, conflicts resolved by confidence voting."""
    def __init__(self,db="collective_world.db"):
        self.c=sqlite3.connect(db,check_same_thread=False);self.c.row_factory=sqlite3.Row
        self.c.executescript(_S);self.c.commit()
        logger.info("CollectiveWorldModel ready")
    def merge_fact(self,subject:str,predicate:str,obj:str,agent_id:str,confidence:float=0.8)->int:
        s,p=subject.lower().strip(),predicate.lower().strip()
        ex=self.c.execute("SELECT id,confidence,votes FROM facts WHERE subject=? AND predicate=? AND object=?",(s,p,obj)).fetchone()
        if ex:
            nc=min(1.0,(ex["confidence"]*ex["votes"]+confidence)/(ex["votes"]+1))
            self.c.execute("UPDATE facts SET confidence=?,votes=votes+1,timestamp=? WHERE id=?",
                           (nc,datetime.utcnow().isoformat(),ex["id"]));self.c.commit();return ex["id"]
        cur=self.c.execute("INSERT INTO facts(subject,predicate,object,confidence,agent_id,timestamp) VALUES(?,?,?,?,?,?)",
                            (s,p,obj,confidence,agent_id,datetime.utcnow().isoformat()))
        self.c.commit();fid=cur.lastrowid;self._detect_conflict(fid,s,p,obj);return fid
    def _detect_conflict(self,fid,s,p,obj):
        rows=self.c.execute("SELECT id FROM facts WHERE subject=? AND predicate=? AND object!=? AND id!=?",(s,p,obj,fid)).fetchall()
        for r in rows:
            self.c.execute("INSERT INTO conflicts(fact_a,fact_b,detected_at) VALUES(?,?,?)",(fid,r["id"],datetime.utcnow().isoformat()))
        if rows:self.c.commit()
    def resolve_conflict(self,conflict_id:int)->Dict:
        row=self.c.execute("SELECT * FROM conflicts WHERE id=?",(conflict_id,)).fetchone()
        if not row:return{"error":"not found"}
        a=self.c.execute("SELECT * FROM facts WHERE id=?",(row["fact_a"],)).fetchone()
        b=self.c.execute("SELECT * FROM facts WHERE id=?",(row["fact_b"],)).fetchone()
        if not a or not b:return{"error":"facts missing"}
        winner=a["id"] if (a["confidence"]*a["votes"])>=(b["confidence"]*b["votes"]) else b["id"]
        loser=b["id"] if winner==a["id"] else a["id"]
        self.c.execute("UPDATE facts SET confidence=MAX(0,confidence-0.8) WHERE id=?",(loser,))
        self.c.execute("UPDATE conflicts SET resolved=1,winner=? WHERE id=?",(winner,conflict_id))
        self.c.commit();return{"winner":winner,"loser":loser}
    def consensus_query(self,subject:str,predicate:str)->List[Dict]:
        rows=self.c.execute("SELECT *,confidence*votes AS score FROM facts WHERE subject=? AND predicate=? ORDER BY score DESC LIMIT 10",
                            (subject.lower(),predicate.lower())).fetchall()
        return[dict(r) for r in rows]
    def query(self,subject:str,limit=20)->List[Dict]:
        return[dict(r) for r in self.c.execute("SELECT * FROM facts WHERE subject=? ORDER BY confidence DESC LIMIT ?",(subject.lower(),limit)).fetchall()]
    def stats(self)->Dict:
        return{"facts":self.c.execute("SELECT COUNT(*) n FROM facts").fetchone()["n"],
               "conflicts":self.c.execute("SELECT COUNT(*) n FROM conflicts WHERE resolved=0").fetchone()["n"]}
    def close(self):self.c.close()
