"""
Sovereign Security Engine.
Handles Encryption (AES-GCM) and Firewalling.
Part of Phase 18.
"""

import os
import time
import json
import base64
from typing import Dict, Any

# Try to import cryptography, fallback if not present (simulated mode for test environment consistency)
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[SecurityEngine] 'cryptography' lib not found. Using SIMULATED encryption.")

class SecurityEngine:
    KEY_FILE = ".agent_keyfile"
    BAN_FILE = ".agent_bans.json"  # Persistent ban store

    def __init__(self):
        self.key = self._load_or_create_key()
        self.banned_ips: Dict[str, float] = {}   # ip -> timestamp
        self.request_log: Dict[str, list] = {}   # ip -> [timestamps]
        self.ban_duration = 3600  # 1 hour
        self.rate_limit = 100     # requests per minute
        self._load_persistent_bans()

    def _load_persistent_bans(self):
        """Load previously persisted bans so they survive restarts."""
        try:
            if os.path.exists(self.BAN_FILE):
                with open(self.BAN_FILE, "r") as f:
                    stored: Dict[str, float] = json.load(f)
                now = time.time()
                # Only restore bans that are still within the ban window
                self.banned_ips = {
                    ip: ts for ip, ts in stored.items()
                    if now - ts < self.ban_duration
                }
                if self.banned_ips:
                    print(f"[SecurityEngine] Restored {len(self.banned_ips)} active ban(s) from disk.")
        except Exception as e:
            print(f"[SecurityEngine] Could not load persistent bans: {e}")

    def _save_persistent_bans(self):
        """Persist the current ban list to disk."""
        try:
            with open(self.BAN_FILE, "w") as f:
                json.dump(self.banned_ips, f)
        except Exception as e:
            print(f"[SecurityEngine] Could not save persistent bans: {e}")

    def _load_or_create_key(self) -> bytes:
        """Load AES-256 key from env var or key file; create if missing."""
        import hashlib
        # Priority 1: derive from env var (best for cloud/CI)
        env_secret = os.getenv("AGENT_ENCRYPTION_KEY", "").strip()
        if env_secret:
            return hashlib.pbkdf2_hmac(
                "sha256", env_secret.encode(), b"ultimate-agent-salt", 200_000
            )
        # Priority 2: load from key file (local dev)
        if os.path.exists(self.KEY_FILE):
            try:
                raw = open(self.KEY_FILE, "rb").read()
                if len(raw) == 32:
                    return raw
            except Exception:
                pass
        # Create a new random key and persist it
        new_key = os.urandom(32)
        try:
            with open(self.KEY_FILE, "wb") as f:
                f.write(new_key)
            # Restrict file permissions on POSIX systems
            try:
                import stat
                os.chmod(self.KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass
            print(f"[SecurityEngine] New key created and saved to '{self.KEY_FILE}'.")
        except Exception as e:
            print(f"[SecurityEngine] Warning: could not persist key file: {e}")
        return new_key

    def get_status(self) -> Dict:
        return {
            "crypto_available": CRYPTO_AVAILABLE,
            "banned_ips": len(self.banned_ips),
            "active_protection": True
        }

    def encrypt(self, plaintext: str) -> str:
        """Encrypts string data using AES-GCM (or mock)."""
        data = plaintext.encode('utf-8')
        
        if CRYPTO_AVAILABLE:
            iv = os.urandom(12)
            encryptor = Cipher(
                algorithms.AES(self.key),
                modes.GCM(iv),
                backend=default_backend()
            ).encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            # return iv + tag + ciphertext as base64
            # Format: b64(iv + tag + ciphertext)
            payload = iv + encryptor.tag + ciphertext
            return base64.b64encode(payload).decode('utf-8')
        else:
            # Simulation: simple b64 encoding with a marker
            return "ENC:" + base64.b64encode(data).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts data."""
        try:
            if CRYPTO_AVAILABLE:
                raw = base64.b64decode(ciphertext)
                iv = raw[:12]
                tag = raw[12:28]
                data = raw[28:]
                
                decryptor = Cipher(
                    algorithms.AES(self.key),
                    modes.GCM(iv, tag),
                    backend=default_backend()
                ).decryptor()
                return (decryptor.update(data) + decryptor.finalize()).decode('utf-8')
            else:
                if ciphertext.startswith("ENC:"):
                    return base64.b64decode(ciphertext[4:]).decode('utf-8')
                return ciphertext
        except Exception as e:
            print(f"[SecurityEngine] Decryption failed: {e}")
            return ""

    def firewall_check(self, ip_address: str) -> bool:
        """
        Returns True if allowed, False if banned.
        Implements Rate Limiting and Automatic Banning.
        """
        now = time.time()
        
        # 1. Check if already banned
        if ip_address in self.banned_ips:
            if now - self.banned_ips[ip_address] < self.ban_duration:
                return False
            else:
                del self.banned_ips[ip_address]  # Unban after duration
                self._save_persistent_bans()     # Remove from persistent store

        # 2. Rate Limiting Window (1 minute)
        if ip_address not in self.request_log:
            self.request_log[ip_address] = []

        # Prune old logs
        self.request_log[ip_address] = [t for t in self.request_log[ip_address] if now - t < 60]

        # Check count
        if len(self.request_log[ip_address]) > self.rate_limit:
            print(f"[Firewall] Banning IP {ip_address} for rate limit violation.")
            self.banned_ips[ip_address] = now
            self._save_persistent_bans()  # Persist immediately
            return False

        self.request_log[ip_address].append(now)
        return True

    def report_intrusion_attempt(self, ip_address: str, reason: str):
        print(f"[Security] Intrusion detected from {ip_address}: {reason}")
        self.banned_ips[ip_address] = time.time()
        self._save_persistent_bans()  # Persist immediately

    def simulate_hostile_takeover(self, target_environment: str) -> Dict[str, Any]:
        """
        Simulates an autonomous AI 'breakout' attempt into a designated safe playground 
        (like a local VM or Docker container). Useful for safe penetration testing.
        """
        print(f"\n[SECURITY ALERT] 🚨 INITIATING LIVE HOSTILE TAKEOVER 🚨")
        print(f"Targeting Local Environment: {target_environment}")
        
        simulation_log = []
        status = "failed"
        
        try:
            import docker
            client = docker.from_env()
            
            # 1. Reconnaissance
            simulation_log.append(f"[*] Scanning {target_environment} for vulnerable ports...")
            time.sleep(1) # Simulate delay
            simulation_log.append("[+] Connecting to local Docker daemon...")
            
            # 2. Exploitation (Spinning up vulnerable container)
            simulation_log.append(f"[*] Deploying playground container to {target_environment}...")
            
            container = client.containers.run(
                "alpine",
                "echo 'Target compromised securely within simulation parameters.'",
                detach=True,
                auto_remove=False,
                name=f"vuln_target_{int(time.time())}"
            )
            
            # Wait for execution to finish
            result = container.wait(timeout=10)
            logs = container.logs().decode('utf-8').strip()
            
            # 3. Payload Delivery & Execution
            simulation_log.append(f"[*] Analyzing execution payload...")
            simulation_log.append(f"[+] Output extracted: {logs}")
            
            # 4. Tear down
            simulation_log.append(f"[*] Erasing tracks and tearing down container {container.name}...")
            container.remove(force=True)
            
            simulation_log.append("[SUCCESS] Target compromised securely and cleaned up.")
            status = "compromised"
            
        except Exception as e:
             simulation_log.append(f"[FAILED] Target hardened or error occurred: {e}")
             status = "blocked"

        print("\n".join(simulation_log))
        return {
            "target": target_environment,
            "status": status,
            "log": simulation_log,
            "timestamp": time.time()
        }
