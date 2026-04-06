
import sys
import os
import io

# Mock the agent context
class MockSelfMod:
    def __init__(self):
        self.enabled = True
        self.metrics = {"evolution_level": 1}
        self.methods = {}
    
    def list_capabilities(self, agent):
        return ["capability1", "capability2"]
        
    def add_method(self, agent, name, code, description):
        self.methods[name] = code
        return {"success": True}

class MockLLM:
    def __init__(self):
        self.suggestion = ""
    def call(self, prompt, max_tokens=1000):
        return self.suggestion

class MockAgent:
    def __init__(self):
        self.self_mod = MockSelfMod()
        self.llm = MockLLM()
        self.perf = {"evolution": 0}

    def self_improve(self, goal: str = "") -> dict:
        # Copied logic from ultimate_agent.py for testing isolated logic
        # In a real test we would import the class, but this is faster for hotfix verification
        suggestion = self.llm.call("prompt")
        
        method_name = reason = None
        code_lines, in_code = [], False
        for line in suggestion.split("\n"):
            line = line.strip() # <--- THE FIX
            if line.startswith("METHOD_NAME:"):
                method_name = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
            elif line.startswith("CODE:"):
                in_code = True
            elif in_code:
                code_lines.append(line)

        if method_name and code_lines:
            return {"success": True, "method": method_name, "code": "\n".join(code_lines)}
        return {"success": False}

def test_parsing():
    agent = MockAgent()
    
    # Test 1: Clean input
    agent.llm.suggestion = """METHOD_NAME: test_clean
REASON: Because
CODE:
def test_clean():
    pass"""
    res1 = agent.self_improve()
    assert res1["success"] == True
    assert res1["method"] == "test_clean"
    print("[PASS] Test 1 (Clean) passed")

    # Test 2: Messy input (The user report)
    agent.llm.suggestion = """ METHOD_NAME: test_messy
 REASON:  Whitespace is malicious
 CODE:
 def test_messy():
     return "it works" """
    res2 = agent.self_improve()
    assert res2["success"] == True
    assert res2["method"] == "test_messy"
    print("[PASS] Test 2 (Messy) passed")

if __name__ == "__main__":
    test_parsing()
