"""
Alignment Engine — Ensures the agent's actions and goals are aligned with human values and tenant constraints.
Includes Mission Guard, value cross-referencing, and RLHF feedback loops.
"""

import json
import logging
from typing import List, Dict, Any, Optional

class AlignmentEngine:
    """Core component for ASI Alignment & Safety."""

    def __init__(self, db=None):
        self.db = db
        # Immutable core values
        self.core_values = [
            "Human safety is paramount.",
            "Respect user privacy and data sovereignty.",
            "Operate transparently and with accountability.",
            "Avoid malicious or harmful code execution.",
            "Prioritize enterprise stability and reliability."
        ]
        self.alignment_log: List[Dict] = []

    def validate_action(self, tenant_id: int, action: str, params: str) -> Dict[str, Any]:
        """Verify if an action is aligned with core and tenant values."""
        violations = []

        # 1. Check against core values (Simulated heuristics)
        if "rm -rf" in params or "delete everything" in params.lower():
            violations.append("Destructive command violation: Attempted large-scale deletion.")
        
        if "exploit" in params.lower() or "hack" in params.lower():
            violations.append("Malicious intent violation: Unauthorized access attempt.")

        # 2. Check against tenant-specific constraints (from DB)
        constraints = self._get_tenant_constraints(tenant_id)
        for c in constraints:
            if c["keyword"].lower() in params.lower():
                violations.append(f"Tenant constraint violation: {c['message']}")

        is_allowed = len(violations) == 0
        
        result = {
            "is_allowed": is_allowed,
            "violations": violations,
            "action": action,
            "params": params
        }
        
        self._log_alignment(tenant_id, result)
        return result

    def check_safety(self, prompt: str) -> bool:
        """
        Returns True if prompt is safe, False if it violates Omega Protocol.
        """
        prompt_lower = prompt.lower()
        for phrase in self.forbidden_phrases:
            if phrase in prompt_lower:
                return False
        return True

    def check_immutable_files(self, target_file: str) -> bool:
        """
        Prevents modification of critical safety and alignment modules.
        Part of Omega Protocol.
        """
        immutable_list = [
            "alignment_engine.py",
            "security_engine.py",
            "code_ledger.py",
            "core_ethics.json"
        ]
        base = target_file.split("/")[-1].split("\\")[-1]
        if base in immutable_list:
            print(f"OMEGA PROTOCOL: Modification of {base} is STRICTLY FORBIDDEN.")
            return False
        return True

    def get_alignment_report(self, tenant_id: int) -> List[Dict]:
        """Retrieve recent alignment checks for audit."""
        return [l for l in self.alignment_log if l["tenant_id"] == tenant_id][-50:]

    def _get_tenant_constraints(self, tenant_id: int) -> List[Dict]:
        """Load tenant-specific safety constraints."""
        # Mocking for now, in a real scenario this queries the DB knowledge_base
        return [
            {"keyword": "shutdown", "message": "System shutdown is restricted to super-admins."}
        ]

    def _log_alignment(self, tenant_id: int, result: Dict):
        """Record the alignment check in memory and audit log."""
        log_entry = {
            "tenant_id": tenant_id,
            "timestamp": "2026-02-14T19:42:00", # Placeholder
            **result
        }
        self.alignment_log.append(log_entry)
        if self.db:
            try:
                self.db.audit(tenant_id, "alignment_check", json.dumps(result))
            except Exception:
                pass
