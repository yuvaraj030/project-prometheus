
"""
Self-Correction Module — Proactive error detection and auto-patching.
Monitors the audit log for failures and attempts to fix them using SelfModEngine.
"""
import json
import logging
import traceback
from typing import List, Dict, Any, Optional

class SelfCorrection:
    """Monitors system health and attempts autonomous repairs."""

    def __init__(self, db: Any, llm: Any, self_mod: Any):
        self.db = db
        self.llm = llm
        self.self_mod = self_mod
        self.logger = logging.getLogger("SelfCorrection")
        self.last_checked_id = 0

    def check_for_errors(self):
        """Scan audit log for recent errors or failures."""
        logs = self.db.get_audit_log(severity="error", limit=10)
        # Filter for new logs only
        new_errors = [l for l in logs if l['id'] > self.last_checked_id]
        
        for error in new_errors:
            self.logger.warning(f"Detected system error: {error['action']} - {error['details']}")
            self._analyze_and_fix(error)
            self.last_checked_id = max(self.last_checked_id, error['id'])

    def _analyze_and_fix(self, error: Dict[str, Any]):
        """Use LLM to analyze the error and propose a patch."""
        action = error['action']
        details = error['details']
        
        # Identify if the error is related to a specific method/class
        # This is a heuristic; real implementation might use stack tracks from a separate table
        prompt = f"""
        Analyze the following system error in an AI Agent:
        Action: {action}
        Details: {details}
        
        Is this error fixable by modifying a Python method in the codebase?
        If yes, identify the class and method name, and explain the fix.
        
        Return a JSON object: 
        {{
            "is_fixable": bool,
            "class_name": str or null,
            "method_name": str or null,
            "analysis": str,
            "proposed_fix_logic": str
        }}
        """
        
        try:
            resp = self.llm.call(prompt, max_tokens=500)
            analysis = json.loads(resp)
            
            if analysis.get("is_fixable") and analysis.get("method_name"):
                self._apply_patch(analysis)
                
        except Exception as e:
            self.logger.error(f"Self-correction analysis failed: {e}")

    def _apply_patch(self, plan: Dict[str, Any]):
        """Attempt to apply the proposed fix using SelfModEngine."""
        method_name = plan["method_name"]
        class_name = plan["class_name"]
        logic = plan["proposed_fix_logic"]
        
        self.logger.info(f"Attempting auto-patch for {method_name}...")
        
        # Generate the actual code fix
        # In a real scenario, we'd pull the existing source first
        # For the demo, we'll ask the LLM to generate the full improved method
        prompt = f"""
        Generate the full Python source code for the method '{method_name}' 
        (inside class '{class_name}') to fix the following issue:
        Fix Logic: {logic}
        
        Output ONLY the code for the method body, starting from the first line after 'def...:'.
        Use 4 spaces for indentation.
        """
        
        try:
            new_code = self.llm.call(prompt, max_tokens=1000)
            # Clean markdown
            if "```python" in new_code:
                new_code = new_code.split("```python")[1].split("```")[0].strip()
            elif "```" in new_code:
                new_code = new_code.split("```")[1].split("```")[0].strip()
            
            # Since we are in-memory (or file-based for core), we need to know WHERE the method is.
            # For simplicity in this module, we'll assume the agent's main orchestrator 
            # will pass the right target object to this method or we use core class modification.
            
            # In Phase 4, we'll use modify_core_class for permanent fixes if class_name is provided
            # Or modify_method if we have a live instance.
            
            if class_name:
                # Permanent file fix
                res = self.self_mod.modify_core_class(class_name, f"class {class_name}:\n    def {method_name}(self, *args, **kwargs):\n        " + new_code.replace("\n", "\n        "))
                if res["success"]:
                    self.db.audit("auto_patch_success", f"Fixed {class_name}.{method_name}")
                else:
                    self.db.audit("auto_patch_failed", f"Failed to fix {class_name}.{method_name}: {res['error']}")
            
        except Exception as e:
            self.logger.error(f"Auto-patch execution failed: {e}")

    def run_periodic_check(self):
        """Background task for periodic health checks."""
        try:
            self.check_for_errors()
        except Exception as e:
            self.logger.error(f"Periodic health check failed: {e}")
