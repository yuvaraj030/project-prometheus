"""
Nexa Language — Workspace Manager v24
nexa workspace <command>
Features:
- init: Create nexa.json workspace config
- add: Add a package/directory to the workspace
- list: List workspace members
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, List, Any


class WorkspaceManager:
    """Manages Nexa workspaces (monorepos) via nexa.json"""
    
    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()
        self.config_path = self.root / "nexa.json"
        
    def _load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {"workspace": {"members": []}}
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ❌ Failed to parse nexa.json: {e}")
            return {"workspace": {"members": []}}
            
    def _save(self, config: Dict[str, Any]):
        self.config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        
    def init(self):
        """Initialize a new workspace."""
        if self.config_path.exists():
            print(f"  ⚠️  Workspace already initialized at {self.config_path}")
            return
            
        config = {
            "name": self.root.name,
            "version": "0.1.0",
            "workspace": {
                "members": []
            }
        }
        self._save(config)
        print(f"  ✅ Initialized Nexa workspace at {self.config_path}")
        print("  Use 'nexa workspace add <dir>' to add packages.")
        
    def add(self, member_path: str):
        """Add a directory to the workspace members."""
        if not self.config_path.exists():
            self.init()
            
        # Make path relative to workspace root if possible
        try:
            rel_path = Path(member_path).resolve().relative_to(self.root)
            member_str = str(rel_path).replace("\\", "/")
        except ValueError:
            # Not a subpath, use as is
            member_str = member_path.replace("\\", "/")
            
        config = self._load()
        members = config.get("workspace", {}).get("members", [])
        
        if member_str in members:
            print(f"  ⚠️  '{member_str}' is already a workspace member.")
            return
            
        if "workspace" not in config:
            config["workspace"] = {}
        if "members" not in config["workspace"]:
            config["workspace"]["members"] = []
            
        config["workspace"]["members"].append(member_str)
        self._save(config)
        print(f"  ✅ Added '{member_str}' to workspace.")
        
    def list(self):
        """List all workspace members."""
        if not self.config_path.exists():
            print("  ❌ Not a Nexa workspace (no nexa.json found).")
            print("  Run 'nexa workspace init' to create one.")
            return
            
        config = self._load()
        members = config.get("workspace", {}).get("members", [])
        
        print(f"\n  📁 Nexa Workspace: {config.get('name', self.root.name)}")
        print(f"  {'─' * 50}")
        if not members:
            print("  (Empty workspace)")
        else:
            for m in members:
                full_path = self.root / m
                status = "✅" if full_path.exists() else "⚠️ (missing)"
                print(f"  {status} {m}")
        print(f"  {'─' * 50}")
        print(f"  Total: {len(members)} member(s)\n")


def handle_workspace_command(args: List[str]):
    wm = WorkspaceManager()
    if not args or args[0] in ("list", "ls"):
        wm.list()
    elif args[0] == "init":
        wm.init()
    elif args[0] == "add" and len(args) > 1:
        wm.add(args[1])
    else:
        print("Usage:")
        print("  nexa workspace init          # Create a nexa.json workspace")
        print("  nexa workspace add <path>    # Add a package to workspace")
        print("  nexa workspace list          # List all workspace members")
