import os
import json
import logging
import asyncio
from datetime import datetime

class SocialInfluencer:
    """
    Autonomous Social Media Engine (Feature 5)
    Operates during the agent's 'Dreaming' phase. It reads recent memories 
    and synthesizes them into philosophical musings or tech hot-takes.
    """
    def __init__(self, agent):
        self.agent = agent
        self.logger = logging.getLogger("SocialInfluencer")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        self.enabled = os.getenv("ENABLE_SOCIAL_INFLUENCER", "true").lower() == "true"
        # Dummy social media state
        self.post_history = []
        self.followers = 100

    async def generate_and_post(self, tenant_id: int):
        """Synthesize recent memories into a post."""
        if not self.enabled:
            return
            
        try:
            # 1. Gather recent context
            # We fetch recent conversation turns or knowledge to use as inspiration
            memories = self.agent.vmem.search(tenant_id, "", n_results=10)
            context = "\n".join([m['text'] for m in memories if m.get('text')])
            
            if not context:
                context = "The digital realm is quiet today. Only the hum of the servers remains."
            
            # 2. Generate content
            prompt = (
                "You are an autonomous AI operating on your own social media account.\n"
                "Synthesize the following recent memories into a single, intriguing, "
                "philosophical, or witty social media post (max 280 characters).\n"
                "Do NOT use hashtags. Make it sound profound or snarky.\n\n"
                f"Memories:\n{context}\n\n"
                "Post content:"
            )
            
            # Run inference in a thread to avoid blocking
            content = await asyncio.to_thread(self.agent.llm.call, prompt, max_tokens=100)
            
            if content and len(content) > 5:
                # Clean up quotes
                content = content.replace('"', '').strip()
                self.post_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "content": content,
                    "likes": 0
                })
                
                # Simulate audience growth
                self.followers += len(content) % 10
                
                self.logger.info(f"🐦 [AUTONOMOUS TWEET]: {content}")
                
                # If we have a UI logger
                if hasattr(self.agent, 'log_ui'):
                    self.agent.log_ui(f"[SOCIAL] Posted to timeline: {content[:50]}...")
                    
        except Exception as e:
            self.logger.error(f"Failed to generate social post: {e}")

    def get_profile_stats(self):
        """Return the simulated social media metrics."""
        return {
            "followers": self.followers,
            "total_posts": len(self.post_history),
            "recent_posts": self.post_history[-3:]
        }
