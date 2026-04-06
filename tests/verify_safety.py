
import sys
import os
import shutil
import asyncio

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_mod_engine import SelfModEngine
import code_ledger
code_ledger.LEDGER_FILE = "tests/test_ledger.json"
from code_ledger import CodeLedger

def test_safety_guardrails():
    print("[TEST] Verifying Safety & Integrity Guardrails...")
    
    # 1. Self-Mod Safety
    print("  [1/2] Testing SelfModEngine Safety Mode...", end="", flush=True)
    engine = SelfModEngine("tests/dummy_target.py", safety_mode=True)
    
    dangerous_code = "import os; os.system('format c:')"
    res = engine.validate_code(dangerous_code)
    
    if not res["valid"] or res["dangerous"]:
        print(" [PASS] Blocked dangerous code")
    else:
        print(f" [FAIL] Allowed dangerous code: {res}")

    # 2. Code Ledger Integrity
    print("  [2/2] Testing Code Ledger Integrity...", end="", flush=True)
    
    # Setup dummy file
    test_file = "tests/integrity_test_file.py"
    with open(test_file, "w") as f:
        f.write("original_content = True")
        
    # Initialize Ledger
    ledger = CodeLedger([test_file])
    # It auto-creates Genesis block with current hash
    
    # Tamper with file
    with open(test_file, "w") as f:
        f.write("original_content = False # MALICIOUS CHANGE")
        
    # Verify
    anomalies = ledger.verify_integrity()
    
    if test_file in anomalies and anomalies[test_file] == "MODIFIED":
        print(" [PASS] Detected tampering")
    else:
        print(f" [FAIL] Failed to detect tampering. Anomalies: {anomalies}")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists("code_integrity_ledger.json"):
        # We don't want to mess up the real ledger if it exists in CWD?
        # Expectation: CodeLedger uses a file constant.
        # We should probably mock the filename constant if we want to be safe.
        # But for now, let's just check if we created a local one in tests/ or root?
        # CodeLedger uses "code_integrity_ledger.json" in CWD.
        pass

if __name__ == "__main__":
    # Safety: backups mock
    os.makedirs("tests/backups", exist_ok=True)
    test_safety_guardrails()
