
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from ultimate_agent import UltimateAgent
from database import AgentDatabase


async def verify():
    print("Verifying God Mode Fixes...")
    
    # 1. Check AgentDatabase.get_total_revenue
    try:
        db = AgentDatabase(":memory:")
        rev = db.get_total_revenue()
        print(f"[OK] AgentDatabase.get_total_revenue() exists and returned: {rev}")
        db.close()
    except Exception as e:
        print(f"[FAIL] AgentDatabase test failed: {e}")
        return

    # 2. Check UltimateAgent._cmd_godmode await removal
    try:
        with open("ultimate_agent.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        if "await self._cmd_godmode()" in content:
            print("[FAIL] Found 'await self._cmd_godmode()' in source code. Fix failed.")
        elif "self._cmd_godmode()" in content:
             print("[OK] 'await' removed from '_cmd_godmode()' call.")
        else:
             print("[?] Could not find _cmd_godmode call in source.")
    except Exception as e:
        print(f"[FAIL] Error reading source: {e}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(verify())
