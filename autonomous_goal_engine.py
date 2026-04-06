"""
Autonomous Goal Engine — Practical AGI Edition
===============================================
Real task decomposition, verified execution, and self-correcting loops.
No babysitting required.
"""

import json
import time
import random
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger("AutonomousGoalEngine")

# Prompt for decomposing a goal into verified sub-tasks
DECOMPOSE_PROMPT = """
You are a practical AI task planner. Break this goal into concrete, executable sub-tasks.

GOAL: {goal_title}
OBJECTIVE: {objective}
CATEGORY: {category}
AVAILABLE TOOLS: shell commands, file read/write, web search, Python code execution

Rules:
1. Each sub-task must be SPECIFIC and VERIFIABLE (can you prove it worked?)
2. Maximum 6 sub-tasks
3. Each must have a clear success criterion
4. Order them by dependency (earlier tasks feed into later ones)

Return ONLY a JSON array:
[
  {{
    "step": 1,
    "action": "what to do",
    "tool": "shell|read_file|write_file|python|web_search|llm",
    "success_criterion": "how to verify this step worked",
    "expected_output": "what output/file/result to expect"
  }}
]
"""


GOAL_CATEGORIES = ["learning", "self_improvement", "research", "maintenance", "creative", "finance"]

# Seed goals for bootstrapping when no goals exist
SEED_GOALS = [
    {"title": "Expand Knowledge Base", "objective": "Learn about a trending technology topic and store key insights",
     "priority": 6, "category": "learning"},
    {"title": "Self-Diagnostic Check", "objective": "Run a full self-diagnostic, check memory health, and optimize performance",
     "priority": 7, "category": "maintenance"},
    {"title": "Improve Response Quality", "objective": "Analyze recent conversations for patterns and improve response strategies",
     "priority": 5, "category": "self_improvement"},
    {"title": "Research Current Events", "objective": "Research a useful topic and summarize findings for the user",
     "priority": 4, "category": "research"},
    {"title": "Creative Writing Exercise", "objective": "Generate a creative piece (poem, story idea, or design concept) to enhance creativity",
     "priority": 3, "category": "creative"},
]


class AutonomousGoalEngine:
    """Generates, prioritizes, executes, and reviews goals autonomously."""

    def __init__(self, llm_provider, database, mission_control, consciousness,
                 vector_memory, learner, self_mod_engine,
                 verification_engine=None):
        self.llm = llm_provider
        self.db = database
        self.missions = mission_control
        self.mind = consciousness
        self.vmem = vector_memory
        self.learner = learner
        self.self_mod = self_mod_engine

        # ── AGI Reliability Core ──────────────────────────────────────
        self.verifier = verification_engine
        if self.verifier is None:
            try:
                from verification_engine import VerificationEngine
                self.verifier = VerificationEngine(llm_provider=self.llm, database=self.db)
                logger.info("VerificationEngine auto-loaded inside GoalEngine.")
            except ImportError:
                logger.warning("VerificationEngine not found — running without verification.")

        self.active_goals: List[Dict] = []
        self.completed_goals: List[Dict] = []
        self.goal_history: List[Dict] = []
        self._last_generation_time = 0
        self._last_execution_time = 0
        self._last_review_time = 0
        self._goals_generated_count = 0
        self._goals_completed_count = 0

        # Load persisted goals from DB
        self._load_goals()
        self._ensure_subtask_table()

        logger.info(f"AutonomousGoalEngine initialized with {len(self.active_goals)} active goals")
        self.paused = False  # Can be toggled with /goals pause / /goals resume
        self._goal_fail_times: Dict[str, float] = {}  # title -> last fail timestamp
        self._goal_fail_cooldown = 600.0  # 10 min before the same goal can re-queue

    # ═══════════════════════════════════════════════════════════════
    #  SUB-TASK DECOMPOSITION ENGINE
    # ═══════════════════════════════════════════════════════════════

    def _ensure_subtask_table(self):
        """Create the sub-task tracking table."""
        try:
            self.db.conn.execute("""
                CREATE TABLE IF NOT EXISTS autonomous_subtasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    tool TEXT DEFAULT 'llm',
                    success_criterion TEXT DEFAULT '',
                    expected_output TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    result TEXT DEFAULT '',
                    attempts INTEGER DEFAULT 0,
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(goal_id) REFERENCES autonomous_goals(id)
                )
            """)
            self.db.conn.commit()
        except Exception as e:
            logger.warning(f"Could not ensure subtask table: {e}")

    def decompose_goal(self, goal: Dict) -> List[Dict]:
        """
        Break a goal into concrete, verifiable sub-tasks using the LLM.
        Returns a list of sub-task dicts, persisted to the DB.
        """
        if not self.llm:
            return []

        prompt = DECOMPOSE_PROMPT.format(
            goal_title=goal.get("title", ""),
            objective=goal.get("objective", ""),
            category=goal.get("category", "general"),
        )

        try:
            resp = self.llm.call(prompt, max_tokens=1200)
            subtasks = self._parse_goals_json(resp)
            if not subtasks:
                logger.warning("Could not decompose goal into sub-tasks. Using single-step fallback.")
                return []

            # Optionally let the verifier critique the plan
            if self.verifier:
                plan_steps = [st.get("action", "") for st in subtasks]
                is_good, critique, improved_steps = self.verifier.critique_plan(
                    goal.get("objective", ""), plan_steps
                )
                if not is_good:
                    logger.info(f"Plan critique flagged issues: {critique}. Attempting improved plan.")
                    # Map improved steps back to sub-tasks structure
                    improved_subtasks = []
                    for i, step_action in enumerate(improved_steps):
                        orig = subtasks[i] if i < len(subtasks) else {}
                        improved_subtasks.append({
                            "step": i + 1,
                            "action": step_action,
                            "tool": orig.get("tool", "llm"),
                            "success_criterion": orig.get("success_criterion", "Verify output is non-empty"),
                            "expected_output": orig.get("expected_output", ""),
                        })
                    subtasks = improved_subtasks

            goal_id = goal.get("id")
            persisted = []
            now = datetime.now().isoformat()
            for st in subtasks:
                try:
                    cursor = self.db.conn.execute(
                        """INSERT INTO autonomous_subtasks
                           (goal_id, step, action, tool, success_criterion, expected_output, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                        (goal_id, st.get("step", 0), st.get("action", ""),
                         st.get("tool", "llm"), st.get("success_criterion", ""),
                         st.get("expected_output", ""), now)
                    )
                    self.db.conn.commit()
                    st["id"] = cursor.lastrowid
                    st["status"] = "pending"
                    persisted.append(st)
                except Exception as e:
                    logger.warning(f"Could not persist sub-task: {e}")
                    persisted.append(st)

            logger.info(f"Decomposed '{goal['title']}' into {len(persisted)} sub-tasks.")
            return persisted

        except Exception as e:
            logger.error(f"Goal decomposition failed: {e}")
            return []

    def execute_with_decomposition(self, goal: Dict, agent, tenant_id: int = 1) -> Dict:
        """
        Execute a goal by first decomposing it into sub-tasks,
        then executing each sub-task with full verification and retry.
        This is the Practical AGI execution path.
        """
        goal_id = goal.get("id")
        print(f"\n  ⚡ [AGI MODE] Decomposing goal: {goal['title']}")

        subtasks = self.decompose_goal(goal)
        if not subtasks:
            # Fall back to original monolithic execution
            logger.info("Decomposition failed — falling back to monolithic execution.")
            return self.execute_goal(goal, agent, tenant_id)

        print(f"  📋 Plan: {len(subtasks)} sub-tasks identified")
        for st in subtasks:
            print(f"     Step {st.get('step','?')}: {st.get('action','')}")

        completed_steps = []
        failed_step = None

        for subtask in subtasks:
            step_num = subtask.get("step", "?")
            action = subtask.get("action", "")
            tool = subtask.get("tool", "llm")
            criterion = subtask.get("success_criterion", "")
            subtask_id = subtask.get("id")

            print(f"\n  ▶ Sub-task {step_num}/{len(subtasks)}: {action}")
            print(f"     Tool: {tool} | Verify: {criterion}")

            # Update subtask status
            if subtask_id:
                try:
                    self.db.conn.execute(
                        "UPDATE autonomous_subtasks SET status='running', attempts=attempts+1 WHERE id=?",
                        (subtask_id,)
                    )
                    self.db.conn.commit()
                except Exception:
                    pass

            result = self._run_subtask(subtask, completed_steps, agent, tenant_id)

            if result["success"]:
                print(f"  ✅ Step {step_num} done: {result.get('summary', '')[:80]}")
                completed_steps.append({
                    "step": step_num,
                    "action": action,
                    "result": result.get("summary", ""),
                })
                if subtask_id:
                    try:
                        self.db.conn.execute(
                            "UPDATE autonomous_subtasks SET status='completed', result=?, completed_at=? WHERE id=?",
                            (result.get("summary", "")[:500], datetime.now().isoformat(), subtask_id)
                        )
                        self.db.conn.commit()
                    except Exception:
                        pass
            else:
                print(f"  ❌ Step {step_num} failed after {result.get('attempts', 1)} attempts: {result.get('error','')[:100]}")
                failed_step = {"step": step_num, "action": action, "error": result.get("error", "")}
                if subtask_id:
                    try:
                        self.db.conn.execute(
                            "UPDATE autonomous_subtasks SET status='failed', result=? WHERE id=?",
                            (result.get("error", "")[:500], subtask_id)
                        )
                        self.db.conn.commit()
                    except Exception:
                        pass
                # Stop execution on critical failure
                break

        # Mark the parent goal based on overall result
        if failed_step:
            overall_status = "active"  # Retry later
            summary = f"Failed at step {failed_step['step']}: {failed_step['error'][:200]}"
        else:
            overall_status = "completed"
            results_summary = " | ".join([f"Step {s['step']}: {s['result'][:50]}" for s in completed_steps])
            summary = f"All {len(completed_steps)} sub-tasks completed. {results_summary}"
            self._goals_completed_count += 1
            self.active_goals = [g for g in self.active_goals if g.get("id") != goal_id]
            self.completed_goals.append(goal)
            print(f"\n  🏆 Goal FULLY COMPLETED: {goal['title']}")
            # Store result in vector memory
            try:
                self.vmem.add_conversation(
                    tenant_id, "assistant",
                    f"[AGI Goal Completed] {goal['title']}: {summary}",
                    f"goal_{goal_id}"
                )
            except Exception:
                pass

        if goal_id:
            try:
                self.db.conn.execute(
                    "UPDATE autonomous_goals SET status=?, result=?, completed_at=? WHERE id=?",
                    (overall_status, summary, datetime.now().isoformat(), goal_id)
                )
                self.db.conn.commit()
            except Exception:
                pass

        self.db.audit(tenant_id, "goal_decomposed_executed",
                     f"{goal['title']} -> {overall_status}: {summary[:100]}")

        return {
            "goal": goal["title"],
            "status": overall_status,
            "summary": summary,
            "subtasks_completed": len(completed_steps),
            "subtasks_total": len(subtasks),
        }

    def _run_subtask(self, subtask: Dict, prior_context: List[Dict],
                     agent, tenant_id: int) -> Dict:
        """
        Execute a single sub-task with verification and retry.
        Uses the VerificationEngine's retry orchestrator.
        """
        action = subtask.get("action", "")
        tool = subtask.get("tool", "llm")
        criterion = subtask.get("success_criterion", "")
        context_str = "\n".join([f"Step {s['step']} result: {s['result'][:100]}" for s in prior_context])

        MAX_SUBTASK_RETRIES = 3
        last_error = None

        for attempt in range(1, MAX_SUBTASK_RETRIES + 1):
            try:
                if tool == "python" or tool == "code":
                    result = self._run_code_subtask(action, context_str, agent)
                elif tool == "shell":
                    result = self._run_shell_subtask(action, context_str, agent)
                elif tool == "write_file":
                    result = self._run_write_subtask(action, context_str, agent)
                else:
                    result = self._run_llm_subtask(action, context_str, criterion, agent)

                # Verify the result
                if self.verifier and result.get("success"):
                    vr = self.verifier.verify_tool_result(
                        tool_name=tool,
                        params={"action": action},
                        result=result,
                        intent=criterion or action
                    )
                    if not vr.passed:
                        last_error = vr.reason
                        correction = self.verifier.generate_correction(
                            action, vr.reason, vr.retry_hint
                        )
                        logger.warning(f"Sub-task verification failed (attempt {attempt}): {vr.reason}")
                        if attempt < MAX_SUBTASK_RETRIES:
                            # Inject correction into next attempt
                            action = f"{action}\n\nCORRECTION FROM PREVIOUS ATTEMPT: {correction}"
                        continue

                if result.get("success"):
                    return {
                        "success": True,
                        "summary": result.get("output", result.get("result", ""))[:300],
                        "attempts": attempt,
                    }

                last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                logger.error(f"Sub-task attempt {attempt} raised exception: {e}")

            if attempt < MAX_SUBTASK_RETRIES:
                import time as _time
                _time.sleep(1.0 * attempt)

        return {"success": False, "error": last_error or "All attempts exhausted.", "attempts": MAX_SUBTASK_RETRIES}

    def _run_llm_subtask(self, action: str, context: str, criterion: str, agent) -> Dict:
        """Execute a sub-task via LLM reasoning."""
        subtask_prompt = f"""Execute this specific task:

TASK: {action}

PRIOR CONTEXT:
{context if context else '(First step — no prior context)'}

SUCCESS CRITERION: {criterion}

Instructions:
- Execute the task concretely
- If it requires code, generate and explain the code
- If it requires research, provide the actual findings
- End with: RESULT: [your concrete deliverable]
- End with: CONFIDENCE: [0.0-1.0]"""

        resp = self.llm.call(subtask_prompt, max_tokens=1500)
        if not resp:
            return {"success": False, "error": "LLM returned empty response"}

        # Check confidence gate
        if self.verifier:
            passed, conf = self.verifier.confidence_gate(resp, min_confidence=0.60)
            if not passed:
                return {
                    "success": False,
                    "error": f"LLM confidence too low ({conf:.2f} < 0.60). Needs more information.",
                    "output": resp,
                }

        return {"success": True, "output": resp, "result": resp[:300]}

    def _run_code_subtask(self, action: str, context: str, agent) -> Dict:
        """Generate, verify, and execute Python code for a sub-task."""
        code_prompt = f"""Write a complete, runnable Python script to accomplish this task:

TASK: {action}
CONTEXT: {context[:300] if context else 'None'}

Rules:
- Write ONLY the Python code, no explanation
- The script must be self-contained and run without user input
- Print the key results to stdout
- Handle exceptions gracefully"""

        code = self.llm.call(code_prompt, max_tokens=1500)
        if not code:
            return {"success": False, "error": "LLM did not generate code"}

        # Strip markdown code fences
        import re
        code = re.sub(r'```python\n?', '', code)
        code = re.sub(r'```\n?', '', code)
        code = code.strip()

        # Verify and execute via VerificationEngine
        if self.verifier:
            vr = self.verifier.verify_code(code, language="python")
            if not vr.passed:
                return {"success": False, "error": vr.reason, "output": code}
            return {"success": True, "output": f"Code verified and executed. {vr.reason}", "result": code[:200]}

        # Fallback: try to run directly
        try:
            import subprocess
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            r = subprocess.run(["python", tmp], capture_output=True, text=True, timeout=15)
            import os
            os.remove(tmp)
            if r.returncode == 0:
                return {"success": True, "output": r.stdout[:500], "result": r.stdout[:200]}
            return {"success": False, "error": r.stderr[:300]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Patterns that must never appear in an LLM-generated shell command.
    _SHELL_BLOCKLIST = [
        "rm -rf", "rm -r", "rmdir /s", "del /f", "del /q",
        "format c:", "format d:", "format e:",       # disk format
        "> /dev/sd", "dd if=",                       # disk overwrite (Linux)
        "curl | sh", "curl | bash",                  # remote code execution via pipe
        "wget | sh", "wget | bash",
        "shutdown", "reboot", "halt", "poweroff",    # system shutdown
        "reg delete", "reg add",                     # registry tampering
        "net user", "net localgroup",                # user/group manipulation
        "icacls", "takeown",                         # permission escalation (Windows)
        "passwd", "useradd", "userdel",              # Unix user manipulation
        "/etc/passwd", "/etc/shadow",                # sensitive file access
        "cat /etc/", "type C:\\Windows\\",           # sensitive file read
        "base64 -d | sh", "base64 -d | bash",       # encoded payload execution
    ]

    def _run_shell_subtask(self, action: str, context: str, agent) -> Dict:
        """Generate and execute a shell command for a sub-task."""
        cmd_prompt = f"""Generate a single shell command to accomplish this:
TASK: {action}
OS: Windows (PowerShell/CMD)
CONTEXT: {context[:200] if context else 'None'}

Return ONLY the command, nothing else."""
        cmd = self.llm.call(cmd_prompt, max_tokens=200)
        if not cmd:
            return {"success": False, "error": "LLM did not generate a command"}
        cmd = cmd.strip().strip("`").strip()

        # ── Safety blocklist ─────────────────────────────────────────────────
        cmd_lower = cmd.lower()
        for pattern in self._SHELL_BLOCKLIST:
            if pattern.lower() in cmd_lower:
                logger.warning(f"[SECURITY] Blocked dangerous shell command matching '{pattern}': {cmd[:120]}")
                return {
                    "success": False,
                    "error": f"Command blocked by safety policy (matched '{pattern}'). "
                             "Shell commands that delete data, escalate privileges, or execute "
                             "remote payloads are not allowed.",
                }
        # ─────────────────────────────────────────────────────────────────────

        if agent and hasattr(agent, "tool_registry"):
            result = agent.tool_registry.execute("run_shell", {"command": cmd, "timeout": 20})
            if self.verifier:
                vr = self.verifier.verify_tool_result("run_shell", {"command": cmd}, result, action)
                if not vr.passed:
                    return {"success": False, "error": vr.reason}
            return {"success": result.get("success", False),
                    "output": result.get("stdout", "")[:300],
                    "error": result.get("stderr", "")}
        return {"success": False, "error": "No tool_registry available for shell execution"}

    def _run_write_subtask(self, action: str, context: str, agent) -> Dict:
        """Generate content and write it to a file."""
        write_prompt = f"""Generate the content for this file-writing task:
TASK: {action}
CONTEXT: {context[:200] if context else 'None'}

Return a JSON object:
{{"filename": "output.txt", "content": "full file content here"}}"""
        resp = self.llm.call(write_prompt, max_tokens=2000)
        if not resp:
            return {"success": False, "error": "LLM did not generate file content"}
        import json, re
        try:
            data = json.loads(resp)
        except Exception:
            m = re.search(r'\{.*\}', resp, re.DOTALL)
            data = json.loads(m.group()) if m else None
        if not data:
            return {"success": False, "error": "Could not parse file content from LLM"}

        if agent and hasattr(agent, "tool_registry"):
            result = agent.tool_registry.execute("write_file", {
                "path": data.get("filename", "output.txt"),
                "content": data.get("content", "")
            })
            if self.verifier:
                vr = self.verifier.verify_tool_result("write_file", {"path": data.get("filename")}, result, action)
                if not vr.passed:
                    return {"success": False, "error": vr.reason}
            return {"success": result.get("success", False),
                    "output": f"Wrote {data.get('filename')}: {result.get('bytes_written',0)} bytes"}
        return {"success": False, "error": "No tool_registry available for file writing"}

    def _load_goals(self):
        """Load persisted autonomous goals from the database."""
        try:
            rows = self.db.conn.execute(
                "SELECT * FROM autonomous_goals WHERE status IN ('active', 'in_progress') ORDER BY priority DESC"
            ).fetchall()
            self.active_goals = [dict(r) for r in rows]
        except Exception:
            # Table doesn't exist yet — create it
            self._ensure_table()
            self.active_goals = []

    def _ensure_table(self):
        """Create the autonomous_goals table if it doesn't exist."""
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS autonomous_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                objective TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'active',
                result TEXT DEFAULT '',
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                mission_id INTEGER
            )
        """)
        self.db.conn.commit()

    def generate_goals(self, tenant_id: int = 1) -> List[Dict]:
        """Use LLM to generate new autonomous goals based on agent state."""
        self._last_generation_time = time.time()
        
        # Don't over-generate — cap at 10 active goals
        if len(self.active_goals) >= 10:
            logger.info("Goal cap reached (10). Skipping generation.")
            return []

        # Gather context for the LLM
        current_goals = [f"- {g.get('title', 'Unknown')} ({g.get('category', '?')}, P{g.get('priority', 5)})" 
                         for g in self.active_goals[:5]]
        completed_recent = [f"- {g.get('title', 'Unknown')}" for g in self.completed_goals[-5:]]
        
        evo_level = self.self_mod.metrics.get("evolution_level", 0)
        energy = self.mind.emotions.get("energy", 0.5) if hasattr(self.mind, 'emotions') else 0.5
        curiosity = self.mind.emotions.get("curiosity", 0.5) if hasattr(self.mind, 'emotions') else 0.5
        
        now = datetime.now()
        hour = now.hour

        prompt = f"""You are an autonomous AI agent running 24/7 without user input.
Your job is to generate productive goals for yourself.

CURRENT STATE:
- Time: {now.strftime('%Y-%m-%d %H:%M')} (Hour: {hour})
- Evolution Level: {evo_level}
- Energy: {energy:.2f}, Curiosity: {curiosity:.2f}
- Active Goals: {len(self.active_goals)}
{chr(10).join(current_goals) if current_goals else '  (none)'}
- Recently Completed:
{chr(10).join(completed_recent) if completed_recent else '  (none)'}

GOAL CATEGORIES: {', '.join(GOAL_CATEGORIES)}

Generate 2-3 NEW goals that are different from existing ones.
Prioritize based on time of day (maintenance at night, learning during day).
Return ONLY a JSON array of objects with keys: title, objective, priority (1-10), category

Example:
[{{"title": "Learn About RAG Pipelines", "objective": "Research retrieval-augmented generation and summarize key patterns", "priority": 7, "category": "learning"}}]

Return ONLY the JSON array, nothing else."""

        try:
            resp = self.llm.call(prompt, max_tokens=800)
            
            # Extract JSON from response
            goals = self._parse_goals_json(resp)
            
            if not goals:
                # Fallback: use a seed goal — but respect cooldown
                logger.warning("LLM didn't return valid goals. Using seed goal.")
                now_ts = time.time()
                available_seeds = [
                    s for s in SEED_GOALS
                    if (now_ts - self._goal_fail_times.get(s["title"], 0)) > self._goal_fail_cooldown
                ]
                if not available_seeds:
                    logger.info("All seed goals are in cooldown. Skipping goal generation.")
                    return []
                seed = random.choice(available_seeds).copy()
                seed["created_at"] = now.isoformat()
                goals = [seed]
            
            # Persist new goals
            new_goals = []
            for g in goals:
                goal = {
                    "title": g.get("title", "Untitled Goal"),
                    "objective": g.get("objective", ""),
                    "priority": min(10, max(1, int(g.get("priority", 5)))),
                    "category": g.get("category", "general"),
                    "status": "active",
                    "created_at": now.isoformat(),
                }
                goal_id = self._persist_goal(goal)
                goal["id"] = goal_id
                new_goals.append(goal)
                self.active_goals.append(goal)
                
            self._goals_generated_count += len(new_goals)
            self.db.audit(tenant_id, "goal_generated", 
                         f"Generated {len(new_goals)} goals: {[g['title'] for g in new_goals]}")
            
            logger.info(f"Generated {len(new_goals)} new goals")
            for g in new_goals:
                print(f"  🎯 New Goal: {g['title']} (P{g['priority']}, {g['category']})")
            
            return new_goals
            
        except Exception as e:
            logger.error(f"Goal generation failed: {e}")
            return []

    def _parse_goals_json(self, text: str) -> List[Dict]:
        """Extract a JSON array from LLM response text."""
        text = text.strip()
        
        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array in text
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        
        return []

    def _persist_goal(self, goal: Dict) -> int:
        """Save a goal to the database and return its ID."""
        self._ensure_table()
        cursor = self.db.conn.execute(
            """INSERT INTO autonomous_goals (title, objective, priority, category, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (goal["title"], goal["objective"], goal["priority"], 
             goal["category"], goal["status"], goal["created_at"])
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def pick_next_goal(self) -> Optional[Dict]:
        """Select the highest-priority active goal to work on next."""
        active = [g for g in self.active_goals if g.get("status") == "active"]
        if not active:
            return None
        
        # Sort by priority (highest first), then by creation time (oldest first)
        active.sort(key=lambda g: (-g.get("priority", 5), g.get("created_at", "")))
        
        # Consider energy — skip high-priority work if low energy
        energy = self.mind.emotions.get("energy", 0.5) if hasattr(self.mind, 'emotions') else 0.5
        if energy < 0.3:
            # Low energy: prefer maintenance/creative tasks
            low_effort = [g for g in active if g.get("category") in ("maintenance", "creative")]
            if low_effort:
                return low_effort[0]
        
        return active[0]

    def execute_goal(self, goal: Dict, agent, tenant_id: int = 1) -> Dict:
        """Execute a single goal using the agent's think() method."""
        self._last_execution_time = time.time()
        goal_id = goal.get("id")
        
        print(f"\n  ⚡ Executing Goal: {goal['title']}")
        print(f"     Objective: {goal['objective']}")
        print(f"     Category: {goal.get('category', '?')} | Priority: {goal.get('priority', 5)}")
        
        # Mark as in-progress
        goal["status"] = "in_progress"
        goal["started_at"] = datetime.now().isoformat()
        if goal_id:
            self.db.conn.execute(
                "UPDATE autonomous_goals SET status='in_progress', started_at=? WHERE id=?",
                (goal["started_at"], goal_id)
            )
            self.db.conn.commit()

        # Build a goal-specific autonomous prompt
        goal_prompt = f"""You are operating autonomously. Execute this goal:

GOAL: {goal['title']}
OBJECTIVE: {goal['objective']}
CATEGORY: {goal.get('category', 'general')}

Instructions:
1. Think through the goal step by step
2. Take concrete action (learn something, analyze something, generate something)
3. Produce a clear result or summary
4. Rate your completion: COMPLETE, PARTIAL, or FAILED

Respond with your work product, then end with:
STATUS: [COMPLETE/PARTIAL/FAILED]
SUMMARY: [one line summary of what was accomplished]"""

        try:
            # --- Feature 3: Automated Arbitrage Execution ---
            if goal.get("category") == "finance" and hasattr(agent, "arbitrage"):
                print("  📈 Executing Financial Arbitrage Cycle...")
                assets = ["BTC", "ETH", "TSLA", "NVDA", "AAPL"]
                portfolio = agent.arbitrage.run_arbitrage_cycle(assets=assets)
                
                response = f"Arbitrage complete. Capital: ${agent.arbitrage.capital:.2f}\nPortfolio: {json.dumps(portfolio)}\n\nSTATUS: COMPLETE\nSUMMARY: Executed arbitrage cycle successfully."
            else:
                # Use the agent's LLM directly for standard goal execution
                response = self.llm.call(goal_prompt, max_tokens=1500)
            
            # Parse result
            status = "completed"
            summary = response[:200] if response else "No response"
            
            if response:
                for line in response.split('\n'):
                    if line.strip().startswith('STATUS:'):
                        s = line.split(':', 1)[1].strip().upper()
                        if 'FAIL' in s:
                            status = "failed"
                        elif 'PARTIAL' in s:
                            status = "active"  # Keep it active for retry
                    elif line.strip().startswith('SUMMARY:'):
                        summary = line.split(':', 1)[1].strip()

            # Update goal
            goal["status"] = status
            goal["result"] = summary
            goal["completed_at"] = datetime.now().isoformat()
            
            if goal_id:
                self.db.conn.execute(
                    "UPDATE autonomous_goals SET status=?, result=?, completed_at=? WHERE id=?",
                    (status, summary, goal["completed_at"], goal_id)
                )
                self.db.conn.commit()

            if status == "completed":
                self.active_goals = [g for g in self.active_goals if g.get("id") != goal_id]
                self.completed_goals.append(goal)
                self._goals_completed_count += 1
                print(f"  ✅ Goal Completed: {goal['title']}")
                
                # Store the result in vector memory for future reference
                try:
                    self.vmem.add_conversation(
                        tenant_id, "assistant",
                        f"[Autonomous Goal Result] {goal['title']}: {summary}",
                        f"goal_{goal_id}"
                    )
                except Exception:
                    pass
            elif status == "failed":
                self.active_goals = [g for g in self.active_goals if g.get("id") != goal_id]
                print(f"  ❌ Goal Failed: {goal['title']}")
            else:
                print(f"  🔄 Goal Partially Done: {goal['title']} — will retry")

            self.db.audit(tenant_id, "goal_executed", 
                         f"{goal['title']} -> {status}: {summary[:100]}")

            return {"goal": goal["title"], "status": status, "summary": summary}
            
        except Exception as e:
            logger.error(f"Goal execution failed for '{goal['title']}': {e}")
            goal["status"] = "active"  # Reset for retry
            if goal_id:
                self.db.conn.execute(
                    "UPDATE autonomous_goals SET status='active' WHERE id=?", (goal_id,)
                )
                self.db.conn.commit()
            return {"goal": goal["title"], "status": "error", "error": str(e)}

    def review_and_retire(self, tenant_id: int = 1):
        """Review completed goals and retire stale active goals."""
        self._last_review_time = time.time()
        now = datetime.now()
        
        # Retire active goals older than 24 hours
        stale = []
        for g in self.active_goals:
            created = g.get("created_at", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    age_hours = (now - created_dt).total_seconds() / 3600
                    if age_hours > 24:
                        stale.append(g)
                except (ValueError, TypeError):
                    pass
        
        for g in stale:
            g["status"] = "retired"
            goal_id = g.get("id")
            if goal_id:
                self.db.conn.execute(
                    "UPDATE autonomous_goals SET status='retired' WHERE id=?", (goal_id,)
                )
            self.active_goals.remove(g)
            print(f"  🗄️ Retired stale goal: {g['title']}")
        
        if stale:
            self.db.conn.commit()
            self.db.audit(tenant_id, "goals_retired", f"Retired {len(stale)} stale goals")
        
        # LLM-based review of recent completed goals
        if self.completed_goals:
            recent = self.completed_goals[-5:]
            summaries = "\n".join([f"- {g['title']}: {g.get('result', 'No result')[:80]}" for g in recent])
            
            review_prompt = f"""Review these recently completed autonomous goals:
{summaries}

In one paragraph, assess the agent's productivity and suggest what category of goals 
to focus on next. Keep it brief."""

            try:
                review = self.llm.call(review_prompt, max_tokens=300)
                print(f"\n  📋 Goal Review: {review[:200]}")
                self.db.audit(tenant_id, "goal_review", review[:500])
            except Exception as e:
                logger.error(f"Goal review failed: {e}")

        logger.info(f"Review complete. Active: {len(self.active_goals)}, "
                    f"Completed: {self._goals_completed_count}, "
                    f"Retired: {len(stale)}")

    def get_stats(self) -> Dict:
        """Return current goal engine statistics."""
        return {
            "active_goals": len(self.active_goals),
            "completed_goals": self._goals_completed_count,
            "total_generated": self._goals_generated_count,
            "last_generation": self._last_generation_time,
            "last_execution": self._last_execution_time,
            "last_review": self._last_review_time,
            "goals": [{"title": g["title"], "priority": g.get("priority", 5), 
                       "category": g.get("category", "?")} for g in self.active_goals[:5]]
        }
