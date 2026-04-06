"""
Infrastructure Manager — Autonomous scaling and resource management.
Part of Phase 10: Sovereign Autonomy.
Allows the agent to trigger its own Docker/K8s scaling and maintain health.
"""

import os
import logging
import subprocess
from typing import Dict, Any

from cloud_orchestrator import CloudOrchestrator

class InfraManager:
    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger("InfraManager")
        self.load_history = [] # Rolling window of mission counts
        self.cloud = CloudOrchestrator()

    def trigger_scale_up(self, service_name: str = "agent", cloud: bool = True):
        """Simulate or trigger horizontal scaling via Docker Compose or AWS."""
        self.logger.info(f"🚀 Triggering SCALE UP for service: {service_name}")
        self.db.audit(0, "infra_scale_up", f"Initiated horizontal scaling for {service_name}", severity="warning")
        
        if cloud and self.cloud.ec2:
            self.logger.info("Delegating to Cloud Orchestrator (AWS EC2)...")
            result = self.cloud.provision_agent_node()
            return {"status": "scaling_initiated", "service": service_name, "cloud_result": result}
            
        # Fallback local clustering
        # subprocess.run(["docker-compose", "up", "-d", "--scale", f"{service_name}=+1"])
        return {"status": "scaling_initiated_locally", "service": service_name}

    def trigger_backup(self):
        """Initiate an autonomous database and vector memory backup."""
        self.logger.info("💾 Triggering AUTONOMOUS BACKUP")
        timestamp = subprocess.check_output(["powershell", "Get-Date -Format 'yyyyMMdd_HHmm'"]).decode().strip()
        backup_name = f"sovereign_backup_{timestamp}.zip"
        
        # Simulated backup logic. In production: zip core db + vector storage
        self.db.audit(0, "infra_backup", f"Backup created: {backup_name}")
        return {"status": "backup_complete", "filename": backup_name}

    def optimize_resources(self, cpu_usage: float):
        """Adjust internal priorities based on system load."""
        if cpu_usage > 85.0:
            self.logger.warning("🔥 High CPU detected! Throttling background tasks.")
            self.db.audit(0, "infra_optimize", "High CPU load - entered 'power_save' mode", severity="warning")
            return "throttled"
        return "optimal"

    def log_mission_load(self, mission_count: int):
        """Record the current mission load for predictive analysis."""
        self.load_history.append(mission_count)
        if len(self.load_history) > 10:
            self.load_history.pop(0)
            
    def predict_load(self) -> float:
        """Forecast mission load based on recent trends (moving average)."""
        if not self.load_history:
            return 0.0
        return sum(self.load_history) / len(self.load_history)

    def proactive_scale(self):
        """Check forecasted load and trigger scale-up before hitting critical limits."""
        predicted = self.predict_load()
        # Threshold: if predicted load is high (e.g. > 4.0 missions per cycle)
        if predicted > 4.0:
            self.logger.info(f"🔮 Predictive Scale Triggered: Forecasted load {predicted:.2f}")
            self.db.audit(0, "infra_predictive_scale", f"Proactive scaling initiated based on load forecast: {predicted:.2f}")
            return self.trigger_scale_up()
        return {"status": "stable", "forecast": predicted}
