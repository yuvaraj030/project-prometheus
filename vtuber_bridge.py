"""
VTuber Bridge
Connects the agent's consciousness and voice to VTube Studio via WebSocket.
"""

import asyncio
import json
import logging
from typing import Dict, Any

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class VTuberBridge:
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.uri = f"ws://{host}:{port}"
        self.logger = logging.getLogger("VTuberBridge")
        self.ws = None
        self.auth_token = None
        self.plugin_name = "UltimateAgent"
        self.plugin_developer = "Agentic"
        self.is_connected = False
        
    async def connect(self):
        if not WEBSOCKETS_AVAILABLE:
            self.logger.warning("websockets not installed. VTuber integration disabled.")
            return

        try:
            self.ws = await websockets.connect(self.uri)
            self.is_connected = True
            self.logger.info("✅ Connected to VTube Studio.")
            await self._authenticate()
        except Exception as e:
            self.logger.error(f"Failed to connect to VTube Studio: {e}")
            self.is_connected = False
            
    async def _send_request(self, message_type: str, data: Dict = None) -> Dict:
        if not self.is_connected or not self.ws:
            return {}
            
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "UltimateAgent_1",
            "messageType": message_type,
            "data": data or {}
        }
        try:
            await self.ws.send(json.dumps(request))
            response_str = await self.ws.recv()
            return json.loads(response_str)
        except Exception as e:
            self.logger.error(f"VTS Request failed: {e}")
            self.is_connected = False
            return {}

    async def _authenticate(self):
        # 1. Request token
        auth_req_data = {
            "pluginName": self.plugin_name,
            "pluginDeveloper": self.plugin_developer
        }
        res = await self._send_request("AuthenticationTokenRequest", auth_req_data)
        self.auth_token = res.get("data", {}).get("authenticationToken")
        
        if self.auth_token:
            # 2. Authenticate with token
            auth_data = {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "authenticationToken": self.auth_token
            }
            auth_res = await self._send_request("AuthenticationRequest", auth_data)
            if auth_res.get("data", {}).get("authenticated"):
                self.logger.info("✅ Authenticated with VTube Studio.")
            else:
                self.logger.warning("VTube Studio authentication failed or denied.")

    async def _inject_parameter(self, param_id: str, value: float):
        """Inject a custom parameter value mapping to an emotion/lipsync into VTS."""
        data = {
            "faceFound": False,
            "mode": "set",
            "parameterValues": [
                {
                    "id": param_id,
                    "value": value,
                    "weight": 1.0
                }
            ]
        }
        await self._send_request("InjectParameterDataRequest", data)

    async def trigger_hotkey(self, hotkey_id: str):
        """Trigger a pre-configured hotkey in VTube Studio (e.g., animation or expression)."""
        data = {"hotkeyID": hotkey_id}
        if self.is_connected:
            await self._send_request("HotkeyTriggerRequest", data)

    async def sync_emotions(self, emotions: Dict[str, float]):
        """Map agent internal emotional state to VTS standard parameters."""
        if not self.is_connected:
            return

        happiness = emotions.get("happiness", 0.5)
        frustration = emotions.get("frustration", 0.0)
        energy = emotions.get("energy", 1.0)

        tasks = []
        smile_val = max(0.0, min(1.0, happiness * 1.5 - frustration))
        tasks.append(self._inject_parameter("ParamMouthSmile", smile_val))

        angry_val = max(0.0, min(1.0, frustration))
        tasks.append(self._inject_parameter("ParamAngry", angry_val))
        
        eye_open = max(0.1, min(1.0, energy))
        tasks.append(self._inject_parameter("ParamEyeLOpen", eye_open))
        tasks.append(self._inject_parameter("ParamEyeROpen", eye_open))
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def set_lipsync(self, value: float):
        """Called directly by TTS engine to map audio amplitude to mouth open."""
        if self.is_connected:
            await self._inject_parameter("ParamMouthOpenY", value)
