
"""
Mission Control Module — Long-term goal persistence and orchestration.
Maintains high-level missions that survive restarts and coordinate swarms.
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

class MissionControl:
    """Manages high-level missions and ensures persistence."""

    def __init__(self, db: Any, llm: Any, swarm_manager: Any):
        self.db = db
        self.llm = llm
        self.swarm = swarm_manager
        self.logger = logging.getLogger("MissionControl")

    def create_mission(self, tenant_id: int, title: str, objective: str, 
                       priority: int = 5, approval_required: bool = False) -> int:
        """Create a new long-term mission (optionally gated by HITL approval)."""
        data = {
            "status": "pending_approval" if approval_required else "active",
            "progress": 0,
            "sub_tasks": [],
            "logs": [f"Mission started at {datetime.now().isoformat()}"]
        }
        mission_id = self.db.add_mission(tenant_id, title, objective, priority, 
                                        metadata=data, approval_required=approval_required)
        self.db.audit(tenant_id, "mission_created", f"Mission #{mission_id}: {title} (Approval: {approval_required})")
        return mission_id

    def update_mission_progress(self, tenant_id: int, mission_id: int):
        """Evaluate mission progress using LLM and update database."""
        mission = self.db.get_mission(tenant_id, mission_id)
        if not mission:
            return

        objective = mission["objective"]
        # In a real scenario, we'd gather data about what has been done
        # For now, we simulate an LLM-based progress check
        prompt = f"""
        Evaluate the progress of the following AI Mission:
        Mission: {mission['title']}
        Goal: {objective}
        Current Status: {mission['status']}
        
        Return a JSON object: {{"progress_percentage": int, "analysis": str, "next_step": str}}
        """
        
        try:
            resp = self.llm.call(prompt, max_tokens=500)
            # Simple extraction (assuming LLM returns clean JSON or we'd need a parser)
            # For robustness, we'd use a regex or pydantic
            eval_data = json.loads(resp)
            
            progress = eval_data.get("progress_percentage", 0)
            analysis = eval_data.get("analysis", "No analysis provided.")
            
            meta = json.loads(mission["metadata"])
            meta["logs"].append(f"Progress update: {progress}% - {analysis}")
            
            self.db.update_mission(
                tenant_id,
                mission_id, 
                progress=progress, 
                metadata=meta
            )
            
            if progress >= 100:
                self.db.update_mission(tenant_id, mission_id, status="completed")
                self.db.audit(tenant_id, "mission_completed", f"Mission #{mission_id} finished.")
                
        except Exception as e:
            self.logger.error(f"Failed to evaluate mission #{mission_id}: {e}")

    def sync_all_tenants(self):
        """Check active missions across all tenants and orchestrate swarms."""
        # Get all tenants from DB
        tenants = self.db.conn.execute("SELECT id FROM tenants WHERE status='active'").fetchall()
        for t in tenants:
            tid = t["id"]
            self.sync_with_swarms(tid)

    def sync_with_swarms(self, tenant_id: int):
        """Check active missions for a specific tenant and spawn/resume swarms if needed."""
        missions = self.db.get_active_missions(tenant_id)
        for m in missions:
            # SKIP if waiting for human approval
            if m["status"] == "pending_approval":
                 continue
                 
            mission_id = m["id"]
            swarm_id = m.get("swarm_id")
            
            if not swarm_id:
                # Mission has no active swarm, spawn one
                self.logger.info(f"Spawning swarm for tenant {tenant_id}, mission #{mission_id}")
                new_swarm_id = self.swarm.spawn_swarm(m["objective"])
                self.db.update_mission(tenant_id, mission_id, swarm_id=new_swarm_id)
            else:
                # Check swarm status
                status = self.swarm.check_status(swarm_id)
                if status == "completed":
                    report = self.swarm.get_final_report(swarm_id)
                    self.logger.info(f"Swarm {swarm_id} completed for mission #{mission_id}")
                    # Update progress based on report
                    self._process_swarm_report(tenant_id, mission_id, report)
                elif status == "failed":
                    self.logger.warning(f"Swarm {swarm_id} failed for mission #{mission_id}. Retrying...")
                    # For simplicity, clear swarm_id to trigger respawn on next sync
                    self.db.update_mission(tenant_id, mission_id, swarm_id=None)

    def _process_swarm_report(self, tenant_id: int, mission_id: int, report: str):
        """Analyze a swarm report and update the mission state."""
        mission = self.db.get_mission(tenant_id, mission_id)
        if not mission: return
        
        prompt = f"""
        Analyze this report for Mission #{mission_id} ({mission['title']}):
        Report: {report}
        
        Is the mission objective '{mission['objective']}' fully achieved?
        Return a JSON object: {{"completed": bool, "progress_increase": int, "summary": str}}
        """
        try:
            resp = self.llm.call(prompt, max_tokens=500)
            eval_data = json.loads(resp)
            
            new_progress = min(100, mission["progress"] + eval_data.get("progress_increase", 10))
            is_done = eval_data.get("completed", False) or new_progress >= 100
            
            meta = json.loads(mission["metadata"])
            meta["logs"].append(f"Swarm reported: {eval_data.get('summary')}")
            
            status = "completed" if is_done else "active"
            self.db.update_mission(
                tenant_id,
                mission_id, 
                progress=new_progress, 
                status=status,
                metadata=meta,
                swarm_id=None # Clear swarm as this window of work is done
            )
        except Exception as e:
             self.logger.error(f"Failed to process report for mission #{mission_id}: {e}")

    def list_missions(self, tenant_id: int) -> List[Dict]:
        """Return all active missions for a tenant."""
        return self.db.get_active_missions(tenant_id)

