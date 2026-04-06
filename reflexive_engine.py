
"""
Reflexive Autonomy Engine — The ability to "think about how to do things".
Enables the agent to:
1. Identify knowledge gaps (Reflect)
2. Perform autonomous research (Research)
3. Build its own tools to solve problems (Tool Building)
"""

import os
import sys
import json
import time
import requests
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

class ReflexiveEngine:
    """
    The engine for higher-order autonomy.
    It doesn't just do tasks; it figures out HOW to do them.
    """

    def __init__(self, llm_provider, database=None):
        self.llm = llm_provider
        self.db = database
        self.tools_dir = os.path.join(os.getcwd(), "tools")
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
        
        # Load existing tools
        self.available_tools = self._scan_tools()

    def _scan_tools(self) -> List[str]:
        """Scan the tools directory for available Python scripts."""
        tools = []
        if os.path.exists(self.tools_dir):
            for f in os.listdir(self.tools_dir):
                if f.endswith(".py"):
                    tools.append(f)
        return tools

    # ==================================================
    #  REFLECTION (Meta-Analysis)
    # ==================================================
    def reflect(self, user_request: str) -> Dict[str, Any]:
        """
        Analyze a request to determine if we know how to do it.
        Returns a plan: "direct_action", "needs_research", or "needs_tool".
        """
        prompt = f"""
        You are a reflexive AI. Analyze this user request:
        "{user_request}"
        
        Do you know how to fulfill this request immediately with your core capabilities 
        (conversation, basic code execution, file reading)?
        
        Or do you need to:
        1. RESEARCH (search web for docs/info)?
        2. BUILD_TOOL (write a specialized Python script, e.g., a scraper, parser, or complex calculator)?
        
        Current custom tools available: {self.available_tools}
        
        Respond in JSON format:
        {{
            "analysis": "Brief thought process",
            "strategy": "DIRECT_ACTION" or "RESEARCH" or "BUILD_TOOL",
            "missing_knowledge": "What specific info is missing?" (optional),
            "tool_needed": "Description of tool needed" (optional)
        }}
        """
        response = self.llm.call(prompt, max_tokens=300, temperature=0.3)
        try:
            # Extract JSON from potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            return json.loads(response)
        except Exception:
            # Fallback if LLM fails JSON format
            return {"strategy": "DIRECT_ACTION", "analysis": "Could not parse robust plan."}

    # ==================================================
    #  RESEARCH (Autonomous Learning)
    # ==================================================
    def research(self, query: str) -> str:
        """
        Perform autonomous research on a query.
        For now, simulates a deep search or uses available search APIs.
        """
        print(f"  🔍 Reflexive Engine: Researching '{query}'...")
        
        # In a real "God-mode" setup, we'd use a SERP API (SerpApi, Google, etc.)
        # For this standalone version without extra keys, we'll try to use a free method
        # or guide the user.
        
        # Try a direct request to a search engine (limited success without API key, but worth a try for simple scraping)
        try:
            # Using DuckDuckGo HTML (no API key needed, but fragile)
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers, timeout=10)
            if resp.status_code == 200:
                # Naive text extraction
                from html.parser import HTMLParser
                class MLStripper(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.reset()
                        self.strict = False
                        self.convert_charrefs= True
                        self.text = []
                    def handle_data(self, d):
                        self.text.append(d)
                    def get_data(self):
                        return "".join(self.text)
                
                s = MLStripper()
                s.feed(resp.text)
                raw_text = s.get_data()
                
                # Clean up whitespace
                clean_text = " ".join(raw_text.split())
                snippet = clean_text[:2000] # Take first 2k chars
                
                # Summarize with LLM
                summary = self.llm.call(
                    f"Summarize this search result for query '{query}':\n\n{snippet}",
                    max_tokens=400
                )
                return f"Research Findings:\n{summary}"
        except Exception as e:
            return f"Research failed: {str(e)}"
        
        return "Could not perform automated research. Please use /search manually."

    # ==================================================
    #  TOOL BUILDING (Self-Extension)
    # ==================================================
    def build_tool(self, tool_name: str, description: str) -> str:
        """
        Write a Python script to verify and save it as a new capability.
        """
        print(f"  🛠️ Reflexive Engine: Building tool '{tool_name}'...")
        
        prompt = f"""
        Write a standalone Python script for a tool named '{tool_name}'.
        Description: {description}
        
        Requirements:
        1. Must be a complete, runnable script.
        2. Must use 'argparse' to accept arguments if needed.
        3. Must print the result to stdout.
        4. Standard library imports only if possible, or common ones (requests, json).
        5. OUTPUT CODE ONLY between ```python and ``` blocks.
        """
        
        response = self.llm.call(prompt, max_tokens=1500, temperature=0.2)
        
        # Extract code
        code = ""
        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
            
        if not code:
            return "Failed to generate tool code."
            
        # Verify syntax
        try:
            compile(code, tool_name, 'exec')
        except SyntaxError as e:
            return f"Generated code has syntax error: {e}"
            
        # Save tool
        filename = f"{tool_name.lower().replace(' ', '_')}.py"
        filepath = os.path.join(self.tools_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
            
        self.available_tools.append(filename)
        return f"Tool built successfully: {filename}\nUsage: Use 'python tools/{filename}' to run it."

    def execute_tool(self, tool_name: str, args: str) -> str:
        """Run a tool from the library."""
        tool_path = os.path.join(self.tools_dir, tool_name)
        if not os.path.exists(tool_path):
            return f"Tool '{tool_name}' not found."
            
        cmd = f"python {tool_path} {args}"
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return f"Tool Output:\n{r.stdout}"
            else:
                return f"Tool Error:\n{r.stderr}"
        except Exception as e:
            return f"Execution failed: {e}"
