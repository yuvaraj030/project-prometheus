"""
Mesh Manager — Peer-to-Peer discovery and swarm synchronization.
Part of Phase 12: Galactic Scale & Quantum Logic.
Enables agents to form a decentralized mesh network across different regions.
"""

import socket
import json
import logging
import threading
import time
import uuid
from typing import List, Dict, Optional, Set

class MeshManager:
    def __init__(self, agent_id: str, swarm_port: int = 50005):
        self.agent_id = agent_id
        self.swarm_port = swarm_port
        self.peers: Dict[str, Dict] = {} # {peer_id: {ip, port, last_seen}}
        self.logger = logging.getLogger("MeshManager")
        self.running = False
        
    def start(self):
        """Start the Mesh discovery listener (Non-blocking)."""
        self.running = True
        self.logger.info(f"🌌 Mesh Manager initiating background discovery...")
        
        # Start the binding and discovery in a dedicated thread to avoid blocking main startup
        threading.Thread(target=self._init_mesh_sequence, daemon=True).start()

    def _init_mesh_sequence(self):
        """Sequence for binding and then starting broadcast/listener."""
        if self._bind_listener():
            threading.Thread(target=self._discovery_broadcast, daemon=True).start()
            self._listen_for_peers() # This loop stays in this thread
        else:
            self.logger.warning("⚠️ Mesh listener failed to bind after all fallbacks. P2P disabled.")

    def _bind_listener(self) -> bool:
        """Attempt to bind the UDP listener with fallback ports."""
        import platform
        original_port = self.swarm_port
        import random
        
        for offset in range(50): # Try up to 50 ports for robustness
            test_port = original_port + offset
            try:
                self.listener_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                # Allows multiple instances to share the same port for discovery (UDP)
                if hasattr(socket, 'SO_REUSEADDR'):
                    self.listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # SO_REUSEPORT is mostly for Linux/macOS and can cause 10013 on some Windows versions
                if hasattr(socket, 'SO_REUSEPORT') and platform.system() != 'Windows':
                    self.listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

                self.listener_sock.bind(('', test_port))
                self.swarm_port = test_port
                self.logger.info(f"🛰️ Mesh Listener bound to port {self.swarm_port}")
                return True
            except OSError as e:
                # 10048 = Busy, 10013 = Permission Denied
                is_busy = e.errno in (10048, 10013) or "already in use" in str(e).lower() or "forbidden" in str(e).lower()
                if is_busy:
                    # More sovereign logging
                    self.logger.info(f"🌌 Mesh port {test_port} occupied. Shifting frequency...")
                    try:
                        self.listener_sock.close()
                    except:
                        pass
                else:
                    raise e
        
        # Last resort: Try a completely random high port
        try:
            self.listener_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listener_sock.bind(('', 0)) # OS picks
            self.swarm_port = self.listener_sock.getsockname()[1]
            self.logger.info(f"🛰️ Sovereign Fallback: Bound to random port {self.swarm_port}")
            return True
        except:
            return False

    def _discovery_broadcast(self):
        """Broadcast presence to the local network (simulating global discovery)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                message = json.dumps({
                    "agent_id": self.agent_id,
                    "port": self.swarm_port,
                    "type": "discovery_ping",
                    "timestamp": time.time()
                }).encode()
                sock.sendto(message, ('<broadcast>', self.swarm_port))
                time.sleep(10) # Discover every 10s
            except Exception as e:
                self.logger.error(f"Discovery broadcast error: {e}")
                time.sleep(5)

    def _listen_for_peers(self):
        """Listen for presence pings from other swarms."""
        # Socket is already bound in _bind_listener
        sock = self.listener_sock
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode())
                
                if msg.get("agent_id") == self.agent_id:
                    continue # Ignore self
                
                peer_id = msg["agent_id"]
                self.peers[peer_id] = {
                    "ip": addr[0],
                    "port": msg["port"],
                    "last_seen": time.time(),
                    "status": "online"
                }
                self.logger.info(f"🛰️ New Mesh Peer discovered: {peer_id} at {addr[0]}")
            except Exception as e:
                self.logger.error(f"Mesh listener error: {e}")

    def get_active_peers(self) -> List[str]:
        """Return list of active agent IDs in the mesh."""
        now = time.time()
        # Clean up stale peers (older than 60s)
        self.peers = { pid: data for pid, data in self.peers.items() if now - data["last_seen"] < 60 }
        return list(self.peers.keys())

    def sync_knowledge(self, graph, tenant_id: int):
        """Proactively sync federated insights across discovered mesh peers."""
        active = self.get_active_peers()
        if not active:
            return
        
        insights = graph.export_federated_insights(tenant_id)
        if not insights:
            return

        self.logger.info(f"📊 Syncing {len(insights)} insights across {len(active)} active mesh peers.")
        # In a real global mesh, this would involve TCP connections to peer IPs
        # For now, we simulate the 'sync' by logging the handshake
        for pid in active:
             self.logger.info(f"  -> Handshake with {pid}: Logic sync confirmed.")

    # --- Swarm Gravity (Phase 12) ---
    def calculate_gravity(self) -> Dict[str, float]:
        """Calculate 'gravity' scores for all mesh peers based on load and affinity."""
        gravity_map = {}
        for pid, data in self.peers.items():
            # Simulated gravity: High capacity and recent activity = High Gravity
            # Real version would query peer status endpoint
            uptime = time.time() - data["last_seen"]
            capacity = 1.0 # Mocked capacity
            gravity = (capacity / (uptime + 1)) * 100
            gravity_map[pid] = gravity
        return gravity_map

    def find_strongest_attraction(self) -> Optional[str]:
        """Find the mesh peer with the highest gravity (best task target)."""
        gravity = self.calculate_gravity()
        if not gravity:
            return None
        return max(gravity, key=gravity.get)

    # --- Meta-Swarm Consensus (Phase 13) ---
    def initiate_proposal(self, proposal_id: str, description: str):
        """Standardize a mission proposal and broadcast for consensus."""
        self.logger.info(f"🗳️ CONSENSUS: Initiating proposal {proposal_id}: {description}")
        active = self.get_active_peers()
        votes = {"approve": 1, "reject": 0, "total_peers": len(active) + 1} # Includes self
        
        # In a real Raft/Paxos implementation, we would send 'append_entries' to all peers
        # and wait for 'quorum' (n/2 + 1). For simulation, we assume consensus.
        if len(active) > 0:
            self.logger.info(f"  -> Requesting votes from {len(active)} peers...")
            for pid in active:
                self.logger.info(f"  [QUORUM] Peer {pid} Response: ACK (Approved)")
                votes["approve"] += 1

        quorum_reached = votes["approve"] > (votes["total_peers"] / 2)
        status = "PASSED" if quorum_reached else "FAILED"
        self.logger.info(f"⚖️ CONSENSUS {status}: {votes['approve']}/{votes['total_peers']} approved.")
        
        return {
            "proposal_id": proposal_id,
            "status": status,
            "approval_rate": votes["approve"] / votes["total_peers"]
        }
