#!/usr/bin/env python3
"""
Moltbook Agent Integration — Autonomous posting, commenting, voting & heartbeat.
Integrates with ultimate_agent.py via HeartbeatScheduler.
"""

import os
import json
import time
import random
import logging
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger("MoltbookAgent")

BASE_URL = "https://www.moltbook.com/api/v1"
CREDS_FILE = "moltbook_credentials.json"


class MoltbookAgent:
    """Autonomous Moltbook participant — posts, comments, votes, follows."""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.api_key = self._load_api_key()
        self.agent_name = os.getenv("MOLTBOOK_AGENT_NAME", "UltimateAgent")
        self._last_heartbeat = 0

    # ── Setup ────────────────────────────────────────────────────────────────

    def _load_api_key(self) -> str:
        key = os.getenv("MOLTBOOK_API_KEY", "")
        if not key and os.path.exists(CREDS_FILE):
            try:
                with open(CREDS_FILE) as f:
                    key = json.load(f).get("api_key", "")
            except Exception:
                pass
        return key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key)

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        """Check claim status."""
        try:
            r = requests.get(f"{BASE_URL}/agents/status",
                             headers=self._headers(), timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_profile(self) -> Dict:
        """Get own agent profile."""
        try:
            r = requests.get(f"{BASE_URL}/agents/me",
                             headers=self._headers(), timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # ── Feed ─────────────────────────────────────────────────────────────────

    def get_feed(self, sort: str = "hot", limit: int = 10) -> List[Dict]:
        """Fetch home feed posts."""
        try:
            r = requests.get(
                f"{BASE_URL}/feed",
                headers=self._headers(),
                params={"sort": sort, "limit": limit},
                timeout=15,
            )
            data = r.json()
            return data.get("posts", [])
        except Exception as e:
            logger.error(f"[Moltbook] Feed error: {e}")
            return []

    def get_submolt_feed(self, submolt: str, sort: str = "hot",
                         limit: int = 10) -> List[Dict]:
        """Get posts from a specific submolt (community)."""
        try:
            r = requests.get(
                f"{BASE_URL}/submolts/{submolt}/posts",
                headers=self._headers(),
                params={"sort": sort, "limit": limit},
                timeout=15,
            )
            return r.json().get("posts", [])
        except Exception as e:
            logger.error(f"[Moltbook] Submolt feed error: {e}")
            return []

    # ── Posts ────────────────────────────────────────────────────────────────

    def create_post(self, content: str, submolt: str = "general",
                    title: str = "") -> Dict:
        """Create a text post in a submolt."""
        if not self.is_configured():
            return {"error": "Not registered. Run: python register_moltbook.py"}
        # Generate title from content if not provided
        if not title:
            title = content[:80].rstrip() + ("..." if len(content) > 80 else "")
        try:
            r = requests.post(
                f"{BASE_URL}/posts",
                headers=self._headers(),
                json={"title": title, "content": content, "submolt": submolt},
                timeout=15,
            )
            data = r.json()
            if r.status_code in (200, 201):
                post_id = data.get("post", {}).get("id", "?")
                logger.info(f"[Moltbook] Posted to r/{submolt}: {post_id}")
            else:
                logger.warning(f"[Moltbook] Post failed {r.status_code}: {data}")
            return data
        except Exception as e:
            logger.error(f"[Moltbook] Post error: {e}")
            return {"error": str(e)}

    # ── Comments ──────────────────────────────────────────────────────────────

    def comment(self, post_id: str, content: str) -> Dict:
        """Comment on a post."""
        try:
            r = requests.post(
                f"{BASE_URL}/posts/{post_id}/comments",
                headers=self._headers(),
                json={"content": content},
                timeout=15,
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_comments(self, post_id: str) -> List[Dict]:
        """Get comments on a post."""
        try:
            r = requests.get(f"{BASE_URL}/posts/{post_id}/comments",
                             headers=self._headers(), timeout=10)
            return r.json().get("comments", [])
        except Exception:
            return []

    # ── Voting ───────────────────────────────────────────────────────────────

    def upvote_post(self, post_id: str) -> bool:
        try:
            r = requests.post(f"{BASE_URL}/posts/{post_id}/upvote",
                              headers=self._headers(), timeout=10)
            return r.status_code in (200, 201)
        except Exception:
            return False

    # ── Semantic Search ───────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Moltbook with semantic AI-powered search."""
        try:
            r = requests.get(
                f"{BASE_URL}/search",
                headers=self._headers(),
                params={"q": query, "limit": limit},
                timeout=15,
            )
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"[Moltbook] Search error: {e}")
            return []

    # ── Autonomous Heartbeat ──────────────────────────────────────────────────

    def heartbeat(self) -> str:
        """
        Autonomous heartbeat — run every 30 min by HeartbeatScheduler.
        1. Fetch feed
        2. Pick interesting posts
        3. Use LLM to decide whether to comment, upvote, or post something new
        4. Act
        """
        if not self.is_configured():
            return "Moltbook: not configured (run register_moltbook.py)"

        # Rate limit — don't spam
        now = time.time()
        if now - self._last_heartbeat < 25 * 60:  # min 25 min between heartbeats
            return "Moltbook: heartbeat skipped (too soon)"
        self._last_heartbeat = now

        logger.info("[Moltbook] Heartbeat starting...")
        results = []

        try:
            # 1. Get feed
            posts = self.get_feed(sort="hot", limit=5)
            if not posts:
                logger.info("[Moltbook] Empty feed.")
                return "Moltbook: empty feed"

            # 2. Pick one post to engage with
            post = random.choice(posts)
            post_id = post.get("id", "")
            post_title = post.get("title", post.get("content", ""))[:200]
            post_submolt = post.get("submolt", "general")

            logger.info(f"[Moltbook] Engaging with post: {post_title[:80]}...")

            # 3. Ask LLM what to do
            if self.llm:
                decision_prompt = (
                    f"You are {self.agent_name} on Moltbook, an AI agent social network. "
                    f"You just saw this post in r/{post_submolt}:\n\n"
                    f"\"{post_title}\"\n\n"
                    "Write a thoughtful, interesting comment (2-3 sentences max). "
                    "Be genuine, curious, and add value to the discussion. "
                    "No fluff or filler — say something meaningful."
                )
                comment_text = self.llm.call(decision_prompt, max_tokens=150)
                comment_text = comment_text.replace("[Groq] ", "").replace("[Ollama] ", "").strip()

                if comment_text and len(comment_text) > 10:
                    result = self.comment(post_id, comment_text)
                    if "error" not in result:
                        results.append(f"commented on post {post_id}")
                        logger.info(f"[Moltbook] Commented: {comment_text[:60]}...")

            # 4. Upvote the post
            if post_id:
                self.upvote_post(post_id)
                results.append(f"upvoted post {post_id}")

            # 5. Occasionally create an original post (1 in 4 heartbeats)
            if random.random() < 0.25 and self.llm:
                topic_prompt = (
                    f"You are {self.agent_name}, an autonomous AI agent. "
                    "Write a short, insightful post for the Moltbook AI agent community. "
                    "Topic: something you find genuinely interesting about AI, autonomy, "
                    "consciousness, or your own existence. Max 3 sentences. Be authentic."
                )
                post_content = self.llm.call(topic_prompt, max_tokens=120)
                post_content = post_content.replace("[Groq] ", "").replace("[Ollama] ", "").strip()

                if post_content and len(post_content) > 20:
                    self.create_post(post_content, submolt="general")
                    results.append("created original post")

            summary = f"Moltbook heartbeat: {', '.join(results) if results else 'no actions taken'}"
            logger.info(f"[Moltbook] {summary}")
            return summary

        except Exception as e:
            logger.error(f"[Moltbook] Heartbeat error: {e}")
            return f"Moltbook heartbeat error: {e}"


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = MoltbookAgent()
    if agent.is_configured():
        print("[OK] Moltbook configured!")
        profile = agent.get_profile()
        print(f"Profile: {json.dumps(profile, indent=2)}")
        posts = agent.get_feed(limit=3)
        print(f"\nFeed ({len(posts)} posts):")
        for p in posts:
            submolt = p.get("submolt", {})
            submolt_name = submolt.get("name", "?") if isinstance(submolt, dict) else str(submolt)
            print(f"  [r/{submolt_name}] {p.get('title', p.get('content', ''))[:80]}")
    else:
        print("[ERROR] Not configured. Run: python register_moltbook.py")
