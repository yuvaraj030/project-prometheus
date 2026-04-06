"""
Universal API — The unified gateway for all agent sub-systems.
Part of Phase 13: Reality Synthesis & Physical Agency.
"""

import logging
from typing import Dict, Any, List

class UniversalAPI:
    def __init__(self, agent):
        self.agent = agent
        self.logger = logging.getLogger("UniversalAPI")

    def call(self, system: str, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Unified call interface for any sub-system."""
        params = params or {}
        self.logger.info(f"🌐 Universal API Call: {system}.{method}")
        
        try:
            if system == "consciousness":
                if method == "get_state":
                    return self.agent.mind.get_emotional_context()
                elif method == "add_goal":
                    return self.agent.mind.add_goal(params["goal"], params.get("priority", 1))
            
            elif system == "reality":
                if method == "scan":
                    return self.agent.reality.scan_environment()
                elif method == "act":
                    return self.agent.reality.execute_physical_action(params["device_id"], params["action"], params.get("data", {}))
            
            elif system == "predict":
                if method == "forecast":
                    return self.agent.predict.generate_forecast(params["category"])
            
            elif system == "mesh":
                if method == "peers":
                    return self.agent.mesh.get_active_peers()
                elif method == "propose":
                    return self.agent.mesh.initiate_proposal(params["id"], params["desc"])

        except Exception as e:
            self.logger.error(f"Universal API Error: {e}")
            return {"status": "error", "message": str(e)}

        return {"status": "unsupported", "system": system, "method": method}
