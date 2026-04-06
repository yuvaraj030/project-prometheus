"""
Resource Manager — Monitors usage, budgets, and rate limits.
Crucial for free-tier sustainability.
"""

import time
import json
import os
from typing import Dict, Any, List

class ResourceManager:
    def __init__(self, db=None):
        self.db = db
        self.usage_log = []
        self.daily_budget = 0.0 # USD, 0 means infinite or free
        self.daily_token_limit = 1000000 # Default 1M tokens
        self.reset_time = time.time() + 86400
        
    def log_usage(self, provider: str, model: str, tokens: int, cost: float = 0.0):
        """Record a single usage event."""
        event = {
            "timestamp": time.time(),
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "cost": cost
        }
        self.usage_log.append(event)
        
        # Persist to database if available
        if self.db:
            try:
                self.db.add_usage_entry(provider, model, tokens, cost)
            except:
                pass
                
    def get_daily_usage(self) -> Dict[str, Any]:
        """Calculate total usage in the last 24 hours."""
        now = time.time()
        day_ago = now - 86400
        
        relevant = [e for e in self.usage_log if e["timestamp"] > day_ago]
        
        total_tokens = sum(e["tokens"] for e in relevant)
        total_cost = sum(e["cost"] for e in relevant)
        
        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "count": len(relevant)
        }
        
    def check_constraints(self) -> Dict[str, Any]:
        """Check if we are exceeding any limits."""
        usage = self.get_daily_usage()
        
        exceeded_tokens = usage["total_tokens"] > self.daily_token_limit
        exceeded_cost = self.daily_budget > 0 and usage["total_cost"] > self.daily_budget
        
        return {
            "allow_execution": not (exceeded_tokens or exceeded_cost),
            "reason": "Token limit exceeded" if exceeded_tokens else ("Budget exceeded" if exceeded_cost else ""),
            "usage": usage
        }

    def get_status_report(self) -> str:
        """String report of current resource status."""
        usage = self.get_daily_usage()
        report = [
            "📊 RESOURCE STATUS REPORT",
            f"Daily Tokens: {usage['total_tokens']:,} / {self.daily_token_limit:,}",
            f"Daily Cost: ${usage['total_cost']:.4f}"
        ]
        if self.daily_budget > 0:
            report[-1] += f" / ${self.daily_budget:.2f}"
            
        return "\n".join(report)
