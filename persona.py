# -*- coding: utf-8 -*-
"""K.persona — cognition-domain kernel module (persona configuration layer: BTCS four-dimension coordinates + ODP 64 directions)

Role:
  - holds two configurations: the persona card (PersonaConfig) and persona coordinates (BTCS) / omnidirectional disposition (ODP);
  - republishes K.perso... to the board after any change"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
 
from ..infrastructure import DecisionLog
from .constants import (BTCS_MIN, BTCS_MAX, BTCS_DRIFT_STEP,
                        BTCS_SWING_LOW, BTCS_SWING_HIGH,
                        ODP_LEVEL_MIN, ODP_LEVEL_MAX, ODP_DIRECTIONS,
                        ODP_BTCS_FALLBACK, PERCEPTION_MATRIX_QUADRANTS,
                        MATRIX_INTERNAL_PHYSICAL, MATRIX_EXTERNAL_PHYSICAL,
                        MATRIX_EXTERNAL_PERCEPTUAL)
 
 
# =============================================================================
# PersonaConfig — the persona card (carrier of configuration declarations; constructed by the caller at assembly time)
# =============================================================================
@dataclass
class PersonaConfig:
    """persona configuration card: minimum acceptable input = name + four letters. All fields optional, backward compatible."""
    name: str = ""
    btcs: dict = field(default_factory=lambda: {"IE": 50.0, "SN": 50.0, "TF": 50.0, "JP": 50.0})  # four-dimension continuous coordinates [20,80]
    locked_dims: tuple = ()                 # locked dimensions (no drift)
    physiology: dict = field(default_factory=dict)      # hard-decoded physiological fine-tuning [-1,1]
    speech_hard: dict = field(default_factory=dict)     # hard-decoded voice parameters (override extrapolation)
    narrative_boundary: str = "all ages"    # content-rating threshold (ambiguous defaults to all-ages)
    interests: list = field(default_factory=list)       # interests (B pool seeds)
    relationships: dict = field(default_factory=dict)   # relationships (D pool seeds)
    core_memories: list = field(default_factory=list)   # core memories (L3 anchor seeds)
    aggression_baseline: float = 0.0        # aggression baseline offset [-1,1]
    attachment_figure: Optional[str] = None  # attachment-figure person_id
    tf_attribution: dict = field(default_factory=dict)  # T/F attribution text override
    safety_refusal: str = ""                # fuse reply (empty = engine neutral default)
    odp: dict = field(default_factory=dict)             # ODP 64-direction declaration
    body_metrics: dict = field(default_factory=dict)    # height/weight/sex (discharge capacity)
    language_layer_in_cns: bool = True      # whether the language layer is in CNS (inner-speech dyeing switch)
    cyclic_modulation: dict = field(default_factory=dict)   # M1 declaration (read by the DLC itself)
    systemic_load: dict = field(default_factory=dict)       # M3 declaration (read by the DLC itself)
    life_support: dict = field(default_factory=dict)        # M5 declaration (read by the DLC itself)
    alcohol_profile: dict = field(default_factory=dict)     # M4 declaration (read by the DLC itself)
    ice_box: dict = field(default_factory=dict)             # M7 declaration (read by the DLC itself)
    trauma_imprints: list = field(default_factory=list)     # M8 declaration (read by the DLC itself)
    philosophy: dict = field(default_factory=dict)          # M9 declaration (read by the DLC itself)
    a_priori_plasticity: float = 0.5                        # M9 prior plasticity
    moral_framework: dict = field(default_factory=dict)     # M10 declaration (read by the DLC itself)
    identity: dict = field(default_factory=dict)            # M10 declaration (read by the DLC itself)
    thermal_profile: dict = field(default_factory=dict)     # M11 declaration (read by the DLC itself)
    sacred_object: str = ""                                 # M14 declaration (read by the DLC itself)
    faith_intensity: float = 0.0                            # M14 faith intensity
    idns_profile: dict = field(default_factory=dict)        # M12/M13 declaration (read by the DLC itself)
 
 
# =============================================================================
# BTCS — behavior-tendency coordinate system (6.1: four-dimension continuous coordinates; 45-55 swing zone not force-weighted)
# =============================================================================
class BehavioralTendencyCoordinateSystem:
    """four-dimension continuous coordinates [20,80], median 50; drift +/-0.02; locked dimensions never drift."""
 
    DIMS = ("IE", "SN", "TF", "JP")                                  # the four dimensions
    DIM_LETTERS = {"IE": ("I", "E"), "SN": ("N", "S"),               # dimension -> letter pair
                   "TF": ("T", "F"), "JP": ("J", "P")}
 
    def __init__(self, coords: dict, locked: tuple = ()) -> None:
        self._coords = {d: min(BTCS_MAX, max(BTCS_MIN, float(coords.get(d, 50.0))))
                        for d in self.DIMS}                          # out-of-range truncation
        self._locked = set(locked)                                   # locked set
 
    def get(self, dim: str) -> float:
        return self._coords[dim]                                     # read one dimension's coordinate
 
    def copy_coords(self) -> dict:
        return dict(self._coords)                                    # coordinate copy
 
    def restore_coords(self, coords: dict) -> None:
        """snapshot restore: write coordinates back directly, bypassing the drift channel (15.2 narrative-safety-layer semantics)."""
        for d in self.DIMS:
            if d in coords:
                self._coords[d] = min(BTCS_MAX, max(BTCS_MIN, float(coords[d])))
 
    def letter(self, dim: str) -> Optional[str]:
        """dimension letter; the 45-55 swing zone returns None (free-swing zone, no forced weighting)."""
        v = self._coords[dim]
        if BTCS_SWING_LOW <= v <= BTCS_SWING_HIGH:
            return None
        lo, hi = self.DIM_LETTERS[dim]
        return hi if v > 50.0 else lo
 
    def type_string(self) -> str:
        return "".join(self.letter(d) or "x" for d in self.DIMS)     # four-letter type
 
    def drift(self, dim: str, direction: float) -> bool:
        """drift +/-0.02; locked dimensions refuse (returns False)."""
        if dim in self._locked:
            return False
        step = BTCS_DRIFT_STEP * (1 if direction > 0 else -1)
        self._coords[dim] = min(BTCS_MAX, max(BTCS_MIN, self._coords[dim] + step))
        return True
 
    def bias_for_quadrant(self, quadrant: str) -> float:
        """Station-1 modulation (7.1): E->external x1.3, I->internal x1.3, S->somatic x1.3, N->perception x1.3."""
        bias = 1.0
        ie, sn = self.letter("IE"), self.letter("SN")
        external = quadrant in (MATRIX_EXTERNAL_PHYSICAL, MATRIX_EXTERNAL_PERCEPTUAL)
        physical = quadrant in (MATRIX_INTERNAL_PHYSICAL, MATRIX_EXTERNAL_PHYSICAL)
        if ie == "E" and external:
            bias *= 1.3
        elif ie == "I" and not external:
            bias *= 1.3
        if sn == "S" and physical:
            bias *= 1.3
        elif sn == "N" and not physical:
            bias *= 1.3
        return bias
 
 
# =============================================================================
# ODP — omnidirectional disposition profile (6.2/14.6: 64 directions, 10 levels; declaration takes priority over BTCS weighting)
# =============================================================================
class OmnidirectionalDispositionProfile:
    """64 directions stored by value; 0.5~5.0 in 0.5 steps; empty declaration falls back to BTCS four-letter mapping."""
 
    def __init__(self, declared: dict,
                 btcs: Optional[BehavioralTendencyCoordinateSystem] = None) -> None:
        self._values: Dict[str, float] = {}
        for did, lv in (declared or {}).items():                     # load declared values
            if did in ODP_DIRECTIONS:
                self._values[did] = self._snap(float(lv))
        if not self._values and btcs is not None:                     # fallback: four letters -> defaults
            for dim in BehavioralTendencyCoordinateSystem.DIMS:
                letter = btcs.letter(dim)
                if letter and letter in ODP_BTCS_FALLBACK:
                    for did, lv in ODP_BTCS_FALLBACK[letter].items():
                        self._values.setdefault(did, lv)
 
    @staticmethod
    def _snap(v: float) -> float:
        v = min(ODP_LEVEL_MAX, max(ODP_LEVEL_MIN, v))                 # truncation range
        return round(v * 2.0) / 2.0                                   # 0.5-step alignment
 
    @property
    def declared(self) -> bool:
        return bool(self._values)                                     # whether a declared value exists
 
    def get(self, direction_id: str, default: float = 0.0) -> float:
        return self._values.get(direction_id, default)
 
    def set(self, direction_id: str, level: float) -> None:
        if direction_id in ODP_DIRECTIONS:
            self._values[direction_id] = self._snap(level)
 
    def nudge(self, direction_id: str, delta: float) -> None:
        """direction-value fine-tuning (M5 economic-security modulation / reparative experience)."""
        if direction_id in self._values:
            self._values[direction_id] = self._snap(self._values[direction_id] + delta)
 
    def drift(self, direction_id: str, delta: float) -> None:
        """continuous drift (not aligned to 0.5 steps, intermediate values allowed)."""
        if direction_id in self._values:
            self._values[direction_id] = min(
                ODP_LEVEL_MAX, max(ODP_LEVEL_MIN, self._values[direction_id] + delta))
 
    def items(self):
        return self._values.items()
 
    def snapshot(self) -> dict:
        return dict(self._values)
 
    def restore(self, values: dict) -> None:
        """snapshot restore: write direction values back directly."""
        self._values = {d: self._snap(float(v)) for d, v in values.items()
                        if d in ODP_DIRECTIONS}
 
 
# =============================================================================
# PersonaEngine — V8 module shell: publishes four board mirrors + service-port drift entries
# =============================================================================
class PersonaEngine:
    """persona configuration layer module: no gears (zero beat cost); publishes on change, drift via service ports."""
 
    def __init__(self, log: DecisionLog, card: PersonaConfig) -> None:
        self.log = log                                              # decision log
        self.card = card                                            # persona card
        self.btcs = BehavioralTendencyCoordinateSystem(card.btcs, card.locked_dims)
        self.odp = OmnidirectionalDispositionProfile(card.odp, self.btcs)
 
    # ---- board mirror publish (must be called after any change; downstream reads only these keys) ----
    def publish_mirrors(self, board: Any) -> None:
        board.batch_publish({
            "K.persona.coords": self.btcs.copy_coords(),            # four-dimension coordinates
            "K.persona.letters": {d: self.btcs.letter(d)            # four letters (swing=None)
                                  for d in BehavioralTendencyCoordinateSystem.DIMS},
            "K.persona.odp": self.odp.snapshot(),                   # ODP direction values
            "K.persona.bias": {q: self.btcs.bias_for_quadrant(q)    # four-quadrant weights
                               for q in PERCEPTION_MATRIX_QUADRANTS},
            "K.persona.type": self.btcs.type_string(),              # four-letter type string
        })
 
    # ---- service-port entries (registered to ServicePorts by bind at install time) ----
    def svc_drift(self, dim: str, direction: float) -> bool:
        """BTCS drift service: +/-0.02; locked dimensions refuse."""
        return self.btcs.drift(dim, direction)
 
    def svc_nudge_odp(self, direction_id: str, delta: float) -> None:
        self.odp.nudge(direction_id, delta)                         # ODP fine-tune
 
    def svc_set_odp(self, direction_id: str, level: float) -> None:
        self.odp.set(direction_id, level)                           # ODP set value
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"coords": self.btcs.copy_coords(), "odp": self.odp.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        if isinstance(snap.get("coords"), dict):
            self.btcs.restore_coords(snap["coords"])                # bypass-drift write-back
        if isinstance(snap.get("odp"), dict):
            self.odp.restore(snap["odp"])
 
    def smoke(self) -> bool:
        return self.btcs is not None and self.odp is not None
 
    def invariants(self) -> bool:
        coords_ok = all(BTCS_MIN <= v <= BTCS_MAX                   # coordinates globally valid
                        for v in self.btcs.copy_coords().values())
        odp_ok = all(ODP_LEVEL_MIN <= v <= ODP_LEVEL_MAX            # direction values globally valid
                     for _, v in self.odp.items())
        return coords_ok and odp_ok
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"type": self.btcs.type_string(), "odp_declared": self.odp.declared}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> PersonaEngine:
        engine = PersonaEngine(ctx.log, ctx.k.card)                 # persona card comes from the kernel port
        engine.publish_mirrors(ctx.board)                           # published at install time (ready before the first tick)
        ctx.k.btcs = engine.btcs                                    # backfill kernel ports (legacy compatibility)
        ctx.k.odp = engine.odp
        return engine
 
    def bind(inst: PersonaEngine, ctx: Any) -> Dict[str, Any]:
        # drift / fine-tune go through service ports: callers never know who provides
        ctx.services.offer("persona.drift",
                           lambda dim, direction: _after(inst, ctx, inst.svc_drift(dim, direction)))
        ctx.services.offer("persona.nudge_odp",
                           lambda did, delta: _after(inst, ctx, inst.svc_nudge_odp(did, delta)))
        ctx.services.offer("persona.set_odp",
                           lambda did, lv: _after(inst, ctx, inst.svc_set_odp(did, lv)))
        return {"report": inst.report}                              # P8 wrap-up report
 
    return {
        "module_id": "K.persona",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {},                                                 # no gears: the configuration layer has zero beats
        "priorities": {},
        "factory": factory,
        "bind": bind,
        "provides": ("K.persona.coords", "K.persona.letters",
                     "K.persona.odp", "K.persona.bias"),
        "requires": {},
        "report_key": "persona",
        "snapshot_label": "persona",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
 
 
def _after(engine: PersonaEngine, ctx: Any, result: Any) -> Any:
    """mirrors republished uniformly after service calls (any change hits the board immediately)."""
    engine.publish_mirrors(ctx.board)
    return result
