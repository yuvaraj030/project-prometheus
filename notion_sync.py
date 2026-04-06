"""
Notion Sync — Read/write Notion pages and databases via the Notion API.
Commands: /notion read|write|search|list|databases
Requires: NOTION_TOKEN env var + pip install requests
"""

import os
import json
from datetime import datetime


class NotionSync:
    """Interface with Notion workspace via the official REST API."""

    API_BASE = "https://api.notion.com/v1"
    VERSION = "2022-06-28"

    def __init__(self, token: str = None):
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.VERSION
        }

    def _get(self, path: str, params: dict = None) -> dict:
        try:
            import requests
            resp = requests.get(f"{self.API_BASE}{path}", headers=self._headers,
                                params=params, timeout=15)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path: str, body: dict) -> dict:
        try:
            import requests
            resp = requests.post(f"{self.API_BASE}{path}", headers=self._headers,
                                 json=body, timeout=15)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def check_connection(self) -> dict:
        """Test API connection."""
        if not self.token:
            return {"connected": False, "error": "NOTION_TOKEN not set. Use: set NOTION_TOKEN=secret_xxx"}
        result = self._get("/users/me")
        if "error" in result or "object" not in result:
            msg = result.get("message") or result.get("error", "Unknown error")
            return {"connected": False, "error": msg}
        return {"connected": True, "user": result.get("name", "Workspace")}

    def search(self, query: str) -> str:
        """Search Notion workspace."""
        check = self.check_connection()
        if not check["connected"]:
            return f"❌ {check['error']}"
        result = self._post("/search", {"query": query, "page_size": 10})
        if "results" not in result:
            return f"❌ Search failed: {result.get('message', 'Unknown error')}"
        if not result["results"]:
            return f"No results found for '{query}'"
        lines = [f"🔍 Notion search: '{query}'\n"]
        for item in result["results"][:8]:
            obj_type = item.get("object", "unknown")
            title = self._extract_title(item)
            item_id = item.get("id", "")[:8]
            lines.append(f"  [{obj_type}] {title} (ID: {item_id}...)")
        return "\n".join(lines)

    def read_page(self, page_id: str) -> str:
        """Read a Notion page."""
        check = self.check_connection()
        if not check["connected"]:
            return f"❌ {check['error']}"
        page = self._get(f"/pages/{page_id}")
        if page.get("object") == "error":
            return f"❌ {page.get('message', 'Page not found')}"
        title = self._extract_title(page)
        # Get blocks (content)
        blocks = self._get(f"/blocks/{page_id}/children", {"page_size": 50})
        content_lines = [f"📄 **{title}**\n"]
        if "results" in blocks:
            for block in blocks["results"][:30]:
                text = self._extract_block_text(block)
                if text:
                    content_lines.append(text)
        return "\n".join(content_lines)

    def write_to_page(self, page_id: str, text: str) -> str:
        """Append text content to a Notion page."""
        check = self.check_connection()
        if not check["connected"]:
            return f"❌ {check['error']}"
        body = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
                    }
                }
            ]
        }
        result = self._post(f"/blocks/{page_id}/children", body)
        if result.get("object") == "error":
            return f"❌ {result.get('message', 'Write failed')}"
        return f"✅ Content appended to Notion page successfully!"

    def list_databases(self) -> str:
        """List accessible databases."""
        check = self.check_connection()
        if not check["connected"]:
            return f"❌ {check['error']}"
        result = self._post("/search", {"filter": {"value": "database", "property": "object"}})
        if "results" not in result:
            return f"❌ {result.get('message', 'Failed')}"
        if not result["results"]:
            return "No databases found. Share databases with your integration first."
        lines = ["📊 NOTION DATABASES:\n"]
        for db in result["results"]:
            title = self._extract_title(db)
            db_id = db.get("id", "")
            lines.append(f"  • {title}")
            lines.append(f"    ID: {db_id}")
        return "\n".join(lines)

    def create_page(self, parent_id: str, title: str, content: str = "") -> str:
        """Create a new Notion page."""
        check = self.check_connection()
        if not check["connected"]:
            return f"❌ {check['error']}"
        body = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        }
        if content:
            body["children"] = [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}
            }]
        result = self._post("/pages", body)
        if result.get("object") == "error":
            return f"❌ {result.get('message', 'Create failed')}"
        page_url = result.get("url", "")
        return f"✅ Page '{title}' created!\n   🔗 {page_url}"

    def _extract_title(self, item: dict) -> str:
        """Extract title from Notion object."""
        try:
            props = item.get("properties", {})
            for key in ["title", "Title", "Name"]:
                if key in props:
                    title_arr = props[key].get("title", props[key].get("rich_text", []))
                    if title_arr:
                        return "".join(t.get("plain_text", "") for t in title_arr)
        except Exception:
            pass
        return "Untitled"

    def _extract_block_text(self, block: dict) -> str:
        """Extract plain text from a block."""
        try:
            block_type = block.get("type", "")
            content = block.get(block_type, {})
            rich = content.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich)
            if block_type == "heading_1":
                return f"# {text}"
            elif block_type == "heading_2":
                return f"## {text}"
            elif block_type == "heading_3":
                return f"### {text}"
            elif block_type == "bulleted_list_item":
                return f"  • {text}"
            elif block_type == "numbered_list_item":
                return f"  1. {text}"
            elif block_type == "to_do":
                checked = content.get("checked", False)
                return f"  [{'x' if checked else ' '}] {text}"
            return text
        except Exception:
            return ""
