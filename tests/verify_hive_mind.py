
import sys
import os
import shutil
import sqlite3

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hive_mind import HiveMind, HIVE_DB_PATH

def test_hive_mind():
    print("[TEST] Testing HiveMind (Simulated Swarm)...")
    
    # Setup: Ensure clean DB or safe query
    # HIVE_DB_PATH is hardcoded in hive_mind.py as "hive_mind_central.db"
    # We should probably mock it or use a temp file, but the class doesn't accept a path arg easily unless we patch it.
    # The class FederatedAggregator uses global HIVE_DB_PATH.
    
    # We will patch the module variable
    import hive_mind
    test_db = "tests/test_hive.db"
    hive_mind.HIVE_DB_PATH = test_db
    
    # Initialize
    hive = HiveMind("test_agent_007")
    
    # 1. Share Fact
    print("  [1/3] Sharing Fact...", end="", flush=True)
    hive.share_fact("sky", "is", "blue")
    
    # Verify in DB directly
    try:
        conn = sqlite3.connect(test_db)
        cursor = conn.execute("SELECT * FROM global_facts WHERE subject='sky'")
        row = cursor.fetchone()
        if row:
            print(" [PASS]")
        else:
            print(" [FAIL] Fact not found in DB")
    except Exception as e:
        print(f" [FAIL] DB Error: {e}")
        
    # 2. Consult (Query)
    print("  [2/3] Consulting Hive...", end="", flush=True)
    results = hive.consult("sky")
    found = any(r['object'] == "blue" for r in results)
    
    if found:
         print(" [PASS]")
    else:
         print(f" [FAIL] Connect query failed. Results: {results}")

    # 3. Optimization
    print("  [3/3] Sharing Optimization...", end="", flush=True)
    hive.share_optimization("sorting", "quick_sort_v2", 0.95)
    best = hive.get_best_code("sorting")
    
    if best == "quick_sort_v2":
        print(" [PASS]")
    else:
        print(f" [FAIL] Got {best}")

    # Cleanup
    conn.close()
    if os.path.exists(test_db):
        os.remove(test_db)

if __name__ == "__main__":
    test_hive_mind()
