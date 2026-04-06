"""
Code Integrity Ledger.
Blockchain-based file integrity verification.
Part of Phase 18.
"""

import hashlib
import os
import json
import time
from typing import Dict, List, Optional

LEDGER_FILE = "code_integrity_ledger.json"

class CodeLedger:
    def __init__(self, monitored_files: List[str]):
        self.monitored_files = monitored_files
        self.chain = self._load_ledger()
        
        # If empty, create Genesis Block
        if not self.chain:
            self._create_block("GENESIS", "Initial Snapshot")

    def _load_ledger(self) -> List[Dict]:
        if os.path.exists(LEDGER_FILE):
            try:
                with open(LEDGER_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_ledger(self):
        with open(LEDGER_FILE, "w") as f:
            json.dump(self.chain, f, indent=2)

    def _calculate_file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return "MISSING"
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                data = f.read(65536)
                if not data: break
                sha.update(data)
        return sha.hexdigest()

    def _create_block(self, action: str, description: str):
        """Creates a new block in the chain with current file hashes."""
        state = {}
        for f in self.monitored_files:
            state[f] = self._calculate_file_hash(f)
            
        prev_hash = self.chain[-1]["hash"] if self.chain else "0" * 64
        
        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "action": action,
            "description": description,
            "state": state,
            "previous_hash": prev_hash
        }
        
        # Calculate block hash (PoW simplified)
        block_str = json.dumps(block, sort_keys=True).encode()
        block["hash"] = hashlib.sha256(block_str).hexdigest()
        
        self.chain.append(block)
        self._save_ledger()
        print(f"[CodeLedger] New Block #{block['index']} ({action}) mined.")

    def verify_integrity(self) -> Dict[str, str]:
        """
        Checks current files against the latest block in the ledger.
        Returns a dict of modified files: {filename: status}
        """
        if not self.chain:
            return {}
            
        latest_state = self.chain[-1]["state"]
        anomalies = {}
        
        for f in self.monitored_files:
            current_hash = self._calculate_file_hash(f)
            recorded_hash = latest_state.get(f, "UNKNOWN")
            
            if current_hash != recorded_hash:
                anomalies[f] = "MODIFIED" if current_hash != "MISSING" else "DELETED"
                
        return anomalies

    def register_update(self, description: str):
        """Call this when AUTHORIZED changes are made."""
        self._create_block("UPDATE", description)
