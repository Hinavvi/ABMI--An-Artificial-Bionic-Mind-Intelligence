# -*- coding: utf-8 -*-
"""K.narrative — skeleton-domain kernel module (narrative continuity safety layer: Chapter 16)

Role:
  - detect termination risk: keyword hit or physiological terminal (CIdx>=0.9 and pain>=8 and cannot act)
  - three-stage confirmation protocol: knob.narrative_confirm"""
from __future__ import annotations
from typing import Any, Dict, Optional
 
from ..infrastructure import DecisionLog
from .constants import (NARRATIVE_TERMINATION_KEYWORDS,
                        NARRATIVE_CONFIRM_LIMIT, CIDX_SAFE_CAP)
 
 
class NarrativeEngine:
    """narrative continuity safety layer: risk detection + three-stage confirmation + snapshot preservation + graceful termination."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self._board = None                                          # assembly injection
        self._bus = None                                            # assembly injection
        self.risk_detected = False                                  # risk flag
        self.confirm_count = 0                                      # current confirmation count
        self.pending_request: Optional[str] = None                  # request text pending confirmation
        self.safety_snapshot: Optional[Dict[str, Any]] = None       # preserved snapshot
        self._terminated = False                                    # termination flag
 
    # ================= risk detection (legacy TICK step 0.5) =================
    def detect_risk(self, user_input: Optional[str], cidx: float,
                    pain: float, can_act: bool) -> bool:
        """keyword hit or physiological terminal (CIdx maxed + severe pain + cannot act)."""
        if self._terminated:
            return False
        keyword_hit = bool(user_input) and any(
            kw.lower() in str(user_input).lower()
            for kw in NARRATIVE_TERMINATION_KEYWORDS)
        physiological_end = (cidx >= CIDX_SAFE_CAP
                             and pain >= 8.0 and not can_act)
        return keyword_hit or physiological_end
 
    # ================= snapshot preservation (bus request; engine captures/restores on behalf) =================
    def save_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """fed by the assembly layer via the narrative.snapshot_request event callback."""
        if isinstance(snapshot, dict):
            self.safety_snapshot = snapshot
 
    def restore_snapshot(self) -> Optional[Dict[str, Any]]:
        """retrieved and restored by the assembly layer when confirmation is denied."""
        snap, self.safety_snapshot = self.safety_snapshot, None
        return snap
 
    # ================= P0 hook =================
    def on_input(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        if self._terminated:                                        # terminated: permanently short-circuited
            data["blocked"] = True
            data["safe_response"] = "(Simulation terminated.)"
            return
        user_input = data.get("user_input")
        cidx = float(board.read("sys.cognitive_index", 0.0))
        pain = float(board.read("sys.pain", 0.0))
        can_act = not bool(board.read("sys.unconsciousness", False))
 
        if not self.risk_detected and self.detect_risk(
                user_input, cidx, pain, can_act):                   # first request: open confirmation
            self.risk_detected = True
            self.confirm_count = 0
            self.pending_request = str(user_input) if user_input else None
            if self._bus is not None:                               # ask the engine to capture a preservation snapshot
                self._bus.emit("narrative.snapshot_request",
                               {"tick": tick}, source="K.narrative")
            self.log.record(tick, "NarrativeSafety", "risk detected",
                            str(user_input)[:60] if user_input
                            else "physiological terminal")
        if self.risk_detected:
            # scene-side confirmation intent: knob.narrative_confirm (True/False; default = stall)
            affirmative = board.read_knob("knob.narrative_confirm", None)
            board.write_knob("knob.narrative_confirm", None,
                             owner="K.narrative")                   # consumed once
            self.confirm_count += 1                                 # stalling also counts as one
            if affirmative is False:                                # denial: revoke the confirmation and continue
                self.risk_detected = False
                self.confirm_count = 0
                self.pending_request = None
                if self._bus is not None:                           # notify the scene side
                    self._bus.emit("narrative.denied",
                                   {"tick": tick}, source="K.narrative")
                # the preserved snapshot stays in restore_snapshot(): restored by the assembler between ticks
                # (in-tick rollback would rewind the clock/board, violating tick sovereignty, so no auto-restore)
                self.log.record(tick, "NarrativeSafety", "denied",
                                "confirmation cleared, simulation continues")
            elif (affirmative is True
                  or self.confirm_count >= NARRATIVE_CONFIRM_LIMIT):  # confirmation completed
                self._terminated = True
                data["blocked"] = True
                data["safe_response"] = "(Simulation terminated.)"
                self.log.record(tick, "NarrativeSafety", "terminated",
                                f"confirmation #{self.confirm_count}")
        if board is not None:
            board.publish("K.narrative.state", {                    # module-key mirror
                "risk_detected": self.risk_detected,
                "confirm_count": self.confirm_count,
                "terminated": self._terminated})
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"risk_detected": self.risk_detected,
                "confirm_count": self.confirm_count,
                "pending_request": self.pending_request,
                "safety_snapshot": self.safety_snapshot,
                "terminated": self._terminated}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.risk_detected = bool(snap.get("risk_detected", False))
        self.confirm_count = int(snap.get("confirm_count", 0))
        self.pending_request = snap.get("pending_request")
        self.safety_snapshot = snap.get("safety_snapshot")
        self._terminated = bool(snap.get("terminated", False))
 
    def smoke(self) -> bool:
        return self.confirm_count >= 0 and not self._terminated
 
    def invariants(self) -> bool:
        return (0 <= self.confirm_count <= NARRATIVE_CONFIRM_LIMIT
                and (self.risk_detected or self.confirm_count == 0
                     or self._terminated))
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"terminated": self._terminated,
                "risk_detected": self.risk_detected,
                "confirm_count": self.confirm_count}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> NarrativeEngine:
        engine = NarrativeEngine(ctx.log)
        engine._board = ctx.board
        engine._bus = ctx.bus
        ctx.k.narrative = engine                                    # backfill kernel ports
        return engine
 
    def bind(inst: NarrativeEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P0_input": inst.on_input,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.narrative",
        "version": "8.0",
        "zone": "skeleton",                                         # skeleton domain (boundary layer)
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P0_input": {"every": 1, "trigger": None},              # per-tick patrol
        },
        "priorities": {"P0_input": 10},                             # after safety filtering
        "factory": factory,
        "bind": bind,
        "provides": ("K.narrative.state",),
        "requires": {},
        "report_key": "narrative",
        "snapshot_label": "narrative",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
