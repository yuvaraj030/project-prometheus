"""
Evolution Sandbox — A safe, high-speed environment for testing recursive self-evolution.
Part of Phase 12: Galactic Scale & Quantum Logic.
Allows the agent to run infinite self-recursive loops in isolation.
"""

import os
import sys
import time
import shutil

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.curdir))

from self_mod_engine import SelfModEngine
from wasm_sandbox import WasmSandbox

class EvolutionSandbox:
    def __init__(self, target_file: str = "sandbox_agent.py"):
        self.target_file = target_file
        self.source_backup = f"{target_file}.orig"
        self._prepare_sandbox()
        self.self_mod = SelfModEngine(source_file=target_file, backup_dir="sandbox_backups")

    def _prepare_sandbox(self):
        """Create a dummy agent file for the sandbox."""
        dummy_code = """
class SandboxAgent:
    def __init__(self):
        self.version = 1.0
        self.capabilities = ["basic_logic"]
    
    def process(self, data):
        return f"Processed {data} with version {self.version}"
"""
        with open(self.target_file, "w") as f:
            f.write(dummy_code.strip())
        shutil.copy2(self.target_file, self.source_backup)
        print(f"🛠️ Sandbox prepared: {self.target_file}")

    def run_evolution_cycle(self, iterations: int = 5):
        """Run multiple generations of self-evolution."""
        print(f"🚀 Starting Evolution Sandbox: {iterations} generations...")
        
        for i in range(iterations):
            print(f"\n--- Generation {i+1} ---")
            
            # 1. Analyze
            analysis = self.self_mod.analyze_source()
            print(f"  Analysis: {analysis.get('methods')} methods, {analysis.get('lines')} lines.")
            
            # 2. Propose & Apply Modification
            # Simulated: Adding a new specialized method in each generation
            method_name = f"evolve_capability_{i+1}"
            method_code = f"return 'Evolution level {i+1} reached.'"
            
            # --- FEATURE 6: Verify through Wasm Sandbox before applying ---
            print(f"  [SECURITY] Verifying {method_name} in Wasm Sandbox...")
            sandbox = WasmSandbox()
            
            # Creating a test execution script
            test_script = f"def {method_name}():\n    {method_code}\n\nprint({method_name}())"
            
            verify_result = sandbox.run_python_code(test_script)
            
            if not verify_result.get("success"):
                print(f"  [BLOCKED] Wasm Sandbox rejected the code: {verify_result.get('error')}")
                continue
                
            print(f"  [VERIFIED] Wasm Output: {verify_result.get('output').strip()}")

            result = self.self_mod.add_method(self, method_name, method_code, 
                                            description=f"Generated in Sandbox Gen {i+1}")
            
            if result.get("success"):
                print(f"  [SUCCESS] Evolved new capability: {method_name}")

        print("\n✨ Sandbox Evolution Complete.")
        self.self_mod.export_log("sandbox_evolution_log.json")

    def cleanup(self):
        """Restore the original sandbox state or delete it."""
        if os.path.exists(self.source_backup):
            shutil.copy2(self.source_backup, self.target_file)
        print("🧹 Sandbox cleanup completed.")

if __name__ == "__main__":
    sandbox = EvolutionSandbox()
    try:
        sandbox.run_evolution_cycle(3)
    finally:
        # sandbox.cleanup()
        pass
