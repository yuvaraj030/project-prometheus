"""
Memory Compressor — Reduces vector memory bloat by summarizing aged data.
Consolidates long conversation histories into semantic knowledge units.
"""

import json
import logging
from typing import List, Dict
from datetime import datetime, timedelta

class MemoryCompressor:
    def __init__(self, database, llm, vector_memory, learner):
        self.db = database
        self.llm = llm
        self.vmem = vector_memory
        self.learner = learner
        self.logger = logging.getLogger("MemoryCompressor")

    def run_compression(self, tenant_id: int):
        """Find old conversations and compress them into knowledge items."""
        self.logger.info(f"Running memory compression for tenant {tenant_id}")
        
        # 1. Fetch conversations older than 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor = self.db.conn.execute(
            "SELECT session_id, role, content FROM conversations WHERE tenant_id=? AND created_at < ? ORDER BY created_at ASC",
            (tenant_id, yesterday)
        )
        rows = cursor.fetchall()
        
        if len(rows) < 20: 
            return # Not enough volume to compress

        # 2. Group by session
        sessions = {}
        for r in rows:
            sid = r["session_id"]
            if sid not in sessions: sessions[sid] = []
            sessions[sid].append(f"{r['role']}: {r['content']}")

        # 3. Compress each session
        for sid, history in sessions.items():
            if len(history) < 4: continue
            
            text_block = "\n".join(history)
            prompt = f"""
            Summarize the following conversation into a set of core facts, lessons, or user preferences.
            Discard redundant fluff. Focus on what the agent should remember long-term.
            
            Conversation:
            {text_block}
            
            Return a concise list of bullet points.
            """
            
            try:
                summary = self.llm.call(prompt, system="You are a knowledge consolidation engine.", max_tokens=500)
                if len(summary.strip()) > 30:
                    # Save as high-level knowledge
                    self.learner.learn_text(tenant_id, summary, topic="compressed_memory", source=f"compression:{sid}")
                    
                    # 4. Optional: Mark original rows as compressed or delete them to save space
                    # For now, we just audit that we've compressed them
                    self.db.audit(tenant_id, "memory_compressed", f"Compressed session {sid}")
            except Exception as e:
                self.logger.error(f"Compression failed for session {sid}: {e}")
