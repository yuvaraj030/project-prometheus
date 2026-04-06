"""
News Briefing Engine (Phase 16 — World Interface)
===================================================
Polls RSS feeds and/or NewsAPI for the latest news.
Summarizes top stories via LLM and injects briefing into agent context.
Runs automatically every morning via HeartbeatScheduler.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


DEFAULT_RSS_FEEDS = [
    ("BBC Top Stories", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
]


class NewsBriefing:
    """
    Realtime News Briefing — fetches, summarizes, and stores news for context injection.
    """

    def __init__(self, llm_provider: Any, database: Any = None,
                 newsapi_key: str = None, max_stories: int = 5):
        self.llm = llm_provider
        self.db = database
        self.newsapi_key = newsapi_key
        self.max_stories = max_stories
        self.last_briefing: Optional[Dict] = None
        self.briefing_cache: List[Dict] = []
        print(f"[NewsBriefing] Initialized. feedparser: {'YES' if FEEDPARSER_AVAILABLE else 'NO'}, "
              f"NewsAPI: {'YES' if newsapi_key else 'NO'}")

    async def _fetch_from_rss(self) -> List[Dict]:
        """Fetch articles from RSS feeds."""
        if not FEEDPARSER_AVAILABLE:
            return []
        articles = []
        for source, url in DEFAULT_RSS_FEEDS:
            try:
                feed = await asyncio.to_thread(feedparser.parse, url)
                for entry in feed.entries[:3]:
                    articles.append({
                        "source": source,
                        "title": entry.get("title", "").strip(),
                        "summary": entry.get("summary", entry.get("description", ""))[:300].strip(),
                        "link": entry.get("link", ""),
                        "published": str(entry.get("published", "")),
                    })
            except Exception as e:
                pass  # Skip failed feeds silently
        return articles[:self.max_stories * 3]

    async def _fetch_from_newsapi(self) -> List[Dict]:
        """Fetch articles from NewsAPI."""
        if not self.newsapi_key or not REQUESTS_AVAILABLE:
            return []
        try:
            url = (
                f"https://newsapi.org/v2/top-headlines?"
                f"language=en&pageSize={self.max_stories}&apiKey={self.newsapi_key}"
            )
            resp = await asyncio.to_thread(requests.get, url, timeout=10)
            data = resp.json()
            return [
                {
                    "source": a.get("source", {}).get("name", "NewsAPI"),
                    "title": a.get("title", ""),
                    "summary": a.get("description", "")[:300] or "",
                    "link": a.get("url", ""),
                    "published": a.get("publishedAt", ""),
                }
                for a in data.get("articles", [])[:self.max_stories]
            ]
        except Exception as e:
            print(f"[NewsBriefing] NewsAPI error: {e}")
            return []

    async def fetch_news(self) -> List[Dict]:
        """Fetch from all sources and deduplicate."""
        rss_task = self._fetch_from_rss()
        api_task = self._fetch_from_newsapi()
        results = await asyncio.gather(rss_task, api_task)
        all_articles = results[0] + results[1]

        # Deduplicate by title similarity (simple word overlap)
        seen_titles = set()
        deduped = []
        for a in all_articles:
            title_key = " ".join(sorted(a["title"].lower().split()[:5]))
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append(a)
        return deduped[:self.max_stories]

    async def generate_briefing(self, tenant_id: int = 1) -> Dict:
        """Fetch news and summarize into an agent briefing."""
        print("\n📰 Fetching today's news...")
        articles = await self.fetch_news()

        if not articles:
            # Placeholder if no feeds available
            articles = [
                {"source": "System", "title": "No news sources available", 
                 "summary": "Configure RSS feeds or NewsAPI key for live news.", "link": ""},
            ]

        # Build summary prompt
        article_text = "\n".join(
            f"{i+1}. [{a['source']}] {a['title']}: {a['summary']}"
            for i, a in enumerate(articles)
        )
        summary_prompt = (
            f"Today is {datetime.now().strftime('%B %d, %Y')}. "
            f"Here are today's top news headlines:\n\n{article_text}\n\n"
            "Write a concise 3-paragraph morning briefing that:\n"
            "1. Highlights the most important story\n"
            "2. Summarizes 2-3 other key developments\n"
            "3. Notes any tech/AI related news\n"
            "Be factual and objective. Use plain prose."
        )
        summary = await asyncio.to_thread(
            self.llm.call, summary_prompt, system=(
                "You are a professional news anchor giving a morning briefing. "
                "Be concise, factual, and clear."
            ), history=[]
        )

        briefing = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "articles": articles,
            "summary": summary or article_text,
            "timestamp": datetime.now().isoformat(),
            "source_count": len(articles),
        }
        self.last_briefing = briefing
        self.briefing_cache.append(briefing)

        if self.db:
            try:
                self.db.audit(tenant_id, "news_briefing", f"{len(articles)} stories fetched")
            except Exception:
                pass

        return briefing

    def get_context_inject(self) -> str:
        """Get a short news context string for system prompt injection."""
        if not self.last_briefing:
            return ""
        date = self.last_briefing.get("date", "today")
        summary = self.last_briefing.get("summary", "")[:500]
        return f"[News Briefing — {date}]:\n{summary}"

    def display(self, briefing: Optional[Dict] = None) -> str:
        """Format briefing for terminal display."""
        b = briefing or self.last_briefing
        if not b:
            return "❌ No briefing available. Run /news first."
        lines = [
            f"\n📰 NEWS BRIEFING — {b.get('date', 'Today')}",
            "=" * 50,
            b.get("summary", ""),
            "\n🔗 Sources:",
        ]
        for a in b.get("articles", [])[:5]:
            lines.append(f"  • [{a.get('source')}] {a.get('title')}")
        return "\n".join(lines)

    def describe(self) -> str:
        last = self.last_briefing.get("date") if self.last_briefing else "never"
        return f"NewsBriefing — Last fetched: {last}. Sources: RSS + {'NewsAPI' if self.newsapi_key else 'no NewsAPI'}."
