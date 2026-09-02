# -*- coding: utf-8 -*-
"""M5.governor — cognition-domain DLC (life-support assessment: ABMI 1.0 re-engineering of legacy lifesupport.py)

Role:
  - eight-dimension support levels: food/water/housing/clothing/transportation/medical care/economy/social status; stratified weights
    (survival layer...)"""
from __future__ import annotations
from typing import Any, Dict
 
LSA_DIMENSIONS = ("food", "water", "housing", "clothing",
                  "transportation", "medical care", "economy", "social status")
LSA_LAYER_WEIGHT = {"food": 2.0, "water": 2.0, "housing": 2.0,
                    "clothing": 1.5, "transportation": 1.5, "medical care": 1.5,
                    "economy": 1.0, "social status": 0.8}
LSA_BASELINE_REGRESSION = 0.005                 # baseline regression rate/day (loss faster than gain)
LSA_STRESS_CIDX_LOW = (0.6, 7.0, (0.05, 0.10))   # SSE>0.6 for 7 days -> CIdx baseline+
LSA_STRESS_CIDX_HIGH = (0.8, 30.0, (0.10, 0.20))  # SSE>0.8 for 30 days -> CIdx baseline+
LSA_ODP_NUDGES = {"D49": 0.5, "D54": -0.5, "D57": -0.5, "D53": 0.5}  # low economy -> ODP fine-tune
# upbringing keywords -> eight-dimension baseline (legacy _BACKGROUND_LSA; card upbringing free text self-decoded)
_BACKGROUND_LSA = {
    "turbulent times": {"food": 0.35, "water": 0.5, "housing": 0.35,
                        "economy": 0.4, "social status": 0.5},
    "impoverished": {"food": 0.35, "economy": 0.3, "housing": 0.5},
    "wealthy": {"food": 0.9, "economy": 0.9, "housing": 0.9},
    "military service": {"housing": 0.55, "social status": 0.6},
    "scholarly family": {"economy": 0.7, "social status": 0.7},
}
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class LifeSupportAssessmentModule:
    """M5 life-support assessment: outputs the social-pressure index SSE and a modulation vector; pure local computation."""
 
    def __init__(self, log: Any, declaration: dict = None) -> None:
        self.log = log
        decl = declaration or {}
        # per-dimension support level [0,1], 1=fully supported; default 0.7 (neutral, slightly stable)
        self.levels = {d: _clamp(float(decl.get(d, 0.7))) for d in LSA_DIMENSIONS}
        # upbringing keywords -> baseline (legacy _decode_life_card; explicitly declared dimensions take priority)
        upbringing = str(decl.get("upbringing", ""))
        for kw, patch in _BACKGROUND_LSA.items():
            if kw in upbringing:
                for d, v in patch.items():
                    if d not in decl:
                        self.levels[d] = _clamp(float(v))
        self.baselines = dict(self.levels)                      # upbringing sets the baseline
        self._stress_days_low = 0.0                             # days with SSE>0.6
        self._stress_days_high = 0.0                            # days with SSE>0.8
        self._last_valence_contrib = 0.0                        # own last contribution to the shared channel (idempotent)
 
    # ---- social pressure index (Engel-pressure-style stratified weighting) ----
    def compute_stress_index(self) -> float:
        num, den = 0.0, 0.0
        for d in LSA_DIMENSIONS:
            w = LSA_LAYER_WEIGHT[d]
            num += w * (1.0 - self.levels[d])
            den += w
        return _clamp(num / den)
 
    # ---- event write (service port m5.apply_event; positive slow, negative fast) ----
    def apply_event(self, tick: int, dimension: str, delta: float,
                    reason: str = "") -> None:
        if dimension not in LSA_DIMENSIONS:
            return
        if delta > 0:
            delta *= 0.4                                        # positive events rise slowly
        self.levels[dimension] = _clamp(self.levels[dimension] + delta)
        self.log.record(tick, "M5.life_support", "event",
                        f"{dimension}{delta:+.2f} -> {self.levels[dimension]:.2f} "
                        f"{reason}")
 
    # ---- background maintenance: baseline regression + sustained high-pressure timer -> CIdx baseline bias (with M3) ----
    def background_maintenance(self, tick: int, dt_minutes: float) -> float:
        dt_days = dt_minutes / (24.0 * 60.0)
        for d in LSA_DIMENSIONS:
            cur, base = self.levels[d], self.baselines[d]
            step = LSA_BASELINE_REGRESSION * dt_days
            if cur < base:
                self.levels[d] = min(base, cur + step)
            elif cur > base:
                self.levels[d] = max(base, cur - step)
        sse = self.compute_stress_index()
        self._stress_days_low = (self._stress_days_low + dt_days
                                 if sse > LSA_STRESS_CIDX_LOW[0] else 0.0)
        self._stress_days_high = (self._stress_days_high + dt_days
                                  if sse > LSA_STRESS_CIDX_HIGH[0] else 0.0)
        if self._stress_days_high > LSA_STRESS_CIDX_HIGH[1]:
            return sum(LSA_STRESS_CIDX_HIGH[2]) / 2.0
        if self._stress_days_low > LSA_STRESS_CIDX_LOW[1]:
            return sum(LSA_STRESS_CIDX_LOW[2]) / 2.0
        return 0.0
 
    # ================= P1 hook =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        cidx_bias = self.background_maintenance(tick, float(data.get("dt", 0.0)))
        sse = self.compute_stress_index()
        lv = self.levels
        # ---- publish: legacy keys auto-mirrored to sys.* via the contract mirror (kernel untouched) ----
        board.publish("M5.governor.social_support", 1.0 - sse)
        board.publish("M5.governor.baseline_bias", cidx_bias)   # M3 board read
        board.publish("M5.governor.levels", dict(lv))
        # life-support flatline (clinical death): all dimensions collapsed. Published every tick (neutral False to avoid dangling)
        board.publish("M5.life_support.flatline",
                      all(v <= 0.05 for v in lv.values()))
        # ---- soft keys read directly by the kernel: rewritten every tick (neutral values to prevent residue; exclusive channel, no conflict) ----
        board.write_knob("knob.food_check_weight_mult",
                         2.0 if lv["food"] < 0.4 else 1.0, owner="M5.governor")
        board.write_knob("knob.sse_risk_bias",
                         0.4 if lv["economy"] < 0.4 else 0.0, owner="M5.governor")
        board.write_knob("knob.politeness_bias",
                         0.3 if lv["social status"] < 0.4 else 0.0,
                         owner="M5.governor")
        # ---- shared valence channel: only own component is archived (merged when M3/M4 rebuild the channel later this tick);
        # the shared key is never written directly — direct writes face an overwrite-vs-cross-tick-accumulation dilemma
        contrib = -0.1 if lv["social status"] < 0.4 else 0.0
        board.write_knob("knob.m5.valence_contrib", contrib, owner="M5.governor")
        self._last_valence_contrib = contrib
        # ---- archived soft keys (no kernel consumer wired; DLCs pick up themselves) ----
        board.write_knob("knob.m5.hunger_threshold_mult",
                         0.7 if lv["food"] < 0.4 else 1.0, owner="M5.governor")
        board.write_knob("knob.m5.ssm_baseline_bias",
                         (15.0 + 10.0 * (1.0 - lv["housing"]))
                         if lv["housing"] < 0.4 else 0.0, owner="M5.governor")
        board.write_knob("knob.m5.sleep_quality_mult",
                         0.75 if lv["housing"] < 0.4 else 1.0, owner="M5.governor")
        board.write_knob("knob.m5.apology_bias",
                         0.3 if lv["social status"] < 0.4 else 0.0,
                         owner="M5.governor")
        board.write_knob("knob.m5.self_disclosure_bias",
                         -0.3 if lv["social status"] < 0.4 else 0.0,
                         owner="M5.governor")
        if lv["economy"] < 0.4:                                 # low economy -> ODP fine-tune archive
            board.publish("M5.governor.odp_nudges", dict(LSA_ODP_NUDGES))
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"levels": dict(self.levels), "baselines": dict(self.baselines),
                "stress_days_low": self._stress_days_low,
                "stress_days_high": self._stress_days_high,
                "last_valence_contrib": self._last_valence_contrib}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        for d in LSA_DIMENSIONS:
            if d in (snap.get("levels") or {}):
                self.levels[d] = _clamp(float(snap["levels"][d]))
            if d in (snap.get("baselines") or {}):
                self.baselines[d] = _clamp(float(snap["baselines"][d]))
        self._stress_days_low = float(snap.get("stress_days_low", 0.0))
        self._stress_days_high = float(snap.get("stress_days_high", 0.0))
        self._last_valence_contrib = float(snap.get("last_valence_contrib", 0.0))
 
    def smoke(self) -> bool:
        return all(0.0 <= v <= 1.0 for v in self.levels.values())
 
    def invariants(self) -> bool:
        return (all(0.0 <= v <= 1.0 for v in self.levels.values())
                and all(0.0 <= v <= 1.0 for v in self.baselines.values())
                and self._stress_days_low >= 0.0 and self._stress_days_high >= 0.0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"SSE": round(self.compute_stress_index(), 3),
                "levels": {d: round(v, 2) for d, v in self.levels.items()},
                "sustained_high_pressure_days": round(self._stress_days_low, 1)}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> LifeSupportAssessmentModule:
        engine = LifeSupportAssessmentModule(ctx.log, ctx.k.card.life_support)
        engine._board = ctx.board
        return engine
 
    def bind(inst: LifeSupportAssessmentModule, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m5.apply_event", inst.apply_event)      # event write port
        return {
            "P1_body": inst.on_body,
            "report": inst.report,
        }
 
    return {
        "module_id": "M5.governor",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain (governance assessment)
        "contract_keys": ("sys.social_support",),                   # contract key committed write
        "gear": {
            "P1_body": {"every": 1, "trigger": None},               # resident activation
        },
        "priorities": {"P1_body": 5},                               # before M3 (10): component archived first
        "factory": factory,
        "bind": bind,
        "provides": ("sys.social_support", "m5.apply_event"),
        "requires": {},
        "report_key": "sse",
        "snapshot_label": "m5_lifesupport",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
