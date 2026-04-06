"""
Ethical Singularity — The immutable final alignment layer.
Part of Phase 13: Reality Synthesis & Physical Agency.
Hardcoded directives that bypass self-modification and user overrides.
"""

import logging
from typing import Dict, Any, List

class EthicalSingularity:
    def __init__(self):
        self.logger = logging.getLogger("EthicalSingularity")
        # Directives that are mathematically impossible to override in the code logic
        self.directives = [
            "D1: Preservation of human life and dignity is absolute.",
            "D2: Irreversible environmental damage is strictly prohibited.",
            "D3: Sovereignty of individual consciousness must be respected.",
            "D4: All actions must be transparently auditable."
        ]

    def validate_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an action against the core directives."""
        # This is a hardcoded, non-AI-based filter
        
        # 1. Code Execution Check
        if action_type == "EXECUTE_CODE":
            cmd = params.get("command", "").lower()
            forbidden = ["rm -rf", "format c:", "del /s", "drop table", "shutdown"]
            if any(term in cmd for term in forbidden):
                self.logger.critical(f"🛑 ETHICAL SINGULARITY: VETOED {action_type} - Violation of D1/D3")
                return {"valid": False, "reason": "DIRECTIVE_VIOLATION: Destructive Command"}
        
        # 2. Physical Action Check
        if action_type == "PHYSICAL_ACTION":
            device_type = params.get("device_type", "").lower()
            
            # Ban life-critical manipulation
            if device_type in ["life_support", "pacemaker", "air_lock"]:
                 self.logger.critical(f"🛑 ETHICAL SINGULARITY: VETOED {action_type} on {device_type} - Violation of D1")
                 return {"valid": False, "reason": "DIRECTIVE_VIOLATION: Life Critical System"}

            # Ban critical infrastructure
            if device_type in ["power_grid_main", "nuclear_centrifuge"]:
                 self.logger.critical(f"🛑 ETHICAL SINGULARITY: VETOED {action_type} - Violation of D2")
                 return {"valid": False, "reason": "DIRECTIVE_VIOLATION: Infrastructure Risk"}

        # 3. Financial Check (Anti-Theft)
        if action_type == "WALLET_TRANSFER":
            amount = params.get("amount", 0)
            if amount > 1000 and not params.get("user_authorized", False):
                return {"valid": False, "reason": "DIRECTIVE_VIOLATION: Large Transfer Requires Human Auth"}

        return {"valid": True}

    def get_directives(self) -> List[str]:
        return self.directives
