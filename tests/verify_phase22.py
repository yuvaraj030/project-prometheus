"""
Verification Script for Phase 22 Features.
Checks Resource Manager and OAuth Engine integration.
"""

import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.abspath("."))

from ultimate_agent import UltimateAgent
from config import CONFIG
import asyncio

async def verify():
    import inspect
    print(f"[*] UltimateAgent file: {inspect.getfile(UltimateAgent)}")
    print(f"[*] Inspecting UltimateAgent.__init__ signature: {inspect.signature(UltimateAgent.__init__)}")
    print("[*] Initializing UltimateAgent in LITE_MODE...")
    agent = UltimateAgent(provider="ollama", enable_self_mod=False)
    
    # 1. Check Resource Manager
    print("[*] Testing Resource Manager...")
    agent.llm.resource_manager.log_usage("test_provider", "test_model", 100, 0.05)
    report = agent.resources.get_status_report()
    print(report)
    if "100" in report and "0.0500" in report:
        print("✅ Resource Manager logging verified.")
    else:
        print("❌ Resource Manager logging failed.")

    # 2. Check OAuth Engine
    print("[*] Testing OAuth Engine...")
    url = agent.oauth.get_auth_url("google")
    print(f"Auth URL: {url}")
    if "google" in url:
        print("✅ OAuth Engine URL generation verified.")
    else:
        print("❌ OAuth Engine URL generation failed.")
        
    # 3. Test Command Handler integration
    print("[*] Testing Command Handler routing...")
    # Wrap in try/except for CLI interactivity
    try:
        await agent.handle_command("/resources")
        print("✅ Command '/resources' executed.")
    except Exception as e:
        print(f"❌ Command '/resources' failed: {e}")

    print("\n[!] Phase 22 Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify())
