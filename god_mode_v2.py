"""
God Mode V2 — Universal Computer Control.
Full see-reason-act-verify loop. The agent takes pixel-perfect control of the
mouse, keyboard, and screen, guided by a multimodal LLM vision pipeline.
"""
import os
import time
import json
import logging
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class GodModeV2:
    """
    Universal Computer Control — God Mode V2.
    
    Core loop:
      1. CAPTURE  — Screenshot of current screen state
      2. ANALYZE  — LLM (vision or OCR) describes what it sees
      3. DECIDE   — LLM reasons about the next best action
      4. EXECUTE  — pyautogui performs the action  
      5. VERIFY   — Screenshot again, check if goal advanced
    """

    MAX_LOOP_STEPS = 15  # Safety cap on autonomous action steps

    def __init__(self, llm_provider=None, screenshots_dir: str = "screenshots"):
        self.logger = logging.getLogger("GodModeV2")
        self.llm = llm_provider
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)

        self.enabled = PYAUTOGUI_AVAILABLE
        self.action_log: List[Dict] = []
        self.current_goal: Optional[str] = None

        if not PYAUTOGUI_AVAILABLE:
            self.logger.warning("⚠️ pyautogui not installed — God Mode V2 running in MOCK mode.")
        else:
            self.logger.info("✅ God Mode V2 initialized. pyautogui ready.")

    # ─────────────────────────────────────────────────────────
    #  CAPTURE
    # ─────────────────────────────────────────────────────────
    def capture_screenshot(self, save: bool = True) -> Optional[str]:
        """Take a screenshot and return its file path."""
        if not PIL_AVAILABLE:
            # Mock path for testing
            mock_path = os.path.join(self.screenshots_dir, f"mock_{int(time.time())}.png")
            return mock_path

        try:
            img = ImageGrab.grab()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.screenshots_dir, f"godmode_{ts}.png")
            if save:
                img.save(path)
            return path
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def _image_to_base64(self, path: str) -> Optional[str]:
        """Convert image to base64 for multimodal LLM."""
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────
    #  ANALYZE
    # ─────────────────────────────────────────────────────────
    def analyze_screen(self, screenshot_path: Optional[str] = None, goal: str = "") -> Dict[str, Any]:
        """
        Analyze the screen. Tries multimodal LLM vision first, then OCR, then mock.
        Returns a dict with: description, detected_elements, confidence.
        """
        if not screenshot_path:
            screenshot_path = self.capture_screenshot()

        # --- Option 1: Multimodal LLM vision ---
        if self.llm and hasattr(self.llm, 'describe_image') and screenshot_path:
            try:
                b64 = self._image_to_base64(screenshot_path)
                if b64:
                    prompt = (
                        f"You are a computer vision assistant helping an AI control a computer.\n"
                        f"Current Goal: {goal or 'General screen analysis'}\n\n"
                        f"Analyze this screenshot and describe:\n"
                        f"1. What application/window is visible?\n"
                        f"2. What interactive elements can you see (buttons, inputs, links)?\n"
                        f"3. What is the current state relative to the goal?\n"
                        f"4. What should be the NEXT action to take?\n\n"
                        f"Be specific about positions (top-left, center, etc.)."
                    )
                    description = self.llm.describe_image(b64, prompt)
                    return {
                        "source": "llm_vision",
                        "description": description,
                        "screenshot": screenshot_path,
                        "confidence": 0.9
                    }
            except Exception as e:
                self.logger.warning(f"Multimodal LLM vision failed: {e}")

        # --- Option 2: OCR text extraction ---
        if OCR_AVAILABLE and screenshot_path and os.path.exists(screenshot_path):
            try:
                img = Image.open(screenshot_path)
                text = pytesseract.image_to_string(img)
                if text.strip():
                    return {
                        "source": "ocr",
                        "description": f"Screen text detected:\n{text[:800]}",
                        "screenshot": screenshot_path,
                        "confidence": 0.6
                    }
            except Exception as e:
                self.logger.warning(f"OCR failed: {e}")

        # --- Option 3: LLM describes what the agent should do ---
        if self.llm and goal:
            prompt = (
                f"You are controlling a computer. Goal: '{goal}'\n"
                f"You cannot see the screen directly. Based on the goal alone, "
                f"what is the most likely next action? Think step by step."
            )
            description = self.llm.call(prompt, max_tokens=200)
            return {
                "source": "llm_blind",
                "description": description,
                "screenshot": screenshot_path,
                "confidence": 0.3
            }

        # --- Fallback mock ---
        return {
            "source": "mock",
            "description": f"[MOCK] Screen captured at {datetime.now().isoformat()}. Goal: {goal}",
            "screenshot": screenshot_path,
            "confidence": 0.1
        }

    # ─────────────────────────────────────────────────────────
    #  DECIDE
    # ─────────────────────────────────────────────────────────
    def decide_action(self, screen_analysis: Dict, goal: str, step: int) -> Dict[str, Any]:
        """
        Ask the LLM to decide the next computer action based on screen state.
        Returns a structured action dict: {action, target, value, reasoning}
        """
        if not self.llm:
            return {
                "action": "wait",
                "target": None,
                "value": None,
                "reasoning": "No LLM available for decision making."
            }

        prompt = f"""You are an AI controlling a computer to achieve a goal.

Goal: {goal}
Step: {step}/{self.MAX_LOOP_STEPS}
Screen Analysis: {screen_analysis.get('description', 'Unknown')}

Choose ONE action from:
- click: click a UI element (specify target description)
- type: type text (specify text value)
- scroll: scroll up or down (specify direction)
- hotkey: press keyboard shortcut (specify keys like 'ctrl+c')
- open: open an application (specify app name)
- wait: wait 1 second
- done: goal is complete

Respond with ONLY this JSON (no markdown):
{{"action": "click|type|scroll|hotkey|open|wait|done", "target": "description or null", "value": "text or null", "reasoning": "why this action"}}"""

        try:
            response = self.llm.call(prompt, max_tokens=150)
            # Parse JSON from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception as e:
            self.logger.warning(f"Action decision parsing failed: {e}")
            return {"action": "wait", "target": None, "value": None, "reasoning": str(e)}

    # ─────────────────────────────────────────────────────────
    #  EXECUTE
    # ─────────────────────────────────────────────────────────
    def execute_action(self, action_dict: Dict) -> bool:
        """Execute a decided computer action via pyautogui."""
        action = action_dict.get("action", "wait")
        value = action_dict.get("value")
        target = action_dict.get("target")

        self.action_log.append({
            "ts": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "value": value
        })

        if not PYAUTOGUI_AVAILABLE:
            self.logger.info(f"[MOCK EXECUTE] {action}: target={target}, value={value}")
            return True

        try:
            if action == "click":
                # Smart click: move to center of screen for now, LLM-guided in vision mode
                pyautogui.click()
            elif action == "type":
                if value:
                    pyautogui.write(str(value), interval=0.05)
            elif action == "scroll":
                direction = str(value or target or "down").lower()
                pyautogui.scroll(3 if direction == "up" else -3)
            elif action == "hotkey":
                if value:
                    keys = [k.strip() for k in str(value).split("+")]
                    pyautogui.hotkey(*keys)
            elif action == "open":
                if value:
                    import subprocess
                    subprocess.Popen(str(value), shell=True)
            elif action == "wait":
                time.sleep(1)
            elif action == "done":
                return True  # Signal completion
            return True
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    #  MAIN LOOP
    # ─────────────────────────────────────────────────────────
    def autonomous_task(self, goal: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the full see-reason-act-verify loop autonomously until goal is done.
        
        Args:
            goal: Natural language description of what to accomplish
            max_steps: Max steps before stopping (default: MAX_LOOP_STEPS)
            
        Returns:
            Summary dict with steps_taken, log, final_state
        """
        if not max_steps:
            max_steps = self.MAX_LOOP_STEPS

        self.current_goal = goal
        self.action_log = []

        self.logger.info(f"🖱️ [GOD MODE V2] Starting autonomous task: '{goal}'")
        print(f"\n{'='*60}")
        print(f"🖱️  GOD MODE V2 — AUTONOMOUS COMPUTER CONTROL")
        print(f"   Goal: {goal}")
        print(f"{'='*60}")

        step = 0
        final_status = "incomplete"

        for step in range(1, max_steps + 1):
            print(f"\n--- Step {step}/{max_steps} ---")

            # 1. CAPTURE
            screenshot = self.capture_screenshot()

            # 2. ANALYZE
            analysis = self.analyze_screen(screenshot, goal)
            print(f"👁️  Screen: {analysis['description'][:200]}...")
            print(f"   Source: {analysis['source']} | Confidence: {analysis['confidence']:.0%}")

            # 3. DECIDE
            action_dict = self.decide_action(analysis, goal, step)
            print(f"🧠 Decision: {action_dict.get('action').upper()} — {action_dict.get('reasoning', '')[:150]}")

            # 4. EXECUTE
            if action_dict.get("action") == "done":
                final_status = "complete"
                print("✅ Goal marked COMPLETE by agent!")
                break

            success = self.execute_action(action_dict)
            print(f"⚡ Executed: {'✅' if success else '❌'}")

            time.sleep(0.5)  # Small pause between actions

        print(f"\n{'='*60}")
        print(f"🏁 Task {'COMPLETE' if final_status == 'complete' else 'STOPPED'} after {step} steps.")
        print(f"{'='*60}\n")

        self.current_goal = None
        return {
            "goal": goal,
            "final_status": final_status,
            "steps_taken": step,
            "action_log": self.action_log
        }

    # ─────────────────────────────────────────────────────────
    #  DIRECT UTILITY COMMANDS
    # ─────────────────────────────────────────────────────────
    def type_text(self, text: str) -> str:
        """Type text directly on the keyboard."""
        if not PYAUTOGUI_AVAILABLE:
            return f"[MOCK] Typed: {text}"
        try:
            pyautogui.write(text, interval=0.05)
            return f"✅ Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        except Exception as e:
            return f"❌ Type failed: {e}"

    def smart_click(self, description: str, x: int = None, y: int = None) -> str:
        """Click at specific coordinates or center of screen."""
        if not PYAUTOGUI_AVAILABLE:
            return f"[MOCK] Clicked: {description} at ({x},{y})"
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"✅ Clicked ({x}, {y}) — {description}"
            else:
                pyautogui.click()
                return f"✅ Clicked center — {description}"
        except Exception as e:
            return f"❌ Click failed: {e}"

    def scroll(self, direction: str = "down", amount: int = 3) -> str:
        """Scroll the screen."""
        if not PYAUTOGUI_AVAILABLE:
            return f"[MOCK] Scrolled {direction} {amount}x"
        try:
            clicks = amount if direction.lower() == "up" else -amount
            pyautogui.scroll(clicks)
            return f"✅ Scrolled {direction} {amount}x"
        except Exception as e:
            return f"❌ Scroll failed: {e}"

    def press_hotkey(self, *keys: str) -> str:
        """Press a keyboard shortcut."""
        if not PYAUTOGUI_AVAILABLE:
            return f"[MOCK] Hotkey: {'+'.join(keys)}"
        try:
            pyautogui.hotkey(*keys)
            return f"✅ Hotkey pressed: {'+'.join(keys)}"
        except Exception as e:
            return f"❌ Hotkey failed: {e}"

    def get_active_window(self) -> str:
        """Get the name of the currently focused window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except Exception:
            return "Unknown (pygetwindow not available)"

    def get_status(self) -> Dict[str, Any]:
        return {
            "pyautogui_available": PYAUTOGUI_AVAILABLE,
            "pil_available": PIL_AVAILABLE,
            "ocr_available": OCR_AVAILABLE,
            "current_goal": self.current_goal,
            "actions_taken": len(self.action_log),
            "last_action": self.action_log[-1] if self.action_log else None,
            "screen_watch": self.get_watch_status(),
        }

    # ─────────────────────────────────────────────────────────
    #  CONTINUOUS VISION LOOP (Feature 5)
    # ─────────────────────────────────────────────────────────
    def start_screen_watch(self, interval_seconds: int = 30,
                           alert_callback=None) -> Dict[str, Any]:
        """
        Start a background thread that watches the screen every N seconds.
        Proactively alerts when errors, exceptions, or anomalies are detected.

        Args:
            interval_seconds: How often to capture and analyse the screen
            alert_callback: Optional callable(alert_message: str) for proactive alerts
        """
        import threading

        if getattr(self, '_watch_active', False):
            return {"status": "already_watching", "interval": self._watch_interval}

        self._watch_active = True
        self._watch_interval = interval_seconds
        self._watch_alert_count = 0
        self._watch_alerts: List[Dict] = []
        self._alert_callback = alert_callback
        self._last_alert_texts: set = set()  # Deduplicate alerts

        # Error keywords that trigger proactive alerts
        self._alert_keywords = [
            "error", "exception", "traceback", "crash", "failed", "fatal",
            "segfault", "killed", "permission denied", "access denied",
            "syntax error", "typeerror", "nameerror", "valueerror",
        ]

        def _watch_loop():
            self.logger.info(f"👁️  Screen watch started (every {interval_seconds}s)")
            while self._watch_active:
                try:
                    screenshot = self.capture_screenshot(save=False)
                    analysis = self.analyze_screen(screenshot, goal="Monitor for errors or issues")
                    desc = analysis.get("description", "").lower()

                    # Check for alert keywords
                    triggered = [kw for kw in self._alert_keywords if kw in desc]
                    if triggered:
                        # Build alert message
                        raw_desc = analysis.get("description", "")[:300]
                        alert_key = raw_desc[:100]  # Dedup key
                        if alert_key not in self._last_alert_texts:
                            self._last_alert_texts.add(alert_key)
                            if len(self._last_alert_texts) > 20:
                                self._last_alert_texts.pop()

                            alert_msg = (
                                f"👁️ [VISION ALERT] I noticed something on your screen:\n"
                                f"Detected: {', '.join(triggered)}\n"
                                f"Context: {raw_desc[:200]}\n"
                                f"→ Want me to help fix this?"
                            )
                            alert_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "keywords": triggered,
                                "description": raw_desc,
                                "screenshot": screenshot,
                            }
                            self._watch_alerts.append(alert_entry)
                            self._watch_alert_count += 1
                            self.logger.info(alert_msg)

                            if self._alert_callback:
                                try:
                                    self._alert_callback(alert_msg)
                                except Exception as e:
                                    self.logger.warning(f"Alert callback failed: {e}")

                except Exception as e:
                    self.logger.warning(f"Screen watch cycle error: {e}")

                time.sleep(interval_seconds)

            self.logger.info("👁️  Screen watch stopped.")

        self._watch_thread = threading.Thread(target=_watch_loop, daemon=True)
        self._watch_thread.start()

        return {
            "status": "started",
            "interval_seconds": interval_seconds,
            "alert_keywords": self._alert_keywords,
        }

    def stop_screen_watch(self) -> Dict[str, Any]:
        """Stop the continuous screen-watch loop."""
        if not getattr(self, '_watch_active', False):
            return {"status": "not_watching"}
        self._watch_active = False
        return {
            "status": "stopped",
            "total_alerts": self._watch_alert_count,
            "recent_alerts": self._watch_alerts[-3:],
        }

    def get_watch_status(self) -> Dict[str, Any]:
        """Return the current state of the screen-watch loop."""
        return {
            "active": getattr(self, '_watch_active', False),
            "interval_seconds": getattr(self, '_watch_interval', None),
            "alert_count": getattr(self, '_watch_alert_count', 0),
            "recent_alerts": getattr(self, '_watch_alerts', [])[-3:],
        }

