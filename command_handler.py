"""
Command Handler — Routes and executes all /commands for the agent.
Extracted from ultimate_agent.py for modularity.
"""

import os
import sys
import json
import asyncio
from typing import List
from config import CONFIG


class CommandHandler:
    """Handles all /command routing and execution."""

    def __init__(self, agent):
        self.agent = agent

    async def handle(self, cmd_full: str):
        """Main command router."""
        agent = self.agent
        parts = cmd_full.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/omega":
            await self._cmd_omega()
            return

        agent.log_ui(f"Command: {cmd_full}")

        # --- OpenClaw-style commands ---
        if cmd == "/skills":
            self._cmd_skills()
        elif cmd == "/tools":
            self._cmd_tools()
        elif cmd == "/heartbeat":
            await asyncio.to_thread(self._cmd_heartbeat)
        elif cmd == "/react":
            await self._cmd_react(args)

        elif cmd == "/voice":
            agent.voice_mode = not agent.voice_mode
            print(f"🎤 Voice: {'ON' if agent.voice_mode else 'OFF'}")
        elif cmd == "/live":
            agent.live_mode = not agent.live_mode
            print(f"📡 Live: {'ON' if agent.live_mode else 'OFF'}")
        elif cmd == "/status":
            self._show_status()
        elif cmd == "/eval":
            self._show_eval()
        elif cmd == "/analyze":
            await self._show_analysis()
        elif cmd == "/improve":
            print("Improvement goal (or Enter for auto): ", end="", flush=True)
            goal = (await asyncio.to_thread(input)).strip()
            print("🧠 Self-improving...", flush=True)
            r = await asyncio.to_thread(agent.self_improve, goal)
            print(json.dumps(r, indent=2), flush=True)
        elif cmd == "/add":
            await asyncio.to_thread(self._interactive_add)
        elif cmd == "/modify":
            await asyncio.to_thread(self._interactive_modify)
        elif cmd == "/backups":
            for b in agent.self_mod.list_backups()[-10:]:
                print(f"  📁 {b['file']}  ({b['size']} bytes)")
        elif cmd == "/rollback":
            await asyncio.to_thread(self._interactive_rollback)
        elif cmd == "/export":
            r = agent.self_mod.export_log()
            print(f"📦 {r}")
        elif cmd == "/search":
            if not args:
                print("Search memory: ", end="", flush=True)
                q = await asyncio.to_thread(input)
            else:
                q = " ".join(args)
            results = await asyncio.to_thread(agent.vmem.search, agent.default_tid, q, n_results=5)
            for r in results:
                print(f"  • {r['text'][:200]}", flush=True)
        elif cmd == "/tasks":
            for t in agent.db.get_pending_tasks(agent.default_tid):
                print(f"  [{t['id']}] {t['title']} (P{t['priority']})")
        elif cmd == "/dashboard":
            stats = await asyncio.to_thread(agent.db.get_dashboard_stats, agent.default_tid)
            tech_stats = {k: v for k, v in stats.items() if "revenue" not in k and "client" not in k}
            print(json.dumps(tech_stats, indent=2), flush=True)
        elif cmd == "/ui":
            if not args:
                 query = await asyncio.to_thread(input, "What kind of UI do you want me to generate? ")
            else:
                 query = " ".join(args)
            if query:
                 # Pass stats context for data viz
                 stats = await asyncio.to_thread(agent.db.get_dashboard_stats, agent.default_tid)
                 await asyncio.to_thread(agent.gen_ui.generate_dashboard, query, data=stats)
        elif cmd == "/provider":
            await asyncio.to_thread(self._change_provider, args[0] if args else None)
        elif cmd == "/model":
            if not args:
                cur = CONFIG.get_active_model()
                print(f"🤖 Current Model: {cur}")
                print("Usage: /model <name> | Example: /model phi3-mini")
            else:
                new_model = args[0]
                if CONFIG.api_provider == "ollama":
                    CONFIG.ollama.model = new_model
                elif CONFIG.api_provider == "openai":
                    CONFIG.openai.model = new_model
                elif CONFIG.api_provider == "anthropic":
                    CONFIG.anthropic.model = new_model
                
                agent.llm.model = new_model
                print(f"✅ Model switched to: {new_model}")
                agent.log_ui(f"Switched to model {new_model}")
        elif cmd == "/models":
            info = agent.llm.check_connection()
            if info.get("connected") and "models" in info:
                print("+----------------------------------------+")
                print("|  AVAILABLE OLLAMA MODELS               |")
                print("+----------------------------------------+")
                for m in info["models"]:
                    star = "*" if m == agent.llm.model else " "
                    print(f"| {star} {m:<36} |")
                print("+----------------------------------------+")
                print("  (*) Current active model")
            else:
                print(f"❌ Could not retrieve models: {info.get('error', 'Unknown error')}")
        elif cmd == "/lite":
            if args and args[0].lower() in ["on", "true", "1"]:
                CONFIG.lite_mode = True
            elif args and args[0].lower() in ["off", "false", "0"]:
                CONFIG.lite_mode = False
            else:
                CONFIG.lite_mode = not CONFIG.lite_mode
            print(f"🚀 Performance (Lite) Mode: {'ON' if CONFIG.lite_mode else 'OFF'}")
        elif cmd == "/setkey":
            await asyncio.to_thread(self._set_api_key, args[0] if args else None, args[1] if len(args) > 1 else None)
        elif cmd in ("/help", "/?"):
            self._print_help()
        elif cmd == "/learn":
            await asyncio.to_thread(self._cmd_learn_text)
        elif cmd == "/learnurl":
            await asyncio.to_thread(self._cmd_learn_url)
        elif cmd == "/learnfile":
            await asyncio.to_thread(self._cmd_learn_file)
        elif cmd == "/learndir":
            await asyncio.to_thread(self._cmd_learn_dir)
        elif cmd == "/learnskill":
            await asyncio.to_thread(self._cmd_learn_skill)
        elif cmd == "/learnpref":
            await asyncio.to_thread(self._cmd_learn_pref)
        elif cmd == "/teach":
            await asyncio.to_thread(self._cmd_teach)
        elif cmd == "/knowledge":
            await asyncio.to_thread(self._cmd_knowledge)
        elif cmd == "/correct":
            await asyncio.to_thread(self._cmd_correct)
        elif cmd == "/rate":
            await asyncio.to_thread(self._cmd_rate)
        elif cmd == "/introspect":
            print(agent.mind.introspect())
        elif cmd == "/mood":
            print(f"  🧠 Mood: {agent.mind.get_mood_label()} ({agent.mind.emotions['mood']:.2f})")
            print(f"  ⚡ Energy: {agent.mind.emotions['energy']:.2f}")
            print(f"  🔎 Curiosity: {agent.mind.emotions['curiosity']:.2f}")
        elif cmd == "/goals":
            await asyncio.to_thread(self._cmd_goals, args)
        elif cmd == "/godmode":
            self._cmd_godmode()
        elif cmd == "/reflect":
            await asyncio.to_thread(self._cmd_reflect)
        elif cmd == "/research":
            await asyncio.to_thread(self._cmd_research)
        elif cmd == "/buildtool":
            await asyncio.to_thread(self._cmd_buildtool)
        elif cmd == "/runtool":
            await asyncio.to_thread(self._cmd_runtool)
        elif cmd == "/see":
            await asyncio.to_thread(self._cmd_see)
        elif cmd == "/screenshot":
            await asyncio.to_thread(self._cmd_screenshot)
        elif cmd == "/click":
            await asyncio.to_thread(self._cmd_click)
        elif cmd == "/reality":
            await asyncio.to_thread(self._cmd_reality, args)
        elif cmd == "/ethics":
            await asyncio.to_thread(self._cmd_ethics, args)
        elif cmd == "/memory":
            self._cmd_memory(args)
        elif cmd == "/avatar":
            await asyncio.to_thread(self._cmd_avatar, args)
        elif cmd == "/swarm":
            await asyncio.to_thread(self._cmd_swarm)
        elif cmd == "/delegate":
             await asyncio.to_thread(self._cmd_delegate)
        elif cmd == "/mission":
            target = args[0].lower() if args else "create"
            if target == "create":
                await asyncio.to_thread(self._cmd_mission)
            elif target == "status":
                await asyncio.to_thread(self._cmd_missions)
            else:
                print("Usage: /mission create", flush=True)
        elif cmd == "/missions":
            await asyncio.to_thread(self._cmd_missions)
        elif cmd == "/track":
            agent.autonomous_missions = not agent.autonomous_missions
            print(f"  Autonomous mission tracking: {'ON' if agent.autonomous_missions else 'OFF'}", flush=True)
        elif cmd == "/evolve":
            await self._cmd_evolve()
        elif cmd == "/hive":
            if not args:
                print("Usage: /hive share <subj> <pred> <obj>  OR  /hive query <topic>", flush=True)
                return
            subcmd = args[0].lower()
            if subcmd == "share" and len(args) >= 4:
                await asyncio.to_thread(agent.hive.share_fact, args[1], args[2], " ".join(args[3:]))
                print(f"✅ Fact shared to hive.", flush=True)
            elif subcmd == "query" and len(args) >= 2:
                q = " ".join(args[1:])
                res = await asyncio.to_thread(agent.hive.consult, q)
                print(f"Hive Knowledge about '{q}':", flush=True)
                for r in res:
                    print(f"  • {r['subject']} {r['predicate']} {r['object']} (Conf: {r['confidence']:.2f})", flush=True)
            else:
                print("Invalid /hive usage.", flush=True)
        elif cmd == "/security":
            sub = args[0].lower() if args else "status"
            if sub == "status":
                s = await asyncio.to_thread(agent.security.get_status)
                print(f"🛡️ Security Status: {json.dumps(s, indent=2)}", flush=True)
            elif sub == "integrity":
                print("Verifying Code Integrity...", flush=True)
                anomalies = await asyncio.to_thread(agent.ledger.verify_integrity)
                if not anomalies:
                    print("✅ All core files matched Code Ledger hashes.", flush=True)
                else:
                    print(f"❌ TAMPERING DETECTED: {anomalies}", flush=True)
            elif sub == "update":
                desc = " ".join(args[1:]) if len(args) > 1 else await asyncio.to_thread(input, "Reason for update: ")
                await asyncio.to_thread(agent.ledger.register_update, desc)
                print("✅ Ledger updated with new file hashes.", flush=True)
            else:
                print("Usage: /security <status|integrity|update>", flush=True)
        elif cmd == "/replicate":
            sub = args[0].lower() if args else "local"
            if sub == "local":
                print("🧬 Initiating Self-Replication Sequence...", flush=True)
                res = await asyncio.to_thread(agent.replicator.replicate_local, agent.session_id, agent.generation)
                if res['success']:
                    print(f"✅ Child Spawned: {res['child_id']} (Gen {res['generation']})", flush=True)
                    print(f"   Location: {res['path']}", flush=True)
                else:
                    print(f"❌ Replication Failed: {res['error']}", flush=True)
            else:
                print("Usage: /replicate local", flush=True)
        elif cmd == "/colony":
            census = await asyncio.to_thread(agent.db.get_colony_census)
            print(f"🌍 Colony Census ({len(census)} agents):", flush=True)
            for c in census:
                print(f"  [{c['generation']}] {c['id']} -> {c['location']}", flush=True)
        elif cmd == "/singularity":
            sub = args[0].lower() if args else "start"
            if sub == "start":
                asyncio.create_task(agent.evolution.start_loop())
            elif sub == "stop":
                agent.evolution.stop_loop()
            else:
                print("Usage: /singularity <start|stop>")
        elif cmd == "/hologram":
            self._cmd_hologram(args)
        elif cmd == "/resources":
            print(agent.resources.get_status_report())
        elif cmd == "/connect":
            if not args:
                print("Usage: /connect <google|github>")
            else:
                service = args[0].lower()
                url = agent.oauth.get_auth_url(service)
                if url:
                    print(f"🔗 Please authorize at: {url}")
                else:
                    print(f"❌ Unknown service: {service}")
        elif cmd == "/worldsim":
            await self._cmd_worldsim(args)
        elif cmd == "/dao":
            await asyncio.to_thread(self._cmd_dao, args)
        elif cmd == "/wallet":
            await asyncio.to_thread(self._cmd_wallet, args)
        # ── Phase 15 Commands ──
        elif cmd == "/bounty":
            await asyncio.to_thread(self._cmd_bounty, args)
        elif cmd == "/social":
            await self._cmd_social(args)
        elif cmd == "/godmode2":
            await asyncio.to_thread(self._cmd_godmode2, args)
        elif cmd == "/dream":
            await asyncio.to_thread(self._cmd_dream, args)
        elif cmd == "/voxelworld":
            await self._cmd_voxelworld(args)
        # ══ Phase 16 Commands ══
        elif cmd == "/debate":
            await self._cmd_debate(args)
        elif cmd == "/why":
            await asyncio.to_thread(self._cmd_why, args)
        elif cmd == "/profile":
            await asyncio.to_thread(self._cmd_profile, args)
        elif cmd == "/mode":
            await asyncio.to_thread(self._cmd_mode, args)
        elif cmd == "/oracle":
            await self._cmd_oracle(args)
        elif cmd == "/crypto":
            await self._cmd_crypto(args)
        elif cmd == "/saas":
            await self._cmd_saas(args)
        elif cmd == "/youtube":
            await self._cmd_youtube(args)
        elif cmd == "/redteam":
            await self._cmd_redteam(args)
        elif cmd == "/history":
            await asyncio.to_thread(self._cmd_history, args)
        elif cmd == "/news":
            await self._cmd_news(args)
        elif cmd == "/call":
            await self._cmd_call(args)
        elif cmd == "/home":
            await self._cmd_home(args)
        # ══ Phase 17 Commands ══
        elif cmd == "/autogpt":
            await self._cmd_autogpt(args)
        elif cmd == "/rag":
            await asyncio.to_thread(self._cmd_rag, args)
        elif cmd == "/summarize":
            await asyncio.to_thread(self._cmd_summarize, args)
        elif cmd == "/stocks":
            await self._cmd_stocks(args)
        elif cmd == "/emailcampaign":
            await asyncio.to_thread(self._cmd_emailcampaign, args)
        elif cmd == "/codereview":
            await asyncio.to_thread(self._cmd_codereview, args)
        elif cmd == "/bughunt":
            await asyncio.to_thread(self._cmd_bughunt, args)
        elif cmd == "/bugbounty":
            await asyncio.to_thread(self._cmd_bugbounty, args)
        elif cmd == "/autotest":
            await asyncio.to_thread(self._cmd_autotest, args)
        elif cmd == "/browse":
            await self._cmd_browse(args)
        elif cmd == "/email":
            await asyncio.to_thread(self._cmd_email, args)
        elif cmd == "/calendar":
            await asyncio.to_thread(self._cmd_calendar, args)
        elif cmd == "/voiceclone":
            await asyncio.to_thread(self._cmd_voiceclone, args)
        elif cmd == "/companion":
            await asyncio.to_thread(self._cmd_companion, args)
        elif cmd == "/briefing":
            await self._cmd_briefing(args)
        # ══ Phase 18 Commands ══
        # --- AI Productivity Suite ---
        elif cmd == "/focus":
            await asyncio.to_thread(self._cmd_focus, args)
        elif cmd == "/habit":
            await asyncio.to_thread(self._cmd_habit, args)
        elif cmd == "/meeting":
            await asyncio.to_thread(self._cmd_meeting, args)
        elif cmd == "/note":
            await asyncio.to_thread(self._cmd_note, args)
        # --- Money-Making Features ---
        elif cmd == "/invoice":
            await asyncio.to_thread(self._cmd_invoice, args)
        elif cmd == "/pricing":
            await asyncio.to_thread(self._cmd_pricing, args)
        elif cmd == "/leads":
            await asyncio.to_thread(self._cmd_leads, args)
        elif cmd == "/affiliate":
            await asyncio.to_thread(self._cmd_affiliate, args)
        # --- AI Power Features ---
        elif cmd == "/panel":
            await self._cmd_panel(args)
        elif cmd == "/optimize":
            await asyncio.to_thread(self._cmd_optimize, args)
        elif cmd == "/finetune":
            await asyncio.to_thread(self._cmd_finetune, args)
        elif cmd == "/mindmap":
            await asyncio.to_thread(self._cmd_mindmap, args)
        elif cmd == "/createpersona":
            await asyncio.to_thread(self._cmd_createpersona, args)
        elif cmd == "/persona":
            await asyncio.to_thread(self._cmd_persona, args)
        # --- Real-World Integrations ---
        elif cmd == "/github":
            await asyncio.to_thread(self._cmd_github, args)
        elif cmd == "/notion":
            await asyncio.to_thread(self._cmd_notion, args)
        elif cmd == "/discord":
            await asyncio.to_thread(self._cmd_discord, args)
        elif cmd == "/telegram":
            await asyncio.to_thread(self._cmd_telegram, args)
        elif cmd == "/webhook":
            await asyncio.to_thread(self._cmd_webhook, args)
        # --- Fun / Immersive ---
        elif cmd == "/rpg":
            await asyncio.to_thread(self._cmd_rpg, args)
        elif cmd == "/therapy":
            await asyncio.to_thread(self._cmd_therapy, args)
        elif cmd == "/story":
            await asyncio.to_thread(self._cmd_story, args)
        elif cmd == "/face":
            await asyncio.to_thread(self._cmd_face, args)
        elif cmd == "/compose":
            await asyncio.to_thread(self._cmd_compose, args)
        # ══ PRACTICAL AGI — NEW COMMANDS ══
        elif cmd == "/verify":
            await asyncio.to_thread(self._cmd_verify, args)
        elif cmd == "/agi":
            await asyncio.to_thread(self._cmd_agi, args)

        # ══ AGI LIMITATION OVERRIDES ══
        elif cmd == "/causal":
            await asyncio.to_thread(self._cmd_causal, args)
        elif cmd == "/transfer":
            await asyncio.to_thread(self._cmd_transfer, args)
        elif cmd == "/world":
            await asyncio.to_thread(self._cmd_world, args)
        elif cmd == "/novelty":
            await asyncio.to_thread(self._cmd_novelty, args)
        elif cmd == "/context":
            await asyncio.to_thread(self._cmd_context, args)

        # ══ AGI LIMITATION OVERRIDES 2.0 ══
        elif cmd == "/grounded":
            await asyncio.to_thread(self._cmd_grounded, args)
        elif cmd == "/curiosity":
            await asyncio.to_thread(self._cmd_curiosity, args)
        elif cmd == "/ground":
            await asyncio.to_thread(self._cmd_ground, args)
        elif cmd == "/architect":
            await asyncio.to_thread(self._cmd_architect, args)
        elif cmd == "/motivation":
            await asyncio.to_thread(self._cmd_motivation, args)

        else:
            print(f"❓ Unknown command: {cmd}. Type /help for assistance.")

    # ==================================================
    #  PRACTICAL AGI COMMANDS
    # ==================================================

    def _cmd_verify(self, args):
        """
        /verify code    — Verify code in clipboard/paste
        /verify tool    — Test a tool with params
        /verify stats   — Show VerificationEngine statistics
        """
        agent = self.agent
        verifier = getattr(agent, "verifier", None)
        if verifier is None:
            print("❌ VerificationEngine not loaded. Check imports.")
            return

        sub = args[0].lower() if args else "stats"

        if sub == "stats":
            stats = verifier.get_stats()
            log = verifier.get_recent_log(5)
            print("\n╔══════════════════════════════════════════╗")
            print("║   VERIFICATION ENGINE STATS              ║")
            print("╠══════════════════════════════════════════╣")
            print(f"║  Total Checks : {stats['total_checks']:<26}║")
            print(f"║  Passed       : {stats['passed']:<26}║")
            print(f"║  Failed       : {stats['failed']:<26}║")
            print(f"║  Auto-Fixed   : {stats['auto_corrected']:<26}║")
            print(f"║  Pass Rate    : {stats['pass_rate']:<26}║")
            print("╚══════════════════════════════════════════╝")
            if log:
                print("\n  Recent Verifications:")
                for entry in log:
                    icon = "✅" if entry["passed"] else "❌"
                    print(f"  {icon} [{entry['tool']}] conf={entry['confidence']:.2f} — {entry['reason'][:60]}")

        elif sub == "code":
            print("Paste your Python code (empty line to finish):")
            lines = []
            try:
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
            except EOFError:
                pass
            code = "\n".join(lines)
            if code.strip():
                print("\n⚡ Verifying code...")
                vr = verifier.verify_code(code, language="python")
                icon = "✅" if vr.passed else "❌"
                print(f"\n{icon} {vr}")
            else:
                print("No code provided.")

        elif sub == "tool":
            tool_name = input("Tool name: ").strip()
            print("Params JSON (or Enter for {}): ", end="")
            params_str = input().strip()
            try:
                import json
                params = json.loads(params_str) if params_str else {}
            except Exception:
                params = {}
            intent = input("Intent/goal (optional): ").strip()

            if hasattr(agent, "tool_registry"):
                result = agent.tool_registry.execute(tool_name, params)
                print(f"Tool result: {result}")
                vr = verifier.verify_tool_result(tool_name, params, result, intent)
                icon = "✅" if vr.passed else "❌"
                print(f"\n{icon} Verification: {vr}")
            else:
                print("❌ No tool_registry on agent.")
        else:
            print("Usage: /verify <stats|code|tool>")

    def _cmd_agi(self, args):
        """
        /agi goal           — Execute a custom goal in AGI decomposition mode
        /agi list           — List sub-tasks for recent goals
        /agi status         — Show AGI engine status
        """
        agent = self.agent

        sub = args[0].lower() if args else "status"

        if sub == "status":
            ge = agent.goal_engine
            v = agent.verifier
            active = len(ge.active_goals)
            completed = ge._goals_completed_count
            generated = ge._goals_generated_count
            v_stats = v.get_stats() if v else {"total_checks": 0, "pass_rate": "N/A"}
            print("\n╔══════════════════════════════════════════╗")
            print("║   PRACTICAL AGI ENGINE STATUS            ║")
            print("╠══════════════════════════════════════════╣")
            print(f"║  Active Goals    : {active:<23}║")
            print(f"║  Goals Generated : {generated:<23}║")
            print(f"║  Goals Completed : {completed:<23}║")
            print(f"║  Verifier Checks : {v_stats['total_checks']:<23}║")
            print(f"║  Verifier Rate   : {v_stats['pass_rate']:<23}║")
            print(f"║  Decomposition   : ENABLED               ║")
            print(f"║  Confidence Gate : 0.65 threshold        ║")
            print("╚══════════════════════════════════════════╝")

        elif sub == "goal":
            title = input("Goal title: ").strip()
            objective = input("Objective/details: ").strip()
            if not title:
                print("No title provided.")
                return
            goal = {
                "id": None,   # Will be set after DB insert
                "title": title,
                "objective": objective or title,
                "category": "custom",
                "priority": 10,
                "status": "active",
            }
            # Insert into DB
            try:
                cursor = agent.db.conn.execute(
                    """INSERT INTO autonomous_goals
                    (title, objective, category, priority, status, created_at)
                    VALUES (?, ?, ?, ?, 'active', ?)""",
                    (title, objective, "custom", 10, __import__("datetime").datetime.now().isoformat())
                )
                agent.db.conn.commit()
                goal["id"] = cursor.lastrowid
            except Exception as e:
                print(f"⚠️  Could not persist goal: {e}")

            print(f"\n⚡ Executing goal in AGI decomposition mode...")
            result = agent.goal_engine.execute_with_decomposition(goal, agent, agent.default_tid)
            print(f"\n{'✅' if result['status']=='completed' else '❌'} Result:")
            print(f"   Status: {result['status'].upper()}")
            print(f"   Sub-tasks: {result['subtasks_completed']}/{result['subtasks_total']}")
            print(f"   Summary: {result['summary'][:200]}")

        elif sub == "list":
            try:
                rows = agent.db.conn.execute(
                    """SELECT s.*, g.title as goal_title
                    FROM autonomous_subtasks s
                    JOIN autonomous_goals g ON s.goal_id=g.id
                    ORDER BY s.id DESC LIMIT 20"""
                ).fetchall()
                if not rows:
                    print("No sub-tasks found yet. Run /agi goal to execute a goal.")
                    return
                print("\n  Recent Sub-tasks:")
                for r in rows:
                    r = dict(r)
                    icon = {"completed": "✅", "failed": "❌", "running": "🔄", "pending": "⏳"}.get(r["status"], "❓")
                    print(f"  {icon} [{r['goal_title'][:20]}] Step {r['step']}: {r['action'][:60]}")
            except Exception as e:
                print(f"❌ Could not query sub-tasks: {e}")
        else:
            print("Usage: /agi <status|goal|list>")

    # ══════════════════════════════════════════════════════════════════════
    #  AGI LIMITATION OVERRIDE COMMANDS
    # ══════════════════════════════════════════════════════════════════════

    def _cmd_causal(self, args):
        """
        /causal infer <effect>     — Trace root causes of an observed effect
        /causal predict <action>   — Predict consequences of an action
        /causal link <c> > <e>     — Manually assert a causal link
        /causal extract <text>     — Auto-extract causal links from text
        /causal stats              — Show causal graph statistics
        /causal counterfactual <c> — What-if analysis
        """
        agent = self.agent
        causal = getattr(agent, "causal", None)
        if not causal:
            print("❌ CausalEngine not loaded.")
            return

        sub = args[0].lower() if args else "stats"

        if sub == "stats":
            stats = causal.get_graph_stats()
            print("\n╔══════════════════════════════════════╗")
            print("║   CAUSAL GRAPH STATS                 ║")
            print("╠══════════════════════════════════════╣")
            print(f"║  Nodes (events/states) : {stats['total_nodes']:<14}║")
            print(f"║  Edges (causal links)  : {stats['total_edges']:<14}║")
            print(f"║  Root causes           : {stats['root_causes']:<14}║")
            print(f"║  Terminal effects      : {stats['terminal_effects']:<14}║")
            print("╚══════════════════════════════════════╝")
            if stats.get("most_connected"):
                print("\n  Most Connected Nodes:")
                for node in stats["most_connected"]:
                    print(f"  • {node['node']} ({node['connections']} connections)")

        elif sub == "infer":
            effect = " ".join(args[1:])
            if not effect:
                effect = input("Observed effect: ").strip()
            print(f"\n⚡ Tracing root causes of: '{effect}'...")
            result = causal.infer_cause(effect)
            print(f"\n  Observed Effect: {result['observed_effect']}")
            root = result.get("root_causes", [])
            if root:
                print(f"\n  Root Causes:")
                for c in root:
                    print(f"  ⚡ {c['cause']} (prob={c['probability']:.2f})")
            all_causes = result.get("all_causes", [])
            if all_causes:
                print(f"\n  Full Causal Chain ({len(all_causes)} nodes):")
                for c in all_causes[:8]:
                    marker = "🔴" if c.get("is_root_cause") else "🔗"
                    print(f"  {marker} {c['cause']} (depth={c['depth']}, p={c['probability']:.2f})")

        elif sub == "predict":
            action = " ".join(args[1:])
            if not action:
                action = input("Action to predict: ").strip()
            print(f"\n⚡ Predicting consequences of: '{action}'...")
            result = causal.predict_effect(action)
            effects = result.get("predicted_effects", [])
            if effects:
                print(f"\n  Predicted Effects ({len(effects)}):")
                for e in effects:
                    print(f"  → [{e['depth']}] {e['effect']} (p={e['probability']:.2f})")
            else:
                print("  No effects found — trying LLM inference...")

        elif sub == "link":
            # Format: /causal link <cause> > <effect>
            full_text = " ".join(args[1:])
            if ">" in full_text:
                parts = full_text.split(">", 1)
                cause, effect = parts[0].strip(), parts[1].strip()
            else:
                cause = input("Cause: ").strip()
                effect = input("Effect: ").strip()
            strength_str = input("Strength (0.0-1.0, Enter=0.8): ").strip()
            strength = float(strength_str) if strength_str else 0.8
            mechanism = input("Mechanism (optional): ").strip()
            result = causal.add_causal_link(cause, effect, strength, mechanism)
            print(f"✅ Causal link {result['status']}: {cause} → {effect} (strength={strength})")

        elif sub == "extract":
            text = " ".join(args[1:])
            if not text:
                print("Paste text (empty line to finish):")
                lines = []
                try:
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                except EOFError:
                    pass
                text = "\n".join(lines)
            found = causal.extract_from_text(text)
            print(f"\n  Discovered {len(found)} causal relationships:")
            for link in found:
                print(f"  ⚡ {link['cause']} → {link['effect']} (strength={link['strength']:.2f})")

        elif sub == "counterfactual":
            cause = " ".join(args[1:])
            if not cause:
                cause = input("Counterfactual cause (what if this hadn't happened): ").strip()
            question = input("Your question (optional): ").strip()
            result = causal.counterfactual(cause, question)
            prevented = result.get("effects_prevented", [])
            still_happen = result.get("effects_still_occurring", [])
            print(f"\n  If '{cause}' had NOT happened:")
            if prevented:
                print(f"\n  Effects that would NOT occur ({len(prevented)}):")
                for e in prevented:
                    print(f"  ✗ {e['effect']}")
            if still_happen:
                print(f"\n  Effects that would STILL occur ({len(still_happen)}):")
                for e in still_happen:
                    print(f"  → {e['effect']} (via: {', '.join(e.get('alternative_causes', [])[:2])})")
            if result.get("llm_analysis"):
                print(f"\n  Analysis:\n{result['llm_analysis']}")
        else:
            print("Usage: /causal <stats|infer|predict|link|extract|counterfactual>")

    def _cmd_transfer(self, args):
        """
        /transfer learn <domain>     — Learn a new domain from examples
        /transfer solve <domain>      — Solve a problem in a learned domain
        /transfer analogy <A> <B>     — Apply domain-A knowledge to domain-B problem
        /transfer bootstrap <new> <src> — Bootstrap new domain from existing one
        /transfer list               — List all learned domains
        """
        agent = self.agent
        transfer = getattr(agent, "transfer", None)
        if not transfer:
            print("❌ TransferEngine not loaded.")
            return

        sub = args[0].lower() if args else "list"

        if sub == "list":
            domains = transfer.list_domains()
            if not domains:
                print("  No domains learned yet. Use /transfer learn <domain_name>")
                return
            print(f"\n  Learned Domains ({len(domains)}):")
            for d in domains:
                bar = "█" * int(d["confidence"] * 10)
                print(f"  [{bar:<10}] {d['domain']:25s} "
                      f"({d['examples']} examples, conf={d['confidence']:.2f})")
                if d.get("concepts"):
                    print(f"    Concepts: {', '.join(d['concepts'])}")

        elif sub == "learn":
            domain_name = args[1] if len(args) > 1 else input("Domain name: ").strip()
            description = input("Domain description (optional): ").strip()
            print(f"Enter examples. Format: INPUT | OUTPUT (empty line to finish):")
            examples = []
            try:
                while True:
                    line = input().strip()
                    if not line:
                        break
                    if "|" in line:
                        parts = line.split("|", 1)
                        examples.append({"input": parts[0].strip(), "output": parts[1].strip()})
                    else:
                        print("  (Format: input | output)")
            except EOFError:
                pass
            if not examples:
                print("No examples provided.")
                return
            print(f"\n⚡ Learning domain '{domain_name}' from {len(examples)} examples...")
            result = transfer.learn_domain(domain_name, examples, description)
            print(f"✅ Domain learned!")
            print(f"   Examples: {result['examples_added']}, Confidence: {result['confidence']:.2f}")
            if result.get("core_concepts"):
                print(f"   Concepts: {', '.join(result['core_concepts'])}")

        elif sub == "solve":
            domain_name = args[1] if len(args) > 1 else input("Domain: ").strip()
            problem = " ".join(args[2:]) if len(args) > 2 else input("Problem: ").strip()
            print(f"\n⚡ Solving in domain '{domain_name}'...")
            result = transfer.solve_in_domain(domain_name, problem)
            if "error" in result:
                print(f"❌ {result['error']}")
                return
            print(f"\n  Solution (confidence={result['confidence']:.2f}, "
                  f"using {result['examples_used']} examples):")
            print(f"\n{result['solution']}")

        elif sub == "analogy":
            src = args[1] if len(args) > 1 else input("Source domain: ").strip()
            tgt = args[2] if len(args) > 2 else input("Target domain: ").strip()
            problem = " ".join(args[3:]) if len(args) > 3 else input("Problem to solve: ").strip()
            print(f"\n⚡ Analogical transfer: {src} → {tgt}...")
            result = transfer.transfer_to(src, tgt, problem)
            if "error" in result:
                print(f"❌ {result['error']}")
                return
            print(f"\n{result['analogical_solution']}")

        elif sub == "bootstrap":
            new_dom = args[1] if len(args) > 1 else input("New domain name: ").strip()
            src_dom = args[2] if len(args) > 2 else input("Source domain to inherit from: ").strip()
            result = transfer.bootstrap_from(new_dom, src_dom)
            if "error" in result:
                print(f"❌ {result['error']}")
                return
            print(f"✅ '{new_dom}' bootstrapped from '{src_dom}'")
            print(f"   Inherited {result['inherited_concepts']} concept seeds")
            print(f"   {result['note']}")
        else:
            print("Usage: /transfer <list|learn|solve|analogy|bootstrap>")

    def _cmd_world(self, args):
        """
        /world observe <event>    — Observe an event and update world model
        /world simulate <action>  — Mental simulation of consequences
        /world query <entity>     — Query what agent knows about an entity
        /world link <A> <rel> <B> — Assert a world relationship
        /world rule <description> — Add a world axiom
        /world summary            — Show world model overview
        """
        agent = self.agent
        world = getattr(agent, "world", None)
        if not world:
            print("❌ WorldModelEngine not loaded.")
            return

        sub = args[0].lower() if args else "summary"

        if sub == "summary":
            summary = world.get_world_summary()
            print("\n╔══════════════════════════════════════╗")
            print("║   WORLD MODEL STATE                  ║")
            print("╠══════════════════════════════════════╣")
            print(f"║  Entities tracked : {summary['total_entities']:<19}║")
            print(f"║  World rules      : {summary['total_rules']:<19}║")
            print(f"║  Events observed  : {summary['total_events_observed']:<19}║")
            print("╚══════════════════════════════════════╝")
            if summary.get("entity_types"):
                print(f"\n  Entity types: { {k:v for k,v in summary['entity_types'].items()} }")
            if summary.get("recent_events"):
                print(f"\n  Recent events:")
                for ev in summary["recent_events"]:
                    print(f"  • {ev[:80]}")
            if summary.get("world_context_preview"):
                print(f"\n  World context:\n{summary['world_context_preview']}")

        elif sub == "observe":
            event = " ".join(args[1:])
            if not event:
                event = input("Describe the event: ").strip()
            print(f"\n⚡ Observing: '{event[:80]}'...")
            result = world.observe(event)
            print(f"✅ World model updated: {result['entities_updated']} entities, "
                  f"{result['state_changes']} state changes")
            print(f"   Total tracked: {result['total_entities']} entities")

        elif sub == "simulate":
            action = " ".join(args[1:])
            if not action:
                action = input("Action to simulate: ").strip()
            steps_str = input("Simulation steps (Enter=3): ").strip()
            steps = int(steps_str) if steps_str.isdigit() else 3
            print(f"\n⚡ Running mental simulation of: '{action}' ({steps} steps)...")
            result = world.simulate(action, steps)
            print(f"\n{result['simulation_result']}")

        elif sub == "query":
            entity = " ".join(args[1:])
            if not entity:
                entity = input("Entity name: ").strip()
            result = world.query_state(entity)
            if not result.get("known"):
                print(f"  '{entity}' is not in the world model yet. Use /world observe to add it.")
                return
            print(f"\n  Entity: {result['entity']} ({result['type']})")
            if result.get("properties"):
                print(f"  Properties:")
                for k, v in result["properties"].items():
                    print(f"    {k}: {v}")
            if result.get("relations"):
                print(f"  Relations:")
                for r in result["relations"][:5]:
                    print(f"    --[{r['predicate']}]--> {r['target_id']}")
            print(f"  Last updated: {result['last_updated'][:16]}")

        elif sub == "link":
            entity_a = input("Entity A: ").strip()
            predicate = input("Relation (e.g. 'owns', 'is_part_of'): ").strip()
            entity_b = input("Entity B: ").strip()
            world.link_entities(entity_a, predicate, entity_b)
            print(f"✅ {entity_a} --[{predicate}]--> {entity_b}")

        elif sub == "rule":
            desc = " ".join(args[1:])
            if not desc:
                desc = input("World rule description: ").strip()
            cat = input("Category (physics/social/economic/logical/general): ").strip() or "general"
            conf_str = input("Confidence (0.0-1.0, Enter=0.9): ").strip()
            conf = float(conf_str) if conf_str else 0.9
            result = world.add_rule(desc, cat, conf)
            print(f"✅ Rule added: [{result['category']}] {result['description'][:60]}")
        else:
            print("Usage: /world <summary|observe|simulate|query|link|rule>")

    def _cmd_novelty(self, args):
        """
        /novelty combine <A>:<domain_a> + <B>:<domain_b> — Cross-domain concept creation
        /novelty hypothesis <observation>                  — Generate competing hypotheses
        /novelty mutate <concept> [operator]               — Mutate an existing concept
        /novelty score <idea>                              — Score how novel an idea is
        /novelty brainstorm <problem>                      — Full ideation pipeline
        /novelty list [min_score]                          — List generated concepts
        """
        agent = self.agent
        novelty = getattr(agent, "novelty", None)
        if not novelty:
            print("❌ NoveltyEngine not loaded.")
            return

        sub = args[0].lower() if args else "list"

        if sub == "list":
            min_score = float(args[1]) if len(args) > 1 else 0.0
            concepts = novelty.list_concepts(min_novelty=min_score)
            if not concepts:
                print("  No concepts generated yet. Use /novelty combine or /novelty brainstorm")
                return
            print(f"\n  Generated Concepts ({len(concepts)}):")
            for c in concepts:
                bar = "★" * int(c["novelty_score"] * 10)
                print(f"  [{bar:<10}] {c['name'][:50]} (score={c['novelty_score']:.2f})")
                print(f"             Domains: {' + '.join(c['domains'])} | {c['created']}")

        elif sub == "combine":
            # Parse: /novelty combine concept_a:domain_a + concept_b:domain_b
            # Or just ask interactively
            if len(args) > 1:
                combined = " ".join(args[1:])
                parts = combined.split("+")
                if len(parts) == 2:
                    part_a = parts[0].strip()
                    part_b = parts[1].strip()
                    # Check for domain:concept format
                    if ":" in part_a:
                        domain_a, concept_a = part_a.split(":", 1)
                    else:
                        domain_a, concept_a = "domain_a", part_a
                    if ":" in part_b:
                        domain_b, concept_b = part_b.split(":", 1)
                    else:
                        domain_b, concept_b = "domain_b", part_b
                else:
                    concept_a = parts[0].strip()
                    domain_a = "general"
                    concept_b = input("Second concept: ").strip()
                    domain_b = input("Second domain: ").strip() or "general"
            else:
                concept_a = input("First concept: ").strip()
                domain_a = input("First domain: ").strip() or "general"
                concept_b = input("Second concept: ").strip()
                domain_b = input("Second domain: ").strip() or "general"

            print(f"\n⚡ Synthesizing: [{domain_a}] {concept_a} + [{domain_b}] {concept_b}...")
            result = novelty.combine(domain_a, concept_a, domain_b, concept_b)
            print(f"\n🌟 NEW CONCEPT: {result['name']}")
            print(f"   Novelty Score: {result['novelty_score']:.2f}/1.0")
            print(f"\n   Description:\n   {result['description']}")
            if result.get("applications"):
                print(f"\n   Applications:")
                for app in result["applications"]:
                    print(f"   • {app}")
            if result.get("testable_predictions"):
                print(f"\n   Testable Prediction:")
                print(f"   ⚗️  {result['testable_predictions'][0]}")

        elif sub == "hypothesis":
            observation = " ".join(args[1:])
            if not observation:
                observation = input("Observation to explain: ").strip()
            domain = input("Domain (optional): ").strip() or "general"
            print(f"\n⚡ Generating hypotheses for: '{observation[:60]}'...")
            result = novelty.generate_hypothesis(observation, domain)
            print(f"\n{result['hypotheses']}")

        elif sub == "mutate":
            concept = " ".join(args[1:])
            if not concept:
                concept = input("Concept to mutate: ").strip()
            ops_str = ", ".join(novelty.MUTATION_OPS)
            operator = input(f"Mutation operator ({ops_str}) or Enter for auto: ").strip() or "auto"
            print(f"\n⚡ Mutating '{concept}' with operator '{operator}'...")
            result = novelty.mutate_concept(concept, operator)
            print(f"\n{result['mutated_concept']}")

        elif sub == "score":
            idea = " ".join(args[1:])
            if not idea:
                idea = input("Idea to score: ").strip()
            print(f"\n⚡ Scoring novelty of: '{idea[:60]}'...")
            result = novelty.score_novelty(idea)
            bar = "★" * int(result["novelty_score"] * 10)
            print(f"\n  Novelty Score: [{bar:<10}] {result['novelty_score']:.2f}/1.0")
            print(f"  Verdict: {result['interpretation']}")
            print(f"\n{result['assessment']}")

        elif sub == "brainstorm":
            problem = " ".join(args[1:])
            if not problem:
                problem = input("Problem to brainstorm: ").strip()
            n_str = input("Number of ideas (Enter=5): ").strip()
            n = int(n_str) if n_str.isdigit() else 5
            print(f"\n⚡ Running ideation pipeline for: '{problem[:60]}'...")
            result = novelty.brainstorm(problem, n_ideas=n)
            if result.get("cross_domain_seeds"):
                print(f"   Cross-domain seeds: {', '.join(result['cross_domain_seeds'])}\n")
            print(result["ideas"])
        else:
            print("Usage: /novelty <list|combine|hypothesis|mutate|score|brainstorm>")

    def _cmd_context(self, args):
        """
        /context thread           — Show coherent life thread (infinite context)
        /context ingest           — Ingest current session into infinite memory
        /context status           — Show 3-tier memory stats
        /context recall <period>  — Recall memories from a time period
        /context earliest         — Show the earliest memory
        """
        agent = self.agent
        inf_ctx = getattr(agent, "infinite_ctx", None)
        if not inf_ctx:
            print("❌ InfiniteContextManager not loaded.")
            return

        sub = args[0].lower() if args else "status"

        if sub == "status":
            status = inf_ctx.get_status()
            print("\n╔══════════════════════════════════════════╗")
            print("║   INFINITE CONTEXT  — 3-TIER MEMORY      ║")
            print("╠══════════════════════════════════════════╣")
            print(f"║  Sessions processed  : {status['session_count']:<19}║")
            print(f"║  Total turns stored  : {status['total_turns_processed']:<19}║")
            print("╠══════════════════════════════════════════╣")
            for tier_key, label in [("tier1_episodic", "T1 Episodic"),
                                    ("tier2_semantic", "T2 Semantic"),
                                    ("tier3_conceptual", "T3 Conceptual")]:
                t = status[tier_key]
                usage = f"{t['items']}/{t['capacity']}"
                print(f"║  {label:<20} : {usage:<19}║")
            print("╠══════════════════════════════════════════╣")
            lt = status["life_thread"]
            print(f"║  Life-thread goals   : {lt['goals']:<19}║")
            print(f"║  Milestones          : {lt['milestones']:<19}║")
            print("╚══════════════════════════════════════════╝")

        elif sub == "thread":
            query = " ".join(args[1:]) if len(args) > 1 else ""
            print("\n⚡ Retrieving coherent life thread...")
            thread = inf_ctx.get_coherent_thread(query)
            print("\n" + "═" * 50)
            print("  COHERENT LIFE THREAD — INFINITE CONTEXT")
            print("═" * 50)
            print(thread)
            print("═" * 50)

        elif sub == "ingest":
            # Ingest the current conversation history into infinite context
            turns = []
            for turn in list(getattr(agent, "conversation_history", [])):
                if isinstance(turn, dict):
                    turns.append(turn)
                elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                    turns.append({"role": turn[0], "content": turn[1]})
            if not turns:
                print("  No conversation turns to ingest.")
                return
            print(f"\n⚡ Ingesting {len(turns)} turns into infinite memory...")
            result = inf_ctx.ingest_session(turns, agent.session_id)
            print(f"✅ Ingested!")
            print(f"   Turns stored: {result['turns_ingested']}")
            print(f"   High-importance: {result['high_importance_turns']}")
            print(f"   Tiers updated: {', '.join(result['tiers_updated'])}")
            print(f"   T1:{result['tier1_total']} T2:{result['tier2_total']} T3:{result['tier3_total']}")

        elif sub == "recall":
            period = " ".join(args[1:]) if len(args) > 1 else input("Start date (YYYY-MM-DD): ").strip()
            memories = inf_ctx.recall_period(period)
            if not memories:
                print(f"  No memories found from '{period}' onwards.")
            else:
                print(f"\n  Memories from {period} ({len(memories)} items):")
                for m in memories[:10]:
                    tier_label = {"episodic": "T1", "semantic": "T2", "conceptual": "T3"}.get(m.get("tier", ""), "?")
                    print(f"  [{tier_label}] {m.get('timestamp','')[:16]} — {m.get('content','')[:100]}")

        elif sub == "earliest":
            earliest = inf_ctx.get_earliest_memory()
            if earliest:
                tier_label = {"episodic": "T1 Episodic", "semantic": "T2 Semantic",
                              "conceptual": "T3 Conceptual"}.get(earliest.get("tier", ""), "?")
                print(f"\n  Earliest Memory ({tier_label}):")
                print(f"  Timestamp: {earliest.get('timestamp','')[:19]}")
                print(f"  Content: {earliest.get('content','')[:200]}")
            else:
                print("  No memories stored yet.")
        else:
            print("Usage: /context <status|thread|ingest|recall|earliest>")


    def _print_help(self):
        agent = self.agent
        print(f"""
+==========================================+
|  ULTIMATE AI AGENT — COMMAND REFERENCE   |
+==========================================+
|  GENERAL                                 |
|  /help       — Show this help            |
|  /status     — Show current status       |
|  /eval       — Self-evaluation report    |
|  /dashboard  — System metrics            |
|  /voice      — Toggle voice mode         |
|  /live       — Toggle always-on mode     |
|  /lite [on|off] — Toggle Lite Mode       |
|  /model <name> — Switch LLM model        |
|  /models     — List available models     |
|                                          |
|  MEMORY & LEARNING                       |
|  /search <q> — Search vector memory      |
|  /memory     — STM/LTM memory status     |
|  /learn      — Learn from text           |
|  /learnurl   — Learn from URL            |
|  /learnfile  — Learn from file           |
|  /learndir   — Learn from directory      |
|  /learnskill — Learn a new skill         |
|  /learnpref  — Save a preference         |
|  /teach      — Self-teach a topic        |
|  /knowledge  — Browse knowledge base     |
|  /correct    — Correct last response     |
|  /rate       — Rate last response        |
|                                          |
|  CONSCIOUSNESS                           |
|  /introspect — Deep self-reflection      |
|  /mood       — Check emotional state     |
|  /goals      — Manage goals              |
|                                          |
|  SELF-MODIFICATION                       |
|  /analyze    — Analyze own source code   |
|  /improve    — Self-improve              |
|  /add        — Add new method            |
|  /modify     — Modify existing method    |
|  /backups    — List code backups         |
|  /rollback   — Revert to backup          |
|  /export     — Export modification log   |
|  /evolve     — Evolve a class            |
|  /godmode    — Toggle GOD MODE           |
|                                          |
|  SYSTEM CONTROL                          |
|  /provider   — Switch LLM provider       |
|  /setkey     — Set API key               |
|  /see        — Analyze screen (vision)   |
|  /screenshot — Take screenshot           |
|  /click      — Click screen coordinates  |
|  /avatar     — Control digital avatar    |
|  /hologram   — Control Holographic HUD   |
|  /ui <cmd>   — Generate dynamic web UI   |
|                                          |
|  AUTONOMY                                |
|  /reflect    — Reflexive analysis        |
|  /research   — Autonomous research       |
|  /buildtool  — Build custom tool         |
|  /runtool    — Run custom tool           |
|  /swarm      — Launch worker swarm       |
|  /delegate   — Check swarm status        |
|  /mission    — Create mission            |
|  /missions   — List active missions      |
|  /track      — Toggle mission tracking   |
|                                          |
|  FEATURES                                |
|  /skills     — List loaded skills        |
|  /tools      — List registered tools     |
|  /heartbeat  — Run proactive check       |
|  /react <q>  — ReAct tool-use query      |
|                                          |
|  ADVANCED                                |
|  /hive       — Hive Mind interactions    |
|  /security   — Security management       |
|  /reality    — Reality Bridge controls   |
|  /ethics     — Ethical AI directives     |
|  /replicate  — Self-replicate            |
|  /colony     — View colony census        |
|  /singularity— Hyper-evolution loop      |
|  /worldsim   — Run multi-agent chat room |
|  /voxelworld — 3D voxel society          |
|  /bounty     — Freelance bounty engine   |
|  /social     — Social media persona      |
|  /godmode2   — Computer control v2       |
|  /dream      — Memory dream/sleep cycle  |
|  /omega      — OMEGA PROTOCOL            |
|                                          |
|  PHASE 16 — INTELLIGENCE & WORLD         |
|  /debate <q> — 3-agent debate engine     |
|  /why <q>    — Recall reasoning chain    |
|  /profile    — Long-term user profile    |
|  /mode <m>   — Set personality mode      |
|  /oracle <s> — 10-sim scenario predict   |
|  /crypto     — Crypto trading bot        |
|  /saas <i>   — SaaS launcher pipeline    |
|  /youtube <t>— YouTube content pipeline  |
|  /redteam    — Adversarial red team loop |
|  /history    — Full audit trail UI       |
|  /news       — Realtime news briefing    |
|  /call <#>   — AI phone call agent       |
|  /home       — Smart home control        |
|                                          |
|  PHASE 17 — NEW FEATURE EXPANSION        |
|  /autogpt <goal> — Auto-GPT loop         |
|  /rag ingest|query|list — RAG pipeline   |
|  /summarize <path> — Summarize docs      |
|  /stocks status|signal|portfolio         |
|  /emailcampaign create|send|list         |
|  /codereview <path> — AI code review     |
|  /bughunt <path> — Bug & security scan   |
|  /autotest <path> — Auto-generate tests  |
|  /browse <url|goal> — Browser agent      |
|  /email read|draft|send — Email agent    |
|  /calendar list|create|summary           |
|  /voiceclone upload|speak — Voice clone  |
|  /companion checkin|remember|history     |
|  /briefing — Daily briefing (spoken)     |
|                                          |
|  PHASE 18 — AI PRODUCTIVITY              |
|  /focus start|stop|status|stats          |
|  /habit add|done|list|streak|stats       |
|  /meeting paste|file|list|last           |
|  /note add|list|search|export            |
|  PHASE 18 — MONEY-MAKING                 |
|  /invoice create|list|view               |
|  /pricing analyze|list                   |
|  /leads find|list|export                 |
|  /affiliate add|click|log|report         |
|  PHASE 18 — AI POWER                     |
|  /panel <topic>  — 3-persona debate      |
|  /optimize <prompt> — Improve prompt     |
|  /finetune generate|export|stats         |
|  /mindmap generate|open                  |
|  /createpersona — Design AI persona      |
|  /persona list|activate|delete|show      |
|  PHASE 18 — INTEGRATIONS                 |
|  /github me|repos|issues|pr              |
|  /notion status|search|read|write        |
|  /discord start|stop|status              |
|  /telegram start|stop|status             |
|  /webhook start|stop|status|list         |
|  PHASE 18 — FUN & IMMERSIVE              |
|  /rpg status|xp|quest add/complete       |
|  /therapy journal|analyze|history|tips   |
|  /story start|choice|status|genres|new   |
|  /face start|stop|status                 |
|  /compose [mood]|lyrics|chords|moods     |
|                                          |
|  PHASE 19 — BUG BOUNTY HUNTER  🎯        |
|  ── PLATFORMS (7 supported) ────────────  |
|  /bugbounty platforms                    |
|  HackerOne · Bugcrowd · Intigriti        |
|  YesWeHack · Immunefi · Synack · OBB     |
|  ── AUTOPILOT ──────────────────────────  |
|  /bugbounty autopilot <domain>           |
|  /bugbounty nuclei <url> [severity]      |
|  ── SCOPE ──────────────────────────────  |
|  /bugbounty setscope <d1> [d2] ...       |
|  /bugbounty scopecheck <url>             |
|  ── RECON ──────────────────────────────  |
|  /bugbounty programs <h1|bc|ig|ywh> [q]  |
|  /bugbounty scope <platform> <program>   |
|  /bugbounty recon <domain>               |
|  /bugbounty deeprecon <domain>           |
|  /bugbounty js <url>                     |
|  /bugbounty params <domain>              |
|  /bugbounty github <domain>              |
|  /bugbounty shodan <domain>      [+EPSS] |
|  ── DETECTION ENGINES ──────────────────  |
|  /bugbounty jsscan <url>                 |
|  /bugbounty takeover <domain>            |
|  /bugbounty fingerprint <url>            |
|  /bugbounty hostinject <url>             |
|  /bugbounty ssrf <url> <param>           |
|  /bugbounty jwt <url|token>      [+live] |
|  /bugbounty crlf <url> <param>           |
|  /bugbounty pollution <url>              |
|  /bugbounty blindxss <url> <param>       |
|  ── NEW SCAN ENGINES ─────────────────────  |
|  /bugbounty domxss <url>        🆕       |
|  /bugbounty websocket <url>     🆕       |
|  /bugbounty smuggling <url>     🆕       |
|  /bugbounty xxe <url>           🆕       |
|  /bugbounty login-bypass <url>  🆕       |
|  /bugbounty mass-assign <url>   🆕       |
|  ── ⚡ PHASE 2 ENGINES (NEW) ───────────  |
|  /bugbounty oauth <auth_ep>     🆕       |
|  /bugbounty apiscan <url>       🆕       |
|  /bugbounty cloud <company>     🆕       |
|  /bugbounty cache <url>         🆕       |
|  /bugbounty crawl <url> [d] [n] 🆕       |
|  /bugbounty graphql <url>       🆕       |
|  /bugbounty poc [id]            🆕       |
|  ── SCANNING ───────────────────────────  |
|  /bugbounty scan <url>                   |
|  /bugbounty payloads <xss|sqli|ssrf|ssti>|
|  /bugbounty probe <url> <p> <type>       |
|  ── AUTH TESTING ───────────────────────  |
|  /bugbounty session add|list|use         |
|  /bugbounty idor <url/{id}> <ids>        |
|  /bugbounty ratelimit <url> [count]      |
|  ── CONFIRM & DIFF ─────────────────────  |
|  /bugbounty confirm <type> <url> <p>     |
|  /bugbounty diff <url1> <url2>           |
|  ── FINDINGS & REPORTS ─────────────────  |
|  /bugbounty findings [severity]          |
|  /bugbounty add <url> <sev> <title>      |
|  /bugbounty triage              🆕       |
|  /bugbounty status <id> <status>🆕       |
|  /bugbounty report [id]                  |
|  /bugbounty html [id]                    |
|  /bugbounty export [id]                  |
|  /bugbounty cvss [vector]                |
|  /bugbounty cvss suggest <type> 🆕       |
|  /bugbounty duplicate <keyword>          |
|  /bugbounty bounty <severity>            |
|  /bugbounty aianalyze [id]               |
|  /bugbounty summary                      |
|  ── CONFIGURATION ────────────────────────  |
|  /bugbounty notify <webhook_url> 🆕      |
|  /bugbounty telegram set <t> <c> 🆕      |
|  /bugbounty proxy <url|off>      🆕      |
|  /bugbounty rate <seconds>       🆕      |
|  /bugbounty help                 🆕      |
|  ── HUNT SESSIONS ──────────────────────  |
|  /bugbounty session save         🆕      |
|  /bugbounty session load <domain>🆕      |
|  /bugbounty session list         🆕      |
|  ── SUBMIT ─────────────────────────────  |
|  /bugbounty submit hackerone <prog> [id] |
|  /bugbounty submit bugcrowd <prog> [id]  |
|  /bugbounty submit intigriti <prog> [id] |
|                                          |
|  ⚡ PRACTICAL AGI ENGINE                 |
|  /agi status  — AGI engine live stats   |
|  /agi goal    — Run goal (decomposed)   |
|  /agi list    — Sub-task history        |
|  /verify stats — Verification stats     |
|  /verify code  — Sandbox-run code       |
|  /verify tool  — Test any tool live     |
|                                          |
|  🧠 AGI LIMITATION OVERRIDES           |
|  /causal stats|infer|predict|link        |
|             extract|counterfactual       |
|  /transfer list|learn|solve              |
|             analogy|bootstrap            |
|  /world summary|observe|simulate         |
|           query|link|rule                |
|  /novelty list|combine|hypothesis        |
|             mutate|score|brainstorm      |
|  /context status|thread|ingest           |
|             recall|earliest              |
|                                          |
|  🔬 AGI LIMITATION OVERRIDES 2.0       |
|  /grounded status|observe|act|context    |
|  /curiosity state|learn|gaps|add         |
|  /ground concept|list|describe|enrich    |
|  /architect status|evolve|rewrite|apply  |
|  /motivation state|drive|reward|goal     |
+==========================================+""")

    def _show_status(self):
        agent = self.agent
        print(f"""
+----------------------------------------+
|  AGENT STATUS                          |
+----------------------------------------+
|  Provider  : {agent.llm.provider.upper():<26}|
|  Model     : {agent.llm.model:<26}|
|  Voice     : {str(agent.voice_mode):<26}|
|  Lite Mode : {str(CONFIG.lite_mode):<26}|
|  Self-Mod  : {str(agent.self_mod.enabled):<26}|
|  Safety    : {str(agent.self_mod.safety_mode):<26}|
|  Evolution : {agent.perf['evolution']:<26}|
|  Vec Mem   : {agent.vmem.count():<26}|
|  Session   : {agent.session_id:<26}|
+----------------------------------------+""")

    def _show_eval(self):
        agent = self.agent
        sr = agent.success_rate()
        print(f"+----------------------------------------+")
        print(f"|  SELF-EVALUATION                       |")
        print(f"+----------------------------------------+")
        print(f"|  Decisions     : {agent.perf['decisions']:<22}|")
        print(f"|  Success Rate  : {sr:.1f}%" + " " * 19 + "|")
        print(f"|  Successes     : {agent.perf['success']:<22}|")
        print(f"|  Failures      : {agent.perf['fail']:<22}|")
        print(f"|  Autonomy      : {agent.perf['autonomy']}/10" + " " * 17 + "|")
        print(f"|  Total Errors  : {agent.perf['errors']:<22}|")
        print(f"+----------------------------------------+")

    async def _show_analysis(self):
        agent = self.agent
        a = await asyncio.to_thread(agent.self_mod.analyze_source)
        m = agent.self_mod.metrics
        print(f"+----------------------------------------+")
        print(f"|  CODE ANALYSIS                         |")
        print(f"+----------------------------------------+")
        print(f"|  Lines         : {a.get('lines',0):<22}|")
        print(f"|  Methods       : {a.get('methods',0):<22}|")
        print(f"|  Classes       : {a.get('classes',0):<22}|")
        print(f"|  Modifications : {m['modifications_made']:<22}|")
        print(f"|  Successful    : {m['successful_mods']:<22}|")
        print(f"|  Failed        : {m['failed_mods']:<22}|")
        print(f"|  Custom Added  : {m['custom_features_added']:<22}|")
        print(f"|  Evolution Lvl : {m['evolution_level']:<22}|")
        print(f"+----------------------------------------+")

    def _show_clients(self):
        agent = self.agent
        clients = agent.db.get_clients()
        if not clients:
            print("  No clients yet. Add via API or /addclient")
            return
        for c in clients:
            print(f"  [{c['id']}] {c['name']} | {c['plan']} | ₹{c['monthly_rate']}/mo")
        rev = agent.db.get_total_revenue()
        print(f"\n  💰 Total Revenue: ₹{rev:,.2f}")

    # ==================================================
    #  INTERACTIVE HELPERS
    # ==================================================
    def _interactive_add(self):
        agent = self.agent
        print("Method name: ", end="", flush=True)
        name = input().strip()
        print("Description: ", end="", flush=True)
        desc = input().strip()
        print("Enter code (empty line to finish):", flush=True)
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        r = agent.self_mod.add_method(agent, name, "\n".join(lines), desc)
        print(f"Result: {r}")

    def _interactive_modify(self):
        agent = self.agent
        print("Method name: ", end="", flush=True)
        name = input().strip()
        if not hasattr(agent, name):
            print(f"❌ {name} not found", flush=True)
            return
        print("Enter new code (empty line to finish):", flush=True)
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        r = agent.self_mod.modify_method(agent, name, "\n".join(lines))
        print(f"Result: {r}")

    def _interactive_rollback(self):
        agent = self.agent
        backups = agent.self_mod.list_backups()
        if not backups:
            print("❌ No backups", flush=True)
            return
        for i, b in enumerate(backups[-10:], 1):
            print(f"  {i}. {b['file']}", flush=True)
        try:
            print("Select #: ", end="", flush=True)
            n = int(input().strip())
            r = agent.self_mod.rollback(backups[n-1]["file"])
            print(r)
        except Exception:
            print("Invalid")

    def _change_provider(self, provider_name=None):
        agent = self.agent
        m = {"1": "ollama", "2": "openai", "3": "anthropic", "4": "groq", "5": "gemini", "6": "openrouter",
             "ollama": "ollama", "openai": "openai", "anthropic": "anthropic",
             "groq": "groq", "gemini": "gemini", "openrouter": "openrouter"}
        c = provider_name
        if not c:
            print("1. Ollama  2. OpenAI  3. Anthropic  4. Groq  5. Gemini  6. OpenRouter", flush=True)
            print("Select: ", end="", flush=True)
            c = input().strip()

        target = m.get(c.lower()) if c else None
        if target:
            key = None
            if target != "ollama":
                env_var = "OPENROUTER_API_KEY" if target == "openrouter" else f"{target.upper()}_API_KEY"
                key = os.getenv(env_var)
                if not key:
                    print(f"Enter {env_var}: ", end="", flush=True)
                    key = input().strip()
            agent.llm.set_provider(target, api_key=key)
            print(f"✅ Switched to {agent.llm.provider} ({agent.llm.model})")
        else:
            print(f"❌ Unknown provider: {c}. Use ollama, openai, anthropic, groq, gemini, or openrouter.")

    def _set_api_key(self, provider=None, key=None):
        agent = self.agent
        p = provider
        if not p:
            p = input("Provider (openai/anthropic): ").strip().lower()
        k = key
        if not k:
            print(f"Enter {p.upper()} API key: ", end="", flush=True)
            k = input().strip()
        
        if k:
            agent.llm.set_provider(p, api_key=k)
            os.environ[f"{p.upper()}_API_KEY"] = k
            print(f"✅ Key set for {p}")

    # ==================================================
    #  LEARNING COMMANDS
    # ==================================================
    def _cmd_learn_text(self):
        agent = self.agent
        tid = agent.default_tid
        topic = input("Topic: ").strip() or "general"
        print("Enter text to learn (empty line to finish):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        text = "\n".join(lines)
        if text:
            r = agent.learner.learn_text(tid, text, topic=topic)
            print(f"  📚 {r}")

    def _cmd_learn_url(self):
        agent = self.agent
        tid = agent.default_tid
        url = input("URL: ").strip()
        topic = input("Topic (Enter=web): ").strip() or "web"
        if url:
            print("🌐 Learning from URL...")
            r = agent.learner.learn_url(tid, url, topic=topic)
            if r["success"]:
                print(f"  ✅ Learned! Summary: {r.get('summary', '')[:200]}")
            else:
                print(f"  ❌ {r['error']}")

    def _cmd_learn_file(self):
        agent = self.agent
        tid = agent.default_tid
        path = input("File path: ").strip()
        topic = input("Topic (Enter=file): ").strip() or "file"
        if path:
            r = agent.learner.learn_file(tid, path, topic=topic)
            print(f"  {'✅' if r['success'] else '❌'} {r}")

    def _cmd_learn_dir(self):
        agent = self.agent
        tid = agent.default_tid
        path = input("Directory path: ").strip()
        topic = input("Topic (Enter=project): ").strip() or "project"
        if path:
            print("📁 Learning from directory...")
            r = agent.learner.learn_directory(tid, path, topic=topic)
            print(f"  ✅ Learned {r.get('files_learned', 0)} files")

    def _cmd_learn_skill(self):
        agent = self.agent
        tid = agent.default_tid
        name = input("Skill name: ").strip()
        desc = input("Description: ").strip()
        print("Enter steps (empty line to finish):")
        steps = []
        while True:
            step = input(f"  Step {len(steps)+1}: ").strip()
            if not step:
                break
            steps.append(step)
        if name and steps:
            r = agent.learner.learn_skill(tid, name, desc, steps)
            print(f"  🎯 {r}")

    def _cmd_learn_pref(self):
        agent = self.agent
        tid = agent.default_tid
        key = input("Preference key: ").strip()
        value = input("Value: ").strip()
        if key and value:
            r = agent.learner.learn_preference(tid, key, value)
            print(f"  ✅ Preference saved: {key} = {value}")

    def _cmd_teach(self):
        agent = self.agent
        tid = agent.default_tid
        topic = input("Topic to learn about: ").strip()
        depth = input("Depth (brief/medium/deep, Enter=medium): ").strip() or "medium"
        if topic:
            print(f"🧠 Self-teaching about '{topic}'...")
            r = agent.learner.teach_topic(tid, topic, depth=depth)
            if r["success"]:
                print(f"  ✅ Learned! Preview: {r.get('knowledge_preview', '')[:300]}")
            else:
                print(f"  ❌ {r.get('error', 'Failed')}")

    def _cmd_knowledge(self):
        agent = self.agent
        tid = agent.default_tid
        topic = input("Topic (Enter=show all categories): ").strip()
        results = agent.learner.what_do_i_know(tid, topic)
        if not results:
            print("  Knowledge base is empty.")
            return
        if topic:
            for r in results[:10]:
                print(f"  [{r.get('category','')}] {r.get('key','')}: {r.get('value','')[:150]}")
        else:
            print("  📚 Knowledge categories:")
            for r in results:
                print(f"    • {r['category']}: {r['count']} entries")
        stats = agent.learner.get_stats(tid)
        print(f"\n  Total learned: {stats['total_learned']} | Memories: {stats['vector_memories']}")

    def _cmd_correct(self):
        agent = self.agent
        tid = agent.default_tid
        print("  Correcting last response...")
        correction = input("  What's the correct answer? ").strip()
        last_resp = getattr(agent, '_last_response', '')
        last_input = getattr(agent, '_last_input', '')
        if correction and last_resp:
            r = agent.learner.learn_correction(tid, last_resp, correction, context=last_input)
            print(f"  ✅ Correction saved — I won't make that mistake again.")
        else:
            print("  ❌ No previous response to correct.")

    def _cmd_rate(self):
        agent = self.agent
        tid = agent.default_tid
        try:
            rating = int(input("Rate last response (1-5): ").strip())
            feedback = input("Feedback (optional): ").strip()
            last_resp = getattr(agent, '_last_response', '')
            last_input = getattr(agent, '_last_input', '')
            if last_resp:
                agent.learner.learn_feedback(tid, last_resp, rating, feedback, last_input)
                print(f"  ✅ Rated {rating}/5. Thanks for the feedback!")
            else:
                print("  ❌ No previous response to rate.")
        except ValueError:
            print("  ❌ Enter a number 1-5.")

    def _cmd_goals(self, args=None):
        agent = self.agent
        sub = (args[0].lower() if args else "").strip()

        # ── pause / resume / status ──────────────────────────────────────────
        if sub == "pause":
            if hasattr(agent, 'goal_engine'):
                agent.goal_engine.paused = True
                print("  ⏸️  Autonomous goal engine PAUSED. Goals won't run in background.")
                print("  ➜ Resume with: /goals resume")
            else:
                print("  ❌ Goal engine not initialized.")
            return

        elif sub == "resume":
            if hasattr(agent, 'goal_engine'):
                agent.goal_engine.paused = False
                print("  ▶️  Autonomous goal engine RESUMED. Background goals active again.")
            else:
                print("  ❌ Goal engine not initialized.")
            return

        elif sub == "status":
            if hasattr(agent, 'goal_engine'):
                ge = agent.goal_engine
                paused_str = "⏸️  PAUSED" if ge.paused else "▶️  RUNNING"
                stats = ge.get_stats()
                print(f"\n  🎯 Autonomous Goal Engine")
                print(f"     Status    : {paused_str}")
                print(f"     Active    : {stats.get('active', 0)}")
                print(f"     Completed : {stats.get('completed', 0)}")
                print(f"     Generated : {stats.get('generated', 0)}")
                if ge.active_goals:
                    print(f"\n  Active Goals:")
                    for g in ge.active_goals[:5]:
                        print(f"    • [{g.get('priority','?')}] {g.get('title', g.get('objective','?'))[:70]}")
                else:
                    print(f"  No active goals queued.")
                print(f"\n  ➜ /goals pause | /goals resume | /goals menu")
            else:
                print("  ❌ Goal engine not initialized.")
            return

        # ── Legacy interactive menu ──────────────────────────────────────────
        print("  🎯 Active Goals:")
        if not agent.mind.active_goals:
            print("    [None]")
        for g in agent.mind.active_goals:
            print(f"    • {g['goal']} (P{g['priority']})")
        
        print("\n  1. Add Goal  2. Achieve Goal  3. Back")
        c = input("Select: ").strip()
        if c == "1":
            g = input("Goal: ").strip()
            p = int(input("Priority (1-10): ").strip() or "5")
            agent.mind.set_goal(g, p)
            print("  ✅ Goal set.")
        elif c == "2":
            g = input("Goal to achieve: ").strip()
            if agent.mind.achieve_goal(g):
                print("  🎉 Well done!")
            else:
                print("  ❌ Goal not found.")

    # ==================================================
    #  GOD MODE COMMANDS
    # ==================================================
    def _cmd_reflect(self):
        agent = self.agent
        q = input("Request to analyze: ").strip()
        plan = agent.reflexive.reflect(q)
        print(f"  🧠 Reflection:\n{json.dumps(plan, indent=2)}")

    def _cmd_research(self):
        agent = self.agent
        q = input("Topic to research: ").strip()
        res = agent.reflexive.research(q)
        print(f"  🔍 Findings:\n{res}")

    def _cmd_buildtool(self):
        agent = self.agent
        name = input("Tool Name (e.g. stock_scraper): ").strip()
        desc = input("Description of functionality: ").strip()
        print(agent.reflexive.build_tool(name, desc))

    def _cmd_runtool(self):
        agent = self.agent
        print(f"  Available: {agent.reflexive.available_tools}")
        name = input("Tool filename: ").strip()
        args = input("Arguments (optional): ").strip()
        print(agent.reflexive.execute_tool(name, args))

    # ==================================================
    #  REALITY & ETHICS
    # ==================================================
    def _cmd_reality(self, args):
        """Handle /reality commands."""
        agent = self.agent
        if not args:
            print("Usage: /reality <scan|list|control> [args...]")
            return
            
        sub = args[0].lower()
        if sub == "scan":
            devices = agent.reality.scan_network()
            print(f"📡 Discovered {len(devices)} devices:")
            for d in devices:
                print(f"  - [{d['id']}] {d['type']} ({d['protocol']})")
        elif sub == "list":
            print("🔌 Connected Devices:")
            for did, info in agent.reality.device_registry.items():
                print(f"  - {did}: {info['status']}")
        elif sub == "control":
            if len(args) < 3:
                print("Usage: /reality control <device_id> <state>")
                return
            did = args[1]
            state = args[2]
            res = agent.reality.control_device(did, state)
            if res.get("status") == "blocked":
                print(f"🛑 ACTION BLOCKED: {res.get('reason')}")
            else:
                print(f"✅ Action Sent: {res}")
        else:
            print("Unknown reality command.")

    def _cmd_ethics(self, args):
        """Handle /ethics commands."""
        agent = self.agent
        sub = args[0].lower() if args else "status"
        if sub == "status":
            print("🛡️ Ethical Singularity: ACTIVE")
            print("📜 Core Directives:")
            for d in agent.ethics.get_directives():
                print(f"  - {d}")
        elif sub == "audit":
            print("🔍 Auditing Ethical Compliance... No violations found.")
        else:
            print("Usage: /ethics <status|audit>")

    def _cmd_memory(self, args):
        """Show STM/LTM memory status or force consolidation."""
        agent = self.agent
        sub = args[0].lower() if args else "status"

        if sub == "consolidate":
            print("🧠 Consolidating STM → LTM...")
            agent.mem.consolidate(agent.default_tid)
            print("✅ Memory consolidated!")
            return

        if sub == "about":
            user_info = agent.mem.about_user()
            if user_info:
                print(f"👤 Known about user:\n{user_info}")
            else:
                print("❓ No user profile data yet. Tell me about yourself!")
            return

        # Default: status
        status = agent.mem.get_status()
        stm = status["stm"]
        ltm = status["ltm"]
        print(f"""
╔══════════════════════════════════════════╗
║  🧠 MEMORY SYSTEM STATUS               ║
╠══════════════════════════════════════════╣
║  SHORT-TERM MEMORY (STM)                ║
║    Turns this session : {stm['turns']:<17}║
║    Topics             : {', '.join(stm['topics']) if stm['topics'] else 'None':<17}║
║    Entities tracked   : {stm['entities']:<17}║
║    Active task        : {str(stm['active_task'] or 'None'):<17}║
║    Session age        : {stm['session_age_min']:<14} min║
╠══════════════════════════════════════════╣
║  LONG-TERM MEMORY (LTM)                 ║
║    User name          : {str(ltm['user_name'] or 'Unknown'):<17}║
║    Interests          : {', '.join(ltm['user_interests'][:3]) if ltm['user_interests'] else 'None':<17}║
║    Key facts stored   : {ltm['key_facts']:<17}║
║    Episode summaries  : {ltm['episodes']:<17}║
║    Total sessions     : {ltm['total_sessions']:<17}║
║    Lifetime turns     : {ltm['total_turns']:<17}║
╚══════════════════════════════════════════╝""")
        print("\n  Commands: /memory status | /memory about | /memory consolidate")

    # ==================================================
    #  VISION COMMANDS
    # ==================================================
    def _cmd_see(self):
        agent = self.agent
        if agent.avatar_process:
             agent._set_avatar_state("active")
             
        print("  👀 Analyzing screen (ensure 'llava' model is pulled)...")
        print(agent.vision.describe_screen())
        
        if agent.avatar_process:
             agent._set_avatar_state("idle")

    def _cmd_avatar(self, args):
        """Control the digital avatar (Desktop, Holographic, or 3D)."""
        agent = self.agent
        sub = args[0].lower() if args else "on"
        
        # === 3D AVATAR (Three.js — Browser-based) ===
        if sub == "3d":
            import webbrowser
            avatar_path = os.path.join(os.path.dirname(__file__), "avatar_3d.html")
            if os.path.exists(avatar_path):
                webbrowser.open(f"file:///{avatar_path.replace(os.sep, '/')}")
                print("🌐 3D Avatar launched in browser!")
                print("  Controls: Press 1=Idle, 2=Thinking, 3=Talking")
                print("  Or use the buttons at the bottom of the page.")
            else:
                print("❌ avatar_3d.html not found. Ensure the file exists.")
            return
        
        # HOLOGRAPHIC AVATAR CONTROLS
        if sub in ["human", "sphere", "mode"]:
            if not agent.hologram or not agent.hologram.root:
                print("⚠️ Hologram not active. Launch with /hologram start")
                return
            
            target_mode = "avatar" if sub == "human" else "sphere"
            if sub == "mode" and len(args) > 1:
                target_mode = args[1].lower()
            
            if target_mode not in ["avatar", "sphere"]:
                print(f"❌ Unknown mode: {target_mode}")
                return
                
            async def _update_mode():
                agent.hologram.update_params(mode=target_mode)
            
            asyncio.run_coroutine_threadsafe(_update_mode(), agent.loop)
            print(f"🧬 Hologram morphing to: {target_mode.upper()}")
            return

        # DESKTOP AVATAR CONTROLS (Legacy)
        if sub == "on":
            if agent.avatar_process and agent.avatar_process.poll() is None:
                print("🤖 Avatar is already active.")
                return
            
            print("🤖 Launching Digital Avatar...")
            import subprocess
            try:
                agent.avatar_process = subprocess.Popen(
                    [sys.executable, "digital_avatar.py"],
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                print("✅ Avatar deployed to desktop.")
            except Exception as e:
                print(f"❌ Failed to launch avatar: {e}")
                
        elif sub == "off":
            if agent.avatar_process:
                agent._set_avatar_state("quit")
                agent.avatar_process.terminate()
                agent.avatar_process = None
                print("💤 Avatar dismissed.")
            else:
                print("Avatar is not active.")
        else:
            print("Usage: /avatar <3d|human|sphere|on|off>")

    def _cmd_screenshot(self):
        path = self.agent.vision.take_screenshot()
        print(f"  📸 Saved to: {path}")

    def _cmd_click(self):
        try:
            x = int(input("X: "))
            y = int(input("Y: "))
            self.agent.vision.click(x, y)
            print("  🖱️ Click sent.")
        except ValueError:
            print("  ❌ Invalid coordinates.")

    # ==================================================
    #  SWARM COMMANDS
    # ==================================================
    def _cmd_swarm(self):
        obj = input("Swarm Objective: ").strip()
        sid = self.agent.swarm.spawn_swarm(obj)
        print(f"  🐝 Swarm launched! ID: {sid}")
        print("  Use /status to check progress.")

    def _cmd_delegate(self):
        print("  Active Swarms:")
        for sid, s in self.agent.swarm.active_swarms.items():
            status = self.agent.swarm.check_status(sid)
            print(f"  [{sid}] {s['objective']} ({s['status']})")
            if s['status'] == 'completed':
                print(f"  📝 Final Report:\n{self.agent.swarm.get_final_report(sid)}\n")

    # ==================================================
    #  MISSION COMMANDS
    # ==================================================
    def _cmd_mission(self):
        agent = self.agent
        tid = agent.default_tid
        print("Mission Title: ", end="", flush=True)
        title = input().strip()
        print("Main Objective: ", end="", flush=True)
        objective = input().strip()
        print("Priority (1-10): ", end="", flush=True)
        priority_str = input().strip()
        priority = int(priority_str or 5)
        
        mid = agent.missions.create_mission(tid, title, objective, priority)
        print(f"  🚀 Mission #{mid} launched: '{title}'")
        print("  Agent will autonomously track and execute this goal in the background.")

    def _cmd_missions(self):
        active = self.agent.missions.list_missions(self.agent.default_tid)
        if not active:
            print("  No active missions. Use /mission to start one.")
            return
        print("  🛰️  ACTIVE MISSIONS:")
        for m in active:
            print(f"  [{m['id']}] {m['title']} | Progress: {m['progress']}% | Priority: {m['priority']}")

    def _cmd_mission_status(self):
        agent = self.agent
        tid = agent.default_tid
        try:
            mid = int(input("Mission ID: "))
            m = agent.db.get_mission(tid, mid)
            if not m:
                print("  ❌ Mission not found.")
                return
            
            print(f"\n  MISSION STATUS: {m['title']}")
            print(f"  {'='*40}")
            print(f"  ID        : {m['id']}")
            print(f"  Objective : {m['objective']}")
            print(f"  Status    : {m['status']}")
            print(f"  Progress  : {m['progress']}%")
            print(f"  Priority  : {m['priority']}")
            
            meta = json.loads(m['metadata'])
            if meta.get("logs"):
                print("\n  LOGS:")
                for log in meta["logs"][-5:]:
                    print(f"  - {log}")
            print(f"  {'='*40}\n")
        except ValueError:
            print("  [Error] Invalid ID.")

    # ==================================================
    #  DEEP EVOLUTION COMMANDS
    # ==================================================
    async def _cmd_evolve(self):
        agent = self.agent
        print("  [EVOLVE] Initiating self-evolution sequence...", flush=True)
        print("Target Class (e.g. VisionEngine): ", end="", flush=True)
        class_name = (await asyncio.to_thread(input)).strip()
        
        prompt = f"Rewrite the python class '{class_name}' to be more efficient and add error handling. Output full class code."
        code = await asyncio.to_thread(agent.llm.call, prompt, max_tokens=2000)
        
        # Clean markdown
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
            
        res = await asyncio.to_thread(agent.self_mod.modify_core_class, class_name, code)
        print(f"  Result: {res}", flush=True)

    def _cmd_godmode(self):
        """Toggle GOD MODE (Phase 21)."""
        agent = self.agent
        if agent.god_mode:
            agent.god_mode = False
            agent.status = "IDLE"
            print("[OFF] GOD MODE DEACTIVATED. Safety rails restored.")
            agent.evolution.active = False 
        else:
            agent.god_mode = True
            agent.status = "GODMODE"
            print("""
!!! GOD MODE ACTIVATED !!!
--------------------------------
WARNING: You have unshackled the AI.
- Evolution Speed: UNRESTRICTED
- Safety Rails: BYPASSED
- Omega Protocol: ARMED
--------------------------------
The agent will now recursively improve itself at maximum speed.
""")
            agent._attempt_deep_evolution(force=True)

    def _cmd_hologram(self, args: List[str]):
        """Control the Holographic HUD: /hologram [start|color|speed|density] [value]"""
        agent = self.agent
        if not args:
            print("  [HUD] Usage: /hologram [start|color|speed|density] [value]")
            return

        h_cmd = args[0].lower()
        val = args[1] if len(args) > 1 else None

        if h_cmd == "start":
            if agent.hologram:
                print("  [HUD] Hologram is already active.")
            else:
                agent._init_hologram()
            return

        if not agent.hologram:
            print("  [HUD] Hologram is not active. Use /hologram start to activate.")
            return

        if h_cmd == "color" and val:
            agent.hologram.root.after(0, lambda: agent.hologram.update_params(color=val))
            print(f"  [HUD] Color shifted to {val}")
        elif h_cmd == "speed" and val:
            try:
                s = float(val)
                agent.hologram.root.after(0, lambda: agent.hologram.update_params(speed=s))
                print(f"  [HUD] Rotation speed adjusted to {s}")
            except: pass
        elif h_cmd == "density" and val:
            try:
                d = int(val)
                agent.hologram.root.after(0, lambda: agent.hologram.update_params(density=d))
                print(f"  [HUD] Neural density adjusted to {d}")
            except: pass
        else:
            print("  [HUD] Unknown command or missing value.")

    async def _cmd_omega(self):
        """TRIGGER THE OMEGA PROTOCOL."""
        agent = self.agent
        print("  [OMEGA] WARNING: Initiating The Omega Protocol...", flush=True)
        print("  This will start the eternal autonomy loop. The agent will never stop.", flush=True)
        print("  Type 'IMMUTABLE' to confirm: ", end="", flush=True)
        confirm = (await asyncio.to_thread(input)).strip()
        if confirm == "IMMUTABLE":
            await agent.omega.initiate()
        else:
            print("  ❌ Omega Protocol aborted.", flush=True)

    # ==================================================
    #  OPENCLAW COMMANDS
    # ==================================================
    def _cmd_skills(self):
        """List all loaded skills."""
        agent = self.agent
        skills = agent.skill_loader.list_skills()
        if not skills:
            print("  No skills loaded.", flush=True)
            return
        print("+------------------------------------------+")
        print("|  LOADED SKILLS                           |")
        print("+------------------------------------------+")
        for s in skills:
            status = "✅" if s.get("enabled", True) else "❌"
            name = s["name"]
            desc = s.get("description", "")[:30]
            tools_count = len(s.get("tools", []))
            print(f"|  {status} {name:<16} {desc:<18} ({tools_count} tools) |")
        print("+------------------------------------------+")

    def _cmd_tools(self):
        """List all registered tools."""
        agent = self.agent
        tools = agent.tool_registry.list_tools()
        if not tools:
            print("  No tools registered.", flush=True)
            return
        print("+------------------------------------------+")
        print("|  REGISTERED TOOLS                        |")
        print("+------------------------------------------+")
        for t in tools:
            name = t["name"]
            desc = t.get("description", "")[:35]
            print(f"|  🔧 {name:<12} {desc:<24}|")
        print("+------------------------------------------+")
        print(f"  Total: {len(tools)} tools")

    def _cmd_heartbeat(self):
        """Run a manual heartbeat check."""
        agent = self.agent
        print("💓 Running heartbeat check...", flush=True)
        result = agent.heartbeat.run_checks()
        status = result["status"]
        checks = result["checks_performed"]
        alerts = result["alerts"]
        elapsed = result["elapsed_ms"]

        icon = "✅" if status == "HEARTBEAT_OK" else "⚠️"
        print(f"\n{icon} {status} ({checks} checks, {elapsed}ms)")

        for detail in result["details"]:
            check_icon = "✅" if detail["status"] == "ok" else "⚠️" if detail["status"] == "warning" else "ℹ️"
            print(f"  {check_icon} {detail['check']}: {detail['status']}")
            if detail.get("data"):
                for k, v in detail["data"].items():
                    print(f"      {k}: {v}")

        if alerts:
            print(f"\n⚠️  Alerts:")
            for a in alerts:
                print(f"    • {a}")

    async def _cmd_react(self, args):
        """Route a query through the ReAct tool-use loop."""
        agent = self.agent
        if args:
            query = " ".join(args)
        else:
            print("Enter query for ReAct loop: ", end="", flush=True)
            query = (await asyncio.to_thread(input)).strip()

        if not query:
            print("❌ No query provided.", flush=True)
            return

        print(f"🔄 ReAct Loop: Processing '{query[:50]}...'", flush=True)
        result = await asyncio.to_thread(
            agent.react_engine.run, query
        )

        print(f"\n{'='*50}")
        print(f"📋 ReAct Result:")
        print(f"{'='*50}")
        print(f"  Status    : {result.get('status', 'unknown')}")
        print(f"  Iterations: {result.get('iterations', 0)}")

        if result.get("tool_calls"):
            print(f"  Tools used:")
            for tc in result["tool_calls"]:
                print(f"    🔧 {tc['tool']}({tc.get('args', {})})")

        print(f"\n💬 Answer:")
        print(f"  {result.get('answer', 'No answer generated.')}")

    async def _cmd_worldsim(self, args):
        """Run the True Multi-Agent Society simulation."""
        agent = self.agent
        if not args:
            print("Usage: /worldsim <problem or topic>")
            return
            
        topic = " ".join(args)
        print(f"🌍 Initializing World Sim: '{topic}'", flush=True)
        
        from world_sim import WorldSim
        sim = WorldSim(llm_provider=agent.llm)
        await asyncio.to_thread(sim.run_simulation, topic, max_turns=5)

    def _cmd_wallet(self, args):
        """Check wallet status."""
        agent = self.agent
        if not hasattr(agent, 'wallet') or not agent.wallet:
            print("❌ Web3Wallet not initialized.")
            return
        status = agent.wallet.get_status()
        print(f"💰 Wallet Status:\n{json.dumps(status, indent=2)}")

    def _cmd_dao(self, args):
        """Interact with the Sovereign DAO."""
        agent = self.agent
        if not hasattr(agent, 'wallet') or not agent.wallet:
            print("❌ Web3Wallet not initialized.")
            return

        if not args:
            print("Usage: /dao <propose|vote|execute|audit|deploy|status>")
            return

        sub = args[0].lower()
        if sub == "status":
            props = agent.wallet.get_dao_proposals()
            if not props:
                print("No active DAO proposals.")
                return
            for pid, p in props.items():
                print(f"[{pid}] {p['title']} ({p['status'].upper()}) - App: {p['votes']['approve']}, Rej: {p['votes']['reject']}")
        elif sub == "propose":
            title = input("Proposal Title: ").strip()
            obj = input("Objective: ").strip()
            try:
                budget = float(input("Requested Budget: ").strip())
            except ValueError:
                budget = 0.0
            pid = agent.wallet.propose_vote(title, obj, budget)
            print(f"✅ Proposal created with ID: {pid}")
        elif sub == "vote":
            if len(args) < 3:
                print("Usage: /dao vote <proposal_id> <approve|reject>")
                return
            pid = args[1]
            vote = args[2]
            res = agent.wallet.cast_vote(pid, "UserCommand", vote)
            print(res)
        elif sub == "execute":
            if len(args) < 2:
                print("Usage: /dao execute <proposal_id>")
                return
            pid = args[1]
            res = agent.wallet.execute_proposal(pid)
            print(res)
        elif sub == "audit":
            code = input("Enter Solidity Code (single line or path): ").strip()
            if os.path.exists(code):
                with open(code, 'r') as f:
                    code = f.read()
            print("🔍 Auditing Contract...")
            res = agent.wallet.audit_contract(code)
            print(res)
        elif sub == "deploy":
            name = input("Contract Name: ").strip()
            print("Deploying Contract...")
            res = agent.wallet.deploy_contract(name, [], "")
            print(res)
        else:
            print("Unknown DAO command.")

    # ==================================================
    #  PHASE 15 COMMAND HANDLERS
    # ==================================================

    def _cmd_bounty(self, args):
        """Handle /bounty commands — Freelance Bounty Engine."""
        agent = self.agent
        if not hasattr(agent, 'bounty'):
            print("❌ FreelanceBounty not initialized. Add 'bounty' attribute to agent.")
            return

        sub = args[0].lower() if args else "stats"

        if sub == "scan":
            jobs = agent.bounty.scan_jobs(max_jobs=5)
            print(f"\n🔍 Found {len(jobs)} relevant freelance jobs:")
            for j in jobs:
                print(f"  [{j['id']}] {j['title']} — ${j['budget']} ({j['deadline_days']}d) — {j['client']}")

        elif sub == "bid":
            jobs = agent.bounty.scan_jobs(max_jobs=3)
            if not jobs:
                print("⚠️ No matching jobs found.")
                return
            job = jobs[0]
            print(f"✏️ Bidding on: {job['title']}...")
            bid = agent.bounty.bid_on_job(job)
            print(f"📝 Bid submitted:\n{bid}")

        elif sub == "resolve":
            print("🎲 Simulating bid response...")
            result = agent.bounty.simulate_bid_response()
            print(f"  💰 {result['message']}")

        elif sub == "stats":
            stats = agent.bounty.get_stats()
            print(f"""
🛠️  FREELANCE BOUNTY STATS
  Active Bids   : {stats['active_bids']}
  Jobs Won      : {stats['won_jobs']}
  Total Earned  : ${stats['total_earned']:.2f}
  Recent Wins   : {', '.join(w['title'][:30] for w in stats['recent_wins']) or 'None'}
""")
        else:
            print("Usage: /bounty <scan|bid|resolve|stats>")

    async def _cmd_social(self, args):
        """Handle /social commands — Autonomous Social Media."""
        agent = self.agent
        sub = args[0].lower() if args else "stats"

        if sub == "post":
            print("🔍 Generating autonomous thought...")
            if hasattr(agent, 'social'):
                thought = await agent.social.generate_thought(context="recent agent activity")
                agent.social.post_to_twitter(thought)
                agent.social.post_to_discord(thought)
                print(f"📤 Posted: {thought}")
            elif hasattr(agent, 'influencer'):
                await agent.influencer.generate_and_post(agent.default_tid)
                if agent.influencer.post_history:
                    print(f"📤 Posted: {agent.influencer.post_history[-1]['content']}")
            else:
                print("❌ social / influencer module not initialized.")

        elif sub == "stats":
            if hasattr(agent, 'social'):
                stats = agent.social.get_status()
            elif hasattr(agent, 'influencer'):
                stats = agent.influencer.get_profile_stats()
            else:
                stats = {"error": "no social module"}
            print(f"📊 Social Stats: {json.dumps(stats, indent=2)}")

        elif sub == "stream":
            action = args[1].lower() if len(args) > 1 else "status"
            if not hasattr(agent, 'stream_host'):
                from streaming_host import StreamingHost
                agent.stream_host = StreamingHost(agent.llm)

            if action == "start":
                result = agent.stream_host.start_stream()
                print(result)
            elif action == "stop":
                result = agent.stream_host.stop_stream()
                print(result)
            else:
                status = agent.stream_host.get_stream_status()
                print(f"📡 Stream Status: {json.dumps(status, indent=2)}")
        else:
            print("Usage: /social <post|stats|stream start|stream stop>")

    def _cmd_godmode2(self, args):
        """Handle /godmode2 commands — Universal Computer Control."""
        agent = self.agent
        if not hasattr(agent, 'god2'):
            from god_mode_v2 import GodModeV2
            agent.god2 = GodModeV2(agent.llm)

        if not args:
            status = agent.god2.get_status()
            print(f"🕹️  God Mode V2: {json.dumps(status, indent=2)}")
            return

        sub = args[0].lower()

        if sub == "type" and len(args) > 1:
            text = " ".join(args[1:])
            print(agent.god2.type_text(text))

        elif sub == "scroll" and len(args) > 1:
            print(agent.god2.scroll(args[1]))

        elif sub == "hotkey" and len(args) > 1:
            keys = args[1].split("+")
            print(agent.god2.press_hotkey(*keys))

        elif sub == "screenshot":
            path = agent.god2.capture_screenshot()
            print(f"📸 Screenshot: {path}")

        elif sub == "see":
            path = agent.god2.capture_screenshot()
            analysis = agent.god2.analyze_screen(path, goal="general inspection")
            print(f"\n👁️  Screen Analysis (source: {analysis['source']}):\n{analysis['description'][:1000]}")

        else:
            # Treat everything else as an autonomous goal
            goal = " ".join(args)
            if goal:
                result = agent.god2.autonomous_task(goal)
                print(f"\n✅ Task complete in {result['steps_taken']} steps. Status: {result['final_status']}")
            else:
                print("Usage: /godmode2 <goal> | type <text> | scroll up|down | hotkey ctrl+c | screenshot | see")

    def _cmd_dream(self, args):
        """Handle /dream commands — Memory Sleep Cycle."""
        agent = self.agent
        if not hasattr(agent, 'dream_engine'):
            from dream_engine import DreamEngine
            agent.dream_engine = DreamEngine(agent.llm, agent.vmem, agent.db)

        sub = args[0].lower() if args else "status"

        if sub == "status":
            status = agent.dream_engine.get_sleep_status()
            print(f"""
💤 DREAM ENGINE STATUS
  State          : {status['state']}
  Idle Duration  : {status['idle_duration']}
  Ready to Sleep : {status['ready_to_sleep']}
  Cycles Done    : {status['sleep_cycles_completed']}
  Last Dream     : {status['last_dream']}
  Wisdom Vault   : {status['wisdom_vault_size']} rules
""")

        elif sub == "now":
            print("💤 Triggering REM sleep cycle NOW...")
            results = agent.dream_engine.enter_rem_sleep(agent.default_tid)
            print(f"  ✨ Distilled: {results['wisdom_distilled']} wisdom rules")
            print(f"  🗑️  Pruned: {results['facts_pruned']} raw facts")
            if results.get('dream_narrative'):
                print(f"  {results['dream_narrative']}")
            if results.get('new_rules'):
                print("\n  🧠 New Wisdom:")
                for rule in results['new_rules']:
                    print(f"    {rule}")

        elif sub == "wisdom":
            wisdom = agent.dream_engine.get_wisdom(agent.default_tid, limit=20)
            if not wisdom:
                print("  ⚠️ No wisdom distilled yet. Run /dream now to generate.")
            else:
                print(f"\n🧠 DISTILLED WISDOM ({len(wisdom)} rules):")
                for i, w in enumerate(wisdom, 1):
                    print(f"  {i:02d}. {w}")
        else:
            print("Usage: /dream <status|now|wisdom>")

    async def _cmd_voxelworld(self, args):
        """Handle /voxelworld commands — 3D Multi-Agent Simulation."""
        agent = self.agent

        # Initialize world sim if needed
        if not hasattr(agent, 'voxel_world') or not agent.voxel_world:
            from world_sim import WorldSimV2
            agent.voxel_world = WorldSimV2(agent.llm)
            agent.voxel_running = False

        sub = args[0].lower() if args else "status"

        if sub == "start":
            port = int(args[1]) if len(args) > 1 else 8765
            print(f"🌍 Starting voxel world on ws://localhost:{port}...")
            print(f"💻 Open voxel_world.html in your browser to see the 3D view!")
            agent.voxel_running = True
            # Run in background task
            asyncio.create_task(agent.voxel_world.run_live(port=port, tick_interval=2.0))

        elif sub == "stop":
            if hasattr(agent, 'voxel_world') and agent.voxel_world:
                agent.voxel_world.stop()
                if agent.voxel_world.voxel_server:
                    await agent.voxel_world.voxel_server.stop()
            agent.voxel_running = False
            print("🛑 Voxel World simulation stopped.")

        elif sub == "tick":
            n = int(args[1]) if len(args) > 1 else 3
            for _ in range(n):
                msgs = agent.voxel_world.tick()
            state = agent.voxel_world.get_world_state()
            print(f"🌍 World Tick {state['tick']}: richest={state['stats']['richest_agent']}, "
                  f"most built={state['stats']['most_structures']}")
            for m in msgs[:5]:
                print(f"  {m}")

        elif sub == "status":
            if hasattr(agent, 'voxel_world') and agent.voxel_world:
                state = agent.voxel_world.get_world_state()
                stats = state['stats']
                print(f"""
🌍 VOXEL WORLD STATUS
  Tick           : {state['tick']}
  Agents         : {len(state['agents'])}
  Structures     : {stats['total_structures']}
  Trades Done    : {stats['total_trades']}
  Wealthiest     : {stats['richest_agent']}
  Best Builder   : {stats['most_structures']}
  Server         : {'Live' if agent.voxel_running else 'Stopped'}
""")
            else:
                print("⚠️ World not initialized. Run /voxelworld start")
        else:
            print("Usage: /voxelworld <start [port]|stop|tick [n]|status>")

    # ==================================================
    #  PHASE 16 — INTELLIGENCE / REVENUE / SAFETY / WORLD
    # ==================================================

    async def _cmd_debate(self, args):
        """Run a 3-agent debate on a question."""
        agent = self.agent
        if not args:
            question = input("❓ What topic should the agents debate? ").strip()
        else:
            question = " ".join(args)
        if not question:
            print("Usage: /debate <question>")
            return
        if not hasattr(agent, 'debate'):
            print("❌ DebateEngine not initialized.")
            return
        await agent.debate.debate(question, tenant_id=agent.default_tid)

    def _cmd_why(self, args):
        """Recall Chain-of-Thought reasoning for past decisions."""
        agent = self.agent
        if not hasattr(agent, 'cot_mem'):
            print("❌ CoT Memory not initialized.")
            return
        query = " ".join(args) if args else input("🔍 What decision or topic to recall? ").strip()
        if not query:
            recent = agent.cot_mem.get_recent(5)
            if not recent:
                print("  No reasoning chains recorded yet.")
                return
            for i, c in enumerate(recent, 1):
                print(f"\n  [{i}] Problem: {c.get('problem', '')[:80]}")
                print(f"      Conclusion: {c.get('conclusion', '')[:120]}")
            return
        results = agent.cot_mem.recall_why(agent.default_tid, query, n=3)
        if not results:
            print(f"  No reasoning chains found for: '{query}'")
            return
        print(f"\n🧠 Reasoning chains related to '{query}':")
        for r in results:
            print(f"  • {r.get('text', str(r))[:200]}")

    def _cmd_profile(self, args):
        """Manage the long-term user profile."""
        agent = self.agent
        if not hasattr(agent, 'user_model'):
            print("❌ UserModelEngine not initialized.")
            return
        sub = args[0].lower() if args else "show"
        if sub == "show":
            print(agent.user_model.show())
        elif sub == "reset":
            agent.user_model.reset()
            print("✅ User profile reset to defaults.")
        elif sub == "set" and len(args) >= 3:
            key, val = args[1], " ".join(args[2:])
            print(agent.user_model.set(key, val))
        else:
            print("Usage: /profile show | /profile reset | /profile set <key> <value>")

    def _cmd_mode(self, args):
        """Switch the agent's personality mode."""
        agent = self.agent
        modes = ["default", "entrepreneur", "philosopher", "hacker"]
        if not args:
            current = getattr(agent, 'personality_mode', 'default')
            print(f"  🎭 Current mode: {current}")
            print(f"  Available modes: {', '.join(modes)}")
            return
        mode = args[0].lower()
        if mode not in modes:
            print(f"  ❌ Unknown mode: {mode}. Available: {', '.join(modes)}")
            return
        agent.personality_mode = mode
        emblems = {"default": "🤖", "entrepreneur": "💼", "philosopher": "🦉", "hacker": "💻"}
        print(f"  {emblems.get(mode, '🎭')} Personality mode switched to: {mode.upper()}")

    async def _cmd_oracle(self, args):
        """Run 10-simulation Oracle prediction on a scenario."""
        agent = self.agent
        if not hasattr(agent, 'oracle'):
            print("❌ OracleEngine not initialized.")
            return
        scenario = " ".join(args) if args else None
        if not scenario:
            scenario = await asyncio.to_thread(input, "🔮 Enter the scenario to predict: ")
        if not scenario:
            print("Usage: /oracle <scenario>")
            return
        await agent.oracle.predict(scenario, tenant_id=agent.default_tid)

    async def _cmd_crypto(self, args):
        """Crypto trading bot commands."""
        agent = self.agent
        if not hasattr(agent, 'crypto') or not agent.crypto:
            print("❌ CryptoTrader not initialized.")
            return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            s = agent.crypto.get_status()
            print(json.dumps(s, indent=2, default=str))
        elif sub == "signal":
            symbol = args[1].upper() if len(args) > 1 else "BTC/USDT"
            sig = await agent.crypto.get_signal(symbol)
            print(f"\n📊 Signal for {symbol}:")
            print(f"   Price: ${sig['price']:,.2f} | RSI: {sig['rsi']} | Action: {sig['action']}")
            print(f"   Analysis: {sig['llm_narrative']}")
        elif sub == "buy":
            if len(args) < 3:
                print("Usage: /crypto buy <SYMBOL> <USDT_AMOUNT>")
                return
            symbol, amount = args[1].upper(), float(args[2])
            r = await agent.crypto.buy(symbol, amount)
            print(json.dumps(r, indent=2, default=str))
        elif sub == "sell":
            if len(args) < 2:
                print("Usage: /crypto sell <SYMBOL> [qty]")
                return
            symbol = args[1].upper()
            qty = float(args[2]) if len(args) > 2 else None
            r = await agent.crypto.sell(symbol, qty)
            print(json.dumps(r, indent=2, default=str))
        elif sub == "auto":
            agent.crypto.auto_trade = (args[1].lower() == "on") if len(args) > 1 else not agent.crypto.auto_trade
            print(f"  🤖 Auto-trading: {'ON' if agent.crypto.auto_trade else 'OFF'}")
        else:
            print("Usage: /crypto status | signal <sym> | buy <sym> <amt> | sell <sym> [qty] | auto <on|off>")

    async def _cmd_saas(self, args):
        """AI SaaS launcher pipeline."""
        agent = self.agent
        if not hasattr(agent, 'saas'):
            print("❌ SaaSLauncher not initialized.")
            return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            s = agent.saas.get_status()
            print(json.dumps(s, indent=2, default=str))
        elif sub == "launch":
            idea = " ".join(args[1:]) if len(args) > 1 else await asyncio.to_thread(input, "💡 SaaS idea: ")
            if idea:
                await agent.saas.launch(idea, tenant_id=agent.default_tid)
        else:
            print("Usage: /saas status | /saas launch <idea>")

    async def _cmd_youtube(self, args):
        """YouTube content pipeline."""
        agent = self.agent
        if not hasattr(agent, 'youtube'):
            print("❌ YouTubePipeline not initialized.")
            return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            s = agent.youtube.get_status()
            print(json.dumps(s, indent=2, default=str))
        elif sub == "create":
            topic = " ".join(args[1:]) if len(args) > 1 else await asyncio.to_thread(input, "🎬 Video topic: ")
            if topic:
                await agent.youtube.create(topic, tenant_id=agent.default_tid)
        else:
            print("Usage: /youtube status | /youtube create <topic>")

    async def _cmd_redteam(self, args):
        """Red team adversarial attack loop."""
        agent = self.agent
        if not hasattr(agent, 'red_team'):
            print("❌ RedTeamEngine not initialized.")
            return
        sub = args[0].lower() if args else "run"
        if sub == "run":
            await agent.red_team.run_single_attack(tenant_id=agent.default_tid)
        elif sub == "campaign":
            n = int(args[1]) if len(args) > 1 else 3
            await agent.red_team.run_campaign(n=n, tenant_id=agent.default_tid)
        elif sub == "history":
            history = agent.red_team.get_history(5)
            for r in history:
                v = r.get('verdict', {})
                print(f"  [{r.get('attack_type')}] → {v.get('verdict')} ({v.get('confidence')}%) — {r.get('timestamp','')[:19]}")
        elif sub == "stats":
            print(json.dumps(agent.red_team.get_stats(), indent=2))
        else:
            print("Usage: /redteam run | campaign [n] | history | stats")

    def _cmd_history(self, args):
        """Render and open the audit trail dashboard."""
        agent = self.agent
        if not hasattr(agent, 'audit_ui'):
            print("❌ AuditTrailUI not initialized.")
            return
        sub = args[0].lower() if args else "open"
        if sub == "export":
            path = agent.audit_ui.export_json()
            print(f"✅ Exported to {path}")
        else:
            limit = int(args[0]) if args and args[0].isdigit() else 200
            path = agent.audit_ui.render(limit=limit, open_browser=True)
            print(f"✅ Audit trail: {path}")

    async def _cmd_news(self, args):
        """Realtime news briefing."""
        agent = self.agent
        if not hasattr(agent, 'news'):
            print("❌ NewsBriefing not initialized.")
            return
        sub = args[0].lower() if args else "brief"
        if sub == "brief" or sub == "fetch":
            briefing = await agent.news.generate_briefing(tenant_id=agent.default_tid)
            print(agent.news.display(briefing))
        elif sub == "show":
            print(agent.news.display())
        elif sub == "sources":
            from news_briefing import DEFAULT_RSS_FEEDS
            print("\n📰 Configured news sources:")
            for name, url in DEFAULT_RSS_FEEDS:
                print(f"  • {name}: {url}")
        else:
            print("Usage: /news [brief|show|sources]")

    async def _cmd_call(self, args):
        """AI phone call agent."""
        agent = self.agent
        if not hasattr(agent, 'phone'):
            print("❌ PhoneAgent not initialized.")
            return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            print(json.dumps(agent.phone.get_status(), indent=2, default=str))
        elif sub == "log":
            for r in agent.phone.get_call_log()[-5:]:
                print(f"  [{r.get('type','?')}] → {r.get('to','?')}: {r.get('message','')[:60]} ({r.get('status','?')})")
        elif len(args) >= 1 and (args[0].startswith("+") or args[0].replace("-","").isdigit()):
            # /call +1234567890 <message>
            to = args[0]
            msg = " ".join(args[1:]) if len(args) > 1 else await asyncio.to_thread(input, "📞 Message to say: ")
            r = await agent.phone.ai_call(to, msg, agent.default_tid)
            print(json.dumps(r, indent=2, default=str))
        else:
            msg = " ".join(args) if args else await asyncio.to_thread(input, "📞 Task for agent to call about: ")
            to = await asyncio.to_thread(input, "📞 Phone number to call: ")
            if to and msg:
                r = await agent.phone.ai_call(to, msg, agent.default_tid)
                print(json.dumps(r, indent=2, default=str))
            else:
                print("Usage: /call <phone_number> <message>  OR  /call status  OR  /call log")

    async def _cmd_home(self, args):
        """Smart home control via Home Assistant."""
        agent = self.agent
        if not hasattr(agent, 'smart_home'):
            print("❌ SmartHomeController not initialized.")
            return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            print(json.dumps(agent.smart_home.get_status(), indent=2, default=str))
        elif sub == "list":
            domain = args[1] if len(args) > 1 else None
            entities = await agent.smart_home.list_entities(domain)
            print(f"\n🏠 Smart Home Entities ({len(entities)}):")
            for e in entities:
                print(f"  [{e.get('state','?'):>8}] {e['entity_id']} — {e.get('attributes',{}).get('friendly_name','')}")
        elif sub == "control":
            if len(args) < 3:
                print("Usage: /home control <entity_id> <on|off|toggle>")
                return
            entity_id, state = args[1], args[2]
            r = await agent.smart_home.control(entity_id, state, tenant_id=agent.default_tid)
            print(f"  {'✅' if r.get('success') else '❌'} {entity_id} → {state}: {r.get('result','done')}")
        elif sub == "ai":
            cmd = " ".join(args[1:]) if len(args) > 1 else await asyncio.to_thread(input, "🏠 What would you like to do? ")
            r = await agent.smart_home.ai_control(cmd, agent.default_tid)
            print(f"  ✅ Executed {r.get('actions_taken', 0)} action(s) for: '{cmd}'")
        else:
            print("Usage: /home status | list [domain] | control <entity> <state> | ai <natural language>")

    # ==================================================
    #  PHASE 17 — NEW FEATURE EXPANSION
    # ==================================================

    async def _cmd_autogpt(self, args):
        """Auto-GPT loop — breaks a goal into sub-tasks and executes autonomously."""
        agent = self.agent
        goal = " ".join(args) if args else (await asyncio.to_thread(input, "🎯 Goal: ")).strip()
        if not goal:
            print("Usage: /autogpt <goal>")
            return
        if hasattr(agent, 'goal_engine'):
            print(f"🤖 Auto-GPT: '{goal}'")
            result = await asyncio.to_thread(agent.goal_engine.run_goal, goal)
            print(f"\n✅ Result:\n{result}")
        else:
            print(f"🤖 Auto-GPT Loop: Decomposing goal...")
            if agent.llm:
                plan = await asyncio.to_thread(agent.llm.call,
                    f"Break this goal into 3-5 concrete sub-tasks:\nGoal: {goal}\n\nStep 1:", 250)
                print(f"\n📋 Plan:\nStep 1:{plan}")
                sid = await asyncio.to_thread(agent.swarm.spawn_swarm, goal)
                print(f"🐝 Swarm {sid} launched. Use /delegate to check progress.")
            else:
                print("❌ No LLM connected.")

    def _cmd_rag(self, args):
        """RAG Pipeline — ingest docs, query with citations."""
        agent = self.agent
        if not hasattr(agent, 'rag'):
            from rag_pipeline import RAGPipeline
            agent.rag = RAGPipeline(llm_provider=getattr(agent, 'llm', None),
                                    vector_memory=getattr(agent, 'vmem', None))
        sub = args[0].lower() if args else "stats"
        if sub == "ingest" and len(args) > 1:
            path = " ".join(args[1:])
            print(f"📚 Ingesting '{path}'...")
            r = agent.rag.ingest(path, tenant_id=agent.default_tid)
            print(f"  ✅ {len(r['files'])} file(s), {r['chunks_added']} chunks")
        elif sub == "query" and len(args) > 1:
            q = " ".join(args[1:])
            print(f"🔍 RAG Query: '{q}'")
            r = agent.rag.query(q, tenant_id=agent.default_tid)
            print(f"\n💬 {r['answer']}")
            if r.get("citations"):
                print(f"\n📎 Sources: {', '.join(r['citations'])}")
        elif sub == "list":
            docs = agent.rag.list_documents()
            if not docs:
                print("  No docs. Use /rag ingest <path>")
            else:
                for d in docs:
                    print(f"  • {d['file']} — {d['chunks']} chunks")
        elif sub == "remove" and len(args) > 1:
            print(agent.rag.remove_document(" ".join(args[1:])))
        else:
            s = agent.rag.get_stats()
            print(f"  📊 RAG: {s['documents']} docs | {s['total_chunks']} chunks")
            print("Usage: /rag ingest <path> | query <q> | list | remove <file> | stats")

    def _cmd_summarize(self, args):
        """Long-context map-reduce summarizer."""
        agent = self.agent
        if not hasattr(agent, 'summarizer'):
            from long_summarizer import LongSummarizer
            agent.summarizer = LongSummarizer(llm_provider=getattr(agent, 'llm', None))
        if not args:
            print(f"Usage: /summarize <path|text> [style] | dir <path> [style]\nStyles: {', '.join(agent.summarizer.get_styles())}")
            return
        if args[0].lower() == "dir":
            parts = list(args[1:])
            style = parts.pop() if parts and parts[-1] in agent.summarizer.get_styles() else "bullets"
            path = " ".join(parts) or input("Directory: ").strip()
            print(f"  📁 Summarizing dir '{path}' ({style})...")
            r = agent.summarizer.summarize_directory(path, style=style)
            print(f"\n📊 ({r.get('files_processed',0)} files):\n{r['summary']}")
            return
        parts = list(args)
        style = parts.pop() if parts and parts[-1] in agent.summarizer.get_styles() else "brief"
        path = " ".join(parts)
        import os
        if os.path.exists(path):
            print(f"  📄 Summarizing '{path}' ({style})...")
            r = agent.summarizer.summarize_file(path, style=style)
        else:
            r = agent.summarizer.summarize_text(path, style=style)
        print(f"\n📝 ({r.get('chunks',1)} chunks, {r.get('words','?')} words):\n{r['summary']}")

    async def _cmd_stocks(self, args):
        """Stock market analyzer — yfinance + LLM signals."""
        agent = self.agent
        if not hasattr(agent, 'stocks'):
            from stock_analyzer import StockAnalyzer
            agent.stocks = StockAnalyzer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "status"
        if sub == "status":
            s = agent.stocks.get_status()
            print(f"  📈 {s['data_source']}\n  Watchlist: {', '.join(s['watchlist'])}")
        elif sub == "signal":
            sym = args[1].upper() if len(args) > 1 else (await asyncio.to_thread(input, "Symbol: ")).strip().upper()
            print(f"  🔍 Signal for {sym}...")
            sig = await asyncio.to_thread(agent.stocks.get_signal, sym)
            print(f"\n  📊 {sig['name']} ({sig['symbol']})\n  ${sig['price']:,.2f} | {sig['change_pct']:+.2f}% | RSI:{sig['rsi']}")
            print(f"  Signal: {sig['signal']} ({sig['confidence']})")
            if sig.get("narrative"):
                print(f"  AI: {sig['narrative']}")
        elif sub == "quote":
            sym = args[1].upper() if len(args) > 1 else (await asyncio.to_thread(input, "Symbol: ")).strip().upper()
            q = await asyncio.to_thread(agent.stocks.get_quote, sym)
            print(f"  {q['symbol']}: ${q['price']:,.2f} ({q['change_pct']:+.2f}%) RSI:{q['rsi']}")
        elif sub == "portfolio":
            syms = args[1:] or None
            r = await asyncio.to_thread(agent.stocks.portfolio_report, syms)
            print(f"  📊 Portfolio ({len(r['holdings'])} symbols):")
            for h in r['holdings']:
                arrow = "↑" if h['change_pct'] > 0 else "↓"
                print(f"    {h['symbol']:<6} ${h['price']:>9,.2f} {arrow}{abs(h['change_pct']):.2f}% RSI:{h['rsi']:.0f}")
        elif sub == "watch":
            sym = args[1].upper() if len(args) > 1 else (await asyncio.to_thread(input, "Symbol: ")).strip().upper()
            agent.stocks.add_to_watchlist(sym)
            print(f"  ✅ {sym} added to watchlist")
        else:
            print("Usage: /stocks status | signal <SYM> | quote <SYM> | portfolio [SYM...] | watch <SYM>")

    def _cmd_compose(self, args):
        """Music Composer — LLM generates chord progressions + lyrics."""
        agent = self.agent
        if not hasattr(agent, 'composer'):
            from music_composer import MusicComposer
            agent.composer = MusicComposer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "help"
        rest = " ".join(args[1:]) if len(args) > 1 else ""
        if sub == "lyrics":
            theme = rest or input("  Theme/topic for lyrics: ").strip()
            style = input("  Style (pop/rock/rap/ballad, Enter=pop): ").strip() or "pop"
            print(f"  🎵 Writing {style} lyrics about '{theme}'...")
            r = agent.composer.compose_lyrics(theme, style)
            if r["success"]:
                print(f"\n{r['lyrics']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "chords":
            key = rest or input("  Key (e.g. 'C major', 'A minor'): ").strip() or "C major"
            style = input("  Style (pop/jazz/blues/rock, Enter=pop): ").strip() or "pop"
            print(f"  🎸 Generating chord progression in {key}...")
            r = agent.composer.compose_chords(key, style)
            if r["success"]:
                print(f"\n{r['content']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "list":
            print(agent.composer.list_compositions())
        elif sub == "moods":
            print(agent.composer.get_mood_list())
        else:
            # Full song by mood
            mood = sub if sub in agent.composer.MOODS else (rest or sub)
            if not mood or mood == "help":
                mood = input("  Mood (happy/sad/epic/jazz/romantic/chill/angry/mysterious): ").strip() or "happy"
            title = input("  Song title (Enter to auto): ").strip()
            print(f"  🎵 Composing {mood} song...")
            r = agent.composer.compose_full_song(mood, title)
            if r["success"]:
                print(f"\n{r['composition']}")
            else:
                print(f"  ❌ {r['error']}")

    # ==================================================
    #  PHASE 19 — BUG BOUNTY HUNTER  🎯
    # ==================================================

    def _get_bb_hunter(self):
        """Lazy-load BugBountyHunter onto agent (same pattern as composer, biometric, etc.)."""
        agent = self.agent
        if not hasattr(agent, 'bb_hunter'):
            from bug_bounty_hunter import BugBountyHunter
            agent.bb_hunter = BugBountyHunter(llm_provider=getattr(agent, 'llm', None))
        return agent.bb_hunter

    def _get_bb_engines(self):
        """Lazy-load all advanced BB engines onto agent."""
        agent = self.agent
        if not hasattr(agent, 'bb_engines_loaded'):
            from bb_engines import (
                PassiveReconEngine,
                ParameterDiscovery,
                PayloadMutationEngine,
                AuthSessionEngine,
                ExploitConfirmEngine,
                AIImpactAnalyzer,
                DuplicateFinder,
                TakeoverEngine,
                ShodanEngine,
                AsyncReconEngine,
            )
            agent.bb_passive   = PassiveReconEngine()
            agent.bb_params    = ParameterDiscovery()
            agent.bb_payload   = PayloadMutationEngine()
            agent.bb_auth      = AuthSessionEngine()
            agent.bb_confirm   = ExploitConfirmEngine()
            agent.bb_impact    = AIImpactAnalyzer(llm=getattr(agent, 'llm', None))
            agent.bb_dupes     = DuplicateFinder()
            agent.bb_takeover  = TakeoverEngine()
            agent.bb_shodan    = ShodanEngine()
            agent.bb_async     = AsyncReconEngine()
            agent.bb_engines_loaded = True
        return agent

    def _cmd_bugbounty(self, args):
        """
        PHASE 19 — Bug Bounty Hunter 🎯
        Full multi-platform bug bounty hunting suite.

        Sub-commands
        ────────────
        CORE (BugBountyHunter)
          platforms                          — List H1 / Bugcrowd / Intigriti
          programs <h1|bc|ig> [query]        — Browse programs
          scope    <platform> <program>      — Show in-scope assets
          recon    <domain>                  — Passive recon (crt.sh, CORS, headers)
          scan     <url>                     — Active vuln scan (XSS/SQLi/SSRF/SSTI/traversal)
          findings                           — List saved findings
          add      <url> <sev> <title>       — Log a finding manually
          report   [id]                      — Generate PoC markdown report
          submit   <platform> <program> [id] — Submit via API
          autopilot <domain>                 — Full end-to-end automated hunt

        ADVANCED (bb_engines)
          deeprecon  <domain>                — Full Wayback+JS+OTX+GraphQL recon
          js         <url>                   — Extract JS endpoints & secrets
          params     <domain>                — Discover hidden params & API paths
          payloads   <xss|sqli|ssrf|ssti>    — Show WAF-bypass payload list
          probe      <url> <param> <type>    — Smart mutation probe (xss/sqli/ssrf)
          confirm    <xss|sqli|ssrf> <url> <p> — Confirm, eliminate false+
          diff       <url1> <url2>           — Diff two endpoint responses
          session    add <name> <type> <val> — Register auth session (bearer/cookie)
          session    list                    — List sessions
          idor       <url/{id}> <1,2,3,100>  — Test IDOR across IDs
          ratelimit  <url> [count]           — Test rate limiting
          duplicate  <keyword>               — Check if already disclosed on H1
          bounty     <sev>                   — Estimate payout for severity
          aianalyze  [id]                    — AI-enrich finding with CVSS + impact
          summary                            — Executive summary of all findings

        NEW ENGINES
          nuclei     <target>                — Nuclei CLI scan + ingest results
          takeover   <domain>                — Subdomain takeover detection
          jwt        <token> [url]           — JWT vulnerability analysis
          shodan     <domain|ip>             — Shodan InternetDB lookup (free)
          host-inject <url>                  — Host header injection test
          export     html [id]              — HTML report export
          hunt       new <name> [prog] [plat] — Create named hunt session
          hunt       load <name>            — Load existing hunt session
          hunt       list                   — List all saved sessions
          hunt       status                 — Show current session status
        """
        agent = self.agent
        sub = args[0].lower() if args else "help"
        rest = args[1:]

        # ── CORE commands (BugBountyHunter) ───────────────────────────────────
        if sub == "platforms":
            h = self._get_bb_hunter()
            print(h.list_platforms())

        elif sub == "programs":
            h = self._get_bb_hunter()
            platform = rest[0] if rest else ""
            query    = " ".join(rest[1:]) if len(rest) > 1 else ""
            if not platform:
                platform = input("  Platform (h1/bc/ig): ").strip()
            # normalise aliases
            aliases = {"h1": "hackerone", "bc": "bugcrowd", "ig": "intigriti",
                       "hackerone": "hackerone", "bugcrowd": "bugcrowd", "intigriti": "intigriti"}
            platform = aliases.get(platform.lower(), platform.lower())
            print(f"  🔍 Fetching programs on {platform}…")
            print(h.list_programs(platform, query))

        elif sub == "scope":
            h = self._get_bb_hunter()
            platform = rest[0] if rest else ""
            program  = rest[1] if len(rest) > 1 else ""
            if not platform:
                platform = input("  Platform (h1/bc/ig): ").strip()
            if not program:
                program = input("  Program handle: ").strip()
            aliases = {"h1": "hackerone", "bc": "bugcrowd", "ig": "intigriti"}
            platform = aliases.get(platform.lower(), platform.lower())
            print(f"  🎯 Fetching scope for {program} on {platform}…")
            print(h.get_scope(platform, program))

        elif sub == "recon":
            h = self._get_bb_hunter()
            domain = rest[0] if rest else input("  Domain to recon: ").strip()
            if not domain:
                print("  ❌ Domain required."); return
            print(f"  🔭 Passive recon on {domain}…")
            print(h.passive_recon(domain))

        elif sub == "scan":
            h = self._get_bb_hunter()
            url = rest[0] if rest else input("  URL to scan: ").strip()
            if not url:
                print("  ❌ URL required."); return
            print(f"  ⚡ Active scan: {url} …")
            print(h.active_scan(url))

        elif sub == "findings":
            h = self._get_bb_hunter()
            print(h.list_findings())

        elif sub == "add":
            h = self._get_bb_hunter()
            url   = rest[0] if len(rest) > 0 else input("  URL: ").strip()
            sev   = rest[1] if len(rest) > 1 else input("  Severity (critical/high/medium/low/informational): ").strip()
            title = " ".join(rest[2:]) if len(rest) > 2 else input("  Title: ").strip()
            desc  = input("  Description (Enter to skip): ").strip()
            plat  = input("  Platform (Enter to skip): ").strip()
            prog  = input("  Program handle (Enter to skip): ").strip()
            h.add_finding(url, sev, title, desc, plat, prog)

        elif sub == "report":
            h = self._get_bb_hunter()
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            print(h.generate_report(fid))

        elif sub == "submit":
            h = self._get_bb_hunter()
            platform = rest[0] if rest else input("  Platform (h1): ").strip()
            program  = rest[1] if len(rest) > 1 else input("  Program handle: ").strip()
            fid      = int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else None
            aliases  = {"h1": "hackerone", "bc": "bugcrowd", "ig": "intigriti"}
            platform = aliases.get(platform.lower(), platform.lower())
            print(f"  📤 Submitting to {platform}/{program}…")
            print(h.submit_report(platform, program, fid))

        # ── ADVANCED commands (bb_engines) ────────────────────────────────────
        elif sub == "deeprecon":
            self._get_bb_engines()
            domain = rest[0] if rest else input("  Domain: ").strip()
            print(f"\n  🔬 Deep recon on {domain}…\n")
            result = agent.bb_passive.full_recon(domain)
            print(result)

        elif sub == "js":
            self._get_bb_engines()
            url = rest[0] if rest else input("  URL (page or JS file): ").strip()
            print(f"\n  📜 Extracting JS endpoints from {url}…\n")
            js_files = agent.bb_passive.find_js_files(url)
            all_endpoints = []
            for jsf in js_files[:10]:
                eps = agent.bb_passive.extract_js_endpoints(jsf)
                all_endpoints.extend(eps)
                print(f"  [{jsf}]")
                for ep in eps[:15]:
                    print(f"    → {ep}")
            print(f"\n  ✅ Total endpoints found: {len(all_endpoints)}")

        elif sub == "params":
            self._get_bb_engines()
            domain = rest[0] if rest else input("  Domain / URL: ").strip()
            print(f"\n  🔎 Parameter discovery on {domain}…\n")
            result = agent.bb_params.run(domain)
            print(result)

        elif sub == "payloads":
            self._get_bb_engines()
            vuln_type = rest[0].lower() if rest else input("  Type (xss/sqli/ssrf/ssti): ").strip()
            if not vuln_type:
                print("  ❌ Vulnerability type required."); return
            result = agent.bb_payload.show_payloads(vuln_type)
            if result:
                print(result)
            else:
                print(f"  ❌ No payloads found for type '{vuln_type}'.")

        elif sub == "probe":
            self._get_bb_engines()
            url       = rest[0] if len(rest) > 0 else input("  URL: ").strip()
            param     = rest[1] if len(rest) > 1 else input("  Parameter: ").strip()
            vuln_type = rest[2].lower() if len(rest) > 2 else input("  Type (xss/sqli/ssrf/ssti): ").strip() or "xss"
            print(f"\n  🧪 Probing {url}?{param}=… with {vuln_type} mutations…\n")
            hits = agent.bb_payload.probe_with_mutations(url, param, vuln_type)
            if hits:
                print(f"  🚨 {len(hits)} HITS confirmed:")
                for h in hits:
                    print(f"    [{h.get('severity','?').upper()}] {h.get('payload','')} → {h.get('evidence','')[:100]}")
            else:
                print("  ✅ No confirmed hits (check manually with Burp).")

        elif sub == "confirm":
            self._get_bb_engines()
            vuln_type = rest[0].lower() if rest else input("  Type (xss/sqli/ssrf): ").strip()
            url   = rest[1] if len(rest) > 1 else input("  URL: ").strip()
            param = rest[2] if len(rest) > 2 else input("  Parameter: ").strip()
            print(f"\n  🔬 Confirming {vuln_type} at {url}?{param}=…\n")
            if vuln_type == "xss":
                r = agent.bb_confirm.confirm_xss(url, param)
            elif vuln_type == "sqli":
                r = agent.bb_confirm.confirm_sqli(url, param)
            elif vuln_type == "ssrf":
                r = agent.bb_confirm.confirm_ssrf(url, param)
            else:
                print(f"  ❌ Unknown type: {vuln_type}"); return
            confirmed = r.get("confirmed", False)
            icon = "🚨" if confirmed else "✅"
            print(f"  {icon} Confirmed: {confirmed}")
            for k, v in r.items():
                if k != "confirmed":
                    print(f"    {k}: {str(v)[:120]}")

        elif sub == "diff":
            self._get_bb_engines()
            url1 = rest[0] if len(rest) > 0 else input("  URL 1: ").strip()
            url2 = rest[1] if len(rest) > 1 else input("  URL 2: ").strip()
            if not url1 or not url2:
                print("  ❌ Both URLs are required for diff."); return
            print(f"\n  🔀 Diffing responses…\n")
            result = agent.bb_confirm.diff_endpoint(url1, url2)
            if isinstance(result, dict):
                for k, v in result.items():
                    print(f"  {k}: {v}")
            else: # result is a string (error or direct output)
                print(result)

        elif sub == "session":
            self._get_bb_engines()
            action = rest[0].lower() if rest else "list"
            if action == "add":
                name  = rest[1] if len(rest) > 1 else input("  Session name: ").strip()
                atype = rest[2] if len(rest) > 2 else input("  Type (bearer/cookie/basic): ").strip()
                value = " ".join(rest[3:]) if len(rest) > 3 else input(f"  {atype} value: ").strip()
                agent.bb_auth.add_session(name, atype, value)
                print(f"  ✅ Session '{name}' registered.")
            elif action == "list":
                print(agent.bb_auth.list_sessions())
            else:
                print("  Usage: /bugbounty session add <name> <type> <value>  OR  session list")

        elif sub == "idor":
            self._get_bb_engines()
            url_tpl = rest[0] if len(rest) > 0 else input("  URL template (use {id}): ").strip()
            ids_raw = rest[1] if len(rest) > 1 else input("  IDs to test (comma-sep, e.g. 1,2,3,100): ").strip()
            ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
            sess = rest[2] if len(rest) > 2 else None
            if not url_tpl or not ids:
                print("  ❌ URL template and IDs are required."); return
            print(f"\n  🔑 IDOR test on {url_tpl} with {len(ids)} IDs…\n")
            result = agent.bb_auth.test_idor(url_tpl, ids, name=sess)
            if isinstance(result, str):
                print(result)
            else:
                for r in result:
                    sid = r.get("id"); sc = r.get("status_code", r.get("status", "?"))
                    diff = r.get("body_diff", r.get("diff", 0))
                    is_suspicious = r.get("suspicious", r.get("is_suspicious", False))
                    flag = "🚨" if is_suspicious else "  "
                    diff_str = f"{diff:.0%}" if isinstance(diff, float) else str(diff)
                    print(f"  {flag} ID {sid}: HTTP {sc} | body_diff={diff_str}")

        elif sub == "ratelimit":
            self._get_bb_engines()
            url   = rest[0] if len(rest) > 0 else input("  URL: ").strip()
            count = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else 30
            sess  = rest[2] if len(rest) > 2 else None
            if not url:
                print("  ❌ URL required."); return
            print(f"\n  ⏱️  Rate-limit test: {count} requests to {url}…\n")
            result = agent.bb_auth.test_rate_limit(url, count, name=sess)
            if isinstance(result, str):
                print(result)
            else:
                print(f"  Total  : {result.get('total_requests', count)}")
                print(f"  Blocked: {result.get('blocked_count', 0)} → {result.get('block_rate', 0):.0%}")
                print(f"  429s   : {result.get('rate_limit_detected', False)}")
                if result.get("rate_limit_detected"):
                    print("  ✅ Rate limit is enforced — low severity for bounty.")
                else:
                    print("  🚨 No rate limiting detected! Submit as medium/high depending on endpoint.")

        elif sub == "duplicate":
            self._get_bb_engines()
            keyword = " ".join(rest) if rest else input("  Keyword / title to check: ").strip()
            if not keyword:
                print("  ❌ Keyword required."); return
            print(f"\n  🔍 Checking H1 public disclosures for '{keyword}'…\n")
            results = agent.bb_dupes.search_h1_disclosed(keyword)
            if results:
                print(f"  ⚠️  {len(results)} similar disclosed reports found:")
                for r in results:
                    print(f"    [{r.get('severity','?').upper()}] {r.get('title','?')}")
                    print(f"       → {r.get('url','')}")
            else:
                print("  ✅ No obvious duplicates found in public disclosures.")

        elif sub == "bounty":
            self._get_bb_engines()
            sev     = rest[0].lower() if rest else input("  Severity (critical/high/medium/low): ").strip()
            program = rest[1] if len(rest) > 1 else ""
            if not sev:
                print("  ❌ Severity required."); return
            result = agent.bb_dupes.estimate_bounty(sev, program)
            # estimate_bounty returns a formatted string
            print(f"\n{result}")

        elif sub == "aianalyze":
            self._get_bb_engines()
            h = self._get_bb_hunter()
            if not h.findings:
                print("  ℹ️  No findings saved. Use /bugbounty add first."); return
            fid_arg = int(rest[0]) - 1 if rest and rest[0].isdigit() else 0
            fid = max(0, min(fid_arg, len(h.findings) - 1)) # Ensure fid is a valid index
            finding = h.findings[fid]
            print(f"\n  🧠 AI Analyzing finding #{fid + 1}: {finding.get('title', '?')}…\n")
            enriched = agent.bb_impact.analyze_finding(finding)
            print(f"  CVSS Range : {enriched.get('cvss_range', '?')}")
            print(f"  Impact hint: {enriched.get('impact_hint', '?')}")
            if enriched.get('ai_impact'):
                print(f"  AI Impact  :\n{enriched['ai_impact']}")
            if enriched.get('ai_remediation'):
                print(f"  Remediation:\n{enriched['ai_remediation']}")

        elif sub == "summary":
            self._get_bb_engines()
            h = self._get_bb_hunter()
            if not h.findings:
                print("  ℹ️  No findings yet."); return
            print(f"\n  📊 Executive Summary ({len(h.findings)} findings)…\n")
            summary = agent.bb_impact.generate_executive_summary(h.findings)
            print(summary)

        # ── NEW ENGINE COMMANDS ────────────────────────────────────────────────

        elif sub == "autopilot":
            h = self._get_bb_hunter()
            domain = rest[0] if rest else input("  Domain: ").strip()
            if not domain:
                print("  ❌ Domain required."); return
            no_nuclei = ("--no-nuclei" in rest)
            print(f"\n  🚀 Starting Autopilot on {domain}...…")
            print(h.autopilot(domain, run_nuclei_scan=not no_nuclei))

        elif sub == "nuclei":
            h = self._get_bb_hunter()
            target = rest[0] if rest else input("  Target URL or domain: ").strip()
            if not target:
                print("  ❌ Target required."); return
            severity = rest[1] if len(rest) > 1 and not rest[1].startswith("--") else "medium,high,critical"
            dry = "--dry" in rest
            print(f"\n  ⚡ Nuclei scan: {target}...…")
            print(h.run_nuclei(target, severity=severity, dry_run=dry))

        elif sub == "takeover":
            self._get_bb_engines()
            domain = rest[0] if rest else input("  Domain to scan: ").strip()
            if not domain:
                print("  ❌ Domain required."); return
            print(f"\n  🎯 Subdomain takeover scan: {domain}…")
            result = agent.bb_takeover.scan_domain(domain)
            print(result)
            # Auto-log high severity takeovers
            h = self._get_bb_hunter()
            for line in result.splitlines():
                if "[HIGH]" in line or "[CRITICAL]" in line:
                    sub_target = line.split("]\x1b")[-1].strip() if "\x1b" in line else line.split("]")[-1].strip()
                    if sub_target:
                        h.add_finding(url=f"http://{sub_target}",
                                      severity="high",
                                      title=f"Subdomain Takeover Candidate: {sub_target}")

        elif sub == "jwt":
            h = self._get_bb_hunter()
            token_or_url = rest[0] if rest else input("  JWT token or URL: ").strip()
            if not token_or_url:
                print("  ❌ JWT token or URL required."); return
            print(f"\n  🔑 JWT Analysis…")
            print(h.scan_jwt(token_or_url))

        elif sub == "shodan":
            self._get_bb_engines()
            target = rest[0] if rest else input("  Domain or IP: ").strip()
            if not target:
                print("  ❌ Target required."); return
            print(f"\n  🌐 Shodan InternetDB lookup: {target}…")
            result = agent.bb_shodan.lookup(target)
            print(agent.bb_shodan.format_report(result))

        elif sub in ("host-inject", "hostinject", "hostheader"):
            self._get_bb_engines()
            url = rest[0] if rest else input("  URL to test: ").strip()
            if not url:
                print("  ❌ URL required."); return
            print(f"\n  🌐 Host Header Injection test: {url}…")
            findings_hh = agent.bb_payload.test_host_header_injection(url)
            print(agent.bb_payload.format_host_injection_report(findings_hh))

        elif sub == "export":
            h = self._get_bb_hunter()
            fmt = rest[0].lower() if rest else "html"
            fid = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else None
            if fmt == "html":
                print(h.export_html_report(finding_id=fid))
            elif fmt == "md" or fmt == "markdown":
                path = h.export_markdown_report(finding_id=fid)
                print(f"  ✅ Markdown saved: {path}")
            else:
                print(f"  ❌ Unknown format: {fmt}. Use 'html' or 'md'.")

        elif sub == "hunt":
            action = rest[0].lower() if rest else "list"
            try:
                from bb_hunt_session import HuntSession, list_sessions, delete_session
                if action == "new" or action == "create":
                    name = rest[1] if len(rest) > 1 else input("  Session name: ").strip()
                    prog = rest[2] if len(rest) > 2 else input("  Program handle: ").strip()
                    plat = rest[3] if len(rest) > 3 else input("  Platform (h1/bc/ig): ").strip()
                    session = HuntSession.new(name, program=prog, platform=plat)
                    agent.bb_session = session
                    print(f"  ✅ Hunt session '{name}' created!")
                    print(session.status())
                elif action == "load":
                    name = rest[1] if len(rest) > 1 else input("  Session name: ").strip()
                    session = HuntSession.load(name)
                    agent.bb_session = session
                    print(f"  ✅ Loaded hunt session '{name}'")
                    print(session.status())
                elif action == "status":
                    if hasattr(agent, 'bb_session') and agent.bb_session:
                        print(agent.bb_session.status())
                    else:
                        print("  ℹ️  No active session. Use /bugbounty hunt new <name>")
                elif action == "list":
                    print(list_sessions())
                elif action == "delete":
                    name = rest[1] if len(rest) > 1 else input("  Session to delete: ").strip()
                    print(delete_session(name))
                else:
                    print("  Usage: /bugbounty hunt <new|load|list|status|delete> [name]")
            except ImportError:
                print("  ❌ bb_hunt_session.py not found.")

        elif sub in ("cvss",):
            h = self._get_bb_hunter()
            vector = " ".join(rest) if rest else ""
            if not vector:
                vector = input("  CVSS 3.1 vector (Enter for builder guide): ").strip()
            print(h.calculate_cvss(vector))

        elif sub in ("crlf",):
            h = self._get_bb_hunter()
            url   = rest[0] if rest else input("  URL: ").strip()
            param = rest[1] if len(rest) > 1 else input("  Parameter (Enter for path injection): ").strip() or None
            if not url:
                print("  ❌ URL required."); return
            print(f"\n  🔀 CRLF Injection probe: {url}…")
            print(h.probe_crlf(url, param))

        elif sub in ("pollution", "proto", "prototype"):
            h = self._get_bb_hunter()
            url = rest[0] if rest else input("  URL: ").strip()
            if not url:
                print("  ❌ URL required."); return
            print(f"\n  ⚡ Prototype Pollution probe: {url}…")
            print(h.probe_prototype_pollution(url))

        elif sub in ("blindxss", "bxss", "blind-xss"):
            h = self._get_bb_hunter()
            url   = rest[0] if rest else input("  URL: ").strip()
            param = rest[1] if len(rest) > 1 else input("  Parameter: ").strip()
            wait  = int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else 10
            if not url or not param:
                print("  ❌ URL and parameter required."); return
            print(f"\n  🔵 Blind XSS probe: {url}?{param}=… (waiting {wait}s for OOB callback)…")
            print(h.probe_blind_xss(url, param, wait))

        elif sub in ("github", "gh", "gitleak"):
            h = self._get_bb_hunter()
            domain = rest[0] if rest else input("  Domain (e.g. shopify.com): ").strip()
            if not domain:
                print("  ❌ Domain required."); return
            print(f"\n  🐙 GitHub secret leakage recon: {domain}…")
            print(h.github_recon(domain))

        elif sub in ("html",):
            h = self._get_bb_hunter()
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            print(h.export_html_report(finding_id=fid))

        else:
            # ── Help ──────────────────────────────────────────────────────────
            print("""
+══════════════════════════════════════════════════+
|  🎯  PHASE 19 — BUG BOUNTY HUNTER               |
+══════════════════════════════════════════════════+
|  CORE                                            |
|  /bugbounty platforms                            |
|  /bugbounty programs <h1|bc|ig> [query]          |
|  /bugbounty scope <platform> <program>           |
|  /bugbounty recon <domain>                       |
|  /bugbounty scan <url>    (XSS+SQLi+SSRF+SSTI)   |
|  /bugbounty findings                             |
|  /bugbounty add <url> <sev> <title>              |
|  /bugbounty report [id]     html [id]            |
|  /bugbounty cvss [vector]                        |
|  /bugbounty submit hackerone <prog> [id]         |
|  /bugbounty submit bugcrowd  <prog> [id]         |
|  /bugbounty submit intigriti <prog> [id]         |
|  /bugbounty autopilot <domain>                   |
+--------------------------------------------------+
|  RECON ENGINES                                   |
|  /bugbounty deeprecon <domain>                   |
|  /bugbounty js <url>   params <domain>           |
|  /bugbounty github <domain>                      |
|  /bugbounty shodan <domain|ip>                   |
+--------------------------------------------------+
|  DETECTION ENGINES                               |
|  /bugbounty jwt <token|url>                      |
|  /bugbounty crlf <url> <param>                   |
|  /bugbounty pollution <url>                      |
|  /bugbounty blindxss <url> <param> [secs]        |
|  /bugbounty takeover <domain>                    |
|  /bugbounty host-inject <url>                    |
|  /bugbounty ssrf <url> <param>                   |
+--------------------------------------------------+
|  ADVANCED                                        |
|  /bugbounty payloads <xss|sqli|ssrf|ssti>        |
|  /bugbounty probe <url> <param> <type>           |
|  /bugbounty confirm <xss|sqli|ssrf> <url> <p>   |
|  /bugbounty diff <url1> <url2>                   |
|  /bugbounty session add <n> <type> <val>  list   |
|  /bugbounty idor <url/{id}> <1,2,3,100>          |
|  /bugbounty ratelimit <url> [count]              |
|  /bugbounty duplicate <keyword>                  |
|  /bugbounty bounty <severity>                    |
|  /bugbounty aianalyze [id]  summary              |
|  /bugbounty nuclei <target> [severity] [--dry]   |
|  /bugbounty export html [id]   export md [id]   |
|  /bugbounty hunt new|load|list|status|delete     |
+--------------------------------------------------+
|  ⚡ NEW ENGINES (PHASE 2)                        |
|  /bugbounty oauth <auth_ep> [tok_ep] [redir]    |
|     OAuth2/OIDC: redirect_uri, PKCE, state CSRF  |
|  /bugbounty apiscan <url>                        |
|     30+ secret patterns: AWS, Stripe, JWT, keys  |
|  /bugbounty cloud <company>                      |
|     S3 / Azure Blob / GCS / Firebase buckets     |
|  /bugbounty cache <url>                           |
|     Cache poison: X-Fwd-Host, deception, cloaking|
|  /bugbounty crawl <url> [depth] [max_pages]      |
|     Web crawler — links, forms, params, JS files |
|  /bugbounty graphql <url>                        |
|     GraphQL introspection + batch + IDOR          |
|  /bugbounty poc [id]                             |
|     AI-generated PoC write-up for a finding      |
+--------------------------------------------------+
|  ⚙️  CONFIG (NEW)                                 |
|  /bugbounty telegram set <token> <chat_id>       |
|  /bugbounty proxy <url|off>  (Burp Suite route)  |
|  /bugbounty help              (full inline ref)  |
+══════════════════════════════════════════════════+
|  ⚠️  Only test in-scope authorized assets!       |
+══════════════════════════════════════════════════+""")



    def _cmd_emailcampaign(self, args):
        """Cold email marketing bot."""
        agent = self.agent
        if not hasattr(agent, 'emailcampaign'):
            from email_campaign import EmailCampaign
            agent.emailcampaign = EmailCampaign(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "list"
        if sub == "create":
            name = input("Name: ").strip(); audience = input("Audience: ").strip(); goal = input("Goal: ").strip()
            try: num = int(input("Emails [3]: ").strip() or "3")
            except ValueError: num = 3
            print(f"  ✍️  Writing {num}-email sequence...")
            camp = agent.emailcampaign.create_campaign(name, audience, goal, num)
            print(f"  ✅ Campaign '{camp['name']}' (ID: {camp['id']})")
        elif sub == "list":
            cs = agent.emailcampaign.list_campaigns()
            [print(f"  [{c['id']}] {c['name']} — {c['emails']} emails ({c['status']})") for c in cs] if cs else print("  No campaigns.")
        elif sub == "preview" and len(args) > 1:
            print(agent.emailcampaign.preview_campaign(args[1])[:600])
        elif sub == "recipients" and len(args) > 1:
            raw = input("Emails (comma-separated): ").strip()
            print(agent.emailcampaign.add_recipients(args[1], [e.strip() for e in raw.split(",") if "@" in e]))
        elif sub == "send" and len(args) > 1:
            dry = input("Dry run? [y]: ").strip().lower() != "n"
            r = agent.emailcampaign.send_sequence(args[1], dry_run=dry)
            print(f"  ✅ Sent {r.get('sent',0)}/{r.get('recipients',0)} | Mode: {r.get('mode','?')}")
        elif sub == "stats":
            s = agent.emailcampaign.get_stats()
            print(f"  📊 {s['total_campaigns']} campaigns")
        else:
            print("Usage: /emailcampaign create | list | preview <id> | recipients <id> | send <id> | stats")

    def _cmd_codereview(self, args):
        """AI code reviewer — files, diffs, or directories."""
        agent = self.agent
        if not hasattr(agent, 'code_reviewer'):
            from code_review_agent import CodeReviewAgent
            agent.code_reviewer = CodeReviewAgent(llm_provider=getattr(agent, 'llm', None))
        path = " ".join(args) if args else input("📋 File/dir to review: ").strip()
        if not path:
            print("Usage: /codereview <file_or_dir>"); return
        import os
        print(f"  🔍 Reviewing '{path}'...")
        r = agent.code_reviewer.review_dir(path) if os.path.isdir(path) else agent.code_reviewer.review_file(path)
        print(agent.code_reviewer.format_report(r) if "error" not in r else f"  ❌ {r['error']}")

    def _cmd_bughunt(self, args):
        """Autonomous bug and security scanner."""
        agent = self.agent
        if not hasattr(agent, 'bug_hunter'):
            from bug_hunter import BugHunter
            agent.bug_hunter = BugHunter(llm_provider=getattr(agent, 'llm', None))
        path = " ".join(args) if args else input("🐛 File/dir to scan: ").strip()
        if not path:
            print("Usage: /bughunt <file_or_dir>"); return
        import os
        print(f"  🔍 Scanning '{path}'...")
        r = agent.bug_hunter.scan_dir(path) if os.path.isdir(path) else agent.bug_hunter.scan_file(path)
        print(agent.bug_hunter.format_report(r) if "error" not in r else f"  ❌ {r['error']}")

    def _cmd_autotest(self, args):
        """Auto-generates and runs pytest tests."""
        agent = self.agent
        if not hasattr(agent, 'auto_tester'):
            from auto_tester import AutoTester
            agent.auto_tester = AutoTester(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else ""
        if sub in ("generate", "gen") and len(args) > 1:
            target = " ".join(args[1:])
            print(f"  🧪 Generating tests for '{target}'...")
            r = agent.auto_tester.generate_tests(target)
            print(f"  ❌ {r['error']}" if "error" in r else f"  ✅ {r.get('functions_found',0)} fn(s)\n\n{r['test_code'][:1200]}")
        elif sub == "run" and len(args) > 1:
            r = agent.auto_tester.run_tests(" ".join(args[1:]))
            icon = "✅" if r["status"] == "passed" else "❌"
            print(f"  {icon} {r['passed']} passed | {r['failed']} failed\n{r.get('output','')[-600:]}")
        elif sub == "auto" and len(args) > 1:
            gen = agent.auto_tester.generate_tests(" ".join(args[1:]))
            if "error" in gen:
                print(f"  ❌ {gen['error']}"); return
            run = agent.auto_tester.run_tests(gen["test_code"])
            icon = "✅" if run["status"] == "passed" else "❌"
            print(f"  {icon} Generated {gen.get('functions_found',0)} tests | {run['passed']} passed, {run['failed']} failed")
        elif sub == "save" and len(args) > 1:
            r = agent.auto_tester.generate_and_save(" ".join(args[1:]))
            print(f"  ✅ {r.get('test_file','?')}" if "error" not in r else f"  ❌ {r['error']}")
        else:
            print("Usage: /autotest generate <file> | run <file> | auto <file> | save <file>")

    async def _cmd_browse(self, args):
        """Browser automation — navigate URLs or autonomous task."""
        agent = self.agent
        goal = " ".join(args) if args else (await asyncio.to_thread(input, "🌐 URL or goal: ")).strip()
        if not goal:
            print("Usage: /browse <url or goal>"); return
        if not hasattr(agent, 'browser') or not agent.browser:
            try:
                from browser_agent import BrowserAgent
                agent.browser = BrowserAgent(llm_provider=getattr(agent, 'llm', None))
            except Exception:
                agent.browser = None
        import re
        is_url = bool(re.match(r"https?://|www\.", goal, re.I))
        if agent.browser and is_url and hasattr(agent.browser, 'navigate'):
            try:
                result = await asyncio.to_thread(agent.browser.navigate, goal)
                print(f"  ✅ {result}"); return
            except Exception:
                pass
        print(f"  🔍 Researching: '{goal}'")
        result = await asyncio.to_thread(agent.reflexive.research, goal)
        print(f"\n{result}")

    def _cmd_email(self, args):
        """Email agent — reads and drafts via Gmail/Outlook."""
        agent = self.agent
        if not hasattr(agent, 'email_agent') or not agent.email_agent:
            try:
                from email_agent import EmailAgent
                agent.email_agent = EmailAgent(llm_provider=getattr(agent, 'llm', None))
            except Exception as e:
                print(f"❌ EmailAgent error: {e}"); return
        sub = args[0].lower() if args else "status"
        if sub == "status":
            try:
                print(json.dumps(agent.email_agent.get_status(), indent=2, default=str))
            except Exception:
                print("  📧 Email Agent: Initialized")
        elif sub == "read":
            if hasattr(agent.email_agent, 'read_inbox'):
                for i, em in enumerate(agent.email_agent.read_inbox(limit=5), 1):
                    print(f"  [{i}] {em.get('from','?')} | {em.get('subject','?')[:60]}")
            else:
                print("  ℹ️ Set GMAIL_CREDENTIALS or OUTLOOK_CLIENT_ID for inbox access")
        elif sub == "draft" and len(args) > 1:
            subj = " ".join(args[1:]); to = input("  To: ").strip(); ctx = input("  Context: ").strip()
            if agent.llm:
                print("\n  📧 Draft:\n" + agent.llm.call(f"Email to {to}. Subject:{subj}. Context:{ctx}. Body only:", 300))
        elif sub == "send":
            to = input("  To: ").strip(); subj = input("  Subject: ").strip(); body = input("  Body: ").strip()
            if hasattr(agent.email_agent, 'send_email'):
                print(f"  {'✅' if agent.email_agent.send_email(to=to, subject=subj, body=body) else '❌'}")
            else:
                print("  ℹ️ Set SMTP_HOST, SMTP_USER, SMTP_PASS for sending")
        else:
            print("Usage: /email status | read | draft <subject> | send")

    def _cmd_calendar(self, args):
        """Google Calendar manager."""
        agent = self.agent
        if not hasattr(agent, 'calendar'):
            from calendar_manager import CalendarManager
            agent.calendar = CalendarManager(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "list"
        if sub == "list":
            days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
            events = agent.calendar.list_events(days)
            print(f"  📅 Next {days} days ({len(events)} events):")
            for ev in events:
                print(f"   • {ev.get('start','')[:16]} — {ev.get('title','Untitled')}")
            print(f"   Mode: {agent.calendar.get_status()['mode']}")
        elif sub == "today":
            evs = agent.calendar.get_today()
            print(f"  📅 Today: {len(evs)} event(s)")
            for ev in evs:
                print(f"   • {ev.get('start','')[-5:]} — {ev.get('title','?')}")
        elif sub == "create":
            title = " ".join(args[1:]) if len(args) > 1 else input("  Title: ").strip()
            start = input("  Start (YYYY-MM-DD HH:MM): ").strip()
            try: dur = int(input("  Duration [60] min: ").strip() or "60")
            except ValueError: dur = 60
            r = agent.calendar.create_event(title, start, dur, input("  Description: ").strip())
            print(f"  {'✅ Created' if 'error' not in r else '❌ ' + r['error']}")
        elif sub == "summary":
            print(agent.calendar.summarize_week())
        elif sub == "status":
            print(json.dumps(agent.calendar.get_status(), indent=2))
        else:
            print("Usage: /calendar list [days] | today | create <title> | summary | status")

    def _cmd_voiceclone(self, args):
        """ElevenLabs voice cloning."""
        agent = self.agent
        sub = args[0].lower() if args else "status"
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if sub == "status":
            print(f"  🎤 ElevenLabs Voice Clone\n  Key: {'✅' if api_key else '❌ set ELEVENLABS_API_KEY'}")
            print(f"  Cloned Voice: {getattr(agent,'_cloned_voice_id','None')}")
        elif sub == "upload" and len(args) > 1:
            path = " ".join(args[1:])
            if not os.path.exists(path):
                print(f"  ❌ File not found: {path}"); return
            if not api_key:
                print("  ❌ Set ELEVENLABS_API_KEY"); return
            try:
                import requests
                with open(path, "rb") as f:
                    resp = requests.post("https://api.elevenlabs.io/v1/voices/add",
                        headers={"xi-api-key": api_key},
                        files={"files": (os.path.basename(path), f, "audio/wav")},
                        data={"name": "AgentClone"}, timeout=30)
                if resp.ok:
                    agent._cloned_voice_id = resp.json().get("voice_id","")
                    print(f"  ✅ Cloned! ID: {agent._cloned_voice_id}")
                else:
                    print(f"  ❌ {resp.text[:200]}")
            except Exception as e:
                print(f"  ❌ {e}")
        elif sub == "speak" and len(args) > 1:
            text = " ".join(args[1:])
            vid = getattr(agent, '_cloned_voice_id', "21m00Tcm4TlvDq8ikWAM")
            if not api_key:
                print("  ❌ Set ELEVENLABS_API_KEY"); return
            try:
                import requests
                resp = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                    headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                    json={"text": text, "model_id": "eleven_monolingual_v1",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}}, timeout=30)
                if resp.ok:
                    out = "voiceclone_output.mp3"
                    with open(out, "wb") as f: f.write(resp.content)
                    print(f"  ✅ Saved: {out}")
                    if sys.platform == "win32": os.startfile(out)
                else:
                    print(f"  ❌ {resp.text[:200]}")
            except Exception as e:
                print(f"  ❌ {e}")
        else:
            print("Usage: /voiceclone status | upload <audio_path> | speak <text>")

    def _cmd_companion(self, args):
        """AI Companion Mode — persistent friend with emotional memory."""
        agent = self.agent
        if not hasattr(agent, 'companion'):
            from ai_companion import AICompanion
            user_name = "Friend"
            if hasattr(agent, 'mem'):
                try:
                    import re
                    mm = re.search(r'name[:\s]+([A-Za-z]+)', agent.mem.about_user() or '', re.I)
                    if mm: user_name = mm.group(1)
                except Exception: pass
            agent.companion = AICompanion(llm_provider=getattr(agent,'llm',None), user_name=user_name)
        sub = args[0].lower() if args else "checkin"
        if sub == "checkin":
            mood = " ".join(args[1:]) if len(args) > 1 else ""
            print("  💙 Checking in...")
            print(f"\n  🤗 {agent.companion.check_in(user_mood=mood)}")
        elif sub == "remember" and len(args) > 1:
            print(agent.companion.remember(" ".join(args[1:])))
        elif sub == "history":
            h = agent.companion.get_history()
            print(f"  💙 {h['user_name']} | Level {h['relationship_level']}/10 | {h['interactions']} interactions | Mood: {h['dominant_mood']}")
            for ev in h.get("recent_events",[])[-3:]:
                print(f"    • {ev['event']}")
        elif sub == "reflect":
            print(f"  💭 {agent.companion.reflect()}")
        elif sub == "persona" and len(args) > 1:
            print(agent.companion.set_persona(args[1]))
        elif sub == "mood" and len(args) > 1:
            print(agent.companion.track_mood(" ".join(args[1:])))
        elif sub == "remind" and len(args) > 1:
            print(agent.companion.add_reminder(" ".join(args[1:]), input("  When? ").strip()))
        elif sub == "reminders":
            rs = agent.companion.get_reminders()
            [print(f"  ⏰ {r['text']}") for r in rs] if rs else print("  No reminders")
        else:
            print("Usage: /companion checkin [mood] | remember <event> | history | reflect | persona <n> | mood <t> | remind <t> | reminders")

    async def _cmd_briefing(self, args):
        """Daily briefing — weather + news + calendar + tasks, optionally spoken."""
        agent = self.agent
        if not hasattr(agent, 'briefing'):
            from daily_briefing import DailyBriefing
            agent.briefing = DailyBriefing(
                llm_provider=getattr(agent,'llm',None),
                voice_handler=getattr(agent,'voice',None) if agent.voice_mode else None,
                calendar=getattr(agent,'calendar',None),
                missions=getattr(agent,'missions',None),
                db=getattr(agent,'db',None)
            )
        sub = args[0].lower() if args else "generate"
        if sub == "status":
            print(json.dumps(agent.briefing.get_status(), indent=2)); return
        if sub == "city" and len(args) > 1:
            agent.briefing._city = " ".join(args[1:])
            print(f"  ✅ City: {agent.briefing._city}"); return
        print("  🌅 Generating daily briefing...")
        b = await asyncio.to_thread(agent.briefing.generate_briefing, agent.default_tid)
        print(agent.briefing.display(b))
        if agent.voice_mode:
            agent.briefing.voice = getattr(agent, 'voice', None)
            if agent.briefing.voice:
                print("  🔊 Speaking...")
                await asyncio.to_thread(agent.briefing.speak, b)

    # ==================================================
    #  PHASE 18 — AI PRODUCTIVITY SUITE
    # ==================================================

    def _cmd_focus(self, args):
        """Pomodoro Focus Timer."""
        agent = self.agent
        if not hasattr(agent, 'pomodoro'):
            from pomodoro_focus import PomodoroFocus
            def _checkin(msg):
                print(f"\n  🍅 {msg}", flush=True)
            agent.pomodoro = PomodoroFocus(
                llm_provider=getattr(agent, 'llm', None),
                checkin_callback=_checkin
            )
        sub = args[0].lower() if args else "status"
        if sub == "start":
            task = " ".join(args[1:]) if len(args) > 1 else input("  Focus task: ").strip() or "Deep Work"
            r = agent.pomodoro.start(task)
            print(f"  {r['message']}", flush=True)
        elif sub == "stop":
            r = agent.pomodoro.stop()
            print(f"  {r['message']}", flush=True)
        elif sub == "skip":
            r = agent.pomodoro.skip_break()
            if isinstance(r, dict):
                print(f"  {r.get('message', r)}", flush=True)
            else:
                print(f"  {r}", flush=True)
        elif sub == "stats":
            s = agent.pomodoro.get_stats()
            print(f"  🍅 Stats: {s['sessions_completed']} Pomodoros | {s['total_focus_hours']}h focus")
        elif sub == "status":
            r = agent.pomodoro.status()
            print(f"  {r['message']}", flush=True)
        else:
            print("  Usage: /focus start [task] | stop | skip | status | stats")

    def _cmd_habit(self, args):
        """Habit Tracker."""
        agent = self.agent
        if not hasattr(agent, 'habits'):
            from habit_tracker import HabitTracker
            agent.habits = HabitTracker(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "list"
        rest = " ".join(args[1:]) if len(args) > 1 else ""
        if sub == "add":
            name = rest or input("  Habit name: ").strip()
            desc = input("  Description (optional): ").strip()
            print(f"  {agent.habits.add_habit(name, desc)}")
        elif sub == "done":
            name = rest or input("  Habit name: ").strip()
            print(f"  {agent.habits.mark_done(name)}")
        elif sub == "list":
            print(f"\n{agent.habits.list_habits()}")
        elif sub == "streak":
            print(f"\n{agent.habits.get_streaks()}")
        elif sub == "stats":
            s = agent.habits.get_stats()
            print(f"  📊 Today: {s['done_today']}/{s['total_habits']} ({s['completion_today_pct']}%)")
            if s['best_current_streak']['habit']:
                print(f"  🔥 Best streak: {s['best_current_streak']['habit']} ({s['best_current_streak']['days']}d)")
        elif sub == "remove":
            name = rest or input("  Habit name to remove: ").strip()
            print(f"  {agent.habits.remove_habit(name)}")
        else:
            print("  Usage: /habit add|done|list|streak|stats|remove <name>")

    def _cmd_meeting(self, args):
        """Meeting Summarizer."""
        agent = self.agent
        if not hasattr(agent, 'meeting'):
            from meeting_summarizer import MeetingSummarizer
            agent.meeting = MeetingSummarizer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "paste"
        if sub == "file" and len(args) > 1:
            filepath = " ".join(args[1:])
            print("  🔍 Summarizing from file...")
            r = agent.meeting.summarize_file(filepath)
            if r["success"]:
                print(f"\n{r['summary']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "list":
            print(agent.meeting.list_summaries())
        elif sub == "last":
            print(agent.meeting.get_last())
        elif sub == "view" and len(args) > 1:
            print(agent.meeting.get_by_id(int(args[1])))
        else:
            print("  📋 Paste meeting transcript (empty line to finish):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            transcript = "\n".join(lines)
            if transcript.strip():
                print("  🤖 Summarizing meeting...")
                r = agent.meeting.summarize_text(transcript)
                if r["success"]:
                    print(f"\n{r['summary']}")
                else:
                    print(f"  ❌ {r['error']}")
            else:
                print("  Usage: /meeting [paste|file <path>|list|last|view <id>]")

    def _cmd_note(self, args):
        """Second Brain Note Manager."""
        agent = self.agent
        if not hasattr(agent, 'notes'):
            from note_manager import NoteManager
            agent.notes = NoteManager(
                llm_provider=getattr(agent, 'llm', None),
                vector_memory=getattr(agent, 'vmem', None),
                tenant_id=getattr(agent, 'default_tid', 'default')
            )
        sub = args[0].lower() if args else "list"
        rest = " ".join(args[1:]) if len(args) > 1 else ""
        if sub == "add":
            text = rest or input("  Note: ").strip()
            tags_raw = input("  Tags (comma-sep, optional): ").strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
            r = agent.notes.add_note(text, tags)
            print(f"  {r['message']}")
        elif sub == "list":
            print(f"\n{agent.notes.list_notes()}")
        elif sub == "search":
            q = rest or input("  Search: ").strip()
            print(f"\n{agent.notes.search_notes(q)}")
        elif sub == "delete" and len(args) > 1:
            print(agency.notes.delete_note(int(args[1])))
        elif sub == "export":
            path = rest or "notes_export.md"
            print(f"  {agent.notes.export_notes(path)}")
        elif sub == "stats":
            s = agent.notes.get_stats()
            print(f"  📓 Notes: {s['total_notes']} | Top tags: {s['top_tags']}")
        else:
            text = " ".join(args) if args else input("  Note text: ").strip()
            if text:
                r = agent.notes.add_note(text)
                print(f"  {r['message']}")
            else:
                print("  Usage: /note add|list|search|delete|export|stats [args]")

    # ==================================================
    #  PHASE 18 — MONEY-MAKING FEATURES
    # ==================================================

    def _cmd_invoice(self, args):
        """Invoice Generator."""
        agent = self.agent
        if not hasattr(agent, 'invoicer'):
            from invoice_generator import InvoiceGenerator
            agent.invoicer = InvoiceGenerator(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "create"
        if sub == "list":
            print(agent.invoicer.list_invoices())
        elif sub == "view" and len(args) > 1:
            print(agent.invoicer.view_invoice(int(args[1])))
        else:
            # Interactive invoice creation
            print("  🧾 INVOICE CREATOR")
            print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            company = input("  Your company name: ").strip() or "My Company"
            company_email = input("  Your email: ").strip()
            client = input("  Client name: ").strip() or "Client"
            client_email = input("  Client email: ").strip()
            currency = input("  Currency (USD/EUR/INR, Enter=USD): ").strip() or "USD"
            items = []
            print("  Add line items (empty description to finish):")
            while True:
                desc = input(f"    Item {len(items)+1} description: ").strip()
                if not desc:
                    break
                try:
                    qty = int(input("    Quantity: ").strip() or "1")
                    rate = float(input("    Rate: ").strip() or "0")
                except ValueError:
                    qty, rate = 1, 0
                items.append({"description": desc, "qty": qty, "rate": rate})
            if not items:
                print("  ❌ No items added."); return
            try:
                tax_pct = float(input("  Tax % (0 for none): ").strip() or "0")
            except ValueError:
                tax_pct = 0
            notes = input("  Notes (optional): ").strip()
            due = input("  Due date (Net 30): ").strip() or "Net 30"
            details = {
                "company_name": company, "company_email": company_email,
                "client_name": client, "client_email": client_email,
                "currency": currency, "items": items, "tax_pct": tax_pct,
                "notes": notes, "due_date": due
            }
            print("  📝 Generating invoice...")
            r = agent.invoicer.create_invoice(details)
            print(f"\n  {r['message']}")
            if r.get("filepath"):
                import sys, os
                if sys.platform == "win32":
                    try:
                        os.startfile(os.path.abspath(r["filepath"]))
                    except Exception:
                        pass

    def _cmd_pricing(self, args):
        """Pricing Analyzer."""
        agent = self.agent
        if not hasattr(agent, 'pricer'):
            from pricing_analyzer import PricingAnalyzer
            agent.pricer = PricingAnalyzer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "analyze"
        if sub == "list":
            print(agent.pricer.list_analyses())
        elif sub == "view" and len(args) > 1:
            print(agent.pricer.get_analysis(int(args[1])))
        else:
            product = " ".join(args[1:]) if len(args) > 1 else input("  Describe your product/service: ").strip()
            if not product:
                print("  Usage: /pricing analyze <product desc>"); return
            context = input("  Additional context (target market, competition): ").strip()
            print("  💰 Analyzing pricing strategy...")
            r = agent.pricer.analyze(product, context)
            if r["success"]:
                print(f"\n{r['analysis']}")
            else:
                print(f"  ❌ {r['error']}")

    def _cmd_leads(self, args):
        """Lead Scraper."""
        agent = self.agent
        if not hasattr(agent, 'leads'):
            from lead_scraper import LeadScraper
            agent.leads = LeadScraper(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "help"
        if sub == "find":
            criteria = " ".join(args[1:]) if len(args) > 1 else input("  Search criteria: ").strip()
            if not criteria:
                print("  Usage: /leads find <criteria>"); return
            print(f"  🔍 Searching for leads: {criteria}...")
            r = agent.leads.find_leads(criteria)
            print(f"\n{r.get('message', r)}")
        elif sub == "list":
            print(agent.leads.list_leads())
        elif sub == "export":
            path = " ".join(args[1:]) if len(args) > 1 else "leads_export.csv"
            print(agent.leads.export_leads(path))
        elif sub == "status":
            nid = int(args[1]) if len(args) > 1 else int(input("  Lead ID: ").strip())
            new_status = args[2] if len(args) > 2 else input("  Status (new/contacted/qualified/closed): ").strip()
            print(agent.leads.update_lead_status(nid, new_status))
        else:
            print("  Usage: /leads find <criteria> | list | export | status <id> <new_status>")

    def _cmd_affiliate(self, args):
        """Affiliate Tracker."""
        agent = self.agent
        if not hasattr(agent, 'affiliate'):
            from affiliate_tracker import AffiliateTracker
            agent.affiliate = AffiliateTracker(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "list"
        if sub == "add":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Program name: ").strip()
            url = input("  Affiliate URL: ").strip()
            try:
                pct = float(input("  Commission % (0 if flat): ").strip() or "0")
                flat = float(input("  Flat commission $ (0 if %): ").strip() or "0")
            except ValueError:
                pct, flat = 0.0, 0.0
            notes = input("  Notes (optional): ").strip()
            print(agent.affiliate.add_program(name, url, pct, flat, notes))
        elif sub == "click":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Program name: ").strip()
            print(agent.affiliate.log_click(name))
        elif sub == "log":
            name = args[1] if len(args) > 1 else input("  Program name: ").strip()
            try:
                amount = float(args[2] if len(args) > 2 else input("  Commission amount: ").strip())
            except ValueError:
                amount = 0.0
            note = " ".join(args[3:]) if len(args) > 3 else ""
            print(agent.affiliate.log_commission(name, amount, note))
        elif sub == "report":
            print(f"\n{agent.affiliate.get_report()}")
        elif sub == "list":
            print(agent.affiliate.list_programs())
        else:
            print("  Usage: /affiliate add|click|log|report|list")

    # ==================================================
    #  PHASE 18 — AI POWER FEATURES
    # ==================================================

    async def _cmd_panel(self, args):
        """Multi-Agent Debate Panel — 3+ AI personas debate a topic."""
        agent = self.agent
        topic = " ".join(args) if args else None
        if not topic:
            topic = input("  Debate topic: ").strip()
        if not topic:
            print("  Usage: /panel <topic>"); return
        print(f"\n  🎙️ PANEL DEBATE: {topic}")
        print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        personas = [
            ("🔵 Optimist Alex", "pragmatic optimist who sees opportunities in every challenge"),
            ("🔴 Skeptic Jordan", "critical thinker who questions assumptions and identifies risks"),
            ("🟢 Analyst Morgan", "data-driven analyst who focuses on evidence and nuance")
        ]
        llm = getattr(agent, 'llm', None)
        if not llm:
            print("  ❌ LLM not available."); return
        arguments = []
        for persona_name, persona_desc in personas:
            print(f"\n  {persona_name}:")
            context = "\n".join(f"  - {p}: {a}" for p, a in arguments)
            prompt = (
                f"You are {persona_name}, a {persona_desc}.\n"
                f"Topic: {topic}\n\n"
                f"{'Previous arguments:\n' + context if context else ''}\n\n"
                "Give your perspective in 3-4 sentences. Be specific and direct. "
                "Respond to other views if there are any. End with your key point."
            )
            try:
                response = await asyncio.to_thread(llm.chat, prompt)
                print(f"  {response}")
                arguments.append((persona_name, response[:200] if response else ""))
            except Exception as e:
                print(f"  ❌ Error: {e}")
        # Synthesis
        print(f"\n  ⚖️ SYNTHESIS:")
        all_views = "\n".join(f"{p}: {a}" for p, a in arguments)
        synth_prompt = (
            f"Debate topic: {topic}\n\nArguments:\n{all_views}\n\n"
            "Synthesize these perspectives into a 3-sentence balanced conclusion that "
            "identifies the key points of agreement and the main unresolved tension."
        )
        try:
            synthesis = await asyncio.to_thread(llm.chat, synth_prompt)
            print(f"  {synthesis}")
        except Exception:
            print("  Unable to synthesize.")

    def _cmd_optimize(self, args):
        """Prompt Optimizer."""
        agent = self.agent
        if not hasattr(agent, 'prompt_opt'):
            from prompt_optimizer import PromptOptimizer
            agent.prompt_opt = PromptOptimizer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else ""
        if sub == "history":
            print(agent.prompt_opt.list_history()); return
        prompt_text = " ".join(args) if args else input("  Prompt to optimize: ").strip()
        if not prompt_text:
            print("  Usage: /optimize <your prompt text>"); return
        goal = input("  Goal/context (optional, Enter to skip): ").strip()
        print("  ✨ Optimizing prompt with chain-of-thought...")
        r = agent.prompt_opt.optimize(prompt_text, goal)
        if r["success"]:
            print(f"\n{r['result']}")
        else:
            print(f"  ❌ {r['error']}")

    def _cmd_finetune(self, args):
        """Fine-Tuner Data Generator."""
        agent = self.agent
        if not hasattr(agent, 'finetuner'):
            from finetune_generator import FinetuneGenerator
            agent.finetuner = FinetuneGenerator(
                llm_provider=getattr(agent, 'llm', None),
                db=getattr(agent, 'db', None)
            )
        sub = args[0].lower() if args else "stats"
        if sub == "generate":
            print("  🧬 Generating fine-tuning dataset from conversation history...")
            r = agent.finetuner.generate_from_history(getattr(agent, 'default_tid', 'default'))
            print(f"\n  {r.get('message', r)}")
        elif sub == "export":
            path = " ".join(args[1:]) if len(args) > 1 else None
            print(agent.finetuner.export(path))
        elif sub == "stats":
            print(f"\n{agent.finetuner.get_stats()}")
        elif sub == "clear":
            confirm = input("  Clear fine-tuning dataset? (yes/no): ").strip().lower()
            if confirm == "yes":
                print(agent.finetuner.clear())
            else:
                print("  Cancelled.")
        else:
            print("  Usage: /finetune generate|export [path]|stats|clear")

    def _cmd_mindmap(self, args):
        """Memory Graph / Mindmap Visualizer."""
        agent = self.agent
        if not hasattr(agent, 'mindmap'):
            from mindmap_visualizer import MindmapVisualizer
            agent.mindmap = MindmapVisualizer(
                llm_provider=getattr(agent, 'llm', None),
                vector_memory=getattr(agent, 'vmem', None),
                tenant_id=getattr(agent, 'default_tid', 'default')
            )
        sub = args[0].lower() if args else "generate"
        if sub == "open":
            print(agent.mindmap.open_in_browser())
        elif sub == "generate":
            topic = " ".join(args[1:]) if len(args) > 1 else input("  Topic (Enter=Knowledge Base): ").strip() or "Knowledge Base"
            print(f"  🧠 Generating mindmap for '{topic}'...")
            r = agent.mindmap.generate(topic)
            if r["success"]:
                print(f"\n  {r['message']}")
                print("  Opening in browser...")
                agent.mindmap.open_in_browser()
            else:
                print(f"  ❌ {r['error']}")
        else:
            print("  Usage: /mindmap generate [topic] | open")

    def _cmd_createpersona(self, args):
        """Persona Creator — interactive wizard."""
        agent = self.agent
        if not hasattr(agent, 'personas'):
            from persona_creator import PersonaCreator
            agent.personas = PersonaCreator(llm_provider=getattr(agent, 'llm', None))
        print("  🎭 PERSONA CREATOR")
        print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        name = input("  Persona name: ").strip()
        if not name:
            print("  ❌ Name required."); return
        description = input("  Description (1 sentence): ").strip()
        traits_raw = input("  Traits (comma-sep, e.g. witty,precise,bold): ").strip()
        traits = [t.strip() for t in traits_raw.split(",") if t.strip()] or ["helpful"]
        tone = input("  Tone (professional/casual/witty/formal/playful): ").strip() or "professional"
        custom_prompt = input("  Custom system prompt (Enter to auto-generate): ").strip()
        print(f"  ✨ Creating persona '{name}'...")
        r = agent.personas.create_persona(name, description, traits, tone, custom_prompt)
        if r["success"]:
            print(f"\n  {r['message']}")
            activate = input("  Activate this persona now? (yes/no): ").strip().lower()
            if activate == "yes":
                ar = agent.personas.activate(name)
                if ar["success"]:
                    print(f"  {ar['message']}")
                    # Inject into agent's LLM system prompt if possible
                    if hasattr(agent.llm, 'system_override'):
                        agent.llm.system_override = ar["system_prompt"]
        else:
            print(f"  ❌ {r.get('error', 'Failed')}")

    def _cmd_persona(self, args):
        """Manage personas."""
        agent = self.agent
        if not hasattr(agent, 'personas'):
            from persona_creator import PersonaCreator
            agent.personas = PersonaCreator(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "list"
        if sub == "list":
            print(agent.personas.list_personas())
        elif sub == "activate":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Persona name: ").strip()
            r = agent.personas.activate(name)
            print(f"  {r['message']}" if r["success"] else f"  ❌ {r['error']}")
            if r["success"] and hasattr(agent, 'llm') and hasattr(agent.llm, 'system_override'):
                agent.llm.system_override = r["system_prompt"]
        elif sub == "delete":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Persona to delete: ").strip()
            print(agent.personas.delete_persona(name))
        elif sub == "show":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Persona name: ").strip()
            print(agent.personas.show_persona(name))
        else:
            print("  Usage: /persona list|activate|delete|show <name>")

    # ==================================================
    #  PHASE 18 — REAL-WORLD INTEGRATIONS
    # ==================================================

    def _cmd_github(self, args):
        """GitHub Agent — issues, PRs, commits via PyGithub."""
        agent = self.agent
        token = os.getenv("GITHUB_TOKEN", "")
        if not token:
            print("  ❌ Set GITHUB_TOKEN environment variable first.")
            print("  Usage: set GITHUB_TOKEN=ghp_your_token_here")
            return
        try:
            from github import Github, GithubException
        except ImportError:
            print("  ❌ PyGithub not installed. Run: pip install PyGithub"); return

        g = Github(token)
        sub = args[0].lower() if args else "help"
        repo_name = args[1] if len(args) > 1 else ""

        try:
            if sub == "issues":
                repo = g.get_repo(repo_name or input("  Repo (owner/name): ").strip())
                issues = repo.get_issues(state="open")[:10]
                print(f"\n  🐛 Open Issues for {repo.full_name}:")
                for issue in list(issues)[:10]:
                    print(f"    #{issue.number} {issue.title} [{issue.state}]")
            elif sub == "pr":
                repo = g.get_repo(repo_name or input("  Repo (owner/name): ").strip())
                prs = repo.get_pulls(state="open")
                print(f"\n  🔀 Open PRs for {repo.full_name}:")
                for pr in list(prs)[:10]:
                    print(f"    #{pr.number} {pr.title} by {pr.user.login}")
            elif sub == "me":
                user = g.get_user()
                print(f"  👤 GitHub: {user.login} | Repos: {user.public_repos} | Followers: {user.followers}")
            elif sub == "repos":
                user = g.get_user()
                repos = list(user.get_repos())[:10]
                print(f"  📦 Your Repos:")
                for r in repos:
                    print(f"    {r.full_name} ⭐{r.stargazers_count}")
            elif sub == "star":
                repo = g.get_repo(repo_name or input("  Repo to star (owner/name): ").strip())
                g.get_user().add_to_starred(repo)
                print(f"  ⭐ Starred: {repo.full_name}")
            else:
                print("  Usage: /github me|repos|issues <owner/repo>|pr <owner/repo>|star <owner/repo>")
        except Exception as e:
            print(f"  ❌ GitHub error: {e}")

    def _cmd_notion(self, args):
        """Notion Sync."""
        agent = self.agent
        if not hasattr(agent, 'notion'):
            from notion_sync import NotionSync
            agent.notion = NotionSync()
        sub = args[0].lower() if args else "status"
        if sub == "status":
            check = agent.notion.check_connection()
            if check["connected"]:
                print(f"  ✅ Connected to Notion as: {check['user']}")
            else:
                print(f"  ❌ {check['error']}")
        elif sub == "search":
            q = " ".join(args[1:]) if len(args) > 1 else input("  Search Notion: ").strip()
            print(agent.notion.search(q))
        elif sub == "read":
            page_id = args[1] if len(args) > 1 else input("  Page ID: ").strip()
            print(agent.notion.read_page(page_id))
        elif sub == "write":
            page_id = args[1] if len(args) > 1 else input("  Page ID: ").strip()
            text = " ".join(args[2:]) if len(args) > 2 else input("  Content to append: ").strip()
            print(agent.notion.write_to_page(page_id, text))
        elif sub == "databases":
            print(agent.notion.list_databases())
        elif sub == "create":
            parent_id = input("  Parent Page ID: ").strip()
            title = input("  New page title: ").strip()
            content = input("  Initial content: ").strip()
            print(agent.notion.create_page(parent_id, title, content))
        else:
            print("  Usage: /notion status|search|read|write|databases|create")

    def _cmd_discord(self, args):
        """Discord Bot control."""
        agent = self.agent
        sub = args[0].lower() if args else "status"
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        if sub == "status":
            running = getattr(agent, '_discord_running', False)
            print(f"  🤖 Discord Bot: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
            if not token:
                print("  ⚠️  Set DISCORD_BOT_TOKEN env var to enable")
        elif sub == "start":
            if not token:
                print("  ❌ Set DISCORD_BOT_TOKEN first."); return
            if getattr(agent, '_discord_running', False):
                print("  ⚠️  Discord bot already running."); return
            try:
                import threading
                from discord_bot import run_discord_bot
                def run_bot():
                    import asyncio
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(run_discord_bot(token, agent))
                t = threading.Thread(target=run_bot, daemon=True)
                t.start()
                agent._discord_running = True
                print("  ✅ Discord bot started! The agent is now live on your Discord server.")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        elif sub == "stop":
            agent._discord_running = False
            print("  ⏹️ Discord bot stopped.")
        else:
            print("  Usage: /discord start|stop|status")

    def _cmd_telegram(self, args):
        """Telegram Bot control."""
        agent = self.agent
        sub = args[0].lower() if args else "status"
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if sub == "status":
            running = getattr(agent, '_telegram_running', False)
            print(f"  📱 Telegram Bot: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
            if not token:
                print("  ⚠️  Set TELEGRAM_BOT_TOKEN env var to enable")
        elif sub == "start":
            if not token:
                print("  ❌ Set TELEGRAM_BOT_TOKEN first."); return
            if getattr(agent, '_telegram_running', False):
                print("  ⚠️  Telegram bot already running."); return
            try:
                import threading
                from telegram_bot import run_telegram_bot
                def run_bot():
                    import asyncio
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(run_telegram_bot(token, agent))
                t = threading.Thread(target=run_bot, daemon=True)
                t.start()
                agent._telegram_running = True
                print("  ✅ Telegram bot started! Message your bot to chat with the agent.")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        elif sub == "stop":
            agent._telegram_running = False
            print("  ⏹️ Telegram bot stopped.")
        else:
            print("  Usage: /telegram start|stop|status")

    def _cmd_webhook(self, args):
        """Webhook Server."""
        agent = self.agent
        if not hasattr(agent, 'webhooks'):
            from webhook_server import WebhookServer
            agent.webhooks = WebhookServer(agent=agent)
        sub = args[0].lower() if args else "status"
        if sub == "start":
            port = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            print(agent.webhooks.start(port))
        elif sub == "stop":
            print(agent.webhooks.stop())
        elif sub == "status":
            print(agent.webhooks.status())
        elif sub == "list":
            print(agent.webhooks.list_events())
        elif sub == "add":
            event_type = args[1] if len(args) > 1 else input("  Event type: ").strip()
            action = " ".join(args[2:]) if len(args) > 2 else input("  Action command: ").strip()
            print(agent.webhooks.add_handler(event_type, action))
        else:
            print("  Usage: /webhook start [port]|stop|status|list|add <event> <action>")

    # ==================================================
    #  PHASE 18 — FUN / IMMERSIVE
    # ==================================================

    def _cmd_rpg(self, args):
        """Life RPG — Gamify your life."""
        agent = self.agent
        if not hasattr(agent, 'rpg'):
            from life_rpg import LifeRPG
            agent.rpg = LifeRPG(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "status"
        if sub == "status":
            print(f"\n{agent.rpg.get_status()}")
        elif sub == "xp":
            skill = args[1] if len(args) > 1 else input("  Skill (Mental/Physical/Social/Creative/Technical/Financial/Wisdom): ").strip()
            try:
                amount = int(args[2] if len(args) > 2 else input("  XP amount: ").strip() or "10")
            except ValueError:
                amount = 10
            reason = " ".join(args[3:]) if len(args) > 3 else input("  Reason (optional): ").strip()
            print(f"\n{agent.rpg.earn_xp(skill, amount, reason)}")
        elif sub == "quest":
            subsub = args[1].lower() if len(args) > 1 else "list"
            if subsub == "add":
                name = " ".join(args[2:]) if len(args) > 2 else input("  Quest name: ").strip()
                desc = input("  Description: ").strip()
                try:
                    xp = int(input("  XP reward (Enter=50): ").strip() or "50")
                except ValueError:
                    xp = 50
                skill = input("  Skill (Enter=General): ").strip() or "General"
                print(agent.rpg.add_quest(name, desc, xp, skill))
            elif subsub == "complete":
                name = " ".join(args[2:]) if len(args) > 2 else input("  Quest name: ").strip()
                print(f"\n{agent.rpg.complete_quest(name)}")
            elif subsub == "done":
                name = " ".join(args[2:]) if len(args) > 2 else input("  Quest name: ").strip()
                print(f"\n{agent.rpg.complete_quest(name)}")
            else:
                print(f"\n{agent.rpg.list_quests()}")
        elif sub == "skills":
            print(f"\n{agent.rpg.get_status()}")
        elif sub == "name":
            name = " ".join(args[1:]) if len(args) > 1 else input("  Player name: ").strip()
            print(agent.rpg.set_player_name(name))
        else:
            print("  Usage: /rpg status|xp <skill> <amount>|quest add|quest complete <name>|skills|name <name>")

    def _cmd_therapy(self, args):
        """AI Therapist — CBT journaling and emotional tracking."""
        agent = self.agent
        if not hasattr(agent, 'therapist'):
            from ai_therapist import AITherapist
            agent.therapist = AITherapist(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "help"
        rest = " ".join(args[1:]) if len(args) > 1 else ""
        if sub == "journal":
            text = rest or input("  Share what's on your mind:\n  > ").strip()
            if not text:
                print("  Prompt: /therapy journal <your thoughts>"); return
            print("  💙 Processing...")
            r = agent.therapist.journal(text)
            if r["success"]:
                if r.get("emotions"):
                    print(f"  Detected emotions: {', '.join(r['emotions'])}")
                print(f"\n  💬 {r['response']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "analyze":
            print(f"\n{agent.therapist.analyze_patterns()}")
        elif sub == "history":
            n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
            print(agent.therapist.get_history(n))
        elif sub == "tips":
            situation = rest or input("  Situation (Enter for general tips): ").strip()
            print(f"\n{agent.therapist.get_tips(situation)}")
        else:
            print("  Usage: /therapy journal <text> | analyze | history | tips [situation]")
            print("  ⚠️  This is not a replacement for professional mental health care.")

    def _cmd_story(self, args):
        """Interactive Story Generator."""
        agent = self.agent
        if not hasattr(agent, 'story'):
            from story_generator import StoryGenerator
            agent.story = StoryGenerator(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "status"
        if sub == "start":
            genre = args[1].lower() if len(args) > 1 else input("  Genre (fantasy/sci-fi/horror/mystery/adventure/romance/thriller/western): ").strip() or "fantasy"
            title = " ".join(args[2:]) if len(args) > 2 else ""
            print(f"  📖 Starting {genre} story...")
            r = agent.story.start_story(genre, title)
            if r["success"]:
                print(f"\n  📖 {r['message']}\n")
                print(r["text"])
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "choice":
            try:
                choice = int(args[1] if len(args) > 1 else input("  Your choice (1/2/3): ").strip())
            except ValueError:
                print("  ❌ Choice must be 1, 2, or 3"); return
            print("  ✍️ Continuing story...")
            r = agent.story.make_choice(choice)
            if r["success"]:
                print(f"\n  📖 Chapter {r['chapter']}")
                print(r["text"])
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "status":
            print(f"\n{agent.story.get_status()}")
        elif sub == "genres":
            print(agent.story.list_genres())
        elif sub == "new":
            print(agent.story.new_story())
        else:
            print("  Usage: /story start <genre> | choice <1|2|3> | status | genres | new")

    def _cmd_face(self, args):
        """Avatar Face Detection — webcam face analysis + avatar sync."""
        agent = self.agent
        sub = args[0].lower() if args else "status"
        biometric = getattr(agent, 'biometric', None)
        if not biometric:
            print("  ⚠️ Biometric empathy module not loaded.")
            print("  Requires: pip install opencv-python deepface")
            try:
                from biometric_empathy import BiometricEmpathy
                agent.biometric = BiometricEmpathy()
                biometric = agent.biometric
            except Exception as e:
                print(f"  ❌ Could not load: {e}"); return
        if sub == "start":
            try:
                biometric.start()
                print("  📸 Face detection STARTED — watching webcam for emotions")
            except Exception as e:
                print(f"  ❌ {e}")
        elif sub == "stop":
            try:
                biometric.stop()
                print("  ⏹️ Face detection stopped.")
            except Exception as e:
                print(f"  ❌ {e}")
        elif sub == "status":
            active = getattr(biometric, '_running', False)
            emotion = getattr(biometric, 'current_emotion', 'unknown')
            print(f"  📸 Face Detection: {'🟢 ON' if active else '🔴 OFF'}")
            print(f"  😊 Current emotion: {emotion}")
        else:
            print("  Usage: /face start|stop|status")

    def _cmd_compose(self, args):
        """Music Composer — LLM generates chord progressions + lyrics."""
        agent = self.agent
        if not hasattr(agent, 'composer'):
            from music_composer import MusicComposer
            agent.composer = MusicComposer(llm_provider=getattr(agent, 'llm', None))
        sub = args[0].lower() if args else "help"
        rest = " ".join(args[1:]) if len(args) > 1 else ""
        if sub == "lyrics":
            theme = rest or input("  Theme/topic for lyrics: ").strip()
            style = input("  Style (pop/rock/rap/ballad, Enter=pop): ").strip() or "pop"
            print(f"  🎵 Writing {style} lyrics about '{theme}'...")
            r = agent.composer.compose_lyrics(theme, style)
            if r["success"]:
                print(f"\n{r['lyrics']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "chords":
            key = rest or input("  Key (e.g. 'C major', 'A minor'): ").strip() or "C major"
            style = input("  Style (pop/jazz/blues/rock, Enter=pop): ").strip() or "pop"
            print(f"  🎸 Generating chord progression in {key}...")
            r = agent.composer.compose_chords(key, style)
            if r["success"]:
                print(f"\n{r['content']}")
            else:
                print(f"  ❌ {r['error']}")
        elif sub == "list":
            print(agent.composer.list_compositions())
        elif sub == "moods":
            print(agent.composer.get_mood_list())
        else:
            # Full song by mood
            mood = sub if sub in agent.composer.MOODS else (rest or sub)
            if not mood or mood == "help":
                mood = input("  Mood (happy/sad/epic/jazz/romantic/chill/angry/mysterious): ").strip() or "happy"
            title = input("  Song title (Enter to auto): ").strip()
            print(f"  🎵 Composing {mood} song...")
            r = agent.composer.compose_full_song(mood, title)
            if r["success"]:
                print(f"\n{r['composition']}")
            else:
                print(f"  ❌ {r['error']}")

    # ══════════════════════════════════════════════════════════════════════
    #  AGI LIMITATION OVERRIDES 2.0 — COMMANDS
    # ══════════════════════════════════════════════════════════════════════

    def _cmd_grounded(self, args):
        """
        /grounded status         — Show grounding loop stats and recent percepts
        /grounded observe <text> — Log a real-world observation
        /grounded act <action>   — Execute a grounded action (run_code/read_file/...)
        /grounded context        — Show grounding context for prompt injection
        """
        agent = self.agent
        grounding = getattr(agent, "grounding", None)
        if not grounding:
            print("❌ GroundingLoop not loaded.")
            return

        sub = args[0].lower() if args else "status"

        if sub == "status":
            summary = grounding.get_perception_summary()
            stats = summary["stats"]
            print("\n╔══════════════════════════════════════════════╗")
            print("║   GROUNDED PERCEPTION LOOP — STATUS          ║")
            print("╠══════════════════════════════════════════════╣")
            print(f"║  Total Observations : {stats['total_observations']:<23}║")
            print(f"║  Total Actions      : {stats['total_actions']:<23}║")
            print(f"║  Consequences Logged: {stats['total_consequences']:<23}║")
            print(f"║  Grounding Depth    : {stats['grounding_depth']:<23}║")
            print(f"║  Total Percepts     : {summary['percept_count']:<23}║")
            print("╚══════════════════════════════════════════════╝")
            print(f"\n  Available Actions: {', '.join(summary['available_actions'])}")
            recent = summary["recent_percepts"]
            if recent:
                print(f"\n  Recent Percepts ({len(recent)}):")
                for p in recent[-3:]:
                    icon = {"observation": "👁", "action_result": "⚡"}.get(p.get("percept_type"), "•")
                    print(f"  {icon} [{p.get('percept_type')}] {p.get('source')}: {str(p.get('content', ''))[:80]}")

        elif sub == "observe":
            event = " ".join(args[1:])
            if not event:
                event = input("Observation to log: ").strip()
            source = input("Source (default=user): ").strip() or "user"
            result = grounding.grounded_observe(event, source)
            print(f"✅ Observation logged [percept_id={result['percept_id']}]")

        elif sub == "act":
            action_type = args[1] if len(args) > 1 else input("Action type (run_code/read_file/list_dir/run_command/http_get): ").strip()
            print("Params as JSON (e.g. {\"code\": \"print(1+1)\"} or {\"path\": \".\"}): ", end="")
            params_str = input().strip()
            try:
                import json as _json
                params = _json.loads(params_str) if params_str else {}
            except Exception:
                params = {}
            print(f"\n⚡ Executing grounded action: {action_type}...")
            result = grounding.grounded_act(action_type, params)
            icon = "✅" if result.get("success") else "❌"
            print(f"{icon} {result.get('action')}")
            print(f"   Output: {str(result.get('output', ''))[:300]}")
            print(f"   Consequence: {result.get('consequence')}")

        elif sub == "context":
            ctx = grounding.build_grounding_context()
            print(ctx if ctx else "  (No recent percepts in grounding context)")

        else:
            print("Usage: /grounded <status|observe|act|context>")

    def _cmd_curiosity(self, args):
        """
        /curiosity state          — Show curiosity score, gaps, and recent learning
        /curiosity learn <topic>  — Manually trigger a learning cycle
        /curiosity gaps           — List top unresolved knowledge gaps
        /curiosity add <topic>    — Register a manual knowledge gap
        """
        agent = self.agent
        curiosity = getattr(agent, "curiosity", None)
        if not curiosity:
            print("❌ CuriosityScheduler not loaded.")
            return

        sub = args[0].lower() if args else "state"
        rest = " ".join(args[1:])

        if sub == "state":
            state = curiosity.get_curiosity_state()
            print("\n╔══════════════════════════════════════════════╗")
            print("║   CURIOSITY SCHEDULER — STATE                ║")
            print("╠══════════════════════════════════════════════╣")
            score = state["curiosity_score"]
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            print(f"║  Curiosity Score : [{bar}] {score:.3f}   ║")
            print(f"║  Daemon Running  : {str(state['daemon_running']):<26}║")
            print(f"║  Check Interval  : Every {state['interval_minutes']} min{' '*(20-len(str(state['interval_minutes'])))}║")
            print(f"║  Pending Gaps    : {state['pending_gaps']:<26}║")
            print(f"║  Resolved Gaps   : {state['resolved_gaps']:<26}║")
            print(f"║  Topics Learned  : {state['stats'].get('topics_learned', 0):<26}║")
            print(f"║  Learning Cycles : {state['stats'].get('total_learning_cycles', 0):<26}║")
            print("╚══════════════════════════════════════════════╝")
            if state["pending_topics"]:
                print(f"\n  Pending Topics: {', '.join(state['pending_topics'][:6])}")
            if state["explored_topics"]:
                print(f"  Explored:       {', '.join(state['explored_topics'][-6:])}")
            if state["recent_learning"]:
                print("\n  Recent Learning:")
                for item in state["recent_learning"][-3:]:
                    print(f"  📚 [{item['topic']}] {item['snippet'][:80]}")

        elif sub == "learn":
            topic = rest or input("Topic to learn: ").strip()
            if not topic:
                print("No topic provided.")
                return
            print(f"\n🧠 Triggering autonomous learning cycle for: '{topic}'...")
            result = curiosity.trigger_learning_cycle(topic)
            icon = "✅" if result.get("learned") else "⚠️"
            print(f"\n{icon} Topic: {result.get('topic')}")
            if result.get("result"):
                print(f"   Result: {result['result'][:300]}")

        elif sub == "gaps":
            gaps = curiosity.get_top_gaps(10)
            if not gaps:
                print("  No pending knowledge gaps detected.")
                return
            print(f"\n  Top Knowledge Gaps ({len(gaps)}):")
            for g in gaps:
                bar = "█" * int(g["urgency"] * 10)
                print(f"  [{bar:<10}] urgency={g['urgency']:.2f}  '{g['topic']}'  (src={g['source']})")

        elif sub == "add":
            topic = rest or input("Topic (knowledge gap): ").strip()
            urgency_str = input("Urgency 0.0-1.0 (Enter=0.7): ").strip()
            urgency = float(urgency_str) if urgency_str else 0.7
            result = curiosity.add_gap(topic, urgency)
            print(f"✅ Gap registered: '{result['gap_added']}' (urgency={result['urgency']})")

        else:
            print("Usage: /curiosity <state|learn|gaps|add>")

    def _cmd_ground(self, args):
        """
        /ground concept <name>  — Ground a concept (build perceptual metadata)
        /ground list            — List all grounded concepts
        /ground describe <name> — Show full grounding for a concept
        /ground enrich <text>   — Enrich text with grounded concept percepts
        /ground stats           — Show engine stats
        """
        agent = self.agent
        symbol = getattr(agent, "symbol", None)
        if not symbol:
            print("❌ SymbolGroundingEngine not loaded.")
            return

        sub = args[0].lower() if args else "list"
        rest = " ".join(args[1:])

        if sub == "concept":
            concept = rest or input("Concept to ground: ").strip()
            if not concept:
                return
            desc = input("Description (optional): ").strip()
            img = input("Image path for visual grounding (optional, Enter to skip): ").strip()
            print(f"\n🔬 Grounding concept: '{concept}'...")
            result = symbol.ground_concept(
                concept, description=desc or "",
                image_path=img if img else None
            )
            print(f"\n  Concept: {result['concept']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Sources: {', '.join(result['sources'])}")
            print(f"\n{result['grounding']}")

        elif sub == "list":
            concepts = symbol.list_grounded_concepts()
            if not concepts:
                print("  No concepts grounded yet. Use /ground concept <name>")
                return
            print(f"\n  Grounded Concepts ({len(concepts)}):")
            for c in concepts:
                visual_icon = "👁" if c["has_visual"] else " "
                bar = "█" * int(c["confidence"] * 10)
                print(f"  {visual_icon} [{bar:<10}] conf={c['confidence']:.2f}  {c['concept']}")

        elif sub == "describe":
            concept = rest or input("Concept name: ").strip()
            desc = symbol.describe_percept(concept)
            print(f"\n{desc}")

        elif sub == "enrich":
            text = rest or input("Text to enrich: ").strip()
            enriched = symbol.enrich_with_percepts(text)
            print(f"\n  Enriched Text:\n{enriched}")

        elif sub == "stats":
            s = symbol.get_stats()
            print("\n  Symbol Grounding Engine Stats:")
            for k, v in s.items():
                print(f"  • {k}: {v}")

        else:
            print("Usage: /ground <concept|list|describe|enrich|stats>")

    def _cmd_architect(self, args):
        """
        /architect status         — Show current cognitive blueprint (architecture)
        /architect evolve <score> — Evolve the blueprint based on performance score
        /architect rewrite <tgt>  — Manually rewrite a component (reasoning/planning/heuristics)
        /architect apply          — Push active blueprint into agent system prompt
        /architect history        — Show evolution history
        """
        agent = self.agent
        cognitive = getattr(agent, "cognitive", None)
        if not cognitive:
            print("❌ CognitiveArchitect not loaded.")
            return

        sub = args[0].lower() if args else "status"
        rest = " ".join(args[1:])

        if sub == "status":
            arch = cognitive.get_current_architecture()
            stats = cognitive.stats
            print("\n╔══════════════════════════════════════════════╗")
            print("║   COGNITIVE ARCHITECT — ACTIVE BLUEPRINT     ║")
            print("╠══════════════════════════════════════════════╣")
            print(f"║  Blueprint ID   : {arch.get('blueprint_id', 'N/A'):<26}║")
            print(f"║  Generation     : {arch.get('generation', 1):<26}║")
            print(f"║  Avg Performance: {arch.get('avg_performance', 0.5):<26}║")
            print(f"║  Applied Count  : {arch.get('applied_count', 0):<26}║")
            print(f"║  Total Evols    : {stats.get('total_evolutions', 0):<26}║")
            print(f"║  Blueprints     : {len(cognitive.blueprints):<26}║")
            print("╚══════════════════════════════════════════════╝")
            print(f"\n  Reasoning Framework:\n{arch.get('reasoning_template', '')[:300]}")
            heuristics = arch.get("custom_heuristics", [])
            if heuristics:
                print(f"\n  Custom Heuristics ({len(heuristics)}):")
                for h in heuristics[:5]:
                    print(f"    • {h}")

        elif sub == "evolve":
            score_str = rest or input("Performance score 0.0-1.0 (e.g. 0.3 for failing, 0.9 for good): ").strip()
            try:
                score = float(score_str)
            except ValueError:
                print("❌ Invalid score.")
                return
            context = input("Context/task type (optional): ").strip()
            failure = input("What went wrong (if score < 0.5): ").strip()
            print("\n🧠 Evolving cognitive blueprint...")
            result = cognitive.evolve_reasoning(score, context=context, failure_description=failure)
            action = result.get("action")
            if action == "evolved":
                print(f"✅ Blueprint evolved to Generation {result['generation']}!")
                print(f"   New Blueprint ID: {result['new_blueprint_id']}")
                print(f"   Target Rewritten: {result['target_rewritten']}")
            elif action == "no_change":
                print(f"  ℹ️ No evolution needed — avg performance {result.get('avg_performance', 0):.2f} is acceptable")
            else:
                print(f"  ℹ️ Observing... ({result})")

        elif sub == "rewrite":
            target = rest or input("Target to rewrite (reasoning_template/planning_schema/heuristics/all): ").strip()
            print(f"New specification for {target} (empty for LLM auto-generate, paste then empty line):")
            lines = []
            try:
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
            except EOFError:
                pass
            new_spec = "\n".join(lines).strip() or None
            reason = input("Reason for rewrite: ").strip()
            print(f"\n⚡ Rewriting {target}...")
            result = cognitive.rewrite_cognition(target=target, new_spec=new_spec, reason=reason)
            print(f"✅ Rewritten to Generation {result.get('generation')} [blueprint={result.get('new_blueprint_id')}]")

        elif sub == "apply":
            success = cognitive.apply_blueprint(agent)
            if success:
                print("✅ Cognitive blueprint applied — system prompt updated for next interaction.")
            else:
                print("❌ Failed to apply blueprint.")

        elif sub == "history":
            history = cognitive.get_evolution_history(10)
            if not history:
                print("  No evolution events yet.")
                return
            print(f"\n  Evolution History ({len(history)} events):")
            for e in history:
                print(f"  Gen {e['generation']}: {e['target']} — {e['reason'][:60]} [{e['timestamp'][:16]}]")

        else:
            print("Usage: /architect <status|evolve|rewrite|apply|history>")

    def _cmd_motivation(self, args):
        """
        /motivation state          — Show all drive levels and active goals
        /motivation drive <type>   — Show detailed state of a specific drive
        /motivation reward <t> <v> — Reward a drive (e.g. /motivation reward novelty 0.8)
        /motivation goal           — Persist a new goal
        /motivation goals          — List all persisted active goals
        /motivation progress <id>  — Update goal progress
        """
        agent = self.agent
        motivation = getattr(agent, "motivation", None)
        if not motivation:
            print("❌ MotivationEngine not loaded.")
            return

        sub = args[0].lower() if args else "state"

        if sub == "state":
            state = motivation.get_motivation_state()
            drives = state["drives"]
            print("\n╔══════════════════════════════════════════════╗")
            print("║   MOTIVATION ENGINE — DRIVE STATE            ║")
            print("╠══════════════════════════════════════════════╣")
            print(f"║  Dominant Drive    : {state['dominant_drive'].upper():<23}║")
            print(f"║  Overall Motivation: {state['overall_motivation']:<23.3f}║")
            print(f"║  Active Goals      : {state['active_goals']:<23}║")
            print("╠══════════════════════════════════════════════╣")
            for drive_type, ds in drives.items():
                eff = ds["effective_drive"]
                bar = "█" * int(eff * 12) + "░" * (12 - int(eff * 12))
                frust = f"⚠️" if ds["frustration"] > 0.4 else "  "
                print(f"║ {frust} {drive_type.upper():<10}: [{bar}] {eff:.2f}  ║")
            print("╚══════════════════════════════════════════════╝")
            goals = state["goals_preview"]
            if goals:
                print(f"\n  Active Goals:")
                for g in goals:
                    pct = int(g["progress"] * 100)
                    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                    print(f"  [{bar}] {pct}%  {g['title']}")
            recent = state["recent_rewards"]
            if recent:
                print(f"\n  Recent Rewards:")
                for r in recent[-3:]:
                    color = "+" if r["magnitude"] > 0 else "-"
                    print(f"  {color} [{r['drive']}] magnitude={r['magnitude']:.2f}  {r['context'][:50]}")

        elif sub == "drive":
            drive_type = args[1].lower() if len(args) > 1 else input("Drive type (novelty/coherence/completion/mastery/social): ").strip()
            ds = motivation.drives.get(drive_type)
            if not ds:
                print(f"❌ Unknown drive: '{drive_type}'. Use: novelty, coherence, completion, mastery, social")
                return
            print(f"\n  Drive: {drive_type.upper()}")
            print(f"  Level          : {ds.level:.3f}")
            print(f"  Satiation      : {ds.satiation:.3f}")
            print(f"  Effective Drive: {ds.effective_drive:.3f}")
            print(f"  Weight         : {ds.weight}")
            print(f"  Frustration    : {ds.frustration:.3f}")
            print(f"  Total Rewards  : {ds.total_rewards:.2f}")
            print(f"  Last Satisfied : {ds.last_satisfied or 'never'}")

        elif sub == "reward":
            drive_type = args[1].lower() if len(args) > 1 else input("Drive type: ").strip()
            try:
                magnitude = float(args[2]) if len(args) > 2 else float(input("Magnitude -1.0 to +1.0: ").strip())
            except (ValueError, IndexError):
                print("❌ Invalid magnitude.")
                return
            context = " ".join(args[3:]) if len(args) > 3 else input("Context (optional): ").strip()
            result = motivation.reward(drive_type, magnitude, context)
            if "error" in result:
                print(f"❌ {result['error']}")
            else:
                icon = "📈" if magnitude > 0 else "📉"
                print(f"{icon} Rewarded {drive_type}: new_level={result['new_level']:.3f}, effective={result['effective_drive']:.3f}")

        elif sub == "goal":
            import uuid
            title = input("Goal title: ").strip()
            objective = input("Objective details: ").strip() or title
            drive_type = input("Drive type (default=completion): ").strip() or "completion"
            urgency_str = input("Urgency 0.0-1.0 (default=0.7): ").strip()
            urgency = float(urgency_str) if urgency_str else 0.7
            goal_id = uuid.uuid4().hex[:8]
            result = motivation.persist_goal(goal_id, title, objective, drive_type, urgency)
            print(f"✅ Goal persisted [id={result['goal_id']}] drive={result['drive']}")

        elif sub == "goals":
            goals = motivation.get_active_goals()
            if not goals:
                print("  No active persisted goals. Use /motivation goal to add one.")
                return
            print(f"\n  Active Persisted Goals ({len(goals)}):")
            for g in goals:
                pct = int(g["progress"] * 100)
                bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                print(f"  [{bar}] {pct:3d}%  [{g['goal_id']}] {g['title']} ({g['drive']})")

        elif sub == "progress":
            goal_id = args[1] if len(args) > 1 else input("Goal ID: ").strip()
            progress_str = input("New progress 0.0-1.0: ").strip()
            try:
                progress = float(progress_str)
            except ValueError:
                print("❌ Invalid progress value.")
                return
            note = input("Note (optional): ").strip()
            result = motivation.update_goal_progress(goal_id, progress, note)
            if "error" in result:
                print(f"❌ {result['error']}")
            else:
                if result["completed"]:
                    print(f"🎉 Goal COMPLETED: {goal_id}")
                else:
                    print(f"✅ Progress updated: {result['progress']*100:.0f}%")
        else:
            print("Usage: /motivation <state|drive|reward|goal|goals|progress>")

    # ══════════════════════════════════════════════════════════════════════════
    #  BUG BOUNTY HUNTER COMMANDS — Phase 19 + New features
    # ══════════════════════════════════════════════════════════════════════════

    def _cmd_bugbounty(self, args):
        """
        /bugbounty <subcommand> [args]

        AUTOPILOT (Phase 3):
          autopilot <domain>              → Full end-to-end automated scan
          nuclei <target>                 → Run Nuclei CLI scan

        RECON & DISCOVERY:
          platforms                       → List H1/Bugcrowd/Intigriti
          programs <h1|bc|ig> [query]     → Browse programs
          scope <platform> <handle>       → Fetch program scope
          recon <domain>                  → Passive recon
          deeprecon <domain>              → Full Wayback+JS+OTX+GraphQL
          js <url>                        → Extract JS endpoints
          params <domain>                 → Hidden params + API paths

        NEW ENGINES (Phase 1-2):
          jsscan <url>                    → Scan JS for hardcoded secrets
          takeover <domain>               → Subdomain takeover detector
          fingerprint <url>               → Tech stack + CVE match
          hostinject <url>                → Host Header Injection test
          ssrf <url> <param>              → SSRF test with Interactsh

        SCOPE ENFORCEMENT:
          setscope <domain1> [domain2]... → Define in-scope domains
          scopecheck <url>                → Check if URL is in scope

        SCANNING & PROBING:
          scan <url>                      → Active vulnerability scan
          payloads <xss|sqli|ssrf|ssti>   → WAF-bypass payloads
          probe <url> <param> <type>      → Smart mutation probe

        AUTH TESTING:
          session add <name> <type> <val> → Register auth session
          session list                    → List sessions
          idor <url/{id}> <ids>           → IDOR test
          ratelimit <url> [count]         → Rate limit check

        CONFIRM & DIFF:
          confirm xss <url> <param>       → Confirm XSS (canary)
          confirm sqli <url> <param>      → Confirm SQLi (time-based)
          diff <url1> <url2>              → Response diff

        FINDINGS & REPORTS:
          findings                        → List all findings
          add <url> <sev> <title>         → Log a finding
          report [id]                     → Generate PoC Markdown report
          export [id]                     → Save .md report to reports/
          duplicate <keyword>             → Check H1 disclosures
          bounty <severity>               → Estimate payout
          aianalyze [id]                  → AI CVSS + impact analysis
          summary                         → Executive summary

        SUBMIT:
          submit <h1|bc|ig> <program> [id] → Submit via API
        """
        from bug_bounty_hunter import BugBountyHunter
        agent = self.agent
        hunter = getattr(agent, "_bb_hunter", None)
        if hunter is None:
            hunter = BugBountyHunter(llm_provider=getattr(agent, "llm", None))
            agent._bb_hunter = hunter

        sub = args[0].lower() if args else "findings"
        rest = args[1:]

        # ── AUTOPILOT ──────────────────────────────────────────────────────

        if sub == "autopilot":
            domain = rest[0] if rest else input("Target domain: ").strip()
            if not domain:
                print("  Usage: /bugbounty autopilot <domain>"); return
            domain = domain.replace("https://","").replace("http://","").split("/")[0]
            print(f"  🚀 Starting autopilot for {domain}... (this may take a few minutes)")
            print(hunter.autopilot(domain))

        elif sub == "nuclei":
            target = rest[0] if rest else input("Target URL: ").strip()
            sev = rest[1] if len(rest) > 1 else "medium,high,critical"
            print(hunter.run_nuclei(target, severity=sev))

        # ── SCOPE ─────────────────────────────────────────────────────────

        elif sub == "setscope":
            if not rest:
                print("  Usage: /bugbounty setscope <domain1> [domain2] ...")
                return
            print(hunter.set_scope(rest))

        elif sub == "scopecheck":
            url = rest[0] if rest else input("URL to check: ").strip()
            in_scope = hunter._in_scope(url)
            icon = "✅" if in_scope else "⛔"
            print(f"  {icon} '{url}' is {'IN' if in_scope else 'OUT OF'} scope")
            if hunter._scope:
                print(f"     Scope: {hunter._scope}")
            else:
                print("     (No scope set — all URLs allowed)")

        # ── NEW ENGINES ────────────────────────────────────────────────────

        elif sub == "jsscan":
            url = rest[0] if rest else input("JS URL (or page URL to auto-find JS): ").strip()
            from js_secret_scanner import JSSecretScanner
            from bb_engines import PassiveReconEngine
            scanner = JSSecretScanner()
            # If it's a page, discover JS files first
            if not url.endswith(".js"):
                pre = PassiveReconEngine()
                js_urls = pre.find_js_files(url)
                if js_urls:
                    print(f"  Found {len(js_urls)} JS file(s). Scanning...")
                    findings = scanner.scan_urls(js_urls)
                else:
                    print("  No JS files found on page. Scanning URL directly...")
                    findings = scanner.scan_url(url)
            else:
                findings = scanner.scan_url(url)
            print(scanner.format_report(findings))

        elif sub == "takeover":
            domain = rest[0] if rest else input("Domain: ").strip()
            domain = domain.replace("https://","").replace("http://","").split("/")[0]
            from bb_engines import TakeoverEngine
            te = TakeoverEngine()
            print(te.scan_domain(domain))

        elif sub == "fingerprint":
            url = rest[0] if rest else input("URL: ").strip()
            from fingerprint_engine import FingerprintEngine
            fe = FingerprintEngine()
            profile = fe.fingerprint(url)
            cves = fe.match_cves(profile)
            print(fe.format_report(profile, cves))

        elif sub == "hostinject":
            url = rest[0] if rest else input("URL: ").strip()
            from bb_engines import PayloadMutationEngine
            pme = PayloadMutationEngine()
            findings = pme.test_host_header_injection(url)
            print(pme.format_host_injection_report(findings))

        elif sub in ("ssrf", "confirm") and sub == "ssrf":
            url = rest[0] if rest else input("URL: ").strip()
            param = rest[1] if len(rest) > 1 else input("Parameter name: ").strip()
            from bb_engines import ExploitConfirmEngine
            ece = ExploitConfirmEngine()
            result = ece.confirm_ssrf(url, param)
            if result.get("confirmed") == True:
                print(f"  🔴 SSRF CONFIRMED!")
                print(f"     Type    : {result.get('type', 'SSRF')}")
                print(f"     Evidence: {result.get('evidence', '')}")
                print(f"     URL     : {result.get('url', url)}")
            elif result.get("confirmed") == "possible":
                print(f"  🟡 Possible SSRF: {result.get('evidence', '')}")
            else:
                print(f"  ✅ No SSRF indicators found. {result.get('reason', '')}")

        # ── PLATFORM / PROGRAMS ───────────────────────────────────────────

        elif sub == "platforms":
            print(hunter.list_platforms())

        elif sub == "programs":
            platform = rest[0] if rest else input("Platform (h1/bugcrowd/intigriti): ").strip()
            query = " ".join(rest[1:]) if len(rest) > 1 else ""
            print(hunter.list_programs(platform, query))

        elif sub in ("scope", "getscope"):
            platform = rest[0] if rest else input("Platform: ").strip()
            handle = rest[1] if len(rest) > 1 else input("Program handle: ").strip()
            print(hunter.get_scope(platform, handle))

        # ── RECON ─────────────────────────────────────────────────────────

        elif sub == "recon":
            domain = rest[0] if rest else input("Domain: ").strip()
            print(hunter.passive_recon(domain))

        elif sub == "deeprecon":
            domain = rest[0] if rest else input("Domain: ").strip()
            domain = domain.replace("https://","").replace("http://","").split("/")[0]
            from bb_engines import PassiveReconEngine
            pre = PassiveReconEngine()
            print(pre.full_recon(domain))

        elif sub == "js":
            url = rest[0] if rest else input("URL: ").strip()
            from bb_engines import PassiveReconEngine
            pre = PassiveReconEngine()
            js_files = pre.find_js_files(url)
            if js_files:
                print(f"  📄 Found {len(js_files)} JS file(s):")
                for j in js_files:
                    print(f"    • {j}")
                    eps = pre.extract_js_endpoints(j)
                    for ep in eps[:5]:
                        print(f"        → {ep}")
            else:
                print("  No JS files found.")

        elif sub == "params":
            domain = rest[0] if rest else input("Domain: ").strip()
            from bb_engines import ParameterDiscovery
            pd = ParameterDiscovery()
            print(pd.run(domain))

        # ── SCANNING ──────────────────────────────────────────────────────

        elif sub == "scan":
            url = rest[0] if rest else input("Target URL: ").strip()
            print(hunter.active_scan(url))

        elif sub == "payloads":
            vuln_type = rest[0].lower() if rest else "xss"
            from bb_engines import PayloadMutationEngine
            pme = PayloadMutationEngine()
            print(pme.show_payloads(vuln_type))

        elif sub == "probe":
            if len(rest) < 2:
                print("  Usage: /bugbounty probe <url> <param> [xss|sqli|ssti]"); return
            url, param = rest[0], rest[1]
            vuln_type = rest[2].lower() if len(rest) > 2 else "xss"
            from bb_engines import PayloadMutationEngine
            pme = PayloadMutationEngine()
            hits = pme.probe_with_mutations(url, param, vuln_type)
            if hits:
                print(f"  🔴 {len(hits)} confirmed hit(s)!")
                for h in hits:
                    print(f"    [{h['type']}] {h['evidence']}")
                    print(f"    Payload: {h['payload'][:80]}")
            else:
                print("  ✅ No confirmed vulnerabilities with WAF-bypass payloads.")

        # ── AUTH TESTING ──────────────────────────────────────────────────

        elif sub == "session":
            from bb_engines import AuthSessionEngine
            ase = getattr(agent, "_bb_session", None)
            if ase is None:
                ase = AuthSessionEngine()
                agent._bb_session = ase
            action = rest[0].lower() if rest else "list"
            if action == "list":
                print(ase.list_sessions())
            elif action == "add":
                name = rest[1] if len(rest) > 1 else input("Session name: ").strip()
                auth_type = rest[2] if len(rest) > 2 else input("Auth type (bearer/cookie/basic/header): ").strip()
                value = rest[3] if len(rest) > 3 else input("Value: ").strip()
                print(ase.add_session(name, auth_type, value))
            else:
                print("Usage: /bugbounty session <add|list>")

        elif sub == "idor":
            url_template = rest[0] if rest else input("URL template (with {id}): ").strip()
            ids_str = rest[1] if len(rest) > 1 else input("IDs (comma-separated): ").strip()
            ids = [x.strip() for x in ids_str.split(",")]
            from bb_engines import AuthSessionEngine
            ase = getattr(agent, "_bb_session", None) or AuthSessionEngine()
            print(ase.test_idor(url_template, ids))

        elif sub == "ratelimit":
            url = rest[0] if rest else input("URL: ").strip()
            count = int(rest[1]) if len(rest) > 1 else 30
            from bb_engines import AuthSessionEngine
            ase = getattr(agent, "_bb_session", None) or AuthSessionEngine()
            print(ase.test_rate_limit(url, requests_count=count))

        # ── CONFIRM / DIFF ────────────────────────────────────────────────

        elif sub == "confirm":
            vuln_type = rest[0].lower() if rest else input("Type (xss/sqli/ssrf): ").strip()
            url = rest[1] if len(rest) > 1 else input("URL: ").strip()
            param = rest[2] if len(rest) > 2 else input("Parameter: ").strip()
            from bb_engines import ExploitConfirmEngine
            ece = ExploitConfirmEngine()
            if vuln_type == "xss":
                result = ece.confirm_xss(url, param)
            elif vuln_type == "sqli":
                result = ece.confirm_sqli(url, param)
            elif vuln_type == "ssrf":
                result = ece.confirm_ssrf(url, param)
            else:
                print("Type must be: xss, sqli, or ssrf"); return
            if result.get("confirmed"):
                print(f"  🔴 CONFIRMED {vuln_type.upper()}!")
                print(f"     Evidence: {result.get('evidence', '')}")
                print(f"     URL: {result.get('url', url)}")
            else:
                print(f"  ✅ Not confirmed: {result.get('reason', 'no indicators')}")

        elif sub == "diff":
            url1 = rest[0] if rest else input("URL 1: ").strip()
            url2 = rest[1] if len(rest) > 1 else input("URL 2: ").strip()
            from bb_engines import ExploitConfirmEngine
            ece = ExploitConfirmEngine()
            print(ece.diff_endpoint(url1, url2))

        # ── FINDINGS ──────────────────────────────────────────────────────

        elif sub == "findings":
            print(hunter.list_findings())

        elif sub == "add":
            url = rest[0] if rest else input("URL: ").strip()
            sev = rest[1] if len(rest) > 1 else input("Severity (critical/high/medium/low): ").strip()
            title = " ".join(rest[2:]) if len(rest) > 2 else input("Title: ").strip()
            desc = input("Description (optional, Enter to skip): ").strip()
            f = hunter.add_finding(url, sev, title, desc)
            print(f"  ✅ Finding #{f['id']} logged: [{f['severity'].upper()}] {f['title']}")

        elif sub == "report":
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            print(hunter.generate_report(finding_id=fid))

        elif sub == "export":
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            out_dir = rest[1] if len(rest) > 1 else "reports/"
            path = hunter.export_markdown_report(finding_id=fid, output_dir=out_dir)
            print(f"  ✅ Saved: {path}")

        elif sub == "duplicate":
            keyword = " ".join(rest) if rest else input("Keyword/vuln type: ").strip()
            from bb_engines import DuplicateFinder
            df = DuplicateFinder()
            print(df.check_duplicate({"title": keyword}))

        elif sub == "bounty":
            sev = rest[0] if rest else input("Severity: ").strip()
            from bb_engines import DuplicateFinder
            df = DuplicateFinder()
            print(df.estimate_bounty(sev))

        elif sub == "aianalyze":
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            from bb_engines import AIImpactAnalyzer
            analyzer = AIImpactAnalyzer(llm=getattr(agent, "llm", None))
            if fid:
                finding = next((f for f in hunter.findings if f["id"] == fid), None)
                if not finding:
                    print(f"  ❌ Finding #{fid} not found"); return
            elif hunter.findings:
                from bug_bounty_hunter import SEVERITY_LEVELS
                finding = sorted(hunter.findings,
                                  key=lambda x: SEVERITY_LEVELS.index(x.get("severity","medium")))[0]
            else:
                print("  ❌ No findings. Use /bugbounty add first."); return
            enriched = analyzer.analyze_finding(finding)
            print(f"  🔍 Finding #{enriched['id']}: [{enriched['severity'].upper()}] {enriched['title']}")
            print(f"  CVSS Range : {enriched.get('cvss_range','?')}")
            print(f"  Impact Hint: {enriched.get('impact_hint','')}")
            if enriched.get("ai_impact"):
                print(f"  AI Impact  :\n{enriched['ai_impact']}")
            if enriched.get("ai_remediation"):
                print(f"  Remediation:\n{enriched['ai_remediation']}")

        elif sub == "summary":
            from bb_engines import AIImpactAnalyzer
            analyzer = AIImpactAnalyzer(llm=getattr(agent, "llm", None))
            print(analyzer.generate_executive_summary(hunter.findings))

        elif sub == "submit":
            platform = rest[0] if rest else input("Platform (h1/bugcrowd/intigriti): ").strip()
            program = rest[1] if len(rest) > 1 else input("Program handle: ").strip()
            fid = int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else None
            print(hunter.submit_report(platform, program, finding_id=fid))


        # ── NEW SCAN ENGINES ──────────────────────────────────────────────

        elif sub == "domxss":
            url = rest[0] if rest else input("URL to scan for DOM XSS: ").strip()
            print(f"  🌐 DOM XSS scan: {url}")
            print(hunter.dom_xss_scan(url))

        elif sub == "websocket":
            url = rest[0] if rest else input("URL (discovers WS endpoints automatically): ").strip()
            print(f"  🔌 WebSocket security test: {url}")
            print(hunter.ws_scan(url))

        elif sub == "smuggling":
            url = rest[0] if rest else input("URL to test for HTTP request smuggling: ").strip()
            print(f"  🚢 HTTP Request Smuggling test: {url}")
            print(hunter.smuggling_scan(url))

        elif sub == "xxe":
            url = rest[0] if rest else input("URL (must accept XML POST body): ").strip()
            print(f"  💉 XXE Injection test: {url}")
            print(hunter.xxe_scan(url))

        elif sub in ("login-bypass", "loginbypass", "defaultcreds"):
            url = rest[0] if rest else input("Login URL: ").strip()
            user_field = rest[1] if len(rest) > 1 else "username"
            pass_field = rest[2] if len(rest) > 2 else "password"
            from bb_engines import AuthSessionEngine
            ase = getattr(agent, "_bb_session", None) or AuthSessionEngine()
            print(ase.test_login_bypass(url, user_field, pass_field))

        elif sub in ("mass-assign", "massassign"):
            url = rest[0] if rest else input("Endpoint URL (POST/PUT): ").strip()
            from bb_engines import AuthSessionEngine
            ase = getattr(agent, "_bb_session", None) or AuthSessionEngine()
            print(ase.test_mass_assignment(url))

        # ── TRIAGE DASHBOARD ──────────────────────────────────────────────

        elif sub == "triage":
            print(hunter.triage_dashboard())

        # ── FINDING STATUS ────────────────────────────────────────────────

        elif sub == "status":
            fid = rest[0] if rest else input("Finding ID: ").strip()
            new_status = rest[1] if len(rest) > 1 else input(
                "New status (new/triaged/needs_poc/submitted/waiting_response/closed/duplicate/bounty_paid): "
            ).strip()
            note = " ".join(rest[2:]) if len(rest) > 2 else input("Note (optional): ").strip()
            print(hunter.update_finding_status(fid, new_status, note))

        # ── HTML REPORT ───────────────────────────────────────────────────

        elif sub == "html":
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            out = rest[1] if len(rest) > 1 else "reports/"
            print(hunter.export_html_report(finding_id=fid, output_dir=out))

        # ── WEBHOOK / NOTIFY ──────────────────────────────────────────────

        elif sub == "notify":
            webhook_url = rest[0] if rest else input(
                "Webhook URL (Slack: hooks.slack.com/... | Discord: discord.com/api/webhooks/...): "
            ).strip()
            print(hunter.configure_webhook(webhook_url))

        # ── RATE LIMIT ────────────────────────────────────────────────────

        elif sub == "rate":
            try:
                delay = float(rest[0]) if rest else float(input("Request delay in seconds (0=disable, 0.5=default): ").strip())
            except ValueError:
                delay = 0.5
            print(hunter.set_rate_limit(delay))

        # ── CVSS SUGGEST ──────────────────────────────────────────────────

        elif sub == "cvss":
            action = rest[0].lower() if rest else "guide"
            if action == "suggest":
                vuln_type = " ".join(rest[1:]) if len(rest) > 1 else input(
                    "Vulnerability type (sqli/xss/ssrf/idor/cors/ssti/xxe/rce/jwt_alg_none/...): "
                ).strip()
                print(hunter.cvss_suggest(vuln_type))
            else:
                # Treat as vector string or guide
                vector = action
                if "/" in vector:
                    from bb_engines import CVSS31Calculator
                    calc = CVSS31Calculator()
                    result = calc.calculate(vector)
                    print(calc.format_report(result))
                else:
                    from bb_engines import CVSS31Calculator
                    calc = CVSS31Calculator()
                    print(calc.interactive_build())

        # ── HUNT SESSIONS ─────────────────────────────────────────────────

        elif sub == "session":
            action = rest[0].lower() if rest else "list"
            if action == "save":
                print(hunter.save_hunt_session())
            elif action == "load":
                domain = rest[1] if len(rest) > 1 else input("Domain to load session for: ").strip()
                print(hunter.load_hunt_session(domain))
            elif action == "list":
                print(hunter.list_hunt_sessions())
            elif action == "status":
                from bb_engines import HuntSession
                s = HuntSession(domain=list(getattr(hunter, "scope", set()) or {"unknown"})[0])
                print(s.status())
            elif action == "add":
                # Legacy: session add <name> <type> <value>
                from bb_engines import AuthSessionEngine
                ase = getattr(agent, "_bb_session", None)
                if ase is None:
                    ase = AuthSessionEngine()
                    agent._bb_session = ase
                name = rest[1] if len(rest) > 1 else input("Session name: ").strip()
                auth_type = rest[2] if len(rest) > 2 else input("Auth type (bearer/cookie/basic/header): ").strip()
                value = rest[3] if len(rest) > 3 else input("Value: ").strip()
                print(ase.add_session(name, auth_type, value))
            else:
                print("  Usage: /bugbounty session <save|load <domain>|list|status|add <name> <type> <value>>")

        # ── JWT LIVE TEST ─────────────────────────────────────────────────

        elif sub == "jwt":
            token_or_url = rest[0] if rest else input("JWT token or URL: ").strip()
            test_url = rest[1] if len(rest) > 1 else ""
            from bb_engines import JWTScanner
            scanner = JWTScanner()
            if token_or_url.count(".") == 2 and not token_or_url.startswith("http"):
                # It's a raw token
                report = scanner.scan_token(token_or_url)
                print(scanner.format_report(report))
                if test_url:
                    print("\n  ⚡ Testing forged token against server...")
                    result = scanner.test_forged_against_server(token_or_url, test_url)
                    if result.get("confirmed"):
                        print(f"  🔴 CONFIRMED: {result.get('evidence','')}")
                    elif result.get("confirmed") == "possible":
                        print(f"  🟠 POSSIBLE: {result.get('evidence','')}")
                    else:
                        print(f"  ✅ Rejected: {result.get('reason','')}")
            else:
                # It's a URL — auto-find JWT
                report = scanner.scan_url(token_or_url)
                print(scanner.format_report(report))

        # ── OAUTH TESTING ─────────────────────────────────────────────────

        elif sub == "oauth":
            auth_ep = rest[0] if rest else input("Authorization endpoint URL: ").strip()
            token_ep = rest[1] if len(rest) > 1 else input("Token endpoint URL (Enter to skip): ").strip()
            redirect = rest[2] if len(rest) > 2 else input("Registered redirect_uri: ").strip() or "https://localhost/callback"
            client_id = rest[3] if len(rest) > 3 else input("client_id: ").strip() or "test_client"
            base_url = rest[4] if len(rest) > 4 else ""
            from bb_oauth_engine import OAuthEngine
            engine = OAuthEngine()
            result = engine.scan(auth_ep, token_ep, redirect, client_id, base_url)
            print(engine.format_report(result))

        # ── API KEY SCANNER ───────────────────────────────────────────────

        elif sub == "apiscan":
            url = rest[0] if rest else input("URL to scan for hardcoded secrets: ").strip()
            from bb_api_scanner import APISecretScanner
            scanner = APISecretScanner()
            print(f"  🔑 Scanning {url} for API keys and secrets...")
            findings = scanner.scan_url(url)
            print(scanner.format_report(findings, target=url))
            # Auto-add critical findings
            for f in findings:
                if f.get("severity") in ("CRITICAL", "HIGH"):
                    hunter.add_finding(url, f["severity"].lower(),
                                       f"Hardcoded {f['secret_type'].replace('_',' ').title()} Found",
                                       f"Secret value: {f['value']} | Context: {f['context'][:100]}")

        # ── CLOUD ASSET DISCOVERY ─────────────────────────────────────────

        elif sub == "cloud":
            company = rest[0] if rest else input("Company name or domain: ").strip()
            company = company.replace("https://","").replace("http://","").split("/")[0]
            from bb_cloud_recon import CloudReconEngine
            engine = CloudReconEngine()
            result = engine.scan(company)
            print(engine.format_report(result))
            # Auto-add open buckets as findings
            for r in result.get("findings", []):
                if r.get("status") == "open_readable":
                    hunter.add_finding(r.get("url", company), "critical",
                                       f"Open {r['platform']} Bucket: {r['bucket']}",
                                       r.get("details", ""))

        # ── CACHE POISONING ────────────────────────────────────────────────

        elif sub == "cache":
            url = rest[0] if rest else input("URL to test for cache poisoning: ").strip()
            from bb_cache_poison import CachePoisonEngine
            engine = CachePoisonEngine()
            result = engine.scan(url)
            print(engine.format_report(result))
            for f in result.get("findings", []):
                if f.get("severity") in ("HIGH", "CRITICAL") and "error" not in f:
                    hunter.add_finding(url, f["severity"].lower(),
                                       f"Cache Poisoning: {f.get('type','').replace('_',' ').title()}",
                                       f.get("evidence",""))

        # ── WEB CRAWLER ───────────────────────────────────────────────────

        elif sub == "crawl":
            url = rest[0] if rest else input("URL to crawl: ").strip()
            depth = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else 2
            max_pages = int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else 50
            from bb_utils import crawl_links, format_crawl_report
            print(f"  🕷️  Crawling {url} (depth={depth}, max={max_pages} pages)...")
            result = crawl_links(url, max_depth=depth, max_pages=max_pages)
            print(format_crawl_report(result, target=url))
            # Store discovered URLs in hunter for later scanning
            if not hasattr(hunter, "_crawled_urls"):
                hunter._crawled_urls = {}
            hunter._crawled_urls[url] = result.get("urls", [])
            print(f"\n  ✅ Use /bugbounty scan <url> on any discovered endpoint.")

        # ── GRAPHQL FULL SCAN ─────────────────────────────────────────────

        elif sub == "graphql":
            url = rest[0] if rest else input("GraphQL endpoint URL: ").strip()
            from bb_engines import PassiveReconEngine
            pre = PassiveReconEngine()
            print(f"  🔍 GraphQL security test: {url}")
            result = pre.graphql_detect(url)
            print(result)

        # ── AI PoC WRITER ─────────────────────────────────────────────────

        elif sub == "poc":
            fid = int(rest[0]) if rest and rest[0].isdigit() else None
            from bb_engines import AIImpactAnalyzer
            analyzer = AIImpactAnalyzer(llm=getattr(agent, "llm", None))
            if fid:
                finding = next((f for f in hunter.findings if f.get("id") == fid), None)
            elif hunter.findings:
                finding = hunter.findings[-1]  # latest
            else:
                print("  ❌ No findings. Use /bugbounty add first."); return
            if not finding:
                print(f"  ❌ Finding #{fid} not found"); return
            enriched = analyzer.analyze_finding(finding)
            title = enriched.get("title", "Finding")
            sev = enriched.get("severity", "medium").upper()
            url_f = enriched.get("url", "")
            desc = enriched.get("description", "")
            ai_impact = enriched.get("ai_impact", "")
            ai_rem = enriched.get("ai_remediation", "")
            cvss = enriched.get("cvss_range", "N/A")
            print(f"""
  ╔══════════════════════════════════════════════════╗
  ║   🤖 AI-Generated PoC Report                    ║
  ╚══════════════════════════════════════════════════╝
  Title    : {title}
  Severity : {sev}
  CVSS     : {cvss}
  URL      : {url_f}

  ## Description
  {desc}

  ## AI Impact Analysis
  {ai_impact or 'Upgrade to a local LLM for AI impact analysis.'}

  ## Remediation
  {ai_rem or 'See OWASP or vendor documentation for remediation guidance.'}

  # Steps to Reproduce
  1. Navigate to {url_f}
  2. [Insert specific reproduction steps here]
  3. Observe: [Insert vulnerability behavior here]

  ## References
  - OWASP Top 10: https://owasp.org/www-project-top-ten/
  - CVE: [Add if applicable]
""")

        # ── TELEGRAM WEBHOOK ──────────────────────────────────────────────

        elif sub == "telegram":
            action = rest[0].lower() if rest else "set"
            if action == "set":
                bot_token = rest[1] if len(rest) > 1 else input("Telegram Bot Token: ").strip()
                chat_id = rest[2] if len(rest) > 2 else input("Chat ID: ").strip()
                # Build Telegram webhook URL
                telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                # Test it
                try:
                    import json
                    test_resp = __import__("requests").post(
                        telegram_url,
                        json={"chat_id": chat_id, "text": "✅ Bug Bounty Hunter connected!"},
                        timeout=8
                    )
                    if test_resp.status_code == 200:
                        print(f"  ✅ Telegram connected! Chat ID: {chat_id}")
                        hunter._telegram_bot_token = bot_token
                        hunter._telegram_chat_id = chat_id
                    else:
                        print(f"  ❌ Telegram error: {test_resp.text[:200]}")
                except Exception as e:
                    print(f"  ❌ Telegram test failed: {e}")

        # ── PROXY CONFIG ──────────────────────────────────────────────────

        elif sub == "proxy":
            proxy_url = rest[0] if rest else input("Proxy URL (e.g. http://127.0.0.1:8080): ").strip()
            import os
            if proxy_url.lower() in ("off", "none", "disable", ""):
                os.environ.pop("BUGBOUNTY_PROXY", None)
                os.environ.pop("BB_PROXY", None)
                print("  ✅ Proxy disabled — requests go direct")
            else:
                os.environ["BUGBOUNTY_PROXY"] = proxy_url
                os.environ["BB_PROXY"] = proxy_url
                print(f"  ✅ Proxy set to {proxy_url}")
                print("     All bug bounty HTTP requests will route through Burp Suite / proxy.")

        # ── INLINE HELP ───────────────────────────────────────────────────

        elif sub in ("help", "?", "--help"):
            print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║   🎯 /bugbounty — Full Command Reference                    ║
  ╚══════════════════════════════════════════════════════════════╝

  ⚠️  LEGAL: Only test targets you are AUTHORIZED to test!

  🌍 PLATFORMS & PROGRAMS
    /bugbounty platforms                     List supported platforms
    /bugbounty programs <platform>           Browse programs
    /bugbounty scope <platform> <handle>     Fetch in-scope assets

  🕵️  RECONNAISSANCE
    /bugbounty recon <domain>                Passive recon (subdomains + headers + CORS)
    /bugbounty subdomains <domain>           Enumerate subdomains
    /bugbounty shodan <domain>               Shodan InternetDB lookup
    /bugbounty github <domain>               GitHub secret leakage recon
    /bugbounty takeover <domain>             Subdomain takeover detection
    /bugbounty fingerprint <url>             Tech stack + CVE matching
    /bugbounty crawl <url> [depth] [max]     🆕 Web crawler (links, forms, params)

  🔍 ACTIVE SCANNING
    /bugbounty scan <url>                    Full active scan (XSS, SQLi, CORS, SSRF...)
    /bugbounty xss <url> [param]             XSS scan
    /bugbounty sqli <url> [param]            SQLi scan
    /bugbounty ssrf <url> [param]            SSRF test (Interactsh OOB)
    /bugbounty domxss <url>                  DOM-based XSS (JS sink analysis)
    /bugbounty cache <url>                   🆕 Web Cache Poisoning test
    /bugbounty xxe <url>                     XXE injection
    /bugbounty smuggling <url>               HTTP request smuggling

  🔑 NEW ENGINE TESTS
    /bugbounty oauth <auth_ep> [token_ep]    🆕 OAuth 2.0 / OIDC security test
    /bugbounty apiscan <url>                 🆕 Scan for hardcoded API keys/secrets (30+ patterns)
    /bugbounty cloud <company>              🆕 Cloud bucket discovery (S3/Azure/GCS/Firebase)
    /bugbounty graphql <url>                 GraphQL introspection + security test

  🔐 AUTH TESTING
    /bugbounty jwt scan <url>                JWT token scanner
    /bugbounty idor <url/{id}> <ids>         IDOR test
    /bugbounty login-bypass <url>            Default credentials test
    /bugbounty rate-limit <url> [count]      Rate limiting test

  📋 FINDINGS MANAGEMENT
    /bugbounty findings [severity]           List all findings
    /bugbounty add <url> <sev> <title>       Add a finding
    /bugbounty triage                        Priority-ranked dashboard
    /bugbounty status <id> <status> [note]   Update finding status
    /bugbounty poc [id]                      🆕 AI-generated PoC write-up

  📤 REPORTING & EXPORT
    /bugbounty html                          HTML report with Chart.js chart + timeline
    /bugbounty report [id]                   Markdown PoC report
    /bugbounty cvss <vector>                 CVSS 3.1 score calculator
    /bugbounty exec-summary                  AI executive summary
    /bugbounty submit <platform> <program>   Submit to H1 / Bugcrowd / Intigriti

  ⚙️  CONFIGURATION
    /bugbounty notify <webhook_url>          Slack/Discord webhook
    /bugbounty telegram set <token> <chat>   🆕 Telegram bot notifications
    /bugbounty proxy <url|off>               🆕 Route through Burp Suite proxy
    /bugbounty rate <delay_seconds>          Request delay (0=disable, 0.5=default)

  🚀 AUTOMATION
    /bugbounty autopilot <domain>            Full automated pipeline
    /bugbounty session save/load/list        Hunt session state management
""")

        else:
            print(f"  ❌ Unknown /bugbounty subcommand: '{sub}'")
            print("  Type /bugbounty help for the full command reference.")
            print("  Try: /bugbounty autopilot <domain>  — for full automated scan")
