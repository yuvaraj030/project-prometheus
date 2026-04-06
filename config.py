#!/usr/bin/env python3
"""
Centralized Configuration for Ultimate AI Agent
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List

# Fix #15: Auto-load .env file if present (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # Don't override already-set env vars
except ImportError:
    pass  # dotenv is optional; env vars still work from the shell


@dataclass
class OllamaConfig:
    host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434").strip())
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2").strip())
    timeout: int = 120
    max_retries: int = 3


@dataclass
class OpenAIConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip() or None)
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o").strip())
    base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip())
    max_tokens: int = 2000
    temperature: float = 0.7


@dataclass
class AnthropicConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"))
    base_url: str = "https://api.anthropic.com/v1"
    max_tokens: int = 2000


@dataclass
class GeminiConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class GroqConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    base_url: str = "https://api.groq.com/openai/v1"


@dataclass
class VoiceConfig:
    enabled: bool = True
    tts_rate: int = 175
    tts_voice_index: int = 1  # 0=male, 1=female on most systems
    wake_word: str = "hey jarvis"
    listen_timeout: int = 5
    phrase_time_limit: int = 15


@dataclass
class DatabaseConfig:
    sqlite_path: str = os.getenv("AGENT_DB_PATH", "agent_database.db")
    vector_db_path: str = os.getenv("AGENT_VECTOR_DB_PATH", "agent_vector_db")
    vector_collection: str = "agent_memory"
    memory_file: str = "ultimate_agent_memory.json"


@dataclass
class SelfModConfig:
    enabled: bool = True
    safety_mode: bool = True
    backup_dir: str = "agent_backups"
    modules_dir: str = "agent_modules"
    max_backups: int = 50


@dataclass
class SwarmConfig:
    enabled: bool = False
    max_workers: int = 10
    ceo_model: str = "gpt-4o"
    worker_model: str = "llama3.2"


@dataclass
class SecurityConfig:
    rate_limit_rpm: int = 60  # requests per minute
    max_code_exec_timeout: int = 10
    audit_logging: bool = True
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /", "format", "del /s /q", "shutdown", "mkfs"
    ])


@dataclass
class APIServerConfig:
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    api_key: str = os.getenv("AGENT_API_KEY", "change-me-in-production")
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


@dataclass
class AgentConfig:
    """Master configuration — all sub-configs in one place."""
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    groq: GroqConfig = field(default_factory=GroqConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    self_mod: SelfModConfig = field(default_factory=SelfModConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    api_server: APIServerConfig = field(default_factory=APIServerConfig)
    
    # Phase 21: God Mode
    god_mode: bool = field(default=False)
    
    # Phase 20: Anime Persona
    persona: str = field(default="standard") # standard, anime

    # Phase 57/59: Performance Optimization (auto-enabled for local models only)
    lite_mode: bool = field(default_factory=lambda: os.getenv("AGENT_PROVIDER", "ollama").strip() == "ollama")

    # Active provider
    api_provider: str = field(default_factory=lambda: os.getenv("AGENT_PROVIDER", "ollama").strip())

    # Phase 70: Autonomous Daemon Mode
    daemon_mode: bool = field(default_factory=lambda: os.getenv("AGENT_DAEMON_MODE", "false").strip().lower() == "true")
    goal_generation_interval: int = 600   # seconds between goal generation cycles (default 10 min)
    goal_execution_interval: int = 120    # seconds between goal execution cycles (default 2 min)
    goal_review_interval: int = 3600      # seconds between goal review/retire cycles (default 1 hour)

    def get_active_model(self) -> str:
        if self.api_provider == "openai":
            return self.openai.model
        elif self.api_provider == "anthropic":
            return self.anthropic.model
        elif self.api_provider == "gemini":
            return self.gemini.model
        elif self.api_provider == "groq":
            return self.groq.model
        return self.ollama.model

    def get_active_api_key(self) -> Optional[str]:
        if self.api_provider == "openai":
            return self.openai.api_key
        elif self.api_provider == "anthropic":
            return self.anthropic.api_key
        elif self.api_provider == "gemini":
            return self.gemini.api_key
        elif self.api_provider == "groq":
            return self.groq.api_key
        return None


# Global singleton
CONFIG = AgentConfig()
