# -*- coding: utf-8 -*-
"""M4.tmo — physiology-domain DLC (targeted metabolic onset module: ABMI 1.0 re-engineering of legacy metabolic.py TMO)

Role:
  - one-compartment metabolism model: C(t)=dose*F/Vd*e^(-ke*t); target occupancy=C/(C+EC5...)"""
from __future__ import annotations
import math
from typing import Any, Dict, List
 
TMO_MEDICAL_DISCLAIMER = (
    "All templates in this module are designed for narrative purposes and carry "
    "no pharmacokinetic or toxicokinetic reference value of any kind. It is "
    "forbidden to use any output of a large language model loaded with this "
    "system as a basis for medical intervention decisions."
)
# built-in neutral demo templates only (compliance boundary 14.4)
TMO_BUILTIN_TEMPLATES = {
    "topical soothing dressing (demo)": {
        "dose": 1.0, "F": 0.6, "Vd": 1.0, "ke": 0.02, "EC50": 0.4,
        "effects": {"pain_relief": 0.6}, "category": "modern generic formulation"},
    "generic depressant class (abstract demo)": {
        "dose": 1.0, "F": 1.0, "Vd": 1.0, "ke": 0.01, "EC50": 0.5,
        "effects": {"consciousness_suppression": 0.9, "motor_impairment": 0.7,
                    "respiratory_suppression": 0.3, "amnesia": 0.5},
        "category": "abstract demo"},
}
TMO_CONSCIOUSNESS_T1 = 0.5    # suppression>0.5 -> attention capacity 2->1
TMO_CONSCIOUSNESS_T2 = 0.8    # suppression>0.8 -> capacity 0; behavior selection/language output sleep
TMO_CONSCIOUSNESS_T3 = 0.95   # suppression>0.95 -> whole-body suppression; only PSM_D1/D2/D4 maintained
TMO_CLEARANCE_C = 0.01        # metabolic clearance concentration threshold
# thermal downstream effect keys (declared in the template's effects; forwarded to M11 via m11.apply_thermal_modifiers)
TMO_THERMAL_KEYS = ("setpoint_shift", "vasodilation",
                    "shivering_suppress", "sweat_suppress")
 
 
class _Agent:
    """one row of the in-vivo active-agent ledger (self-contained, no dependence on the shared type library)."""
    __slots__ = ("name", "concentration", "occupancy", "effects",
                 "ke", "ec50", "elapsed_minutes")
 
    def __init__(self, name: str, concentration: float, effects: dict,
                 ke: float, ec50: float) -> None:
        self.name = name
        self.concentration = concentration
        self.occupancy = 0.0
        self.effects = dict(effects)
        self.ke = ke
        self.ec50 = ec50
        self.elapsed_minutes = 0.0
 
 
class TargetedMetabolicOnsetModule:
    """M4 TMO: one-compartment metabolism + target occupancy + consciousness-suppression grading; pure local computation."""
 
    DISCLAIMER = TMO_MEDICAL_DISCLAIMER
 
    def __init__(self, log: Any) -> None:
        self.log = log
        self.templates: Dict[str, dict] = dict(TMO_BUILTIN_TEMPLATES)
        self.active_agents: List[_Agent] = []
        self._holding_unconscious = False                         # whether currently occupying sys.unconsciousness
 
    # ---- external injection interface (compliance responsibility lies with the caller) ----
    def register_custom_template(self, name: str, spec: dict) -> None:
        required = {"dose", "F", "Vd", "ke", "EC50", "effects"}
        missing = required - set(spec)
        if missing:
            raise ValueError(f"TMO template missing fields: {missing}")
        self.templates[name] = dict(spec)
        self.log.record(0, "M4.tmo", "external template injection",
                        f"{name} (category={spec.get('category', 'custom')})")
 
    # ---- dosing/exposure (service port m4.administer) ----
    def administer(self, tick: int, template_name: str, dose_mult: float = 1.0) -> bool:
        tpl = self.templates.get(template_name)
        if tpl is None:
            return False
        c0 = tpl["dose"] * dose_mult * tpl["F"] / tpl["Vd"]
        self.active_agents.append(_Agent(template_name, c0, tpl["effects"],
                                         tpl["ke"], tpl["EC50"]))
        self.log.record(tick, "M4.tmo", "dose/exposure",
                        f"{template_name} C0={c0:.3f}")
        return True
 
    # ---- metabolism advance ----
    def advance(self, tick: int, dt_minutes: float) -> None:
        survivors = []
        for a in self.active_agents:
            a.elapsed_minutes += dt_minutes
            a.concentration *= math.exp(-a.ke * dt_minutes)         # one-compartment elimination
            a.occupancy = a.concentration / (a.concentration + a.ec50)
            if a.concentration > TMO_CLEARANCE_C:
                survivors.append(a)
            else:
                self.log.record(tick, "M4.tmo", "metabolic clearance", a.name)
        self.active_agents = survivors
 
    # ---- compose effect vector ----
    def effect_vector(self) -> Dict[str, float]:
        out = {"consciousness_suppression": 0.0, "motor_impairment": 0.0,
               "respiratory_suppression": 0.0, "amnesia": 0.0, "pain_relief": 0.0}
        for a in self.active_agents:
            for key, strength in a.effects.items():
                if key in out:
                    out[key] = min(1.0, out[key] + a.occupancy * strength)
        return out
 
    # ---- thermal modifier vector (occupancy-weighted; M11 downstream) ----
    def thermal_modifiers(self) -> Dict[str, float]:
        mods: Dict[str, float] = {}
        for a in self.active_agents:
            for key in TMO_THERMAL_KEYS:
                if key in a.effects:
                    val = a.occupancy * float(a.effects[key])
                    if key == "setpoint_shift":
                        mods[key] = mods.get(key, 0.0) + val      # additive
                    else:
                        mods[key] = max(mods.get(key, 0.0), val)  # strongest wins
        return mods
 
    @staticmethod
    def consciousness_grade(suppression: float) -> str:
        if suppression > TMO_CONSCIOUSNESS_T3:
            return "whole-body suppression (only PSM_D1/D2/D4 maintained)"
        if suppression > TMO_CONSCIOUSNESS_T2:
            return "capacity 0 (behavior selector / language output dormant)"
        if suppression > TMO_CONSCIOUSNESS_T1:
            return "capacity 1 (external perception weights suppressed)"
        return "none"
 
    @property
    def active(self) -> bool:
        return bool(self.active_agents)
 
    # ================= P1 hook =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        exposure = data.get("tmo_exposure")                         # scene-side acute exposure
        if exposure:
            self.administer(tick, str(exposure), float(data.get("dose_mult", 1.0)))
        self.advance(tick, float(data.get("dt", 0.0)))
        vec = self.effect_vector()
        board = self._board
        for key, val in vec.items():                                # effect vector archiving
            board.write_knob(f"knob.m4.tmo.{key}", round(val, 4), owner="M4.tmo")
        # soft keys read directly by the kernel (K.attention/K.language/K.hub/K.memory);
        # trigger still awake on the final-clearance tick -> write back neutral values to prevent residue
        board.write_knob("knob.consciousness_suppression",
                         vec["consciousness_suppression"], owner="M4.tmo")
        board.write_knob("knob.motor_impairment",
                         vec["motor_impairment"], owner="M4.tmo")
        board.write_knob("knob.amnesia", vec["amnesia"], owner="M4.tmo")
        # ---- thermal downstream: active-agent thermal effects -> M11 (still awake on the final-clearance tick -> flushed with {} to prevent residue) ----
        if self._services is not None:
            self._services.call("m11.apply_thermal_modifiers",
                                self.thermal_modifiers(), default=None)
        sup = vec["consciousness_suppression"]
        if sup > TMO_CONSCIOUSNESS_T3:                              # whole-body suppression hard threshold
            board.publish("sys.unconsciousness", True)
            self._holding_unconscious = True
        elif self._holding_unconscious:                             # release the occupation (yield to alcohol/guard)
            board.publish("sys.unconsciousness", False)
            self._holding_unconscious = False
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"agents": [{"name": a.name, "c": a.concentration, "o": a.occupancy,
                            "effects": dict(a.effects), "ke": a.ke, "ec50": a.ec50,
                            "elapsed": a.elapsed_minutes}
                           for a in self.active_agents],
                "templates": {k: dict(v) for k, v in self.templates.items()},
                "holding_unconscious": self._holding_unconscious}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.templates = {k: dict(v) for k, v in
                          (snap.get("templates") or TMO_BUILTIN_TEMPLATES).items()}
        self.active_agents = []
        for d in snap.get("agents") or []:
            a = _Agent(str(d.get("name", "")), float(d.get("c", 0.0)),
                       d.get("effects") or {}, float(d.get("ke", 0.01)),
                       float(d.get("ec50", 0.5)))
            a.occupancy = float(d.get("o", 0.0))
            a.elapsed_minutes = float(d.get("elapsed", 0.0))
            self.active_agents.append(a)
        self._holding_unconscious = bool(snap.get("holding_unconscious", False))
 
    def smoke(self) -> bool:
        return all(a.concentration >= 0.0 for a in self.active_agents)
 
    def invariants(self) -> bool:
        return all(0.0 <= a.occupancy <= 1.0 and a.concentration >= 0.0
                   for a in self.active_agents)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        if not self.active_agents:
            return {"state": "dormant"}
        return {a.name: {"concentration": round(a.concentration, 3),
                         "occupancy": round(a.occupancy, 3)}
                for a in self.active_agents}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug; instance-aware trigger injected at bind time)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    spec: Dict[str, Any] = {
        "module_id": "M4.tmo",
        "version": "1.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": ("sys.unconsciousness",),                  # written while suppression>T3
        "gear": {
            "P1_body": {"every": 1, "trigger": None},               # rewritten at bind time
        },
        "priorities": {"P1_body": 25},                              # after alcohol (20)
        "provides": ("m4.administer", "m4.register_template"),
        "requires": {"soft": {"m11.apply_thermal_modifiers": None}},
        "report_key": "tmo",
        "snapshot_label": "m4_tmo",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
 
    def factory(ctx: Any) -> TargetedMetabolicOnsetModule:
        engine = TargetedMetabolicOnsetModule(ctx.log)
        engine._board = ctx.board
        engine._services = ctx.services
        return engine
 
    def bind(inst: TargetedMetabolicOnsetModule, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m4.administer", inst.administer)
        ctx.services.offer("m4.register_template", inst.register_custom_template)
        # instance-aware trigger: sleeps when no active agent (zero-cost sleep)
        spec["gear"]["P1_body"]["trigger"] = (
            lambda t, d: inst.active or bool(d.get("tmo_exposure")))
        return {"P1_body": inst.on_body, "report": inst.report}
 
    spec["factory"] = factory
    spec["bind"] = bind
    return spec
