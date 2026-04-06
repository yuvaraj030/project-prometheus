"""
ReAct Engine — Reason + Act loop for tool-assisted thinking.
Upgraded with Verification, Confidence Gating, and Self-Correction.

Flow:
  1. Build system prompt with tool descriptions + AGI instructions
  2. Send user query to LLM
  3. If LLM responds with TOOL_CALL JSON → execute → verify result → feed back
  4. If FINAL_ANSWER → confidence gate before accepting
  5. Repeat with targeted self-correction until confident or max iterations
"""

import json
import re
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ReactEngine")

# Regex to locate the start of a tool call — full JSON extracted by brace-balancer
TOOL_CALL_PREFIX = re.compile(r'TOOL_CALL:\s*', re.DOTALL)


def _extract_balanced_json(text: str, start: int) -> str:
    """
    Extract a brace-balanced JSON object starting at `start` in `text`.
    This correctly handles nested objects like {"params": {"key": "value"}}.
    Returns the JSON string or '' if not found.
    """
    depth = 0
    i = start
    while i < len(text) and text[i] != '{':
        i += 1
    if i >= len(text):
        return ''
    json_start = i
    in_string = False
    escape_next = False
    while i < len(text):
        ch = text[i]
        if escape_next:
            escape_next = False
        elif ch == '\\':
            escape_next = True
        elif ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[json_start:i + 1]
        i += 1
    return ''

FINAL_ANSWER_PATTERN = re.compile(
    r'FINAL_ANSWER:\s*(.*)',
    re.DOTALL
)


class ReactEngine:
    """
    ReAct (Reason → Act → Observe → Verify → Repeat) engine.
    Integrates with LLMProvider, ToolRegistry, and VerificationEngine.
    """

    def __init__(self, llm_provider, tool_registry, max_iterations: int = 10,
                 verification_engine=None):
        self.llm = llm_provider
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self._trace: List[Dict] = []  # Execution trace for debugging
        self._verifier = verification_engine
        if self._verifier is None:
            try:
                from verification_engine import VerificationEngine
                self._verifier = VerificationEngine(llm_provider=self.llm)
                logger.info("VerificationEngine auto-loaded in ReactEngine.")
            except ImportError:
                self._verifier = None

    @staticmethod
    def _clean_response(text: str) -> str:
        """Strip any leaked TOOL_CALL / FINAL_ANSWER protocol text from a response."""
        if not text:
            return text
        cleaned = TOOL_CALL_PREFIX.sub('', text)
        cleaned = FINAL_ANSWER_PATTERN.sub('', cleaned)
        # Also strip bare JSON tool objects
        cleaned = re.sub(r'\{"name":\s*"[^"]*",\s*"params":\s*\{[^}]*\}\}', '', cleaned)
        return cleaned.strip()

    def build_system_prompt(self, base_system: str = "") -> str:
        """Build the system prompt with tool descriptions and ReAct instructions."""
        tools_prompt = self.tools.get_tools_prompt()

        react_instructions = """
TOOL USE INSTRUCTIONS:
You have access to the tools listed below. To use a tool, output EXACTLY this format on its own line:

TOOL_CALL: {"name": "tool_name", "params": {"param1": "value1"}}

After using a tool, you'll see the result prefixed with TOOL_RESULT.
You can chain multiple tool calls across iterations.

When you have enough information to answer, output:

FINAL_ANSWER: <your complete answer here>

RULES:
1. THINK step-by-step before using tools.
2. Only call ONE tool per response.
3. Always end with FINAL_ANSWER when you have the answer.
4. If a tool fails, try an alternative approach.
5. Keep your reasoning concise.
"""
        parts = []
        if base_system:
            parts.append(base_system)
        if tools_prompt:
            parts.append(f"\n# Available Tools\n{tools_prompt}")
        parts.append(react_instructions)
        return "\n".join(parts)

    def run(self, user_query: str, system: str = "",
            history: List[Dict] = None, tenant_id: int = 1,
            min_confidence: float = 0.65) -> str:
        """
        Run the full AGI ReAct loop with verification and confidence gating.
        Returns the final answer string.
        """
        start_time = time.time()
        self._trace = []
        consecutive_failures = 0

        full_system = self.build_system_prompt(system)
        conversation = list(history or [])

        # Initial user message
        current_prompt = f"User: {user_query}"

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"ReAct iteration {iteration}/{self.max_iterations}")

            # Call LLM
            response = self.llm.call(
                current_prompt,
                system=full_system,
                history=conversation,
                max_tokens=2000,
            )

            if not response:
                consecutive_failures += 1
                logger.warning(f"LLM returned empty response (failure #{consecutive_failures})")
                if consecutive_failures >= 2:
                    return "I couldn't process that request after multiple attempts. Please try again."
                # Inject a nudge
                conversation.append({"role": "user", "content": "Please continue and provide your answer."})
                current_prompt = "Please continue."
                continue

            consecutive_failures = 0

            self._trace.append({
                "iteration": iteration,
                "prompt": current_prompt[:200],
                "response": response[:500],
            })

            # ── Check for FINAL_ANSWER with confidence gate ─────────────
            final_match = FINAL_ANSWER_PATTERN.search(response)
            if final_match:
                answer = final_match.group(1).strip()
                elapsed = time.time() - start_time

                # Run confidence gate if verifier is available
                if self._verifier:
                    passed, conf = self._verifier.confidence_gate(response, min_confidence)
                    if not passed and iteration < self.max_iterations - 1:
                        logger.info(f"Confidence gate failed (conf={conf:.2f}). Forcing deeper research.")
                        conversation.append({"role": "assistant", "content": response})
                        conversation.append({
                            "role": "user",
                            "content": (
                                f"Your answer has low confidence ({conf:.0%}). "
                                f"Use a tool to verify your key claims, then provide a FINAL_ANSWER "
                                f"with CONFIDENCE above {min_confidence:.0%}."
                            )
                        })
                        current_prompt = conversation[-1]["content"]
                        continue

                logger.info(f"ReAct completed in {iteration} iterations ({elapsed:.1f}s)")
                # Strip the CONFIDENCE line from the user-facing answer
                clean_answer = re.sub(r'\nCONFIDENCE:\s*[0-9.]+\s*$', '', answer, flags=re.IGNORECASE).strip()
                return clean_answer if clean_answer else answer

            # ── Check for TOOL_CALL ──────────────────────────────────────
            prefix_match = TOOL_CALL_PREFIX.search(response)
            if prefix_match:
                json_str = _extract_balanced_json(response, prefix_match.end())
                try:
                    if not json_str:
                        raise json.JSONDecodeError("No balanced JSON found", "", 0)
                    tool_call = json.loads(json_str)
                    tool_name = tool_call.get("name", "")
                    tool_params = tool_call.get("params", {})

                    logger.info(f"Executing tool: {tool_name}({tool_params})")

                    # Execute the tool
                    result = self.tools.execute(tool_name, tool_params)

                    # ── Verify the tool result ──────────────────────────
                    verification_note = ""
                    if self._verifier:
                        intent = f"Answering: {user_query}"  # What we're ultimately trying to do
                        vr = self._verifier.verify_tool_result(tool_name, tool_params, result, intent)
                        if not vr.passed:
                            logger.warning(f"Tool result verification failed: {vr.reason}")
                            correction = self._verifier.generate_correction(
                                f"{tool_name} with {tool_params}", vr.reason, vr.retry_hint
                            )
                            verification_note = (
                                f"\n\n⚠️ VERIFICATION FAILED: {vr.reason}"
                                f"\n{correction}"
                                f"\nDo NOT repeat this exact tool call. Try a different approach."
                            )

                    self._trace[-1]["tool_call"] = {
                        "name": tool_name,
                        "params": tool_params,
                        "result": str(result)[:500],
                        "verified": not verification_note,
                    }

                    # Build next prompt with tool result
                    result_str = json.dumps(result, indent=2, default=str)
                    if len(result_str) > 3000:
                        result_str = result_str[:3000] + "\n... (truncated)"

                    # Add reasoning + tool call to history
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({
                        "role": "user",
                        "content": (
                            f"TOOL_RESULT ({tool_name}):\n{result_str}"
                            f"{verification_note}"
                            f"\n\nContinue reasoning. Use another tool or provide FINAL_ANSWER with CONFIDENCE."
                        )
                    })
                    current_prompt = conversation[-1]["content"]

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool call JSON: {e}")
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({
                        "role": "user",
                        "content": (
                            f"Error: Your TOOL_CALL JSON was malformed (parse error: {e}). "
                            f"Please try again.\n"
                            f"Correct format: TOOL_CALL: {{\"name\": \"tool_name\", \"params\": {{\"key\": \"value\"}}}}"
                        )
                    })
                    current_prompt = conversation[-1]["content"]
            else:
                # No tool call and no FINAL_ANSWER
                # Nudge the LLM to finish properly
                if iteration < self.max_iterations - 1:
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({
                        "role": "user",
                        "content": (
                            "Please finalize: if you have enough information, output "
                            "FINAL_ANSWER followed by CONFIDENCE. "
                            "If you need more information, use a TOOL_CALL."
                        )
                    })
                    current_prompt = conversation[-1]["content"]
                else:
                    elapsed = time.time() - start_time
                    logger.info(f"ReAct: LLM gave direct answer at iteration {iteration} ({elapsed:.1f}s)")
                    cleaned = self._clean_response(response)
                    return cleaned if cleaned else "I couldn't process that request. Please try again."

        # Max iterations reached
        logger.warning(f"ReAct hit max iterations ({self.max_iterations})")
        if self._trace:
            last = self._trace[-1].get("response", "")
            cleaned = self._clean_response(last)
            return cleaned if cleaned else "I ran out of thinking steps. Please try a simpler request."
        return "Could not complete the task within the iteration limit."

    def get_trace(self) -> List[Dict]:
        """Return the execution trace for debugging."""
        return self._trace

    def run_single(self, user_query: str, system: str = "") -> str:
        """
        Run a single-shot LLM call WITHOUT the ReAct loop.
        For simple queries that don't need tools.
        """
        response = self.llm.call(user_query, system=system, max_tokens=2000)
        return response if response else "..."


# --- Quick test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Mock LLM for testing
    class MockLLM:
        def __init__(self):
            self.call_count = 0
            self.provider = "mock"

        def call(self, prompt, system="", history=None, max_tokens=2000, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                return 'Let me check the time.\nTOOL_CALL: {"name": "get_time", "params": {}}'
            else:
                return "FINAL_ANSWER: The current time has been retrieved successfully."

    from tool_registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_builtins()

    engine = ReactEngine(MockLLM(), registry, max_iterations=5)
    result = engine.run("What time is it?")
    print(f"Result: {result}")
    print(f"\nTrace ({len(engine.get_trace())} steps):")
    for step in engine.get_trace():
        print(f"  Step {step['iteration']}: {step['response'][:80]}...")
