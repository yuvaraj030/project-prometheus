"""
Chat Bridge — Multi-platform messaging adapter system.

Adapter pattern: each platform (WhatsApp, Telegram, Discord, Slack) has its own
adapter class that handles platform-specific formatting and webhooks.
All messages route through ChatBridge.route_message() for unified handling.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger("ChatBridge")


# ============================================================
#  Base Adapter
# ============================================================

class PlatformAdapter(ABC):
    """Base class for all messaging platform adapters."""

    platform_name: str = "unknown"

    def __init__(self, llm_provider, database):
        self.llm = llm_provider
        self.db = database

    @abstractmethod
    def parse_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw webhook data into a normalized message dict:
          {"sender": str, "text": str, "chat_id": str, "platform": str, "raw": dict}
        """
        pass

    @abstractmethod
    def send_reply(self, chat_id: str, message: str) -> bool:
        """Send a reply back to the platform. Returns True on success."""
        pass

    def get_system_prompt(self) -> str:
        """Platform-specific system prompt override."""
        return f"You are a helpful AI assistant on {self.platform_name}. Be concise and friendly."


# ============================================================
#  WhatsApp Adapter (Twilio)
# ============================================================

class WhatsAppAdapter(PlatformAdapter):
    platform_name = "WhatsApp"

    def __init__(self, llm_provider, database):
        super().__init__(llm_provider, database)
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_WHATSAPP_FROM", "")

    def parse_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sender = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "")
        return {
            "sender": sender,
            "text": body,
            "chat_id": f"wa_{sender}",
            "platform": "whatsapp",
            "raw": data,
        }

    def send_reply(self, chat_id: str, message: str) -> bool:
        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured; printing reply instead")
            print(f"[WhatsApp -> {chat_id}] {message}")
            return True
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            phone = chat_id.replace("wa_", "")
            resp = requests.post(url, auth=(self.account_sid, self.auth_token), data={
                "From": f"whatsapp:{self.from_number}",
                "To": f"whatsapp:{phone}",
                "Body": message[:1600],  # WhatsApp limit
            })
            return resp.status_code == 201
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False

    def get_system_prompt(self) -> str:
        return "You are a helpful AI assistant on WhatsApp. Keep answers short and friendly (under 100 words)."


# ============================================================
#  Telegram Adapter
# ============================================================

class TelegramAdapter(PlatformAdapter):
    platform_name = "Telegram"

    def __init__(self, llm_provider, database):
        super().__init__(llm_provider, database)
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def parse_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        sender = message.get("from", {}).get("username", str(chat_id))
        return {
            "sender": sender,
            "text": text,
            "chat_id": f"tg_{chat_id}",
            "platform": "telegram",
            "raw": data,
        }

    def send_reply(self, chat_id: str, message: str) -> bool:
        if not self.bot_token:
            logger.warning("Telegram bot token not configured; printing reply instead")
            print(f"[Telegram -> {chat_id}] {message}")
            return True
        try:
            tg_chat_id = chat_id.replace("tg_", "")
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": tg_chat_id,
                "text": message[:4096],  # Telegram limit
                "parse_mode": "Markdown",
            })
            return resp.json().get("ok", False)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def get_system_prompt(self) -> str:
        return "You are a helpful AI assistant on Telegram. Be concise."


# ============================================================
#  Discord Adapter
# ============================================================

class DiscordAdapter(PlatformAdapter):
    platform_name = "Discord"

    def __init__(self, llm_provider, database):
        super().__init__(llm_provider, database)
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")

    def parse_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        author = data.get("author", {})
        return {
            "sender": author.get("username", "unknown"),
            "text": data.get("content", ""),
            "chat_id": f"dc_{data.get('channel_id', '')}",
            "platform": "discord",
            "raw": data,
        }

    def send_reply(self, chat_id: str, message: str) -> bool:
        if self.webhook_url:
            try:
                resp = requests.post(self.webhook_url, json={"content": message[:2000]})
                return resp.status_code in (200, 204)
            except Exception as e:
                logger.error(f"Discord webhook failed: {e}")
                return False
        elif self.bot_token:
            channel_id = chat_id.replace("dc_", "")
            try:
                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                resp = requests.post(url, headers={
                    "Authorization": f"Bot {self.bot_token}",
                    "Content-Type": "application/json",
                }, json={"content": message[:2000]})
                return resp.status_code == 200
            except Exception as e:
                logger.error(f"Discord API send failed: {e}")
                return False
        else:
            print(f"[Discord -> {chat_id}] {message}")
            return True

    def get_system_prompt(self) -> str:
        return "You are a helpful AI assistant on Discord. Use markdown formatting when appropriate."


# ============================================================
#  Slack Adapter
# ============================================================

class SlackAdapter(PlatformAdapter):
    platform_name = "Slack"

    def __init__(self, llm_provider, database):
        super().__init__(llm_provider, database)
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

    def parse_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event = data.get("event", {})
        return {
            "sender": event.get("user", "unknown"),
            "text": event.get("text", ""),
            "chat_id": f"sl_{event.get('channel', '')}",
            "platform": "slack",
            "raw": data,
        }

    def send_reply(self, chat_id: str, message: str) -> bool:
        if self.webhook_url:
            try:
                resp = requests.post(self.webhook_url, json={"text": message})
                return resp.status_code == 200
            except Exception as e:
                logger.error(f"Slack webhook failed: {e}")
                return False
        elif self.bot_token:
            channel = chat_id.replace("sl_", "")
            try:
                url = "https://slack.com/api/chat.postMessage"
                resp = requests.post(url, headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json",
                }, json={"channel": channel, "text": message})
                return resp.json().get("ok", False)
            except Exception as e:
                logger.error(f"Slack API send failed: {e}")
                return False
        else:
            print(f"[Slack -> {chat_id}] {message}")
            return True

    def get_system_prompt(self) -> str:
        return "You are a helpful AI assistant on Slack. Use Slack-compatible formatting."


# ============================================================
#  Unified Chat Bridge
# ============================================================

class ChatBridge:
    """
    Unified message routing — routes incoming webhooks to the correct adapter,
    gets AI response, and sends back via the same platform.
    """

    ADAPTERS = {
        "whatsapp": WhatsAppAdapter,
        "telegram": TelegramAdapter,
        "discord": DiscordAdapter,
        "slack": SlackAdapter,
    }

    def __init__(self, db_provider, llm_provider):
        self.db = db_provider
        self.llm = llm_provider
        self.adapters: Dict[str, PlatformAdapter] = {}

        # Initialize all adapters
        for name, cls in self.ADAPTERS.items():
            self.adapters[name] = cls(llm_provider, db_provider)
            logger.info(f"Initialized {name} adapter")

    def route_message(self, platform: str, data: Dict[str, Any]) -> str:
        """
        Route an incoming message from any platform to the AI and send a response.

        Args:
            platform: "whatsapp", "telegram", "discord", or "slack"
            data: Raw webhook payload from the platform

        Returns:
            AI response string
        """
        adapter = self.adapters.get(platform)
        if not adapter:
            logger.error(f"Unknown platform: {platform}")
            return f"Error: unknown platform '{platform}'"

        # Parse incoming message
        msg = adapter.parse_incoming(data)
        logger.info(f"[{platform}] {msg['sender']}: {msg['text']}")

        # Get AI response
        tenant_id = 1
        system_prompt = adapter.get_system_prompt()
        response = self.llm.call(msg["text"], system=system_prompt, max_tokens=300)

        # Log to database
        try:
            self.db.save_message(tenant_id, msg["chat_id"], "user", msg["text"], platform)
            self.db.save_message(tenant_id, msg["chat_id"], "assistant", response, platform)
        except Exception as e:
            logger.error(f"DB logging failed: {e}")

        # Send reply
        adapter.send_reply(msg["chat_id"], response)

        return response

    # --- Legacy compatibility ---

    def handle_whatsapp_webhook(self, data: Dict[str, Any]) -> str:
        return self.route_message("whatsapp", data)

    def handle_telegram_webhook(self, data: Dict[str, Any]) -> str:
        return self.route_message("telegram", data)

    def handle_discord_webhook(self, data: Dict[str, Any]) -> str:
        return self.route_message("discord", data)

    def handle_slack_webhook(self, data: Dict[str, Any]) -> str:
        return self.route_message("slack", data)

    def list_adapters(self) -> list:
        return [{"platform": name, "class": type(adapter).__name__}
                for name, adapter in self.adapters.items()]


# --- Quick test ---
if __name__ == "__main__":
    class MockLLM:
        def call(self, p, **kwargs): return f"Echo: {p}"
    class MockDB:
        def save_message(self, *args): pass

    bridge = ChatBridge(MockDB(), MockLLM())

    print("--- Adapters ---")
    for a in bridge.list_adapters():
        print(f"  • {a['platform']}: {a['class']}")

    print("\n--- WhatsApp Test ---")
    bridge.route_message("whatsapp", {"From": "whatsapp:+1234567890", "Body": "Hello AI!"})

    print("\n--- Telegram Test ---")
    bridge.route_message("telegram", {"message": {"chat": {"id": 12345}, "text": "Start bot"}})

    print("\n--- Discord Test ---")
    bridge.route_message("discord", {"author": {"username": "user1"}, "content": "Hi bot!", "channel_id": "ch123"})

    print("\n--- Slack Test ---")
    bridge.route_message("slack", {"event": {"user": "U123", "text": "Hey agent!", "channel": "C456"}})
