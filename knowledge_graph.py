"""
Knowledge Graph Engine — Relational Memory for advanced reasoning.
Part of Phase 10: Sovereign Autonomy.
Manages Subject-Predicate-Object triples for deep semantic linking.
"""

import logging
from typing import Dict, Any, List, Optional

class KnowledgeGraph:
    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger("KnowledgeGraph")

    def add_triple(self, tenant_id: int, subject: str, predicate: str, object: str,
                   confidence: float = 1.0, privacy_level: str = "private"):
        """Add a relationship fact to the graph."""
        try:
            sql = """INSERT INTO knowledge_triples (tenant_id, subject, predicate, object, confidence, privacy_level)
                     VALUES (?, ?, ?, ?, ?, ?)
                     ON CONFLICT(tenant_id, subject, predicate, object) DO UPDATE SET 
                     confidence=excluded.confidence, privacy_level=excluded.privacy_level"""
            
            # Convert ? to %s for Postgres
            if self.db.is_postgres:
                sql = sql.replace("?", "%s")
                with self.db.conn.cursor() as cur:
                    cur.execute(sql, (tenant_id, subject, predicate, object, confidence, privacy_level))
                self.db.conn.commit()
            else:
                self.db.conn.execute(sql, (tenant_id, subject, predicate, object, confidence, privacy_level))
                self.db.conn.commit()
            
            self.logger.info(f"Added triple: {subject} ({predicate}) {object}")
        except Exception as e:
            self.logger.error(f"Error adding triple: {e}")

    def query_subject(self, tenant_id: int, subject: str) -> List[Dict]:
        """Find all relationships for a given subject."""
        sql = "SELECT predicate, object, confidence FROM knowledge_triples WHERE tenant_id=? AND subject LIKE ?"
        query = f"%{subject}%"
        
        if self.db.is_postgres:
            sql = sql.replace("?", "%s")
            with self.db.conn.cursor() as cur:
                cur.execute(sql, (tenant_id, query))
                return [dict(r) for r in cur.fetchall()]
        else:
            rows = self.db.conn.execute(sql, (tenant_id, query)).fetchall()
            return [dict(r) for r in rows]

    def query_triple(self, tenant_id: int, subject: str = None, predicate: str = None, 
                     object: str = None) -> List[Dict]:
        """General multi-parameter search for relationships."""
        sql = "SELECT subject, predicate, object, confidence FROM knowledge_triples WHERE tenant_id=?"
        params = [tenant_id]
        
        if subject:
            sql += " AND subject LIKE ?"
            params.append(f"%{subject}%")
        if predicate:
            sql += " AND predicate LIKE ?"
            params.append(f"%{predicate}%")
        if object:
            sql += " AND object LIKE ?"
            params.append(f"%{object}%")
            
        if self.db.is_postgres:
            sql = sql.replace("?", "%s")
            with self.db.conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                return [dict(r) for r in cur.fetchall()]
        else:
            rows = self.db.conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def expand_context(self, tenant_id: int, keywords: List[str]) -> str:
        """Find relevant facts for a list of keywords to expand prompt context."""
        facts = []
        for kw in keywords:
            triples = self.query_triple(tenant_id, subject=kw)
            for t in triples[:5]:
                facts.append(f"{t['subject']} -> {t['predicate']} -> {t['object']}")
        
        if not facts:
            return ""
        return "[Relational Knowledge]:\n" + "\n".join(f"  - {f}" for f in list(set(facts)))

    # --- Federated Knowledge ---
    def export_federated_insights(self, tenant_id: int) -> List[Dict]:
        """Export all 'shared' or 'public' triples for federation."""
        sql = "SELECT subject, predicate, object, confidence FROM knowledge_triples WHERE tenant_id=? AND privacy_level IN ('shared', 'public')"
        
        if self.db.is_postgres:
            sql = sql.replace("?", "%s")
            with self.db.conn.cursor() as cur:
                cur.execute(sql, (tenant_id,))
                return [dict(r) for r in cur.fetchall()]
        else:
            rows = self.db.conn.execute(sql, (tenant_id,)).fetchall()
            return [dict(r) for r in rows]

    def import_federated_insights(self, tenant_id: int, insights: List[Dict]):
        """Merge federated insights into the local graph as 'shared' status."""
        for fact in insights:
            self.add_triple(
                tenant_id, 
                fact["subject"], 
                fact["predicate"], 
                fact["object"], 
                confidence=fact.get("confidence", 0.5),
                privacy_level="shared"
            )
        self.logger.info(f"Imported {len(insights)} federated facts for tenant {tenant_id}")
