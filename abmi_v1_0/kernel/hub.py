# -*- coding: utf-8 -*-
"""K.hub — cognition-domain kernel module (central decision routing node: Chapter 10)

Role:
  - time stitching: working-slot theme comparison -> CONTINUE / BREAK (BREAK window -> event density)
  - behavior-goal generation: inner push (nine-column encoding) vs outer pull (scene fragments); the stronger..."""
from __future__ import annotations
from collections import deque
from typing import Any, Dict, Optional
 
from ..infrastructure import DecisionLog
from .constants import (OBJ_NEGATIVE_AVOIDANCE, OBJ_POSITIVE_INTERACTION,
                        OBJ_STATE_MAINTENANCE, OBJ_INFORMATION_SAMPLING,
                        OBJ_INFORMATION_OUTPUT, SM_SRF, SM_CRF, SM_ARF, SM_HMF)
from .models import (PerceptionScene, AffectiveStateEncoding,
                     BehaviorObjectiveCommand, clamp)
 
 
class HubEngine:
    """central decision routing: time stitching / goal generation / attention direction / agitation index / final binding."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.work_slot_theme: Optional[str] = None                  # working-slot theme (previous scene)
        self.break_window: deque = deque(maxlen=6)                  # BREAK window (<=6 ticks)
        self.continue_count = 0                                     # consecutive CONTINUE count
        self.last_intent = OBJ_STATE_MAINTENANCE                    # last round's behavior goal
        self.alc_behavior_random = False                            # M4 L4: goals near-random
        self.alc_response_delay_mult = 1.0                          # M4 L6: reaction-delay multiplier
        self.alc_unconscious = False                                # M4 L7: unconscious (no goals produced)
 
    # ---- M4 alcohol-degradation injection (legacy compatibility surface) ----
    def apply_alcohol_degradation(self, behavior_random: bool = False,
                                  response_delay_mult: float = 1.0,
                                  unconscious: bool = False) -> None:
        self.alc_behavior_random = behavior_random
        self.alc_response_delay_mult = response_delay_mult
        self.alc_unconscious = unconscious
 
    # ================= 10.1 time stitching =================
    def determine_temporal_continuity(self, tick: int,
                                      scene: PerceptionScene) -> str:
        if self.work_slot_theme is None:
            continuity = "BREAK"                                    # first scene always breaks
        elif self.work_slot_theme == scene.integrated_theme:
            continuity = "CONTINUE"                                 # same-theme continuation
        else:
            continuity = "BREAK"
        self.break_window.append(1 if continuity == "BREAK" else 0)
        self.continue_count = self.continue_count + 1 if continuity == "CONTINUE" else 0
        self.work_slot_theme = scene.integrated_theme
        self.log.record(tick, "CNS", "temporal stitching",
                        f"{continuity}(theme={scene.integrated_theme})")
        return continuity
 
    def compute_event_density(self) -> tuple:
        """event density: break count within the BREAK window -> low/mid/high."""
        n = sum(self.break_window)
        band = "low" if n <= 1 else ("mid" if n <= 3 else "high")
        return n, band
 
    # ================= 10.2 behavior-goal generation (inner push vs outer pull) =================
    def generate_behavior_objective(self, tick: int, body: Dict[str, Any],
                                    scene: PerceptionScene) -> tuple:
        """push priority: D6 > D5 > D3 > D7 > D8/D9; intensity 3 wins outright; ties hold."""
        enc = body.get("encodings", {}) or {}
        push_intent, push_strength = OBJ_STATE_MAINTENANCE, 0
        c6, c5, c3 = enc.get("PSM_D6"), enc.get("PSM_D5"), enc.get("PSM_D3")
        c7, c8, c9 = enc.get("PSM_D7"), enc.get("PSM_D8"), enc.get("PSM_D9")
        if c6 and body.get("pain_level", 0) >= 5.0:                 # pain push: avoidance
            push_intent, push_strength = OBJ_NEGATIVE_AVOIDANCE, c6["urgency_level"]
        elif c5 and body.get("stress_level", 0) >= 2.0:             # stress push: avoidance
            push_intent, push_strength = OBJ_NEGATIVE_AVOIDANCE, c5["urgency_level"]
        elif c3 and body.get("hunger", 0) >= 3.0:                   # hunger push: sampling
            push_intent, push_strength = OBJ_INFORMATION_SAMPLING, c3["urgency_level"]
        elif c7 and c7["discomfort_level"] >= 2:                    # thermal-discomfort push: sampling
            push_intent, push_strength = OBJ_INFORMATION_SAMPLING, c7["urgency_level"]
        elif (c8 and c8["urgency_level"] >= 2) or (c9 and c9["urgency_level"] >= 2):
            col = c8 if (c8 and (not c9 or c8["urgency_level"] >= c9["urgency_level"])) else c9
            push_intent, push_strength = OBJ_INFORMATION_SAMPLING, col["urgency_level"]
        pull_intent, pull_strength = OBJ_STATE_MAINTENANCE, 0
        if scene.perception_fragments:                              # outer pull: the most urgent fragment's suggestion
            top = max(scene.perception_fragments, key=lambda f: f.urgency)
            pull_intent = top.recommended_intent
            pull_strength = scene.urgency
        if push_strength == 3:                                      # survival level wins outright
            intent, strength = push_intent, push_strength
        elif pull_strength == 3:
            intent, strength = pull_intent, pull_strength
        elif push_strength > pull_strength:
            intent, strength = push_intent, push_strength
        elif pull_strength > push_strength:
            intent, strength = pull_intent, pull_strength
        else:
            intent, strength = OBJ_STATE_MAINTENANCE, 0             # tie -> hold
        objective_conflict = (push_strength >= 2 and pull_strength >= 2
                              and push_intent != pull_intent)       # push-pull conflict mark
        if self.alc_behavior_random and strength < 3:               # M4 L4: goals near-random
            pool = (OBJ_STATE_MAINTENANCE, OBJ_NEGATIVE_AVOIDANCE,
                    OBJ_POSITIVE_INTERACTION, OBJ_INFORMATION_SAMPLING)
            intent = pool[tick % len(pool)]
            strength = max(strength, 1)
            self.log.record(tick, "CNS", "alcohol L4: objective randomized", intent)
        self.last_intent = intent
        self.log.record(tick, "CNS", "behavior objective",
                        f"push[{push_intent}×{push_strength}] vs "
                        f"pull[{pull_intent}×{pull_strength}] → {intent}×{strength}")
        return intent, strength, objective_conflict
 
    # ================= 10.3 attention modulation direction =================
    def generate_attention_directive(self, intent: str) -> str:
        table = {
            OBJ_STATE_MAINTENANCE: "keep",
            OBJ_NEGATIVE_AVOIDANCE: "switch: external_physical",
            OBJ_POSITIVE_INTERACTION: "switch: external_perceptual",
            OBJ_INFORMATION_SAMPLING: "switch: external_physical + internal_physical",
            OBJ_INFORMATION_OUTPUT: "switch: external_perceptual",
        }
        return table.get(intent, "keep")
 
    # ================= hormone agitation index (CNS pre-settlement) =================
    def compute_behavior_activation_coefficient(self, hormones: Dict[str, float]) -> float:
        raw = 0.5 + 0.5 * ((hormones.get(SM_SRF, 0) + hormones.get(SM_CRF, 0)
                            - hormones.get(SM_ARF, 0) - hormones.get(SM_HMF, 0)) / 100.0)
        return round(clamp(raw), 3)
 
    # ================= behavior goal -> column threshold pull (effective next tick) =================
    def objective_pulls_for_dimensions(self, intent: str, strength: int) -> Dict[str, float]:
        pull = strength / 3.0
        if intent == OBJ_NEGATIVE_AVOIDANCE:
            return {"PSM_D4": pull, "PSM_D5": pull, "PSM_D6": pull}
        if intent == OBJ_INFORMATION_SAMPLING:
            return {"PSM_D4": pull * 0.5, "PSM_D3": pull}
        if intent in (OBJ_POSITIVE_INTERACTION, OBJ_INFORMATION_OUTPUT):
            return {"PSM_D4": pull * 0.3}
        return {}
 
    # ================= final binding (Chapter 8 pre-binding step three) =================
    def finalize_perception_scene(self, tick: int, scene: PerceptionScene,
                                  emotion: AffectiveStateEncoding) -> PerceptionScene:
        scene.emotional_tone = emotion.label                        # emotion tone written back into the scene
        self.log.record(tick, "CNS", "final binding",
                        f"{scene.integrated_theme} + emotional_tone={emotion.label}")
        return scene
 
    # ================= P4 hook (V8 module surface) =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        scene = data["scene"]                                       # trigger guarantees non-empty
        emotion = data.get("emotion")                               # emotion may be absent (neutral default)
        self.alc_behavior_random = bool(board.read("sys.alcohol_behavior_random", False))
        self.alc_response_delay_mult = float(board.read("sys.alcohol_response_delay", 1.0))
        self.alc_unconscious = bool(board.read("sys.unconsciousness", False))
        continuity = self.determine_temporal_continuity(tick, scene)
        body = board.read("K.columnar.body", {}) or {}              # same-tick body report
        if self.alc_unconscious:                                    # L7 hard power-cut: no goals produced
            data["continuity"] = continuity
            self.log.record(tick, "CNS", "alcohol L7", "no behavior objective")
            return
        intent, strength, conflict = self.generate_behavior_objective(tick, body, scene)
        if emotion is not None:
            self.finalize_perception_scene(tick, scene, emotion)    # emotion tone write-back
        hormones = board.read("K.pns.hormones", {}) or {}           # same-tick hormone mirror
        data["continuity"] = continuity
        data["objective_conflict"] = conflict
        data["attention_directive"] = self.generate_attention_directive(intent)
        data["objective_cmd"] = BehaviorObjectiveCommand(           # -> behavior decision engine
            intent=intent, strength=strength, continuity=continuity,
            compute_behavior_activation_coefficient=
            self.compute_behavior_activation_coefficient(hormones),
            scene_summary=scene.integrated_theme,
            conflict_mark=str(board.read("sys.odp_mark", "") or ""),
            sse_risk_bias=float(board.read_knob("knob.sse_risk_bias", 0.0)),
            motor_impairment=float(board.read_knob("knob.motor_impairment", 0.0)))
        board.batch_publish({                                       # next-tick column pull + continuity mirror
            "K.hub.pulls": self.objective_pulls_for_dimensions(intent, strength),
            "K.hub.continuity": continuity,
        })
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"work_slot_theme": self.work_slot_theme,
                "break_window": list(self.break_window),
                "continue_count": self.continue_count,
                "last_intent": self.last_intent}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.work_slot_theme = snap.get("work_slot_theme")
        if isinstance(snap.get("break_window"), list):
            self.break_window = deque(snap["break_window"], maxlen=6)
        self.continue_count = int(snap.get("continue_count", 0))
        self.last_intent = str(snap.get("last_intent", OBJ_STATE_MAINTENANCE))
 
    def smoke(self) -> bool:
        return self.break_window is not None
 
    def invariants(self) -> bool:
        return len(self.break_window) <= 6 and self.continue_count >= 0
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        n, band = self.compute_event_density()
        return {"intent": self.last_intent, "continue": self.continue_count,
                "event_density": band}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> HubEngine:
        engine = HubEngine(ctx.log)
        engine._board = ctx.board
        ctx.k.hub = engine                                          # backfill kernel ports
        return engine
 
    def bind(inst: HubEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P4_decision": inst.on_decision,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.hub",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P4_decision": {"every": 1,
                            "trigger": lambda t, d: d.get("scene") is not None},  # no scene -> sleep
        },
        "priorities": {"P4_decision": 0},                           # front of the decision phase
        "factory": factory,
        "bind": bind,
        "provides": ("K.hub.pulls", "K.hub.continuity"),
        "requires": {},
        "report_key": "hub",
        "snapshot_label": "hub",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
