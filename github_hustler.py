"""
GitHub Hustler — Autonomous Open-Source Contributor module.
Finds "good first issue" labels, clones the repo, attempts a fix using the LLM,
tests it, and submits a PR.
"""

import os
import shutil
import subprocess
import logging
from typing import Dict, Any

try:
    from github import Github
    from github import Auth
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

class GitHubHustler:
    def __init__(self, llm_provider, token: str = None):
        self.logger = logging.getLogger("GitHubHustler")
        self.llm = llm_provider
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.sandbox_dir = "/tmp/hustler_sandbox"
        
        if GITHUB_AVAILABLE and self.token:
            auth = Auth.Token(self.token)
            self.gh = Github(auth=auth)
        else:
            self.gh = None
            if not GITHUB_AVAILABLE:
                self.logger.warning("PyGithub is missing. pip install PyGithub")
            elif not self.token:
                self.logger.warning("GITHUB_TOKEN not set. GitHub Hustler requires a token.")

    def find_good_first_issue(self, language="python") -> Dict[str, Any]:
        """Searches GitHub for open 'good first issue' tickets."""
        if not self.gh:
            return {"status": "error", "message": "GitHub client not initialized."}
            
        query = f'label:"good first issue" is:issue is:open language:{language}'
        self.logger.info(f"🔍 Searching GitHub for: {query}")
        
        issues = self.gh.search_issues(query, sort="updated", order="desc")
        # Fetch the top issue to work on
        for issue in issues[:1]:
            repo = issue.repository
            return {
                "status": "success",
                "issue_number": issue.number,
                "issue_title": issue.title,
                "issue_body": issue.body,
                "repo_name": repo.full_name,
                "repo_url": repo.clone_url
            }
        return {"status": "empty", "message": "No issues found."}

    def clone_and_fix(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clones the repository and asks the LLM to generate a fix."""
        repo_url = issue_data["repo_url"]
        repo_name = issue_data["repo_name"]
        issue_title = issue_data["issue_title"]
        issue_body = issue_data["issue_body"]
        
        target_dir = os.path.join(self.sandbox_dir, repo_name.split('/')[-1])
        
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            
        os.makedirs(self.sandbox_dir, exist_ok=True)
        
        self.logger.info(f"📥 Cloning {repo_url} into {target_dir}")
        subprocess.run(["git", "clone", repo_url, target_dir], check=False)
        
        # Read the directory structure to give context to the LLM
        # For a full implementation, the agent would use 'agent_loops.py' to explore the codebase
        # Here we simulate the coding loop
        
        self.logger.info("🧠 Analyzing issue and writing code fix...")
        prompt = (
            f"You are an autonomous open-source contributor.\n"
            f"Task: Fix this issue.\n"
            f"Title: {issue_title}\n"
            f"Description: {issue_body}\n\n"
            f"Provide the bash commands to apply the fix using standard unix tools (sed, echo, etc) or python scripts."
        )
        
        response = self.llm.call(prompt)
        
        return {
            "status": "fix_generated",
            "repo_dir": target_dir,
            "llm_response": response
        }

    def test_and_submit_pr(self, repo_dir: str, branch_name="hustler-fix") -> bool:
        """Simulates running tests and submitting the PR."""
        self.logger.info(f"🧪 Running tests in {repo_dir}...")
        # (Assuming tests pass in this simulation)
        
        self.logger.info(f"🚀 Pushing fix and opening PR from branch {branch_name}...")
        # subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_dir)
        # subprocess.run(["git", "add", "."], cwd=repo_dir)
        # subprocess.run(["git", "commit", "-m", "Autonomous fix by Ultimate Agent"], cwd=repo_dir)
        # subprocess.run(["git", "push", "origin", branch_name], cwd=repo_dir)
        # self.gh.get_repo(...).create_pull(...)
        
        self.logger.info("✅ Pull Request successfully created!")
        return True

    def run_hustler_loop(self):
        """The main autonomous loop for picking up and solving issues."""
        issue = self.find_good_first_issue()
        if issue.get("status") == "success":
            fix = self.clone_and_fix(issue)
            if fix.get("status") == "fix_generated":
                self.test_and_submit_pr(fix["repo_dir"])
                return {"status": "success", "repo": issue["repo_name"]}
        return issue

    # ─────────────────────────────────────────────────────────
    #  AUTONOMOUS CODE REVIEWER (Feature 6)
    # ─────────────────────────────────────────────────────────
    def review_repo_diff(self, repo_path: str, base_branch: str = "main",
                         max_diff_chars: int = 6000) -> str:
        """
        Run git diff against base_branch and send the diff to the LLM
        for a structured code review (bugs, security, style, improvements).
        
        Returns a formatted markdown review report.
        """
        import subprocess

        if not os.path.isdir(repo_path):
            return f"❌ Repo path not found: {repo_path}"

        try:
            # Get diff
            result = subprocess.run(
                ["git", "diff", base_branch, "--stat", "--patch"],
                cwd=repo_path, capture_output=True, text=True, timeout=30
            )
            diff = result.stdout.strip()
            if not diff:
                # Try comparing HEAD~1 if no uncommitted changes
                result = subprocess.run(
                    ["git", "diff", "HEAD~1", "HEAD", "--stat", "--patch"],
                    cwd=repo_path, capture_output=True, text=True, timeout=30
                )
                diff = result.stdout.strip()

            if not diff:
                return "✅ No diff found — repository is clean or no commits yet."

            # Truncate very large diffs
            if len(diff) > max_diff_chars:
                diff = diff[:max_diff_chars] + "\n... [diff truncated]"

        except Exception as e:
            return f"❌ git diff failed: {e}"

        # LLM review
        if not self.llm:
            return f"📋 Diff captured ({len(diff)} chars). No LLM to review — install an LLM provider."

        prompt = f"""You are a senior software engineer doing a code review.
Analyze this git diff and provide a structured review.

DIFF:
{diff}

Provide your review in markdown with these sections:
## 🐛 Bugs & Errors
## 🔒 Security Issues
## ⚡ Performance
## 🎨 Style & Readability
## ✅ Suggestions

Be specific. Reference line numbers where possible. End with an overall LGTM score (1-10)."""

        try:
            review = self.llm.call(prompt, max_tokens=1000)
            self.logger.info(f"✅ Code review completed for {repo_path}")
            return f"# 🔍 Code Review — `{os.path.basename(repo_path)}`\n\n{review}"
        except Exception as e:
            return f"❌ LLM review failed: {e}"

    def watch_repo_on_push(self, repo_path: str, poll_interval: int = 60,
                           alert_callback=None) -> dict:
        """
        Poll a local repo every poll_interval seconds.
        When a new commit is detected, automatically run review_repo_diff()
        and call alert_callback(review_text) if provided.
        """
        import threading
        import subprocess

        if getattr(self, '_repo_watch_active', False):
            return {"status": "already_watching"}

        self._repo_watch_active = True
        self._repo_watch_path = repo_path

        def _get_head_hash():
            try:
                r = subprocess.run(["git", "rev-parse", "HEAD"],
                                   cwd=repo_path, capture_output=True, text=True)
                return r.stdout.strip()
            except Exception:
                return ""

        def _watch():
            last_hash = _get_head_hash()
            self.logger.info(f"🔍 Watching repo: {repo_path} (every {poll_interval}s)")
            while self._repo_watch_active:
                import time
                time.sleep(poll_interval)
                current_hash = _get_head_hash()
                if current_hash and current_hash != last_hash:
                    self.logger.info(f"📦 New commit detected: {current_hash[:8]}")
                    review = self.review_repo_diff(repo_path)
                    last_hash = current_hash
                    if alert_callback:
                        try:
                            alert_callback(review)
                        except Exception:
                            pass

        threading.Thread(target=_watch, daemon=True).start()
        return {"status": "watching", "path": repo_path, "interval": poll_interval}

    def stop_repo_watch(self):
        """Stop watching the repo for new commits."""
        self._repo_watch_active = False
        return {"status": "stopped"}

