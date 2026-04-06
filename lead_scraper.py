"""
Lead Scraper — find leads via DuckDuckGo search (no Selenium needed).
Commands: /leads find <criteria>|list|export|clear
"""

import os
import json
import re
from datetime import datetime


class LeadScraper:
    """Discover leads using DuckDuckGo search and LLM qualification."""

    DATA_FILE = "leads_data.json"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"leads": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def find_leads(self, criteria: str, limit: int = 10) -> dict:
        """Search for leads matching criteria using DuckDuckGo."""
        try:
            import requests
        except ImportError:
            return {"success": False, "error": "requests library needed: pip install requests"}

        results = []
        queries = [
            f'{criteria} contact email',
            f'{criteria} hire freelancer',
            f'{criteria} "looking for" site:linkedin.com OR site:upwork.com OR site:reddit.com',
        ]
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}

        for query in queries[:2]:  # limit requests
            try:
                url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.ok:
                    # Extract snippets from DDG HTML
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                    urls_found = re.findall(r'<a class="result__a" href="([^"]+)"', resp.text)
                    for i, (t, s) in enumerate(zip(titles[:limit//2], snippets[:limit//2])):
                        clean_t = re.sub(r'<[^>]+>', '', t).strip()
                        clean_s = re.sub(r'<[^>]+>', '', s).strip()
                        url_found = urls_found[i] if i < len(urls_found) else ""
                        if clean_t and clean_s:
                            results.append({
                                "title": clean_t,
                                "snippet": clean_s[:300],
                                "url": url_found,
                                "source": "duckduckgo"
                            })
            except Exception:
                continue

        if not results:
            # Fallback: LLM-based lead generation tips
            if self.llm:
                prompt = (
                    f"List 5 specific places and strategies to find leads for: {criteria}\n"
                    "Include specific websites, communities, and outreach tactics. "
                    "Format as a numbered list."
                )
                try:
                    tip_text = self.llm.chat(prompt)
                    return {
                        "success": True,
                        "leads": [],
                        "ai_suggestions": tip_text,
                        "message": f"🔍 Web search unavailable. Here are AI-generated lead strategies:\n\n{tip_text}"
                    }
                except Exception:
                    pass
            return {"success": False, "error": "No leads found. Try a more specific search."}

        # Qualify leads with LLM
        qualified = []
        for r in results[:limit]:
            lead = {
                "id": len(self._data["leads"]) + len(qualified) + 1,
                "criteria": criteria,
                "title": r["title"],
                "snippet": r["snippet"],
                "url": r["url"],
                "source": r["source"],
                "score": self._score_lead(r, criteria),
                "found_at": datetime.now().isoformat(),
                "status": "new"
            }
            qualified.append(lead)

        # Sort by score
        qualified.sort(key=lambda x: x["score"], reverse=True)
        self._data["leads"].extend(qualified[:limit])
        self._data["leads"] = self._data["leads"][-500:]  # keep 500
        self._save()

        lines = [f"🎯 Found {len(qualified)} leads for '{criteria}':\n"]
        for lead in qualified[:5]:
            lines.append(f"  ⭐{'⭐' if lead['score'] > 0.6 else ''} {lead['title'][:60]}")
            lines.append(f"     {lead['snippet'][:120]}")
            if lead["url"]:
                lines.append(f"     🔗 {lead['url'][:80]}")
            lines.append("")

        return {
            "success": True,
            "count": len(qualified),
            "leads": qualified[:5],
            "message": "\n".join(lines)
        }

    def _score_lead(self, result: dict, criteria: str) -> float:
        """Simple relevance score."""
        score = 0.3
        text = (result.get("title", "") + " " + result.get("snippet", "")).lower()
        keywords = criteria.lower().split()
        for kw in keywords:
            if kw in text:
                score += 0.1
        if any(x in text for x in ["hire", "looking for", "need", "want", "freelance"]):
            score += 0.2
        if any(x in text for x in ["email", "contact", "dm", "message"]):
            score += 0.1
        return min(score, 1.0)

    def list_leads(self, status: str = None) -> str:
        """List saved leads."""
        leads = self._data["leads"]
        if status:
            leads = [l for l in leads if l.get("status") == status]
        if not leads:
            return "No leads found. Use /leads find <criteria> to search."
        lines = [f"📋 LEADS ({len(leads)} total):\n"]
        for lead in reversed(leads[-10:]):
            lines.append(f"  [{lead['id']}] {lead['title'][:60]}")
            lines.append(f"       🎯 {lead['criteria']} | ⭐ {lead['score']:.0%} | {lead['status']}")
        return "\n".join(lines)

    def export_leads(self, filepath: str = "leads_export.csv") -> str:
        """Export leads to CSV."""
        if not self._data["leads"]:
            return "No leads to export."
        try:
            import csv
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "criteria", "title", "snippet", "url", "score", "status", "found_at"])
                writer.writeheader()
                for lead in self._data["leads"]:
                    writer.writerow({k: lead.get(k, "") for k in writer.fieldnames})
            return f"✅ {len(self._data['leads'])} leads exported to: {filepath}"
        except Exception as e:
            return f"❌ Export failed: {e}"

    def update_lead_status(self, lead_id: int, status: str) -> str:
        """Update a lead's status (new/contacted/qualified/closed)."""
        for lead in self._data["leads"]:
            if lead["id"] == lead_id:
                lead["status"] = status
                self._save()
                return f"✅ Lead #{lead_id} status → {status}"
        return f"Lead #{lead_id} not found."
