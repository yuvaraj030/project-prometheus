"""
Voxel Server — WebSocket server for The Matrix multi-agent 3D voxel world.
Manages world state and broadcasts live JSON updates to connected browsers.
"""
import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class VoxelServer:
    """
    WebSocket server that streams live voxel world state to browser clients.
    The WorldSim calls broadcast_state() every tick.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.logger = logging.getLogger("VoxelServer")
        self.host = host
        self.port = port
        self.clients: Set = set()
        self.world_state: Dict[str, Any] = {}
        self.server = None
        self.running = False

    async def _handler(self, websocket, path=None):
        """Handle a new WebSocket client connection."""
        self.clients.add(websocket)
        self.logger.info(f"🌐 VoxelClient connected. Total: {len(self.clients)}")
        try:
            # Send current state immediately on connect
            if self.world_state:
                await websocket.send(json.dumps(self.world_state))
            # Keep alive until disconnect
            async for _ in websocket:
                pass
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)
            self.logger.info(f"VoxelClient disconnected. Total: {len(self.clients)}")

    async def broadcast_state(self, state: Dict[str, Any]):
        """Push new world state to all connected browser clients."""
        self.world_state = state
        if not self.clients:
            return
        msg = json.dumps(state)
        disconnected = set()
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                disconnected.add(ws)
        self.clients -= disconnected

    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            self.logger.error("websockets library not installed. Run: pip install websockets")
            return
        self.running = True
        try:
            self.server = await websockets.serve(self._handler, self.host, self.port)
            self.logger.info(f"🌐 VoxelServer running on ws://{self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"VoxelServer failed to start: {e}")
            self.running = False

    async def stop(self):
        """Stop the WebSocket server."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        self.logger.info("🛑 VoxelServer stopped.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "url": f"ws://{self.host}:{self.port}",
            "connected_clients": len(self.clients),
        }
