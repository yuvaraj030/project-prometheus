
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add parent dir to path (PRIORITIZE LOCAL OVER C:\AI)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies to avoid full startup
sys.modules['speech_recognition'] = MagicMock()
sys.modules['pyttsx3'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

import ultimate_agent
print(f"DEBUG: Imported ultimate_agent from: {ultimate_agent.__file__}")

from ultimate_agent import UltimateAgent

def test_startup_attributes():
    print("[TEST] Verifying UltimateAgent Startup Attributes...")
    
    # We need to mock args or just instantiate with defaults
    # The __init__ takes args, but it uses argparse. 
    # Actually UltimateAgent class doesn't take args in __init__, it parses them or uses them from outside?
    # Checking code... __init__ takes 'args' parameters? 
    # Let's check signature or just try.
    
    # Wait, ultimate_agent.py has a main() that parses args, but the class __init__ 
    # likely takes the parsed args or nothing.
    # Let's check the code content from previous view... 
    # It seems to take `args` in __init__? 
    # "self.self_mod = SelfModEngine(..., enabled=(not args.no_self_mod)...)"
    # Yes, it takes 'args'.
    
    import inspect
    print(f"inspect.signature: {inspect.signature(UltimateAgent.__init__)}")
    try:
        agent = UltimateAgent(
            provider="ollama",
            api_key="test_key",
            model="llama2",
            wake_word="test",
            enable_self_mod=False,
            safety_mode=True
        )
        print(" [PASS] Agent instantiated")
        
        attributes = [
            "wallet", "billing", "repair", "marketing", 
            "compressor", "monitor", "autonomous_repair"
        ]
        
        missing = []
        for attr in attributes:
            if hasattr(agent, attr):
                print(f"   [OK] {attr} exists")
            else:
                print(f"   [FAIL] {attr} MISSING")
                missing.append(attr)
                
        if not missing:
            print(" [PASS] All Sovereign Modules present")
        else:
            print(f" [FAIL] Missing modules: {missing}")
            
    except Exception as e:
        print(f" [FAIL] Manifestation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_startup_attributes()
