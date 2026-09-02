# -*- coding: utf-8 -*-
"""M1.cycle — physiology-domain DLC (cyclic state modulation: ABMI 1.0 re-engineering of legacy cyclic.py)

Role:
  - activated by the persona-card cyclic_modulation declaration; never sleeps once active (autonomous cycle)"""
from __future__ import annotations
import math
from typing import Any, Dict
 
CYCLIC_PERIOD_DAYS = 28.0                                     # cycle length (days)
CYCLIC_PHASES = ("phase one", "phase two", "phase three", "phase four")
CYCLIC_PHASE_BOUNDARIES = (0.18, 0.46, 0.68, 0.93)            # phase boundary (progress ratio)
 
 
class CyclicStateModulator:
    """M1 cyclic modulation: sinusoidal superposition waves + four phases + exogenous suppression; pure local computation."""
 
    def __init__(self, log: Any, declaration: dict = None) -> None:
        self.log = log
        decl = declaration or {}
        self.active = bool(decl.get("enabled", False))            # card-declared activation
        self.day_in_cycle = float(decl.get("start_day", 0.0)) % CYCLIC_PERIOD_DAYS
        self.phase = CYCLIC_PHASES[0]
        self.cm_a = 0.5                                           # CM_A wave (phase-III peak)
        self.cm_b = 0.5                                           # CM_B wave (phase-IV peak)
        self.suppressed = False                                   # exogenous suppression flag
 
    # ---- cycle advance (P6 background maintenance) ----
    def advance(self, tick: int, dt_minutes: float) -> None:
        if not self.active or self.suppressed:
            return
        self.day_in_cycle = (self.day_in_cycle
                             + dt_minutes / (24.0 * 60.0)) % CYCLIC_PERIOD_DAYS
        progress = self.day_in_cycle / CYCLIC_PERIOD_DAYS
        self.cm_a = 0.5 + 0.5 * math.sin(2.0 * math.pi * (progress - 0.25))
        self.cm_b = 0.5 + 0.5 * math.sin(2.0 * math.pi * (progress - 0.62))
        b = CYCLIC_PHASE_BOUNDARIES
        phase = (CYCLIC_PHASES[0] if progress < b[0] else
                 CYCLIC_PHASES[1] if progress < b[1] else
                 CYCLIC_PHASES[2] if progress < b[2] else
                 CYCLIC_PHASES[3] if progress < b[3] else CYCLIC_PHASES[0])
        if phase != self.phase:
            self.log.record(tick, "M1.cycle", "phase switch",
                            f"{self.phase} -> {phase} (day {self.day_in_cycle:.1f})")
            self.phase = phase
 
    def suppress(self, tick: int, reason: str = "exogenous agent") -> None:
        if self.active and not self.suppressed:
            self.suppressed = True
            self.log.record(tick, "M1.cycle", "exogenous suppression", reason)
 
    # ---- modulation vector (produced in phase I/IV, zero otherwise) ----
    def modulation_vector(self) -> Dict[str, float]:
        mv = {"pain_bias": 0.0, "gut_mult": 1.0, "valence_bias": 0.0,
              "sleep_quality_mult": 1.0, "discharge_d9_sensitivity": 1.0,
              "temp_bias": 0.0, "ssm_baseline_bias": 0.0}
        if not self.active or self.suppressed:
            return mv
        if self.phase == "phase one":                     # low phase
            mv["pain_bias"] = 0.3 + 0.3 * (1.0 - self.cm_a)
            mv["gut_mult"] = 1.3
            mv["valence_bias"] = -(0.1 + 0.2 * (1.0 - self.cm_a))
            mv["sleep_quality_mult"] = 0.85
            mv["discharge_d9_sensitivity"] = 1.2
        elif self.phase == "phase four":                  # decline phase (incl. premenstrual segment)
            mv["temp_bias"] = 0.3 + 0.2 * self.cm_b
            mv["gut_mult"] = 0.8
            if self.cm_b > 0.6:                           # premenstrual segment
                mv["ssm_baseline_bias"] = 10.0 + 10.0 * self.cm_b
                mv["valence_bias"] = -(0.2 + 0.2 * self.cm_b)
        return mv
 
    # ================= P6 hook =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.advance(tick, float(data.get("dt", 0.0)))
        board = self._board
        if not self.active:
            return
        mv = self.modulation_vector()
        # soft keys already read by the kernel are written directly; valence_bias is a shared channel (jointly written by M3/M4/M5),
        # M1 only archives knob.m1.valence_bias, combined into the shared channel by M3 (anti-overwrite/anti-accumulation)
        board.write_knob("knob.gut_mult", mv["gut_mult"], owner="M1.cycle")
        board.write_knob("knob.d9_sensitivity",
                         mv["discharge_d9_sensitivity"], owner="M1.cycle")
        for key in ("pain_bias", "temp_bias", "ssm_baseline_bias",
                    "sleep_quality_mult", "valence_bias"):
            board.write_knob(f"knob.m1.{key}", mv[key], owner="M1.cycle")
        board.publish("M1.cycle.state", {                 # module-key mirror
            "phase": self.phase, "day": round(self.day_in_cycle, 2),
            "cm_a": round(self.cm_a, 3), "cm_b": round(self.cm_b, 3),
            "suppressed": self.suppressed})
        # PSM_D1 offer (legacy psm_d1_offer: (0.15, "cyclic"), resident while active)
        if self._columnar is not None:
            self._columnar.route_psm_d1_signal(tick, 0.15, "cyclic")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"active": self.active, "day": self.day_in_cycle,
                "phase": self.phase, "cm_a": self.cm_a, "cm_b": self.cm_b,
                "suppressed": self.suppressed}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.active = bool(snap.get("active", self.active))
        self.day_in_cycle = float(snap.get("day", 0.0))
        self.phase = str(snap.get("phase", CYCLIC_PHASES[0]))
        self.cm_a = float(snap.get("cm_a", 0.5))
        self.cm_b = float(snap.get("cm_b", 0.5))
        self.suppressed = bool(snap.get("suppressed", False))
 
    def smoke(self) -> bool:
        return 0.0 <= self.day_in_cycle < CYCLIC_PERIOD_DAYS
 
    def invariants(self) -> bool:
        return (0.0 <= self.cm_a <= 1.0 and 0.0 <= self.cm_b <= 1.0
                and self.phase in CYCLIC_PHASES)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"active": self.active, "phase": self.phase,
                "day": round(self.day_in_cycle, 1)}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> CyclicStateModulator:
        engine = CyclicStateModulator(ctx.log, ctx.k.card.cyclic_modulation)
        engine._board = ctx.board
        engine._columnar = ctx.k.columnar
        return engine
 
    def bind(inst: CyclicStateModulator, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m1.suppress", inst.suppress)            # exogenous suppression port
        return {
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "M1.cycle",
        "version": "1.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": (),                                        # writes knob.* soft keys only
        "gear": {
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P6_maintenance": 10},
        "factory": factory,
        "bind": bind,
        "provides": ("M1.cycle.state",),
        "requires": {},
        "report_key": "cyclic",
        "snapshot_label": "m1_cyclic",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
