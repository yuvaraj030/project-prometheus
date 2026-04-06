"""
Fine-Tuner Data Generator — creates JSONL training data from conversation history.
Commands: /finetune generate|export|stats|clear
"""

import os
import json
from datetime import datetime


class FinetuneGenerator:
    """Generate fine-tuning datasets from conversation history."""

    DATA_FILE = "finetune_data.jsonl"
    META_FILE = "finetune_meta.json"

    def __init__(self, llm_provider=None, db=None):
        self.llm = llm_provider
        self.db = db
        self._meta = self._load_meta()

    def _load_meta(self):
        if os.path.exists(self.META_FILE):
            try:
                with open(self.META_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"total_pairs": 0, "last_generated": None, "quality_filter": True}

    def _save_meta(self):
        try:
            with open(self.META_FILE, "w") as f:
                json.dump(self._meta, f, indent=2)
        except Exception:
            pass

    def generate_from_history(self, tenant_id: str = "default", limit: int = 200) -> dict:
        """Generate JSONL training pairs from conversation history."""
        pairs = []

        # Source 1: DB conversation history
        if self.db:
            try:
                history = self.db.get_conversation_history(tenant_id, limit=limit)
                for i in range(0, len(history) - 1, 2):
                    user_msg = history[i] if history[i].get("role") == "user" else None
                    asst_msg = history[i+1] if i+1 < len(history) and history[i+1].get("role") == "assistant" else None
                    if user_msg and asst_msg:
                        content_u = user_msg.get("content", "").strip()
                        content_a = asst_msg.get("content", "").strip()
                        if len(content_u) > 10 and len(content_a) > 20:
                            pairs.append(self._make_pair(content_u, content_a))
            except Exception:
                pass

        # Source 2: Synthetically generate Q&A using LLM if not enough pairs
        if len(pairs) < 20 and self.llm:
            try:
                synth = self._generate_synthetic_pairs(10)
                pairs.extend(synth)
            except Exception:
                pass

        if not pairs:
            return {"success": False, "error": "No conversation history found. Chat more first!"}

        # Write to JSONL
        try:
            with open(self.DATA_FILE, "a", encoding="utf-8") as f:
                for pair in pairs:
                    f.write(json.dumps(pair) + "\n")
        except Exception as e:
            return {"success": False, "error": f"Write failed: {e}"}

        self._meta["total_pairs"] += len(pairs)
        self._meta["last_generated"] = datetime.now().isoformat()
        self._save_meta()

        return {
            "success": True,
            "pairs_generated": len(pairs),
            "total_pairs": self._meta["total_pairs"],
            "output_file": self.DATA_FILE,
            "message": (
                f"✅ Generated {len(pairs)} training pairs!\n"
                f"   📁 File: {self.DATA_FILE}\n"
                f"   📊 Total dataset: {self._meta['total_pairs']} pairs\n"
                f"   💡 Compatible with OpenAI fine-tuning format"
            )
        }

    def _make_pair(self, user_text: str, assistant_text: str) -> dict:
        """Format a training pair in OpenAI JSONL format."""
        return {
            "messages": [
                {"role": "system", "content": "You are a helpful, intelligent AI assistant."},
                {"role": "user", "content": user_text[:2000]},
                {"role": "assistant", "content": assistant_text[:2000]}
            ]
        }

    def _generate_synthetic_pairs(self, n: int) -> list:
        """Generate synthetic Q&A pairs for augmentation."""
        if not self.llm:
            return []
        prompt = (
            f"Generate {n} high-quality question-answer pairs for fine-tuning an AI assistant. "
            "Cover topics like: coding help, writing assistance, analysis, problem-solving, explanations. "
            "Format as JSON array: [{\"user\": \"...\", \"assistant\": \"...\"}]"
        )
        try:
            result = self.llm.chat(prompt)
            if not result:
                return []
            # Extract JSON
            import re
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return [self._make_pair(d["user"], d["assistant"]) for d in data if "user" in d and "assistant" in d]
        except Exception:
            pass
        return []

    def export(self, filepath: str = None) -> str:
        """Export JSONL dataset to a custom path."""
        if not os.path.exists(self.DATA_FILE):
            return "❌ No fine-tuning data generated yet. Run /finetune generate first."
        dest = filepath or f"finetune_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        try:
            import shutil
            shutil.copy2(self.DATA_FILE, dest)
            return f"✅ Exported to: {dest}"
        except Exception as e:
            return f"❌ Export failed: {e}"

    def get_stats(self) -> str:
        """Statistics about the dataset."""
        total = self._meta.get("total_pairs", 0)
        if not os.path.exists(self.DATA_FILE):
            return "No fine-tuning data yet. Run /finetune generate."
        try:
            with open(self.DATA_FILE) as f:
                lines = [l for l in f if l.strip()]
            actual = len(lines)
            size_kb = os.path.getsize(self.DATA_FILE) / 1024
        except Exception:
            actual = 0
            size_kb = 0
        return (
            f"📊 FINE-TUNE DATASET STATS\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Total Pairs : {actual}\n"
            f"  File Size   : {size_kb:.1f} KB\n"
            f"  Last Update : {self._meta.get('last_generated', 'Never')[:10]}\n"
            f"  Format      : OpenAI JSONL (messages)\n"
            f"  File        : {self.DATA_FILE}\n\n"
            f"  💡 Use with: openai api fine_tunes.create -t {self.DATA_FILE}"
        )

    def clear(self) -> str:
        """Clear the dataset."""
        if os.path.exists(self.DATA_FILE):
            os.remove(self.DATA_FILE)
        self._meta["total_pairs"] = 0
        self._save_meta()
        return "🗑️ Fine-tuning dataset cleared."
