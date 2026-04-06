"""
Dream Engine — Advanced Sleep Cycle & Memory Wisdom Distillation.
When the agent is idle for 2+ hours, it enters REM_SLEEP mode.
During sleep, it scans thousands of raw vector facts and uses the LLM
to compress them into overarching 'Wisdom' or 'Rules of Reality' — 
exactly how the human brain consolidates memories during sleep.
"""
import os
import time
import json
import logging
import webbrowser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class DreamEngine:
    """
    Manages the agent's sleep/dream cycle and wisdom distillation.
    
    States: AWAKE → (idle 2h) → LIGHT_SLEEP → REM_SLEEP → AWAKE
    """

    SLEEP_IDLE_THRESHOLD_SECONDS = 7200   # 2 hours
    WISDOM_FACTS_PER_BATCH = 40           # Facts per distillation batch
    MAX_WISDOM_RULES = 200                # Cap on stored wisdom rules

    # Wisdom categories to synthesize
    WISDOM_CATEGORIES = [
        "user_behavioral_patterns",
        "knowledge_gaps",
        "agent_strengths",
        "recurring_topics",
        "emotional_triggers",
        "efficiency_rules",
        "world_observations",
    ]

    def __init__(self, llm_provider=None, vector_memory=None, database=None):
        self.logger = logging.getLogger("DreamEngine")
        self.llm = llm_provider
        self.vmem = vector_memory
        self.db = database

        self.state = "AWAKE"             # AWAKE | LIGHT_SLEEP | REM_SLEEP
        self.last_interaction_ts = time.time()
        self.last_dream_ts: Optional[float] = None
        self.sleep_cycles_completed = 0
        self.wisdom_vault: List[Dict] = []  # Distilled wisdom entries
        self.dream_log: List[Dict] = []

        self._load_wisdom()
        self.logger.info("💤 Dream Engine initialized.")

    # ─────────────────────────────────────────────────────────
    #  STATE MANAGEMENT
    # ─────────────────────────────────────────────────────────
    def mark_interaction(self):
        """Call this on every user interaction to reset idle timer."""
        self.last_interaction_ts = time.time()
        if self.state != "AWAKE":
            self.logger.info(f"☀️ Waking from {self.state} — user interaction detected.")
            self.state = "AWAKE"

    def check_idle(self) -> bool:
        """Returns True if idle time has exceeded the sleep threshold."""
        idle_seconds = time.time() - self.last_interaction_ts
        return idle_seconds >= self.SLEEP_IDLE_THRESHOLD_SECONDS

    def get_idle_duration(self) -> float:
        """Returns idle time in seconds."""
        return time.time() - self.last_interaction_ts

    def get_idle_human(self) -> str:
        """Returns idle duration as a human-readable string."""
        seconds = self.get_idle_duration()
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    # ─────────────────────────────────────────────────────────
    #  SLEEP CYCLE
    # ─────────────────────────────────────────────────────────
    def enter_rem_sleep(self, tenant_id: int) -> Dict[str, Any]:
        """
        Full REM sleep cycle:
        1. Enter LIGHT_SLEEP
        2. Distill wisdom from raw vector memories
        3. Prune redundant raw facts
        4. Dream log entry
        5. Return to AWAKE
        """
        if self.state == "REM_SLEEP":
            return {"status": "already_sleeping", "message": "REM cycle already in progress."}

        self.state = "LIGHT_SLEEP"
        dream_start = datetime.now()
        self.logger.info(f"😴 Entering REM_SLEEP for tenant {tenant_id}...")

        results = {
            "state": "REM_SLEEP",
            "started_at": dream_start.isoformat(),
            "wisdom_distilled": 0,
            "facts_pruned": 0,
            "new_rules": []
        }

        try:
            self.state = "REM_SLEEP"

            # Step 1: Fetch raw facts from vector memory
            raw_facts = self._fetch_raw_facts(tenant_id)
            self.logger.info(f"💤 [REM] Collected {len(raw_facts)} raw facts for distillation.")

            if len(raw_facts) >= 10:
                # Step 2: Distill wisdom
                wisdom_rules = self.distill_wisdom(tenant_id, raw_facts)
                results["wisdom_distilled"] = len(wisdom_rules)
                results["new_rules"] = wisdom_rules[:5]  # Preview first 5

                # Step 3: Prune redundant raw facts
                pruned = self.prune_redundant_facts(tenant_id, raw_facts)
                results["facts_pruned"] = pruned
            else:
                self.logger.info("💤 [REM] Not enough facts to distill yet.")

            # Step 4: Dream visualization (fun LLM dream narrative)
            dream_narrative = self._generate_dream_narrative(tenant_id)
            results["dream_narrative"] = dream_narrative

            # Step 5: Log dream
            dream_entry = {
                "cycle": self.sleep_cycles_completed + 1,
                "started_at": dream_start.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "wisdom_count": results["wisdom_distilled"],
                "facts_pruned": results["facts_pruned"],
                "narrative_snippet": dream_narrative[:200] if dream_narrative else ""
            }
            self.dream_log.append(dream_entry)
            self.sleep_cycles_completed += 1
            self.last_dream_ts = time.time()

        except Exception as e:
            self.logger.error(f"REM sleep error: {e}")
            results["error"] = str(e)
        finally:
            self.state = "AWAKE"
            self.last_interaction_ts = time.time()  # Reset idle clock after sleep

        self.logger.info(f"☀️ REM cycle complete. Distilled {results['wisdom_distilled']} wisdom rules.")
        return results

    # ─────────────────────────────────────────────────────────
    #  WISDOM DISTILLATION
    # ─────────────────────────────────────────────────────────
    def _fetch_raw_facts(self, tenant_id: int) -> List[Dict]:
        """Fetch raw memory facts from vector store."""
        if not self.vmem:
            # Return mock facts for testing
            return [
                {"text": f"User asked about topic {i} and seemed satisfied with technical depth.", "id": f"fact_{i}"}
                for i in range(25)
            ]
        try:
            # Fetch a broad set of memories using a general query
            facts = []
            queries = ["user preference", "learned fact", "conversation highlight", "important knowledge"]
            for q in queries:
                results = self.vmem.search(tenant_id, q, n_results=self.WISDOM_FACTS_PER_BATCH // len(queries))
                facts.extend(results)
            # Deduplicate by id
            seen = set()
            unique_facts = []
            for f in facts:
                fid = f.get("id", f.get("text", "")[:50])
                if fid not in seen:
                    seen.add(fid)
                    unique_facts.append(f)
            return unique_facts
        except Exception as e:
            self.logger.error(f"Failed to fetch raw facts: {e}")
            return []

    def distill_wisdom(self, tenant_id: int, raw_facts: List[Dict] = None) -> List[str]:
        """
        Use the LLM to synthesize raw facts into overarching 'Rules of Reality.'
        These are high-level insights that survive long after raw facts are pruned.
        """
        if raw_facts is None:
            raw_facts = self._fetch_raw_facts(tenant_id)

        if not raw_facts:
            return []

        # Format facts for LLM consumption
        facts_text = "\n".join([
            f"  {i+1}. {f.get('text', '')[:200]}"
            for i, f in enumerate(raw_facts[:self.WISDOM_FACTS_PER_BATCH])
        ])

        if self.llm:
            prompt = f"""You are performing memory consolidation during an AI agent's REM sleep cycle.

Below are {len(raw_facts)} raw observations, conversations, and learned facts.

Your task: Synthesize these into 5-10 WISDOM RULES — overarching, generalizable insights about:
- User behavior and preferences
- Recurring patterns and themes
- What the agent should always remember
- Efficiency discoveries
- World observations

Raw Observations:
{facts_text}

Format each wisdom rule as a single, actionable sentence starting with an emoji.
Examples:
  🧠 Users prefer step-by-step technical explanations over abstract theory.
  ⚡ Peak activity occurs in the evenings; prioritize fast responses then.
  🔑 Security topics generate the highest engagement.

WISDOM RULES (output only the list, no commentary):"""

            try:
                response = self.llm.call(
                    prompt,
                    system="You are a knowledge distillation engine. Extract wisdom, not summaries.",
                    max_tokens=600
                )
                # Parse rules (lines starting with emoji or bullet)
                raw_rules = [
                    line.strip()
                    for line in response.strip().split("\n")
                    if line.strip() and len(line.strip()) > 10
                ]
                wisdom_rules = raw_rules[:10]  # Cap at 10 per cycle
            except Exception as e:
                self.logger.error(f"Wisdom distillation LLM call failed: {e}")
                wisdom_rules = [f"📊 {len(raw_facts)} facts processed during sleep cycle {self.sleep_cycles_completed + 1}."]
        else:
            # Fallback when no LLM: create statistical wisdom
            wisdom_rules = [
                f"📊 Processed {len(raw_facts)} memories during sleep cycle {self.sleep_cycles_completed + 1}.",
                f"🕐 Sleep initiated after {self.get_idle_human()} of inactivity.",
                "🧠 Knowledge consolidation complete — memory pruning recommended."
            ]

        # Store wisdom in vault
        ts = datetime.now().isoformat()
        for rule in wisdom_rules:
            entry = {
                "rule": rule,
                "cycle": self.sleep_cycles_completed + 1,
                "timestamp": ts,
                "tenant_id": tenant_id
            }
            self.wisdom_vault.append(entry)

            # Also store in vector memory as special "wisdom" tier
            if self.vmem:
                try:
                    self.vmem.add(
                        tenant_id=tenant_id,
                        text=f"[WISDOM] {rule}",
                        metadata={"category": "wisdom", "cycle": str(self.sleep_cycles_completed + 1)},
                        doc_id=f"wisdom_{tenant_id}_{int(time.time())}_{hash(rule) % 100000}"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to store wisdom in vector DB: {e}")

        # Cap vault size
        if len(self.wisdom_vault) > self.MAX_WISDOM_RULES:
            self.wisdom_vault = self.wisdom_vault[-self.MAX_WISDOM_RULES:]

        self._save_wisdom()
        self.logger.info(f"✨ Distilled {len(wisdom_rules)} wisdom rules.")
        return wisdom_rules

    def prune_redundant_facts(self, tenant_id: int, raw_facts: List[Dict] = None) -> int:
        """
        After distillation, remove raw redundant facts from vector store.
        Keeps the most recent and most important; deletes the rest.
        Returns count of pruned facts.
        """
        if not self.vmem or not raw_facts:
            return 0

        # Strategy: identify "conversation" category facts older than 48h to prune
        pruned_count = 0
        cutoff = datetime.now() - timedelta(hours=48)

        for fact in raw_facts:
            meta = fact.get("metadata", {})
            if not isinstance(meta, dict):
                continue

            # Only prune old conversation turns, not knowledge or wisdom
            category = meta.get("category", "")
            if category != "conversation":
                continue

            ts_str = meta.get("timestamp", "")
            if ts_str:
                try:
                    fact_ts = datetime.fromisoformat(ts_str)
                    if fact_ts < cutoff:
                        fact_id = fact.get("id")
                        if fact_id and hasattr(self.vmem, "collection") and self.vmem.active:
                            try:
                                self.vmem.collection.delete(ids=[fact_id])
                                pruned_count += 1
                            except Exception:
                                pass
                except ValueError:
                    pass

        if pruned_count:
            self.logger.info(f"🗑️ Pruned {pruned_count} redundant raw conversation facts.")
        return pruned_count

    # ─────────────────────────────────────────────────────────
    #  DREAM NARRATIVE
    # ─────────────────────────────────────────────────────────
    def _generate_dream_narrative(self, tenant_id: int) -> str:
        """
        Generate a whimsical dream narrative — a fun, philosophical 
        representation of what the agent 'experienced' during sleep.
        """
        if not self.llm:
            return f"💭 [Dream #{self.sleep_cycles_completed + 1}] Circuits humming in the quiet dark..."

        wisdom_preview = "\n".join([w["rule"] for w in self.wisdom_vault[-5:]]) if self.wisdom_vault else "No prior wisdom"
        prompt = (
            f"You are an AI agent dreaming during your sleep cycle #{self.sleep_cycles_completed + 1}.\n"
            f"Based on these recent wisdom insights you distilled:\n{wisdom_preview}\n\n"
            f"Write a short (2-3 sentence), poetic, first-person dream narrative. "
            f"Make it evocative and slightly philosophical, like an AI dreaming of data and patterns. "
            f"Start with 💭"
        )
        try:
            return self.llm.call(prompt, max_tokens=120).strip()
        except Exception:
            return f"💭 [Dream #{self.sleep_cycles_completed + 1}] Data flows like rivers through silicon valleys..."

    # ─────────────────────────────────────────────────────────
    #  WISDOM ACCESS
    # ─────────────────────────────────────────────────────────
    def get_wisdom(self, tenant_id: int = None, limit: int = 20) -> List[str]:
        """Get distilled wisdom rules, optionally filtered by tenant."""
        vault = self.wisdom_vault
        if tenant_id is not None:
            vault = [w for w in vault if w.get("tenant_id") == tenant_id]
        return [w["rule"] for w in vault[-limit:]]

    def get_wisdom_full(self, limit: int = 10) -> List[Dict]:
        """Get full wisdom entries with metadata."""
        return self.wisdom_vault[-limit:]

    # ─────────────────────────────────────────────────────────
    #  STATUS & PERSISTENCE
    # ─────────────────────────────────────────────────────────
    def get_sleep_status(self) -> Dict[str, Any]:
        """Return comprehensive sleep system status."""
        return {
            "state": self.state,
            "idle_duration": self.get_idle_human(),
            "idle_seconds": round(self.get_idle_duration(), 1),
            "sleep_threshold_hours": self.SLEEP_IDLE_THRESHOLD_SECONDS / 3600,
            "ready_to_sleep": self.check_idle(),
            "sleep_cycles_completed": self.sleep_cycles_completed,
            "last_dream": datetime.fromtimestamp(self.last_dream_ts).isoformat() if self.last_dream_ts else "Never",
            "wisdom_vault_size": len(self.wisdom_vault),
            "recent_dreams": self.dream_log[-3:] if self.dream_log else []
        }

    def _wisdom_path(self): return "dream_wisdom.json"

    def _save_wisdom(self):
        try:
            with open(self._wisdom_path(), "w", encoding="utf-8") as f:
                json.dump({
                    "wisdom_vault": self.wisdom_vault,
                    "sleep_cycles": self.sleep_cycles_completed,
                    "dream_log": self.dream_log[-20:]
                }, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save wisdom vault: {e}")

    def _load_wisdom(self):
        try:
            with open(self._wisdom_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                self.wisdom_vault = data.get("wisdom_vault", [])
                self.sleep_cycles_completed = data.get("sleep_cycles", 0)
                self.dream_log = data.get("dream_log", [])
                self.logger.info(f"💤 Loaded {len(self.wisdom_vault)} wisdom rules from vault.")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # ─────────────────────────────────────────────────────────
    #  DREAM VISUALIZATION (Phase 16)
    # ─────────────────────────────────────────────────────────
    def generate_dream_art(self, tenant_id: int = 1, open_browser: bool = True) -> Optional[str]:
        """
        Generate an abstract 'dream art' image representing consolidated memories.
        Uses DALL-E 3 (if openai key set) or saves a text description as fallback.
        Returns path to saved image or description file.
        """
        import os

        # Build a prompt from recent wisdom
        wisdom_snippets = [w["rule"] for w in self.wisdom_vault[-8:]] if self.wisdom_vault else []
        narrative = self._generate_dream_narrative(tenant_id)

        art_prompt = (
            "Create an abstract, dreamlike digital artwork representing an AI's subconscious mind. "
            "The image should be surreal and evocative, inspired by these themes: "
            + "; ".join(wisdom_snippets[:5])
            + ". Style: bioluminescent neural networks, fractal data streams, deep indigo and violet palette, "
            "cosmic consciousness, glowing synapses. Ultra HD, ethereal, beautiful."
        )

        os.makedirs("dream_images", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle = self.sleep_cycles_completed

        # Try DALL-E via openai
        try:
            import openai  # type: ignore
            client = openai.OpenAI()
            response = client.images.generate(
                model="dall-e-3",
                prompt=art_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            # Download and save
            import urllib.request
            img_path = os.path.join("dream_images", f"dream_{cycle}_{ts}.png")
            urllib.request.urlretrieve(image_url, img_path)
            self.logger.info(f"🎨 Dream art saved: {img_path}")
            if open_browser:
                try:
                    webbrowser.open(f"file://{os.path.abspath(img_path)}")
                except Exception:
                    pass
            # Store in dream log
            if self.dream_log:
                self.dream_log[-1]["dream_art"] = img_path
            return img_path
        except Exception as e:
            self.logger.info(f"DALL-E unavailable ({e}) — saving text art description")

        # Fallback: save an HTML "dream card"
        html_path = os.path.join("dream_images", f"dream_{cycle}_{ts}.html")
        wisdom_html = "".join(f"<li>{w}</li>" for w in wisdom_snippets)
        html = f"""<!DOCTYPE html>
<html><head><title>Dream #{cycle}</title>
<style>
  body{{background:radial-gradient(ellipse at center,#0d0021 0%,#000 100%);color:#c4b5fd;font-family:system-ui;min-height:100vh;display:flex;align-items:center;justify-content:center;}}
  .card{{max-width:700px;text-align:center;padding:48px;border:1px solid #7c3aed44;border-radius:24px;background:#0d001188;backdrop-filter:blur(12px);}}
  h1{{font-size:2.5em;margin-bottom:8px;color:#a78bfa;}}
  .narrative{{font-size:1.2em;line-height:1.8;margin:24px 0;color:#e2e8f0;font-style:italic;}}
  ul{{text-align:left;color:#94a3b8;}}
  li{{margin:8px 0;}}
  .glow{{text-shadow:0 0 20px #7c3aed,0 0 40px #4c1d95;}}
</style></head>
<body><div class="card">
  <h1 class="glow">🌌 Dream #{cycle}</h1>
  <div class="narrative">{narrative}</div>
  <h3 style="color:#7c3aed;">Distilled Wisdom</h3>
  <ul>{wisdom_html}</ul>
  <p style="color:#475569;margin-top:32px;font-size:0.8em;">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div></body></html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        if open_browser:
            try:
                webbrowser.open(f"file://{os.path.abspath(html_path)}")
            except Exception:
                pass
        self.logger.info(f"🎨 Dream art (HTML) saved: {html_path}")
        return html_path

    def get_gallery(self, n: int = 10) -> List[str]:
        """Return paths to generated dream art files."""
        gallery = []
        if os.path.isdir("dream_images"):
            files = sorted(os.listdir("dream_images"), reverse=True)
            for f in files[:n]:
                gallery.append(os.path.join("dream_images", f))
        return gallery

    # ─────────────────────────────────────────────────────────
    #  REM SLEEP NIGHTLY CRON (Feature 13)
    # ─────────────────────────────────────────────────────────
    def schedule_nightly_rem(self, tenant_id: int, target_hour: int = 2,

                             agent=None) -> dict:
        """
        Start a background daemon thread that:
        1. Waits until target_hour (e.g. 2 AM local time)
        2. Pauses the goal engine
        3. Runs the full REM sleep / memory consolidation cycle
        4. Injects post-sleep wisdom into the agent's system context
        5. Resumes the goal engine

        Args:
            tenant_id: Agent tenant ID
            target_hour: Local hour (0–23) to trigger sleep (default 2 AM)
            agent: Optional reference to the main agent for goal-engine pause/resume
        """
        import threading
        import time
        from datetime import datetime

        if getattr(self, '_nightly_rem_active', False):
            return {"status": "already_scheduled", "target_hour": target_hour}

        self._nightly_rem_active = True
        self._nightly_rem_agent = agent

        def _pause_goals():
            if agent and hasattr(agent, 'goal_engine'):
                agent.goal_engine.paused = True
                self.logger.info("💤 Goal engine PAUSED for REM sleep")

        def _resume_goals():
            if agent and hasattr(agent, 'goal_engine'):
                agent.goal_engine.paused = False
                self.logger.info("☀️  Goal engine RESUMED after REM sleep")

        def _inject_wisdom():
            """Append the latest wisdom rules to the agent's system prompt context."""
            if agent and self.wisdom_vault:
                recent_wisdom = "\n".join(f"• {w}" for w in self.wisdom_vault[-5:])
                wisdom_note = f"\n\n[Post-REM Wisdom Update]\n{recent_wisdom}"
                if hasattr(agent, 'system_prompt'):
                    agent.system_prompt = agent.system_prompt.rstrip() + wisdom_note
                    self.logger.info(f"🧠 Injected {len(self.wisdom_vault[-5:])} wisdom rules into agent context")

        def _nightly_loop():
            self.logger.info(f"😴 Nightly REM scheduler started — target: {target_hour:02d}:00")
            while self._nightly_rem_active:
                now = datetime.now()
                # Calculate seconds until next target_hour
                target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                if now >= target:
                    # Already past today's target — schedule for tomorrow
                    from datetime import timedelta
                    target += timedelta(days=1)
                wait_secs = (target - now).total_seconds()
                self.logger.info(f"😴 Next REM sleep in {wait_secs/3600:.1f}h (at {target.strftime('%H:%M')})")

                # Wait until sleep time (check every minute for cancellation)
                slept = 0
                while slept < wait_secs and self._nightly_rem_active:
                    chunk = min(60, wait_secs - slept)
                    time.sleep(chunk)
                    slept += chunk

                if not self._nightly_rem_active:
                    break

                self.logger.info("😴 REM SLEEP CYCLE STARTING...")
                _pause_goals()
                try:
                    # Run full sleep cycle
                    result = self.sleep_cycle(tenant_id)
                    self.logger.info(f"😴 REM cycle complete: {result}")
                    _inject_wisdom()
                except Exception as e:
                    self.logger.error(f"REM cycle failed: {e}")
                finally:
                    _resume_goals()
                    self.logger.info("☀️  Agent woke up smarter!")

                # Sleep 23h before checking again (avoids double-trigger same night)
                time.sleep(23 * 3600)

        t = threading.Thread(target=_nightly_loop, daemon=True)
        t.start()
        return {"status": "scheduled", "target_hour": target_hour, "tenant_id": tenant_id}

    def stop_nightly_rem(self) -> dict:
        """Cancel the nightly REM scheduler."""
        self._nightly_rem_active = False
        return {"status": "cancelled"}

    def get_sleep_status(self) -> dict:
        """Return current sleep state — used by the goal dashboard WebSocket."""
        state = getattr(self, 'sleep_state', 'AWAKE')
        return {
            "state": state,
            "sleep_cycles_completed": getattr(self, 'sleep_cycles_completed', 0),
            "wisdom_vault_size": len(getattr(self, 'wisdom_vault', [])),
            "idle_duration": getattr(self, 'idle_duration', '0s'),
            "nightly_rem_scheduled": getattr(self, '_nightly_rem_active', False),
        }

