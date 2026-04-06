"""
Meeting Summarizer — paste transcript → action items + summary via LLM.
Commands: /meeting [paste|file <path>|last]
"""

import os
import json
from datetime import datetime


class MeetingSummarizer:
    """Summarize meeting transcripts into action items and key points."""

    DATA_FILE = "meeting_summaries.json"

    SYSTEM_PROMPT = (
        "You are an expert meeting facilitator and note-taker. "
        "When given a meeting transcript, extract structured information clearly."
    )

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"summaries": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    # ── Core API ─────────────────────────────────────────────────────────────

    def summarize_text(self, transcript: str, title: str = "") -> dict:
        """Summarize a meeting transcript."""
        if not transcript.strip():
            return {"success": False, "error": "Empty transcript provided."}

        truncated = transcript[:6000]  # limit context
        prompt = f"""Analyze this meeting transcript and provide a structured report:

TRANSCRIPT:
{truncated}

Provide your response in this exact format:
## 📋 MEETING SUMMARY
[2-3 sentence overview of what was discussed]

## ✅ ACTION ITEMS
[List each action item as: - [Owner/Unknown] Task description (Due: date or ASAP)]

## 🔑 KEY DECISIONS
[Bullet list of decisions made]

## 📊 PARTICIPANTS
[List names/roles mentioned, or "Not specified"]

## ⚠️ OPEN QUESTIONS
[Unresolved items or follow-ups needed]
"""
        if not self.llm:
            return {
                "success": False,
                "error": "LLM not available. Connect an LLM provider first."
            }

        try:
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            if not result:
                return {"success": False, "error": "LLM returned empty response."}

            summary_record = {
                "id": len(self._data["summaries"]) + 1,
                "title": title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "summarized_at": datetime.now().isoformat(),
                "transcript_preview": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "summary": result
            }
            self._data["summaries"].append(summary_record)
            self._data["summaries"] = self._data["summaries"][-50:]  # keep last 50
            self._save()

            return {"success": True, "summary": result, "id": summary_record["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def summarize_file(self, filepath: str) -> dict:
        """Summarize a meeting transcript from a file."""
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        try:
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                transcript = f.read()
            title = os.path.basename(filepath)
            return self.summarize_text(transcript, title=title)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_summaries(self) -> str:
        """List all saved meeting summaries."""
        if not self._data["summaries"]:
            return "No meeting summaries yet. Use /meeting to paste a transcript."
        lines = ["📅 MEETING SUMMARIES:\n"]
        for s in reversed(self._data["summaries"][-10:]):
            lines.append(f"  [{s['id']}] {s['title']}")
            lines.append(f"       📅 {s['summarized_at'][:10]}")
            lines.append(f"       📝 {s['transcript_preview'][:80]}...")
            lines.append("")
        return "\n".join(lines)

    def get_last(self) -> str:
        """Get the most recent summary."""
        if not self._data["summaries"]:
            return "No meeting summaries yet."
        return self._data["summaries"][-1]["summary"]

    def get_by_id(self, summary_id: int) -> str:
        """Get a specific summary by ID."""
        for s in self._data["summaries"]:
            if s["id"] == summary_id:
                return f"# {s['title']}\n\n{s['summary']}"
        return f"Summary #{summary_id} not found."
