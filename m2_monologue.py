# -*- coding: utf-8 -*-
"""M2.monologue — cognition-domain DLC (inner voice: ABMI 1.0 re-engineering of legacy monologue.py / X1)

Role: internal-state statement output (15.1 V2.0). Dormant by default, produces nothing on most ticks; sleeps right after producing.
  Ten trigger kinds: emotion..."""
from __future__ import annotations
from typing import Any, Dict, Optional
 
MONOLOGUE_TRIGGER_DEFAULT_ROUNDS = 5    # default mode for >=5 consecutive ticks + I type -> statement
MONOLOGUE_RUMINATION_SSM = 60.0         # SM_SSM>60 + default mode -> rumination enhancement
 
# trigger condition -> neutral statement template (engine default, no persona-card text)
_TEMPLATES = {
    "affect shift": "the emotional baseline swung from {prev} to {cur}; "
                    "the internal state shows a marked swing",
    "disposition conflict triggered": "two disposition groups were pushed up "
                                      "at once; hard to tell which should "
                                      "take priority",
    "default-mode statement": "no external input; attention wanders back and "
                              "forth among internal states",
    "behavior-goal conflict": "internal drives and external pulls point in "
                              "different directions; deadlocked",
    "state cache resurfacing": "a past state suddenly surfaced, overlapping "
                               "with the current scene",
    "physiological limit": "the {domain} signal has reached critical level "
                           "and cannot be ignored",
    "major behavior shift": "the scene theme ruptured; the behavior goal "
                            "switched from {prev} to {cur}",
    # ---- V3.0 three new triggers ----
    "trauma response": "the body entered alert before judgment; a familiar "
                       "sense of danger rises again",
    "moral emotion": "a feeling of {kind} presses on the chest, directly "
                     "tied to the behavior choice just made",
    "identity threat": "the narrative of \"who am I\" suddenly wavers; "
                       "cracks appear in the self-description",
}
 
 
class InternalStateUtteranceEmitter:
    """inner-voice emitter: engine neutral templates + SpeechProfile coloring; pure local computation."""
 
    def __init__(self, log: Any, language_layer_in_cns: bool = True) -> None:
        self.log = log
        self.language_layer_in_cns = language_layer_in_cns
        self._default_mode_rounds = 0
        self._prev_label = ""
        self._prev_valence = 0.0
        self._prev_arousal = 0.0
        self._prev_strategy = ""
        self.last_utterance: Optional[Dict[str, Any]] = None
 
    # ---- trigger check (full legacy check_triggers semantics) ----
    def check_triggers(self, tick: int, *, prev_emotion: Optional[dict],
                       emotion: dict, conflict_mark: str,
                       default_mode: bool, ie_letter: Optional[str],
                       objective_conflict: bool, memory_resurfaced: bool,
                       limit_columns: list, major_shift: tuple,
                       ssm: float, particle_set: tuple,
                       combat_suppression: bool,
                       trauma_active: bool = False,
                       moral_emotion: str = "",
                       identity_threat: bool = False
                       ) -> Optional[Dict[str, Any]]:
        triggers = []
        # V3.0 three new: trauma response / moral emotion / identity threat (all suppressible)
        if trauma_active:
            triggers.append(("trauma response", True, {}))
        if moral_emotion:
            triggers.append(("moral emotion", True, {"kind": moral_emotion}))
        if identity_threat:
            triggers.append(("identity threat", True, {}))
        # 1. emotion shift (label changed and V+A distance >= 0.5)
        if prev_emotion and prev_emotion.get("label") != emotion.get("label") \
                and abs(emotion.get("valence", 0.0) - prev_emotion.get("valence", 0.0)) \
                + abs(emotion.get("arousal", 0.0) - prev_emotion.get("arousal", 0.0)) >= 0.5:
            triggers.append(("affect shift", True,
                             {"prev": prev_emotion.get("label"),
                              "cur": emotion.get("label")}))
        # 2. disposition conflict trigger
        if conflict_mark:
            triggers.append(("disposition conflict triggered", True, {}))
        # 3. default-mode statement (>=5 consecutive ticks + I type)
        self._default_mode_rounds = (self._default_mode_rounds + 1
                                     if default_mode else 0)
        if self._default_mode_rounds >= MONOLOGUE_TRIGGER_DEFAULT_ROUNDS \
                and ie_letter == "I":
            triggers.append(("default-mode statement", True, {}))
        # 4. behavior-goal conflict
        if objective_conflict:
            triggers.append(("behavior-goal conflict", True, {}))
        # 5. state-cache resurfacing
        if memory_resurfaced:
            triggers.append(("state cache resurfacing", True, {}))
        # 6. physiological limit (not suppressible)
        if limit_columns:
            triggers.append(("physiological limit", False,
                             {"domain": limit_columns[0]}))
        # 7. major behavior shift
        if major_shift:
            triggers.append(("major behavior shift", True,
                             {"prev": major_shift[0], "cur": major_shift[1]}))
        if not triggers:
            return None
        # suppression rule: physiological-limit kind is not suppressible; the rest are suppressed under external urgency/fight-or-flight/acute stress
        usable = [t for t in triggers if not t[1]] if combat_suppression \
            else triggers
        if not usable:
            return None
        # rumination enhancement: SM_SSM>60 + default mode -> default-mode statement takes priority
        if ssm > MONOLOGUE_RUMINATION_SSM and any(
                t[0] == "default-mode statement" for t in usable):
            chosen = next(t for t in usable
                          if t[0] == "default-mode statement")
        else:
            chosen = usable[0]
        trigger, _suppressible, params = chosen
        text = _TEMPLATES[trigger].format(**params)
        # SpeechProfile coloring: if the language layer is in CNS -> particle rendering; otherwise neutral wording
        if self.language_layer_in_cns and particle_set:
            text += particle_set[0] if trigger != "physiological limit" \
                else "..."
        utterance = {"trigger": trigger, "text": text,
                     "suppressible": chosen[1], "tick": tick}
        self.log.record(tick, "M2.monologue", f"trigger [{trigger}]", text)
        self.last_utterance = utterance
        return utterance
 
    # ================= hook: P4 trigger evaluation (after emotion/behavior ready) =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        # ---- emotion (this tick's encoded object first, board key as fallback) ----
        emo_obj = data.get("emotion")
        if emo_obj is not None:
            emotion = {"valence": float(getattr(emo_obj, "valence", 0.0)),
                       "arousal": float(getattr(emo_obj, "arousal", 0.0)),
                       "label": str(getattr(emo_obj, "label", ""))}
        else:
            emotion = dict(board.read("K.emotion.state", {}) or {})
        prev_emotion = ({"label": self._prev_label,
                         "valence": self._prev_valence,
                         "arousal": self._prev_arousal}
                        if self._prev_label else None)
        # ---- major behavior shift: strategy renamed + new behavior goal (BREAK-like semantics) ----
        strategy = str(board.read("sys.last_strategy_name", "") or "")
        major_shift = ()
        if strategy and self._prev_strategy and strategy != self._prev_strategy \
                and data.get("objective_cmd"):
            major_shift = (self._prev_strategy, strategy)
        # ---- physiological-limit column (urgency=3) ----
        limit_columns = []
        if self._columnar is not None:
            try:
                for cid, enc in (self._columnar.encodings() or {}).items():
                    if enc is not None and int(getattr(enc, "urgency_level", 0)) >= 3:
                        limit_columns.append(cid)
            except Exception:
                limit_columns = []
        # ---- combat suppression: scene urgency or trauma activation ----
        scene = board.read("K.binder.scene", {}) or {}
        combat_suppression = bool(scene.get("urgency")) or \
            bool(board.read("sys.trauma_active", False))
        # ---- hormones / particles / IE ----
        ssm = 0.0
        if self._hormones is not None:
            ssm = float(self._hormones.compute_effective_levels().get(
                "SM_SSM", 0.0))
        particle_set: tuple = ()
        if self._language is not None:
            particle_set = tuple(getattr(
                getattr(self._language, "profile", None), "particle_set", ())
                or ())
        ie_letter = self._btcs.letter("IE") if self._btcs is not None else None
        # ---- default mode: no external input and no stimuli ----
        default_mode = not data.get("user_input") and not data.get("stimuli")
 
        utterance = self.check_triggers(
            tick, prev_emotion=prev_emotion, emotion=emotion,
            conflict_mark=str(board.read("sys.odp_mark", "") or ""),
            default_mode=default_mode, ie_letter=ie_letter,
            objective_conflict=bool(data.get("objective_conflict")),
            memory_resurfaced=bool(data.get("memory_resurfaced")),
            limit_columns=limit_columns, major_shift=major_shift,
            ssm=ssm, particle_set=particle_set,
            combat_suppression=combat_suppression,
            trauma_active=bool(board.read("sys.trauma_active", False)),
            moral_emotion=str(board.read("sys.moral_emotion", "") or ""),
            identity_threat=bool(board.read("sys.identity_threat", False)))
        # ---- per-round state deposit (next tick's prev reference) ----
        self._prev_label = str(emotion.get("label", "") or "")
        self._prev_valence = float(emotion.get("valence", 0.0) or 0.0)
        self._prev_arousal = float(emotion.get("arousal", 0.0) or 0.0)
        if strategy:
            self._prev_strategy = strategy
        # ---- output: board publish + event + tick data ----
        if utterance is not None:
            board.publish("M2.monologue.utterance", dict(utterance))
            data["monologue"] = utterance["text"]
            if self._bus is not None:
                self._bus.emit("monologue.utterance", dict(utterance),
                               source="M2.monologue")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"default_mode_rounds": self._default_mode_rounds,
                "prev_label": self._prev_label,
                "prev_valence": self._prev_valence,
                "prev_arousal": self._prev_arousal,
                "prev_strategy": self._prev_strategy,
                "last_utterance": (dict(self.last_utterance)
                                   if self.last_utterance else None)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._default_mode_rounds = int(snap.get("default_mode_rounds", 0))
        self._prev_label = str(snap.get("prev_label", ""))
        self._prev_valence = float(snap.get("prev_valence", 0.0))
        self._prev_arousal = float(snap.get("prev_arousal", 0.0))
        self._prev_strategy = str(snap.get("prev_strategy", ""))
        lu = snap.get("last_utterance")
        self.last_utterance = dict(lu) if isinstance(lu, dict) else None
 
    def smoke(self) -> bool:
        return self._default_mode_rounds >= 0
 
    def invariants(self) -> bool:
        return 0 <= self._default_mode_rounds < 100000
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        if self.last_utterance is None:
            return {"state": "dormant"}
        return {"trigger": self.last_utterance["trigger"],
                "text": self.last_utterance["text"]}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> InternalStateUtteranceEmitter:
        engine = InternalStateUtteranceEmitter(
            ctx.log, bool(getattr(ctx.k.card, "language_layer_in_cns", True)))
        engine._board = ctx.board
        engine._bus = ctx.bus
        engine._columnar = ctx.k.columnar
        engine._hormones = ctx.k.hormones
        engine._language = ctx.k.language
        engine._btcs = ctx.k.btcs
        return engine
 
    def bind(inst: InternalStateUtteranceEmitter, ctx: Any) -> Dict[str, Any]:
        return {
            "P4_decision": inst.on_decision,
            "report": inst.report,
        }
 
    return {
        "module_id": "M2.monologue",
        "version": "1.0",
        "zone": "cognitive",
        "contract_keys": (),
        "gear": {"P4_decision": {"every": 1, "trigger": None}},  # evaluation lightweight resident
        "priorities": {"P4_decision": 40},                        # after behavior P4-10
        "factory": factory,
        "bind": bind,
        "provides": ("M2.monologue.utterance",),
        "requires": {"soft": {}},
        "report_key": "monologue",
        "snapshot_label": "m2_monologue",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
