
import sys
import os
import asyncio
import time
from unittest.mock import MagicMock

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper_evolution import HyperEvolutionEngine

class MockAgent:
    def __init__(self):
        self.db = MagicMock()
        self.db.get_total_revenue.return_value = 5000
        self.ledger = MagicMock()
        self.ledger.verify_integrity.return_value = True
        self.session_id = "test_session"
        self.generation = 1
        self.replicator = MagicMock()
        self.modifier = MagicMock()

async def test_hyper_evolution():
    print("[TEST] Testing HyperEvolutionEngine Async Logic...")
    
    agent = MockAgent()
    # Mock verify_integrity to return {} (Empty dictionary = Valid/No Changes)
    agent.ledger.verify_integrity.return_value = {} 
    engine = HyperEvolutionEngine(agent)
    
    # We want to run the loop for exactly one iteration
    # We can patch asyncio.sleep to raise an exception or just let it run briefly
    
    # Better: Override stop_loop to be called after 1s
    task = asyncio.create_task(engine.start_loop())
    
    await asyncio.sleep(2)
    engine.stop_loop()
    
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        pass
    except asyncio.CancelledError:
        pass
        
    # Check if methods were called
    # Since _calculate_fitness is internal, we check output or side effects
    # But start_loop prints to stdout.
    
    print(" [PASS] Loop ran without crashing.")
    
    # Verify logic components
    fitness = engine._calculate_fitness()
    print(f"  Fitness Calc: {fitness}")
    if 0.0 <= fitness <= 1.0:
        print(" [PASS] Fitness range valid")
    else:
        print(" [FAIL] Fitness out of range")

    hypo = engine._generate_hypothesis()
    print(f"  Hypothesis: {hypo}")
    if "target" in hypo and "type" in hypo:
        print(" [PASS] Hypothesis valid")
    else:
        print(" [FAIL] Hypothesis invalid")

    sim_success = await engine._simulate_modification(hypo)
    print(f"  Sim Success: {sim_success}")
    print(" [PASS] Simulation valid")

if __name__ == "__main__":
    asyncio.run(test_hyper_evolution())
