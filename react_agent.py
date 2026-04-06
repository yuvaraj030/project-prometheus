"""
ReAct Agent — Real Reason → Act → Observe loop.
================================================
This is the core of "real" agentic behavior:
  1. REASON: LLM decides what to do next
  2. ACT:    Call a real tool (web search, code exec, file write…)
  3. OBSERVE: Feed the actual tool output back to the LLM
  4. Repeat until DONE or step limit reached

Usage:
    from react_agent import ReactAgent
    agent = ReactAgent(llm_provider, tool_registry)
    result = agent.run("Research AI trends and write a summary to ai_trends.md")
"""

import re
import json
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger("ReactAgent")

# ─── Prompt Templates ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a real autonomous AI agent. Complete goals EFFICIENTLY — do NOT over-search.

## Available Tools
{tools_prompt}

## How to Respond
Each turn, choose ONE of:

A) Use a tool:
   THOUGHT: <why you need this tool>
   ACTION: <tool_name>
   PARAMS: {{"key": "value"}}

B) Finish (USE THIS AS SOON AS YOU HAVE USEFUL INFORMATION):
   THOUGHT: <summary of what was accomplished>
   DONE: <one-line result>

## CRITICAL RULES
- After a SUCCESSFUL web_search that returns ANY results → call DONE immediately
- Do NOT search more than 2 times for the same goal
- Do NOT say "I searched" without actually calling web_search
- If web_search returns results, those ARE your findings — summarize and call DONE
- If a tool fails twice, call DONE with what you have
- Maximum {max_steps} steps, then stop
- When in doubt → call DONE with partial results

## Example of CORRECT behaviour
Step 1: ACTION: web_search → gets results → 
Step 2: DONE: Found 3 articles about X: [brief summary]   ← STOP HERE
"""

STEP_PROMPT = """\
## Goal
{goal}

## Steps completed so far ({step}/{max_steps})
{history}

## Last Observation
{last_observation}

{stop_hint}
What do you do next? (THOUGHT + ACTION/DONE)
"""

# ─── ReAct Engine ─────────────────────────────────────────────────────────────

class ReactAgent:
    """
    Reason–Act–Observe agent loop wired to real tools.

    Args:
        llm_provider:  instance of LLMProvider
        tool_registry: instance of ToolRegistry (with tools registered)
        max_steps:     max iterations before giving up (default 8)
        verbose:       print step-by-step progress (default True)
    """

    def __init__(self, llm_provider, tool_registry, max_steps: int = 12,
                 verbose: bool = True):
        self.llm = llm_provider
        self.tools = tool_registry
        self.max_steps = max_steps
        self.verbose = verbose

    # ── Public API ──────────────────────────────────────────────────────────

    def run(self, goal: str, context: str = "") -> Dict[str, Any]:
        """
        Execute a goal using the ReAct loop.

        Returns:
            {
                "success": bool,
                "result":  str,          # final DONE text or last meaningful output
                "steps":   int,          # number of steps taken
                "transcript": [...]      # full step-by-step log
            }
        """
        self._log(f"[GOAL] {goal}")
        start_time = time.time()

        tools_prompt = self.tools.get_tools_prompt()
        system = SYSTEM_PROMPT.format(
            tools_prompt=tools_prompt,
            max_steps=self.max_steps,
        )

        history: List[str] = []
        last_observation = context or "(No prior context. Use tools to gather information.)"
        transcript: List[Dict] = []
        last_was_success = False
        no_action_streak = 0

        for step in range(1, self.max_steps + 1):
            self._log(f"\n--- Step {step}/{self.max_steps} ---")

            # Build stop hint — injected when last tool succeeded
            if last_was_success:
                stop_hint = (
                    "⚠️ IMPORTANT: The last tool call SUCCEEDED. "
                    "You now have the information needed. "
                    "Call DONE immediately with a summary of what you found. "
                    "Do NOT call another tool."
                )
            elif step >= self.max_steps - 2:
                stop_hint = (
                    f"⚠️ Only {self.max_steps - step + 1} step(s) left. "
                    "You MUST call DONE now with whatever you have."
                )
            else:
                stop_hint = ""

            # Build the per-step user prompt
            history_str = "\n".join(history) if history else "(none yet)"
            user_prompt = STEP_PROMPT.format(
                goal=goal,
                step=step,
                max_steps=self.max_steps,
                history=history_str,
                last_observation=last_observation,
                stop_hint=stop_hint,
            )

            # ── REASON ──────────────────────────────────────────────────
            raw_response = self.llm.call(user_prompt, system=system,
                                         max_tokens=1200, temperature=0.3)
            if not raw_response:
                self._log("LLM returned empty response. Stopping.")
                break

            self._log(f"LLM:\n{raw_response[:600]}")

            # ── Parse response ───────────────────────────────────────────
            thought, action, params, done_text = self._parse_response(raw_response)

            step_record = {
                "step": step,
                "thought": thought,
                "action": action,
                "params": params,
                "done": done_text,
                "observation": None,
                "timestamp": datetime.now().isoformat(),
            }

            # ── DONE? ─────────────────────────────────────────────────────
            if done_text:
                self._log(f"[DONE] {done_text}")
                step_record["observation"] = done_text
                transcript.append(step_record)
                elapsed = round(time.time() - start_time, 1)
                return {
                    "success": True,
                    "result": done_text,
                    "steps": step,
                    "elapsed_s": elapsed,
                    "transcript": transcript,
                }

            # ── ACT ───────────────────────────────────────────────────────
            if action:
                observation = self._execute_tool(action, params)
                self._log(f"[TOOL] [{action}] observation:\n{str(observation)[:400]}")
                obs_str = self._format_observation(action, observation)
                # Track whether last tool succeeded — used to inject STOP hint
                last_was_success = observation.get("success", False)
                no_action_streak = 0
            else:
                # LLM gave a thought but no clear action — treat full response as observation
                obs_str = f"[No tool called] LLM said: {raw_response[:300]}"
                observation = {"success": False, "error": "No ACTION found in response"}
                self._log("[WARN] No ACTION found. Treating as observation and continuing.")
                last_was_success = False
                no_action_streak += 1
                # Auto-finish if stuck with no action twice in a row
                if no_action_streak >= 2:
                    self._log("[WARN] No action for 2 consecutive steps — auto-finishing.")
                    return {
                        "success": True,
                        "result": f"Completed with available context: {raw_response[:300]}",
                        "steps": step,
                        "elapsed_s": round(time.time() - start_time, 1),
                        "transcript": transcript,
                    }

            step_record["observation"] = obs_str
            transcript.append(step_record)

            history.append(
                f"Step {step}: {thought or '(thinking)'} → {action or 'no action'}"
                f"\n  Result: {obs_str[:200]}"
            )
            last_observation = obs_str

        # ── Step limit reached ────────────────────────────────────────────
        elapsed = round(time.time() - start_time, 1)
        last_useful = history[-1] if history else "No steps completed"
        self._log(f"[WARN] Step limit ({self.max_steps}) reached.")
        return {
            "success": False,
            "result": f"Step limit reached. Last action: {last_useful}",
            "steps": self.max_steps,
            "elapsed_s": elapsed,
            "transcript": transcript,
        }

    # ── Parsing ──────────────────────────────────────────────────────────────

    def _parse_response(self, text: str):
        """Extract THOUGHT, ACTION, PARAMS, and DONE from LLM response."""
        thought = ""
        action = ""
        params = {}
        done_text = ""

        # THOUGHT
        m = re.search(r"THOUGHT\s*:\s*(.+?)(?=ACTION|PARAMS|DONE|$)", text,
                      re.IGNORECASE | re.DOTALL)
        if m:
            thought = m.group(1).strip()[:300]

        # DONE
        m = re.search(r"DONE\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        if m:
            done_text = m.group(1).strip()[:500]
            return thought, "", {}, done_text

        # ACTION
        m = re.search(r"ACTION\s*:\s*(\w+)", text, re.IGNORECASE)
        if m:
            action = m.group(1).strip().lower()

        # PARAMS
        m = re.search(r"PARAMS\s*:\s*(\{.*?\})", text,
                      re.IGNORECASE | re.DOTALL)
        if m:
            try:
                params = json.loads(m.group(1))
            except json.JSONDecodeError:
                # Try to rescue partial JSON
                raw = m.group(1)
                params = self._fuzzy_parse_params(raw)

        return thought, action, params, done_text

    def _fuzzy_parse_params(self, raw: str) -> dict:
        """Try to extract key-value pairs from malformed JSON."""
        result = {}
        # Match "key": "value" or "key": value patterns
        for match in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', raw):
            result[match.group(1)] = match.group(2)
        for match in re.finditer(r'"(\w+)"\s*:\s*(\d+)', raw):
            result[match.group(1)] = int(match.group(2))
        return result

    # ── Tool Execution ───────────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, params: dict) -> dict:
        """Execute a tool from the registry and return the raw result dict."""
        # Normalize tool name aliases
        aliases = {
            "search": "web_search",
            "websearch": "web_search",
            "google": "web_search",
            "write": "write_file",
            "read": "read_file",
            "shell": "run_shell",
            "bash": "run_shell",
            "code": "run_code",
            "exec": "run_code",
            "python": "run_code",
            "ls": "list_files",
            "dir": "list_files",
            "time": "get_time",
        }
        normalized = aliases.get(tool_name, tool_name)

        if not self.tools.get(normalized):
            available = [t["name"] for t in self.tools.list_tools()]
            return {
                "success": False,
                "error": f"Unknown tool '{tool_name}'. Available: {available}",
            }

        return self.tools.execute(normalized, params)

    def _format_observation(self, tool_name: str, result: dict) -> str:
        """Convert a tool result dict into a human-readable observation string."""
        if not result.get("success"):
            return f"[ERROR] Tool '{tool_name}' failed: {result.get('error', 'unknown error')}"

        # Tool-specific formatting
        if tool_name == "web_search":
            items = result.get("results", [])
            if not items:
                return "[web_search] No results found."
            lines = [f"[web_search] Found {len(items)} result(s):"]
            for i, r in enumerate(items[:5], 1):
                title = r.get("title", "")
                snippet = r.get("snippet", r.get("body", ""))[:200]
                url = r.get("url", r.get("href", ""))
                lines.append(f"  {i}. {title}\n     {snippet}\n     URL: {url}")
            return "\n".join(lines)

        elif tool_name == "write_file":
            return (f"[write_file] Wrote {result.get('bytes_written', 0)} bytes "
                    f"to '{result.get('path', '?')}'")

        elif tool_name == "read_file":
            content = result.get("content", "")[:1000]
            return f"[read_file] Content ({result.get('size', 0)} bytes):\n{content}"

        elif tool_name == "run_shell":
            stdout = result.get("stdout", "").strip()[:800]
            stderr = result.get("stderr", "").strip()[:200]
            rc = result.get("return_code", 0)
            out = f"[run_shell] Return code: {rc}\n"
            if stdout:
                out += f"STDOUT:\n{stdout}\n"
            if stderr:
                out += f"STDERR:\n{stderr}"
            return out.strip()

        elif tool_name == "run_code":
            output = result.get("output", "").strip()[:800]
            error = result.get("error", "").strip()[:200]
            out = f"[run_code] Output:\n{output}"
            if error:
                out += f"\nError:\n{error}"
            return out.strip()

        elif tool_name == "list_files":
            entries = result.get("entries", [])
            lines = [f"[list_files] {result.get('count', 0)} entries:"]
            for e in entries[:20]:
                kind = "📁" if e.get("is_dir") else "📄"
                lines.append(f"  {kind} {e['name']}")
            return "\n".join(lines)

        elif tool_name == "get_time":
            return f"[get_time] {result.get('time', '?')}"

        else:
            # Generic: dump result as JSON
            return f"[{tool_name}] {json.dumps(result, default=str)[:500]}"

    # ── Logging ──────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        if self.verbose:
            try:
                print(f"[ReAct] {msg}")
            except UnicodeEncodeError:
                # Fallback for Windows cp1252 consoles — strip non-ASCII
                safe = msg.encode("ascii", errors="replace").decode("ascii")
                print(f"[ReAct] {safe}")
        logger.info(msg)


# ─── Quick self-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.WARNING)

    # Bootstrap minimal environment
    sys.path.insert(0, os.path.dirname(__file__))
    from tool_registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_builtins()

    class MockLLM:
        """Fake LLM for testing without an API key."""
        call_count = 0

        def call(self, prompt, system="", max_tokens=1000, temperature=0.7, **kw):
            self.call_count += 1
            if self.call_count == 1:
                return (
                    "THOUGHT: I need to get the current time first.\n"
                    "ACTION: get_time\n"
                    "PARAMS: {}\n"
                )
            elif self.call_count == 2:
                return (
                    "THOUGHT: I have the time. Now write a greeting file.\n"
                    "ACTION: write_file\n"
                    'PARAMS: {"path": "hello_test.txt", "content": "Hello from ReAct!\\n"}\n'
                )
            else:
                return (
                    "THOUGHT: File was written successfully.\n"
                    "DONE: Created hello_test.txt with a greeting.\n"
                )

    llm = MockLLM()
    agent = ReactAgent(llm, registry, max_steps=6, verbose=True)

    print("=" * 60)
    print("ReAct Agent Self-Test")
    print("=" * 60)
    result = agent.run("Get the current time and write a greeting file.")
    print("\n" + "=" * 60)
    print(f"Success: {result['success']}")
    print(f"Result: {result['result']}")
    print(f"Steps: {result['steps']}")
    print(f"Elapsed: {result['elapsed_s']}s")

    # Cleanup
    if os.path.exists("hello_test.txt"):
        os.remove("hello_test.txt")
        print("Cleaned up hello_test.txt")
