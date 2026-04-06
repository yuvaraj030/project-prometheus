
import sys
import unittest
from unittest.mock import MagicMock, patch
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rl_hobby import RLHobbyEngine

# Optional skip if gymnasium not installed
try:
    import gymnasium
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

class TestRLHobby(unittest.TestCase):
    def setUp(self):
        self.engine = RLHobbyEngine(env_name="CartPole-v1")

    @unittest.skipIf(not GYM_AVAILABLE, "Gymnasium not installed")
    @patch('gymnasium.make')
    def test_start_stop_training(self, mock_gym_make):
        # Create a mock environment
        mock_env = MagicMock()
        mock_env.reset.return_value = ([0, 0, 0, 0], {})
        mock_env.step.return_value = ([0, 0, 0, 0], 1.0, True, False, {})
        mock_env.action_space.n = 2
        mock_env.action_space.sample.return_value = 1
        
        mock_gym_make.return_value = mock_env

        # Start, wait momentarily, then stop
        self.engine.start_training()
        self.assertTrue(self.engine.running)
        
        # In a real test we'd wait, but here we just stop immediately to verify state flags
        self.engine.stop_training()
        self.assertFalse(self.engine.running)

    def test_discretize_state(self):
        state = [0.0, 0.0, 0.0, 0.0]
        bins = (10, 10, 10, 10)
        d_state = self.engine._discretize_state(state, bins)
        self.assertEqual(len(d_state), 4)
        for val in d_state:
            self.assertTrue(0 <= val < 10)

if __name__ == '__main__':
    unittest.main()
