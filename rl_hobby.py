"""
Game Engine Reinforcement Learning (Feature 7)
Allows the agent to spin up headless gymnasium environments
and train simple RL models during idle time.
"""

import threading
import time
import logging

try:
    import gymnasium as gym
    import numpy as np
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

logger = logging.getLogger("RLHobby")

class RLHobbyEngine:
    """
    A lightweight background trainer.
    When the agent is bored or has high energy, it plays games
    (like CartPole) in memory to "dream" and learn.
    """
    def __init__(self, env_name: str = "CartPole-v1"):
        self.env_name = env_name
        self.running = False
        self.thread = None
        self.episodes_played = 0
        self.best_score = 0.0
        # A very rudimentary Q-table mapping (simplified for demo)
        self.q_table = {}

    def start_training(self):
        if not GYM_AVAILABLE:
            logger.warning("Gymnasium (gym) not installed. RL Hobby disabled.")
            return

        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._training_loop, daemon=True)
        self.thread.start()
        logger.info(f"RL Hobby Engine started training on {self.env_name}.")

    def stop_training(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("RL Hobby Engine stopped.")

    def _discretize_state(self, state, bins=(10, 10, 10, 10)):
        """Utility for simple tabular Q-learning on continuous states."""
        # This is strictly a naive discretization for CartPole
        upper_bounds = [4.8, 4, 0.418, 4]
        lower_bounds = [-4.8, -4, -0.418, -4]
        ratios = [(state[i] + abs(lower_bounds[i])) / (upper_bounds[i] - lower_bounds[i]) for i in range(len(state))]
        new_obs = [int(round((bins[i] - 1) * ratios[i])) for i in range(len(state))]
        new_obs = [min(bins[i] - 1, max(0, new_obs[i])) for i in range(len(state))]
        return tuple(new_obs)

    def _training_loop(self):
        """Play headless episodes continuously."""
        try:
            env = gym.make(self.env_name)
        except Exception as e:
            logger.error(f"Failed to create gym environment {self.env_name}: {e}")
            self.running = False
            return

        alpha = 0.1
        gamma = 0.99
        epsilon = 0.1

        while self.running:
            state, _ = env.reset()
            state = self._discretize_state(state)
            done = False
            total_reward = 0

            while not done and self.running:
                # Epsilon-greedy action
                if np.random.uniform(0, 1) < epsilon:
                    action = env.action_space.sample()
                else:
                    q_vals = [self.q_table.get((state, a), 0.0) for a in range(env.action_space.n)]
                    action = np.argmax(q_vals)

                next_state_raw, reward, terminated, truncated, _ = env.step(action)
                next_state = self._discretize_state(next_state_raw)
                done = terminated or truncated

                # Best next action
                next_max = max([self.q_table.get((next_state, a), 0.0) for a in range(env.action_space.n)])
                
                # Update Q-table
                current_q = self.q_table.get((state, action), 0.0)
                self.q_table[(state, action)] = current_q + alpha * (reward + gamma * next_max - current_q)

                state = next_state
                total_reward += reward

            self.episodes_played += 1
            if total_reward > self.best_score:
                self.best_score = total_reward
                logger.debug(f"New best score in {self.env_name}: {self.best_score}")

            # Sleep to prevent burning 100% CPU on a background task
            time.sleep(0.05)
            
        env.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    engine = RLHobbyEngine()
    print("Testing RL Hobby Engine for 3 seconds...")
    engine.start_training()
    time.sleep(3)
    engine.stop_training()
    print(f"Played {engine.episodes_played} episodes. Best score: {engine.best_score}")

