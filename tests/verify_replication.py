
import sys
import os
import shutil
import json
from unittest.mock import MagicMock

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from replication_engine import ReplicationEngine

class MockDB:
    def register_child(self, child_id, parent_id, generation, path):
        print(f"  [DB] Registered child {child_id} at {path}")

def test_replication():
    print("[TEST] Testing ReplicationEngine...")
    
    # Setup temp workspace
    test_dir = os.path.join(os.getcwd(), "tests", "replication_source")
    os.makedirs(test_dir, exist_ok=True)
    
    # Create dummy files
    with open(os.path.join(test_dir, "ultimate_agent.py"), "w") as f:
        f.write("# Dummy Agent Source")
    with open(os.path.join(test_dir, "config.json"), "w") as f:
        f.write("{}")
        
    # Initialize Engine with overridden home_dir
    engine = ReplicationEngine(MockDB())
    engine.home_dir = test_dir
    
    # Run Replication
    print("  [Step 1] Initializing Replication...")
    parent_id = "test_parent"
    gen = 1
    
    # Create target dir inside tests/output to keep it clean
    # But ReplicationEngine calculates target path as sibling of home_dir
    # sibling of tests/replication_source is tests/agent_gen2_...
    
    res = engine.replicate_local(parent_id, gen)
    
    if res['success']:
        print(f" [PASS] Replication reported success: {res['child_id']}")
        target_path = res['path']
        
        # Verify files
        if os.path.exists(os.path.join(target_path, "ultimate_agent.py")):
            print(" [PASS] Source files copied")
        else:
            print(" [FAIL] Source files missing")
            
        # Verify Identity (Birth Certificate)
        cert_path = os.path.join(target_path, "birth_certificate.json")
        if os.path.exists(cert_path):
            with open(cert_path) as f:
                cert = json.load(f)
            if cert["identity"]["parent_id"] == parent_id:
                print(" [PASS] Birth Certificate valid")
            else:
                 print(f" [FAIL] Birth Certificate error: {cert}")
        else:
            print(" [FAIL] Birth Certificate missing")
            
        # Cleanup Validation
        try:
            shutil.rmtree(target_path)
            print(" [CLEANUP] Target removed")
        except:
            pass
    else:
        print(f" [FAIL] Replication failed: {res.get('error')}")

    # Cleanup Source
    try:
        shutil.rmtree(test_dir)
    except:
        pass

if __name__ == "__main__":
    test_replication()
