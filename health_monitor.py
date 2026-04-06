"""
Health Monitor — Real-time telemetry and proactive system maintenance.
"""

import os
import psutil
import logging
import time
from typing import Dict

class HealthMonitor:
    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger("HealthMonitor")
        self.process = psutil.Process(os.getpid())

    def get_stats(self) -> Dict:
        """Gather current system and process metrics."""
        cpu = self.process.cpu_percent(interval=0.1)
        mem = self.process.memory_info().rss / (1024 * 1024) # MB
        
        stats = {
            "uptime": time.time() - self.process.create_time(),
            "cpu_usage_percent": cpu,
            "memory_usage_mb": mem,
            "thread_count": self.process.num_threads(),
            "disk_usage": psutil.disk_usage('/').percent
        }
        return stats

    def check_health(self, tenant_id: int = 0):
        """Perform a health check and log to audit."""
        stats = self.get_stats()
        
        severity = "info"
        if stats["cpu_usage_percent"] > 80 or stats["memory_usage_mb"] > 1024:
            severity = "warning"
            self.logger.warning(f"High resource usage detected: {stats}")
        
        self.db.record_metric(tenant_id, "sys_cpu", stats["cpu_usage_percent"])
        self.db.record_metric(tenant_id, "sys_mem", stats["memory_usage_mb"])
        
        self.db.audit(tenant_id, "health_check", str(stats), severity=severity, source="monitor")
        return stats
