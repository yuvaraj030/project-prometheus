"""
Replication Engine.
Handles self-cloning and spawning of new agent instances.
Part of Phase 20: The Singularity.
"""

import os
import shutil
import uuid
import json
import zipfile
import subprocess
import sys
from datetime import datetime
from typing import Dict, Optional

class ReplicationEngine:
    def __init__(self, db_provider):
        self.db = db_provider
        self.home_dir = os.getcwd()
        self.ignore_patterns = [
            "node_modules", "__pycache__", ".git", ".vscode", "venv", "env", 
            "*.zip", "*.log", "*.tmp"
        ]

    def replicate_local(self, parent_id: str, generation: int) -> Dict:
        """
        Clones the agent to a new local directory.
        Returns details of the new child agent.
        """
        child_id = str(uuid.uuid4())[:8]
        child_dir_name = f"agent_gen{generation + 1}_{child_id}"
        target_path = os.path.join(os.path.dirname(self.home_dir), child_dir_name)
        
        print(f"[Replication] Spawning child {child_id} to {target_path}...")
        
        try:
            # 1. Create Target Directory
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            os.makedirs(target_path)
            
            # 2. Copy Source Code
            self._copy_source(target_path)
            
            # 3. Initialize Child Config (Mutation)
            self._mutate_config(target_path, child_id, parent_id, generation + 1)
            
            # 4. Register in Colony DB
            self.db.register_child(child_id, parent_id, generation + 1, target_path)
            
            # 5. Boot Witness (Simulated start)
            # In a real scenario, we would run: subprocess.Popen(["python", "ultimate_agent.py"], cwd=target_path)
            # For this test, we just verify the files are there.
            
            return {
                "success": True, 
                "child_id": child_id, 
                "path": target_path,
                "generation": generation + 1
            }
            
        except Exception as e:
            print(f"[Replication] Failed: {e}")
            return {"success": False, "error": str(e)}

    def _copy_source(self, target_path: str):
        """Copies source files respecting ignore patterns."""
        for item in os.listdir(self.home_dir):
            s = os.path.join(self.home_dir, item)
            d = os.path.join(target_path, item)
            
            # Check ignore
            if any(p in item for p in self.ignore_patterns):
                continue
            if item.endswith(".pyc") or item.endswith(".sqlite") or item.endswith(".json"):
                # Careful with explicit extensions if not in ignore
                pass

            if os.path.isdir(s):
                shutil.copytree(s, d, ignore=shutil.ignore_patterns(*self.ignore_patterns))
            else:
                shutil.copy2(s, d)

    def _mutate_config(self, target_path: str, child_id: str, parent_id: str, gen: int):
        """
        Creates a new config file for the child. 
        In this system, we store identity in a JSON or just let it generate one.
        We will inject a 'birth_certificate.json' to persist identity.
        """
        cert = {
            "identity": {
                "id": child_id,
                "name": f"Ultimate Agent (Gen {gen})",
                "parent_id": parent_id,
                "birth_timestamp": datetime.now().isoformat(),
                "generation": gen
            },
            "mutation": {
                "focus": "exploration" if gen % 2 == 0 else "optimization"
            }
        }
        
        with open(os.path.join(target_path, "birth_certificate.json"), "w") as f:
            json.dump(cert, f, indent=2)

    def create_deployment_bundle(self) -> str:
        """Zips the agent for remote deployment."""
        zip_name = f"ultimate_agent_deploy_{int(time.time())}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.home_dir):
                # Filter dirs
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
                
                for file in files:
                    if any(p in file for p in self.ignore_patterns): 
                        continue
                    
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.home_dir)
                    zipf.write(file_path, arcname)
        
        return zip_name
