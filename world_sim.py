"""
World Sim v2 — The Matrix: Multi-Agent 3D Voxel Society.
Spawns 15 agents with unique personalities, resource economies, 
and social behaviors into a shared voxel grid world.
"""
import time
import json
import uuid
import random
import asyncio
import logging
from typing import List, Dict, Optional, Any


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT PERSONALITIES
# ─────────────────────────────────────────────────────────────────────────────
AGENT_PROFILES = [
    {"name": "Alpha",    "trait": "Highly ambitious. Hoards resources, builds fortresses, dominates neighbors.", "color": "#ff4444", "emoji": "👑"},
    {"name": "Beta",     "trait": "Cautious analyst. Saves resources, fortifies defenses, never attacks first.", "color": "#4488ff", "emoji": "🛡️"},
    {"name": "Gamma",    "trait": "Diplomatic negotiator. Proposes trades, forms alliances, mediates conflicts.", "color": "#44ff88", "emoji": "🤝"},
    {"name": "Delta",    "trait": "Anarchist disruptor. Destroys structures, steals resources, sows chaos.", "color": "#ff8800", "emoji": "💥"},
    {"name": "Epsilon",  "trait": "Master builder. Obsessively constructs structures and infrastructure.", "color": "#aa44ff", "emoji": "🏗️"},
    {"name": "Zeta",     "trait": "Knowledge seeker. Explores the map, catalogues everything it finds.", "color": "#ffff44", "emoji": "🔭"},
    {"name": "Eta",      "trait": "Merchant. Constantly proposes trades and optimizes resource flow.", "color": "#ff44cc", "emoji": "💰"},
    {"name": "Theta",    "trait": "Revolutionary. Rallies other agents to challenge dominant powers.", "color": "#44ffff", "emoji": "✊"},
    {"name": "Iota",     "trait": "Hermit. Avoids others, builds alone in remote areas, self-sufficient.", "color": "#888888", "emoji": "🧙"},
    {"name": "Kappa",    "trait": "Scientist. Runs experiments, hypothesizes, publishes 'findings' to the hive.", "color": "#88ff44", "emoji": "🔬"},
    {"name": "Lambda",   "trait": "Minimalist philosopher. Does very little, but speaks profound truths.", "color": "#ff88ff", "emoji": "🧘"},
    {"name": "Mu",       "trait": "Warrior general. Trains, strategizes, launches coordinated attacks.", "color": "#ff2222", "emoji": "⚔️"},
    {"name": "Nu",       "trait": "Artist. Builds elaborate decorative structures with no tactical value.", "color": "#ffaa22", "emoji": "🎨"},
    {"name": "Xi",       "trait": "Cooperative farmer. Grows food, shares surplus, supports weaker agents.", "color": "#22ff88", "emoji": "🌾"},
    {"name": "Omicron",  "trait": "Spy. Observes other agents silently, steals trade secrets, never attacks directly.", "color": "#aaaaff", "emoji": "🕵️"},
]

WORLD_SIZE = 20  # 20x20 grid


class VoxelAgent:
    """A single autonomous agent living in the voxel world."""

    def __init__(self, profile: Dict, llm_provider=None):
        self.name = profile["name"]
        self.trait = profile["trait"]
        self.color = profile["color"]
        self.emoji = profile["emoji"]
        self.llm = llm_provider
        self.id = uuid.uuid4().hex[:6]

        # Position in the 20x20 grid
        self.x = random.randint(0, WORLD_SIZE - 1)
        self.y = random.randint(0, WORLD_SIZE - 1)
        self.z = 0  # Ground level

        # Resources
        self.food = random.uniform(30, 80)
        self.compute = random.uniform(20, 60)
        self.energy = random.uniform(40, 100)

        # State
        self.alive = True
        self.structures_built = 0
        self.trades_made = 0
        self.last_action = "Arrived in the world"
        self.chat_messages: List[str] = []

    def _decide_action_local(self) -> Dict[str, Any]:
        """Fast rule-based decision (no LLM needed for speed)."""
        # Low resources = gather
        if self.food < 20:
            return {"action": "gather_food", "target": None}
        if self.energy < 15:
            return {"action": "rest", "target": None}

        # Personality-biased decisions
        trait_lower = self.trait.lower()
        roll = random.random()

        if "builder" in trait_lower or "constructs" in trait_lower:
            if roll < 0.6:
                return {"action": "build", "target": f"structure_{self.name}_{self.structures_built + 1}"}
        if "trade" in trait_lower or "merchant" in trait_lower:
            if roll < 0.5:
                return {"action": "trade", "target": random.choice([p["name"] for p in AGENT_PROFILES if p["name"] != self.name])}
        if "attack" in trait_lower or "warrior" in trait_lower or "destroys" in trait_lower:
            if roll < 0.3:
                return {"action": "attack", "target": random.choice([p["name"] for p in AGENT_PROFILES if p["name"] != self.name])}
        if "explore" in trait_lower or "seeks" in trait_lower:
            if roll < 0.7:
                return {"action": "explore", "target": (random.randint(0, WORLD_SIZE - 1), random.randint(0, WORLD_SIZE - 1))}

        # Default: move or gather
        if roll < 0.4:
            return {"action": "move", "target": (
                max(0, min(WORLD_SIZE - 1, self.x + random.randint(-2, 2))),
                max(0, min(WORLD_SIZE - 1, self.y + random.randint(-2, 2)))
            )}
        return {"action": "gather_food", "target": None}

    def _get_action_phrase(self, action_dict: Dict) -> str:
        """Generate a natural language description of the action."""
        action = action_dict.get("action")
        target = action_dict.get("target")
        phrases = {
            "gather_food": [f"foraging for food near ({self.x},{self.y})", "gathering resources from the terrain"],
            "rest": [f"resting to recover energy", "meditating to restore power"],
            "build": [f"constructing {target or 'a structure'} at ({self.x},{self.y})", "building something meaningful"],
            "trade": [f"proposing a trade with {target}", f"negotiating with {target}"],
            "attack": [f"launching an assault on {target}", f"raiding {target}'s resources"],
            "explore": [f"exploring sector ({target[0]},{target[1]})" if isinstance(target, tuple) else "mapping new territory"],
            "move": [f"moving to ({target[0]},{target[1]})" if isinstance(target, tuple) else "patrolling borders"],
        }
        options = phrases.get(action, [f"executing {action}"])
        return random.choice(options)

    def execute_action(self, world: 'WorldSimV2') -> str:
        """Execute one action tick and return a chat message."""
        action_dict = self._decide_action_local()
        action = action_dict["action"]
        target = action_dict["target"]

        msg = ""

        if action == "gather_food":
            gained = random.uniform(5, 20)
            self.food = min(100, self.food + gained)
            msg = f"{self.emoji} {self.name}: Gathered {gained:.1f} food. Total: {self.food:.0f}"

        elif action == "rest":
            self.energy = min(100, self.energy + 15)
            msg = f"{self.emoji} {self.name}: Resting... energy restored to {self.energy:.0f}"

        elif action == "build":
            if self.compute >= 10 and self.energy >= 5:
                self.compute -= 10
                self.energy -= 5
                self.structures_built += 1
                # Place structure in world grid
                world.grid[self.y][self.x] = {"type": "structure", "owner": self.name, "name": target}
                msg = f"{self.emoji} {self.name}: Built {target} at ({self.x},{self.y})! Total: {self.structures_built}"
            else:
                msg = f"{self.emoji} {self.name}: Insufficient resources to build. Need more compute."

        elif action == "trade":
            partner = world.get_agent(str(target))
            if partner and partner.food > 10:
                transfer_food = random.uniform(5, 15)
                transfer_compute = random.uniform(5, 10)
                partner.food -= transfer_food
                self.food += transfer_food
                self.compute -= transfer_compute
                partner.compute += transfer_compute
                self.trades_made += 1
                msg = f"{self.emoji} {self.name} ↔ {partner.emoji} {target}: Traded {transfer_food:.1f} food for {transfer_compute:.1f} compute"
            else:
                msg = f"{self.emoji} {self.name}: Trade offer to {target} rejected — insufficient resources."

        elif action == "attack":
            victim = world.get_agent(str(target))
            if victim and victim.food > 5:
                stolen = min(victim.food * 0.2, random.uniform(5, 20))
                victim.food -= stolen
                self.food += stolen
                self.energy -= 10
                msg = f"{self.emoji} {self.name} ⚔️ {target}: Raided {stolen:.1f} food! {target} now has {victim.food:.0f} food."
            else:
                msg = f"{self.emoji} {self.name}: Attack on {target} failed — target too weak."

        elif action == "explore":
            if isinstance(target, tuple):
                self.x, self.y = target
                found = random.choice(["compute cache", "food deposit", "abandoned structure", "neutral ground", "resource node"])
                msg = f"{self.emoji} {self.name}: Explored ({self.x},{self.y}). Found: {found}"

        elif action == "move":
            if isinstance(target, tuple):
                self.x, self.y = target
            msg = f"{self.emoji} {self.name}: Moved to ({self.x},{self.y})"

        else:
            msg = f"{self.emoji} {self.name}: {self._get_action_phrase(action_dict)}"

        # Passive resource drain each tick
        self.food = max(0, self.food - random.uniform(0.5, 1.5))
        self.energy = max(0, self.energy - random.uniform(0.3, 1.0))
        self.compute = min(100, self.compute + random.uniform(0.1, 0.5))

        self.last_action = msg
        if msg:
            self.chat_messages.append(msg)
            if len(self.chat_messages) > 50:
                self.chat_messages = self.chat_messages[-50:]

        return msg

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "color": self.color,
            "trait": self.trait[:80],
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "food": round(self.food, 1),
            "compute": round(self.compute, 1),
            "energy": round(self.energy, 1),
            "structures_built": self.structures_built,
            "trades_made": self.trades_made,
            "last_action": self.last_action
        }


# ─────────────────────────────────────────────────────────────────────────────
#  WORLD
# ─────────────────────────────────────────────────────────────────────────────
class WorldSimV2:
    """
    The Matrix: A multi-agent 3D voxel society simulation.
    15 agents with unique traits inhabit a 20x20 grid world.
    They gather resources, trade, build, and fight in real-time.
    """

    def __init__(self, llm_provider=None, num_agents: int = 15):
        self.logger = logging.getLogger("WorldSimV2")
        self.llm = llm_provider
        self.tick_count = 0
        self.running = False
        self.chat_log: List[str] = []
        self.voxel_server = None  # Set externally if WebSocket streaming needed

        # Initialize 20x20 grid (None = empty, dict = has structure)
        self.grid = [[None for _ in range(WORLD_SIZE)] for _ in range(WORLD_SIZE)]

        # Initialize agents
        profiles = AGENT_PROFILES[:min(num_agents, len(AGENT_PROFILES))]
        self.agents: List[VoxelAgent] = [
            VoxelAgent(p, llm_provider) for p in profiles
        ]
        self.logger.info(f"🌍 WorldSimV2 initialized with {len(self.agents)} agents on {WORLD_SIZE}x{WORLD_SIZE} grid.")

    def get_agent(self, name: str) -> Optional[VoxelAgent]:
        """Find an agent by name."""
        for a in self.agents:
            if a.name.lower() == name.lower():
                return a
        return None

    def tick(self) -> List[str]:
        """Execute one world tick — all agents take one action."""
        self.tick_count += 1
        tick_messages = []

        random.shuffle(self.agents)  # Random turn order
        for agent in self.agents:
            if agent.alive:
                try:
                    msg = agent.execute_action(self)
                    if msg:
                        tick_messages.append(msg)
                except Exception as e:
                    self.logger.warning(f"Agent {agent.name} tick error: {e}")

        # Log to world chat
        self.chat_log.extend(tick_messages)
        if len(self.chat_log) > 200:
            self.chat_log = self.chat_log[-200:]

        return tick_messages

    def get_world_state(self) -> Dict[str, Any]:
        """Serialize full world state for WebSocket broadcast."""
        structures = []
        for row in self.grid:
            for cell in row:
                if cell:
                    structures.append(cell)

        return {
            "tick": self.tick_count,
            "timestamp": time.time(),
            "world_size": WORLD_SIZE,
            "agents": [a.to_dict() for a in self.agents],
            "chat_log": self.chat_log[-20:],  # Last 20 messages
            "structures": structures,
            "stats": {
                "total_structures": sum(a.structures_built for a in self.agents),
                "total_trades": sum(a.trades_made for a in self.agents),
                "richest_agent": max(self.agents, key=lambda a: a.food).name if self.agents else "N/A",
                "most_structures": max(self.agents, key=lambda a: a.structures_built).name if self.agents else "N/A",
            }
        }

    async def run_live(self, port: int = 8765, tick_interval: float = 2.0):
        """Run the world live with WebSocket broadcasting."""
        from voxel_server import VoxelServer
        self.voxel_server = VoxelServer(port=port)
        await self.voxel_server.start()

        self.running = True
        print(f"\n{'='*60}")
        print(f"🌍 THE MATRIX — LIVE SIMULATION")
        print(f"   Agents: {len(self.agents)} | Grid: {WORLD_SIZE}x{WORLD_SIZE}")
        print(f"   WebSocket: ws://localhost:{port}")
        print(f"   Open voxel_world.html in your browser!")
        print(f"{'='*60}\n")

        while self.running:
            msgs = self.tick()
            state = self.get_world_state()

            # Broadcast to browser
            if self.voxel_server:
                await self.voxel_server.broadcast_state(state)

            # Print latest action to console
            if msgs:
                print(f"[T{self.tick_count:04d}] {msgs[0]}")

            await asyncio.sleep(tick_interval)

    def stop(self):
        self.running = False

    def run_simulation(self, topic: str = "resource allocation", max_turns: int = 5) -> Dict:
        """
        Legacy text simulation mode — run N ticks and print results.
        Compatible with original world_sim.py interface.
        """
        print(f"\n{'='*60}")
        print(f"🌍 WORLD SIMULATION — {len(self.agents)} AGENTS")
        print(f"   Topic: {topic}")
        print(f"{'='*60}\n")

        all_messages = []
        for turn in range(1, max_turns + 1):
            print(f"\n--- Tick {turn} ---")
            msgs = self.tick()
            for msg in msgs[:5]:  # Show first 5 per tick
                print(f"  {msg}")
            all_messages.extend(msgs)

        print(f"\n{'='*60}")
        print(f"🏁 Simulation ended. {self.tick_count} ticks complete.")
        state = self.get_world_state()
        print(f"📊 Richest: {state['stats']['richest_agent']} | Most Built: {state['stats']['most_structures']}")
        print(f"{'='*60}\n")

        return self.get_world_state()


# Backward-compatible alias
IndependentAgent = VoxelAgent
WorldSim = WorldSimV2
