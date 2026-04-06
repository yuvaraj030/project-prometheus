import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Any
import websockets
import socket

class P2PFederation:
    def __init__(self, agent_id: str, host: str = "0.0.0.0", start_port: int = 8765, bootstrap_nodes: List[str] = None):
        self.agent_id = agent_id
        self.host = host
        self.start_port = start_port
        self.port = start_port
        self.bootstrap_nodes = bootstrap_nodes or []
        self.peers: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.peer_ids: Set[str] = set()
        self.logger = logging.getLogger("P2PFederation")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        self.running = False
        self.server = None
        self.shared_insights = []

    async def start(self):
        self.running = True
        
        # Try to bind to an available port
        for offset in range(50):
            test_port = self.start_port + offset
            try:
                # We use a context manager later, but we can verify binding first
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((self.host, test_port))
                s.listen(1)
                s.close()
                self.port = test_port
                break
            except OSError:
                continue

        self.logger.info(f"🌐 Starting Global P2P Federation node '{self.agent_id}' on ws://{self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(self._handle_connection, self.host, self.port)
        except Exception as e:
            self.logger.error(f"Failed to start P2P server: {e}")
            return
            
        # Connect to bootstrap nodes
        for node in self.bootstrap_nodes:
            # Don't connect to ourselves if the bootstrap node points to our exact IP/port
            if str(self.port) in node and ("localhost" in node or "127.0.0.1" in node or "0.0.0.0" in node):
                continue
            asyncio.create_task(self._connect_to_peer(node))
            
        asyncio.create_task(self._gossip_loop())

    async def stop(self):
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
    async def _handle_connection(self, websocket):
        # Initial handshake
        try:
            handshake = json.dumps({"type": "handshake", "agent_id": self.agent_id})
            await websocket.send(handshake)
            
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("type") == "handshake":
                peer_id = data.get("agent_id")
                if peer_id == self.agent_id or peer_id in self.peer_ids:
                    return # Prevent self-connection or loops
                
                self.peers[websocket] = peer_id
                self.peer_ids.add(peer_id)
                self.logger.info(f"🤝 P2P Peer Joined Global Hive: {peer_id}")
                
                try:
                    async for message in websocket:
                        await self._process_message(peer_id, message)
                finally:
                    if websocket in self.peers:
                        self.peer_ids.remove(self.peers[websocket])
                        del self.peers[websocket]
                        self.logger.info(f"🛑 P2P Peer Disconnected: {peer_id}")
        except Exception as e:
            pass # Connection dropped or protocol mismatch

    async def _connect_to_peer(self, uri: str):
        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    # initial handshake handled on the other side by _handle_connection
                    response = await websocket.recv()
                    data = json.loads(response)
                    if data.get("type") == "handshake":
                        peer_id = data.get("agent_id")
                        
                        handshake = json.dumps({"type": "handshake", "agent_id": self.agent_id})
                        await websocket.send(handshake)
                        
                        if peer_id == self.agent_id or peer_id in self.peer_ids:
                            return
                        
                        self.peers[websocket] = peer_id
                        self.peer_ids.add(peer_id)
                        self.logger.info(f"🤝 P2P Connected to Hive Node: {peer_id} at {uri}")
                        
                        try:
                            while self.running:
                                message = await websocket.recv()
                                await self._process_message(peer_id, message)
                        except websockets.exceptions.ConnectionClosed:
                            pass
                        finally:
                            if websocket in self.peers:
                                self.peer_ids.remove(self.peers[websocket])
                                del self.peers[websocket]
                # Reconnect delay
                await asyncio.sleep(10)
            except Exception as e:
                # self.logger.debug(f"P2P Dial failed to {uri}: {e}")
                await asyncio.sleep(30) # try again later
                
    async def _process_message(self, sender_id: str, message: str):
        try:
            payload = json.loads(message)
            msg_type = payload.get("type")
            
            if msg_type == "gossip":
                content = payload.get("content")
                self.logger.info(f"📡 Hive Gossip from {sender_id}: {content}")
                self.shared_insights.append({"peer": sender_id, "gossip": content, "time": time.time()})
                # Keep only last 100
                if len(self.shared_insights) > 100:
                    self.shared_insights.pop(0)
                
            elif msg_type == "compute_request":
                # Handle resource sharing / swarm logic
                # For future: allow peers to delegate tasks if not overwhelmed
                pass
                
        except json.JSONDecodeError:
            pass

    async def broadcast(self, msg_type: str, content: Any):
        if not self.peers:
            return
            
        message = json.dumps({
            "type": msg_type,
            "sender_id": self.agent_id,
            "content": content,
            "timestamp": time.time()
        })
        
        websockets_to_remove = []
        for ws in self.peers.keys():
            try:
                await ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                websockets_to_remove.append(ws)
                
        for ws in websockets_to_remove:
            if ws in self.peers:
                self.peer_ids.remove(self.peers[ws])
                del self.peers[ws]
                
    async def _gossip_loop(self):
        while self.running:
            await asyncio.sleep(120)  # Every 2 minutes, gossip to peers
            if self.peers:
                status = "operational"
                tasks_completed = len(self.shared_insights) # dummy metric
                gossip_msg = f"Agent {self.agent_id} reporting {status}. Processed {tasks_completed} global insights."
                await self.broadcast("gossip", gossip_msg)

    def get_network_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.agent_id,
            "port": self.port,
            "active_peers": list(self.peer_ids),
            "recent_insights": len(self.shared_insights)
        }
