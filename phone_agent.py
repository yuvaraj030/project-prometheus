"""
Phone Call Agent (Phase 16 — World Interface)
===============================================
Twilio + ElevenLabs/pyttsx3 to make/receive actual phone calls.
Transcribes calls via Whisper. Logs all calls to database.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from twilio.rest import Client as TwilioClient
    from twilio.twiml.voice_response import VoiceResponse, Say, Gather
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class PhoneAgent:
    """
    Phone Call Agent — uses Twilio to make/receive calls with AI-powered
    speech synthesis (ElevenLabs/pyttsx3) and Whisper transcription.
    """

    def __init__(self, llm_provider: Any, database: Any = None,
                 twilio_account_sid: str = None,
                 twilio_auth_token: str = None,
                 twilio_phone_number: str = None,
                 elevenlabs_key: str = None):
        self.llm = llm_provider
        self.db = database
        self.call_log: List[Dict] = []

        self.twilio_phone = twilio_phone_number
        self.client = None
        if TWILIO_AVAILABLE and twilio_account_sid and twilio_auth_token:
            try:
                self.client = TwilioClient(twilio_account_sid, twilio_auth_token)
                print("[PhoneAgent] Twilio connected.")
            except Exception as e:
                print(f"[PhoneAgent] Twilio init failed: {e}")
        else:
            print("[PhoneAgent] Running in SIMULATION mode (no Twilio credentials).")

        # ElevenLabs for voice synthesis
        self.el_key = elevenlabs_key
        self.whisper_model = None

    def _load_whisper(self):
        """Lazy-load Whisper model."""
        if WHISPER_AVAILABLE and not self.whisper_model:
            try:
                import whisper as w
                self.whisper_model = w.load_model("base")
            except Exception:
                pass

    async def make_call(self, to_number: str, message: str, tenant_id: int = 1) -> Dict:
        """Initiate an outbound call with a spoken message."""
        if not self.client:
            # Simulation mode
            print(f"📞 [SIMULATED CALL] → {to_number}")
            print(f"   Agent says: \"{message}\"")
            record = {
                "type": "outbound",
                "to": to_number,
                "message": message,
                "status": "simulated",
                "sid": f"SIMULATED_{datetime.now().strftime('%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
            }
            self.call_log.append(record)
            return record

        try:
            # Build TwiML for the call
            resp = VoiceResponse()
            resp.say(message, voice="Polly.Joanna")
            twiml_url = None  # Would need a hosted TwiML endpoint for real calls
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.twilio_phone,
                twiml=str(resp),
            )
            record = {
                "type": "outbound",
                "to": to_number,
                "message": message,
                "status": call.status,
                "sid": call.sid,
                "timestamp": datetime.now().isoformat(),
            }
            self.call_log.append(record)
            
            if self.db:
                self.db.audit(tenant_id, "phone_call", f"→ {to_number}: {message[:100]}")
            
            print(f"📞 Call initiated: {call.sid} → {to_number}")
            return record
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def ai_call(self, to_number: str, task: str, tenant_id: int = 1) -> Dict:
        """Make an AI-scripted call: LLM generates what to say based on task."""
        call_prompt = (
            f"You are calling someone to: {task}\n"
            f"Write a natural, polite, brief phone script (max 100 words). "
            "Sound human. Include greeting, main message, and closing."
        )
        script = await asyncio.to_thread(self.llm.call, call_prompt, system=(
            "You are writing a phone script for an AI calling agent. Be natural and brief."
        ), history=[])
        script = script or f"Hello, I'm calling regarding: {task}. Please call back at your convenience. Thank you, goodbye."
        return await self.make_call(to_number, script, tenant_id)

    async def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe an audio file using Whisper."""
        self._load_whisper()
        if not self.whisper_model:
            return None
        try:
            result = await asyncio.to_thread(self.whisper_model.transcribe, audio_file)
            return result.get("text", "")
        except Exception as e:
            print(f"[PhoneAgent] Transcription error: {e}")
            return None

    def get_call_log(self) -> List[Dict]:
        db_calls = []
        if self.db:
            try:
                import sqlite3
                conn = sqlite3.connect(getattr(self.db, 'db_path', 'agent_database.db'))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM audit_log WHERE action='phone_call' ORDER BY id DESC LIMIT 20")
                db_calls = [dict(r) for r in cur.fetchall()]
                conn.close()
            except Exception:
                pass
        return self.call_log + db_calls

    def get_status(self) -> Dict:
        return {
            "twilio": "CONNECTED" if self.client else "SIMULATION",
            "whisper": "AVAILABLE" if WHISPER_AVAILABLE else "NOT INSTALLED",
            "from_number": self.twilio_phone or "N/A",
            "total_calls": len(self.call_log),
        }

    def describe(self) -> str:
        mode = "LIVE" if self.client else "SIMULATION"
        return f"PhoneAgent — {mode} mode. {len(self.call_log)} calls placed this session."
