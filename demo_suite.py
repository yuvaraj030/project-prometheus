"""
Launch Demo Suite — Scripted scenarios for sales demos.
Part of Phase 15: Startup Launch.
"""

import time
import sys
import logging

class DemoSuite:
    def __init__(self):
        self.logger = logging.getLogger("DemoSuite")
        logging.basicConfig(level=logging.INFO)

    def run_demo(self, mode: str):
        print(f"\n🎬 STARTING DEMO SCENARIO: {mode.upper()}")
        print("========================================")
        
        if mode == "support":
            self._demo_support_bot()
        elif mode == "research":
            self._demo_research_agent()
        elif mode == "coding":
            self._demo_coding_companion()
        else:
            print(f"Unknown mode: {mode}")

    def _typewriter(self, text: str, speed: float = 0.03):
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(speed)
        print("")

    def _demo_support_bot(self):
        """Scenario: Handling a frustrated customer request."""
        self._typewriter("USER: I can't log in to my account! It says error 503.")
        time.sleep(1)
        print("\n🤖 AGENT (Thinking): Analyzing error 503... Checking server status... Known incident #992.")
        time.sleep(1.5)
        self._typewriter("\n🤖 AGENT: I apologize for the trouble. Error 503 indicates a temporary maintenance outage on our auth server.\n"
                         "Good news: It is scheduled to be resolved in 15 minutes. I have subscribed you to the status update notification.\n"
                         "Is there anything else I can help with while you wait?")

    def _demo_research_agent(self):
        """Scenario: Deep research on a complex topic."""
        self._typewriter("USER: Research the impact of quantum computing on modern cryptography.")
        time.sleep(1)
        print("\n🤖 AGENT (Thinking): Identifying key encryption schemes (RSA, ECC)... Checking Shor's Algorithm...")
        time.sleep(1)
        print("🤖 AGENT (Tool): Searching Arxiv for 'post-quantum cryptography'...")
        time.sleep(1.5)
        print("🤖 AGENT (Tool): Reading 'NIST Post-Quantum Standardization Process'...")
        time.sleep(1.5)
        self._typewriter("\n🤖 AGENT: **Executive Summary**:\n"
                         "1. **Threat**: Shor's algorithm can factor large integers, breaking RSA/ECC.\n"
                         "2. **Timeline**: Experts predict cryptographically relevant quantum computers by 2030-2035.\n"
                         "3. **Solution**: NIST has standardized Lattice-based cryptography (Kyber, Dilithium) as replacements.\n"
                         "Recommendation: Begin migrating critical infrastructure to hybrid schemes (Classical + PQ) immediately.")

    def _demo_coding_companion(self):
        """Scenario: Refactoring legacy code."""
        self._typewriter("USER: Refactor this Python function to use list comprehensions.")
        print("\n📄 CODE:\n"
              "res = []\n"
              "for i in range(10):\n"
              "  if i % 2 == 0:\n"
              "    res.append(i * i)")
        time.sleep(1)
        print("\n🤖 AGENT (Thinking): Analyzing loop structure... Identifying pattern (filter + map)...")
        time.sleep(1.5)
        self._typewriter("\n🤖 AGENT: Here is the optimized version:\n"
                         "```python\n"
                         "res = [i * i for i in range(10) if i % 2 == 0]\n"
                         "```\n"
                         "This reduces the line count and improves readability.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["support", "research", "coding"])
    args = parser.parse_args()
    
    demo = DemoSuite()
    demo.run_demo(args.mode)
