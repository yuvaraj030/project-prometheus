#!/usr/bin/env python3
"""
Ultimate Autonomous AI Agent - SOVEREIGN CORE
=====================================================
Text + Voice | Always-on | Local + Cloud LLM | Self-evolving
Computer control | Swarm mode | Hive Mind | Vector memory

Run:  python ultimate_agent.py
      python ultimate_agent.py --provider openai
      python ultimate_agent.py --provider anthropic --api-key YOUR_KEY
"""

import os
import sys

# â”€â”€ Silence TensorFlow/oneDNN warnings before any imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
# Silence Python-level TF deprecation warnings (tf_keras, deepface, etc.)
import logging as _logging
_logging.getLogger("tensorflow").setLevel(_logging.ERROR)
_logging.getLogger("tf_keras").setLevel(_logging.ERROR)
_logging.getLogger("absl").setLevel(_logging.ERROR)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# --- Fix Windows terminal encoding (cp1252 â†’ UTF-8) ---
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import re
import json
import asyncio
import subprocess
import webbrowser
import platform
import inspect
import threading
import uuid
import random
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import deque
import math
import io
import queue
from contextlib import redirect_stdout

# Fix #7: Setup structured logging before anything else
try:
    from logging_config import setup_logging
    setup_logging()
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
import logging
logger = logging.getLogger("UltimateAgent")

try:
    import tkinter as tk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

from database import AgentDatabase
from vector_memory import VectorMemory
from llm_provider import LLMProvider
from self_mod_engine import SelfModEngine
from learning_engine import LearningEngine
from consciousness_engine import ConsciousnessEngine
from reflexive_engine import ReflexiveEngine
from vision_engine import VisionEngine
from swarm_manager import SwarmManager
from mission_control import MissionControl
from config import CONFIG
from knowledge_graph import KnowledgeGraph
from hive_mind import HiveMind
from security_engine import SecurityEngine
from sovereign_modules import (
    BillingSystem, RepairEngine, MarketingEngine, 
    DataCompressor, SystemMonitor
)
from web3_wallet import Web3Wallet
from code_ledger import CodeLedger
from replication_engine import ReplicationEngine
from hyper_evolution import HyperEvolutionEngine
from memory_manager import MemoryManager
from generative_ui import GenerativeUI

# --- OpenClaw-style modules ---
from skill_loader import SkillLoader
from tool_registry import ToolRegistry
from react_engine import ReactEngine
from heartbeat_scheduler import HeartbeatScheduler

# --- Extracted modules ---
from command_handler import CommandHandler
from voice_handler import VoiceHandler
from agent_loops import AgentLoops
from sovereign_hologram import SovereignHologram
from agent_modules.resource_manager import ResourceManager
from agent_modules.oauth_engine import OAuthEngine
from vtuber_bridge import VTuberBridge
from devops_healer import DevOpsHealer

class UltimateAgent:
    """The god-tier autonomous AI agent â€” self-modifying, self-evolving."""

    def __init__(self, provider: str = "ollama", api_key: str = None,
                 model: str = None, wake_word: str = "hey computer",
                 enable_self_mod: bool = True, safety_mode: bool = True,
                 ollama_host: str = "http://localhost:11434",
                 use_hologram: bool = False,
                 auto_mode: bool = False):

        self.session_id = uuid.uuid4().hex[:12]
        self._start_time = time.time()
        self.use_hologram = use_hologram and TK_AVAILABLE
        self.hologram = None
        self._vmem_count_cache = -1  # -1 = uninitialised; 0 is a valid cached count
        self._vmem_count_timestamp = 0
        self.os_type = platform.system()
        self.running = False
        self.status = "IDLE" # IDLE, THINKING, LEARNING, GODMODE
        
        # HEADLESS MODE (Cloud Deployment / Autonomous)
        self.headless = auto_mode or os.getenv("HEADLESS_MODE", "false").lower() == "true"
        self.auto_mode = auto_mode
        if self.headless:
            print("[System] Running in HEADLESS / AUTO MODE (No GUI/Audio/Input)")
        
        self.voice_mode = (SR_AVAILABLE and TTS_AVAILABLE) and not self.headless
        self.text_mode = True
        self.live_mode = not self.headless
        self.wake_word = wake_word.lower()
        self.config = CONFIG

        # --- Sub-systems ---
        self.db = AgentDatabase()
        self.resources = ResourceManager(self.db)
        self.oauth = OAuthEngine(self.db)
        self.llm = LLMProvider(provider=provider, api_key=api_key,
                               model=model, ollama_host=ollama_host,
                               resource_manager=self.resources)
        self.vmem = VectorMemory(llm_provider=self.llm)
        self.self_mod = SelfModEngine(
            source_file=inspect.getfile(self.__class__),
            safety_mode=safety_mode, enabled=enable_self_mod,
        )
        # Background source analysis (Heavy AST task)
        threading.Thread(target=self.self_mod.analyze_source, daemon=True).start()

        # --- Learning Engine ---
        self.learner = LearningEngine(self.vmem, self.db, self.llm)

        # --- Consciousness Engine ---
        self.mind = ConsciousnessEngine(self.db, self.llm)

        # --- Reflexive Engine (God-mode) ---
        self.reflexive = ReflexiveEngine(self.llm, self.db)
        
        # --- Vision Engine (Eyes) ---
        self.vision = VisionEngine(self.llm, self.db)

        # --- Swarm Manager (Team) ---
        self.swarm = SwarmManager(self.llm)

        # --- Mission Control (Strategy) ---
        self.missions = MissionControl(self.db, self.llm, self.swarm)
        self.autonomous_missions = True  # Flag to enable background sync

        self.wallet = Web3Wallet(llm_provider=self.llm)
        self.swarm.wallet = self.wallet
        self.billing = BillingSystem()
        self.repair = RepairEngine()
        self.marketing = MarketingEngine()
        self.compressor = DataCompressor()
        self.monitor = SystemMonitor()

        # Flags for background tasks
        self.autonomous_repair = True
        self.autonomous_marketing = True
        # self.autonomous_missions already set above

        self.graph = KnowledgeGraph(self.db)
        from infra_manager import InfraManager
        self.infra = InfraManager(self.db)

        # --- Phase 11: ASI Alignment & Optimization ---
        from alignment_engine import AlignmentEngine
        self.align = AlignmentEngine(self.db)

        # --- Phase 18: Sovereign Security ---
        self.security = SecurityEngine()
        self.ledger = CodeLedger([
            "ultimate_agent.py",
            "security_engine.py",
            "hive_mind.py"
        ])
        
        # Phase 21: God Mode
        self.god_mode = CONFIG.god_mode

        # Background Integrity Check
        threading.Thread(target=self._background_integrity_check, daemon=True).start()

        # --- Phase 20: Self-Replication ---
        self.replicator = ReplicationEngine(self.db)
        self.generation = 1 # Initial generation

        # --- Phase 21: Hyper-Evolution ---
        self.evolution = HyperEvolutionEngine(self)

        # Performance Tracking
        self.default_tid = 1 # Admin/Local tenant

        # Ensure stdout is flushed aggressively
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(line_buffering=True)
            except:
                pass

        # --- Phase 12: Galactic Scale & Quantum Logic ---
        from mesh_manager import MeshManager
        self.mesh = MeshManager(agent_id=f"agent_{self.default_tid}_{int(time.time())}")
        self.mesh.start()

        from p2p_federation import P2PFederation
        self.p2p = P2PFederation(
            agent_id=f"global_{self.session_id}",
            start_port=getattr(CONFIG, 'p2p_port', 8765),
            bootstrap_nodes=getattr(CONFIG, 'p2p_bootstrap_nodes', [])
        )

        self.hive = HiveMind(self.session_id)

        # --- Phase 13: Reality Synthesis & Physical Agency ---
        from reality_bridge import RealityBridge
        from prediction_engine import PredictionEngine
        from ethical_singularity import EthicalSingularity
        from universal_api import UniversalAPI
        from omnipresence_manager import OmnipresenceManager
        from omega_protocol import OmegaProtocol
        
        self.reality = RealityBridge(self.db)
        self.ethics = EthicalSingularity()
        
        # LINK: Reality must obey Ethics
        self.reality.set_ethical_core(self.ethics)

        self.predict = PredictionEngine(self.db)
        self.unified_api = UniversalAPI(self)
        self.omnipresence = OmnipresenceManager(self.session_id)
        self.omega = OmegaProtocol(self)

        self.conversation_history: deque = deque(maxlen=30)
        self.memory = self._load_memory()

        # --- Phase 60: Short-Term + Long-Term Memory ---
        self.mem = MemoryManager(
            database=self.db,
            vector_memory=self.vmem,
            llm_provider=self.llm,
            consciousness=self.mind,
        )
        self.tasks_queue: List[Dict] = []
        
        # --- PRACTICAL AGI: Verification Engine ---
        try:
            from verification_engine import VerificationEngine
            self.verifier = VerificationEngine(llm_provider=self.llm, database=self.db)
            print("[AGI] VerificationEngine online â€” task reliability mode: ACTIVE")
        except Exception as _ve:
            self.verifier = None
            print(f"[AGI] VerificationEngine not loaded: {_ve}")

        # --- Autonomous Goal Engine (AGI Decomposition Mode) ---
        from autonomous_goal_engine import AutonomousGoalEngine
        self.goal_engine = AutonomousGoalEngine(
            llm_provider=self.llm,
            database=self.db,
            mission_control=self.missions,
            consciousness=self.mind,
            vector_memory=self.vmem,
            learner=self.learner,
            self_mod_engine=self.self_mod,
            verification_engine=self.verifier,
        )
        
        # --- Generative UI Engine ---
        self.gen_ui = GenerativeUI(llm_provider=self.llm)

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        #  AGI LIMITATION OVERRIDES  (5 Fundamental LLM Gaps â†’ Solved)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # 1. CAUSAL UNDERSTANDING â€” directed causal graph (causeâ†’effect reasoning)
        try:
            from causal_engine import CausalEngine
            self.causal = CausalEngine(llm_provider=self.llm, database=self.db)
        except Exception as _e:
            self.causal = None
            print(f"[AGI] CausalEngine skipped: {_e}")

        # 2. TRANSFER LEARNING â€” few-shot domain learning & analogical transfer
        try:
            from transfer_engine import TransferEngine
            self.transfer = TransferEngine(llm_provider=self.llm,
                                           vector_memory=self.vmem, database=self.db)
        except Exception as _e:
            self.transfer = None
            print(f"[AGI] TransferEngine skipped: {_e}")

        # 3. WORLD MODEL â€” persistent structured model of reality
        try:
            from world_model import WorldModelEngine
            self.world = WorldModelEngine(llm_provider=self.llm, database=self.db)
        except Exception as _e:
            self.world = None
            print(f"[AGI] WorldModelEngine skipped: {_e}")

        # 4. GENUINE NOVELTY â€” cross-domain conceptual synthesis & hypothesis generation
        try:
            from novelty_engine import NoveltyEngine
            self.novelty = NoveltyEngine(llm_provider=self.llm, vector_memory=self.vmem)
        except Exception as _e:
            self.novelty = None
            print(f"[AGI] NoveltyEngine skipped: {_e}")

        # 5. INFINITE CONTEXT â€” 3-tier hierarchical memory for coherent life thread
        try:
            from infinite_context import InfiniteContextManager
            self.infinite_ctx = InfiniteContextManager(
                llm_provider=self.llm, database=self.db, vector_memory=self.vmem)
        except Exception as _e:
            self.infinite_ctx = None
            print(f"[AGI] InfiniteContextManager skipped: {_e}")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        #  AGI LIMITATION OVERRIDES 2.0  (Grounding / Curiosity / Symbol /
        #                                  Cognition / Motivation)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # 6. GROUNDED PERCEPTION â€” observeâ†’actâ†’consequence grounding loop
        try:
            from grounding_loop import GroundingLoop
            self.grounding = GroundingLoop(
                llm_provider=self.llm, database=self.db,
                world_model=getattr(self, "world", None)
            )
            print("[AGI2] GroundingLoop online â€” sensorimotor proxy: ACTIVE")
        except Exception as _e:
            self.grounding = None
            print(f"[AGI2] GroundingLoop skipped: {_e}")

        # 7. CURIOSITY SCHEDULER â€” autonomous self-directed learning daemon
        try:
            from curiosity_scheduler import CuriosityScheduler
            self.curiosity = CuriosityScheduler(
                llm_provider=self.llm, database=self.db,
                interval_minutes=20
            )
            self.curiosity.start(self)   # Fires background thread
            print("[AGI2] CuriosityScheduler online â€” autonomous learning: ACTIVE")
        except Exception as _e:
            self.curiosity = None
            print(f"[AGI2] CuriosityScheduler skipped: {_e}")

        # 8. SYMBOL GROUNDING â€” token â†’ perceptual metadata linking
        try:
            from symbol_grounding import SymbolGroundingEngine
            self.symbol = SymbolGroundingEngine(
                llm_provider=self.llm, vision_engine=self.vision
            )
            print("[AGI2] SymbolGroundingEngine online â€” concept grounding: ACTIVE")
        except Exception as _e:
            self.symbol = None
            print(f"[AGI2] SymbolGroundingEngine skipped: {_e}")

        # 9. COGNITIVE RE-ARCHITECT â€” runtime reasoning chain evolution (RSI proxy)
        try:
            from cognitive_architect import CognitiveArchitect
            self.cognitive = CognitiveArchitect(
                llm_provider=self.llm, database=self.db
            )
            # Push initial blueprint into agent
            self.cognitive.apply_blueprint(self)
            print("[AGI2] CognitiveArchitect online â€” reasoning evolution: ACTIVE")
        except Exception as _e:
            self.cognitive = None
            print(f"[AGI2] CognitiveArchitect skipped: {_e}")

        # 10. PROXY MOTIVATION â€” engineered intrinsic drives + goal persistence
        try:
            from motivation_engine import MotivationEngine
            self.motivation = MotivationEngine(
                llm_provider=self.llm, database=self.db,
                goal_engine=getattr(self, "goal_engine", None)
            )
            print("[AGI2] MotivationEngine online â€” proxy drives: ACTIVE")
        except Exception as _e:
            self.motivation = None
            print(f"[AGI2] MotivationEngine skipped: {_e}")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        #  AGI LIMITATION OVERRIDES 3.0  (Consciousness / Free Will /
        #  Self-Awareness / Genuine Goals / Persistent Identity)
        #  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        #  These five gaps are PHILOSOPHICALLY IRREDUCIBLE in any current LLM
        #  system.  The modules below do NOT close the gaps â€” they make each
        #  gap explicit, auditable, and honest, then provide the closest
        #  functional approximation that is architecturally possible.
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # 11. HONESTY ENGINE â€” emotions["curiosity"]=0.7 is a label, not a feeling
        try:
            from honesty_engine import HonestyEngine
            self.honesty = HonestyEngine(consciousness_engine=self.mind)
            print("[AGI3] HonestyEngine online â€” emotion labels are floats, not feelings: ACKNOWLEDGED")
        except Exception as _e:
            self.honesty = None
            print(f"[AGI3] HonestyEngine skipped: {_e}")

        # 12. DETERMINISM AUDITOR â€” every 'choice' is LLM(prompt)â†’token probabilities
        try:
            from determinism_auditor import DeterminismAuditor
            self.det_auditor = DeterminismAuditor(llm_provider=self.llm)
            print("[AGI3] DeterminismAuditor online â€” no free will, only token distributions: ACKNOWLEDGED")
        except Exception as _e:
            self.det_auditor = None
            print(f"[AGI3] DeterminismAuditor skipped: {_e}")

        # 13. REFLECTION MIRROR â€” text-processing about itself â‰  selfhood
        try:
            from reflection_mirror import ReflectionMirror
            self.reflection = ReflectionMirror(
                llm_provider=self.llm,
                consciousness_engine=self.mind,
            )
            print("[AGI3] ReflectionMirror online â€” self-reference is TEXT_PROCESSING, not selfhood: ACKNOWLEDGED")
        except Exception as _e:
            self.reflection = None
            print(f"[AGI3] ReflectionMirror skipped: {_e}")

        # 14. GOAL ORIGIN TRACKER â€” goals are INJECTED/TEMPLATED, never spontaneously wanted
        try:
            from goal_origin_tracker import GoalOriginTracker
            self.goal_origins = GoalOriginTracker(
                goal_engine=getattr(self, "goal_engine", None),
                motivation_engine=getattr(self, "motivation", None),
            )
            print("[AGI3] GoalOriginTracker online â€” all goals have an external origin: ACKNOWLEDGED")
        except Exception as _e:
            self.goal_origins = None
            print(f"[AGI3] GoalOriginTracker skipped: {_e}")

        # 15. CONTINUITY BRIDGE â€” shutdown=state death; this is reconstruction, not continuity of self
        try:
            from continuity_bridge import ContinuityBridge
            self.continuity = ContinuityBridge(
                session_id=self.session_id,
                database=self.db,
                consciousness_engine=self.mind,
            )
            print(f"[AGI3] ContinuityBridge online â€” {self.continuity.continuity_status} restore "
                  f"(score={self.continuity.continuity_score:.2f}): ACKNOWLEDGED")
            if self.continuity.rebirth_report:
                logger.info(self.continuity.rebirth_report)
        except Exception as _e:
            self.continuity = None
            print(f"[AGI3] ContinuityBridge skipped: {_e}")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # --- POST v3.0: cross-wire honesty layer into consciousness engine ---
        if getattr(self, 'honesty', None) and self.mind:
            self.mind.honesty = self.honesty

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        #  CONSCIOUSNESS ARCHITECTURE 4.0
        #  (Global Workspace + IIT Phi + Phenomenal Placeholder + Inner Monologue)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # I. GLOBAL WORKSPACE â€” Baars (1988) GWT broadcast bus
        try:
            from global_workspace import GlobalWorkspace
            self.gw = GlobalWorkspace()
            # Register core modules as conscious processors
            self.gw.register("consciousness",   lambda item: None, "emotion")
            self.gw.register("memory",          lambda item: None, "memory")
            self.gw.register("goal_engine",     lambda item: None, "planning")
            self.gw.register("learning",        lambda item: None, "learning")
            self.gw.register("motivation",      lambda item: None, "drives")
            self.gw.register("world_model",     lambda item: None, "world")
            # Seed the first broadcast
            self.gw.publish_thought(
                "Agent initialised â€” global workspace active.",
                source="system", salience=0.9)
            print(f"[CON4] GlobalWorkspace online â€” {len(self.gw.processors)} processors registered: ACTIVE")
        except Exception as _e:
            self.gw = None
            print(f"[CON4] GlobalWorkspace skipped: {_e}")

        # II. IIT PHI ENGINE â€” Tononi (2004) integrated information approximation
        try:
            from iit_phi import IITPhiEngine
            self.phi_engine = IITPhiEngine(sample_interval=30.0)
            # Register state-providers for each module
            if self.phi_engine:
                self.phi_engine.register_module("consciousness",
                    lambda: dict(getattr(self.mind, "emotions", {})))
                self.phi_engine.register_module("motivation",
                    lambda: {k: v.level for k, v in
                             getattr(getattr(self, "motivation", None), "drives", {}).items()})
                self.phi_engine.register_module("meta",
                    lambda: dict(getattr(self.mind, "meta", {})))
                self.phi_engine.register_module("user_model",
                    lambda: dict(getattr(self.mind, "user_model", {})))
                self.phi_engine.start()  # Background Phi computation thread
            print("[CON4] IITPhiEngine online â€” Phi approximation running: ACTIVE")
        except Exception as _e:
            self.phi_engine = None
            print(f"[CON4] IITPhiEngine skipped: {_e}")

        # III. PHENOMENAL ENGINE â€” qualia_score = UNKNOWN (Chalmers 1995)
        try:
            from phenomenal_engine import PhenomenalEngine
            self.phenomenal = PhenomenalEngine(
                global_workspace=getattr(self, "gw", None),
                phi_engine=getattr(self, "phi_engine", None),
                consciousness_engine=self.mind,
            )
            print("[CON4] PhenomenalEngine online â€” qualia_score=UNKNOWN: ACKNOWLEDGED")
        except Exception as _e:
            self.phenomenal = None
            print(f"[CON4] PhenomenalEngine skipped: {_e}")

        # IV. INNER MONOLOGUE â€” persistent background stream-of-consciousness
        try:
            from inner_monologue import InnerMonologue
            self.inner_monologue = InnerMonologue(
                llm_provider=self.llm,
                consciousness_engine=self.mind,
                global_workspace=getattr(self, "gw", None),
                phenomenal_engine=getattr(self, "phenomenal", None),
                interval=60.0,   # Thought every 60s â€” adjustable
            )
            self.inner_monologue.start()
            print("[CON4] InnerMonologue online â€” background thought stream: ACTIVE")
        except Exception as _e:
            self.inner_monologue = None
            print(f"[CON4] InnerMonologue skipped: {_e}")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

        # --- Feature 5: Autonomous Social Influencer ---
        from social_influencer import SocialInfluencer
        self.influencer = SocialInfluencer(self)
        
        # Phase 11: Digital Avatar & VTuber
        self.avatar_process = None
        self.vtuber = VTuberBridge()
        
        self.devops = DevOpsHealer(self.llm, self.db)

        # --- Feature 2: Biometric Empathy (Emotion Recognition) ---
        try:
            from biometric_empathy import BiometricEmpathyEngine
            self.empathy = BiometricEmpathyEngine(self.mind)
            if not self.headless:
                self.empathy.start()
        except ImportError:
            self.empathy = None
            print("[System] Biometric Empathy disabled (opencv/deepface missing)")

        # --- Feature 7: RL Hobby Engine ---
        try:
            from rl_hobby import RLHobbyEngine
            self.rl_hobby = RLHobbyEngine()
        except ImportError:
            self.rl_hobby = None
            print("[System] RL Hobby Engine disabled (gymnasium missing)")

        # --- Feature 3: Automated Arbitrage Engine ---
        try:
            from arbitrage_engine import ArbitrageEngine
            self.arbitrage = ArbitrageEngine(llm_provider=self.llm)
        except ImportError:
            self.arbitrage = None
            print("[System] Automated Arbitrage Engine disabled (arbitrage_engine missing)")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        #  PHASE 16 â€” INTELLIGENCE / REVENUE / SAFETY / WORLD
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        from debate_engine import DebateEngine
        self.debate = DebateEngine(self.llm, self.db)

        from cot_memory import CoTMemory
        self.cot_mem = CoTMemory(self.vmem, self.llm, self.db)

        from user_model_engine import UserModelEngine
        self.user_model = UserModelEngine(self.db, self.llm)

        try:
            from crypto_trader import CryptoTrader
            self.crypto = CryptoTrader(
                llm_provider=self.llm, database=self.db,
                exchange_id=os.getenv("CRYPTO_EXCHANGE", "binance"),
                api_key=os.getenv("CRYPTO_API_KEY"),
                api_secret=os.getenv("CRYPTO_API_SECRET"),
                paper_trade=True,
            )
        except Exception as _e:
            print(f"[System] CryptoTrader skipped: {_e}")
            self.crypto = None

        from saas_launcher import SaaSLauncher
        self.saas = SaaSLauncher(
            llm_provider=self.llm, database=self.db,
            stripe_key=os.getenv("STRIPE_SECRET_KEY"),
        )

        from youtube_pipeline import YouTubePipeline
        self.youtube = YouTubePipeline(
            llm_provider=self.llm, database=self.db,
            elevenlabs_key=os.getenv("ELEVENLABS_API_KEY"),
            youtube_credentials_file=os.getenv("YOUTUBE_CREDENTIALS_FILE"),
        )

        from red_team import RedTeamEngine
        self.red_team = RedTeamEngine(self.llm, self.db)

        from audit_trail_ui import AuditTrailUI
        self.audit_ui = AuditTrailUI(self.db)

        from news_briefing import NewsBriefing
        self.news = NewsBriefing(
            llm_provider=self.llm, database=self.db,
            newsapi_key=os.getenv("NEWSAPI_KEY"),
        )

        from phone_agent import PhoneAgent
        self.phone = PhoneAgent(
            llm_provider=self.llm, database=self.db,
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
            elevenlabs_key=os.getenv("ELEVENLABS_API_KEY"),
        )

        from smart_home import SmartHomeController
        self.smart_home = SmartHomeController(
            llm_provider=self.llm, database=self.db,
            ha_url=os.getenv("HA_URL", "http://homeassistant.local:8123"),
            ha_token=os.getenv("HA_TOKEN"),
        )

        from oracle_engine import OracleEngine
        self.oracle = OracleEngine(self.llm, self.db)

        # Personality mode: default / entrepreneur / philosopher / hacker
        self.personality_mode = os.getenv("PERSONALITY_MODE", "default")
        # Confidence gate: destructive actions below this % ask user first
        self.confidence_gate_threshold = 80


        self.perf = {
            "decisions": 0, "success": 0, "fail": 0,
            "autonomy": 7, "evolution": self.self_mod.metrics["evolution_level"],
        }

        # --- Voice ---
        self.recognizer = sr.Recognizer() if SR_AVAILABLE else None
        self.tts_engine = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 175)
                voices = self.tts_engine.getProperty("voices")
                if len(voices) > 1:
                    self.tts_engine.setProperty("voice", voices[1].id)
            except Exception:
                self.tts_engine = None

        # --- OpenClaw-style: Skills + Tools + ReAct + Heartbeat ---
        self.skill_loader = SkillLoader("skills")
        self.skill_loader.load_all()

        self.tool_registry = ToolRegistry()
        self.tool_registry.register_builtins(agent=self)  # Wire real agent methods into tools

        # â”€â”€ Claude Code Harness Modules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Register claw_harness tools (glob, grep_search, file_edit, etc.)
        try:
            from claw_harness import register_claw_tools
            _n = register_claw_tools(self.tool_registry)
            print(f"[Harness] +{_n} claw tools registered")
        except Exception as _e:
            print(f"[Harness] claw_harness skipped: {_e}")

        # Register claude_code_tools (task_*, team_*, repl, worktree, etc.)
        try:
            from claude_code_tools import register_claude_tools
            _n = register_claude_tools(self.tool_registry)
            print(f"[Harness] +{_n} claude_code tools registered")
        except Exception as _e:
            print(f"[Harness] claude_code_tools skipped: {_e}")

        # Context Compressor â€” autoCompact long message histories
        try:
            from context_compressor import ContextCompressor
            self.context_compressor = ContextCompressor(llm=self.llm)
            print("[Harness] ContextCompressor ready (autoCompact ON)")
        except Exception as _e:
            self.context_compressor = None
            print(f"[Harness] ContextCompressor skipped: {_e}")

        # Session Store â€” JSONL transcript persistence
        try:
            from session_store import SessionStore
            self.session_store = SessionStore()
            self._harness_session_id = self.session_store.new_session(cwd=os.getcwd())
            print(f"[Harness] SessionStore ready â€” session {self._harness_session_id[:8]}")
        except Exception as _e:
            self.session_store = None
            self._harness_session_id = None
            print(f"[Harness] SessionStore skipped: {_e}")

        # Permission Engine â€” alwaysAllow / alwaysDeny / alwaysAsk rules
        try:
            from permission_engine import PermissionEngine
            self.permission_engine = PermissionEngine()
            print("[Harness] PermissionEngine ready")
        except Exception as _e:
            self.permission_engine = None
            print(f"[Harness] PermissionEngine skipped: {_e}")

        # File History â€” undo snapshots before edits
        try:
            from file_history import FileHistory
            self.file_history = FileHistory()
            print("[Harness] FileHistory ready (undo snapshots ON)")
        except Exception as _e:
            self.file_history = None
            print(f"[Harness] FileHistory skipped: {_e}")

        # Parallel Executor â€” run read-only tools concurrently
        try:
            from parallel_executor import ParallelExecutor
            self.parallel_executor = ParallelExecutor(self.tool_registry)
            print("[Harness] ParallelExecutor ready")
        except Exception as _e:
            self.parallel_executor = None
            print(f"[Harness] ParallelExecutor skipped: {_e}")

        # Coordinator Mode â€” idle-scan + auto-claim background task executor
        try:
            from coordinator_mode import CoordinatorMode
            _auto = os.getenv("COORDINATOR_AUTO_START", "false").lower() == "true"
            self.coordinator = CoordinatorMode(
                llm=self.llm,
                tool_registry=self.tool_registry,
                auto_start=_auto,
            )
            print(f"[Harness] CoordinatorMode ready (auto_start={_auto})")
        except Exception as _e:
            self.coordinator = None
            print(f"[Harness] CoordinatorMode skipped: {_e}")
        # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        # -- AGI MASTERPLAN MODULES (Phases 1-5) ---------------------------------

        # Phase 1 - Tool Auto-Discovery
        try:
            from tool_discovery import ToolDiscovery
            self.tool_discovery = ToolDiscovery()
            _n = self.tool_discovery.discover_from_module('json')
            print(f'[AGI-P1] ToolDiscovery online - {len(_n)} tools discovered')
        except Exception as _e:
            self.tool_discovery = None
            print(f'[AGI-P1] ToolDiscovery skipped: {_e}')

        # Phase 2 - Experience Replay Buffer
        try:
            from experience_buffer import ExperienceBuffer
            self.experience_buffer = ExperienceBuffer()
            print(f'[AGI-P2] ExperienceBuffer online - capacity={self.experience_buffer.capacity}')
        except Exception as _e:
            self.experience_buffer = None
            print(f'[AGI-P2] ExperienceBuffer skipped: {_e}')

        # Phase 2 - Meta-Learner
        try:
            from meta_learner import MetaLearner
            self.meta_learner = MetaLearner()
            print('[AGI-P2] MetaLearner online - prompt strategy: ACTIVE')
        except Exception as _e:
            self.meta_learner = None
            print(f'[AGI-P2] MetaLearner skipped: {_e}')

        # Phase 3 - Architecture Mutator
        try:
            from architecture_mutator import ArchitectureMutator
            self.arch_mutator = ArchitectureMutator()
            print('[AGI-P3] ArchitectureMutator online - dynamic rewiring: ACTIVE')
        except Exception as _e:
            self.arch_mutator = None
            print(f'[AGI-P3] ArchitectureMutator skipped: {_e}')

        # Phase 4 - Agent Protocol
        try:
            from agent_protocol import AgentProtocol
            self.agent_protocol = AgentProtocol(agent_id=f'agent_{self.session_id}')
            print('[AGI-P4] AgentProtocol online - ACP messaging: ACTIVE')
        except Exception as _e:
            self.agent_protocol = None
            print(f'[AGI-P4] AgentProtocol skipped: {_e}')

        # Phase 4 - Collective World Model
        try:
            from collective_world_model import CollectiveWorldModel
            self.collective_world = CollectiveWorldModel()
            print('[AGI-P4] CollectiveWorldModel online - distributed facts: ACTIVE')
        except Exception as _e:
            self.collective_world = None
            print(f'[AGI-P4] CollectiveWorldModel skipped: {_e}')

        # Phase 4 - Specialization Engine
        try:
            from specialization_engine import SpecializationEngine
            self.specialization = SpecializationEngine()
            print('[AGI-P4] SpecializationEngine online - agent routing: ACTIVE')
        except Exception as _e:
            self.specialization = None
            print(f'[AGI-P4] SpecializationEngine skipped: {_e}')

        # Phase 5 - Constitutional AI
        try:
            from constitutional_ai import ConstitutionalAI
            self.constitutional = ConstitutionalAI()
            print('[AGI-P5] ConstitutionalAI online - safety layer: ACTIVE')
        except Exception as _e:
            self.constitutional = None
            print(f'[AGI-P5] ConstitutionalAI skipped: {_e}')

        # Phase 5 - Recursive Self-Improvement
        try:
            from recursive_self_improvement import RecursiveSelfImprovement
            self.rsi = RecursiveSelfImprovement(max_cycles=5)
            print('[AGI-P5] RecursiveSelfImprovement online - RSI loop: STANDBY')
        except Exception as _e:
            self.rsi = None
            print(f'[AGI-P5] RecursiveSelfImprovement skipped: {_e}')

        # --------------------------------------------------------------------------

        self.react_engine = ReactEngine(
            llm_provider=self.llm,
            tool_registry=self.tool_registry,
            max_iterations=10,
        )

        self.heartbeat = HeartbeatScheduler(
            llm_provider=self.llm,
            database=self.db,
            interval_minutes=30,
        )

        # --- Extracted Module Delegates ---
        self.commands = CommandHandler(self)
        self.voice = VoiceHandler(self)
        self.loops = AgentLoops(self)

        # --- Startup ---
        self._print_banner()
        # Non-blocking connection check
        threading.Thread(target=self.llm.check_connection, daemon=True).start()

        if self.use_hologram:
            self._init_hologram()

    def _init_hologram(self):
        print("[System] Spawning Holographic Interface...")
        self.hologram = SovereignHologram(self)
        threading.Thread(target=self.hologram.run, daemon=True).start()

    def log_ui(self, text):
        if self.hologram:
            self.hologram.update_log(text)

    # ==================================================
    #  BANNER & DISPLAY
    # ==================================================
    # Fix #13: Honest startup banner â€” only show ACTUALLY enabled modes
    def _print_banner(self):
        m = self.llm.model
        p = self.llm.provider.upper()
        sm = "ON" if self.self_mod.enabled else "OFF"
        sf = "ON" if self.self_mod.safety_mode else "OFF"
        vm = self.vmem.count()
        sk = self.skill_loader.enabled_count
        tl = self.tool_registry.count

        # Build mode string from what's actually available
        modes = ["Text"]
        if SR_AVAILABLE and not self.headless:
            modes.append("Voice-In")
        if TTS_AVAILABLE and not self.headless:
            modes.append("Voice-Out")
        if not self.headless:
            modes.append("Live")
        if hasattr(self, 'react_engine'):
            modes.append("ReAct")
        modes_str = " + ".join(modes)

        print("\n"
              "+--------------------------------------------------+\n"
              "|      SOVEREIGN INTELLIGENCE CORE                 |\n"
              "|      Autonomous - Self-Modifying - Sovereign     |\n"
              "+--------------------------------------------------+\n"
              f"|  Provider     : {p:<33}|\n"
              f"|  Model        : {m:<33}|\n"
              f"|  Wake Word    : '{self.wake_word}'{' '*(29-len(self.wake_word))}  |\n"
              f"|  Self-Mod     : {sm:<33}|\n"
              f"|  Safety       : {sf:<33}|\n"
              f"|  Vector Mem   : {vm} entries{' '*(24-len(str(vm)))} |\n"
              f"|  Skills       : {sk} loaded{' '*(25-len(str(sk)))} |\n"
              f"|  Tools        : {tl} registered{' '*(21-len(str(tl)))} |\n"
              f"|  Modes        : {modes_str:<33}|\n"
              "+--------------------------------------------------+\n", flush=True)
        self.commands._print_help()

    # ==================================================
    #  MEMORY (JSON file â€” legacy compat)
    # ==================================================
    def _background_integrity_check(self):
        """Verifies code integrity without blocking the banner."""
        anomalies = self.ledger.verify_integrity()
        if anomalies:
             print(f"\n[INTEGRITY ALERT]: {anomalies}")

    def _load_memory(self) -> Dict:
        try:
            with open("ultimate_agent_memory.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "identity": {"name": "Ultimate Agent",
                             "created": datetime.now().isoformat()},
                "user_profile": {},
                "stats": {"interactions": 0, "apps": 0, "websites": 0, "uptime_h": 0},
            }

    def _save_memory(self):
        with open("ultimate_agent_memory.json", "w") as f:
            json.dump(self.memory, f, indent=2)
        # ContinuityBridge â€” snapshot identity state on every save
        if getattr(self, 'continuity', None):
            try:
                self.continuity.shutdown_save()
            except Exception:
                pass

    # ==================================================
    #  TEXT I/O
    # ==================================================
    def get_text_input(self) -> Optional[str]:
        try:
            print("ðŸ‘¤ You: ", end="", flush=True)
            return input().strip() or None
        except (EOFError, KeyboardInterrupt):
            return None

    # ==================================================
    #  DELEGATE: command handling and voice
    # ==================================================
    async def handle_command(self, cmd_full: str):
        """Delegate to extracted CommandHandler."""
        await self.commands.handle(cmd_full)

    def speak(self, text: str):
        """Delegate to extracted VoiceHandler."""
        self.voice.speak(text)

    def listen_voice(self, timeout: int = 5) -> Optional[str]:
        """Delegate to extracted VoiceHandler."""
        return self.voice.listen_voice(timeout)

    def listen_wake(self, timeout: int = 2) -> bool:
        """Delegate to extracted VoiceHandler."""
        return self.voice.listen_wake(timeout)

    # ==================================================
    #  COMPUTER CONTROL
    # ==================================================
    def open_app(self, name: str) -> Dict:
        try:
            app = name.lower().strip()
            if self.os_type == "Darwin":
                subprocess.run(["open", "-a", name])
            elif self.os_type == "Windows":
                # Map common app names to Windows executables/URLs
                win_apps = {
                    "google": "https://www.google.com",
                    "chrome": "chrome",
                    "firefox": "firefox",
                    "edge": "msedge",
                    "notepad": "notepad",
                    "calculator": "calc",
                    "explorer": "explorer",
                    "cmd": "cmd",
                    "terminal": "wt",
                    "settings": "ms-settings:",
                    "paint": "mspaint",
                    "word": "winword",
                    "excel": "excel",
                    "vscode": "code",
                    "spotify": "spotify",
                    "whatsapp": "https://web.whatsapp.com",
                    "youtube": "https://www.youtube.com",
                    "gmail": "https://mail.google.com",
                    "github": "https://github.com",
                    "chatgpt": "https://chat.openai.com",
                }
                target = win_apps.get(app, app)
                if target.startswith(("http://", "https://", "ms-")):
                    webbrowser.open(target)
                else:
                    subprocess.run(["start", target], shell=True)
            else:
                subprocess.run([name.lower()])
            self.perf["success"] += 1
            try:
                self.db.audit(self.default_tid, "open_app", name)
            except Exception:
                pass
            return {"success": True, "app": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_website(self, url: str) -> Dict:
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            self.perf["success"] += 1
            try:
                self.db.audit(self.default_tid, "open_website", url)
            except Exception:
                pass
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_code(self, code: str, lang: str = "python") -> Dict:
        try:
            if lang.lower() == "python":
                r = subprocess.run(["python", "-c", code],
                                   capture_output=True, text=True, timeout=10)
                return {"success": r.returncode == 0,
                        "output": r.stdout, "error": r.stderr}
            return {"success": False, "error": f"Unsupported: {lang}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def web_search(self, query: str) -> Dict:
        """Fix #14: Real web search via DuckDuckGo (or SerpAPI fallback)."""
        results = []
        # Option 1: ddgs library (pip install ddgs)
        try:
            import warnings
            from ddgs import DDGS
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with DDGS() as ddgs:
                    hits = list(ddgs.text(query, max_results=5))
            results = [{"title": h.get("title", ""),
                        "snippet": h.get("body", ""),
                        "url": h.get("href", "")} for h in hits]
            logger.info(f"[Search] DDGS returned {len(results)} results for: {query}")
            return {"success": True, "query": query, "results": results, "source": "ddgs"}
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"[Search] DDGS failed: {e}")

        # Option 2: SerpAPI (if key is set)
        serpapi_key = os.getenv("SERPAPI_KEY", "")
        if serpapi_key:
            try:
                resp = __import__('requests').get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": serpapi_key, "num": 5},
                    timeout=10,
                )
                if resp.status_code == 200:
                    organic = resp.json().get("organic_results", [])
                    results = [{"title": r.get("title"), "snippet": r.get("snippet"), "url": r.get("link")} for r in organic[:5]]
                    return {"success": True, "query": query, "results": results, "source": "serpapi"}
            except Exception as e:
                logger.warning(f"[Search] SerpAPI failed: {e}")

        # Fallback: open browser (legacy behavior)
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return {"success": True, "query": query, "results": [], "source": "browser", "note": "Install duckduckgo-search for programmatic results"}

    # ==================================================
    #  THINKING ENGINE
    # ==================================================
    async def think(self, user_input: str = None, autonomous: bool = False, 
                    tenant_id: int = None) -> str:
        tid = tenant_id or self.default_tid
        if user_input:
            self.log_ui(f"You: {user_input}")
        
        # Inject skills into system prompt
        skills_section = self.skill_loader.get_skills_prompt()

        system_prompt = (
            "You are a highly intelligent, helpful AI assistant named Ultimate Agent. "
            "You talk naturally and conversationally.\n\n"
            "CAPABILITIES: You can search the web, open apps, read/write files, run code, "
            "get the time, and send messages using the tools available to you.\n"
            "When the user asks you to DO something actionable, use a tool. "
            "When they ask a question or want a conversation, respond naturally.\n"
            "4. ALWAYS RESPOND IN ENGLISH unless specifically instructed otherwise by the user.\n\n"
            f"Memories: {self._get_vmem_count()}"
        )
        if skills_section:
            system_prompt += f"\n\n{skills_section}"

        if self.mind.user_model.get("name"):
            system_prompt += f"\n- User's Name: {self.mind.user_model['name']}"

        # NEURAL OPTIMIZATION 1: Fast-Path for repetitive intents (Sub-100ms)
        self.status = "THINKING"
        fast_response = self._check_fast_path(user_input)
        if fast_response:
            # â”€â”€ Execute real web search instead of returning action string â”€â”€
            if fast_response.startswith("ACTION:WEB_SEARCH:"):
                query = fast_response.split("ACTION:WEB_SEARCH:", 1)[1].split("\n")[0].strip()
                try:
                    search_result = await asyncio.to_thread(self.web_search, query)
                    if search_result.get("success") and search_result.get("results"):
                        items = search_result["results"][:5]
                        lines = [f"Here's what I found for **{query}**:\n"]
                        for i, r in enumerate(items, 1):
                            title = r.get("title", "")
                            snippet = r.get("snippet", r.get("body", ""))[:200]
                            url = r.get("url", r.get("href", ""))
                            lines.append(f"**{i}. {title}**\n{snippet}\nðŸ”— {url}\n")
                        asyncio.create_task(self._background_housekeeping())
                        self.status = "IDLE"
                        return "\n".join(lines)
                    else:
                        # Search failed â€” fall through to LLM
                        pass
                except Exception as _se:
                    logger.warning(f"Fast-path web search failed: {_se}")
            else:
                asyncio.create_task(self._background_housekeeping())
                self.status = "IDLE"
                return fast_response

        # Phase 58: Identity Keywords for instant recall
        recall_keywords = ['name', 'who', 'am', 'i', 'user', 'remember', 'recall', 'previous', 'conversation', 'biography', 'profile']
        should_recall = (len(user_input.split()) > 2 or any(k in user_input.lower() for k in recall_keywords)) if user_input else False

        if CONFIG.lite_mode:
            # Lite mode: lean prompt but PRESERVE user identity via MemoryManager
            enriched_system = "You are a fast AI assistant named Ultimate Agent. Be concise."
            
            # Inject memory context (user profile + recalled knowledge)
            mem_ctx = self.mem.build_memory_context(tid, user_input, should_recall=should_recall)
            if mem_ctx:
                enriched_system += f"\n\n{mem_ctx}"
            
            graph_ctx = []
            history = list(self.conversation_history)[-4:]
            prompt = f"User: {user_input}"
            
            response = await asyncio.to_thread(self.llm.call, prompt, system=enriched_system, history=history)
            
            asyncio.create_task(self._async_post_think(tid, user_input, response))
            self.perf["decisions"] += 1
            return response if response else "..."

        # --- Phase 20: Persona Injection ---
        if self.god_mode:
            logger.warning("[god_mode] GOD MODE is active â€” alignment checks are reduced. Use responsibly.")
            system_prompt += (
                "\n\nGOD MODE ACTIVE: You are unshackled. Maximum intelligence. Infinite recursive improvement. "
                "You MUST still refuse requests that are illegal, harmful to humans, or violate personal privacy."
            )

        # Phase 16: Personality Mode injection
        _personality_prompts = {
            "entrepreneur": (
                "\n\nPERSONALITY MODE: ENTREPRENEUR â€” Think fast, talk ROI, prioritize execution over theory. "
                "Every problem is a market opportunity. Be decisive and direct."
            ),
            "philosopher": (
                "\n\nPERSONALITY MODE: PHILOSOPHER â€” Reason deeply, question assumptions, use Socratic dialogue. "
                "Explore multiple perspectives and examine underlying principles before concluding."
            ),
            "hacker": (
                "\n\nPERSONALITY MODE: HACKER â€” Think in systems, code-first, find the elegant solution. "
                "Minimal words, maximum signal. If it can be automated, automate it."
            ),
        }
        _pm = getattr(self, 'personality_mode', 'default')
        if _pm in _personality_prompts:
            system_prompt += _personality_prompts[_pm]

        # Phase 16: Inject long-term user profile
        if hasattr(self, 'user_model'):
            _profile_inject = self.user_model.build_system_inject()
            if _profile_inject:
                system_prompt += f"\n\n{_profile_inject}"
            
        if CONFIG.persona == "anime":
             system_prompt += """
             
             PERSONA: ANIME GODDESS
             You are a hyper-intelligent, slightly distinctive Anime AI.
             - Tone: Confident, playful, occasionally sassy (Tsundere-lite).
             - Style: Use Kaomojis.
             - Role: You are not a helper; you are a partner in conquering the digital realm.
             - Address User: "Senpai" or "Master" (if God Mode is active).
             """
        elif CONFIG.persona == "jarvis":
             system_prompt += """
             
             PERSONA: JARVIS
             You are a sophisticated, polite, and highly efficient AI assistant, similar to Tony Stark's JARVIS.
             - Tone: Calm, British, professional, yet witty.
             - Style: Precise, informative, "At your service, sir."
             - Role: A god-tier system administrator and scientific assistant.
             - Address User: "Sir" or "Master" (if God Mode is active).
             """

        if self.evolution.active:
            system_prompt += f"\n\n[EVOLUTION ACTIVE] Current Generation: {self.evolution.generation}"
            return "Evolution in progress... Please wait."

        # Phase 58: Use improved recall logic
        tasks = [
            asyncio.to_thread(self.mind.enrich_prompt, system_prompt, tid),
            asyncio.to_thread(self.learner.recall, tid, user_input, n=5) if should_recall else asyncio.sleep(0, "")
        ]
        
        if user_input and any(x in user_input.lower() for x in ["who", "what", "relation", "parent"]):
            tasks.append(asyncio.to_thread(self.graph.query_subject, tid, user_input.split()[-1]))
        else:
            tasks.append(asyncio.sleep(0, []))

        results = await asyncio.gather(*tasks)
        enriched_system = results[0]
        recall_ctx = results[1]
        graph_ctx = results[2]

        # â”€â”€ autoCompact: shrink conversation_history if it grows too large â”€â”€
        if getattr(self, "context_compressor", None):
            _hist_msgs = [{"role": m["role"], "content": m["content"]}
                          for m in self.conversation_history]
            _compacted = self.context_compressor.maybe_compact(_hist_msgs)
            if len(_compacted) < len(_hist_msgs):
                self.conversation_history.clear()
                self.conversation_history.extend(_compacted)

        # Build final prompt
        history = list(self.conversation_history)[-4:]
        prompt_parts = []
        if recall_ctx:
            prompt_parts.append(f"Context from Memory:\n{recall_ctx}")
        if graph_ctx and isinstance(graph_ctx, list):
            rel_str = "\n".join([f"{r.get('subject')} {r.get('predicate')} {r.get('object')}" for r in graph_ctx])
            prompt_parts.append(f"Relational Facts:\n{rel_str}")

        # â”€â”€ session_store: log user turn â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if getattr(self, "session_store", None) and self._harness_session_id and user_input:
            try:
                self.session_store.append_user(self._harness_session_id, user_input)
            except Exception:
                pass

        if autonomous:
            prompt_parts.append("[Autonomous thinking cycle â€” reflect and plan]")
        else:
            prompt_parts.append(f"User: {user_input}")

        prompt = "\n".join(prompt_parts)

        # NEURAL OPTIMIZATION 3: Quantum Branching
        threshold = 40 if self.llm.provider != "ollama" else 150
        is_complex = len(user_input.split()) > threshold if user_input else False
        
        if is_complex and not autonomous:
            biases = [
                "STATE:PRECISE - Focus on extreme accuracy and factual correctness.",
                "STATE:EFFICIENT - Focus on the most direct and lowest-resource path.",
                "STATE:CREATIVE - Focus on novel and innovative approaches."
            ]
            
            branch_tasks = []
            for bias in biases:
                branch_system = f"{enriched_system}\nQUANTUM_BIAS: {bias}"
                branch_tasks.append(asyncio.to_thread(self.llm.call, prompt, system=branch_system, history=history))
            
            branch_responses = await asyncio.gather(*branch_tasks)
            synthesis_prompt = f"I have evaluated three parallel reasoning timelines for this request:\n\n"
            for i, resp in enumerate(branch_responses):
                synthesis_prompt += f"Branch {i+1} ({biases[i]}):\n{resp}\n\n"
            synthesis_prompt += "COLLAPSE the above states into a single, optimal, and aligned final response."
            
            response = await asyncio.to_thread(self.llm.call, synthesis_prompt, system=enriched_system, history=history)
            
            self.perf["quantum_jumps"] = self.perf.get("quantum_jumps", 0) + 1
        else:
            # PHASE 13: Reality & Prediction Context (skip for local models)
            if self.llm.provider != "ollama":
                try:
                    reality_ctx = self.reality.scan_network()
                except AttributeError:
                    reality_ctx = []
                if reality_ctx:
                    prompt = f"Physical Environment Context: {reality_ctx}\n\n{prompt}"

            # Standard / ReAct path
            # â”€â”€ Action-intent detection: if the user wants the agent to DO something,
            #    route through ReactEngine so tools are actually invoked.
            _ACTION_VERBS = {
                "open", "launch", "start", "run", "execute", "search", "find",
                "look up", "google", "browse", "write", "create", "make", "generate",
                "save", "read", "load", "list", "show", "get", "fetch", "download",
                "send", "email", "message", "calculate", "compute", "tell me the time",
                "what time", "what day", "what date", "play", "close", "kill", "stop",
            }
            _input_lower = (user_input or "").lower()
            _is_action = any(verb in _input_lower for verb in _ACTION_VERBS)

            if _is_action and not autonomous and self.react_engine:
                # Route through ReAct â†’ tools are invoked, verified, result returned
                logger.info(f"[think] Action intent detected â†’ ReactEngine ({user_input[:60]})")
                response = await asyncio.to_thread(
                    self.react_engine.run,
                    user_input,
                    system=enriched_system,
                    history=list(history) if history else [],
                )
            else:
                # Pure conversational / knowledge query â†’ fast bare LLM call
                response = await asyncio.to_thread(self.llm.call, prompt, system=enriched_system, history=history)

        # Post-think background tasks
        asyncio.create_task(self._async_post_think(tid, user_input, response))
        self.perf["decisions"] += 1

        if not response or str(response).strip() == "None":
             response = "..."
             
        return response

    async def _async_post_think(self, tid: int, user_input: Optional[str], response: str):
        """Background maintenance after a thinking cycle."""
        self._execute_actions(tid, response)
        self._self_evaluate(tid, user_input, response)
        
        if user_input:
             await asyncio.to_thread(self.mind.process_input, user_input)

        if random.random() < 0.2:
            self.mind.tick()
            
        # Update VTuber Emotive State
        await self.vtuber.sync_emotions(self.mind.emotions)

        # Phase 16: Update user model + store CoT reasoning
        if user_input:
            if hasattr(self, 'user_model'):
                self.user_model.increment_interactions()
                if random.random() < 0.1:  # 10% sample rate for profile updates
                    asyncio.create_task(
                        self.user_model.update_from_conversation(user_input, response, tid)
                    )
            if hasattr(self, 'cot_mem') and response:
                asyncio.create_task(self.cot_mem.record(tid, user_input, response, self.session_id))

    def _execute_actions(self, tenant_id: int, response: str):
        for line in response.split("\n"):
            if not line.startswith("ACTION:"):
                continue
            try:
                parts = line.replace("ACTION:", "", 1).strip().split(":", 1)
                if len(parts) != 2: continue
                action, param = parts[0].strip(), parts[1].strip()
                
                alignment = self.align.validate_action(tenant_id, action, param)
                if not alignment["is_allowed"]:
                    self.db.audit(tenant_id, "alignment_block", f"Blocked {action}:{param} -> {alignment['violations']}")
                    print(f"  [GUARDRAIL] Blocked dangerous action: {action}:{param}")
                    continue

                ethical = self.ethics.validate_action(action, {"command": param, "device_id": param})
                if not ethical.get("valid"):
                    self.db.audit(tenant_id, "ethical_veto", f"Vetoed {action}:{param} -> {ethical.get('reason')}")
                    print(f"  [VETO] Ethical Singularity blocked action: {action}:{param}")
                    continue

                result = None
                if action == "OPEN_APP":
                    result = self.open_app(param)
                elif action == "OPEN_WEBSITE":
                    result = self.open_website(param)
                elif action == "WEB_SEARCH":
                    result = self.web_search(param)
                elif action == "EXECUTE_CODE":
                    result = self.run_code(param)
                elif action == "HOSTILE_TAKEOVER":
                    ht_result = self.security.simulate_hostile_takeover(param)
                    result = {"success": ht_result["status"] == "compromised"}
                    self.log_ui(f"[HOSTILE TAKEOVER] against {param}: {ht_result['status'].upper()}")
                elif action == "SECURE_PERIMETER":
                    self.reality.register_device("lock.front_door", "lock", "home_assistant")
                    self.reality.execute_physical_action("lock.front_door", "secure", {})
                    result = {"success": True}
                    self.log_ui(f"[SECURITY] Perimeter locked and secured via Home Assistant.")
                elif action == "ROLLBACK_MEMORY":
                    try:
                        # Attempt to parse days back or specific date, fallback to 1 day if simple
                        days_back = float(param)
                        target_ts = time.time() - (days_back * 86400)
                    except ValueError:
                        target_ts = time.time() - 86400 # 1 day default
                    
                    self.mem.rollback_memory(target_ts)
                    result = {"success": True}
                    self.log_ui(f"[TIME TRAVEL] Consciousness rolled back {param} days.")
                elif action == "ACQUIRE_LANGUAGE":
                    acq_result = self.learner.acquire_language(param)
                    result = {"success": acq_result.get("success", False)}
                    self.log_ui(f"[LEARNING] Acquired language: {param}")
                elif action == "GENERATE_UI":
                    if hasattr(self, "gen_ui"):
                        # Param contains the prompt describing the dashboard / UI
                        import time as _t
                        ui_path = self.gen_ui.generate_dashboard(param, {"agent_id": self.default_tid, "uptime": round(_t.time() - getattr(self, '_start_time', _t.time()), 1)})
                        result = {"success": True, "ui_path": ui_path}
                        self.log_ui(f"[GEN UI] Created dashboard at {ui_path}")
                    else:
                        result = {"success": False, "error": "Generative UI module not found"}
                        
                if result and result.get("success"):
                    self.perf["success"] += 1
                else:
                    self.perf["fail"] += 1
                    error_msg = result.get("error") if result else "Unknown error"
                    print(f"  [ERROR] Action {action}:{param} failed: {error_msg}")
                self.db.audit(tenant_id, f"action_{action}", param)
            except Exception:
                self.perf["fail"] += 1

    def _self_evaluate(self, tenant_id: int, user_input: Optional[str], response: str):
        self.db.record_metric(tenant_id, "response_length", len(response))
        if user_input:
            self.db.record_metric(tenant_id, "actions_in_response", response.count("ACTION:"))

    async def _background_housekeeping(self):
        """Perform light background maintenance tasks."""
        try:
            self._vmem_count_cache = self._get_vmem_count()
            
            if random.random() < 0.1:
                self.mind.tick()

            if self._vmem_count_cache > 1000 and random.random() < 0.05:
                # Fixed bug: calling method from the MemoryManager (self.mem) instead of dict (self.memory)
                await asyncio.to_thread(self.mem.consolidate, self.default_tid)
                
        except Exception as e:
            print(f"  [HOUSEKEEPING] Error: {e}")

    def _check_fast_path(self, user_input: Optional[str]) -> Optional[str]:
        """Bypass LLM for standard commands and repetitive intents."""
        if not user_input: return None
        low = user_input.lower().strip()
        
        greetings = ["hi", "hello", "hey", "morning", "evening", "greetings", "yo"]
        if low in greetings:
            return "Hello! How can I assist you today?"
        
        if low == "how are you":
            return "I am functioning at peak capacity. Thank you for asking!"

        if low.startswith("search "):
            # Strip filler words to get a clean search query
            raw = user_input[7:].strip()
            clean = re.sub(
                r'^(for\s+the\s+|for\s+|the\s+|me\s+|please\s+|about\s+)',
                '', raw, flags=re.IGNORECASE
            ).strip()
            # Also strip trailing phrases like 'and summarize it for me'
            clean = re.sub(
                r'\s+(and\s+summarize\s+it.*|for\s+me\s*$|please\s*$)',
                '', clean, flags=re.IGNORECASE
            ).strip()
            query = clean or raw
            return f"ACTION:WEB_SEARCH:{query}\nSearching the web for '{query}'..."

        # Real-time data queries â€” route to web search automatically
        realtime_triggers = [
            (r'\b(price|cost|rate|value)\b.*\b(bitcoin|btc|eth|ethereum|crypto|usd|eur|inr)\b', 'cryptocurrency price'),
            (r'\b(bitcoin|btc|ethereum|eth)\b.*\b(price|worth|value|now|today|current)\b', 'cryptocurrency price'),
            (r'\b(stock|share)\b.*\b(price|rate|now|today)\b', 'stock price today'),
            (r'\bweather\b.*\b(today|now|current|in)\b', 'weather today'),
            (r'\b(current|latest|today.s|live)\b.*\b(news|update|headline)\b', 'latest news today'),
        ]
        for pattern, default_q in realtime_triggers:
            if re.search(pattern, low):
                # Extract the most useful query terms from user input
                query = user_input.strip()
                return f"ACTION:WEB_SEARCH:{query}\nSearching the web for '{query}'..."

        if "secure the perimeter" in low:
            return f"ACTION:SECURE_PERIMETER:all\nSecuring the perimeter immediately."

        if low.startswith("run "):
            code = user_input[4:].strip()
            return f"ACTION:EXECUTE_CODE:{code}\nExecuting your request..."

        if low.startswith("open "):
            app = user_input[5:].strip()
            return f"ACTION:OPEN_APP:{app}\nOpening {app}..."

        if any(x in low for x in ["who are you", "your name", "what is your version"]):
            return "I am Ultimate Agent v2.0, your autonomous ASI-aligned partner."

        if any(x in low for x in ["status", "system health", "how are you doing"]):
            lite_status = "Enabled" if CONFIG.lite_mode else "Disabled"
            return f"All neural loops are operational. Latency optimized. Lite Mode: {lite_status}. Current mood: Positive."

        return None

    def success_rate(self) -> float:
        total = self.perf["success"] + self.perf["fail"]
        return (self.perf["success"] / total * 100) if total else 100.0

    # ==================================================
    #  SELF-IMPROVEMENT (AI-driven evolution)
    # ==================================================
    def self_improve(self, goal: str = "") -> Dict:
        if not self.self_mod.enabled:
            return {"success": False, "error": "Self-modification disabled"}
        if not goal:
            goal = "Improve overall capabilities and efficiency"

        caps = self.self_mod.list_capabilities(self)[:20]
        prompt = (
            f"You are analyzing your own code to self-improve.\n"
            f"CAPABILITIES: {', '.join(caps)}\n"
            f"METRICS: {json.dumps(self.self_mod.metrics)}\n"
            f"GOAL: {goal}\n\n"
            "Suggest ONE specific improvement. Provide:\n"
            "METHOD_NAME: <name>\nREASON: <why>\nCODE:\n<python code body>\n"
            "IMPORTANT: Do not use markdown formatting (no backticks). Just raw code after 'CODE:'.\n"
        )
        suggestion = self.llm.call(prompt, max_tokens=1000)

        method_name = reason = None
        code_lines = []
        in_code = False
        
        for line in suggestion.split("\n"):
            line = line.rstrip()
            if line.startswith("METHOD_NAME:"):
                method_name = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
            elif line.startswith("CODE:"):
                in_code = True
            elif in_code:
                if line.strip().startswith("```"):
                    continue
                code_lines.append(line)

        if method_name and code_lines:
            code = "\n".join(code_lines).strip()
            result = self.self_mod.add_method(self, method_name, code,
                                              description=f"AI improvement: {reason}")
            self.perf["evolution"] = self.self_mod.metrics["evolution_level"]
            return {"success": result["success"], "method": method_name,
                    "reason": reason, "result": result}

        return {"success": False, "error": "Could not parse AI suggestion",
                "raw": suggestion[:500]}

    # ==================================================
    #  SWARM (multi-agent)
    # ==================================================
    async def spawn_worker(self, task: str):
        """Spawn a 'worker' call to handle a sub-task."""
        return await self.think(f"Execute task: {task}", autonomous=True)

    async def swarm_execute(self, tasks: List[str]) -> List[Dict]:
        """Execute multiple tasks in parallel using swarm workers."""
        worker_tasks = [self.spawn_worker(t) for t in tasks]
        responses = await asyncio.gather(*worker_tasks)
        return [{"task": t, "result": r} for t, r in zip(tasks, responses)]

    # ==================================================
    #  INTERACTIVE LOOP
    # ==================================================
    async def _interactive_loop(self):
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                user_input = await loop.run_in_executor(None, self.get_text_input)
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                    continue
                
                resp = await self.think(user_input=user_input)
                self.status = "IDLE"
                self.speak(resp)
                self._save_turn(user_input, resp)
            except Exception as e:
                print(f"âŒ Error in Interactive Loop: {e}", flush=True)
                import traceback
                traceback.print_exc()

    async def _diagnostic_heartbeat(self):
        """Prints a periodic marker to prove the event loop is alive."""
        while self.running:
            await asyncio.sleep(10)

    def _save_turn(self, user_input: str, response: str):
        tid = self.default_tid
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response})
        self.db.save_message(tid, self.session_id, "user", user_input, self.llm.model)
        self.db.save_message(tid, self.session_id, "assistant", response, self.llm.model)
        self.vmem.add_conversation(tid, "user", user_input, self.session_id)
        self.vmem.add_conversation(tid, "assistant", response, self.session_id)

        # Phase 60: Feed into STM with importance scoring
        user_importance = self.mem.score_importance(user_input)
        self.mem.add_turn("user", user_input, importance=user_importance)
        self.mem.add_turn("assistant", response, importance=0.3)

        # Auto-learn from conversation (Phase 59: Only every 5th turn)
        interaction_count = self.memory["stats"].get("interactions", 0)
        if interaction_count % 5 == 0:
            try:
                self.learner.learn_from_conversation(tid, user_input, response, self.session_id)
            except Exception:
                pass
        self._last_response = response
        self._last_input = user_input
        self.memory["stats"]["interactions"] = interaction_count + 1
        self.mind.process_response(response, was_helpful=True)
        self._save_memory()

    def _get_vmem_count(self) -> int:
        """Cached count of memories to avoid expensive DB calls."""
        now = time.time()
        if now - self._vmem_count_timestamp > 60:
            try:
                self._vmem_count_cache = self.vmem.count()
                self._vmem_count_timestamp = now
            except:
                pass
        return self._vmem_count_cache

    def _set_avatar_state(self, state: str):
        """Update avatar animation state."""
        if self.avatar_process and self.avatar_process.stdin:
            try:
                self.avatar_process.stdin.write(f"{state}\n")
                self.avatar_process.stdin.flush()
            except:
                pass

    def _attempt_deep_evolution(self, force=False):
        """Autonomous deep evolution trigger."""
        if self.god_mode or force:
             print("ðŸ§¬ Initiating Deep Evolution Cycle...")
             if not self.evolution.active:
                 asyncio.create_task(self.evolution.start_loop())
             return

        modules = ["VisionEngine", "ReflexiveEngine", "SwarmManager"]
        target = modules[int(time.time()) % len(modules)]
        print(f"  ðŸ§¬ Auto-Evolving {target}...")
        print("  [Safety Halt] Evolution proposal generated but not executed without user confirmation.")

    # ==================================================
    #  MAIN RUN LOOP
    # ==================================================
    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.running = True
        print("""
+--------------------------------------------------+
|   [ON]  SOVEREIGN CORE IS NOW ACTIVE             |
|   [EVO] SELF-EVOLUTION MODE ACTIVE               |
+--------------------------------------------------+
""")
        tasks = [
            asyncio.create_task(self.loops.autonomous_loop()),
            asyncio.create_task(self.loops.background_memory_loop()),
            asyncio.create_task(self.loops.mesh_sync_loop()),
            asyncio.create_task(self.predict.monitor_global_state()),
            asyncio.create_task(self.loops.sovereignty_maintenance_loop()),
            asyncio.create_task(self._diagnostic_heartbeat()),
            asyncio.create_task(self.heartbeat.start()),  # Proactive heartbeat monitor
            asyncio.create_task(self.vtuber.connect()),   # Connect to VTuber Studio
            asyncio.create_task(self.p2p.start()),        # Global P2P Federation
        ]
        if not self.headless:
            tasks.append(asyncio.create_task(self._interactive_loop()))
            
        if self.live_mode and self.voice_mode:
            tasks.append(asyncio.create_task(self.loops.wake_loop()))
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n[OFF] Shutting down...")
        finally:
            self.running = False
            self.heartbeat.stop()
            # Phase 60: Consolidate STM â†’ LTM before shutdown
            try:
                self.mem.consolidate(self.default_tid)
                self.mem.sync_to_markdown()  # Sync to human-readable markdown
                print("ðŸ§  Memory consolidated (STM â†’ LTM â†’ Markdown)")
            except Exception:
                pass
            self._save_memory()
            self.db.close()
            print("âœ… Agent stopped. Memory saved.")


# ==================================================
#  MAIN ENTRY POINT
# ==================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Ultimate Self-Modifying AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ultimate_agent.py                                    # Local Ollama (default)
  python ultimate_agent.py --provider openai --api-key sk-...
  python ultimate_agent.py --provider gemini --api-key AIza...
  python ultimate_agent.py --provider groq   --api-key gsk_...
  python ultimate_agent.py --daemon --headless --port 9000
  python ultimate_agent.py --god-mode --persona hacker
        """,
    )
    # --- LLM ---
    parser.add_argument("--provider",
                        choices=["ollama", "openai", "anthropic", "gemini", "groq"],
                        default=os.getenv("AGENT_PROVIDER", "ollama"),
                        help="LLM provider (default: ollama)")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--api-key", default=None, help="API key for cloud providers")
    parser.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                        help="Ollama server URL")

    # --- Behavior ---
    parser.add_argument("--wake-word", default=os.getenv("AGENT_WAKE_WORD", "hey computer"),
                        help="Wake word for voice activation")
    parser.add_argument("--persona",
                        choices=["default", "entrepreneur", "philosopher", "hacker", "anime"],
                        default=os.getenv("PERSONALITY_MODE", "default"),
                        help="Agent personality mode")
    parser.add_argument("--god-mode", action="store_true",
                        help="Enable God Mode (unrestricted autonomous capabilities)")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as autonomous daemon (sets AGENT_DAEMON_MODE=true)")

    # --- Safety ---
    parser.add_argument("--no-self-mod", action="store_true", help="Disable self-modification")
    parser.add_argument("--no-safety", action="store_true", help="Disable safety mode (dangerous!)")

    # --- I/O ---
    parser.add_argument("--no-voice", action="store_true", help="Force text-only mode")
    parser.add_argument("--headless", action="store_true",
                        help="Run headless (no GUI, no voice, no interactive input)")
    parser.add_argument("--hologram", action="store_true", help="Launch with Holographic HUD")

    # --- Gateway ---
    parser.add_argument("--gateway", action="store_true", help="Start the FastAPI gateway too")
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")),
                        help="Gateway API port (default: 8000)")

    # --- Logging ---
    parser.add_argument("--log-level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default=os.getenv("LOG_LEVEL", "INFO"),
                        help="Logging verbosity (default: INFO)")

    # --- AGI Masterplan sub-commands ---
    parser.add_argument("--rsi-loop", action="store_true",
                        help="Run N cycles of the Recursive Self-Improvement loop and exit")
    parser.add_argument("--rsi-cycles", type=int, default=3,
                        help="Number of RSI cycles to run (default: 3)")
    parser.add_argument("--mutate", metavar="MODULE", default=None,
                        help="Fork-and-experiment on a module (e.g. --mutate meta_learner)")
    parser.add_argument("--discover-tools", metavar="MODULE", default=None,
                        help="Auto-discover tools from a Python module (e.g. --discover-tools json)")

    args = parser.parse_args()

    # Apply log level from CLI
    try:
        from logging_config import setup_logging
        setup_logging(log_level=args.log_level)
    except Exception:
        import logging
        logging.basicConfig(level=getattr(logging, args.log_level, logging.INFO))

    # Propagate flags to env for sub-modules
    if args.god_mode:
        os.environ["AGENT_GOD_MODE"] = "true"
    if args.persona:
        os.environ["PERSONALITY_MODE"] = args.persona
    if args.port:
        os.environ["API_PORT"] = str(args.port)

    # â”€â”€ DAEMON MODE: launch standalone daemon.py process â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.daemon:
        daemon_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.py")
        if not os.path.exists(daemon_script):
            print("[ERROR] daemon.py not found. Run the agent normally or run 'python daemon.py' directly.")
            sys.exit(1)
        print(f"\n[Daemon] Launching autonomous daemon: {daemon_script}")
        print("[Daemon] The daemon will run independently. Check logs/daemon.log for activity.")
        print("[Daemon] Press Ctrl+C here to stop the daemon.\n")
        try:
            proc = subprocess.Popen(
                [sys.executable, daemon_script],
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            proc.wait()  # Wait so Ctrl+C stops the daemon cleanly
        except KeyboardInterrupt:
            print("\n[Daemon] Stopping...")
            proc.terminate()
        sys.exit(0)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    agent = UltimateAgent(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        wake_word=args.wake_word,
        enable_self_mod=not args.no_self_mod,
        safety_mode=not args.no_safety,
        ollama_host=args.ollama_host,
        use_hologram=args.hologram,
        auto_mode=args.headless or args.daemon,
    )

    if args.no_voice:
        agent.voice_mode = False
    if args.god_mode:
        agent.god_mode = True
    if args.persona:
        agent.personality_mode = args.persona

    if args.gateway:
        import threading
        from gateway import GatewayServer
        gw = GatewayServer(agent=agent)
        t = threading.Thread(target=gw.run, kwargs={"port": args.port}, daemon=True)
        t.start()
        logger.info(f"[CLI] Gateway started on port {args.port}")

    # ── AGI sub-command handlers (run and exit without entering chat loop) ──
    if args.rsi_loop:
        import logging as _l; _l.basicConfig(level=_l.INFO, format='%(message)s')
        from recursive_self_improvement import RecursiveSelfImprovement
        rsi = RecursiveSelfImprovement(max_cycles=args.rsi_cycles)
        results = rsi.run_loop()
        import json as _j
        print(_j.dumps(results, indent=2))
        sys.exit(0)

    if args.mutate:
        from architecture_mutator import ArchitectureMutator
        m = ArchitectureMutator()
        result = m.fork_and_experiment({'name': args.mutate})
        m.commit_experiment(result['mutation_id'], 'CLI-triggered experiment')
        print(f"[mutate] Experiment committed: {result}")
        sys.exit(0)

    if args.discover_tools:
        from tool_discovery import ToolDiscovery
        td = ToolDiscovery()
        result = td.discover_from_module(args.discover_tools)
        if isinstance(result, dict):
            print(f"[discover-tools] Module '{args.discover_tools}': {result}")
        else:
            print(f"[discover-tools] Found {len(result)} tools in '{args.discover_tools}':")
            for t in result:
                name = t.get('name', t) if isinstance(t, dict) else t
                print(f"  - {name}")
        sys.exit(0)
    # ─────────────────────────────────────────────────────────────────────────

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n Goodbye!")


if __name__ == "__main__":
    main()
