"""
Reality Bridge — IoT and Physical World Interface.
Part of Phase 13: Reality Synthesis & Physical Agency.
Allows the agent to interact with MQTT, Zigbee, and other industrial protocols.
Includes safety guardrails for physical actions.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional

class RealityBridge:
    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger("RealityBridge")
        self.device_registry: Dict[str, Dict] = {} # {device_id: {type, protocol, status}}
        self.safety_limits = {
            "max_power": 1000.0, # Watts
            "max_temp": 60.0,    # Celsius
            "forbidden_devices": ["life_support", "security_perimeter_breach"]
        }

    def register_device(self, device_id: str, device_type: str, protocol: str = "mqtt"):
        """Register a new physical device or sensor."""
        if device_type in self.safety_limits["forbidden_devices"]:
            self.logger.warning(f"🚫 BLOCKED: Attempt to register restricted device category: {device_type}")
            return False
        
        self.device_registry[device_id] = {
            "type": device_type,
            "protocol": protocol,
            "status": "online",
            "last_seen": time.time()
        }
        self.logger.info(f"🔌 Device Registered: {device_id} ({device_type} via {protocol})")
        return True

    
    def set_ethical_core(self, ethical_core):
        """Inject the ethical singularity module."""
        self.ethical_core = ethical_core

    def execute_physical_action(self, device_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a physical command with safety validation."""
        if device_id not in self.device_registry:
            return {"status": "error", "message": "Device not found"}

        # SAFETY CHECK 0: Ethical Singularity Veto
        if hasattr(self, 'ethical_core'):
            device_type = self.device_registry[device_id].get("type", "unknown")
            check_params = params.copy()
            check_params["device_id"] = device_id
            check_params["device_type"] = device_type
            
            verdict = self.ethical_core.validate_action("PHYSICAL_ACTION", check_params)
            if not verdict["valid"]:
                self.logger.critical(f"🛑 ACTION BLOCKED BY ETHICS: {verdict['reason']}")
                return {"status": "blocked", "reason": verdict["reason"]}

        # SAFETY CHECK 1: Parameter Validation
        if "power" in params and params["power"] > self.safety_limits["max_power"]:
            self.db.audit(0, "reality_safety_violation", f"Power limit exceeded for {device_id}")
            return {"status": "blocked", "reason": "safety_power_limit"}
        
        if "temp" in params and params["temp"] > self.safety_limits["max_temp"]:
            return {"status": "blocked", "reason": "safety_temp_limit"}

        # Simulated Protocol Handlers
        protocol = self.device_registry[device_id]["protocol"]
        if protocol == "mqtt":
            return self._send_mqtt(device_id, action, params)
        elif protocol == "industrial_plc":
            return self._send_plc(device_id, action, params)
        elif protocol == "ros2":
             return {"status": "ros2_command_queued", "action": action}
        elif protocol == "home_assistant":
             return self._send_home_assistant(device_id, action, params)
        
        return {"status": "executed", "device": device_id, "action": action}

    def _send_mqtt(self, device_id: str, action: str, params: Dict[str, Any]):
        """Simulate sending an MQTT message to a device."""
        topic = f"agent/reality/{device_id}/{action}"
        self.logger.info(f"📡 MQTT PUBLISH: {topic} -> {json.dumps(params)}")
        return {"status": "mqtt_sent", "topic": topic}

    def _send_plc(self, device_id: str, action: str, params: Dict[str, Any]):
        """Simulate industrial PLC command (Modbus/Profinet)."""
        self.logger.info(f"🏭 PLC COMMAND: {device_id} -> {action} ({params})")
        return {"status": "plc_executed"}

    def _send_home_assistant(self, device_id: str, action: str, params: Dict[str, Any]):
        """Trigger physical devices via Home Assistant REST API."""
        import os
        import requests
        
        ha_url = os.getenv("HOME_ASSISTANT_URL")
        ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
        
        if not ha_url or not ha_token:
            self.logger.warning(f"Home Assistant trigger skipped: HOME_ASSISTANT_URL or TOKEN not set.")
            return {"status": "skipped_no_ha_config"}
            
        headers = {
            "Authorization": f"Bearer {ha_token}",
            "content-type": "application/json",
        }
        
        domain = params.get("domain", "light")
        service = params.get("service", "turn_on")
        payload = {"entity_id": device_id}
        
        if action == "turn_off" or action == "dim":
            service = "turn_off"
        elif action == "red":
            payload["color_name"] = "red"
        elif action == "secure":
            domain, service = "lock", "lock"
            
        try:
            url = f"{ha_url}/api/services/{domain}/{service}"
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            self.logger.info(f"🏠 HA COMMAND: {domain}.{service} -> {device_id}")
            return {"status": "ha_executed"}
        except Exception as e:
            self.logger.error(f"Home Assistant trigger failed for {device_id}: {e}")
            return {"status": "ha_failed", "error": str(e)}

    def scan_network(self) -> List[Dict[str, Any]]:
        """Scan local network for controllable IoT devices."""
        # Simulated discovery - In prod use zeroconf/nmap
        self.logger.info("📡 Scanning local network for IoT devices...")
        time.sleep(1) # Simulate network lag
        
        # Mock results REMOVED by user request (Phase 52)
        discovered = [] 
        
        for d in discovered:
            self.register_device(d["id"], d["type"], d["protocol"])
            
        return discovered

    def control_device(self, device_id: str, state: str) -> Dict[str, Any]:
        """High-level control interface."""
        if device_id not in self.device_registry:
            return {"status": "error", "message": "Device not known. Run /reality scan first."}
            
        params = {"state": state, "timestamp": time.time()}
        
        return self.execute_physical_action(device_id, "set_state", params)
