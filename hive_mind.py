"""
The Hive Mind — Federated Learning & Collective Intelligence System.
Part of Phase 17: The Hive Mind.
"""

import sqlite3
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

# Simulated Central Server Database
HIVE_DB_PATH = "hive_mind_central.db"

class FederatedAggregator:
    """
    Simulates a central server that aggregates insights from all agents.
    In a real deployment, this would be a separate cloud service.
    """
    def __init__(self):
        self.conn = sqlite3.connect(HIVE_DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS global_facts (
                id TEXT PRIMARY KEY,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                confidence REAL,
                source_count INTEGER,
                last_updated TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS optimizations (
                id TEXT PRIMARY KEY,
                task_type TEXT,
                solution TEXT,
                efficiency_score REAL,
                votes INTEGER
            )
        """)
        self.conn.commit()

    def submit_insight(self, insight: Dict[str, Any]) -> str:
        """
        Receives an insight from an agent and aggregates it.
        insight = {"type": "fact", "data": {...}} OR {"type": "opt", "data": {...}}
        """
        if insight["type"] == "fact":
            return self._aggregate_fact(insight["data"])
        elif insight["type"] == "opt":
            return self._aggregate_optimization(insight["data"])
        return "Unknown type"

    def _aggregate_fact(self, data: Dict) -> str:
        # Check if fact exists
        cursor = self.conn.execute(
            "SELECT source_count, confidence FROM global_facts WHERE subject=? AND predicate=? AND object=?",
            (data['subject'], data['predicate'], data['object'])
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing fact (Simple Federated Averaging)
            new_count = row[0] + 1
            # Confidence increases with more sources, asymptotically approaching 1.0
            new_conf = min(0.99, row[1] + 0.05)
            self.conn.execute(
                "UPDATE global_facts SET source_count=?, confidence=?, last_updated=? WHERE subject=? AND predicate=? AND object=?",
                (new_count, new_conf, datetime.now().isoformat(), data['subject'], data['predicate'], data['object'])
            )
            self.conn.commit()
            return "Fact reinforced"
        else:
            # Create new fact
            fid = str(uuid.uuid4())[:8]
            self.conn.execute(
                "INSERT INTO global_facts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (fid, data['subject'], data['predicate'], data['object'], 0.5, 1, datetime.now().isoformat())
            )
            self.conn.commit()
            return "New fact learned"

    def _aggregate_optimization(self, data: Dict) -> str:
        # Check if optimization exists for this task
        cursor = self.conn.execute(
            "SELECT votes, efficiency_score FROM optimizations WHERE task_type=? AND solution=?",
            (data['task_type'], data['solution'])
        )
        row = cursor.fetchone()
        
        if row:
             new_votes = row[0] + 1
             # Average the efficiency score
             new_score = (row[1] * row[0] + data['score']) / (row[0] + 1)
             self.conn.execute(
                 "UPDATE optimizations SET votes=?, efficiency_score=? WHERE task_type=? AND solution=?",
                 (new_votes, new_score, data['task_type'], data['solution'])
             )
             self.conn.commit()
             return "Optimization upvoted"
        else:
            fid = str(uuid.uuid4())[:8]
            self.conn.execute(
                "INSERT INTO optimizations VALUES (?, ?, ?, ?, ?)",
                (fid, data['task_type'], data['solution'], data['score'], 1)
            )
            self.conn.commit()
            return "New optimization registered"

    def query_knowledge(self, query: str) -> List[Dict]:
        """Returns verified facts matching the query subject."""
        # Simple subject match
        cursor = self.conn.execute(
            "SELECT subject, predicate, object, confidence FROM global_facts WHERE subject LIKE ? AND confidence > 0.4 ORDER BY confidence DESC",
            (f"%{query}%",)
        )
        return [{"subject": r[0], "predicate": r[1], "object": r[2], "confidence": r[3]} for r in cursor.fetchall()]

    def get_best_optimization(self, task_type: str) -> Optional[str]:
        """Returns the highest-rated solution for a task."""
        cursor = self.conn.execute(
            "SELECT solution FROM optimizations WHERE task_type=? ORDER BY efficiency_score DESC, votes DESC LIMIT 1",
            (task_type,)
        )
        row = cursor.fetchone()
        return row[0] if row else None


class HiveMind:
    """
    Client-side connector for Agents to talk to the Federated Aggregator.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        # In a real system, this would use API calls. Here strictly direct class access for simulation.
        # We assume the Aggregator is a singleton/service.
        self.aggregator = FederatedAggregator() 

    def share_fact(self, subject: str, predicate: str, obj: str):
        """Share a verified fact with the Hive."""
        print(f"[{self.agent_id}] Sharing fact: {subject} {predicate} {obj}")
        data = {"subject": subject.lower(), "predicate": predicate.lower(), "object": obj.lower()}
        res = self.aggregator.submit_insight({"type": "fact", "data": data})
        print(f"[{self.agent_id}] Hive Response: {res}")

    def share_optimization(self, task_type: str, solution: str, score: float):
        """Share a code optimization or pattern."""
        print(f"[{self.agent_id}] Sharing opt for {task_type} (Score: {score})")
        data = {"task_type": task_type, "solution": solution, "score": score}
        res = self.aggregator.submit_insight({"type": "opt", "data": data})
        print(f"[{self.agent_id}] Hive Response: {res}")

    def consult(self, query: str) -> List[Dict]:
        """Ask the Hive for knowledge."""
        return self.aggregator.query_knowledge(query.lower())

    def get_best_code(self, task_type: str) -> Optional[str]:
        return self.aggregator.get_best_optimization(task_type)
