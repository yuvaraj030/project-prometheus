
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from ultimate_agent import UltimateAgent
import inspect

print(f"DEBUG: UltimateAgent file: {inspect.getfile(UltimateAgent)}")
print(f"DEBUG: UltimateAgent.__init__ signature: {inspect.signature(UltimateAgent.__init__)}")

try:
    a = UltimateAgent(provider="ollama")
    print("DEBUG: Successfully initialized!")
except TypeError as e:
    print(f"DEBUG: TypeError: {e}")
except Exception as e:
    print(f"DEBUG: Exception: {e}")
