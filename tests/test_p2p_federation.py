import unittest
import asyncio
import json
import logging
from unittest.mock import AsyncMock, patch
import websockets

from p2p_federation import P2PFederation

class TestP2PFederation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mute logging for tests
        logging.getLogger("P2PFederation").setLevel(logging.CRITICAL)

    async def test_start_and_stop(self):
        """Test that the P2P federation node can start and stop gracefully on available ports."""
        p2p1 = P2PFederation(agent_id="test_node_1", host="127.0.0.1", start_port=9980)
        await p2p1.start()
        
        self.assertTrue(p2p1.running)
        self.assertIsNotNone(p2p1.server)
        self.assertGreaterEqual(p2p1.port, 9980)
        
        await p2p1.stop()
        self.assertFalse(p2p1.running)
        
    async def test_peer_connection_and_handshake(self):
        """Test that two nodes can connect and exchange a handshake."""
        # Node 1 acts as the bootstrap reference point
        p2p1 = P2PFederation(agent_id="node_a", host="127.0.0.1", start_port=9990)
        await p2p1.start()
        
        # Node 2 connects to Node 1
        p2p2 = P2PFederation(
            agent_id="node_b", 
            host="127.0.0.1", 
            start_port=9995, 
            bootstrap_nodes=[f"ws://127.0.0.1:{p2p1.port}"]
        )
        await p2p2.start()
        
        # Wait a moment for the handshake to occur
        await asyncio.sleep(0.5)
        
        # Verify Node 1 saw Node 2, and Node 2 saw Node 1
        status1 = p2p1.get_network_status()
        status2 = p2p2.get_network_status()
        
        try:
            self.assertIn("node_b", status1["active_peers"])
            self.assertIn("node_a", status2["active_peers"])
        finally:
            await p2p1.stop()
            await p2p2.stop()
            
    async def test_broadcast_and_gossip(self):
        """Test that gossip messages are correctly broadcast to connected peers."""
        p2p1 = P2PFederation(agent_id="node_alpha", host="127.0.0.1", start_port=10000)
        await p2p1.start()
        
        p2p2 = P2PFederation(
            agent_id="node_beta", 
            host="127.0.0.1", 
            start_port=10005, 
            bootstrap_nodes=[f"ws://127.0.0.1:{p2p1.port}"]
        )
        await p2p2.start()
        
        await asyncio.sleep(0.5)
        
        # Node 1 broadcasts a gossip
        await p2p1.broadcast("gossip", "Hello from Alpha!")
        
        await asyncio.sleep(0.2) # Allow propagation
        
        status2 = p2p2.get_network_status()
        self.assertEqual(status2["recent_insights"], 1)
        self.assertEqual(p2p2.shared_insights[0]["gossip"], "Hello from Alpha!")
        
        await p2p1.stop()
        await p2p2.stop()

if __name__ == "__main__":
    unittest.main()
