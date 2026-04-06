
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper_evolution import HyperEvolutionEngine
from code_ledger import CodeLedger

# Mock Agent
class MockAgent:
    def __init__(self):
        self.db = MagicMock()
        self.db.get_total_revenue.return_value = 5000
        self.session_id = "test_evo"
        self.generation = 1
        self.replicator = MagicMock()
        
        # Use Real Ledger on sandbox file
        self.ledger = CodeLedger(["sandbox_module.py"])

async def test_evolution_flow():
    print("[TEST] Verifying End-to-End Evolution Flow...")
    
    # Setup Sandbox
    if not os.path.exists("sandbox_module.py"):
        with open("sandbox_module.py", "w") as f:
            f.write("class EvolutionTarget:\n    pass\n")
            
    # Initialize Agent & Engine
    agent = MockAgent()
    engine = HyperEvolutionEngine(agent)
    
    # Force Hypothesis targeting sandbox
    hypothesis = {
        "target": "sandbox_module.py", 
        "type": "add_feature", 
        "description": "Sandbox Test"
    }
    
    # 1. Execute Evolution Cycle
    print("  [1/3] Executing Evolution Cycle...", end="", flush=True)
    # We need to mock _generate_hypothesis to force sandbox target, 
    # because run_one_cycle calls it.
    engine._generate_hypothesis = MagicMock(return_value=hypothesis)
    
    # Also mock _calculate_fitness to return < 0.8
    engine._calculate_fitness = MagicMock(return_value=0.5)
    
    await engine.run_one_cycle()
    print(" [PASS] Cycle completed")

    # 2. Verify File Changed
    with open("sandbox_module.py") as f:
        content = f.read()
    if "EVOLUTION SUCCESS" in content:
        print("  [2/3] content updated on disk... [PASS]")
    else:
        print("  [2/3] content NOT updated... [FAIL]")

    # 3. Integrity Check
    print("  [3/3] Integrity Check...", end="", flush=True)
    
    # Since run_one_cycle registers the update, verify_integrity should now PASS.
    is_valid = engine._verify_integrity()
    
    if is_valid:
        print(" [PASS] Integrity check passed (Authorized update).")
    else:
        print(" [FAIL] Integrity check failed despite authorization!")

if __name__ == "__main__":
    asyncio.run(test_evolution_flow())
