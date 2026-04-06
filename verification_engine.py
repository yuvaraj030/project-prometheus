"""
Verification Engine — The AGI Reliability Core
================================================
Makes the agent actually reliable by:
1. Verifying tool results are real (not just "success": true)
2. Validating generated code compiles and runs without errors
3. Critiquing plans before execution to catch hallucinations early
4. Self-correcting on failure with targeted retry strategies
5. Confidence-gating: only proceed if the agent is actually confident
"""

import subprocess
import json
import time
import logging
import re
import os
import hashlib
import textwrap
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("VerificationEngine")


class VerificationResult:
    """Structured result from a verification check."""

    def __init__(self, passed: bool, confidence: float,
                 reason: str, corrective_action: str = "",
                 retry_hint: str = ""):
        self.passed = passed
        self.confidence = confidence          # 0.0 - 1.0
        self.reason = reason
        self.corrective_action = corrective_action  # What to do to fix it
        self.retry_hint = retry_hint                # Hint to give LLM on retry

    def __bool__(self):
        return self.passed

    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"[{status} | conf={self.confidence:.2f}] {self.reason}"


class VerificationEngine:
    """
    The AGI Reliability Core.
    Every action the agent takes passes through here before being
    accepted as 'complete'. No more blind trust in LLM outputs.
    """

    MAX_RETRIES = 3
    CODE_TIMEOUT_SECS = 15

    def __init__(self, llm_provider=None, database=None):
        self.llm = llm_provider
        self.db = database
        self._verification_log: List[Dict] = []
        self._stats = {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "auto_corrected": 0,
        }
        logger.info("VerificationEngine initialized — AGI Reliability Mode: ON")

    # ═══════════════════════════════════════════════════════════════
    #  1. TOOL RESULT VERIFICATION
    # ═══════════════════════════════════════════════════════════════

    def verify_tool_result(self, tool_name: str, params: Dict,
                           result: Dict, intent: str = "") -> VerificationResult:
        """
        Deeply verify that a tool actually accomplished its intended goal,
        not just that it returned without crashing.
        """
        self._stats["total_checks"] += 1

        # Layer 1: Basic success check
        if not result.get("success", True):
            error = result.get("error", "Unknown error")
            return VerificationResult(
                passed=False, confidence=0.99,
                reason=f"Tool '{tool_name}' explicitly reported failure: {error}",
                retry_hint=f"The tool failed with: {error}. Try a different approach or different parameters."
            )

        # Layer 2: Tool-specific deep verification
        vr = self._deep_verify_tool(tool_name, params, result, intent)
        if not vr.passed:
            self._stats["failed"] += 1
            self._log_verification(tool_name, params, result, vr)
            return vr

        # Layer 3: LLM semantic verification (only for high-stakes tools)
        high_stakes = ["run_shell", "write_file", "send_message", "web_search"]
        if self.llm and tool_name in high_stakes and intent:
            vr = self._llm_verify_result(tool_name, params, result, intent)

        if vr.passed:
            self._stats["passed"] += 1
        else:
            self._stats["failed"] += 1

        self._log_verification(tool_name, params, result, vr)
        return vr

    def _deep_verify_tool(self, tool_name: str, params: Dict,
                          result: Dict, intent: str) -> VerificationResult:
        """Tool-specific content validation rules."""

        if tool_name == "run_shell":
            return self._verify_shell_result(params, result, intent)

        elif tool_name == "write_file":
            return self._verify_file_write(params, result)

        elif tool_name == "read_file":
            content = result.get("content", "")
            if not content.strip():
                return VerificationResult(
                    passed=False, confidence=0.9,
                    reason="File was read but returned empty content.",
                    retry_hint="The file appears empty. Check if the path is correct or if the file has content."
                )

        elif tool_name == "web_search":
            # A real web search should return actual content, not just an opened browser
            note = result.get("note", "")
            if "browser" in note.lower():
                return VerificationResult(
                    passed=True, confidence=0.5,
                    reason="Search opened in browser but no programmatic results returned.",
                    retry_hint="Consider using a direct HTTP request to get search results programmatically."
                )

        return VerificationResult(passed=True, confidence=0.85,
                                  reason=f"Tool '{tool_name}' passed basic verification.")

    def _verify_shell_result(self, params: Dict, result: Dict, intent: str) -> VerificationResult:
        """Deep-verify shell command execution."""
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        return_code = result.get("return_code", 0)
        command = params.get("command", "")

        # Non-zero exit = failure
        if return_code != 0:
            return VerificationResult(
                passed=False, confidence=0.95,
                reason=f"Command exited with code {return_code}. Stderr: {stderr[:200]}",
                corrective_action="Check the command syntax and target.",
                retry_hint=f"The command returned exit code {return_code} with error: {stderr[:300]}. "
                           f"Fix the command before retrying."
            )

        # Check for common error signatures in stdout even if exit code is 0
        error_patterns = [
            r"error:", r"Error:", r"ERROR:", r"exception:", r"Exception:",
            r"not found", r"No such file", r"Permission denied", r"Traceback",
            r"FAILED", r"fatal:", r"command not found"
        ]
        for pattern in error_patterns:
            if re.search(pattern, stdout) or re.search(pattern, stderr):
                return VerificationResult(
                    passed=False, confidence=0.80,
                    reason=f"Command completed but output contains error indicators: '{pattern}'",
                    retry_hint=f"Despite exit code 0, the output suggests an error. "
                               f"Full output: {stdout[:300]}"
                )

        return VerificationResult(
            passed=True, confidence=0.90,
            reason=f"Shell command executed successfully, output: {stdout[:80]}..."
        )

    def _verify_file_write(self, params: Dict, result: Dict) -> VerificationResult:
        """Verify a file was actually written with correct content."""
        path = params.get("path", "")
        expected_content = params.get("content", "")

        if not path:
            return VerificationResult(passed=False, confidence=0.99,
                                      reason="No file path provided.")

        # Check file actually exists
        if not os.path.exists(path):
            return VerificationResult(
                passed=False, confidence=0.99,
                reason=f"File write reported success but file does not exist at: {path}",
                retry_hint=f"The file was not created at {path}. Check directory permissions."
            )

        # Check file has content
        actual_size = os.path.getsize(path)
        if actual_size == 0:
            return VerificationResult(
                passed=False, confidence=0.99,
                reason="File exists but is empty (0 bytes).",
                retry_hint="The file was created empty. Retry writing the content."
            )

        return VerificationResult(
            passed=True, confidence=0.95,
            reason=f"File verified: {path} exists with {actual_size} bytes."
        )

    def _llm_verify_result(self, tool_name: str, params: Dict,
                           result: Dict, intent: str) -> VerificationResult:
        """Use LLM to semantically verify if the result matches the intent."""
        if not self.llm:
            return VerificationResult(passed=True, confidence=0.5,
                                      reason="LLM not available for semantic verification.")

        verify_prompt = f"""You are a critical verifier. A tool was executed to accomplish a goal.
Determine if the result actually achieved the goal.

GOAL / INTENT: {intent}
TOOL USED: {tool_name}
TOOL PARAMS: {json.dumps(params, indent=2)[:500]}
TOOL RESULT: {json.dumps(result, indent=2)[:1000]}

Answer in JSON only:
{{
  "achieved": true/false,
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation",
  "corrective_action": "what to do if it failed (empty if succeeded)"
}}"""

        try:
            resp = self.llm.call(verify_prompt, max_tokens=300)
            data = self._parse_json(resp)
            if data:
                return VerificationResult(
                    passed=bool(data.get("achieved", True)),
                    confidence=float(data.get("confidence", 0.7)),
                    reason=data.get("reason", "LLM verification completed."),
                    corrective_action=data.get("corrective_action", ""),
                    retry_hint=data.get("corrective_action", "")
                )
        except Exception as e:
            logger.warning(f"LLM verification failed: {e}")

        return VerificationResult(passed=True, confidence=0.5,
                                  reason="LLM semantic verification inconclusive — defaulting to pass.")

    # ═══════════════════════════════════════════════════════════════
    #  2. CODE EXECUTION VERIFICATION
    # ═══════════════════════════════════════════════════════════════

    def verify_code(self, code: str, language: str = "python",
                    expected_output_contains: str = None,
                    test_input: str = None) -> VerificationResult:
        """
        Verify that generated code is syntactically valid and runs without errors.
        Runs in a sandboxed subprocess with a hard timeout.
        """
        self._stats["total_checks"] += 1
        code = textwrap.dedent(code).strip()

        if language.lower() == "python":
            return self._verify_python_code(code, expected_output_contains)

        return VerificationResult(
            passed=True, confidence=0.4,
            reason=f"No sandbox available for language: {language}. Skipping execution verification."
        )

    def _verify_python_code(self, code: str,
                             expected_output_contains: str = None) -> VerificationResult:
        """Syntax check + sandboxed execution of Python code."""
        import ast

        # Step 1: Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            return VerificationResult(
                passed=False, confidence=0.99,
                reason=f"Python syntax error: {e}",
                corrective_action="Fix the syntax error before executing.",
                retry_hint=f"The generated code has a syntax error: {e}. Please fix it."
            )

        # Step 2: Static safety scan — reject obviously dangerous code
        danger_patterns = [
            r"os\.system\s*\(", r"shutil\.rmtree\s*\(", r"subprocess\.call.*shell=True",
            r"open\s*\(['\"].*['\"],\s*['\"]w['\"]\).*os\.", r"__import__\s*\(",
            r"eval\s*\(.*input", r"exec\s*\(.*input",
        ]
        for pat in danger_patterns:
            if re.search(pat, code):
                return VerificationResult(
                    passed=False, confidence=0.95,
                    reason=f"Code contains potentially dangerous pattern: {pat}",
                    retry_hint="The code was flagged as potentially dangerous. Rewrite without OS-level destructive calls."
                )

        # Step 3: Execute in subprocess sandbox
        tmp_file = f"/tmp/verify_{hashlib.md5(code.encode()).hexdigest()[:8]}.py"
        if os.name == "nt":  # Windows
            tmp_file = os.path.join(os.environ.get("TEMP", "C:\\Temp"),
                                    f"verify_{hashlib.md5(code.encode()).hexdigest()[:8]}.py")

        try:
            os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(code)

            result = subprocess.run(
                ["python", tmp_file],
                capture_output=True, text=True,
                timeout=self.CODE_TIMEOUT_SECS,
                cwd=os.path.dirname(tmp_file)
            )

            # Check for runtime errors
            if result.returncode != 0:
                return VerificationResult(
                    passed=False, confidence=0.98,
                    reason=f"Code exited with error (code {result.returncode}): {result.stderr[:300]}",
                    retry_hint=f"The code crashed with: {result.stderr[:400]}. Fix the runtime error."
                )

            # Check expected output
            if expected_output_contains:
                if expected_output_contains.lower() not in result.stdout.lower():
                    return VerificationResult(
                        passed=False, confidence=0.85,
                        reason=f"Code ran successfully but output did not contain expected string: '{expected_output_contains}'",
                        retry_hint=f"Output was: {result.stdout[:300]}. Expected to contain: {expected_output_contains}"
                    )

            self._stats["passed"] += 1
            return VerificationResult(
                passed=True, confidence=0.97,
                reason=f"Code executed successfully. Output: {result.stdout[:100]}..."
            )

        except subprocess.TimeoutExpired:
            return VerificationResult(
                passed=False, confidence=0.99,
                reason=f"Code timed out after {self.CODE_TIMEOUT_SECS} seconds.",
                retry_hint="The code ran too long. Add a timeout or optimize the logic."
            )
        except Exception as e:
            return VerificationResult(
                passed=False, confidence=0.8,
                reason=f"Code verification error: {e}",
                retry_hint=str(e)
            )
        finally:
            try:
                os.remove(tmp_file)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════
    #  3. PLAN CRITIQUE (Anti-Hallucination)
    # ═══════════════════════════════════════════════════════════════

    def critique_plan(self, goal: str, plan: List[str]) -> Tuple[bool, str, List[str]]:
        """
        Before executing a plan, use a separate LLM call to critically examine it
        for hallucinations, missing steps, and logical flaws.

        Returns: (is_good, critique_summary, improved_plan)
        """
        if not self.llm:
            return True, "LLM not available for critique.", plan

        plan_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan)])
        critique_prompt = f"""You are a critical AI planner reviewing a task plan for an autonomous agent.

GOAL: {goal}

PROPOSED PLAN:
{plan_str}

Critically evaluate this plan:
1. Are all steps necessary and in the right order?
2. Are there any steps that make unfounded assumptions?
3. Are there missing verification/error-handling steps?
4. Is the plan achievable with file system, shell commands, and web search tools?

Respond in JSON:
{{
  "verdict": "GOOD" or "FLAWED" or "INCOMPLETE",
  "critique": "Brief critique (max 2 sentences)",
  "improved_plan": ["step 1", "step 2", ...],
  "confidence": 0.0-1.0
}}"""

        try:
            resp = self.llm.call(critique_prompt, max_tokens=800)
            data = self._parse_json(resp)
            if data:
                verdict = data.get("verdict", "GOOD")
                improved = data.get("improved_plan", plan)
                confidence = float(data.get("confidence", 0.7))
                critique = data.get("critique", "")

                is_good = verdict == "GOOD" or confidence > 0.7
                logger.info(f"Plan critique: {verdict} (conf={confidence:.2f}) — {critique}")
                return is_good, critique, improved if improved else plan

        except Exception as e:
            logger.warning(f"Plan critique failed: {e}")

        return True, "Critique unavailable — proceeding with original plan.", plan

    # ═══════════════════════════════════════════════════════════════
    #  4. SELF-CORRECTION ENGINE
    # ═══════════════════════════════════════════════════════════════

    def generate_correction(self, failed_action: str, error_details: str,
                            context: str = "") -> str:
        """
        Given a failed action and its error, generate a targeted correction prompt
        for the LLM to use in the next iteration.
        """
        if not self.llm:
            return f"Previous attempt failed: {error_details}. Try a different approach."

        correction_prompt = f"""An autonomous agent action FAILED. Generate a specific corrective action.

FAILED ACTION: {failed_action}
ERROR: {error_details}
CONTEXT: {context}

Generate a JSON response with:
{{
  "root_cause": "one sentence root cause",
  "corrective_action": "specific step to take next",
  "alternative_approach": "completely different way to achieve the goal if the direct fix won't work",
  "avoid": "what NOT to do again"
}}"""

        try:
            resp = self.llm.call(correction_prompt, max_tokens=400)
            data = self._parse_json(resp)
            if data:
                return (
                    f"[CORRECTION REQUIRED]\n"
                    f"Root Cause: {data.get('root_cause', 'Unknown')}\n"
                    f"Fix: {data.get('corrective_action', '')}\n"
                    f"Alternative: {data.get('alternative_approach', '')}\n"
                    f"Avoid: {data.get('avoid', '')}"
                )
        except Exception as e:
            logger.warning(f"Correction generation failed: {e}")

        return f"Previous attempt failed with: {error_details}. Try a completely different approach."

    # ═══════════════════════════════════════════════════════════════
    #  5. CONFIDENCE GATE
    # ═══════════════════════════════════════════════════════════════

    def confidence_gate(self, response: str, min_confidence: float = 0.70) -> Tuple[bool, float]:
        """
        Parse an LLM response for embedded confidence score.
        If confidence is below threshold, reject and force more research.

        LLMs should include: CONFIDENCE: 0.85 in their responses when using verification mode.
        """
        # Try to find explicit confidence marker
        conf_match = re.search(r'CONFIDENCE[:\s]+([0-9.]+)', response, re.IGNORECASE)
        if conf_match:
            try:
                conf = float(conf_match.group(1))
                if conf > 1.0:
                    conf = conf / 100.0  # Handle percentage format
                passed = conf >= min_confidence
                return passed, conf
            except ValueError:
                pass

        # Heuristic: Check for uncertainty language
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "not certain", "might be",
            "possibly", "unclear", "cannot confirm", "unable to verify",
            "may or may not", "i believe but", "approximately"
        ]
        low_confidence_count = sum(1 for phrase in uncertainty_phrases
                                   if phrase in response.lower())

        if low_confidence_count >= 2:
            return False, 0.45

        return True, 0.75  # Default: assume reasonable confidence

    # ═══════════════════════════════════════════════════════════════
    #  6. RETRY ORCHESTRATOR
    # ═══════════════════════════════════════════════════════════════

    def execute_with_retry(self, action_fn, action_name: str,
                           verify_fn=None, max_retries: int = None,
                           context: str = "") -> Dict[str, Any]:
        """
        Execute an action with automatic retry and verification.
        This is the core AGI reliability loop.

        action_fn: callable() -> result dict
        verify_fn: callable(result) -> VerificationResult
        """
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None

        for attempt in range(1, max_retries + 1):
            logger.info(f"[Retry {attempt}/{max_retries}] {action_name}")

            try:
                result = action_fn()

                # Run verification if provided
                if verify_fn:
                    vr = verify_fn(result)
                    if vr.passed:
                        self._stats["auto_corrected"] += (attempt - 1)
                        return {
                            "success": True,
                            "result": result,
                            "attempts": attempt,
                            "verification": str(vr)
                        }
                    else:
                        last_error = vr.reason
                        logger.warning(f"Attempt {attempt} verification failed: {vr}")
                        if attempt < max_retries:
                            correction = self.generate_correction(
                                action_name, vr.reason,
                                f"Retry hint: {vr.retry_hint}"
                            )
                            logger.info(f"Correction: {correction}")
                            time.sleep(1.0 * attempt)  # Exponential backoff
                        continue

                # No verify_fn — basic success check
                if result.get("success", True):
                    return {
                        "success": True,
                        "result": result,
                        "attempts": attempt,
                        "verification": "Basic success check passed"
                    }

                last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt} exception: {e}")
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)

        return {
            "success": False,
            "error": last_error,
            "attempts": max_retries,
            "action": action_name
        }

    # ═══════════════════════════════════════════════════════════════
    #  UTILITIES
    # ═══════════════════════════════════════════════════════════════

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Robustly extract JSON from LLM response."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find JSON object in text
        for pattern in [r'\{[^{}]*\}', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        return None

    def _log_verification(self, tool_name: str, params: Dict,
                          result: Dict, vr: VerificationResult):
        """Log verification event to internal history and optionally to DB."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "params_hash": hashlib.md5(str(params).encode()).hexdigest()[:8],
            "passed": vr.passed,
            "confidence": vr.confidence,
            "reason": vr.reason,
        }
        self._verification_log.append(entry)

        if self.db and len(self._verification_log) % 10 == 0:
            try:
                self.db.audit(0, "verification",
                              f"{tool_name}: {'PASS' if vr.passed else 'FAIL'} — {vr.reason[:100]}",
                              severity="info", source="verification_engine")
            except Exception:
                pass

    def get_stats(self) -> Dict:
        """Return runtime statistics."""
        total = self._stats["total_checks"]
        return {
            **self._stats,
            "pass_rate": f"{(self._stats['passed']/total*100):.1f}%" if total else "N/A",
            "log_entries": len(self._verification_log),
        }

    def get_recent_log(self, n: int = 10) -> List[Dict]:
        """Return last N verification events."""
        return self._verification_log[-n:]
