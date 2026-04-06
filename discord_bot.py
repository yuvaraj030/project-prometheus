"""
Discord Bot — Front-end to the Ultimate AI Agent via Discord slash commands.
Requires: pip install discord.py
Set DISCORD_BOT_TOKEN env var.
"""

import os
import logging
import threading
from typing import Optional

logger = logging.getLogger("DiscordBot")

try:
    import discord
    from discord import app_commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    logger.warning("discord.py not installed. Run: pip install discord.py")

try:
    import requests
    _REQ = True
except ImportError:
    _REQ = False


class DiscordBot:
    """
    Discord bot front-end for the Ultimate AI Agent.
    Slash commands route to the gateway REST API.
    """

    def __init__(self, gateway_url: str = "http://localhost:8000",
                 api_key: str = None):
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.gateway_url = gateway_url
        self.api_key = api_key or os.getenv("AGENT_API_KEY", "")
        self._client = None
        logger.info("💬 DiscordBot initialized.")

    def _headers(self):
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _call_gateway(self, endpoint: str, payload: dict = None) -> dict:
        if not _REQ:
            return {"error": "requests not installed"}
        try:
            url = f"{self.gateway_url}/{endpoint.lstrip('/')}"
            if payload:
                resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            else:
                resp = requests.get(url, headers=self._headers(), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def build(self):
        """Build and return the Discord client with all slash commands registered."""
        if not DISCORD_AVAILABLE:
            raise RuntimeError("discord.py not installed")

        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)

        @client.event
        async def on_ready():
            await tree.sync()
            logger.info(f"🤖 Discord bot logged in as {client.user}")

        @tree.command(name="chat", description="Send a message to the AI agent")
        @app_commands.describe(message="Your message to the agent")
        async def slash_chat(interaction: discord.Interaction, message: str):
            await interaction.response.defer()
            result = self._call_gateway("/chat", {"message": message, "tenant_id": 1})
            reply = result.get("response", result.get("error", "No response"))
            await interaction.followup.send(f"🤖 {reply[:2000]}")

        @tree.command(name="status", description="Check the agent's health and status")
        async def slash_status(interaction: discord.Interaction):
            await interaction.response.defer()
            result = self._call_gateway("/status")
            if "error" in result:
                await interaction.followup.send(f"❌ {result['error']}")
                return
            embed = discord.Embed(title="🤖 Agent Status", color=0x6c63ff)
            embed.add_field(name="Mode", value=str(result.get("mode", "?")), inline=True)
            embed.add_field(name="Active Goals", value=str(result.get("active_goals", "?")), inline=True)
            embed.add_field(name="Uptime", value=str(result.get("uptime", "?")), inline=True)
            embed.add_field(name="Memory Items", value=str(result.get("memory_items", "?")), inline=True)
            await interaction.followup.send(embed=embed)

        @tree.command(name="goals", description="View the agent's active goal missions")
        async def slash_goals(interaction: discord.Interaction):
            await interaction.response.defer()
            result = self._call_gateway("/api/goals")
            goals = result.get("active_goals", [])
            if not goals:
                await interaction.followup.send("📭 No active goals right now.")
                return
            embed = discord.Embed(title="🎯 Active Missions", color=0x22d3ee)
            for g in goals[:8]:
                embed.add_field(
                    name=f"[{g.get('category','?')}] {g.get('title','?')[:50]}",
                    value=f"Priority: {g.get('priority','?')} | Status: {g.get('status','?')}",
                    inline=False
                )
            await interaction.followup.send(embed=embed)

        @tree.command(name="heartbeat", description="Manually trigger a heartbeat check")
        async def slash_heartbeat(interaction: discord.Interaction):
            await interaction.response.defer()
            result = self._call_gateway("/heartbeat/trigger", {})
            await interaction.followup.send(f"💓 Heartbeat triggered: {result}")

        @tree.command(name="bid", description="Trigger the freelance auto-bidder")
        @app_commands.describe(keywords="Job keywords (e.g. 'python api')")
        async def slash_bid(interaction: discord.Interaction, keywords: str = "python ai"):
            await interaction.response.defer()
            result = self._call_gateway("/chat", {"message": f"/bid-jobs {keywords}", "tenant_id": 1})
            reply = result.get("response", "Bidding complete.")
            await interaction.followup.send(f"💼 {reply[:2000]}")

        @tree.command(name="dream", description="Trigger a REM memory consolidation cycle")
        async def slash_dream(interaction: discord.Interaction):
            await interaction.response.defer()
            result = self._call_gateway("/chat", {"message": "/rem-sleep", "tenant_id": 1})
            reply = result.get("response", "Dream cycle initiated.")
            await interaction.followup.send(f"😴 {reply[:2000]}")

        self._client = client
        self._tree = tree
        return client

    def start(self):
        """Start the Discord bot (blocking)."""
        if not DISCORD_AVAILABLE:
            logger.error("discord.py not installed.")
            return
        if not self.token:
            logger.error("DISCORD_BOT_TOKEN not set.")
            return
        client = self.build()
        logger.info("🚀 Starting Discord bot...")
        client.run(self.token)

    def start_in_thread(self):
        """Start the Discord bot in a background daemon thread."""
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return t
