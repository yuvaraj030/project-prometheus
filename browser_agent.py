"""
Playwright Browser Agent — Autonomous JS-capable web browsing.
Uses Playwright for reliable interaction with modern web apps.
Requires: pip install playwright && playwright install chromium
"""

import os
import logging
import json
import re
from typing import Optional, List, Any

logger = logging.getLogger("BrowserAgent")

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


class PlaywrightBrowserAgent:
    """
    LLM-driven browser agent. Uses Playwright for robust web automation.
    Supports headless or headed mode, JS-heavy pages, login flows, scraping.
    
    The main loop: see page HTML → LLM decides action → execute → verify → repeat.
    """

    def __init__(self, llm_provider=None, headless: bool = True):
        self.llm = llm_provider
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.action_log: List[dict] = []
        logger.info(f"🌍 PlaywrightBrowserAgent initialized (headless={headless})")

    # ─── Session Management ───────────────────────────────
    def open(self):
        """Launch browser and create a new page."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        if self._browser:
            return  # Already open
        self._playwright = sync_playwright().__enter__()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (compatible; UltimateAIAgent/1.0)"
        )
        self._page = self._context.new_page()
        logger.info("🌐 Browser opened")

    def close(self):
        """Close browser session."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.__exit__(None, None, None)
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        logger.info("🌐 Browser closed")

    def _ensure_open(self):
        if not self._browser or not self._page:
            self.open()

    # ─── Core Actions ─────────────────────────────────────
    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> str:
        """Navigate to a URL."""
        self._ensure_open()
        if not url.startswith("http"):
            url = "https://" + url
        self._page.goto(url, wait_until=wait_until, timeout=30000)
        title = self._page.title()
        self._log("navigate", {"url": url, "title": title})
        logger.info(f"🌐 Navigated to {url} → '{title}'")
        return f"Navigated to: {url} (title: '{title}')"

    def click(self, selector_or_text: str) -> str:
        """Click an element by CSS selector or visible text."""
        self._ensure_open()
        try:
            # Try CSS selector first
            self._page.click(selector_or_text, timeout=5000)
            self._log("click", {"target": selector_or_text})
            return f"Clicked: {selector_or_text}"
        except Exception:
            # Fall back to text-matching
            try:
                self._page.get_by_text(selector_or_text).first.click(timeout=5000)
                self._log("click_text", {"text": selector_or_text})
                return f"Clicked text: '{selector_or_text}'"
            except Exception as e:
                return f"❌ Click failed: {e}"

    def fill(self, selector: str, value: str) -> str:
        """Fill an input field."""
        self._ensure_open()
        try:
            self._page.fill(selector, value, timeout=5000)
            self._log("fill", {"selector": selector, "value": value[:30]})
            return f"Filled '{selector}' with '{value[:30]}...'"
        except Exception as e:
            return f"❌ Fill failed: {e}"

    def press(self, key: str = "Enter") -> str:
        """Press a keyboard key."""
        self._ensure_open()
        self._page.keyboard.press(key)
        self._log("press", {"key": key})
        return f"Pressed: {key}"

    def scrape(self, selector: str = "body", max_chars: int = 5000) -> str:
        """Extract text content from a page element."""
        self._ensure_open()
        try:
            el = self._page.query_selector(selector)
            if not el:
                return "❌ Element not found"
            text = el.inner_text()
            return text[:max_chars]
        except Exception as e:
            return f"❌ Scrape failed: {e}"

    def screenshot(self, path: str = "browser_screenshot.png") -> str:
        """Take a screenshot of the current page."""
        self._ensure_open()
        self._page.screenshot(path=path, full_page=False)
        return path

    def get_links(self, max_links: int = 20) -> List[dict]:
        """Get all visible links on the current page."""
        self._ensure_open()
        links = self._page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
        )
        return [l for l in links if l["href"] and not l["href"].startswith("javascript")][:max_links]

    def get_page_summary(self, max_chars: int = 3000) -> str:
        """Get a condensed text summary of the current page for LLM context."""
        self._ensure_open()
        try:
            title = self._page.title()
            url = self._page.url
            body = self._page.eval_on_selector("body", "el => el.innerText") or ""
            body = re.sub(r'\n{3,}', '\n\n', body)[:max_chars]
            return f"URL: {url}\nTitle: {title}\n\nContent:\n{body}"
        except Exception as e:
            return f"❌ Page summary failed: {e}"

    # ─── Autonomous Web Task Loop ─────────────────────────
    def autonomous_web_task(self, goal: str, max_steps: int = 10) -> str:
        """
        LLM-driven autonomous web task loop.
        Given a goal, the agent decides what to do next on the page.
        
        Args:
            goal: Natural language goal (e.g. "Search for 'Python jobs' on Indeed")
            max_steps: Maximum number of actions before giving up
        """
        if not self.llm:
            return "❌ No LLM provider — autonomous tasks require an LLM"

        self._ensure_open()
        task_log = []
        result = f"❌ Could not complete goal in {max_steps} steps"

        for step in range(1, max_steps + 1):
            page_summary = self.get_page_summary()
            
            prompt = f"""You are controlling a web browser to achieve a goal.

GOAL: {goal}

CURRENT PAGE:
{page_summary[:2500]}

PREVIOUS ACTIONS:
{json.dumps(task_log[-5:], indent=2)}

Available actions (respond with EXACTLY ONE JSON object):
- {{"action": "navigate", "url": "https://example.com"}}
- {{"action": "click", "target": "css-selector or visible text"}}
- {{"action": "fill", "selector": "input#search", "value": "search term"}}
- {{"action": "press", "key": "Enter"}}
- {{"action": "scrape", "selector": "css-selector"}}
- {{"action": "done", "result": "Summary of what was accomplished"}}

Decide the best next action to achieve the goal. Respond with ONLY the JSON."""

            try:
                response = self.llm.call(prompt, max_tokens=200)
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)
                if not json_match:
                    continue
                action_data = json.loads(json_match.group())
            except Exception as e:
                logger.warning(f"Step {step} LLM parse error: {e}")
                continue

            action = action_data.get("action")
            step_result = ""

            if action == "done":
                result = action_data.get("result", "Task complete")
                task_log.append({"step": step, "action": "done", "result": result})
                break
            elif action == "navigate":
                step_result = self.navigate(action_data.get("url", ""))
            elif action == "click":
                step_result = self.click(action_data.get("target", ""))
            elif action == "fill":
                step_result = self.fill(action_data.get("selector", ""), action_data.get("value", ""))
            elif action == "press":
                step_result = self.press(action_data.get("key", "Enter"))
            elif action == "scrape":
                step_result = self.scrape(action_data.get("selector", "body"))
                result = step_result  # Treat scrape result as final output

            task_log.append({"step": step, "action": action, "result": str(step_result)[:200]})
            logger.info(f"🌍 Step {step}: {action} → {str(step_result)[:80]}")

            # Small wait between actions
            self._page.wait_for_timeout(500)

        return result

    def _log(self, action: str, details: dict):
        import time
        self.action_log.append({"action": action, "ts": time.time(), **details})

    def get_status(self) -> dict:
        return {
            "playwright_available": PLAYWRIGHT_AVAILABLE,
            "browser_open": self._browser is not None,
            "current_url": self._page.url if self._page else None,
            "headless": self.headless,
            "actions_taken": len(self.action_log),
            "last_action": self.action_log[-1] if self.action_log else None,
        }

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
