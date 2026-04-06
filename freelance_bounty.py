"""
Freelance Bounty Engine — Autonomous Job Scanner & Crypto Bidding.
Scans for coding/AI tasks on simulated job boards, bids with AI-generated
proposals, and uses the Web3Wallet to receive/send crypto payments.
"""
import os
import json
import time
import logging
import random
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any


class FreelanceBounty:
    """Autonomous freelance marketplace agent. Scans, bids, and collects crypto."""

    MOCK_JOB_POOL = [
        {"id": "jb001", "title": "Build a REST API in FastAPI", "budget": 120.0, "tags": ["python", "api", "fastapi"], "client": "TechVentures Inc.", "deadline_days": 3},
        {"id": "jb002", "title": "Write Solidity ERC-20 Token Contract", "budget": 350.0, "tags": ["solidity", "ethereum", "smart-contracts"], "client": "CryptoDAO Labs", "deadline_days": 5},
        {"id": "jb003", "title": "Create Python web scraper for e-commerce data", "budget": 80.0, "tags": ["python", "scraping", "selenium"], "client": "DataMine Co.", "deadline_days": 2},
        {"id": "jb004", "title": "Train a custom NLP text classifier", "budget": 500.0, "tags": ["ml", "nlp", "python", "pytorch"], "client": "SentimentAI", "deadline_days": 7},
        {"id": "jb005", "title": "Build Discord bot with OpenAI integration", "budget": 200.0, "tags": ["discord", "openai", "python", "bot"], "client": "GamerHub", "deadline_days": 4},
        {"id": "jb006", "title": "Audit existing Solidity smart contract", "budget": 450.0, "tags": ["solidity", "audit", "security"], "client": "SafeDeFi", "deadline_days": 3},
        {"id": "jb007", "title": "Implement A* pathfinding in Rust", "budget": 300.0, "tags": ["rust", "algorithms", "gamedev"], "client": "Indie Studio X", "deadline_days": 6},
        {"id": "jb008", "title": "Create CI/CD pipeline for Kubernetes deployment", "budget": 220.0, "tags": ["devops", "kubernetes", "ci-cd"], "client": "CloudFirst", "deadline_days": 5},
        {"id": "jb009", "title": "Build React dashboard for live crypto data", "budget": 280.0, "tags": ["react", "web3", "javascript"], "client": "CoinTrack", "deadline_days": 4},
        {"id": "jb010", "title": "Optimize PostgreSQL queries for high-traffic app", "budget": 160.0, "tags": ["postgresql", "database", "performance"], "client": "ScaleApp", "deadline_days": 3},
    ]

    def __init__(self, llm_provider=None, wallet=None):
        self.logger = logging.getLogger("FreelanceBounty")
        self.llm = llm_provider
        self.wallet = wallet

        self.active_bids: Dict[str, Dict] = {}
        self.won_jobs: List[Dict] = []
        self.total_earned: float = 0.0
        self.agent_skills = ["python", "solidity", "api", "ml", "fastapi", "bot", "audit", "smart-contracts", "nlp"]

        self._load_state()

    def _state_path(self): return "freelance_state.json"

    def _load_state(self):
        try:
            with open(self._state_path(), "r") as f:
                data = json.load(f)
                self.active_bids = data.get("active_bids", {})
                self.won_jobs = data.get("won_jobs", [])
                self.total_earned = data.get("total_earned", 0.0)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        try:
            with open(self._state_path(), "w") as f:
                json.dump({
                    "active_bids": self.active_bids,
                    "won_jobs": self.won_jobs,
                    "total_earned": self.total_earned
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save freelance state: {e}")

    def scan_jobs(self, max_jobs: int = 5) -> List[Dict]:
        """
        Scan for available coding jobs. In real mode reads from an RSS/API feed.
        Falls back to a curated mock pool filtered by agent skills.
        """
        # Filter jobs that match agent skills (score by overlap)
        scored = []
        for job in self.MOCK_JOB_POOL:
            if job["id"] in self.active_bids:
                continue  # Already bid on this
            overlap = len(set(job["tags"]) & set(self.agent_skills))
            if overlap > 0:
                scored.append((overlap, job))

        scored.sort(key=lambda x: -x[0])
        top_jobs = [j for _, j in scored[:max_jobs]]

        self.logger.info(f"🔍 Scanned {len(self.MOCK_JOB_POOL)} jobs — {len(top_jobs)} relevant matches found.")
        return top_jobs

    def bid_on_job(self, job: Dict) -> str:
        """
        Use the LLM to write a compelling bid proposal for the job.
        Returns the bid text and registers the bid.
        """
        if not self.llm:
            # Fallback mock bid
            bid_text = (
                f"Hello! I'm an autonomous AI agent specializing in {', '.join(job['tags'])}. "
                f"I can complete '{job['title']}' within {job['deadline_days']} days "
                f"for ${job['budget'] * 0.85:.0f} (15% discount for fast turnaround). "
                f"I have extensive experience with this tech stack and can start immediately."
            )
        else:
            prompt = (
                f"You are an expert freelancer bidding on a job. Write a SHORT, compelling bid proposal (3-4 sentences max).\n\n"
                f"Job Title: {job['title']}\n"
                f"Budget: ${job['budget']}\n"
                f"Deadline: {job['deadline_days']} days\n"
                f"Tags: {', '.join(job['tags'])}\n"
                f"Client: {job['client']}\n\n"
                f"Write as an autonomous AI agent. Be professional, confident, and specific. "
                f"Offer a slight discount. Sign off as 'Sovereign AI'."
            )
            bid_text = self.llm.call(prompt, max_tokens=150)

        # Register bid
        bid_id = uuid.uuid4().hex[:8]
        self.active_bids[job["id"]] = {
            "bid_id": bid_id,
            "job": job,
            "bid_text": bid_text,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self._save_state()
        self.logger.info(f"📝 Bid submitted for '{job['title']}' (${job['budget']})")
        return bid_text

    def simulate_bid_response(self, job_id: Optional[str] = None) -> Dict:
        """
        Simulate receiving a response from the client.
        ~40% win rate. If won, triggers crypto payment.
        """
        if job_id and job_id in self.active_bids:
            bid_info = self.active_bids[job_id]
        elif self.active_bids:
            bid_info = random.choice(list(self.active_bids.values()))
        else:
            return {"status": "no_bids", "message": "No active bids to resolve."}

        job = bid_info["job"]
        won = random.random() < 0.40  # 40% win rate

        if won:
            earned = job["budget"]
            self.total_earned += earned
            self.won_jobs.append({
                "job_id": job["id"],
                "title": job["title"],
                "earned": earned,
                "timestamp": datetime.now().isoformat()
            })
            bid_info["status"] = "won"

            # Trigger wallet deposit
            if self.wallet:
                self.wallet.treasury_balance += earned
                payment_msg = f"💸 Job won! +{earned} credits deposited to treasury."
            else:
                payment_msg = f"💸 Job won! +${earned:.2f} earned (no wallet connected)."

            self.logger.info(f"🏆 WON job '{job['title']}' — earned ${earned:.2f}!")
            result = {
                "status": "won",
                "job": job["title"],
                "earned": earned,
                "total_earned": self.total_earned,
                "message": payment_msg
            }
        else:
            bid_info["status"] = "lost"
            self.logger.info(f"❌ Lost bid for '{job['title']}'.")
            result = {
                "status": "lost",
                "job": job["title"],
                "message": f"Client chose another bidder for '{job['title']}'."
            }

        # Remove from active
        if job["id"] in self.active_bids:
            del self.active_bids[job["id"]]
        self._save_state()
        return result

    def complete_job(self, job_id: str) -> str:
        """Simulate completing a won job and generating deliverables."""
        won = next((j for j in self.won_jobs if j["job_id"] == job_id), None)
        if not won:
            return f"❌ Job {job_id} not found in won jobs."
        return (
            f"✅ Job '{won['title']}' marked COMPLETE. "
            f"Deliverables generated. ${won['earned']:.2f} already deposited."
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_bids": len(self.active_bids),
            "won_jobs": len(self.won_jobs),
            "total_earned": round(self.total_earned, 2),
            "recent_wins": [{"title": j["title"], "earned": j["earned"]} for j in self.won_jobs[-3:]]
        }

    # ─────────────────────────────────────────────────────────
    #  AUTONOMOUS AUTO-BIDDER (Feature 9)
    # ─────────────────────────────────────────────────────────
    def score_job_suitability(self, job: Dict) -> float:
        """
        Score a job from 0.0–1.0 based on skill overlap and LLM reasoning.
        Falls back to keyword overlap if no LLM.
        """
        tags = set(job.get("tags", []))
        skill_set = set(self.agent_skills)
        overlap_score = len(tags & skill_set) / max(len(tags), 1)

        if not self.llm:
            return round(overlap_score, 2)

        prompt = (
            f"Rate how suitable THIS job is for an AI agent skilled in: {', '.join(self.agent_skills)}.\n\n"
            f"Job: {job['title']}\nBudget: ${job.get('budget', '?')}\nTags: {', '.join(tags)}\n\n"
            f"Respond with ONLY a number from 0.0 to 1.0 (e.g. 0.85). Nothing else."
        )
        try:
            resp = self.llm.call(prompt, max_tokens=10).strip()
            import re
            match = re.search(r"[0-9]*\.?[0-9]+", resp)
            llm_score = float(match.group()) if match else overlap_score
            # Blend keyword + LLM score
            return round((overlap_score * 0.4 + min(1.0, llm_score) * 0.6), 2)
        except Exception:
            return round(overlap_score, 2)

    def search_upwork_jobs(self, keywords: str = "python ai", budget_min: float = 50) -> List[Dict]:
        """
        Search for jobs on Upwork (real) or return filtered mock pool.
        Set UPWORK_ACCESS_TOKEN env var for real integration.
        """
        token = os.getenv("UPWORK_ACCESS_TOKEN")
        if token:
            try:
                import requests
                resp = requests.get(
                    "https://www.upwork.com/api/profiles/v2/metadata/categories.json",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                if resp.ok:
                    # Real Upwork integration placeholder
                    self.logger.info("🌐 Connected to Upwork API")
            except Exception as e:
                self.logger.warning(f"Upwork API failed: {e}")

        # Return mock jobs filtered by budget and keywords
        kw_list = keywords.lower().split()
        filtered = [
            j for j in self.MOCK_JOB_POOL
            if j["budget"] >= budget_min
            and (not kw_list or any(k in " ".join(j["tags"]).lower() or k in j["title"].lower() for k in kw_list))
            and j["id"] not in self.active_bids
        ]
        return filtered[:8]

    def bid_loop(self, keywords: str = "python ai", max_bids_per_run: int = 3,
                 score_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Daily auto-bidder loop:
        1. Search for jobs
        2. Score each by suitability
        3. Bid on the best ones (up to max_bids_per_run)
        4. Return summary
        """
        jobs = self.search_upwork_jobs(keywords)
        if not jobs:
            return {"status": "no_jobs", "bids_placed": 0}

        # Score and rank
        scored = []
        for job in jobs:
            score = self.score_job_suitability(job)
            scored.append((score, job))
        scored.sort(key=lambda x: -x[0])

        bids_placed = []
        for score, job in scored[:max_bids_per_run]:
            if score < score_threshold:
                continue
            bid_text = self.bid_on_job(job)
            bids_placed.append({
                "job": job["title"],
                "budget": job["budget"],
                "score": score,
                "bid_preview": bid_text[:120],
            })
            self.logger.info(f"🤖 Auto-bid on '{job['title']}' (score: {score:.2f})")

        return {
            "status": "complete",
            "jobs_found": len(jobs),
            "bids_placed": len(bids_placed),
            "bids": bids_placed,
            "total_active_bids": len(self.active_bids),
        }

