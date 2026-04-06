"""
Pricing Analyzer — AI analyzes product/service and suggests pricing strategy.
Commands: /pricing analyze|report|history
"""

import os
import json
from datetime import datetime


class PricingAnalyzer:
    """Uses LLM to suggest tiered pricing strategies for products/services."""

    DATA_FILE = "pricing_data.json"

    SYSTEM_PROMPT = (
        "You are a world-class pricing strategist with expertise in SaaS, freelancing, "
        "physical products, and digital services. You analyze markets and suggest data-driven "
        "pricing with clear rationale."
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
        return {"analyses": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def analyze(self, product_desc: str, context: str = "") -> dict:
        """Analyze a product/service and suggest pricing strategy."""
        if not self.llm:
            return {"success": False, "error": "LLM not available."}
        if not product_desc.strip():
            return {"success": False, "error": "Describe your product or service first."}

        prompt = f"""Perform a comprehensive pricing analysis for:

PRODUCT/SERVICE: {product_desc}
{f'ADDITIONAL CONTEXT: {context}' if context else ''}

Provide a structured pricing strategy report covering:

## 💰 RECOMMENDED PRICING TIERS
[3 tiers with names, prices, and what's included — e.g., Starter/Pro/Enterprise or Basic/Standard/Premium]

## 🎯 PRICING STRATEGY RATIONALE
[Why these price points? What psychological pricing principles apply?]

## 📊 MARKET POSITIONING
[Where does this fit in the market? Who are similar competitors and their pricing?]

## ⚡ QUICK-WIN RECOMMENDATIONS
[3 specific, actionable pricing tactics to implement immediately]

## ⚠️ PRICING MISTAKES TO AVOID
[Top 2-3 common pricing errors for this type of product/service]

## 🔮 FUTURE PRICING EVOLUTION
[How should pricing evolve as the product/user base grows?]
"""
        try:
            result = self.llm.chat(prompt, system=self.SYSTEM_PROMPT)
            if not result:
                return {"success": False, "error": "LLM returned empty response."}

            record = {
                "id": len(self._data["analyses"]) + 1,
                "product": product_desc[:200],
                "context": context[:200],
                "analysis": result,
                "created_at": datetime.now().isoformat()
            }
            self._data["analyses"].append(record)
            self._data["analyses"] = self._data["analyses"][-20:]
            self._save()
            return {"success": True, "analysis": result, "id": record["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_analyses(self) -> str:
        """List past pricing analyses."""
        if not self._data["analyses"]:
            return "No pricing analyses yet. Use /pricing analyze to start."
        lines = ["💰 PRICING ANALYSES:\n"]
        for a in reversed(self._data["analyses"][-10:]):
            lines.append(f"  [{a['id']}] {a['created_at'][:10]}: {a['product'][:80]}")
        return "\n".join(lines)

    def get_analysis(self, analysis_id: int) -> str:
        """Retrieve a specific analysis."""
        for a in self._data["analyses"]:
            if a["id"] == analysis_id:
                return f"# Pricing Analysis — {a['product'][:50]}\n\n{a['analysis']}"
        return f"Analysis #{analysis_id} not found."
