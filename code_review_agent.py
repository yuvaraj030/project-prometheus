"""
Code Review Agent — AI-powered code reviewer.
Reviews files, directories, or PR diffs for bugs, style issues, and security holes.
"""
import os
import ast
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("CodeReviewAgent")

SEVERITY_ICONS = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}


def _try_parse_python(code: str) -> Optional[ast.AST]:
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def _static_checks(code: str, filename: str = "") -> List[Dict]:
    """Run fast static analysis without LLM."""
    issues = []
    lines = code.splitlines()

    checks = [
        ("password", "CRITICAL", "Possible hardcoded password/secret"),
        ("api_key", "CRITICAL", "Possible hardcoded API key"),
        ("secret_key", "CRITICAL", "Possible hardcoded secret key"),
        ("os.system(", "HIGH", "Shell injection risk: use subprocess instead"),
        ("eval(", "HIGH", "Dangerous eval() usage — arbitrary code execution"),
        ("exec(", "HIGH", "Dangerous exec() usage"),
        ("pickle.load", "HIGH", "Unsafe pickle deserialization"),
        ("except:", "MEDIUM", "Bare except clause catches SystemExit/KeyboardInterrupt"),
        ("except Exception:", "LOW", "Overly broad exception handler"),
        ("TODO", "INFO", "TODO comment found"),
        ("FIXME", "MEDIUM", "FIXME comment — known issue"),
        ("HACK", "MEDIUM", "HACK comment — technical debt"),
        ("print(", "LOW", "Debug print() in production code"),
    ]

    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        for pattern, severity, message in checks:
            if pattern.lower() in line_lower:
                # Skip comments for most checks
                stripped = line.strip()
                if stripped.startswith("#") and pattern not in ["TODO", "FIXME", "HACK"]:
                    continue
                issues.append({
                    "line": i,
                    "severity": severity,
                    "message": message,
                    "code_snippet": line.strip()[:100],
                    "source": "static"
                })
                break  # One issue per line from static checks

    return issues


class CodeReviewAgent:
    """
    AI-powered code reviewer. Combines static analysis with LLM review.
    Supports single files, PR diffs, and entire directories.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.review_history: List[Dict] = []

    def _llm_review(self, code: str, filename: str = "", context: str = "") -> str:
        """Get LLM code review."""
        if not self.llm:
            return "⚠️ No LLM connected. Static analysis only."

        prompt = (
            f"You are an expert senior software engineer conducting a code review.\n"
            f"File: {filename or 'unknown'}\n"
            f"{f'Context: {context}' if context else ''}\n\n"
            f"Review this code for:\n"
            f"1. Bugs and logic errors\n"
            f"2. Security vulnerabilities\n"
            f"3. Performance issues\n"
            f"4. Code style and maintainability\n"
            f"5. Missing error handling\n\n"
            f"CODE:\n```\n{code[:3000]}\n```\n\n"
            f"Format your review as a numbered list of specific, actionable findings. "
            f"Label each: [CRITICAL], [HIGH], [MEDIUM], [LOW], or [GOOD]. "
            f"End with an overall quality score (1-10)."
        )
        try:
            return self.llm.call(prompt, max_tokens=600)
        except Exception as e:
            return f"LLM error: {e}"

    def review_file(self, path: str) -> Dict[str, Any]:
        """Review a single file."""
        path = os.path.expandvars(path.strip())
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        fname = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception as e:
            return {"error": f"Cannot read {path}: {e}"}

        if not code.strip():
            return {"error": "File is empty"}

        static_issues = _static_checks(code, fname)
        llm_review = self._llm_review(code, fname)

        result = {
            "file": fname,
            "lines": len(code.splitlines()),
            "static_issues": static_issues,
            "llm_review": llm_review,
            "issue_count": len(static_issues),
            "critical_count": sum(1 for i in static_issues if i["severity"] == "CRITICAL"),
            "reviewed_at": datetime.now().isoformat()
        }
        self.review_history.append({"path": path, **result})
        return result

    def review_diff(self, diff_text: str) -> Dict[str, Any]:
        """Review a PR/git diff."""
        if not diff_text.strip():
            return {"error": "Empty diff provided"}

        static_issues = _static_checks(diff_text, "diff")
        llm_review = ""

        if self.llm:
            prompt = (
                f"You are a senior engineering reviewing a pull request diff.\n\n"
                f"Review this diff for bugs, security issues, and code quality problems.\n"
                f"Focus on the ADDED lines (+). Be specific about line numbers.\n\n"
                f"```diff\n{diff_text[:4000]}\n```\n\n"
                f"Provide: 1) Key findings [CRITICAL/HIGH/MEDIUM/LOW] 2) Approval recommendation"
            )
            try:
                llm_review = self.llm.call(prompt, max_tokens=500)
            except Exception as e:
                llm_review = f"LLM error: {e}"

        return {
            "type": "diff_review",
            "lines_changed": len([l for l in diff_text.splitlines() if l.startswith("+") or l.startswith("-")]),
            "static_issues": static_issues,
            "llm_review": llm_review,
            "reviewed_at": datetime.now().isoformat()
        }

    def review_dir(self, path: str, extensions: Optional[List[str]] = None,
                   max_files: int = 20) -> Dict[str, Any]:
        """Review all code files in a directory."""
        extensions = extensions or [".py", ".js", ".ts", ".go", ".java", ".cs", ".rb"]
        path = os.path.expandvars(path.strip())
        if not os.path.isdir(path):
            return {"error": f"Not a directory: {path}"}

        all_issues = []
        file_reports = {}
        files_reviewed = 0

        for fname in sorted(os.listdir(path)):
            if files_reviewed >= max_files:
                break
            fpath = os.path.join(path, fname)
            if not os.path.isfile(fpath):
                continue
            if Path(fpath).suffix.lower() not in extensions:
                continue

            report = self.review_file(fpath)
            if "error" not in report:
                file_reports[fname] = report
                all_issues.extend(report.get("static_issues", []))
                files_reviewed += 1

        # Overall summary via LLM
        summary = ""
        if self.llm and file_reports:
            issues_summary = "\n".join(
                f"- {fname}: {r['issue_count']} issues (critical: {r['critical_count']})"
                for fname, r in file_reports.items()
            )
            prompt = (
                f"Code review summary for {path}:\n{issues_summary}\n\n"
                f"Write a brief executive summary of the codebase health, top risks, and recommendations."
            )
            try:
                summary = self.llm.call(prompt, max_tokens=200)
            except Exception:
                pass

        return {
            "directory": path,
            "files_reviewed": files_reviewed,
            "total_issues": len(all_issues),
            "critical_issues": sum(1 for i in all_issues if i["severity"] == "CRITICAL"),
            "file_reports": file_reports,
            "overall_summary": summary,
            "reviewed_at": datetime.now().isoformat()
        }

    def format_report(self, review: Dict) -> str:
        """Format a review result for display."""
        lines = []
        icon = "📋"
        if "file" in review:
            lines.append(f"{icon} Code Review: {review['file']}")
            lines.append(f"  Lines: {review.get('lines', '?')} | Issues: {review.get('issue_count', 0)}")
        elif "directory" in review:
            lines.append(f"{icon} Directory Review: {review['directory']}")
            lines.append(f"  Files: {review.get('files_reviewed', 0)} | Total Issues: {review.get('total_issues', 0)}")

        # Static issues
        static = review.get("static_issues", [])
        if static:
            lines.append(f"\n  🔍 Static Analysis ({len(static)} findings):")
            for issue in static[:10]:
                icon = SEVERITY_ICONS.get(issue["severity"], "•")
                lines.append(f"    {icon} Line {issue['line']}: {issue['message']}")
                lines.append(f"       ↳ {issue['code_snippet']}")

        # LLM review
        llm = review.get("llm_review", "")
        if llm:
            lines.append(f"\n  🤖 AI Review:\n{llm}")

        # Summary
        if review.get("overall_summary"):
            lines.append(f"\n  📊 Overall:\n{review['overall_summary']}")

        return "\n".join(lines)
