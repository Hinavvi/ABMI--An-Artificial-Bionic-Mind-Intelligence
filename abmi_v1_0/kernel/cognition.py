# -*- coding: utf-8 -*-
"""K.cognition — cognition-domain kernel module (Station 2: cognitive interpreter, 7.2)

Role:
  - interpretation pipeline: signal -> [T/F attribution] -> [S/N+novelty -> processing depth] -> [J/P time anchoring] -> perceptual fragment
  - T/F attribution text"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import (DEFAULT_COGNITIVE_ARBITRATION, DEFAULT_COGNITIVE_FALLBACK,
                        CATEGORY_OBJECTIVE_MAP, CATEGORY_OBJECTIVE_DEFAULT)
from .models import SignalSourceEntry, CognitiveFragment
 
 
class CognitionEngine:
    """cognitive interpreter: translates Station 1's winning signals into personalized perceptual fragments."""
 
    def __init__(self, log: DecisionLog,
                 tf_attribution: Optional[dict] = None) -> None:
        self.log = log
        self._tf_table = dict(DEFAULT_COGNITIVE_ARBITRATION)        # engine neutral default table
        if tf_attribution:
            self._tf_table.update(tf_attribution)                   # persona-card override
        self.alcohol_station2_cut = False                           # M4 L5: this station disconnected
 
    # ---- main pipeline (legacy compatibility surface) ----
    def execute_cognitive_mapping(self, tick: int, winners: list,
                                  letters: Dict[str, Optional[str]]) -> List[CognitiveFragment]:
        fragments = []
        for s in winners:
            if self.alcohol_station2_cut:                           # L5 disconnected: only shallow fragments remain
                frag = CognitiveFragment(
                    signal=s, attribution="(cognitive interpretation disconnected)",
                    depth_level="shallow", time_projection=None,
                    emotional_tag=s.theme_hint,
                    recommended_intent=CATEGORY_OBJECTIVE_MAP.get(
                        s.category, CATEGORY_OBJECTIVE_DEFAULT),
                    urgency=max(0, self._urgency(s) - 1))
            else:
                frag = CognitiveFragment(
                    signal=s,
                    attribution=self._cognitive_arbitrate(s, letters),
                    depth_level=self._processing_depth(s, letters),
                    time_projection=self._temporal_prediction(s, letters),
                    emotional_tag=s.theme_hint,
                    recommended_intent=CATEGORY_OBJECTIVE_MAP.get(
                        s.category, CATEGORY_OBJECTIVE_DEFAULT),
                    urgency=self._urgency(s))
            fragments.append(frag)
        self.log.record(tick, "biomimetic.Station-2", "cognitive interpretation",
                        [(f.signal.category, f.attribution, f.depth_level,
                          f.recommended_intent) for f in fragments])
        return fragments
 
    def _cognitive_arbitrate(self, s: SignalSourceEntry,
                             letters: Dict[str, Optional[str]]) -> str:
        """T/F attribution: T takes the objective item, F takes the self item, swing annotated as both."""
        pair = self._tf_table.get(s.category, DEFAULT_COGNITIVE_FALLBACK)
        tf = letters.get("TF")
        if tf == "T":
            return pair[0]
        if tf == "F":
            return pair[1]
        return f"{pair[0]} / {pair[1]}(wavering)"
 
    def _processing_depth(self, s: SignalSourceEntry,
                          letters: Dict[str, Optional[str]]) -> str:
        """S/N + novelty -> processing depth: S tends shallow, N tends deep, high novelty raises one level."""
        sn = letters.get("SN")
        high_novelty = s.novelty >= 0.5
        if sn == "S":
            return "mid" if high_novelty else "shallow"
        if sn == "N":
            return "deep" if high_novelty else "mid"
        return "mid(wavering)"
 
    def _temporal_prediction(self, s: SignalSourceEntry,
                             letters: Dict[str, Optional[str]]) -> Optional[str]:
        """J-type forward time projection; others have none."""
        if letters.get("JP") == "J":
            return f"forward projection: {s.category} means what comes next is..."
        return None
 
    def _urgency(self, s: SignalSourceEntry) -> int:
        """urgency: urgency flag 3; intensity >=0.8 -> 2; >=0.5 -> 1; otherwise 0."""
        if s.urgency_flag:
            return 3
        if s.raw_intensity >= 0.8:
            return 2
        if s.raw_intensity >= 0.5:
            return 1
        return 0
 
    # ================= P3 hook (V8 module surface) =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        self.alcohol_station2_cut = bool(                           # M4 soft keys
            self._board.read("sys.alcohol_station2_off", False))
        letters = self._board.read("K.persona.letters", {}) or {}   # persona-letter mirror
        fragments = self.execute_cognitive_mapping(
            tick, data.get("winners", ()), letters)
        data["fragments"] = fragments                               # -> Station 3 binding
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"tf_table": dict(self._tf_table),
                "alcohol_station2_cut": self.alcohol_station2_cut}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        if isinstance(snap.get("tf_table"), dict):
            self._tf_table = dict(snap["tf_table"])
        self.alcohol_station2_cut = bool(snap.get("alcohol_station2_cut", False))
 
    def smoke(self) -> bool:
        return isinstance(self._tf_table, dict) and bool(self._tf_table)
 
    def invariants(self) -> bool:
        return all(isinstance(v, tuple) and len(v) == 2
                   for v in self._tf_table.values())
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"station2_cut": self.alcohol_station2_cut}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> CognitionEngine:
        engine = CognitionEngine(ctx.log, ctx.k.card.tf_attribution)  # persona-card attribution override
        engine._board = ctx.board
        ctx.k.persona_if = engine                                   # backfill kernel ports
        return engine
 
    def bind(inst: CognitionEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P3_cognition": inst.on_cognition,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.cognition",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P3_cognition": {"every": 1,
                             "trigger": lambda t, d: bool(d.get("winners"))},  # no winner -> sleep
        },
        "priorities": {"P3_cognition": 20},                         # after competition, before binding
        "factory": factory,
        "bind": bind,
        "provides": (),
        "requires": {},
        "report_key": "cognition",
        "snapshot_label": "cognition",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
