
"""
Vision Engine — The "Eyes" of the Agent.
Enables:
1. Taking screenshots of the desktop.
2. Understanding screen content via Vision LLM (e.g. llava).
3. Controlling the mouse and keyboard (GUI Automation).
"""

import os
import time
import base64
import platform
from typing import Dict, Any, List, Optional, Tuple

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image, ImageGrab
    VISION_AVAILABLE = True
except Exception:
    # Catches ImportError AND runtime errors like KeyError('DISPLAY')
    # which pyautogui raises in headless/Docker environments
    VISION_AVAILABLE = False


class VisionEngine:
    """
    Handles visual perception and GUI interaction.
    """

    def __init__(self, llm_provider, database=None):
        self.llm = llm_provider
        self.db = database
        self.screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
            
        # Safety: Fail-safe for pyautogui (move mouse to corner to abort)
        if VISION_AVAILABLE:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5  # Add delay for human-like movement

    def is_available(self) -> bool:
        return VISION_AVAILABLE

    # ==================================================
    #  PERCEPTION (See)
    # ==================================================
    def take_screenshot(self, name: str = "current_screen") -> str:
        """Capture the screen and save to file."""
        if not VISION_AVAILABLE:
            return "Error: Vision dependencies (pyautogui, Pillow) not installed."
        
        filepath = os.path.join(self.screenshots_dir, f"{name}_{int(time.time())}.png")
        try:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            return filepath
        except Exception as e:
            return f"Error taking screenshot: {e}"

    def describe_screen(self, query: str = "Describe what is on the screen.") -> str:
        """
        Take a screenshot and ask the Vision LLM to describe it.
        NOTE: Requires a multimodal model (e.g., llava) in Ollama or GPT-4o.
        """
        if not VISION_AVAILABLE:
            return "Error: Vision module inactive."

        # 1. Capture
        path = self.take_screenshot("analysis")
        if path.startswith("Error"):
            return path
            
        # 2. Encode image for API (if using OpenAI/Ollama with images)
        # For this implementation, we'll assume Ollama's 'llava' model is used for vision tasks
        # or we fallback to text if the model supports image specs (like gpt-4o).
        
        # Check current model capabilities
        model = self.llm.model.lower()
        if "llava" not in model and "gpt-4" not in model and "claude-3" not in model:
             return f"⚠️ Current model '{model}' may not support vision. Switch to 'llava' (Ollama) or 'gpt-4o' (OpenAI)."

        print(f"  👀 Analyzing screen with {model}...")
        
        # Basic implementation for Ollama with llava:
        # We need to construct a specific payload. Since our LLMProvider is generic text,
        # we might need to extend it or do a direct call here for vision specialized tasks.
        
        # Let's try a direct call to Ollama for vision if local
        if self.llm.provider == "ollama":
            import requests
            with open(path, "rb") as f:
                img_bytes = f.read()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            payload = {
                "model": "llava", # Default vision model for local
                "prompt": query,
                "images": [img_b64],
                "stream": False
            }
            try:
                r = requests.post(f"{self.llm.ollama_host}/api/generate", json=payload, timeout=60)
                if r.status_code == 200:
                    return r.json().get("response", "No response")
                elif r.status_code == 404:
                    return "Error: Model 'llava' not found. Run `ollama pull llava` first."
            except Exception as e:
                return f"Vision API Error: {e}"

        return "Vision analysis only implemented for local Ollama (llava) currently."

    def analyze_image(self, path_or_url: str, query: str = "Describe this image in detail.") -> str:
        """
        Fix #11: Multimodal image analysis for arbitrary files or URLs.
        Routes to GPT-4o Vision, Gemini Vision, or LLaVA based on provider.
        """
        import requests

        # Load image as base64 if local file
        b64_image = None
        if os.path.exists(path_or_url):
            with open(path_or_url, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode("utf-8")
            # Guess mime type
            ext = os.path.splitext(path_or_url)[1].lower()
            mime = {"png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/png")
        else:
            # Treat as URL
            mime = "image/jpeg"

        provider = self.llm.provider

        # GPT-4o Vision
        if provider == "openai" and self.llm.api_key:
            try:
                image_payload = (
                    {"type": "image_url", "image_url": {"url": path_or_url}}
                    if not b64_image else
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}}
                )
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.llm.api_key}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": [
                            {"type": "text", "text": query},
                            image_payload,
                        ]}],
                        "max_tokens": 1024,
                    },
                    timeout=60,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"GPT-4o Vision error: {e}"

        # Gemini Vision
        try:
            from config import CONFIG
            if provider == "gemini" and CONFIG.gemini.api_key:
                model = CONFIG.gemini.model
                parts = [{"text": query}]
                if b64_image:
                    parts.append({"inlineData": {"mimeType": mime, "data": b64_image}})
                else:
                    parts.append({"fileData": {"mimeType": mime, "fileUri": path_or_url}})
                resp = requests.post(
                    f"{CONFIG.gemini.base_url}/models/{model}:generateContent?key={CONFIG.gemini.api_key}",
                    json={"contents": [{"parts": parts}]},
                    timeout=60,
                )
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    if candidates:
                        return "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
        except Exception as e:
            return f"Gemini Vision error: {e}"

        # LLaVA (Ollama local)
        if provider == "ollama" and b64_image:
            try:
                r = requests.post(
                    f"{self.llm.ollama_host}/api/generate",
                    json={"model": "llava", "prompt": query, "images": [b64_image], "stream": False},
                    timeout=120,
                )
                if r.status_code == 200:
                    return r.json().get("response", "No response from LLaVA")
                return "Error: LLaVA not available. Run: ollama pull llava"
            except Exception as e:
                return f"LLaVA error: {e}"

        return "No vision-capable provider configured. Set OPENAI_API_KEY (gpt-4o) or GEMINI_API_KEY or use Ollama with llava."

    # ==================================================
    #  ACTION (Do)
    # ==================================================
    def click(self, x: int, y: int):
        """Move mouse and click."""
        if not VISION_AVAILABLE: return "Error: Vision module inactive."
        try:
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})"
        except Exception as e:
            return f"Click failed: {e}"

    def type_text(self, text: str):
        """Type text via keyboard."""
        if not VISION_AVAILABLE: return "Error: Vision module inactive."
        try:
            pyautogui.write(text, interval=0.1)
            return f"Typed: {text}"
        except Exception as e:
            return f"Type failed: {e}"
            
    def press(self, key: str):
        """Press a key (e.g., 'enter', 'esc')."""
        if not VISION_AVAILABLE: return "Error: Vision module inactive."
        try:
            pyautogui.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Press failed: {e}"
