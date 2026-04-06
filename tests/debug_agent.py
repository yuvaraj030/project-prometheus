
import sys
import os
import inspect

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ultimate_agent import UltimateAgent
    print(f"Imported UltimateAgent from: {sys.modules['ultimate_agent'].__file__}")
    
    print("Class definition:")
    print(UltimateAgent)
    
    print("\n__init__ signature:")
    print(inspect.signature(UltimateAgent.__init__))
    
    print("\nAttributes:")
    print(dir(UltimateAgent))
    
    if hasattr(UltimateAgent, 'speak'):
        print("\nSpeak method found:")
        print(inspect.getsource(UltimateAgent.speak))
    else:
        print("\nSpeak method NOT found in class directory.")
        
except Exception as e:
    print(f"Error: {e}")
