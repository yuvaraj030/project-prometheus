import unittest
from unittest.mock import MagicMock, patch
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from biometric_empathy import BiometricEmpathyEngine

class TestBiometricEmpathy(unittest.TestCase):
    def setUp(self):
        self.mock_consciousness = MagicMock()
        self.mock_consciousness.user_model = {"mood_estimate": 0.5}
        self.engine = BiometricEmpathyEngine(self.mock_consciousness)

    def test_update_consciousness_happy(self):
        self.engine._update_consciousness("happy")
        self.mock_consciousness.feel.assert_called_with("user_happy", 0.1)
        self.assertEqual(self.mock_consciousness.user_model["mood_estimate"], 0.55)
        self.mock_consciousness.think_inner.assert_called()

    def test_update_consciousness_sad(self):
        self.engine._update_consciousness("sad")
        self.mock_consciousness.feel.assert_called_with("user_frustrated", 0.1)
        self.assertEqual(self.mock_consciousness.user_model["mood_estimate"], 0.45)
        self.mock_consciousness.think_inner.assert_called()

    @patch('cv2.VideoCapture')
    def test_analyze_snapshot_no_camera(self, mock_vidcap):
        mock_cap_instance = MagicMock()
        mock_cap_instance.isOpened.return_value = False
        mock_vidcap.return_value = mock_cap_instance
        
        emotion = self.engine.analyze_snapshot()
        self.assertIsNone(emotion)

if __name__ == '__main__':
    unittest.main()
