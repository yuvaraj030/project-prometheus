
import sys
import os
import asyncio
import time

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_mod_engine import SelfModEngine

class DummyTarget:
    def hello(self):
        return "original"

async def test_self_mod():
    print("[TEST] Testing SelfModEngine Async Compatibility...")
    
    # Setup
    engine = SelfModEngine("tests/dummy_target.py", backup_dir="tests/backups")
    target = DummyTarget()
    
    # 1. Analyze Source (Synchronous but wrapped)
    print("  [1/3] Testing Analysis...", end="", flush=True)
    start = time.time()
    # We simulate how the agent calls it: via to_thread
    metrics = await asyncio.to_thread(engine.analyze_source)
    duration = time.time() - start
    
    if "error" not in metrics:
        print(f" [PASS] ({duration:.4f}s)")
    else:
        print(f" [FAIL]: {metrics.get('error')}")

    # 2. Dynamic Method Injection
    print("  [2/3] Testing Dynamic Injection...", end="", flush=True)
    new_code = "def hello(self): return 'evolved'"
    
    # The dummy file needs to exist for this to work
    if not os.path.exists("tests/dummy_target.py"):
         with open("tests/dummy_target.py", "w") as f:
            f.write("class DummyTarget:\n    def hello(self):\n        return 'original'\n")

    print(f"    Current hello: {target.hello()}")
    res = await asyncio.to_thread(engine.add_method, target, "hello", new_code)
    
    print(f"    New hello: {target.hello()}")
    print(f"    Is bound? {hasattr(target.hello, '__self__')}")
    
    if res.get("success") and target.hello() == "evolved":
        print(f" [PASS]")
    else:
        print(f" [FAIL]: {res}")

    # 3. Safety Check
    print("  [3/3] Testing Safety Guardrails...", end="", flush=True)
    unsafe_code = "import os; os.system('echo hacked')"
    res = await asyncio.to_thread(engine.validate_code, unsafe_code)
    
    if not res["valid"] or (engine.safety_mode and res["dangerous"]):
        print(f" [PASS] (Blocked)")
    else:
        print(f" [FAIL] (Allowed unsafe code)")

if __name__ == "__main__":
    # Create dummy file for analysis
    os.makedirs("tests", exist_ok=True)
    with open("tests/dummy_target.py", "w") as f:
        f.write("class DummyTarget:\n    def hello(self):\n        return 'original'\n")
        
    asyncio.run(test_self_mod())
    
    # Cleanup
    try:
        os.remove("tests/dummy_target.py")
        import shutil
        shutil.rmtree("tests/backups")
    except:
        pass
