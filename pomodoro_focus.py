"""
Pomodoro Focus Timer — 25-min work / 5-min break cycle.
Provides /focus start|stop|status|skip commands.
"""

import time
import threading
import json
import os
from datetime import datetime


class PomodoroFocus:
    """Track focus sessions with Pomodoro technique."""

    WORK_DURATION = 25 * 60   # 25 minutes
    SHORT_BREAK = 5 * 60      # 5 minutes
    LONG_BREAK = 15 * 60      # 15 minutes (every 4 pomodoros)
    DATA_FILE = "pomodoro_data.json"

    def __init__(self, llm_provider=None, checkin_callback=None):
        self.llm = llm_provider
        self.checkin_callback = checkin_callback  # called with message at break
        self._state = "idle"   # idle / working / break
        self._start_time = None
        self._timer_thread = None
        self._stop_event = threading.Event()
        self._data = self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions_completed": 0, "total_focus_minutes": 0, "history": []}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    # ── Core Logic ───────────────────────────────────────────────────────────

    def start(self, task_name: str = "Focus Session"):
        """Start a 25-minute Pomodoro session."""
        if self._state == "working":
            return {"status": "already_running", "message": "⏱️ A Pomodoro is already in progress!"}
        self._stop_event.clear()
        self._state = "working"
        self._start_time = time.time()
        self._current_task = task_name
        self._timer_thread = threading.Thread(
            target=self._run_timer, daemon=True
        )
        self._timer_thread.start()
        return {
            "status": "started",
            "message": f"🍅 Pomodoro started! Focus on: '{task_name}'\n"
                       f"   ⏱️ 25 minutes of deep work begins now.\n"
                       f"   I'll check in at the break. GO! 💪"
        }

    def stop(self):
        """Stop the current session."""
        if self._state == "idle":
            return {"status": "not_running", "message": "No active Pomodoro session."}
        self._stop_event.set()
        self._state = "idle"
        elapsed = int((time.time() - self._start_time) / 60) if self._start_time else 0
        return {
            "status": "stopped",
            "message": f"⏹️ Session stopped after {elapsed} min. Good effort — every minute counts! 🎯"
        }

    def skip_break(self):
        """Skip the current break."""
        if self._state != "break":
            return "No break active to skip."
        self._stop_event.set()
        time.sleep(0.2)
        return self.start(getattr(self, '_current_task', 'Next Session'))

    def status(self):
        """Return current status."""
        if self._state == "idle":
            return {
                "state": "idle",
                "sessions_completed": self._data["sessions_completed"],
                "total_focus_minutes": self._data["total_focus_minutes"],
                "message": f"💤 No active session.\n   ✅ Completed: {self._data['sessions_completed']} Pomodoros\n   ⏱️ Total Focus: {self._data['total_focus_minutes']} min"
            }
        elapsed = int((time.time() - self._start_time) / 60) if self._start_time else 0
        if self._state == "working":
            remaining = max(0, 25 - elapsed)
            return {
                "state": "working",
                "task": getattr(self, '_current_task', ''),
                "elapsed_min": elapsed,
                "remaining_min": remaining,
                "message": f"🍅 WORKING — '{getattr(self,'_current_task','')}'\n   ⏳ {elapsed}m elapsed | {remaining}m remaining"
            }
        else:
            remaining = max(0, 5 - elapsed)
            return {
                "state": "break",
                "remaining_min": remaining,
                "message": f"☕ ON BREAK — {remaining}m remaining. Stretch, hydrate!"
            }

    def _run_timer(self):
        """Background timer thread."""
        # Work phase
        end = self._start_time + self.WORK_DURATION
        while time.time() < end and not self._stop_event.is_set():
            time.sleep(1)

        if self._stop_event.is_set():
            return

        # Session complete
        self._data["sessions_completed"] += 1
        self._data["total_focus_minutes"] += 25
        self._data["history"].append({
            "task": getattr(self, '_current_task', ''),
            "completed_at": datetime.now().isoformat(),
            "duration_min": 25
        })
        self._data["history"] = self._data["history"][-100:]  # keep last 100
        self._save()

        # Check-in message
        checkin_msg = self._generate_checkin()
        if self.checkin_callback:
            self.checkin_callback(f"\n🍅 POMODORO COMPLETE! #{self._data['sessions_completed']}\n{checkin_msg}\n☕ Take a 5-minute break!")

        # Break phase
        self._state = "break"
        self._start_time = time.time()
        break_end = self._start_time + self.SHORT_BREAK
        while time.time() < break_end and not self._stop_event.is_set():
            time.sleep(1)

        if self._stop_event.is_set():
            return

        self._state = "idle"
        if self.checkin_callback:
            self.checkin_callback("⏰ Break over! Ready for the next Pomodoro? Type /focus start")

    def _generate_checkin(self):
        """Generate an LLM check-in message."""
        if not self.llm:
            msgs = [
                "Excellent focus session! Your brain has been working hard. 🧠",
                "25 minutes of pure focus — you're building momentum! 🚀",
                "Another Pomodoro in the books! Consistency is the key to mastery. 🏆",
            ]
            idx = self._data["sessions_completed"] % len(msgs)
            return msgs[idx]
        try:
            count = self._data["sessions_completed"]
            task = getattr(self, '_current_task', 'work')
            prompt = (
                f"The user just completed Pomodoro #{count} working on '{task}'. "
                "Give them a short (2-sentence) energetic, motivating check-in message. "
                "Be specific and uplifting. No fluff."
            )
            return self.llm.chat(prompt, system="You are an energetic productivity coach.") or ""
        except Exception:
            return "Great work! Keep the momentum going. 💪"

    def get_stats(self):
        """Return full statistics."""
        return {
            "sessions_completed": self._data["sessions_completed"],
            "total_focus_minutes": self._data["total_focus_minutes"],
            "total_focus_hours": round(self._data["total_focus_minutes"] / 60, 1),
            "recent_sessions": self._data["history"][-5:]
        }
