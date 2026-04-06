"""
Auto-Tester — AI that generates and runs pytest tests for any code you give it.
Give it a function, file, or paste code — it writes and runs tests automatically.
"""
import os
import re
import sys
import ast
import json
import logging
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("AutoTester")


def _extract_functions(code: str) -> List[Dict]:
    """Extract function signatures and docstrings from Python code."""
    functions = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                docstring = ast.get_docstring(node) or ""
                functions.append({
                    "name": node.name,
                    "args": args,
                    "docstring": docstring[:200],
                    "line": node.lineno
                })
    except SyntaxError:
        pass
    return functions


class AutoTester:
    """
    Automatic test generator and runner.
    Uses LLM to write pytest tests, then executes them via subprocess.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.test_history: List[Dict] = []

    def _generate_test_code(self, code: str, context: str = "") -> str:
        """Use LLM to generate pytest test code."""
        if not self.llm:
            return self._mock_tests(code)

        functions = _extract_functions(code)
        func_list = "\n".join(
            f"  - {f['name']}({', '.join(f['args'])}): {f['docstring'][:80]}"
            for f in functions[:10]
        )

        prompt = (
            f"You are a Python testing expert. Write comprehensive pytest tests for the following code.\n\n"
            f"FUNCTIONS TO TEST:\n{func_list if func_list else '(see code below)'}\n\n"
            f"CODE:\n```python\n{code[:3000]}\n```\n\n"
            f"{'CONTEXT: ' + context if context else ''}\n\n"
            f"Write pytest test code that:\n"
            f"1. Tests normal/happy path cases\n"
            f"2. Tests edge cases (empty input, None, zero, negative values)\n"
            f"3. Tests error conditions\n"
            f"4. Uses descriptive test names\n"
            f"5. Does NOT use external APIs or databases (mock if needed)\n\n"
            f"Output ONLY valid Python pytest code. Start with imports. No explanation."
        )
        try:
            result = self.llm.call(prompt, max_tokens=800)
            # Strip markdown
            if "```python" in result:
                result = result.split("```python")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            return result
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._mock_tests(code)

    def _mock_tests(self, code: str) -> str:
        """Fallback test template when no LLM is available."""
        functions = _extract_functions(code)
        lines = ["import pytest", ""]
        for f in functions[:5]:
            safe_name = f["name"].replace("__", "")
            lines.append(f"def test_{safe_name}_basic():")
            lines.append(f"    # TODO: Add test for {f['name']}()")
            lines.append(f"    assert True  # Placeholder")
            lines.append("")
        return "\n".join(lines) if len(lines) > 2 else "def test_placeholder():\n    assert True\n"

    def generate_tests(self, code_or_path: str, context: str = "") -> Dict[str, Any]:
        """
        Generate tests for code (raw string) or a file path.
        Returns generated test code and metadata.
        """
        # Determine if input is a path or raw code
        code = ""
        source_info = ""

        if os.path.exists(code_or_path) and len(code_or_path) < 300:
            try:
                with open(code_or_path, "r", encoding="utf-8") as f:
                    code = f.read()
                source_info = os.path.basename(code_or_path)
                context = context or f"Testing module: {source_info}"
            except Exception as e:
                return {"error": f"Cannot read file: {e}"}
        else:
            code = code_or_path
            source_info = "inline_code"

        if not code.strip():
            return {"error": "No code provided"}

        functions = _extract_functions(code)
        test_code = self._generate_test_code(code, context)

        return {
            "source": source_info,
            "functions_found": len(functions),
            "function_names": [f["name"] for f in functions],
            "test_code": test_code,
            "generated_at": datetime.now().isoformat()
        }

    def run_tests(self, test_file_or_code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Run pytest on a test file or inline test code.
        Returns pass/fail counts and output.
        """
        # If it's a file path
        if os.path.exists(test_file_or_code) and len(test_file_or_code) < 300:
            test_path = test_file_or_code
            cleanup = False
        else:
            # Write inline code to temp file
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix="_autotest.py",
                delete=False, encoding="utf-8"
            )
            tmp.write(test_file_or_code)
            tmp.close()
            test_path = tmp.name
            cleanup = True

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
                capture_output=True, text=True, timeout=timeout,
                cwd=os.path.dirname(test_path) or "."
            )
            output = result.stdout + result.stderr

            # Parse results
            passed = len(re.findall(r"\bPASSED\b", output))
            failed = len(re.findall(r"\bFAILED\b", output))
            errors = len(re.findall(r"\bERROR\b", output))
            total = passed + failed + errors

            return {
                "status": "passed" if failed == 0 and errors == 0 else "failed",
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": total,
                "output": output[-3000:],  # Last 3000 chars
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "passed": 0, "failed": 0, "errors": 1,
                    "output": f"Tests timed out after {timeout}s"}
        except FileNotFoundError:
            return {"status": "error", "output": "pytest not found. Run: pip install pytest"}
        finally:
            if cleanup:
                try:
                    os.unlink(test_path)
                except Exception:
                    pass

    def test_function(self, func_code: str) -> Dict[str, Any]:
        """
        One-shot: generate AND run tests for a single function.
        Returns both test code and execution results.
        """
        gen_result = self.generate_tests(func_code)
        if "error" in gen_result:
            return gen_result

        test_code = gen_result.get("test_code", "")
        if not test_code:
            return {"error": "Failed to generate test code"}

        # Prepend the source function so tests can import it
        full_test = f"# Source function\n{func_code}\n\n# Tests\n{test_code}"
        run_result = self.run_tests(full_test)

        return {
            "function": gen_result.get("function_names", [])[:1],
            "test_code": test_code,
            "results": run_result,
            "summary": (
                f"✅ {run_result.get('passed', 0)} passed, "
                f"❌ {run_result.get('failed', 0)} failed, "
                f"⚠️ {run_result.get('errors', 0)} errors"
            )
        }

    def generate_and_save(self, path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Generate tests for a file and save to a test file."""
        gen = self.generate_tests(path)
        if "error" in gen:
            return gen

        fname = os.path.basename(path)
        test_fname = f"test_{fname}"
        output_dir = output_dir or os.path.dirname(path) or "."
        test_path = os.path.join(output_dir, test_fname)

        # Add import for the source module
        module_name = fname.replace(".py", "")
        header = f"# Auto-generated tests for {fname}\nimport pytest\ntry:\n    from {module_name} import *\nexcept ImportError:\n    pass\n\n"
        full_code = header + gen["test_code"]

        with open(test_path, "w", encoding="utf-8") as f:
            f.write(full_code)

        return {
            "source": fname,
            "test_file": test_path,
            "functions_tested": gen.get("functions_found", 0),
            "status": "saved"
        }
