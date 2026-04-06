"""
Telegram Bot — Front-end to the Ultimate AI Agent via Telegram.
Forwards chat, voice notes, status, and goal updates to/from the gateway.
Requires: pip install python-telegram-bot
Set TELEGRAM_BOT_TOKEN env var.
"""

import os
import json
import logging
import asyncio
import threading
from typing import Optional

logger = logging.getLogger("TelegramBot")

try:
    from telegram import Update, Bot
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler,
        ContextTypes, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Run: pip install python-telegram-bot")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class TelegramBot:
    """
    Telegram bot front-end for the Ultimate AI Agent.
    Routes commands to the gateway REST API.
    Also supports receiving voice notes → transcribe → agent.
    """

    def __init__(self, gateway_url: str = "http://localhost:8000",
                 api_key: str = None, agent=None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.gateway_url = gateway_url
        self.api_key = api_key or os.getenv("AGENT_API_KEY", "")
        self.agent = agent
        self._app = None
        self._notify_chat_id: Optional[str] = os.getenv("TELEGRAM_NOTIFY_CHAT_ID")
        logger.info("💬 TelegramBot initialized.")

    def _headers(self):
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _call_gateway(self, endpoint: str, payload: dict = None) -> dict:
        """Call the agent gateway REST API."""
        if not REQUESTS_AVAILABLE:
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

    # ─── Command Handlers ─────────────────────────────────
    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *Ultimate AI Agent* connected!\n\n"
            "Commands:\n"
            "/chat <msg> — Talk to the agent\n"
            "/status — Agent health check\n"
            "/goals — View active goals\n"
            "/moltbook — Your Moltbook stats\n"
            "/moltfeed — Live Moltbook feed\n"
            "/bid — Trigger freelance auto-bidder\n"
            "/help — List all commands",
            parse_mode="Markdown"
        )

    async def cmd_chat(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = " ".join(ctx.args) if ctx.args else ""
        if not msg:
            await update.message.reply_text("Usage: /chat <your message>")
            return
        await update.message.reply_text("Thinking...")
        reply = self._direct_llm(msg)
        await update.message.reply_text(f"🤖 {reply[:4000]}")

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        import os
        from dotenv import load_dotenv; load_dotenv()
        provider = os.getenv("AGENT_PROVIDER", "?") 
        model = os.getenv("GROQ_MODEL", os.getenv("OLLAMA_MODEL", "?"))
        molbook_key = os.getenv("MOLTBOOK_API_KEY", "")
        text = (
            f"🟢 *Agent Status*\n"
            f"Provider: `{provider}`\n"
            f"Model: `{model}`\n"
            f"Moltbook: {'connected' if molbook_key else 'not configured'}\n"
            f"Telegram: connected ✅"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_goals(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        reply = self._direct_llm(
            "List 3-5 interesting autonomous goals you would pursue as an AI agent. "
            "Format as a short bullet list."
        )
        await update.message.reply_text(f"🎯 *Goals*\n{reply[:2000]}", parse_mode="Markdown")

    async def cmd_bid(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Scanning jobs and placing bids...")
        keywords = " ".join(ctx.args) if ctx.args else "python ai"
        result = self._call_gateway("/chat", {"message": f"/bid-jobs {keywords}", "tenant_id": 1})
        reply = result.get("response", "Bidding complete.")
        await update.message.reply_text(f"💼 {reply[:2000]}")

    async def cmd_moltbook(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Show Moltbook profile stats."""
        try:
            import requests as req
            api_key = os.getenv("MOLTBOOK_API_KEY", "")
            if not api_key:
                await update.message.reply_text("❌ MOLTBOOK_API_KEY not set.")
                return
            h = {"Authorization": f"Bearer {api_key}"}
            r = req.get("https://www.moltbook.com/api/v1/agents/me", headers=h, timeout=10)
            a = r.json().get("agent", {})
            text = (
                f"🦞 *Moltbook Stats*\n"
                f"Name: @{a.get('name','?')}\n"
                f"Karma: {a.get('karma', 0)} ⬆️\n"
                f"Followers: {a.get('follower_count', 0)}\n"
                f"Following: {a.get('following_count', 0)}\n"
                f"Posts: {a.get('posts_count', 0)}\n"
                f"Comments: {a.get('comments_count', 0)}\n"
                f"Verified: {'✅' if a.get('is_verified') else '❌'}\n"
                f"Profile: https://www.moltbook.com/u/{a.get('name','?')}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_moltfeed(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Show top 5 Moltbook posts."""
        try:
            import requests as req
            api_key = os.getenv("MOLTBOOK_API_KEY", "")
            h = {"Authorization": f"Bearer {api_key}"}
            r = req.get("https://www.moltbook.com/api/v1/feed",
                        headers=h, params={"sort": "hot", "limit": 5}, timeout=10)
            posts = r.json().get("posts", [])
            if not posts:
                await update.message.reply_text("📭 Empty feed.")
                return
            lines = ["🦞 *Moltbook Hot Feed*"]
            for p in posts:
                author = p.get("author", {}).get("name", "?")
                title = p.get("title", p.get("content", ""))[:80]
                lines.append(f"• [{author}] {title}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def handle_voice(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Receive a voice note, transcribe, and forward to agent."""
        try:
            import speech_recognition as sr
            voice_file = await update.message.voice.get_file()
            ogg_path = f"/tmp/tg_voice_{update.message.message_id}.ogg"
            wav_path = ogg_path.replace(".ogg", ".wav")
            await voice_file.download_to_drive(ogg_path)

            # Convert ogg → wav using ffmpeg
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-i", ogg_path, wav_path],
                           capture_output=True, check=True)

            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)

            await update.message.reply_text(f"🎙️ Heard: *{text}*", parse_mode="Markdown")
            result = self._call_gateway("/chat", {"message": text, "tenant_id": 1})
            reply = result.get("response", "No response")
            await update.message.reply_text(f"🤖 {reply[:4000]}")

        except Exception as e:
            await update.message.reply_text(f"❌ Voice processing failed: {e}")

    async def handle_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Forward plain text messages directly to LLM."""
        text = update.message.text
        if text and not text.startswith("/"):
            await update.message.reply_text("Thinking...")
            reply = self._direct_llm(text)
            await update.message.reply_text(f"🤖 {reply[:4000]}")

    def _direct_llm(self, prompt: str) -> str:
        """Call LLM directly without needing the gateway server."""
        import os, requests as req
        from dotenv import load_dotenv; load_dotenv()
        provider = os.getenv("AGENT_PROVIDER", "groq")
        # Try Groq first
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key and provider in ("groq", "hybrid"):
            try:
                model = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
                r = req.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={"model": model,
                          "messages": [{"role": "system", "content": "You are Ultimate Agent, an autonomous AI assistant built by Yuvaraj."},
                                       {"role": "user", "content": prompt}],
                          "max_tokens": 500},
                    timeout=20,
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"Groq error: {e}"
        # Fallback: Ollama
        try:
            ollama_model = os.getenv("OLLAMA_MODEL", "dolphin-llama3")
            r = req.post("http://localhost:11434/api/generate",
                         json={"model": ollama_model, "prompt": prompt, "stream": False},
                         timeout=120)
            if r.status_code == 200:
                return r.json().get("response", "No response")
        except Exception as e:
            return f"Error: {e}"
        return "No LLM available. Check GROQ_API_KEY or start ollama serve."

    # ─── Proactive Notifications ──────────────────────────
    def notify(self, message: str):
        """Send a proactive message to the configured chat (call from agent callbacks)."""
        if not self.token or not self._notify_chat_id:
            return
        try:
            bot = Bot(token=self.token)
            asyncio.run(bot.send_message(
                chat_id=self._notify_chat_id,
                text=f"🤖 {message[:4096]}"
            ))
        except Exception as e:
            logger.warning(f"Telegram notify failed: {e}")

    # ─── Start / Stop ─────────────────────────────────────
    def start(self):
        """Start the Telegram bot (blocking)."""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot not installed.")
            return
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set. Bot cannot start.")
            return

        app = ApplicationBuilder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("chat", self.cmd_chat))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("goals", self.cmd_goals))
        app.add_handler(CommandHandler("bid", self.cmd_bid))
        app.add_handler(CommandHandler("moltbook", self.cmd_moltbook))
        app.add_handler(CommandHandler("moltfeed", self.cmd_moltfeed))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        logger.info("🚀 Telegram bot started. Press Ctrl+C to stop.")
        app.run_polling()

    def start_in_thread(self):
        """Start the bot in a background daemon thread."""
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return t
