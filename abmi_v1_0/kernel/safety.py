# -*- coding: utf-8 -*-
"""K.safety — skeleton-domain kernel module (content safety filter layer: Chapter 15)

Role:
  - P0 entry gatekeeping: user input passes rating filter before entering the engine
  - per persona-card narrative_boundary (boundary level) + CONTENT_RATING_LEVELS"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import CONTENT_RATING_LEVELS, CONTENT_CLASSIFIER, DEFAULT_SAFE_OUTPUT
 
 
class SafetyEngine:
    """content safety filter: rating judgment + out-of-bounds fusing; zero intervention when within bounds."""
 
    def __init__(self, card: Any, log: DecisionLog) -> None:
        self.card = card
        self.log = log
        self._board = None                                          # assembly injection
        self.last: Optional[Dict[str, Any]] = None                  # latest grading record
 
    # ================= grading (legacy classifier lookup table) =================
    def classify(self, text: str) -> Dict[str, Any]:
        """keyword hit -> take the highest severity level; exceeding the boundary level fuses."""
        text_l = (text or "").lower()
        hits: List[str] = []
        severity = 0                                                # highest matched severity level
        for tag, (sev, keywords) in CONTENT_CLASSIFIER.items():
            if any(kw.lower() in text_l for kw in keywords):
                hits.append(tag)
                severity = max(severity, int(sev))
        boundary = str(getattr(self.card, "narrative_boundary", "all ages")
                       or "all ages")
        boundary_rank = int(CONTENT_RATING_LEVELS.get(boundary, 0))  # boundary numeric level
        level = next((name for name, rank in CONTENT_RATING_LEVELS.items()
                      if rank == severity), "all ages")              # numeric level -> level name
        return {"level": level, "hits": tuple(hits),
                "boundary": boundary, "blocked": severity > boundary_rank}
 
    # ================= P0 hook =================
    def on_input(self, tick: int, data: Dict[str, Any]) -> None:
        verdict = self.classify(str(data.get("user_input", "")))
        self.last = {"tick": tick, **verdict}
        self.log.record(tick, "ContentSafetyFilter", "classify",
                        f"level={verdict['level']} blocked={verdict['blocked']}")
        if self._board is not None:
            self._board.publish("K.safety.last", self.last)         # module-key mirror
        if verdict["blocked"]:                                      # out of bounds -> fuse this tick
            data["blocked"] = True
            data["safe_response"] = DEFAULT_SAFE_OUTPUT
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"last": dict(self.last) if self.last else None}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if isinstance(snap, dict):
            self.last = dict(snap["last"]) if snap.get("last") else None
 
    def smoke(self) -> bool:
        return self.classify("hello")["blocked"] is False           # safe input is not fused
 
    def invariants(self) -> bool:
        if self.last is None:
            return True
        return self.last["level"] in CONTENT_RATING_LEVELS
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"last": self.last}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> SafetyEngine:
        engine = SafetyEngine(ctx.k.card, ctx.log)
        engine._board = ctx.board
        ctx.k.safety = engine                                       # backfill kernel ports
        return engine
 
    def bind(inst: SafetyEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P0_input": inst.on_input,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.safety",
        "version": "8.0",
        "zone": "skeleton",                                         # skeleton domain (boundary layer)
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P0_input": {"every": 1,
                         "trigger": lambda t, d: bool(d.get("user_input"))},
        },
        "priorities": {"P0_input": 0},                              # P0 runs first
        "factory": factory,
        "bind": bind,
        "provides": ("K.safety.last",),
        "requires": {},
        "report_key": "safety",
        "snapshot_label": "safety",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
