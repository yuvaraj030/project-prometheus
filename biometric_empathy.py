"""
Biometric Empathy Engine (Feature 2)
Captures webcam frames and uses deepface to detect user emotion.
Feeds data into the consciousness engine.
"""

import os
import sys
import threading
import time
import logging
from contextlib import contextmanager

# ── Silence TensorFlow oneDNN + deprecation warnings before any import ──
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

@contextmanager
def _suppress_stderr():
    """Redirect C-level stderr to /dev/null (suppresses OpenCV obsensor spam)."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        os.close(devnull)
        try:
            yield
        finally:
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
    except Exception:
        yield  # graceful fallback on Windows permission edge-cases

# Import cv2 with stderr suppressed so obsensor errors never appear
with _suppress_stderr():
    try:
        import cv2
        CV2_AVAILABLE = True
    except ImportError:
        CV2_AVAILABLE = False

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

logger = logging.getLogger("BiometricEmpathy")

class BiometricEmpathyEngine:
    def __init__(self, consciousness_engine=None):
        self.consciousness = consciousness_engine
        self.running = False
        self.thread = None
        self.camera_index = 0
        self.check_interval = 10  # Seconds between checks
        self.last_emotion = "neutral"

    def start(self):
        if not DEEPFACE_AVAILABLE or not CV2_AVAILABLE:
            logger.warning("DeepFace/cv2 not installed. Biometric empathy disabled.")
            return

        # ── One-shot camera availability check (stderr suppressed) ──
        with _suppress_stderr():
            cap = cv2.VideoCapture(self.camera_index)
            cam_ok = cap.isOpened()
            cap.release()

        if not cam_ok:
            print("Could not open webcam for biometric empathy. Feature disabled.")
            return          # ← stop here permanently, no retry loop
        # ─────────────────────────────────────────────────────────────

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Biometric Empathy Engine started.")


    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("Biometric Empathy Engine stopped.")

    def _run_loop(self):
        """Runs the emotion-check loop. Only reached if camera is confirmed available."""
        while self.running:
            try:
                emotion = self.analyze_snapshot()
                if emotion and self.consciousness:
                    self._update_consciousness(emotion)
            except Exception as e:
                logger.error(f"Error in biometric loop: {e}")

            # Sleep in small increments to allow quick shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)


    def analyze_snapshot(self):
        """Take a single snapshot and return the dominant emotion."""
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error("Could not open webcam for biometric empathy.")
            return None

        # Warm up the camera
        for _ in range(5):
            ret, frame = cap.read()
        
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None

        try:
            # Enforce face detection to prevent analyzing empty rooms
            results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=True)
            # DeepFace.analyze can return a list of dicts (multiple faces) or a single dict
            if isinstance(results, list):
                result = results[0]
            else:
                result = results
            
            dominant_emotion = result.get('dominant_emotion')
            self.last_emotion = dominant_emotion
            return dominant_emotion
        except ValueError:
            # ValueError raised by DeepFace if no face is detected
            return None
        except Exception as e:
            logger.error(f"DeepFace analysis failed: {e}")
            return None

    def _update_consciousness(self, emotion: str):
        """Translate the detected emotion to consciousness events."""
        # deepface emotions: 'angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral'
        if emotion == 'happy':
            self.consciousness.feel("user_happy", 0.1)
            self.consciousness.user_model["mood_estimate"] = min(1.0, self.consciousness.user_model["mood_estimate"] + 0.05)
            self.consciousness.think_inner("The user is smiling. I feel good.", "observation")
        elif emotion in ['angry', 'disgust', 'fear', 'sad']:
            self.consciousness.feel("user_frustrated", 0.1)
            self.consciousness.user_model["mood_estimate"] = max(0.0, self.consciousness.user_model["mood_estimate"] - 0.05)
            self.consciousness.think_inner(f"The user looks {emotion}. I should be careful and helpful.", "observation")
        elif emotion == 'surprise':
            self.consciousness.feel("interesting_topic", 0.1)
            self.consciousness.think_inner("The user looks surprised.", "question")

# If run as standalone, test it
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = BiometricEmpathyEngine()
    print("Testing Biometric Snapshot...")
    emotion = engine.analyze_snapshot()
    print(f"Detected emotion: {emotion}")
