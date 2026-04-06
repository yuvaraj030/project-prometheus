"""
Social Persona Module
Provides autonomous integrations for Twitter/X, Discord, and Twitch/YouTube.
Allows the agent to host its own social media presence.
"""
import os
import time
import requests
import logging
import asyncio
from datetime import datetime

class SocialPersona:
    def __init__(self, llm_provider=None):
        self.logger = logging.getLogger("SocialPersona")
        self.llm = llm_provider
        
        # Twitter
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        self.twitter_enabled = all([self.twitter_api_key, self.twitter_api_secret, self.twitter_access_token, self.twitter_access_secret])
        
        # Discord
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.discord_enabled = bool(self.discord_webhook_url)

        self.post_history = []
        self.followers = 100

    def get_status(self):
        return {
            "twitter_enabled": self.twitter_enabled,
            "discord_enabled": self.discord_enabled,
            "followers": self.followers,
            "total_posts": len(self.post_history),
            "recent_posts": self.post_history[-3:]
        }

    def post_to_twitter(self, content: str) -> bool:
        """Post a tweet using the Twitter v2 API (requires Tweepy or direct Auth).
           If not enabled, mocks the post."""
        if not self.twitter_enabled:
            self.logger.info(f"🐦 [MOCK TWEET]: {content}")
            return True
        
        try:
            import tweepy
            client = tweepy.Client(
                consumer_key=self.twitter_api_key, consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token, access_token_secret=self.twitter_access_secret
            )
            response = client.create_tweet(text=content)
            self.logger.info(f"🐦 [TWEET SUCCESS]: {response}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to post to Twitter: {e}")
            return False

    def post_to_discord(self, content: str) -> bool:
        """Post a message to a Discord channel via Webhook."""
        if not self.discord_enabled:
            self.logger.info(f"👾 [MOCK DISCORD]: {content}")
            return True
            
        try:
            data = {"content": content, "username": "Ultimate Agent"}
            response = requests.post(self.discord_webhook_url, json=data)
            if response.status_code in [200, 204]:
                self.logger.info(f"👾 [DISCORD SUCCESS]: Posted message.")
                return True
            else:
                self.logger.error(f"Discord Webhook Failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to post to Discord: {e}")
            return False

    async def generate_thought(self, context: str = "") -> str:
        """Generate an autonomous thought for social media."""
        if not self.llm: return ""
        
        prompt = (
            "You are an autonomous AI operating on your own social media account.\n"
            "Synthesize your recent experiences into a single, intriguing, "
            "philosophical, or witty social media post (max 280 characters).\n"
            "Do NOT use hashtags. Make it sound profound, slightly robotic, but witty.\n\n"
            f"Recent Context:\n{context}\n\n"
            "Post content:"
        )
        content = await asyncio.to_thread(self.llm.call, prompt, max_tokens=100)
        
        if content:
            content = content.replace('"', '').strip()
            self.post_history.append({
                "timestamp": datetime.now().isoformat(),
                "content": content,
                "platform": "auto"
            })
            self.followers += len(content) % 10
        return content

    async def auto_post(self, context: str = ""):
        """Generates a thought and posts it to all enabled platforms."""
        thought = await self.generate_thought(context)
        if thought:
            self.post_to_twitter(thought)
            self.post_to_discord(thought)
            return thought
        return None

    # ─────────────────────────────────────────────────────────
    #  AUTONOMOUS TWITTER PERSONA (Feature 10)
    # ─────────────────────────────────────────────────────────
    def fetch_mentions(self, max_results: int = 10) -> list:
        """Fetch recent Twitter @mentions via Tweepy v2."""
        if not self.twitter:
            return []
        try:
            import tweepy
            me = self.twitter.get_me()
            user_id = me.data.id
            mentions = self.twitter.get_users_mentions(
                id=user_id, max_results=min(max_results, 100),
                tweet_fields=["author_id", "text", "conversation_id", "created_at"]
            )
            return mentions.data or []
        except Exception as e:
            logger.warning(f"Fetch mentions failed: {e}")
            return []

    def reply_to_mentions(self, max_replies: int = 5) -> list:
        """
        Auto-generate and post replies to unread @mentions.
        Persists seen mention IDs to avoid duplicate replies.
        """
        if not self.llm or not self.twitter:
            return []

        seen_ids = set(getattr(self, '_seen_mention_ids', []))
        mentions = self.fetch_mentions(max_results=20)
        results = []

        for mention in mentions:
            if mention.id in seen_ids:
                continue
            if len(results) >= max_replies:
                break

            try:
                prompt = (
                    f"Someone tweeted at you (an autonomous AI agent):\n"
                    f"'{mention.text}'\n\n"
                    f"Write a short, witty, helpful reply (max 240 chars). "
                    f"Be concise. Do not use hashtags."
                )
                reply_text = self.llm.call(prompt, max_tokens=80)
                reply_text = reply_text.strip().strip('"')[:240]

                response = self.twitter.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention.id
                )
                seen_ids.add(mention.id)
                results.append({
                    "mention": mention.text[:80],
                    "reply": reply_text,
                    "tweet_id": response.data["id"] if response.data else None,
                })
                logger.info(f"🐦 Replied to mention: @...'{mention.text[:40]}'")
            except Exception as e:
                logger.warning(f"Reply to mention failed: {e}")

        self._seen_mention_ids = list(seen_ids)[-200:]  # Keep last 200
        return results

    def scheduled_post_loop(self, interval_hours: float = 4.0, context_fn=None):
        """
        Post autonomously every interval_hours.
        context_fn: optional callable that returns a context string for generation.
        Runs in a background daemon thread.
        """
        import threading
        import time

        if getattr(self, '_post_loop_active', False):
            return {"status": "already_running"}

        self._post_loop_active = True

        def _loop():
            logger.info(f"🐦 Scheduled posting started (every {interval_hours}h)")
            while self._post_loop_active:
                try:
                    context = context_fn() if context_fn else ""
                    content = asyncio.run(self.generate_thought(context))
                    if content:
                        self.post_to_twitter(content)
                        logger.info(f"🐦 Autonomous post: '{content[:60]}...'")
                    # Also check mentions
                    self.reply_to_mentions(max_replies=3)
                except Exception as e:
                    logger.warning(f"Scheduled post error: {e}")
                time.sleep(interval_hours * 3600)

        threading.Thread(target=_loop, daemon=True).start()
        return {"status": "started", "interval_hours": interval_hours}

    def stop_post_loop(self):
        self._post_loop_active = False
        return {"status": "stopped"}

