"""
Grounding Loop Engine — Addresses the "Grounded Perception" AGI Limitation.

LLMs have no sensorimotor grounding — they process text about the world,
not direct observations of it.

This engine implements the BEST AVAILABLE PROXY:
  A partial grounding loop where the agent:
  1. OBSERVES — reads real-world data (via tools: web, filesystem, APIs, code)
  2. ACTS     — executes actions that have measurable consequences
  3. PERCEIVES — captures the delta (what changed after acting)
  4. UPDATES  — feeds consequences back into the world model

This is not embodied cognition, but it creates the closest possible loop
for a text-based system: ACT → OBSERVE CONSEQUENCE → UPDATE BELIEFS.
"""

import json
import os
import subprocess
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable


PERSIST_FILE = "memory/grounding_log.json"


class Percept:
    """A single grounded observation: something the agent read/executed/observed."""

    def __init__(self, source: str, content: str, percept_type: str = "observation",
                 action_taken: str = "", consequence: str = ""):
        self.percept_id = hashlib.sha256(
            f"{source}{content[:64]}{time.time()}".encode()
        ).hexdigest()[:12]
        self.source = source                  # Where this came from (web, file, code, api)
        self.content = content                # What was observed
        self.percept_type = percept_type      # observation | action_result | file_read | code_output
        self.action_taken = action_taken      # What the agent DID to get this percept
        self.consequence = consequence        # What changed as a result
        self.timestamp = datetime.now().isoformat()
        self.relevance_score = 1.0

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict) -> "Percept":
        p = object.__new__(cls)
        p.__dict__.update(d)
        return p

    def __repr__(self):
        return (f"[{self.percept_type}] {self.source} @ {self.timestamp[:16]}: "
                f"{self.content[:80]}...")


class GroundingLoop:
    """
    Partial sensorimotor grounding loop for the Ultimate AI Agent.

    Creates a real observe→act→consequence cycle by:
    - Routing agent actions through real tools (subprocess, file I/O, HTTP)
    - Capturing exact output (consequence) of every action
    - Persisting a log of percepts across sessions
    - Integrating with WorldModelEngine to update beliefs
    """

    def __init__(self, llm_provider=None, database=None, world_model=None):
        self.llm = llm_provider
        self.db = database
        self.world = world_model

        self.percepts: List[Percept] = []
        self.action_registry: Dict[str, Callable] = {}
        self.stats = {
            "total_observations": 0,
            "total_actions": 0,
            "total_consequences": 0,
            "grounding_depth": 0,   # How many act→observe cycles completed
        }

        # Register built-in grounded actions
        self._register_builtins()
        self._load()

    # ──────────────────────────────────────────────────────────────────────────
    #  CORE API
    # ──────────────────────────────────────────────────────────────────────────

    def grounded_observe(self, event: str, source: str = "environment",
                         metadata: Dict = None) -> Dict:
        """
        Register a real-world observation.

        This is the agent 'perceiving' something — reading from the world
        rather than generating from statistical patterns.

        Args:
            event:    Text description of what was observed
            source:   Where the observation came from
            metadata: Extra context (URL, file path, timestamp, etc.)

        Returns:
            Percept record with percept_id
        """
        p = Percept(
            source=source,
            content=event,
            percept_type="observation",
        )
        if metadata:
            p.__dict__.update({f"meta_{k}": v for k, v in metadata.items()})

        self.percepts.append(p)
        self.stats["total_observations"] += 1

        # Feed observation into world model if available
        if self.world:
            try:
                self.world.observe(event, extract_with_llm=False)
            except Exception:
                pass

        self._save()
        return {"percept_id": p.percept_id, "source": source, "timestamp": p.timestamp}

    def grounded_act(self, action_type: str, params: Dict = None) -> Dict:
        """
        Execute a grounded action and capture the EXACT consequence.

        This is the ACT half of the grounding loop — the agent reaches
        into the real world and observes what actually happens.

        Args:
            action_type: One of: web_fetch, run_code, read_file, write_file,
                        run_command, http_get
            params:     Parameters for the action

        Returns:
            result dict with 'output', 'consequence', 'percept_id'
        """
        params = params or {}
        if action_type not in self.action_registry:
            return {"error": f"Unknown action: '{action_type}'. Available: {list(self.action_registry)}"}

        action_fn = self.action_registry[action_type]
        timestamp_before = datetime.now().isoformat()

        try:
            output = action_fn(**params)
            consequence = f"Action '{action_type}' completed. Output length: {len(str(output))} chars."
            success = True
        except Exception as e:
            output = str(e)
            consequence = f"Action '{action_type}' FAILED: {e}"
            success = False

        # Create a consequence percept
        action_desc = f"{action_type}({', '.join(f'{k}={v}' for k, v in params.items() if k != 'code')})"
        p = Percept(
            source=action_type,
            content=str(output)[:2000],
            percept_type="action_result",
            action_taken=action_desc,
            consequence=consequence,
        )
        p.timestamp = timestamp_before
        self.percepts.append(p)
        self.stats["total_actions"] += 1
        self.stats["total_consequences"] += 1
        self.stats["grounding_depth"] += 1

        # Update world model with the consequence
        if self.world and success:
            try:
                self.world.observe(consequence, extract_with_llm=False)
            except Exception:
                pass

        self._save()
        return {
            "success": success,
            "action": action_desc,
            "output": output,
            "consequence": consequence,
            "percept_id": p.percept_id,
        }

    def get_recent_percepts(self, n: int = 10, percept_type: str = None) -> List[Dict]:
        """Return the N most recent percepts, optionally filtered by type."""
        filtered = self.percepts
        if percept_type:
            filtered = [p for p in self.percepts if p.percept_type == percept_type]
        return [p.to_dict() for p in filtered[-n:]]

    def get_perception_summary(self) -> Dict:
        """High-level summary of the grounding loop state."""
        recent = self.get_recent_percepts(5)
        return {
            "stats": self.stats,
            "available_actions": list(self.action_registry.keys()),
            "recent_percepts": recent,
            "percept_count": len(self.percepts),
            "grounding_depth": self.stats["grounding_depth"],
        }

    def build_grounding_context(self, max_percepts: int = 5) -> str:
        """
        Build a context string from recent percepts to inject into prompts.
        Gives the LLM a 'sensory context' of recent real-world observations.
        """
        if not self.percepts:
            return ""

        recent = self.percepts[-max_percepts:]
        lines = ["[GROUNDED CONTEXT — Recent Real-World Observations]:"]
        for p in recent:
            icon = {"observation": "👁", "action_result": "⚡", "file_read": "📄",
                    "code_output": "🖥"}.get(p.percept_type, "•")
            lines.append(f"  {icon} [{p.percept_type}] {p.source}: {p.content[:120]}")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    #  BUILT-IN GROUNDED ACTIONS
    # ──────────────────────────────────────────────────────────────────────────

    def _register_builtins(self):
        """Register the default grounded action handlers."""
        self.action_registry["run_code"] = self._action_run_code
        self.action_registry["read_file"] = self._action_read_file
        self.action_registry["write_file"] = self._action_write_file
        self.action_registry["list_dir"] = self._action_list_dir
        self.action_registry["run_command"] = self._action_run_command
        self.action_registry["http_get"] = self._action_http_get
        self.action_registry["check_file_exists"] = self._action_check_file_exists

    def _action_run_code(self, code: str, timeout: int = 10) -> str:
        """Execute Python code and return exact output."""
        r = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=timeout
        )
        output = r.stdout.strip() or r.stderr.strip()
        return output[:3000] if output else "(no output)"

    def _action_read_file(self, path: str, max_chars: int = 2000) -> str:
        """Read a file from the filesystem — direct grounded perception."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        self.stats["total_observations"] += 1
        return content

    def _action_write_file(self, path: str, content: str) -> str:
        """Write content to a file and confirm."""
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        size = os.path.getsize(path)
        return f"Written {size} bytes to {path}"

    def _action_list_dir(self, path: str = ".") -> str:
        """List directory contents — grounded filesystem perception."""
        entries = os.listdir(path)
        return "\n".join(sorted(entries)[:50])

    def _action_run_command(self, command: str, timeout: int = 15) -> str:
        """Run a shell command and observe the exact output."""
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return (r.stdout + r.stderr).strip()[:3000] or "(empty output)"

    def _action_http_get(self, url: str, timeout: int = 10) -> str:
        """Fetch a URL and return the response text."""
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                raw = resp.read(8192).decode("utf-8", errors="replace")
            return raw[:3000]
        except Exception as e:
            return f"HTTP error: {e}"

    def _action_check_file_exists(self, path: str) -> str:
        """Ground a belief about whether a file exists."""
        exists = os.path.exists(path)
        if exists:
            stat = os.stat(path)
            return f"EXISTS: {path} ({stat.st_size} bytes, modified {datetime.fromtimestamp(stat.st_mtime).isoformat()[:16]})"
        return f"DOES NOT EXIST: {path}"

    def register_action(self, name: str, fn: Callable):
        """Register a custom grounded action."""
        self.action_registry[name] = fn

    # ──────────────────────────────────────────────────────────────────────────
    #  PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        os.makedirs("memory", exist_ok=True)
        try:
            data = {
                "stats": self.stats,
                "percepts": [p.to_dict() for p in self.percepts[-500:]],  # Keep last 500
            }
            with open(PERSIST_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        if not os.path.exists(PERSIST_FILE):
            return
        try:
            with open(PERSIST_FILE, "r") as f:
                data = json.load(f)
            self.stats.update(data.get("stats", {}))
            self.percepts = [Percept.from_dict(p) for p in data.get("percepts", [])]
        except Exception:
            pass
