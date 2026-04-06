"""
Note Manager — Second Brain quick-capture notes + search.
Commands: /note add|list|search|delete|export
"""

import os
import json
from datetime import datetime


class NoteManager:
    """Quick-capture notes with tags and search, backed by JSON and vector memory."""

    DATA_FILE = "notes_data.json"

    def __init__(self, llm_provider=None, vector_memory=None, tenant_id="default"):
        self.llm = llm_provider
        self.vmem = vector_memory
        self.tid = tenant_id
        self._data = self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"notes": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    # ── Core API ─────────────────────────────────────────────────────────────

    def add_note(self, text: str, tags: list = None) -> dict:
        """Add a new note."""
        if not text.strip():
            return {"success": False, "error": "Note text cannot be empty."}

        note_id = len(self._data["notes"]) + 1
        note = {
            "id": note_id,
            "text": text.strip(),
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._data["notes"].append(note)
        self._save()

        # Also store in vector memory if available
        if self.vmem:
            try:
                self.vmem.add(
                    self.tid,
                    text=f"[NOTE #{note_id}] {text}",
                    meta={"type": "note", "note_id": note_id, "tags": ",".join(tags or [])}
                )
            except Exception:
                pass

        tags_str = f" | Tags: {', '.join(tags)}" if tags else ""
        return {
            "success": True,
            "note_id": note_id,
            "message": f"📝 Note #{note_id} saved!{tags_str}"
        }

    def list_notes(self, limit: int = 10, tag: str = None) -> str:
        """List recent notes, optionally filtered by tag."""
        notes = self._data["notes"]
        if tag:
            notes = [n for n in notes if tag.lower() in [t.lower() for t in n.get("tags", [])]]
        if not notes:
            return "No notes found." if tag else "No notes yet. Add one with: /note add <text>"

        lines = [f"📓 NOTES ({len(notes)} total):\n"]
        for note in reversed(notes[-limit:]):
            dt = note["created_at"][:10]
            tags_str = f"  #{' #'.join(note['tags'])}" if note.get("tags") else ""
            text_preview = note["text"][:120] + ("..." if len(note["text"]) > 120 else "")
            lines.append(f"  [{note['id']}] {dt}{tags_str}")
            lines.append(f"       {text_preview}")
            lines.append("")
        return "\n".join(lines)

    def search_notes(self, query: str) -> str:
        """Search notes by text content."""
        query_lower = query.lower()
        matches = [
            n for n in self._data["notes"]
            if query_lower in n["text"].lower()
            or any(query_lower in t.lower() for t in n.get("tags", []))
        ]

        # Also try vector memory search
        vector_results = []
        if self.vmem:
            try:
                vr = self.vmem.search(self.tid, query, n_results=5)
                for r in vr:
                    if r.get("meta", {}).get("type") == "note":
                        vector_results.append(r.get("text", "")[:200])
            except Exception:
                pass

        if not matches and not vector_results:
            return f"No notes found matching '{query}'."

        lines = [f"🔍 Search results for '{query}':\n"]
        for note in matches[:5]:
            dt = note["created_at"][:10]
            lines.append(f"  [{note['id']}] {dt}: {note['text'][:150]}")
        if vector_results and not matches:
            lines.append("\n  📡 Semantic matches (via RAG):")
            for vr in vector_results[:3]:
                lines.append(f"  • {vr[:150]}")
        return "\n".join(lines)

    def delete_note(self, note_id: int) -> str:
        """Delete a note by ID."""
        for i, note in enumerate(self._data["notes"]):
            if note["id"] == note_id:
                del self._data["notes"][i]
                self._save()
                return f"🗑️ Note #{note_id} deleted."
        return f"❌ Note #{note_id} not found."

    def export_notes(self, filepath: str = "notes_export.md") -> str:
        """Export all notes to a Markdown file."""
        if not self._data["notes"]:
            return "No notes to export."
        try:
            lines = ["# 📓 My Second Brain — Notes Export\n"]
            lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            lines.append(f"Total Notes: {len(self._data['notes'])}\n\n---\n")
            for note in self._data["notes"]:
                lines.append(f"## Note #{note['id']} — {note['created_at'][:10]}")
                if note.get("tags"):
                    lines.append(f"**Tags:** {', '.join(note['tags'])}")
                lines.append(f"\n{note['text']}\n\n---\n")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return f"✅ {len(self._data['notes'])} notes exported to: {filepath}"
        except Exception as e:
            return f"❌ Export failed: {e}"

    def get_stats(self) -> dict:
        """Return note statistics."""
        notes = self._data["notes"]
        all_tags = []
        for n in notes:
            all_tags.extend(n.get("tags", []))
        tag_counts = {}
        for t in all_tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
        return {
            "total_notes": len(notes),
            "top_tags": sorted(tag_counts.items(), key=lambda x: -x[1])[:5],
            "recent_note": notes[-1]["text"][:100] if notes else None
        }
