# -*- coding: utf-8 -*-
"""K.behavior — cognition-domain kernel module (behavior decision engine: Chapter 11)

Role:
  - strategy library: 5 behavior goals x 4 strategy templates = 20 strategies; screen -> modulate -> ODP/BTCS weight -> choose
  - ODP declaration replaces BTCS weighting"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, Optional
 
from ..infrastructure import DecisionLog
from .constants import (BEHAVIOR_STRATEGY_LIBRARY, BEHAVIOR_STRATEGY_META,
                        OBJ_STATE_MAINTENANCE, BTCS_SWING_LOW, BTCS_SWING_HIGH)
from .models import (BehaviorObjectiveCommand, BehaviorStrategyTemplate,
                     AffectiveStateEncoding)
 
 
class BehaviorEngine:
    """behavior-strategy selection: 1+1=2, only compare and map; persona weighting is pluggable (ODP first)."""
 
    AFFECTIVE_CHANGE_THRESHOLD = 0.4                                # emotion reselection threshold
    # ODP direction -> strategy affinity (declaration takes priority over BTCS weighting, 6.2)
    _ODP_AFFINITY = {
        "active contact": ("A02", "A07"), "disclosure": ("A07", "D57"),
        "verbal probing": ("A02", "C37"), "increase physical distance": ("A14", "D49"),
        "reduce social exposure": ("A14", "A15"), "freeze": ("D49", "B20"),
        "defensive fawning": ("A04", "A15"), "active sampling": ("D52", "D57"),
        "follow curiosity": ("D52", "D54"), "remote observation": ("B20", "C48"),
        "probing": ("B28", "C37"), "direct statement": ("A07", "B17"),
        "indirect hinting": ("A15", "C35"), "somatized expression": ("C38", "B30"),
        "creation/diversion": ("C35", "B26"), "silent presence": ("C36", "D58"),
        "observation": ("C48", "B24"), "introspection": ("B24", "C38"),
        "low-arousal rest": ("D58", "C42"), "presence maintenance": ("A06", "D55"),
    }
    # M8 4F mode -> strategy mapping (fight=confront / flight=flee / freeze=freeze / fawn=appease)
    _4F_STRATEGY_MAP = {"fight": "direct statement",
                        "flight": "increase physical distance",
                        "freeze": "freeze", "fawn": "defensive fawning",
                        "somatic_freeze": "freeze"}
 
    def __init__(self, card: Any, rng: Any, log: DecisionLog) -> None:
        self.card = card
        self.rng, self.log = rng, log
        self.btcs = None                                            # assembly-time wiring (attach_btcs)
        self.odp = None                                             # assembly-time wiring (attach_odp)
        self.prev_strategy: Optional[BehaviorStrategyTemplate] = None
        self.prev_emotion_valence = 0.0
        self._contradiction_rounds = 0                              # consecutive contradictory-strategy count (M6 awakening condition 3)
        # V3.0 soft-key offsets (refreshed by the per-tick hook; read-only, never written back)
        self._v3_trauma_mode = ""
        self._v3_moral_impulse = ""
        self._v3_leak_hint = ""
        self._v3_paralyzed = False
 
    def attach_btcs(self, btcs: Any) -> None:
        self.btcs = btcs                                            # kernel port wiring
 
    def attach_odp(self, odp: Any) -> None:
        self.odp = odp
 
    @property
    def contradiction_rounds(self) -> int:
        return self._contradiction_rounds
 
    # ---- V3.0 offset injection (legacy compatibility surface) ----
    def set_v3_offsets(self, trauma_mode: str = "", moral_impulse: str = "",
                       leak_hint: str = "", decision_paralyzed: bool = False) -> None:
        self._v3_trauma_mode = trauma_mode
        self._v3_moral_impulse = moral_impulse
        self._v3_leak_hint = leak_hint
        self._v3_paralyzed = decision_paralyzed
 
    # ---- step one: trigger-condition screening ----
    def _passes_trigger(self, name: str, emotion: AffectiveStateEncoding,
                        hormones: Dict[str, float]) -> bool:
        trig = BEHAVIOR_STRATEGY_META[name]["trigger"]
        if not trig:
            return True
        if "emotions" in trig and emotion.label not in trig["emotions"]:
            return False
        for hid, minimum in trig.get("hormone_min", {}).items():
            if hormones.get(hid, 0) < minimum:
                return False
        return True
 
    # ---- step three: BTCS affinity weighting (every 3-point deviation = 1%; swing zone not forced) ----
    def _btcs_weight(self, name: str) -> float:
        w = 1.0
        for letter in BEHAVIOR_STRATEGY_META[name]["aff"]:
            for dim, (lo, hi) in (("IE", ("I", "E")), ("SN", ("N", "S")),
                                  ("TF", ("T", "F")), ("JP", ("J", "P"))):
                if letter not in (lo, hi):
                    continue
                coord = self.btcs.get(dim)
                if BTCS_SWING_LOW <= coord <= BTCS_SWING_HIGH:
                    continue                                        # swing zone skipped
                actual = hi if coord > 50.0 else lo
                if actual == letter:
                    w += abs(coord - 50.0) / 3.0 * 0.01
        return w
 
    # ---- step three (V2.0): ODP affinity weighting (replaces BTCS when declared) ----
    def _odp_weight(self, name: str) -> float:
        aff = self._ODP_AFFINITY.get(name, ())
        if not aff:
            return 1.0
        return 1.0 + sum(self.odp.get(d) for d in aff) * 0.05
 
    # ---- main selection flow ----
    def select_behavior_strategy(self, tick: int, cmd: BehaviorObjectiveCommand,
                                 emotion: AffectiveStateEncoding,
                                 hormones: Dict[str, float]) -> BehaviorStrategyTemplate:
        pool = [s for s in BEHAVIOR_STRATEGY_LIBRARY.get(
                    cmd.intent, BEHAVIOR_STRATEGY_LIBRARY[OBJ_STATE_MAINTENANCE])
                if self._passes_trigger(s, emotion, hormones)]
        if not pool:                                                # all triggers dead -> unscreened full set
            pool = BEHAVIOR_STRATEGY_LIBRARY.get(
                cmd.intent, BEHAVIOR_STRATEGY_LIBRARY[OBJ_STATE_MAINTENANCE])
        # step two: agitation index + aggression baseline offset + SSE risk offset - motor impairment
        aggression = (cmd.compute_behavior_activation_coefficient
                      + self.card.aggression_baseline * 0.2
                      - cmd.sse_risk_bias * 0.3
                      - cmd.motor_impairment * 0.4)
        # M10 decision paralysis (high rigidity + core-value conflict) -> forced hold this round
        if self._v3_paralyzed:
            self.log.record(tick, "BehaviorDecisionEngine", "M10 decision paralysis",
                            "core value conflict -> frozen")
            return BehaviorStrategyTemplate(
                strategy_name="low-arousal rest", intent=cmd.intent,
                body_hint="frozen stiff", face_hint="tense",
                voice_hint="silent", stance="hesitant")
        # M8 trauma activation -> behavior lock (highest priority; ODP participation suspended)
        if self._v3_trauma_mode:
            locked = self._4F_STRATEGY_MAP.get(self._v3_trauma_mode, "freeze")
            body, face, voice, stance = BEHAVIOR_STRATEGY_META[locked]["hints"]
            self.log.record(tick, "BehaviorDecisionEngine", "M8 behavior lock",
                            f"4F[{self._v3_trauma_mode}] → {locked}")
            strategy = BehaviorStrategyTemplate(
                strategy_name=locked, intent=cmd.intent, body_hint=body,
                face_hint=face, voice_hint=voice, stance=stance)
            self.prev_strategy = strategy
            self.prev_emotion_valence = emotion.valence
            return strategy
        # M10 moral-emotion behavior-impulse offset (guilt->repair suppresses aggression; shame->withdrawal lowers exposure)
        if "repair" in self._v3_moral_impulse:
            aggression = max(0.0, aggression - 0.3)
        elif "withdrawal" in self._v3_moral_impulse:
            pool = [s for s in pool if BEHAVIOR_STRATEGY_META[s]["aggro"] <= 0.4] or pool
        # M6: the heavier the fracture, the less stable the strategy (agitation-index jitter, deterministic RNG)
        if cmd.conflict_mark:
            jitter = {"mild": 0.1, "moderate": 0.25, "severe": 0.45}.get(cmd.conflict_mark, 0.0)
            if jitter:
                aggression += self.rng.uniform(-jitter, jitter)
        # step four: CONTINUE keeps last round (emotion change <= threshold x switching resistance)
        if (cmd.continuity == "CONTINUE" and self.prev_strategy is not None
                and self.prev_strategy.intent == cmd.intent):
            emotion_change = abs(emotion.valence - self.prev_emotion_valence)
            jp = self.btcs.letter("JP")
            switch_resistance = 1.5 if jp == "J" else (0.7 if jp == "P" else 1.0)
            if emotion_change <= self.AFFECTIVE_CHANGE_THRESHOLD * switch_resistance:
                self._contradiction_rounds = 0
                return self.prev_strategy
        use_odp = self.odp is not None and self.odp.declared
 
        def score(name: str) -> float:
            match = 1.0 - abs(BEHAVIOR_STRATEGY_META[name]["aggro"] - aggression)
            return match * (self._odp_weight(name) if use_odp else self._btcs_weight(name))
 
        best = max(pool, key=score)
        # M6 awakening condition 3: stance opposite to last round -> consecutive contradiction count
        if self.prev_strategy is not None and self.prev_strategy.strategy_name != best:
            if abs(BEHAVIOR_STRATEGY_META[best]["aggro"]
                   - BEHAVIOR_STRATEGY_META[self.prev_strategy.strategy_name]["aggro"]) > 0.5:
                self._contradiction_rounds += 1
            else:
                self._contradiction_rounds = 0
        body, face, voice, stance = BEHAVIOR_STRATEGY_META[best]["hints"]
        # M7 iceberg leakage: suppressed content expressed via behavior-detail offsets (strategy name unchanged)
        if self._v3_leak_hint:
            body = f"{body}+{self._v3_leak_hint}"
        strategy = BehaviorStrategyTemplate(
            strategy_name=best, intent=cmd.intent, body_hint=body,
            face_hint=face, voice_hint=voice, stance=stance)
        self.prev_strategy = strategy
        self.prev_emotion_valence = emotion.valence
        self.log.record(tick, "BehaviorDecisionEngine", "strategy selected",
                        f"{best}(aggression={aggression:.2f}, "
                        f"weighted={'ODP' if use_odp else 'BTCS'})")
        return strategy
 
    # ================= P4 hook (V8 module surface) =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        # soft-key refresh (sys.* contract keys + module soft keys, all neutral defaults)
        self.set_v3_offsets(
            trauma_mode=str(board.read("sys.trauma_type", "") or "")
            if board.read("sys.trauma_active", False) else "",
            moral_impulse=str(board.read("M10.morality.behavior_impulse", "") or ""),
            leak_hint=str(board.read("sys.iceberg_leak", "") or ""),
            decision_paralyzed=bool(board.read("sys.decision_paralyzed", False)))
        emotion = data.get("emotion") or AffectiveStateEncoding(0.0, 0.0, "neutral")
        hormones = board.read("K.pns.hormones", {}) or {}
        strategy = self.select_behavior_strategy(
            tick, data["objective_cmd"], emotion, hormones)         # trigger guarantees the directive is non-empty
        data["strategy"] = strategy                                 # -> language interface
        board.batch_publish({
            "K.behavior.strategy": asdict(strategy),
            "sys.last_strategy_name": strategy.strategy_name,       # contract keys: cross-tick facts
        })
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {
            "prev_strategy": asdict(self.prev_strategy) if self.prev_strategy else None,
            "prev_emotion_valence": self.prev_emotion_valence,
            "contradiction_rounds": self._contradiction_rounds,
            "rng": self.rng.snapshot(),                     # stream cursor saved with the snapshot (ABMI 1.0)
        }
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        prev = snap.get("prev_strategy")
        if isinstance(prev, dict):
            self.prev_strategy = BehaviorStrategyTemplate(**prev)
        self.prev_emotion_valence = float(snap.get("prev_emotion_valence", 0.0))
        self._contradiction_rounds = int(snap.get("contradiction_rounds", 0))
        self.rng.restore(snap.get("rng"))                   # cursor rewind (silent when absent)
 
    def smoke(self) -> bool:
        return self.btcs is not None                                # assembly wiring must be ready
 
    def invariants(self) -> bool:
        return self._contradiction_rounds >= 0
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"strategy": self.prev_strategy.strategy_name if self.prev_strategy else "",
                "contradiction_rounds": self._contradiction_rounds}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> BehaviorEngine:
        engine = BehaviorEngine(ctx.k.card, ctx.rng_for("behavior"), ctx.log)
        engine.attach_btcs(ctx.k.btcs)                              # kernel port assembly wiring
        engine.attach_odp(ctx.k.odp)
        engine._board = ctx.board
        ctx.k.behavior = engine                                     # backfill kernel ports
        return engine
 
    def bind(inst: BehaviorEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P4_decision": inst.on_decision,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.behavior",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.last_strategy_name",),               # contract keys committed for write
        "gear": {
            "P4_decision": {"every": 1,
                            "trigger": lambda t, d: d.get("objective_cmd") is not None},
        },
        "priorities": {"P4_decision": 10},                          # after routing, before language
        "factory": factory,
        "bind": bind,
        "provides": ("K.behavior.strategy",),
        "requires": {},
        "report_key": "behavior",
        "snapshot_label": "behavior",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
