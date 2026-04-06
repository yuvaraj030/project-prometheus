"""
Smart Home Control (Phase 16 — World Interface)
================================================
Home Assistant REST API integration.
Agent can discover, read, and control home devices autonomously.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SmartHomeController:
    """
    Smart Home Controller — wraps Home Assistant REST API for device discovery
    and autonomous control (lights, thermostat, media, etc.).
    """

    def __init__(self, llm_provider: Any, database: Any = None,
                 ha_url: str = None, ha_token: str = None):
        self.llm = llm_provider
        self.db = database
        self.ha_url = (ha_url or "http://homeassistant.local:8123").rstrip("/")
        self.ha_token = ha_token
        self.action_log: List[Dict] = []
        self._entities_cache: List[Dict] = []

        if ha_token:
            print(f"[SmartHome] Connected to Home Assistant at {self.ha_url}")
        else:
            print("[SmartHome] Running in SIMULATION mode (no HA_TOKEN configured).")

    @property
    def _headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Device Discovery
    # ------------------------------------------------------------------
    async def list_entities(self, domain: Optional[str] = None) -> List[Dict]:
        """List all Home Assistant entities (or filter by domain)."""
        if not REQUESTS_AVAILABLE or not self.ha_token:
            # Return simulated devices
            return self._simulated_entities(domain)

        try:
            url = f"{self.ha_url}/api/states"
            resp = await asyncio.to_thread(requests.get, url, headers=self._headers, timeout=10)
            entities = resp.json()
            self._entities_cache = entities
            if domain:
                entities = [e for e in entities if e.get("entity_id", "").startswith(domain)]
            return entities
        except Exception as e:
            print(f"[SmartHome] List entities error: {e}")
            return self._simulated_entities(domain)

    def _simulated_entities(self, domain: Optional[str] = None) -> List[Dict]:
        """Return simulated entities for demo/testing."""
        entities = [
            {"entity_id": "light.living_room", "state": "on", "attributes": {"brightness": 128, "friendly_name": "Living Room Light"}},
            {"entity_id": "light.bedroom", "state": "off", "attributes": {"brightness": 0, "friendly_name": "Bedroom Light"}},
            {"entity_id": "climate.thermostat", "state": "heat", "attributes": {"temperature": 72, "friendly_name": "Thermostat"}},
            {"entity_id": "switch.coffee_maker", "state": "off", "attributes": {"friendly_name": "Coffee Maker"}},
            {"entity_id": "media_player.tv", "state": "idle", "attributes": {"friendly_name": "Living Room TV"}},
            {"entity_id": "sensor.outdoor_temperature", "state": "65", "attributes": {"unit_of_measurement": "°F", "friendly_name": "Outdoor Temp"}},
            {"entity_id": "lock.front_door", "state": "unlocked", "attributes": {"friendly_name": "Front Door Lock"}},
            {"entity_id": "cover.garage_door", "state": "closed", "attributes": {"friendly_name": "Garage Door"}},
        ]
        if domain:
            entities = [e for e in entities if e["entity_id"].startswith(domain)]
        return entities

    async def get_state(self, entity_id: str) -> Optional[Dict]:
        """Get the current state of a specific entity."""
        if not REQUESTS_AVAILABLE or not self.ha_token:
            # Simulated
            for e in self._simulated_entities():
                if e["entity_id"] == entity_id:
                    return e
            return None
        try:
            url = f"{self.ha_url}/api/states/{entity_id}"
            resp = await asyncio.to_thread(requests.get, url, headers=self._headers, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Device Control
    # ------------------------------------------------------------------
    async def control(self, entity_id: str, state: str,
                      service_data: Optional[Dict] = None,
                      tenant_id: int = 1) -> Dict:
        """
        Control a Home Assistant entity.
        state: 'on', 'off', 'toggle', or domain-specific (e.g. 'set_temperature').
        """
        domain = entity_id.split(".")[0]
        service_map = {
            "light": {"on": "turn_on", "off": "turn_off", "toggle": "toggle"},
            "switch": {"on": "turn_on", "off": "turn_off", "toggle": "toggle"},
            "cover": {"on": "open_cover", "off": "close_cover", "open": "open_cover", "close": "close_cover"},
            "lock": {"on": "unlock", "off": "lock", "lock": "lock", "unlock": "unlock"},
            "media_player": {"on": "turn_on", "off": "turn_off", "play": "media_play", "pause": "media_pause"},
            "climate": {"on": "turn_on", "off": "turn_off"},
        }
        service = domain + "." + service_map.get(domain, {}).get(state, state)

        record = {
            "entity_id": entity_id,
            "action": state,
            "service": service,
            "data": service_data or {},
            "timestamp": datetime.now().isoformat(),
        }

        if not REQUESTS_AVAILABLE or not self.ha_token:
            print(f"  🏠 [SIMULATED] {service}({entity_id}) → {state}")
            record["result"] = "simulated"
            self.action_log.append(record)
            return {"success": True, "simulated": True, **record}

        try:
            url = f"{self.ha_url}/api/services/{service.replace('.', '/', 1)}"
            payload = {"entity_id": entity_id, **(service_data or {})}
            resp = await asyncio.to_thread(requests.post, url, headers=self._headers,
                                            json=payload, timeout=10)
            record["result"] = "success" if resp.ok else f"error_{resp.status_code}"
            self.action_log.append(record)
            if self.db:
                self.db.audit(tenant_id, "smart_home", f"{service}: {entity_id} → {state}")
            return {"success": resp.ok, **record}
        except Exception as e:
            record["result"] = f"exception: {e}"
            self.action_log.append(record)
            return {"success": False, "error": str(e), **record}

    # ------------------------------------------------------------------
    # AI-Driven Control
    # ------------------------------------------------------------------
    async def ai_control(self, natural_language_command: str, tenant_id: int = 1) -> Dict:
        """
        Let the LLM interpret a natural language command and control devices.
        E.g., 'Turn on the bedroom light and lower the thermostat to 68°F'
        """
        entities = await self.list_entities()
        entity_list = "\n".join([
            f"- {e['entity_id']} (state: {e.get('state', '?')}, name: {e.get('attributes', {}).get('friendly_name', '')})"
            for e in entities[:20]
        ])
        parse_prompt = (
            f"Available smart home entities:\n{entity_list}\n\n"
            f"User command: '{natural_language_command}'\n\n"
            "Return a JSON array of actions: "
            '[{"entity_id": ..., "state": "on"|"off"|"toggle"|...}]'
            "\nOutput valid JSON only."
        )
        raw = await asyncio.to_thread(self.llm.call, parse_prompt, system=(
            "You are a smart home control AI. Parse commands and return JSON action arrays."
        ), history=[])

        try:
            import re
            match = re.search(r'\[.*\]', raw or "", re.DOTALL)
            actions = json.loads(match.group()) if match else []
        except Exception:
            actions = []

        results = []
        for action in actions:
            entity_id = action.get("entity_id", "")
            state = action.get("state", "on")
            r = await self.control(entity_id, state, tenant_id=tenant_id)
            results.append(r)

        return {
            "command": natural_language_command,
            "actions_taken": len(results),
            "results": results,
        }

    def get_status(self) -> Dict:
        return {
            "ha_url": self.ha_url,
            "connected": bool(self.ha_token and REQUESTS_AVAILABLE),
            "mode": "LIVE" if (self.ha_token and REQUESTS_AVAILABLE) else "SIMULATION",
            "actions_taken": len(self.action_log),
            "recent": self.action_log[-3:],
        }

    def describe(self) -> str:
        mode = "LIVE" if self.ha_token else "SIMULATION"
        return f"SmartHomeController — {mode} mode. {len(self.action_log)} actions taken."
