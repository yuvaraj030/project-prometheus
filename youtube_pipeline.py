"""
YouTube Content Pipeline (Phase 16)
=====================================
Topic → Script (LLM) → Voiceover (ElevenLabs/pyttsx3) → Video (MoviePy) → Upload (YouTube API)
Each stage runs independently with graceful fallbacks.
"""

import os
import json
import asyncio
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save as elevenlabs_save
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

try:
    from moviepy.editor import (
        ColorClip, TextClip, CompositeVideoClip, AudioFileClip, concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class YouTubePipeline:
    """
    YouTube Content Pipeline — end-to-end from topic to uploaded video.
    Stages degrade gracefully: script always works, video/upload need optional libs.
    """

    def __init__(self, llm_provider: Any, database: Any = None,
                 elevenlabs_key: str = None,
                 youtube_credentials_file: str = None,
                 output_dir: str = "youtube_output"):
        self.llm = llm_provider
        self.db = database
        self.output_dir = output_dir
        self.pipeline_history: List[Dict] = []
        os.makedirs(output_dir, exist_ok=True)

        # ElevenLabs setup
        self.el_client = None
        if elevenlabs_key and ELEVENLABS_AVAILABLE:
            try:
                self.el_client = ElevenLabs(api_key=elevenlabs_key)
                print("[YouTubePipeline] ElevenLabs connected")
            except Exception as e:
                print(f"[YouTubePipeline] ElevenLabs init failed: {e}")

        # YouTube API
        self.youtube = None
        self.yt_creds_file = youtube_credentials_file

    # ------------------------------------------------------------------
    # Stage 1: Script Generation
    # ------------------------------------------------------------------
    async def generate_script(self, topic: str, duration_minutes: int = 5) -> Dict:
        """Generate a YouTube video script for a topic."""
        words_estimate = duration_minutes * 130  # avg speaking rate
        script_prompt = (
            f"Write a {duration_minutes}-minute YouTube video script about: '{topic}'\n"
            f"Target ~{words_estimate} words.\n"
            "Format:\n"
            "TITLE: <catchy title>\n"
            "DESCRIPTION: <100-word YouTube description with keywords>\n"
            "TAGS: tag1, tag2, tag3, ...\n"
            "SCRIPT:\n<full narration script>\n"
            "Make it engaging, structured with clear sections, and optimized for retention."
        )
        raw = await asyncio.to_thread(self.llm.call, script_prompt, system=(
            "You are a professional YouTube scriptwriter and SEO expert. "
            "Write engaging, well-structured video scripts."
        ), history=[])

        result = {"topic": topic, "raw": raw or "", "title": topic, "description": "", "tags": [], "script": ""}
        if raw:
            lines = raw.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("TITLE:"):
                    result["title"] = line.replace("TITLE:", "").strip()
                elif line.startswith("DESCRIPTION:"):
                    result["description"] = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("TAGS:"):
                    result["tags"] = [t.strip() for t in line.replace("TAGS:", "").split(",")]
                elif line.startswith("SCRIPT:"):
                    result["script"] = "\n".join(lines[i + 1:]).strip()
        return result

    # ------------------------------------------------------------------
    # Stage 2: Voiceover
    # ------------------------------------------------------------------
    async def generate_voiceover(self, script_text: str, output_path: str) -> Optional[str]:
        """Synthesize voiceover using ElevenLabs, fallback to pyttsx3."""
        if self.el_client and ELEVENLABS_AVAILABLE:
            try:
                print("  🎙️  ElevenLabs TTS...")
                audio = await asyncio.to_thread(
                    self.el_client.generate,
                    text=script_text,
                    voice="Rachel",
                    model="eleven_monolingual_v1",
                )
                with open(output_path, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)
                return output_path
            except Exception as e:
                print(f"  ⚠️  ElevenLabs error: {e} — trying pyttsx3")

        if PYTTSX3_AVAILABLE:
            try:
                print("  🎙️  pyttsx3 TTS (fallback)...")
                engine = pyttsx3.init()
                engine.setProperty("rate", 165)
                audio_path = output_path.replace(".mp3", ".wav")
                await asyncio.to_thread(engine.save_to_file, script_text, audio_path)
                await asyncio.to_thread(engine.runAndWait)
                return audio_path
            except Exception as e:
                print(f"  ⚠️  pyttsx3 error: {e}")

        print("  ⚠️  No TTS available — voiceover skipped")
        return None

    # ------------------------------------------------------------------
    # Stage 3: Video Assembly
    # ------------------------------------------------------------------
    async def assemble_video(self, script_data: Dict, audio_path: Optional[str], output_path: str) -> Optional[str]:
        """Assemble a simple video with title card + sections using MoviePy."""
        if not MOVIEPY_AVAILABLE:
            print("  ⚠️  MoviePy not installed — video assembly skipped")
            return None

        try:
            print("  🎞️  Assembling video with MoviePy...")
            duration = 5  # seconds per slide (when no audio)
            clips = []

            # Title slide
            title_clip = ColorClip(size=(1280, 720), color=[15, 15, 30], duration=4)
            title_text = TextClip(
                script_data.get("title", "AI Video"),
                fontsize=60, color="white", bg_color="transparent",
                size=(1100, None), method="caption"
            ).set_position("center").set_duration(4)
            clips.append(CompositeVideoClip([title_clip, title_text]))

            # Script sections as slides
            script = script_data.get("script", "")
            paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
            for para in paragraphs[:8]:  # Max 8 slides
                bg = ColorClip(size=(1280, 720), color=[10, 10, 25], duration=duration)
                txt = TextClip(
                    para[:200], fontsize=32, color="#e2e8f0",
                    size=(1100, None), method="caption"
                ).set_position("center").set_duration(duration)
                clips.append(CompositeVideoClip([bg, txt]))

            video = concatenate_videoclips(clips)

            # Add audio if available
            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                video = video.set_audio(audio.subclip(0, min(audio.duration, video.duration)))

            await asyncio.to_thread(video.write_videofile, output_path, fps=24, logger=None)
            print(f"  ✅ Video assembled: {output_path}")
            return output_path
        except Exception as e:
            print(f"  ⚠️  Video assembly error: {e}")
            return None

    # ------------------------------------------------------------------
    # Stage 4: Upload to YouTube
    # ------------------------------------------------------------------
    async def upload_to_youtube(self, video_path: str, script_data: Dict) -> Optional[str]:
        """Upload video to YouTube. Returns video URL or None."""
        if not YOUTUBE_AVAILABLE or not self.yt_creds_file:
            print("  ⚠️  YouTube upload not configured (need google-api-python-client + credentials)")
            return None
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(self.yt_creds_file)
            yt = build("youtube", "v3", credentials=creds)
            request = yt.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": script_data.get("title", "AI Generated Video"),
                        "description": script_data.get("description", ""),
                        "tags": script_data.get("tags", []),
                        "categoryId": "22",  # People & Blogs
                    },
                    "status": {"privacyStatus": "private"},
                },
                media_body=MediaFileUpload(video_path, mimetype="video/mp4"),
            )
            response = await asyncio.to_thread(request.execute)
            video_id = response.get("id")
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"  ✅ Uploaded to YouTube: {url}")
            return url
        except Exception as e:
            print(f"  ⚠️  YouTube upload error: {e}")
            return None

    # ------------------------------------------------------------------
    # Full Pipeline
    # ------------------------------------------------------------------
    async def create(self, topic: str, duration_minutes: int = 5, tenant_id: int = 1) -> Dict:
        """Run the full pipeline: script → voiceover → video → upload."""
        print(f"\n🎬 YouTube Pipeline — Topic: '{topic}'")
        print("=" * 60)

        slug = topic.lower().replace(" ", "_")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(self.output_dir, f"{slug}_{ts}")
        os.makedirs(out_dir, exist_ok=True)

        # Stage 1
        print("  📝 Generating script...")
        script_data = await self.generate_script(topic, duration_minutes)
        script_path = os.path.join(out_dir, "script.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2)
        print(f"  ✅ Script: {script_data.get('title')}")

        # Stage 2
        print("  🎙️  Generating voiceover...")
        audio_path = await self.generate_voiceover(
            script_data.get("script", topic),
            os.path.join(out_dir, "voiceover.mp3")
        )

        # Stage 3
        print("  🎞️  Assembling video...")
        video_path = await self.assemble_video(
            script_data, audio_path,
            os.path.join(out_dir, "video.mp4")
        )

        # Stage 4
        yt_url = None
        if video_path:
            print("  📤 Uploading to YouTube...")
            yt_url = await self.upload_to_youtube(video_path, script_data)

        result = {
            "topic": topic,
            "title": script_data.get("title"),
            "script_path": script_path,
            "audio_path": audio_path,
            "video_path": video_path,
            "youtube_url": yt_url,
            "output_dir": out_dir,
            "timestamp": datetime.now().isoformat(),
        }
        self.pipeline_history.append(result)

        print(f"\n✅ Pipeline complete! Output: {out_dir}")
        print(f"   YouTube URL: {yt_url or 'Not uploaded (see video_path)'}")
        print("=" * 60)

        if self.db:
            try:
                self.db.audit(tenant_id, "youtube_create", topic[:200])
            except Exception:
                pass

        return result

    def get_status(self) -> Dict:
        return {
            "total_videos": len(self.pipeline_history),
            "elevenlabs": "YES" if self.el_client else "NOT CONFIGURED",
            "moviepy": "YES" if MOVIEPY_AVAILABLE else "NOT INSTALLED",
            "youtube_api": "YES" if (YOUTUBE_AVAILABLE and self.yt_creds_file) else "NOT CONFIGURED",
            "recent": [{"title": p.get("title"), "ts": p.get("timestamp")} for p in self.pipeline_history[-3:]],
        }

    def describe(self) -> str:
        return f"YouTubePipeline — {len(self.pipeline_history)} videos created. ElevenLabs: {'YES' if self.el_client else 'NO'}."
