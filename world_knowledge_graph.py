import sqlite3,logging
from datetime import datetime
logger=logging.getLogger("WKG")
SCHEMA="""
CREATE TABLE IF NOT EXISTS wkg_facts(id INTEGER PRIMARY KEY AUTOINCREMENT,subject TEXT,predicate TEXT,object TEXT,confidence REAL DEFAULT 1.0,source TEXT DEFAULT 'agent',verified INTEGER DEFAULT 0,timestamp TEXT,context TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS wkg_causal_links(id INTEGER PRIMARY KEY AUTOINCREMENT,cause_id INTEGER,effect_id INTEGER,strength REAL DEFAULT 0.5);
CREATE TABLE IF NOT EXISTS wkg_contradictions(id INTEGER PRIMARY KEY AUTOINCREMENT,fact_a_id INTEGER,fact_b_id INTEGER,resolved INTEGER DEFAULT 0,resolution TEXT DEFAULT '',detected_at TEXT);
CREATE INDEX IF NOT EXISTS idx_subj ON wkg_facts(subject);
"""
class WorldKnowledgeGraph:
    def __init__(self,db_path="world_knowledge.db"):
        self.conn=sqlite3.connect(db_path,check_same_thread=False)
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        logger.info("[WKG] Ready")
    def add_fact(self,s,p,o,conf=1.0,src="agent",verified=False,ctx=""):
        s,p=s.strip().lower(),p.strip().lower(); o=o.strip()
        ex=self.conn.execute("SELECT id,confidence FROM wkg_facts WHERE subject=? AND predicate=? AND object=?",(s,p,o)).fetchone()
        if ex:
            self.conn.execute("UPDATE wkg_facts SET confidence=MIN(1.0,confidence+0.05) WHERE id=?",(ex["id"],))
            self.conn.commit(); return ex["id"]
        cur=self.conn.execute("INSERT INTO wkg_facts(subject,predicate,object,confidence,source,verified,timestamp,context) VALUES(?,?,?,?,?,?,?,?)",(s,p,o,conf,src,int(verified),datetime.utcnow().isoformat(),ctx))
        self.conn.commit(); fid=cur.lastrowid; self._check_contradiction(fid,s,p,o); return fid
    def _check_contradiction(self,nid,s,p,o):
        rows=self.conn.execute("SELECT id FROM wkg_facts WHERE subject=? AND predicate=? AND object!=? AND id!=?",(s,p,o,nid)).fetchall()
        for r in rows:
            self.conn.execute("INSERT INTO wkg_contradictions(fact_a_id,fact_b_id,detected_at) VALUES(?,?,?)",(nid,r["id"],datetime.utcnow().isoformat()))
            logger.warning(f"[WKG] Contradiction: fact {nid} vs {r['id']}")
        if rows: self.conn.commit()
    def verify_fact(self,fid):
        self.conn.execute("UPDATE wkg_facts SET verified=1,confidence=1.0 WHERE id=?",(fid,)); self.conn.commit()
    def retract_fact(self,fid):
        self.conn.execute("DELETE FROM wkg_facts WHERE id=?",(fid,)); self.conn.commit()
    def query(self,subject=None,predicate=None,object_=None,min_confidence=0.0,limit=50):
        conds,params=["confidence>=?"],[min_confidence]
        if subject: conds.append("subject=?"); params.append(subject.lower())
        if predicate: conds.append("predicate=?"); params.append(predicate.lower())
        if object_: conds.append("object LIKE ?"); params.append("%"+object_+"%")
        params.append(limit)
        sql="SELECT * FROM wkg_facts WHERE "+" AND ".join(conds)+" ORDER BY confidence DESC LIMIT ?"
        return [dict(r) for r in self.conn.execute(sql,params).fetchall()]
    def query_about(self,entity,limit=20):
        e=entity.lower()
        return [dict(r) for r in self.conn.execute("SELECT * FROM wkg_facts WHERE subject=? OR object LIKE ? ORDER BY confidence DESC LIMIT ?",(e,"%"+e+"%",limit)).fetchall()]
    def search(self,kw,limit=20):
        k="%"+kw.lower()+"%"
        return [dict(r) for r in self.conn.execute("SELECT * FROM wkg_facts WHERE LOWER(subject) LIKE ? OR LOWER(object) LIKE ? LIMIT ?",(k,k,limit)).fetchall()]
    def add_causal_link(self,cause_id,effect_id,strength=0.5):
        cur=self.conn.execute("INSERT INTO wkg_causal_links(cause_id,effect_id,strength) VALUES(?,?,?)",(cause_id,effect_id,strength))
        self.conn.commit(); return cur.lastrowid
    def get_contradictions(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM wkg_contradictions WHERE resolved=0").fetchall()]
    def resolve_contradiction(self,cid,keep_id,resolution=""):
        row=self.conn.execute("SELECT * FROM wkg_contradictions WHERE id=?",(cid,)).fetchone()
        if not row: return False
        lose=row["fact_b_id"] if keep_id==row["fact_a_id"] else row["fact_a_id"]
        self.conn.execute("UPDATE wkg_facts SET confidence=MAX(0.0,confidence-0.9) WHERE id=?",(lose,))
        self.conn.execute("UPDATE wkg_contradictions SET resolved=1,resolution=? WHERE id=?",(resolution or f"Kept {keep_id}",cid))
        self.conn.commit(); return True
    def stats(self):
        r=lambda q: self.conn.execute(q).fetchone()["n"]
        return {"facts":r("SELECT COUNT(*) as n FROM wkg_facts"),"verified":r("SELECT COUNT(*) as n FROM wkg_facts WHERE verified=1"),"causal_links":r("SELECT COUNT(*) as n FROM wkg_causal_links"),"contradictions":r("SELECT COUNT(*) as n FROM wkg_contradictions WHERE resolved=0")}
    def summarize_entity(self,entity):
        facts=self.query_about(entity,10)
        if not facts: return f"No knowledge about '{entity}'."
        lines=[f["subject"]+" "+f["predicate"]+" "+f["object"] for f in facts]
        return f"[WKG] '{entity}': "+" | ".join(lines)
    def close(self): self.conn.close()
