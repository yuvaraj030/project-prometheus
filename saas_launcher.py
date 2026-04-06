"""
AI SaaS Launcher (Phase 16)
============================
Agent proposes a micro-SaaS idea and auto-generates:
  1. A static HTML/CSS landing page
  2. A Stripe checkout session link
  3. An email onboarding sequence template
All artifacts saved to saas_output/<slug>/
"""

import os
import re
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


class SaaSLauncher:
    """
    AI SaaS Launcher — from idea to landing page + checkout + emails in one command.
    """

    def __init__(self, llm_provider: Any, database: Any = None,
                 stripe_key: str = None, output_dir: str = "saas_output"):
        self.llm = llm_provider
        self.db = database
        self.output_dir = output_dir
        self.launches: List[Dict] = []

        if stripe_key and STRIPE_AVAILABLE:
            stripe.api_key = stripe_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False

        os.makedirs(output_dir, exist_ok=True)

    def _slugify(self, text: str) -> str:
        return re.sub(r'[^a-z0-9_-]', '-', text.lower().strip())[:40]

    async def _generate_landing_page(self, idea: str, product: Dict) -> str:
        """Generate a modern HTML landing page for the SaaS product."""
        page_prompt = (
            f"Generate a complete, modern HTML/CSS landing page for this SaaS product:\n"
            f"Name: {product.get('name', idea)}\n"
            f"Tagline: {product.get('tagline', '')}\n"
            f"Features: {', '.join(product.get('features', []))}\n"
            f"Price: {product.get('price', '$29/mo')}\n\n"
            "Requirements:\n"
            "- Full HTML5 page with embedded CSS (no external frameworks)\n"
            "- Dark modern design with gradient hero section\n"
            "- CTA button that says 'Start Free Trial'\n"
            "- Features section with 3 feature cards\n"
            "- Pricing section with one plan\n"
            "- Footer with copyright\n"
            "Output ONLY the complete HTML, no markdown."
        )
        html = await asyncio.to_thread(self.llm.call, page_prompt, system=(
            "You are an expert web designer and copywriter. Generate beautiful, "
            "complete, self-contained HTML pages. Output raw HTML only."
        ), history=[])
        return html or self._fallback_landing_page(product)

    def _fallback_landing_page(self, product: Dict) -> str:
        name = product.get("name", "My SaaS")
        tagline = product.get("tagline", "The smart way to get things done.")
        price = product.get("price", "$29/mo")
        features = product.get("features", ["Fast", "Reliable", "Intelligent"])
        feature_cards = "".join(
            f'<div class="card"><h3>✨ {f}</h3><p>Powered by AI to save you hours every week.</p></div>'
            for f in features[:3]
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{name}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:system-ui,sans-serif; }}
  body {{ background:#0f0f1a; color:#e2e8f0; }}
  .hero {{ background:linear-gradient(135deg,#6366f1,#8b5cf6); padding:80px 20px; text-align:center; }}
  .hero h1 {{ font-size:3em; font-weight:900; margin-bottom:16px; }}
  .hero p {{ font-size:1.3em; opacity:0.9; margin-bottom:32px; }}
  .cta {{ background:#fff; color:#6366f1; padding:16px 40px; border-radius:50px; font-size:1.1em; font-weight:700; border:none; cursor:pointer; text-decoration:none; }}
  .features {{ display:flex; gap:24px; justify-content:center; flex-wrap:wrap; padding:60px 20px; background:#1a1a2e; }}
  .card {{ background:#16213e; border-radius:12px; padding:32px; max-width:280px; border:1px solid #6366f133; }}
  .card h3 {{ font-size:1.2em; margin-bottom:12px; }}
  .pricing {{ text-align:center; padding:60px 20px; }}
  .price-box {{ display:inline-block; background:#1a1a2e; border:1px solid #6366f1; border-radius:16px; padding:40px 60px; }}
  .price {{ font-size:3em; font-weight:900; color:#6366f1; }}
  footer {{ text-align:center; padding:24px; color:#666; background:#0a0a15; }}
</style></head>
<body>
<div class="hero">
  <h1>{name}</h1>
  <p>{tagline}</p>
  <a href="#pricing" class="cta">Start Free Trial</a>
</div>
<div class="features">{feature_cards}</div>
<div class="pricing" id="pricing">
  <h2>Simple Pricing</h2>
  <div class="price-box">
    <div class="price">{price}</div>
    <p>Everything you need. Cancel anytime.</p>
    <br><a href="#" class="cta" style="background:#6366f1;color:#fff;">Get Started</a>
  </div>
</div>
<footer>© {datetime.now().year} {name}. All rights reserved.</footer>
</body></html>"""

    async def _generate_email_sequence(self, product: Dict) -> List[Dict]:
        """Generate a 3-email onboarding sequence."""
        email_prompt = (
            f"Generate a 3-email onboarding sequence for '{product.get('name')}' SaaS. "
            "Each email should have: subject, body (plain text, 100-150 words). "
            "Email 1: Welcome (Day 0). Email 2: Getting Started (Day 2). "
            "Email 3: Pro Tips (Day 7). "
            "Return a JSON array: [{\"subject\": ..., \"body\": ...}, ...]"
        )
        raw = await asyncio.to_thread(self.llm.call, email_prompt, system=(
            "You are a SaaS email copywriter. Output valid JSON only."
        ), history=[])
        try:
            match = re.search(r'\[.*\]', raw or "", re.DOTALL)
            return json.loads(match.group()) if match else []
        except Exception:
            return [
                {"subject": f"Welcome to {product.get('name')}!", "body": "Thanks for signing up! We're excited to have you on board."},
                {"subject": "Getting the most out of your account", "body": "Here are 3 tips to get started quickly..."},
                {"subject": "You're just getting started 🚀", "body": "Power users do these 5 things every week..."},
            ]

    async def launch(self, idea: str, tenant_id: int = 1) -> Dict:
        """Full SaaS launch pipeline for a given idea."""
        print(f"\n🚀 SaaS Launcher — Building product for: '{idea}'")
        print("=" * 60)

        # Step 1: Flesh out the idea
        product_prompt = (
            f"Create a micro-SaaS product concept for: '{idea}'\n"
            "Return JSON: {\"name\": ..., \"tagline\": ..., \"features\": [...], \"price\": ...}"
        )
        raw = await asyncio.to_thread(self.llm.call, product_prompt, system=(
            "You are a startup product strategist. Output valid JSON only."
        ), history=[])
        try:
            match = re.search(r'\{.*\}', raw or "", re.DOTALL)
            product = json.loads(match.group()) if match else {}
        except Exception:
            product = {}
        product.setdefault("name", idea.title())
        product.setdefault("tagline", "The smarter way to work.")
        product.setdefault("features", ["AI-Powered", "Easy Setup", "No-Code"])
        product.setdefault("price", "$29/mo")

        print(f"  📱 Product: {product['name']} — {product['tagline']}")

        slug = self._slugify(product["name"])
        out_dir = os.path.join(self.output_dir, slug)
        os.makedirs(out_dir, exist_ok=True)

        # Step 2: Landing page
        print("  🎨 Generating landing page...")
        html = await self._generate_landing_page(idea, product)
        landing_path = os.path.join(out_dir, "index.html")
        with open(landing_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✅ Landing page: {landing_path}")

        # Step 3: Stripe checkout (if available)
        checkout_url = None
        if self.stripe_enabled:
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": product["name"]},
                            "unit_amount": 2900,
                            "recurring": {"interval": "month"},
                        },
                        "quantity": 1,
                    }],
                    mode="subscription",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )
                checkout_url = session.url
                print(f"  💳 Stripe checkout: {checkout_url}")
            except Exception as e:
                print(f"  ⚠️  Stripe error: {e}")
        else:
            checkout_url = "#checkout-not-configured"
            print("  💳 Stripe: not configured (add STRIPE_KEY to env)")

        # Step 4: Email sequence
        print("  📧 Generating email onboarding sequence...")
        emails = await self._generate_email_sequence(product)
        emails_path = os.path.join(out_dir, "email_sequence.json")
        with open(emails_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2)
        print(f"  ✅ Email sequence: {emails_path}")

        # Summary
        manifest = {
            "idea": idea,
            "product": product,
            "landing_page": landing_path,
            "checkout_url": checkout_url,
            "emails": emails_path,
            "launched": datetime.now().isoformat(),
        }
        manifest_path = os.path.join(out_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        self.launches.append(manifest)

        print(f"\n🎉 {product['name']} is ready! Files in: {out_dir}")
        print("=" * 60)

        if self.db:
            try:
                self.db.audit(tenant_id, "saas_launch", idea[:200])
            except Exception:
                pass

        return manifest

    def get_status(self) -> Dict:
        return {
            "total_launches": len(self.launches),
            "stripe_enabled": self.stripe_enabled,
            "output_dir": self.output_dir,
            "launches": [{"name": l["product"]["name"], "launched": l["launched"]} for l in self.launches],
        }

    def describe(self) -> str:
        return f"SaaSLauncher — {len(self.launches)} products launched. Stripe: {'YES' if self.stripe_enabled else 'NOT CONFIGURED'}."
