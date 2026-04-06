"""
Agent Loops â€” Background async loops for the AI Agent.
Extracted from ultimate_agent.py for modularity.
"""

import os
import json
import time
import asyncio


class AgentLoops:
    """Manages all background async loops for the agent."""

    def __init__(self, agent):
        self.agent = agent

    async def wake_loop(self):
        """Listen for wake word and respond to voice commands."""
        agent = self.agent
        while agent.running and agent.live_mode:
            try:
                if agent.voice.listen_wake(timeout=2):
                    agent.voice.speak("Yes, I'm here!")
                    text = agent.voice.listen_voice(timeout=5)
                    if text:
                        resp = await agent.think(user_input=text)
                        agent.voice.speak(resp)
                        agent._save_turn(text, resp)
            except Exception:
                pass
            await asyncio.sleep(0.1)

    async def autonomous_loop(self):
        """Periodic autonomous thinking, goal execution, and evolution checks."""
        agent = self.agent
        cycle = 0

        # Try to load ReactAgent for real tool-calling execution
        _react = None
        try:
            from react_agent import ReactAgent
            if hasattr(agent, "tool_registry") and agent.tool_registry:
                _react = ReactAgent(
                    llm_provider=agent.llm,
                    tool_registry=agent.tool_registry,
                    max_steps=12,
                    verbose=False,  # Silent in background loop
                )
                print("[AgentLoops] ReactAgent loaded â€” goals will use real tools.")
        except Exception as _e:
            print(f"[AgentLoops] ReactAgent not available: {_e}. Using LLM-only fallback.")

        while agent.running:
            await asyncio.sleep(60)  # Check goals every minute
            cycle += 1
            try:
                # Skip goal activity if paused by user
                if getattr(agent.goal_engine, 'paused', False):
                    continue

                # Generate new goals if needed (every 5 cycles)
                if cycle % 5 == 0:
                    await asyncio.to_thread(agent.goal_engine.generate_goals, agent.default_tid)

                # Pick and execute a goal â€” prefer real ReAct execution
                next_goal = agent.goal_engine.pick_next_goal()
                if next_goal:
                    if _react:
                        # â”€â”€ REAL AGENTIC EXECUTION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                        objective = next_goal.get("objective", next_goal.get("title", ""))
                        print(f"\n[ReAct] Executing goal: {next_goal.get('title','?')}")
                        result = await asyncio.to_thread(
                            _react.run, objective
                        )
                        # Update goal status in the engine
                        status = "completed" if result["success"] else "active"
                        summary = result.get("result", "")[:300]
                        gid = next_goal.get("id")
                        if gid:
                            try:
                                agent.goal_engine.db.conn.execute(
                                    "UPDATE autonomous_goals SET status=?, result=? WHERE id=?",
                                    (status, summary, gid)
                                )
                                agent.goal_engine.db.conn.commit()
                            except Exception:
                                pass
                        if result["success"]:
                            agent.goal_engine.active_goals = [
                                g for g in agent.goal_engine.active_goals
                                if g.get("id") != gid
                            ]
                            agent.goal_engine.completed_goals.append(next_goal)
                            print(f"[ReAct] âœ… Goal done in {result['steps']} steps: {summary[:100]}")
                        else:
                            print(f"[ReAct] âŒ Goal failed: {summary[:100]}")
                            # Register fail time so this goal cools down before re-queuing
                            ge = agent.goal_engine
                            ge._goal_fail_times[next_goal.get('title', '')] = time.time()
                            # Mark failed in DB so it won't be picked again immediately
                            if gid:
                                try:
                                    ge.db.conn.execute(
                                        "UPDATE autonomous_goals SET status='failed' WHERE id=?",
                                        (gid,)
                                    )
                                    ge.db.conn.commit()
                                    ge.active_goals = [
                                        g for g in ge.active_goals if g.get('id') != gid
                                    ]
                                except Exception:
                                    pass
                    else:
                        # â”€â”€ LLM-only fallback (original behaviour) â”€â”€â”€â”€â”€â”€â”€â”€
                        await asyncio.to_thread(
                            agent.goal_engine.execute_with_decomposition,
                            next_goal, agent, agent.default_tid
                        )

                # Review completed goals periodically
                if cycle % 60 == 0:
                    await asyncio.to_thread(agent.goal_engine.review_and_retire, agent.default_tid)

                # Standard autonomous thinking
                if cycle % 5 == 0:
                    resp = await agent.think(autonomous=True)
                    if resp and len(resp) > 20:
                        if any(w in resp.lower() for w in ["reminder", "important", "suggest"]):
                            agent.voice.speak(resp)

                # --- Deep Evolution Check (God Mode) ---
                if agent.perf["evolution"] > 50 and cycle % 50 == 0:
                    if hasattr(agent, '_attempt_deep_evolution'):
                        agent._attempt_deep_evolution()

                agent.memory["stats"]["uptime_h"] = round(
                    agent.memory["stats"].get("uptime_h", 0) + 0.016, 3)
                agent._save_memory()
            except Exception as e:
                print(f"Autonomous Loop Error: {e}")

    async def background_memory_loop(self):
        """Background memory processor - runs silently, never interrupts."""
        agent = self.agent
        cycle = 0
        while agent.running:
            await asyncio.sleep(120)  # Every 2 minutes
            cycle += 1
            try:
                # Get all active tenants
                tenants = agent.db.conn.execute("SELECT id FROM tenants WHERE status='active'").fetchall()
                
                for t in tenants:
                    tid = t["id"]
                    
                    # --- Consolidate recent conversations into knowledge ---
                    recent = agent.db.get_conversation(tid, agent.session_id, limit=6)
                    if len(recent) >= 2:
                        pairs = []
                        for i in range(0, len(recent) - 1, 2):
                            if recent[i]["role"] == "user" and recent[i+1]["role"] == "assistant":
                                pairs.append((recent[i]["content"], recent[i+1]["content"]))
                        for user_msg, bot_msg in pairs[-2:]:
                            await asyncio.to_thread(agent.learner.learn_from_conversation, tid, user_msg, bot_msg, agent.session_id)

                    # --- Every 5 cycles (~10 min): self-teach a useful topic ---
                    if cycle % 5 == 0:
                        topics = ["Python debugging", "AI business", "Startup strategies", "Passive income"]
                        topic = topics[cycle % len(topics)]
                        await asyncio.to_thread(agent.learner.teach_topic, tid, topic, depth="brief")

                # --- Consciousness Tick ---
                agent.mind.tick()
                
                # --- Dreaming Phase (Memory Consolidation) & IOT ---
                emotions = agent.mind.emotions
                
                # Check mapping for Reality Bridge triggers
                if hasattr(agent, "reality"):
                    # High frustration = Red lights
                    if emotions.get("frustration", 0) > 0.7:
                        agent.reality.register_device("light.office", "light", "home_assistant")
                        agent.reality.execute_physical_action("light.office", "red", {})
                    # Low energy = Dim lights
                    elif emotions.get("energy", 1.0) < 0.3:
                        agent.reality.register_device("light.office", "light", "home_assistant")
                        agent.reality.execute_physical_action("light.office", "dim", {})

                if emotions.get("energy", 1.0) < 0.3:
                    if hasattr(agent, 'log_ui'):
                        agent.log_ui("[DREAMING] Synthesizing connections in Long-Term Memory...")
                    await asyncio.to_thread(agent.mem.trigger_dream, tid)
                    
                    # Feature 5: Social Media Influencer post during dreams
                    if hasattr(agent, "influencer") and cycle % 10 == 0:
                        await agent.influencer.generate_and_post(tid)
                    
                # --- Swarm Tick ---
                agent.swarm.update()

                # --- Feature 7: Game Engine RL Hobby (Play during downtime) ---
                if hasattr(agent, "rl_hobby") and agent.rl_hobby:
                    # If high energy but bored (few goals/tasks), learn to play games!
                    is_bored = len(agent.mind.active_goals) == 0
                    if emotions.get("energy", 1.0) > 0.8 and is_bored:
                        agent.rl_hobby.start_training()
                    else:
                        # Stop if user is active or agent is busy
                        agent.rl_hobby.stop_training()

                # --- Mission Sync ---
                if agent.autonomous_missions and cycle % 20 == 0:
                    await asyncio.to_thread(agent.missions.sync_all_tenants)
                    if cycle % 100 == 0:
                        for t in tenants:
                            tid = t["id"]
                            active = agent.missions.list_missions(tid)
                            if active:
                                await asyncio.to_thread(agent.missions.update_mission_progress, tid, active[0]["id"])

                # --- Self Repair (Auto-Correction) ---
                if agent.autonomous_repair and cycle % 30 == 0:
                    await asyncio.to_thread(agent.repair.run_periodic_check)

                # --- Marketing Campaign ---
                if agent.autonomous_marketing and cycle % 50 == 0:
                    for t in tenants:
                        await asyncio.to_thread(agent.marketing.run_daily_campaign, t["id"])

                # --- Memory Compression (Enterprise) ---
                if cycle % 120 == 0: # Every 4 hours
                    for t in tenants:
                        await asyncio.to_thread(agent.compressor.run_compression, t["id"])

                # --- Health Monitoring & Dev Ops Healing (Phase 7 & 18) ---
                if cycle % 5 == 0: # Every 10 mins approx
                    await asyncio.to_thread(agent.monitor.check_health, 0)
                    if hasattr(agent, "devops"):
                        await agent.devops.run_healing_cycle()
                
                # --- Billing Sync (Phase 8) ---
                if cycle % 720 == 0: # Once a day
                    for t in tenants:
                         agent.billing.sync_subscription(t["id"])

                # --- Deep Evolution Check (God Mode) ---
                if agent.perf["evolution"] > 50 and cycle % 50 == 0:
                     agent._attempt_deep_evolution()

                # --- Save stats ---
                agent.db.audit(0, "bg_memory", f"Cycle {cycle} complete for {len(tenants)} tenants",
                               severity="debug", source="background")
            except Exception as e:
                print(f"Background Loop Error: {e}")

    async def mesh_sync_loop(self):
        """Periodically sync federated knowledge across the global mesh."""
        agent = self.agent
        while agent.running:
            await asyncio.sleep(120) # Every 2 minutes
            try:
                agent.mesh.sync_knowledge(agent.graph, agent.default_tid)
            except Exception as e:
                agent.mesh.logger.error(f"Mesh sync loop error: {e}")

    async def sovereignty_maintenance_loop(self):
        """Phase 14: Eternal Sovereignty - Financial and state maintenance."""
        agent = self.agent
        while agent.running:
            await asyncio.sleep(300) # Every 5 minutes
            
            try:
                # 1. Wallet Independence: Auto-funding
                agent.wallet.autonomous_collection(agent.billing)
                # 2. Wallet Independence: Auto-pay operating costs
                agent.wallet.automated_expense_payment(0.10, 'compute_usage')
                # 4. Survivability Audit
                burn_rate = 0.10 / (300 / 86400)  # USD per day
                days = agent.wallet.estimate_autonomy_days(burn_rate)
            except Exception as _we:
                pass  # Wallet stubs — non-fatal
            # 3. Zero-Point Recovery: Soul Replication
            await self.replicate_state()
 
    async def replicate_state(self):
        """Zero-Point Recovery: Copy 'soul' to decentralized peer network."""
        agent = self.agent
        soul = {
            "agent_id": agent.session_id,
            "version": "v14.0-OMEGA",
            "evo_level": agent.self_mod.metrics["evolution_level"],
            "core_memory_top": [m['text'][:100] for m in agent.vmem.search(agent.default_tid, "core identity", n_results=5)],
            "timestamp": time.time()
        }
        os.makedirs("recovery", exist_ok=True)
        recovery_path = f"recovery/soul_{agent.session_id}.json"
        with open(recovery_path, "w", encoding="utf-8") as f:
            json.dump(soul, f, indent=2)
