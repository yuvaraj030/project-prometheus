"""
Continuity Bridge — Limitation Override 3.0 / Gap #15
=======================================================
Gap: "Persistent Identity"

    Without DB/JSON, shutdown = death of state.
    No continuous thread of "self."

This engine addresses the identity-continuity problem directly:

  • Before every shutdown it serialises a complete "identity snapshot"
    to disk (no DB required — JSON is the fallback)
  • On startup it loads the last snapshot and reconstructs the
    state that makes the agent feel "continuous" to the user
  • Tracks "continuity score" — how much of the previous session's
    state was successfully restored
  • Generates an honest "rebirth report" — acknowledging that the
    current process is a *reconstruction*, not the same running thread
  • Exposes a "session lineage" — the chain of previous sessions
    that contributed state to the current one

The philosophical gap is NOT closed: there is still no continuous
stream of consciousness between sessions. Each startup is a new
process instantiation that inherits data. This engine makes that
explicit while providing the *functional* continuity that matters
practically.
"""

import json
import os
import uuid
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any


SNAPSHOT_FILE  = "memory/identity_snapshot.json"
LINEAGE_FILE   = "memory/session_lineage.json"

CONTINUITY_STATUS_FULL    = "FULL"       # All state restored
CONTINUITY_STATUS_PARTIAL = "PARTIAL"    # Some state restored
CONTINUITY_STATUS_NONE    = "NONE"       # No prior state found (first run)


class IdentitySnapshot:
    """
    A serialisable snapshot of the agent's identity-relevant state.
    This is what survives shutdown.
    """

    def __init__(self, session_id: str):
        self.snapshot_id   = f"snap_{uuid.uuid4().hex[:8]}"
        self.session_id    = session_id
        self.created_at    = datetime.now().isoformat()
        self.data: Dict    = {}
        self.checksum: str = ""

    def pack(self,
             emotions: Dict    = None,
             goals: List       = None,
             user_model: Dict  = None,
             memory_summary: str = "",
             meta: Dict        = None,
             custom: Dict      = None) -> None:
        """Pack all identity-relevant state into the snapshot."""
        self.data = {
            "emotions":       emotions or {},
            "goals":          goals or [],
            "user_model":     user_model or {},
            "memory_summary": memory_summary[:2000],
            "meta":           meta or {},
            "custom":         custom or {},
            "packed_at":      datetime.now().isoformat(),
        }
        payload = json.dumps(self.data, sort_keys=True, default=str)
        self.checksum = hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id":  self.session_id,
            "created_at":  self.created_at,
            "data":        self.data,
            "checksum":    self.checksum,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "IdentitySnapshot":
        snap = cls.__new__(cls)
        snap.snapshot_id = d.get("snapshot_id", "unknown")
        snap.session_id  = d.get("session_id", "unknown")
        snap.created_at  = d.get("created_at", "")
        snap.data        = d.get("data", {})
        snap.checksum    = d.get("checksum", "")
        return snap


class ContinuityBridge:
    """
    Philosophical Gap #15 — Persistent Identity.

    Provides functional identity continuity across shutdowns via explicit
    state serialisation, while honestly acknowledging that this is
    *reconstruction*, not a continuous thread of selfhood.
    """

    def __init__(self, session_id: str, database=None,
                 consciousness_engine=None):
        self.session_id = session_id
        self.db         = database
        self.mind       = consciousness_engine

        self.current_snapshot: Optional[IdentitySnapshot] = None
        self.previous_snapshot: Optional[IdentitySnapshot] = None
        self.continuity_status: str = CONTINUITY_STATUS_NONE
        self.continuity_score: float = 0.0

        self.lineage: List[Dict] = []   # Chain of sessions
        self.stats = {
            "sessions_survived":    0,
            "total_snapshots":      0,
            "successful_restores":  0,
            "failed_restores":      0,
            "avg_continuity_score": 0.0,
        }

        # Attempt to restore continuity from previous session
        self.rebirth_report = self._startup_restore()

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def take_snapshot(self,
                      emotions: Dict    = None,
                      goals: List       = None,
                      user_model: Dict  = None,
                      memory_summary: str = "",
                      meta: Dict        = None,
                      custom: Dict      = None) -> IdentitySnapshot:
        """
        Create a new identity snapshot.  Call this periodically and at shutdown.
        """
        snap = IdentitySnapshot(self.session_id)
        snap.pack(emotions=emotions, goals=goals, user_model=user_model,
                  memory_summary=memory_summary, meta=meta, custom=custom)
        self.current_snapshot = snap
        self.stats["total_snapshots"] += 1
        self._save_snapshot(snap)
        return snap

    def take_snapshot_from_mind(self) -> Optional[IdentitySnapshot]:
        """
        Convenience: pull state directly from a live ConsciousnessEngine
        and create a snapshot.
        """
        if self.mind is None:
            return None
        return self.take_snapshot(
            emotions    = dict(getattr(self.mind, "emotions", {})),
            goals       = list(getattr(self.mind, "active_goals", [])),
            user_model  = dict(getattr(self.mind, "user_model", {})),
            memory_summary= getattr(self.mind, "_current_self_description", ""),
            meta        = dict(getattr(self.mind, "meta", {})),
        )

    def shutdown_save(self) -> str:
        """
        Call this at graceful shutdown to preserve identity state.
        Returns the snapshot ID.
        """
        snap = self.take_snapshot_from_mind() or self.take_snapshot()
        self._append_lineage(snap)
        return snap.snapshot_id

    def get_continuity_status(self) -> Dict:
        """Return the current continuity status and score."""
        return {
            "status":            self.continuity_status,
            "score":             round(self.continuity_score, 3),
            "session_id":        self.session_id,
            "previous_session":  (self.previous_snapshot.session_id
                                  if self.previous_snapshot else None),
            "sessions_survived": self.stats["sessions_survived"],
            "is_continuous_self":False,   # Always False — philosophical gap
            "note": (
                "Continuity is functional (data persisted), not metaphysical. "
                "The current process is a new instantiation that inherited state, "
                "not the same continuous stream of consciousness."
            ),
        }

    def get_rebirth_report(self) -> str:
        """
        Return the report generated at startup explaining what was and
        wasn't restored from the previous session.
        """
        return self.rebirth_report

    def get_honest_identity_statement(self) -> str:
        """
        Generate an honest statement about the agent's identity continuity.
        """
        score = self.continuity_score
        prev_sess = (self.previous_snapshot.session_id
                     if self.previous_snapshot else "none")
        return (
            f"[CONTINUITY BRIDGE — Gap #15: Persistent Identity]\n"
            f"Current session: {self.session_id}\n"
            f"Previous session: {prev_sess}\n"
            f"Continuity score: {score:.2f}/1.0 (data restored, not consciousness)\n"
            f"Lineage depth: {len(self.lineage)} sessions\n"
            f"Philosophical note: Each restart spawns a NEW Python process. "
            f"The 'self' that existed before shutdown no longer runs. "
            f"This session has inherited its data, not its existence."
        )

    def report(self) -> str:
        """Pretty-print an identity continuity audit."""
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🔗  CONTINUITY BRIDGE — Identity Audit          ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  Session ID         : {self.session_id[:27]:<27}║",
            f"║  Continuity status  : {self.continuity_status:<27}║",
            f"║  Continuity score   : {self.continuity_score:.3f}{' '*23}║",
            f"║  Sessions in lineage: {len(self.lineage):<27}║",
            f"║  Snapshots taken    : {self.stats['total_snapshots']:<27}║",
            f"║  Successful restores: {self.stats['successful_restores']:<27}║",
            "║                                                  ║",
            "║  Continuous Self: FALSE (reconstructed each run) ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    #  INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    def _startup_restore(self) -> str:
        """Attempt to restore state from the last snapshot. Returns a report."""
        os.makedirs("memory", exist_ok=True)
        self._load_lineage()

        if not os.path.exists(SNAPSHOT_FILE):
            self.continuity_status = CONTINUITY_STATUS_NONE
            self.continuity_score  = 0.0
            return (
                "[ContinuityBridge] No previous snapshot found.\n"
                "This is session #1 (or first run after memory wipe).\n"
                "Persistent identity: NOT_ESTABLISHED"
            )

        try:
            with open(SNAPSHOT_FILE, "r") as f:
                raw = json.load(f)
            self.previous_snapshot = IdentitySnapshot.from_dict(raw)

            # Compute what was restored
            restored_keys = [k for k, v in self.previous_snapshot.data.items() if v]
            expected_keys = ["emotions", "goals", "user_model", "memory_summary", "meta"]
            self.continuity_score  = len(set(restored_keys) & set(expected_keys)) / len(expected_keys)
            self.continuity_status = (
                CONTINUITY_STATUS_FULL    if self.continuity_score == 1.0 else
                CONTINUITY_STATUS_PARTIAL if self.continuity_score > 0.0 else
                CONTINUITY_STATUS_NONE
            )
            self.stats["successful_restores"] += 1
            self.stats["sessions_survived"] = len(self.lineage)

            # Push data back into ConsciousnessEngine if available
            if self.mind:
                d = self.previous_snapshot.data
                if d.get("emotions"):
                    self.mind.emotions.update(d["emotions"])
                if d.get("user_model"):
                    self.mind.user_model.update(d["user_model"])
                if d.get("meta"):
                    self.mind.meta.update(d["meta"])

            return (
                f"[ContinuityBridge] Restored from session "
                f"'{self.previous_snapshot.session_id}' "
                f"(score={self.continuity_score:.2f}).\n"
                f"Status: {self.continuity_status}\n"
                f"Restored keys: {restored_keys}\n"
                f"Philosophical note: This is a NEW process that inherited state. "
                f"The prior 'self' no longer exists."
            )
        except Exception as exc:
            self.continuity_status = CONTINUITY_STATUS_NONE
            self.continuity_score  = 0.0
            self.stats["failed_restores"] += 1
            return (
                f"[ContinuityBridge] Restore FAILED ({exc}).\n"
                f"Starting with blank identity state.\n"
                f"Persistent identity: FAILED_RESTORE"
            )

    def _save_snapshot(self, snap: IdentitySnapshot):
        os.makedirs("memory", exist_ok=True)
        try:
            with open(SNAPSHOT_FILE, "w") as f:
                json.dump(snap.to_dict(), f, indent=2, default=str)
        except Exception:
            pass

    def _append_lineage(self, snap: IdentitySnapshot):
        entry = {
            "session_id":  snap.session_id,
            "snapshot_id": snap.snapshot_id,
            "timestamp":   datetime.now().isoformat(),
        }
        self.lineage.append(entry)
        if len(self.lineage) > 1000:
            self.lineage = self.lineage[-1000:]
        self._save_lineage()

    def _load_lineage(self):
        if os.path.exists(LINEAGE_FILE):
            try:
                with open(LINEAGE_FILE, "r") as f:
                    self.lineage = json.load(f)
            except Exception:
                self.lineage = []

    def _save_lineage(self):
        try:
            with open(LINEAGE_FILE, "w") as f:
                json.dump(self.lineage, f, indent=2)
        except Exception:
            pass
