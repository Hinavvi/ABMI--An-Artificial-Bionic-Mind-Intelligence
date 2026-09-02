# -*- coding: utf-8 -*-
# =============================================================================
# trust.py — V8 governance: trust ledger (constitution, governance)
#
# trust ladder: normal 1.0 -> scout 0.8 -> hold 0.4 -> attenuate 0.2.
# audit rejections push down the ladder (single deweight entry at AuditAuthority); clean behavior rebounds
# (gradual recovery after 20 consecutive clean ticks, capped at the hold tier — the attenuate tier never auto-refills).
# =============================================================================
from __future__ import annotations
from typing import Any, Dict
 
LADDER: tuple = (
    ("normal", 1.0),
    ("scout", 0.8),
    ("hold", 0.4),
    ("attenuate", 0.2),
)
REJECT_STEP = 0.2        # deweight step per audit rejection
REBOUND_RATE = 0.001     # per-tick rebound rate
REBOUND_FLOOR = 0.4      # rebound ceiling tier (attenuate may rebound to frozen, never auto-refills)
REBOUND_CLEAN_MIN = 20   # minimum consecutive clean ticks required for rebound
 
 
class TrustLedger:
    """track per-module trust weights along the ladder. Unrecorded = full trust 1.0."""
 
    __slots__ = ("_weights", "_history", "_clean_ticks")
 
    def __init__(self) -> None:
        self._weights: Dict[str, float] = {}
        self._history: Dict[str, int] = {}
        self._clean_ticks: Dict[str, int] = {}
 
    # ---- weight and tier queries ----
    def weight(self, module_id: str) -> float:
        return self._weights.get(module_id, 1.0)
 
    def tier(self, module_id: str) -> str:
        w = self.weight(module_id)
        for name, level in LADDER:
            if w >= level - 1e-9:
                return name
        return LADDER[-1][0]
 
    def is_normal(self, module_id: str) -> bool:
        return self.tier(module_id) == "normal"
 
    # ---- reject — audit linkage (called solely by AuditAuthority) ----
    def reject(self, tick: int, module_id: str, reason: str = "") -> None:
        current = self.weight(module_id)
        self._weights[module_id] = max(LADDER[-1][1], current - REJECT_STEP)
        self._history[module_id] = self._history.get(module_id, 0) + 1
        self._clean_ticks[module_id] = 0  # rejection resets clean ticks
 
    # ---- clean-tick tracking (fed by the governance loop when audits pass) ----
    def mark_clean(self, module_id: str) -> None:
        self._clean_ticks[module_id] = self._clean_ticks.get(module_id, 0) + 1
 
    def clean_counts(self) -> Dict[str, int]:
        return dict(self._clean_ticks)
 
    # ---- rebound — gradual recovery after 20 consecutive clean ticks ----
    def rebound(self, tick: int, module_id: str) -> None:
        if self._clean_ticks.get(module_id, 0) < REBOUND_CLEAN_MIN:
            return
        w = self.weight(module_id)
        if w < REBOUND_FLOOR:
            self._weights[module_id] = min(REBOUND_FLOOR, w + REBOUND_RATE)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"weights": dict(self._weights),
                "rejects": dict(self._history),
                "clean_ticks": dict(self._clean_ticks)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        for key, attr in (("weights", "_weights"),
                          ("rejects", "_history"),
                          ("clean_ticks", "_clean_ticks")):
            v = snap.get(key)
            if isinstance(v, dict):
                setattr(self, attr, dict(v))
 
    def smoke(self) -> bool:
        return all(w >= LADDER[-1][1] - 1e-9 for w in self._weights.values())
 
    def invariants(self) -> bool:
        return (all(w <= 1.0 + 1e-9 for w in self._weights.values())
                and all(c >= 0 for c in self._clean_ticks.values()))
