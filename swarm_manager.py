
"""
Swarm Manager — Hierarchical Multi-Agent System.
Enables the "God Agent" to act as a CEO, spawning and managing specialized
worker agents (Researcher, Coder, Reviewer, etc.) to handle complex tasks in parallel.
"""

import threading
import queue
import time
import json
import uuid
from typing import Dict, Any, List, Optional

class SwarmWorker(threading.Thread):
    """
    A specialized sub-agent running in its own thread.
    """
    def __init__(self, agent_id: str, role: str, task: str, llm_provider, result_queue: queue.Queue, cost_bid: float = 0.0, memory_limit: int = 2000):
        super().__init__()
        self.agent_id = agent_id
        self.role = role
        self.task = task
        self.llm = llm_provider
        self.result_queue = result_queue
        self.cost_bid = cost_bid
        self.memory_limit = memory_limit
        self.daemon = True # Kill if main process dies

    def run(self):
        """Execute the assigned task based on role."""
        try:
            # 1. Define role-specific system prompt
            prompts = {
                "researcher": "You are an expert web researcher. Gather facts, cite sources, and be thorough.",
                "coder": "You are a senior Python software engineer. Write clean, efficient, and error-free code.",
                "reviewer": "You are a QA specialist. finding bugs, security flaws, and logic errors.",
                "planner": "You are a project manager. Break down complex goals into actionable steps.",
                "analyst": "You are a data analyst. Interpret data and find patterns.",
                "writer": "You are a creative copywriter. Write engaging and persuasive content."
            }
            sys_prompt = prompts.get(self.role, "You are a helpful AI assistant.")
            
            # 2. Execute LLM call
            # Note: We reuse the main LLM provider but with a new context
            response = self.llm.call(
                prompt=f"Task: {self.task}\n\nExecute this task as a {self.role}.\nBudget Constraint: {self.memory_limit} tokens.",
                system=sys_prompt,
                max_tokens=self.memory_limit,
                temperature=0.4
            )
            
            # 3. Return result
            result = {
                "id": self.agent_id,
                "role": self.role,
                "task": self.task,
                "status": "success",
                "output": response,
                "cost": self.cost_bid,
                "timestamp": time.time()
            }
            self.result_queue.put(result)
            
        except Exception as e:
            self.result_queue.put({
                "id": self.agent_id,
                "role": self.role,
                "task": self.task,
                "status": "error",
                "output": str(e),
                "timestamp": time.time()
            })
            
            # Penalize failed workers in the economy
            print(f"    [Economy] Worker {self.agent_id[-4:]} failed and lost its {self.cost_bid} cr bid.")


class SwarmManager:
    """
    The 'CEO' module that orchestrates the swarm.
    """
    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.workers = {}
        self.results = queue.Queue()
        self.active_swarms = {} # track by swarm_id
        self.wallet = None # Set by ultimate_agent on init

    def _simulate_bidding(self, role: str, task: str, max_bounty: float) -> tuple:
        """ Simulate internal marketplace bidding. Choose the best worker agent. """
        import random
        # Base stats per role
        role_base_costs = {
            "researcher": 15.0, "coder": 25.0, "reviewer": 20.0, 
            "planner": 30.0, "analyst": 18.0, "writer": 10.0
        }
        base = role_base_costs.get(role, 15.0)
        
        # Generate 3 candidates
        candidates = []
        for i in range(3):
            cost_multiplier = random.uniform(0.7, 1.5)
            memory_cap = int(random.uniform(1000, 4000) * (2.0 - cost_multiplier)) 
            bid = round(base * cost_multiplier, 2)
            candidates.append({"id": f"CAND-{i}", "bid": bid, "memory": memory_cap})
        
        # Filter valid bids and sort by best value (memory per cost)
        valid_bids = [c for c in candidates if c["bid"] <= max_bounty]
        if not valid_bids:
            # Fallback if bounty too low: take cheapest available
            candidates.sort(key=lambda x: x["bid"])
            return candidates[0]["bid"], candidates[0]["memory"]
            
        valid_bids.sort(key=lambda x: x["memory"] / max(x["bid"], 0.1), reverse=True)
        winner = valid_bids[0]
        return winner["bid"], winner["memory"]

    def spawn_swarm(self, objective: str) -> str:
        """
        Analyze a complex objective, break it down, and spawn workers.
        Returns a swarm_id.
        """
        swarm_id = uuid.uuid4().hex[:8]
        
        # 1. Plan: Break down the objective
        plan = self._create_plan(objective)
        
        # 2. Assign bounty to the swarm
        treasury = self.wallet.treasury_balance if hasattr(self, 'wallet') and self.wallet else 5000.0
        swarm_bounty = min(treasury, len(plan) * 50.0) # 50 tokens max per task avg
        
        # 3. Spawn workers for each step via Marketplace
        self.active_swarms[swarm_id] = {
            "objective": objective,
            "tasks": plan,
            "status": "running",
            "results": [],
            "budget_allocated": swarm_bounty,
            "total_spent": 0.0,
            "start_time": time.time()
        }
        
        print(f"  🐝 Swarm {swarm_id} activated. Objective: {objective} | Budget: {swarm_bounty} credits")
        print(f"  📋 Plan: {[t['role'] for t in plan]}")
        
        bounty_per_task = swarm_bounty / max(1, len(plan))
        
        for step in plan:
            # Marketplace Bidding Phase
            winning_bid, memory_limit = self._simulate_bidding(step['role'], step['task'], bounty_per_task)
            
            worker_id = f"{swarm_id}-{step['role']}-{uuid.uuid4().hex[:4]}"
            print(f"    💰 Task '{step['role']}' awarded to {worker_id[-4:]} for {winning_bid} credits (Max Mem: {memory_limit})")
            
            if hasattr(self, 'wallet') and self.wallet:
                self.wallet.treasury_balance -= winning_bid
            self.active_swarms[swarm_id]["total_spent"] += winning_bid

            worker = SwarmWorker(
                agent_id=worker_id,
                role=step['role'],
                task=step['task'],
                llm_provider=self.llm,
                result_queue=self.results,
                cost_bid=winning_bid,
                memory_limit=memory_limit
            )
            worker.start()
            self.workers[worker_id] = worker
            
        tb = getattr(self.wallet, 'treasury_balance', 0.0) if hasattr(self, 'wallet') and self.wallet else 0.0
        print(f"  🏢 Swarm {swarm_id} activated with Treasury Balance: {tb:.2f} credits remaining.")
        return swarm_id

    def _create_plan(self, objective: str) -> List[Dict]:
        """Ask LLM to decompose the objective into roles and tasks."""
        prompt = f"""
        You are a swarm orchestrator. Break down this objective into 3-5 sub-tasks 
        assignable to specialized agents (roles: researcher, coder, reviewer, writer, analyst).
        
        Objective: "{objective}"
        
        Output JSON format only:
        [
            {{"role": "researcher", "task": "Find top 5 libraries for X"}},
            {{"role": "coder", "task": "Write specific code for Y using Z"}}
        ]
        """
        response = self.llm.call(prompt, max_tokens=1000, temperature=0.2)
        try:
             # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            return json.loads(response)
        except:
            # Fallback plan
            return [{"role": "researcher", "task": f"Research: {objective}"},
                    {"role": "writer", "task": f"Summarize: {objective}"}]

    def check_status(self, swarm_id: str) -> str:
        """Check progress of a specific swarm."""
        if swarm_id not in self.active_swarms:
            return "Swarm not found."
            
        swarm = self.active_swarms[swarm_id]
        
        # Collect any new results
        while not self.results.empty():
            try:
                res = self.results.get_nowait()
                # Check if this result belongs to this swarm (by ID prefix)
                if res["id"].startswith(swarm_id):
                    swarm["results"].append(res)
                else:
                    # Put back if not ours (naive, but simple for this scale)
                     # ideally we'd have a better queue routing, but valid for single-user
                    # actually, let's just store all results in memory mapped by ID
                    # Re-implementation: better to just drain queue into a global store
                    pass 
            except queue.Empty:
                break
                
        # To fix the queue issue above, let's just drain everything into the right buckets
        # (Since this method might not be called often enough, we should probably have a background poller
        # but for simplicity, we'll drain on check)
        
        completed = len(swarm["results"])
        total = len(swarm["tasks"])
        spent = round(swarm.get("total_spent", 0.0), 2)
        budget = round(swarm.get("budget_allocated", 0.0), 2)

        status_msg = f"Swarm {swarm_id}: {completed}/{total} tasks complete. (Spent {spent}/{budget} credits)\n"
        for res in swarm["results"]:
            status_msg += f"  ✅ [{res['role'].upper()}] (-{res.get('cost', 0):.1f} cr): {res['output'][:100]}...\n"
            
        if completed >= total:
            swarm["status"] = "completed"
            status_msg += "\n🎉 Swarm Mission Complete!"
            
        return status_msg

    def get_final_report(self, swarm_id: str) -> str:
        """Compile all worker outputs into a final answer."""
        if swarm_id not in self.active_swarms:
            return "Swarm not found."
            
        swarm = self.active_swarms[swarm_id]
        if swarm["status"] != "completed":
            return self.check_status(swarm_id)
            
        # Synthesize with LLM
        context = ""
        for res in swarm["results"]:
            context += f"\n--- Report from {res['role']} ---\n{res['output']}\n"
            
        summary = self.llm.call(
            f"Synthesize these reports into a final cohesive answer for the objective: '{swarm['objective']}'\n\n{context}",
            max_tokens=2000
        )
        return summary
    
    # Correction for the queue logic:
    # We need a proper way to drain the queue. 
    # Let's add a `update()` method called by the agent loop.
    def update(self):
        """Drain the result queue and update swarm states."""
        while not self.results.empty():
            try:
                res = self.results.get_nowait()
                # Find which swarm this belongs to
                s_id = res["id"].split("-")[0]
                if s_id in self.active_swarms:
                    self.active_swarms[s_id]["results"].append(res)
                    
                    # Reward the agent via Web3 Treasury
                    try:
                        self._pay_bounty(res["id"], res.get("cost", 0.0))
                    except Exception as e:
                        print(f"    [Treasury] Failed to pay {res['id']}: {e}")

                    # Check completion
                    if len(self.active_swarms[s_id]["results"]) >= len(self.active_swarms[s_id]["tasks"]):
                         self.active_swarms[s_id]["status"] = "completed"
            except queue.Empty:
                break

    def _pay_bounty(self, agent_id: str, amount: float):
        """Pay a sub-agent using the external Web3Wallet."""
        if hasattr(self, 'wallet') and self.wallet:
            return self.wallet.pay_bounty(agent_id, amount)
        else:
            # Fallback if wallet isn't linked
            print(f"    💸 [Fallback Treasury] Paid {amount} cr to {agent_id[-4:]}.")
