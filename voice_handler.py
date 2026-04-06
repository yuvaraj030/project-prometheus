"""
Voice Handler — TTS/STT voice interface for the AI Agent.
Supports ElevenLabs (cloud, voice cloning), Coqui TTS (offline),
and pyttsx3 (fallback). Wired to VTuber lipsync via amplitude streaming.
"""

import threading
import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("VoiceHandler")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ElevenLabs v1+ SDK
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import play, stream as el_stream
    ELEVENLABS_AVAILABLE = True
except ImportError:
    try:
        # Legacy SDK fallback
        from elevenlabs import generate, stream, set_api_key, play
        ELEVENLABS_AVAILABLE = True
        _LEGACY_ELEVENLABS = True
    except ImportError:
        ELEVENLABS_AVAILABLE = False
    _LEGACY_ELEVENLABS = False

# Coqui TTS (offline)
try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False


class VoiceHandler:
    """Handles Text-to-Speech and Speech-to-Text operations.
    
    Priority order:
      1. ElevenLabs (cloud, voice cloning) — needs ELEVENLABS_API_KEY
      2. Coqui TTS (offline neural TTS) — needs TTS package installed
      3. pyttsx3 (system TTS, always available on Windows/Linux/Mac)
    """

    def __init__(self, agent):
        self.agent = agent
        self._coqui_model = None  # Lazy-load Coqui model
        self._elevenlabs_client = None

    def _get_elevenlabs_client(self):
        """Lazy-init ElevenLabs client."""
        if self._elevenlabs_client is None and ELEVENLABS_AVAILABLE:
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if api_key:
                try:
                    self._elevenlabs_client = ElevenLabs(api_key=api_key)
                except Exception:
                    pass
        return self._elevenlabs_client

    def _get_coqui_model(self):
        """Lazy-load Coqui TTS model (first call downloads it)."""
        if self._coqui_model is None and COQUI_AVAILABLE:
            try:
                logger.info("Loading Coqui TTS model (offline neural TTS)...")
                self._coqui_model = CoquiTTS("tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
                logger.info("Coqui TTS model loaded.")
            except Exception as e:
                logger.warning(f"Coqui TTS load failed: {e}")
        return self._coqui_model

    def speak(self, text: str):
        """Text-to-Speech output (threaded) with VTuber Lip Sync.
        
        Automatically selects the best available TTS engine.
        """
        if not text:
            return
        print(f"🤖 {text}", flush=True)

        if not self.agent.voice_mode:
            return

        agent = self.agent

        def _speak_thread():
            try:
                # Lip Sync Start
                if hasattr(agent, "avatar_process") and agent.avatar_process:
                    agent._set_avatar_state("talking")

                use_elevenlabs = (
                    getattr(agent.config, "use_advanced_tts", False)
                    and ELEVENLABS_AVAILABLE
                    and os.getenv("ELEVENLABS_API_KEY")
                )
                use_coqui = (
                    not use_elevenlabs
                    and COQUI_AVAILABLE
                    and getattr(agent.config, "use_coqui_tts", False)
                )

                if use_elevenlabs:
                    self._speak_elevenlabs(text, agent)
                elif use_coqui:
                    self._speak_coqui(text, agent)
                else:
                    self._speak_pyttsx3(text, agent)

            except Exception as e:
                logger.error(f"[TTS Error] {e}")
            finally:
                # Lip Sync End
                if hasattr(agent, "avatar_process") and agent.avatar_process:
                    agent._set_avatar_state("idle")
                if hasattr(agent, "vtuber"):
                    try:
                        asyncio.run(agent.vtuber.set_lipsync(0.0))
                    except Exception:
                        pass

        threading.Thread(target=_speak_thread, daemon=True).start()

    def _speak_elevenlabs(self, text: str, agent):
        """Speak using ElevenLabs cloud TTS (supports custom voice cloning)."""
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        
        # Lipsync approximation before we start playing
        if hasattr(agent, "vtuber"):
            try:
                asyncio.run(agent.vtuber.set_lipsync(0.8))
            except Exception:
                pass

        try:
            client = self._get_elevenlabs_client()
            if client:
                # New ElevenLabs v1 SDK
                audio = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
                play(audio)
            else:
                # Legacy SDK
                from elevenlabs import generate as el_generate, play as el_play, set_api_key as el_set_key
                el_set_key(os.getenv("ELEVENLABS_API_KEY"))
                audio = el_generate(
                    text=text,
                    voice=voice_id,
                    model="eleven_multilingual_v2"
                )
                el_play(audio)
        except Exception as e:
            logger.warning(f"ElevenLabs TTS failed ({e}), falling back to pyttsx3")
            self._speak_pyttsx3(text, agent)

    def _speak_coqui(self, text: str, agent):
        """Speak using Coqui TTS (offline neural voice)."""
        import tempfile
        import subprocess

        model = self._get_coqui_model()
        if not model:
            self._speak_pyttsx3(text, agent)
            return

        try:
            # Lipsync approximation
            if hasattr(agent, "vtuber"):
                try:
                    asyncio.run(agent.vtuber.set_lipsync(0.7))
                except Exception:
                    pass

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_wav = f.name

            model.tts_to_file(text=text, file_path=tmp_wav)

            # Play using available player
            try:
                import playsound
                playsound.playsound(tmp_wav)
            except ImportError:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", tmp_wav],
                               capture_output=True)
            os.unlink(tmp_wav)
        except Exception as e:
            logger.warning(f"Coqui TTS failed ({e}), falling back to pyttsx3")
            self._speak_pyttsx3(text, agent)

    def _speak_pyttsx3(self, text: str, agent):
        """Speak using pyttsx3 (system TTS, always available)."""
        if not TTS_AVAILABLE:
            return

        # VTuber Lipsync (approximate mouth open based on text length)
        words = len(text.split())
        lipsync_val = min(1.0, 0.3 + words * 0.02)
        if hasattr(agent, "vtuber"):
            try:
                asyncio.run(agent.vtuber.set_lipsync(lipsync_val))
            except Exception:
                pass

        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()

    def listen_voice(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice command."""
        if not self.agent.voice_mode or not SR_AVAILABLE:
            return None

        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("  [MIC] Listening...", end="", flush=True)
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
                text = r.recognize_google(audio)
                print(f" '{text}'")
                return text
            except sr.WaitTimeoutError:
                print(" (Timeout)")
                return None
            except sr.UnknownValueError:
                print(" (?)")
                return None
            except Exception as e:
                print(f" (Error: {e})")
                return None

    def listen_wake(self, timeout: int = 2) -> bool:
        """Listen for wake word."""
        if not self.agent.voice_mode or not SR_AVAILABLE:
            return False

        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=3)
                text = r.recognize_google(audio).lower()
                if self.agent.wake_word in text:
                    print(f"  ⚡ Wake word detected: '{text}'")
                    return True
            except Exception:
                pass
        return False

    def get_tts_status(self) -> dict:
        """Return status of all TTS engines."""
        return {
            "elevenlabs_available": ELEVENLABS_AVAILABLE,
            "elevenlabs_api_key_set": bool(os.getenv("ELEVENLABS_API_KEY")),
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "Rachel (default)"),
            "coqui_available": COQUI_AVAILABLE,
            "pyttsx3_available": TTS_AVAILABLE,
            "active_engine": (
                "elevenlabs" if (ELEVENLABS_AVAILABLE and os.getenv("ELEVENLABS_API_KEY"))
                else "coqui" if COQUI_AVAILABLE
                else "pyttsx3" if TTS_AVAILABLE
                else "none"
            ),
        }
