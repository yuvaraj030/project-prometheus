"""
OAuth Engine — Manages secure OAuth2 flows for external services.
Allows the agent to act on the user's behalf (Gmail, GitHub, etc.).
"""

import os
import json
import webbrowser
from typing import Dict, Any, Optional

class OAuthEngine:
    def __init__(self, db=None):
        self.db = db
        self.credentials_path = "agent_credentials.json"
        self.tokens = self._load_tokens()
        
    def _load_tokens(self) -> Dict[str, Any]:
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path, "r") as f:
                return json.load(f)
        return {}
        
    def _save_tokens(self):
        with open(self.credentials_path, "w") as f:
            json.dump(self.tokens, f, indent=2)
            
    def get_auth_url(self, service: str) -> str:
        """Generate the authorization URL for a service."""
        # Simple simulation/placeholder for real OAuth libraries like google-auth
        if service == "google":
            return "https://accounts.google.com/o/oauth2/auth?client_id=AGENT_CLIENT_ID&..."
        if service == "github":
            return "https://github.com/login/oauth/authorize?client_id=AGENT_CLIENT_ID&..."
        return ""
        
    def register_service(self, service: str, token: str):
        """Manually register a token for a service (for testing/CLI setup)."""
        self.tokens[service] = {"token": token, "status": "active"}
        self._save_tokens()
        return {"success": True, "service": service}
        
    def is_connected(self, service: str) -> bool:
        return service in self.tokens and self.tokens[service].get("status") == "active"
        
    def get_token(self, service: str) -> Optional[str]:
        return self.tokens.get(service, {}).get("token")

    def disconnect(self, service: str):
        if service in self.tokens:
            del self.tokens[service]
            self._save_tokens()
            return True
        return False
