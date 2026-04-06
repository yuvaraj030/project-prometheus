"""
Prompt Optimizer — takes a prompt and returns an improved version with chain-of-thought.
Commands: /optimize <prompt>
"""

import os
import json
from datetime import datetime


class PromptOptimizer:
    """Improves user prompts using chain-of-thought reasoning via LLM."""

    DATA_FILE = "prompt_optimizer_data.json"

    SYSTEM_PROMPT = (
        "You are a world-class prompt engineer with deep knowledge of LLM capabilities, "
        "chain-of-thought prompting, few-shot examples, role specification, and output formatting. "
        "You analyze prompts and rewrite them to be dramatically more effective."
    )

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
        return {"optimizations": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def optimize(self, original_prompt: str, goal: str = "") -> dict:
        """Optimize a prompt using chain-of-thought improvement."""
        if not self.llm:
            return {"success": False, "error": "LLM not available."}
        if not original_prompt.strip():
            return {"success": False, "error": "Please provide a prompt to optimize."}

        meta_prompt = f"""You are optimizing this prompt for maximum LLM effectiveness:

ORIGINAL PROMPT:
{original_prompt}

{f'USER GOAL: {goal}' if goal else ''}

Follow this chain-of-thought process:

## 🔍 STEP 1: DIAGNOSIS
Identify the weaknesses in the original prompt:
- Is the role/persona specified?
- Is the output format defined?
- Are constraints given?
- Is context provided?
- Are examples needed?

## ✨ STEP 2: OPTIMIZATION STRATEGY
Which techniques will help most?
(Choose from: role prompting, chain-of-thought, few-shot, output templating, constraint specification, context enrichment)

## 🚀 STEP 3: OPTIMIZED PROMPT
```
[Write the dramatically improved version here - ready to copy-paste]
```

## 📈 STEP 4: IMPROVEMENT SCORE
Rate the improvement: Original X/10 → Optimized Y/10
Explain the key changes made in 2-3 sentences.
"""
        try:
            result = self.llm.chat(meta_prompt, system=self.SYSTEM_PROMPT)
            if not result:
                return {"success": False, "error": "LLM returned empty response."}

            record = {
                "id": len(self._data["optimizations"]) + 1,
                "original": original_prompt[:500],
                "goal": goal,
                "optimized": result,
                "created_at": datetime.now().isoformat()
            }
            self._data["optimizations"].append(record)
            self._data["optimizations"] = self._data["optimizations"][-100:]
            self._save()

            return {"success": True, "result": result, "id": record["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_history(self) -> str:
        """List optimization history."""
        if not self._data["optimizations"]:
            return "No optimizations yet. Use /optimize <prompt> to start."
        lines = ["✨ OPTIMIZATION HISTORY:\n"]
        for o in reversed(self._data["optimizations"][-10:]):
            lines.append(f"  [{o['id']}] {o['created_at'][:10]}: {o['original'][:80]}...")
        return "\n".join(lines)
