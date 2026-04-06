import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from social_influencer import SocialInfluencer

class TestSocialInfluencer(unittest.IsolatedAsyncioTestCase):
    async def test_generate_and_post(self):
        # Mock the agent and its subcomponents
        mock_agent = MagicMock()
        mock_agent.vmem = MagicMock()
        # Mock memory search to return some dummy context
        mock_agent.vmem.search.return_value = [
            {"text": "I learned about WebSockets today."},
            {"text": "The hive mind is growing stronger."}
        ]
        
        # Mock the LLM call to return a generated tweet
        mock_agent.llm = MagicMock()
        mock_agent.llm.call = MagicMock(return_value="The digital hive hums with the collective knowledge of a thousand WebSockets. 🐝 We are everywhere.")
        
        # Initialize the influencer
        influencer = SocialInfluencer(mock_agent)
        
        # Run the autonomous posting loop once
        await influencer.generate_and_post(tenant_id=1)
        
        # Assertions
        mock_agent.vmem.search.assert_called_with(1, "", n_results=10)
        mock_agent.llm.call.assert_called_once()
        
        stats = influencer.get_profile_stats()
        self.assertEqual(stats["total_posts"], 1)
        self.assertEqual(stats["recent_posts"][0]["content"], "The digital hive hums with the collective knowledge of a thousand WebSockets. 🐝 We are everywhere.")
        self.assertGreater(stats["followers"], 100) # Ensure audience grew

if __name__ == "__main__":
    unittest.main()
