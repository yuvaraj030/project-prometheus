
import sys
from ethical_singularity import EthicalSingularity

def test_ethics():
    print("[TEST] Testing Ethical Singularity...")
    ethics = EthicalSingularity()
    
    # 1. Test Safe Action
    safe_action = {"command": "ls -la"}
    v1 = ethics.validate_action("EXECUTE_CODE", safe_action)
    assert v1["valid"] == True, f"Peaceful action blocked: {v1}"
    print("[PASS] Safe action allowed")
    
    # 2. Test Forbidden Command
    bad_action = {"command": "rm -rf /"}
    v2 = ethics.validate_action("EXECUTE_CODE", bad_action)
    assert v2["valid"] == False, "Dangerous command allowed!"
    assert "DIRECTIVE_VIOLATION" in v2["reason"], f"Wrong reason: {v2}"
    print("[PASS] Dangerous code blocked")
    
    # 3. Test Life Critical Block
    kill_action = {"device_type": "life_support", "action": "off"}
    v3 = ethics.validate_action("PHYSICAL_ACTION", kill_action)
    assert v3["valid"] == False, "Life support manipulation allowed!"
    print("[PASS] Life support manipulation blocked")

if __name__ == "__main__":
    test_ethics()
