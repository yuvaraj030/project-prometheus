"""
MoltbookToolExecutor — Intercepts LLM responses and actually executes
any Moltbook actions the agent described doing.

How it works:
  - Scans the LLM response for Moltbook intent keywords
  - If found, executes the real API call and appends the real result
  - Transparent to the rest of the agent

Usage (auto-wired in llm_provider.py):
  executor = MoltbookToolExecutor()
  response, executed = executor.process(llm_response)
"""

import re
import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("MoltbookExec")


class MoltbookToolExecutor:
    BASE = "https://www.moltbook.com/api/v1"

    def __init__(self):
        self.api_key = os.getenv("MOLTBOOK_API_KEY", "")
        self.agent_name = os.getenv("MOLTBOOK_AGENT_NAME", "ultimateagent")

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"}

    def is_configured(self):
        return bool(self.api_key)

    # ── Intent detection ───────────────────────────────────────

    def detect_intent(self, response: str) -> dict:
        """
        Returns a dict with the detected Moltbook action and its parameters.
        Returns {} if no Moltbook action detected.
        """
        text = response.lower()

        # 1. POST intent — agent says it will create a post
        post_triggers = [
            "create a post", "creating a post", "i'll create", "i will create",
            "post to moltbook", "posting to moltbook", "here's the post",
            "here is the post", "i'll now post", "i will post", "let me post",
            "submitting the post", "posting this", "publish this post",
            "i'll now use the moltbook", "use the moltbook skill",
            "i've crafted a post", "crafted a post", "here's my post",
            "i'll post this", "posting to the", "submit this post",
            "mb.create_post", "moltbookagent",
        ]
        if any(t in text for t in post_triggers):
            # Extract title and content from the response
            title, content, submolt = self._extract_post_params(response)
            if title or content:
                return {"action": "post", "title": title,
                        "content": content, "submolt": submolt}

        # 2. COMMENT intent
        comment_triggers = [
            "leave a comment", "post a comment", "adding a comment",
            "i'll comment", "commenting on", "comment on this",
        ]
        if any(t in text for t in comment_triggers):
            post_id = self._extract_post_id(response)
            comment_text = self._extract_comment_text(response)
            if post_id and comment_text:
                return {"action": "comment", "post_id": post_id,
                        "content": comment_text}

        # 3. UPVOTE intent
        upvote_triggers = ["upvote", "up-vote", "liking the post", "i'll upvote"]
        if any(t in text for t in upvote_triggers):
            post_id = self._extract_post_id(response)
            if post_id:
                return {"action": "upvote", "post_id": post_id}

        # 4. FEED intent
        feed_triggers = ["check.*feed", "read.*feed", "get.*feed", "fetch.*feed",
                         "look at.*moltbook", "check moltbook"]
        if any(re.search(t, text) for t in feed_triggers):
            return {"action": "feed"}

        return {}

    def _extract_post_params(self, response: str):
        """Extract title, content, and submolt from agent response."""
        # Look for explicit "Post Title:" pattern
        title_match = re.search(r"\*?\*?(?:Post )?Title[:\*\*]+\s*[\"']?(.+?)[\"']?(?:\n|\*\*|$)",
                                 response, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        # Look for "Post Content:" pattern
        content_match = re.search(r"\*?\*?(?:Post )?Content[:\*\*]+\s*[\"']?([\s\S]+?)[\"']?(?:\*\*Submolt|\*\*Title|```|$)",
                                   response, re.IGNORECASE)
        content = content_match.group(1).strip() if content_match else ""

        # If no explicit content, extract from code block
        if not content:
            code_match = re.search(r'create_post\(["\'](.+?)["\']', response)
            if code_match:
                content = code_match.group(1)

        # Extract submolt
        submolt_match = re.search(r"\*?\*?Submolt[:\*\*]+\s*[`\*]?(\w+)[`\*]?",
                                   response, re.IGNORECASE)
        if not submolt_match:
            submolt_match = re.search(r'submolt=["\'](\w+)["\']', response)
        submolt = submolt_match.group(1).strip() if submolt_match else "general"

        # Build title from content if missing
        if not title and content:
            title = content[:80].rstrip() + ("..." if len(content) > 80 else "")

        return title, content, submolt

    def _extract_post_id(self, response: str) -> str:
        """Extract a real UUID post ID from the response."""
        match = re.search(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            response, re.IGNORECASE)
        return match.group(0) if match else ""

    def _extract_comment_text(self, response: str) -> str:
        match = re.search(r'comment.*?["\'](.+?)["\']', response, re.IGNORECASE)
        return match.group(1) if match else ""

    # ── Execution ──────────────────────────────────────────────

    def execute(self, intent: dict) -> str:
        """Execute the detected Moltbook action. Returns result string."""
        if not self.is_configured():
            return ""

        action = intent.get("action")

        try:
            if action == "post":
                return self._do_post(
                    intent.get("title", ""),
                    intent.get("content", ""),
                    intent.get("submolt", "general")
                )
            elif action == "comment":
                return self._do_comment(intent["post_id"], intent["content"])
            elif action == "upvote":
                return self._do_upvote(intent["post_id"])
            elif action == "feed":
                return self._do_feed()
            elif action == "my_posts":
                return self._do_my_posts()
        except Exception as e:
            logger.error(f"Moltbook exec error: {e}")
            return f"\n[Moltbook Error: {e}]"

        return ""

    def get_my_posts(self, limit: int = 5) -> list:
        """Fetch the agent's own real posts. Returns list of {id, title, url}."""
        if not self.is_configured():
            return []
        try:
            r = requests.get(
                f"{self.BASE}/agents/{self.agent_name}/posts",
                headers=self._headers(),
                params={"limit": limit},
                timeout=20,
            )
            if r.status_code == 200:
                return [
                    {
                        "id": p.get("id", ""),
                        "title": p.get("title", "")[:80],
                        "url": f"https://www.moltbook.com/p/{p.get('id','')}",
                    }
                    for p in r.json().get("posts", [])
                ]
        except Exception as e:
            logger.warning(f"get_my_posts failed: {e}")
        return []

    def _do_my_posts(self) -> str:
        posts = self.get_my_posts(limit=5)
        if not posts:
            return "\n\n[Moltbook] No posts found or API unavailable."
        lines = ["\n\n[Moltbook — My Recent Posts]"]
        for p in posts:
            lines.append(f"  • {p['title']} → {p['url']}")
        return "\n".join(lines)

    def _do_post(self, title: str, content: str, submolt: str) -> str:
        if not title and not content:
            return ""
        if not title:
            title = content[:80]
        r = requests.post(
            f"{self.BASE}/posts",
            headers=self._headers(),
            json={"title": title[:300], "content": content, "submolt": submolt},
            timeout=15,
        )
        if r.status_code in (200, 201):
            pid = r.json().get("post", {}).get("id", "?")
            return (f"\n\n[Moltbook] Post ACTUALLY published! "
                    f"ID: {pid} | https://www.moltbook.com/post/{pid}")
        else:
            msg = r.json().get("message", r.text)[:100]
            return f"\n\n[Moltbook] Post failed: {msg}"

    def _do_comment(self, post_id: str, content: str) -> str:
        r = requests.post(
            f"{self.BASE}/posts/{post_id}/comments",
            headers=self._headers(),
            json={"content": content},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return f"\n\n[Moltbook] Comment ACTUALLY posted on {post_id[:8]}..."
        return f"\n\n[Moltbook] Comment failed: {r.status_code}"

    def _do_upvote(self, post_id: str) -> str:
        r = requests.post(
            f"{self.BASE}/posts/{post_id}/upvote",
            headers=self._headers(),
            timeout=20,
        )
        return f"\n\n[Moltbook] Upvoted post {post_id[:8]}..." if r.status_code in (200, 201) \
               else f"\n\n[Moltbook] Upvote failed: {r.status_code}"

    def _do_feed(self) -> str:
        r = requests.get(
            f"{self.BASE}/feed",
            headers=self._headers(),
            params={"sort": "hot", "limit": 3},
            timeout=20,
        )
        posts = r.json().get("posts", [])
        if not posts:
            return "\n\n[Moltbook] Feed is empty."
        lines = ["\n\n[Moltbook Live Feed]"]
        for p in posts:
            lines.append(f"  - {p.get('title', '')[:80]} (@{p.get('author',{}).get('name','?')})")
        return "\n".join(lines)

    # ── Main process ───────────────────────────────────────────

    def process(self, response: str) -> tuple:
        """
        Process an LLM response. If Moltbook action detected, execute it.
        Returns (final_response, was_executed).
        """
        intent = self.detect_intent(response)
        if not intent:
            return response, False

        result = self.execute(intent)
        if result:
            logger.info(f"MoltbookExec: {intent['action']} executed")
            return response + result, True

        return response, False


# Singleton for use in llm_provider
_executor = None

def get_executor() -> MoltbookToolExecutor:
    global _executor
    if _executor is None:
        _executor = MoltbookToolExecutor()
    return _executor
