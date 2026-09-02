# -*- coding: utf-8 -*-
"""M10.morality — cognition-domain DLC (morality & identity: ABMI 1.0 re-engineering of legacy morality.py)

Role: M10 sits at the biomimetic interface layer (CNS), via signal path C: perceptual content -> iceberg+experience retrieval ->
  M10 processing"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
KOHLBERG_STAGES = (1, 2, 3, 4, 5, 6)
MORAL_RIGIDITY_BY_JP = {"J": (0.6, 0.75), "P": (0.35, 0.5), None: 0.5}
MORAL_VIOLATION_THRESHOLD = 0.5           # composite violation >0.5 -> moral emotion
MORAL_INTENTION_WEIGHT = 0.4              # composite violation = 0.4*intent + 0.6*outcome
MORAL_OUTCOME_WEIGHT = 0.6
MORAL_GUILT_VALENCE = (-0.7, -0.5)        # guilt (repair)
MORAL_SHAME_VALENCE = (-0.9, -0.6)        # shame (withdrawal)
MORAL_PRIDE_VALENCE = (0.3, 0.5)          # moral pride
MORAL_EMOTION_VALENCE_WEIGHT = (0.05, 0.15)   # moral-emotion shift weight on the emotion vector
MORAL_RIGIDITY_HIGH = 0.7                 # high rigidity: no conflict allowed -> decision paralysis
MORAL_RIGIDITY_LOW = 0.4                  # low rigidity: may yield to higher priority
MORAL_PARALYSIS_TICKS = (1, 3)
MORAL_REFLECTION_COUNT = 3                # same core value violated 3 times -> moral reflection
MORAL_REFLECTION_RIGIDITY_MULT = 0.8
MORAL_VALUE_REMOVE_RIGIDITY = 0.2
MORAL_STAGE_TRAUMA_INTEGRATION = 0.7      # moral-injury integration >0.7 and a higher principle realized -> stage ascension
IDENTITY_FRICTION_THRESHOLD = 0.4         # behavior-trait match <0.4 -> narrative friction
IDENTITY_FRICTION_CONSEC = 5              # 5 consecutive ticks -> identity threat
IDENTITY_FRICTION_WINDOW = 8              # or 8 accumulated within the window
IDENTITY_REWRITE_COHERENCE = (0.2, 0.4)   # coherence interval during rewrite
IDENTITY_RECOVER_COHERENCE = 0.6          # completion flag: coherence rebound >0.6
IDENTITY_DENIAL_TICKS = (10, 30)          # life-course event rupture: denial phase
IDENTITY_COLLAPSE_TICKS = (30, 100)       # collapse phase
IDENTITY_REBUILD_TICKS = (50, 200)        # rebuild phase
# ODP social direction -> moral stage extrapolation (social harmony->L3 / rule order->L4 / personal principle->L5)
_ODP_STAGE_MAP = (("A08", "A01", "A06", "A05"), ("B18", "B21", "B22"),
                  ("D56", "B24", "C36"))
# behavior-direction keywords -> trait match (1+1=2: label hit, approximate cosine)
_TRAIT_KEYWORDS = {
    "brave": ("fight", "active contact", "direct statement", "disclosure",
              "adventure"),
    "cautious": ("freeze", "remote observation", "observation", "probing",
                 "prudence"),
    "kind": ("fawn", "defensive fawning", "presence maintenance", "forgiveness"),
    "honest": ("direct statement", "disclosure", "candor"),
    "loyal": ("presence maintenance", "low-arousal rest", "dutifulness"),
    "cunning": ("indirect hinting", "concealment", "deception"),
    "impulsive": ("active sampling", "follow curiosity", "impulsiveness"),
}
# behavior strategy -> aggression index (local copy of the aggro column of the kernel strategy meta-table, for intent judgment)
_STRATEGY_AGGRO = {
    "increase physical distance": 0.2, "reduce social exposure": 0.1,
    "freeze": 0.0, "defensive fawning": 0.3, "active contact": 0.8,
    "verbal probing": 0.5, "presence maintenance": 0.3, "disclosure": 0.9,
    "silent presence": 0.1, "observation": 0.2, "introspection": 0.0,
    "low-arousal rest": 0.0, "active sampling": 0.7, "remote observation": 0.3,
    "probing": 0.5, "follow curiosity": 0.8, "direct statement": 0.8,
    "indirect hinting": 0.4, "somatized expression": 0.2,
    "creation/diversion": 0.5,
}
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class MoralEmotionEvent:
    """moral-emotion event (self-contained)."""
    __slots__ = ("emotion", "intensity", "violation_severity", "behavior_impulse",
                 "touched_value", "created_tick", "delayed", "resolved",
                 "valence_effect")
 
    def __init__(self, emotion: str, intensity: float, severity: float,
                 impulse: str, value: str, tick: int, delayed: bool) -> None:
        self.emotion = emotion
        self.intensity = intensity
        self.violation_severity = severity
        self.behavior_impulse = impulse
        self.touched_value = value
        self.created_tick = tick
        self.delayed = delayed
        self.resolved = False
        sign = 1.0 if emotion == "moral_pride" else -1.0
        self.valence_effect = sign * intensity
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MoralEmotionEvent":
        ev = cls(str(d.get("emotion", "")), float(d.get("intensity", 0.0)),
                 float(d.get("violation_severity", 0.0)),
                 str(d.get("behavior_impulse", "")),
                 str(d.get("touched_value", "")),
                 int(d.get("created_tick", 0)), bool(d.get("delayed", False)))
        ev.resolved = bool(d.get("resolved", False))
        ev.valence_effect = float(d.get("valence_effect", ev.valence_effect))
        return ev
 
 
class MoralityAndIdentityEngine:
    """M10 morality & identity engine; pure local computation."""
 
    def __init__(self, rng: Any, log: Any, moral_decl: Optional[dict] = None,
                 identity_decl: Optional[dict] = None) -> None:
        self.rng = rng                                            # derived deterministic substream
        self.log = log
        self._seq = 0
        # ---- moral framework (declaration first, otherwise extrapolated) ----
        decl = moral_decl or {}
        stage = int(decl.get("stage", 0) or 0)
        if stage not in KOHLBERG_STAGES:
            stage = 0
        rigidity = decl.get("moral_rigidity")
        source = str(decl.get("moral_source", "") or "")
        self._declared_stage = stage in KOHLBERG_STAGES
        self._declared_rigidity = rigidity is not None
        self._declared_source = bool(source)
        self.moral = {
            "stage": stage or 3,
            "domain_modifiers": dict(decl.get("domain_modifiers", {})),
            "core_values": list(decl.get("core_values", []))[:5],
            "moral_rigidity": (_clamp(float(rigidity))
                               if rigidity is not None else 0.5),
            "moral_source": source or "external",
            "violation_counts": {},
        }
        # ---- identity narrative ----
        idecl = identity_decl or {}
        self.identity = {
            "core_traits": list(idecl.get("core_traits", [])),
            "relation_positions": {}, "life_story": [],
            "identity_coherence": 0.7,
            "friction_count": 0, "friction_consecutive": 0,
            "threat_type": "", "threat_level": 0.0,
            "rewrite_phase": "", "rewrite_ticks": 0,
        }
        self._framework_inferred = False
        self.active_emotion: Optional[MoralEmotionEvent] = None
        self.emotion_history: List[MoralEmotionEvent] = []
        self._delayed_queue: List[Dict[str, Any]] = []            # in-drunkenness delayed settlement queue
        self._paralysis_ticks = 0                                 # high-rigidity conflict -> paralysis
        # alcohol degradation (written by M4 event)
        self.alc_rigidity_delta = 0.0                             # L3: rigidity temporarily -0.3
        self.alc_identity_check_paused = False                    # L4: identity check suspended
 
    # ================= card validation (legacy validate_identity, compile-time warnings) =================
    @staticmethod
    def validate_identity(decl: dict) -> Optional[str]:
        """gender_identity=='other' forces a gender_description check."""
        gi = (decl or {}).get("gender_identity", "")
        if gi == "other" and not str((decl or {}).get(
                "gender_description", "") or "").strip():
            return ("gender_identity='other' but no gender_description "
                    "provided (required)")
        if gi and gi not in ("male", "female", "other"):
            return f"illegal gender_identity value: {gi} (male|female|other)"
        return None
 
    # ================= framework extrapolation (only undeclared fields are extrapolated; declarations are never overridden) =================
    def infer_framework(self, odp: dict, jp_letter: Optional[str],
                        materialism_mid: bool, religion: str) -> None:
        m = self.moral
        if not self._declared_stage:
            if any(d in odp for d in _ODP_STAGE_MAP[2]):
                m["stage"] = 5
            elif any(d in odp for d in _ODP_STAGE_MAP[1]):
                m["stage"] = 4
            else:
                m["stage"] = 3
        if not self._declared_rigidity:
            span = MORAL_RIGIDITY_BY_JP.get(jp_letter,
                                            MORAL_RIGIDITY_BY_JP[None])
            m["moral_rigidity"] = (span if isinstance(span, float)
                                   else self.rng.uniform(*span))
        if not self._declared_source:
            m["moral_source"] = ("internalized" if religion
                                 else "utilitarian" if materialism_mid
                                 else "external")
        self.log.record(0, "M10.morality", "framework extrapolation",
                        f"stage=L{m['stage']} rigidity={m['moral_rigidity']:.2f} "
                        f"source={m['moral_source']}")
 
    # ================= moral judgment (post-behavior trigger; service port m10.judge_behavior) =================
    def judge_behavior(self, tick: int, behavior_desc: str,
                       intention_score: float, outcome_score: float,
                       touched_values: tuple = (), victim_is_other: bool = True,
                       self_image_denied: bool = False,
                       intoxicated: bool = False) -> Optional[MoralEmotionEvent]:
        values = ([v for v in touched_values if v in self.moral["core_values"]]
                  or [v for v in touched_values])
        if self.moral["core_values"] and not values:
            return None                                 # no core value touched -> no judgment
        composite = (MORAL_INTENTION_WEIGHT * intention_score
                     + MORAL_OUTCOME_WEIGHT * outcome_score)
        severity = abs(min(0.0, composite)) * self.effective_rigidity()
        if intoxicated and composite < 0.0:                   # in drunkenness -> delayed settlement queue
            self._delayed_queue.append({
                "tick": tick, "behavior": behavior_desc,
                "intention": intention_score, "outcome": outcome_score,
                "values": values, "victim_is_other": victim_is_other,
                "self_image_denied": self_image_denied})
            self.log.record(tick, "M10.morality", "delayed settlement enqueued",
                            f"[{behavior_desc}] during drunkenness -> "
                            f"judged after sobering")
            return None
        return self._emit_moral_emotion(tick, behavior_desc, composite, severity,
                                        values, victim_is_other,
                                        self_image_denied)
 
    def _emit_moral_emotion(self, tick: int, behavior_desc: str,
                            composite: float, severity: float, values: list,
                            victim_is_other: bool, self_image_denied: bool,
                            delayed: bool = False) -> Optional[MoralEmotionEvent]:
        if composite >= 0.0 and not self_image_denied:
            if composite > 0.3 and values:                # positive intent + positive outcome -> moral pride
                ev = self._make_emotion(
                    tick, "moral_pride",
                    abs(self.rng.uniform(*MORAL_PRIDE_VALENCE)), composite,
                    "—", values[0] if values else "", delayed)
                self.active_emotion = ev
                return ev
            return None
        if severity <= MORAL_VIOLATION_THRESHOLD:
            return None
        if self_image_denied:                             # "the whole me" negated -> shame
            ev = self._make_emotion(
                tick, "shame", abs(self.rng.uniform(*MORAL_SHAME_VALENCE)),
                severity, "withdrawal/hiding/aggression",
                values[0] if values else "", delayed)
        elif victim_is_other:                             # the victim is another -> guilt
            ev = self._make_emotion(
                tick, "guilt", abs(self.rng.uniform(*MORAL_GUILT_VALENCE)),
                severity, "repair/make amends",
                values[0] if values else "", delayed)
        else:
            return None
        self.active_emotion = ev
        if values:                                        # moral reflection: same value violated 3 times
            cnt = self.moral["violation_counts"].get(values[0], 0) + 1
            self.moral["violation_counts"][values[0]] = cnt
            if cnt >= MORAL_REFLECTION_COUNT:
                self._moral_reflection(tick, values[0])
        return ev
 
    def _make_emotion(self, tick: int, kind: str, intensity: float,
                      severity: float, impulse: str, value: str,
                      delayed: bool) -> MoralEmotionEvent:
        self._seq += 1
        ev = MoralEmotionEvent(kind, round(_clamp(intensity), 3),
                               round(severity, 3), impulse, value, tick, delayed)
        self.emotion_history.append(ev)
        self.log.record(tick, "M10.morality", f"moral emotion [{kind}]",
                        f"intensity={ev.intensity:.2f} severity={severity:.2f} "
                        f"touched '{value}' -> impulse:{impulse}"
                        f"{'[delayed · stricter]' if delayed else ''}")
        return ev
 
    # ================= after waking: delayed moral settlement (alcohol.delayed_settlement event) =================
    def settle_delayed_judgments(self, tick: int) -> list:
        """"the sober self judges the drunk self": real-time judgment is stricter (violation x1.2)."""
        settled = []
        for item in self._delayed_queue:
            composite = (MORAL_INTENTION_WEIGHT * item["intention"]
                         + MORAL_OUTCOME_WEIGHT * item["outcome"]) * 1.2
            severity = abs(min(0.0, composite)) * self.effective_rigidity()
            ev = self._emit_moral_emotion(tick, item["behavior"], composite,
                                          severity, item["values"],
                                          item["victim_is_other"],
                                          item["self_image_denied"], delayed=True)
            if ev is not None:
                settled.append(ev)
        self._delayed_queue = []
        return settled
 
    # ================= core-value conflict arbitration (service port m10.arbitrate) =================
    def arbitrate_value_conflict(self, tick: int,
                                 values_in_conflict: tuple) -> dict:
        """declaration order = priority. High rigidity (>0.7): no conflict allowed -> paralysis 1~3 ticks -> forced choice
                triggers severe moral emotion; low rigidity (<0.4): may yield to higher priority.        """
        ordered = [v for v in self.moral["core_values"] if v in values_in_conflict]
        if len(ordered) < 2:
            return {"conflict": False}
        rigidity = self.effective_rigidity()
        winner = ordered[0]
        if rigidity > MORAL_RIGIDITY_HIGH:
            self._paralysis_ticks = self._randint(*MORAL_PARALYSIS_TICKS)
            self.log.record(tick, "M10.morality",
                            "core-value conflict (high rigidity)",
                            f"{' <-> '.join(ordered)} -> paralysis "
                            f"{self._paralysis_ticks} ticks")
            return {"conflict": True, "paralysis_ticks": self._paralysis_ticks,
                    "forced_choice": winner, "severe_emotion": True}
        if rigidity < MORAL_RIGIDITY_LOW:
            self.log.record(tick, "M10.morality",
                            "core-value conflict (low rigidity)",
                            f"yield to priority '{winner}'")
            return {"conflict": True, "paralysis_ticks": 0,
                    "forced_choice": winner, "severe_emotion": False}
        self.log.record(tick, "M10.morality", "core-value conflict",
                        f"by priority -> '{winner}' (mild moral tension)")
        return {"conflict": True, "paralysis_ticks": 0,
                "forced_choice": winner, "severe_emotion": False}
 
    def _randint(self, lo: int, hi: int) -> int:
        """deterministic integer draw (the derived stream has no randint; implemented via random)."""
        return lo + min(hi - lo, int(self.rng.random() * (hi - lo + 1)))
 
    @property
    def decision_paralyzed(self) -> bool:
        return self._paralysis_ticks > 0
 
    # ================= moral reflection and stage evolution =================
    def _moral_reflection(self, tick: int, value: str) -> None:
        """same core value violated 3 times: A change behavior / B adjust the standard (rigidity x0.8, removable below 0.2) /
                C adjust the self-narrative (or trigger identity threat).        """
        path = self.rng.choice(["A behavior change", "B standard adjustment",
                                "C narrative adjustment"])
        if path == "B standard adjustment":
            self.moral["moral_rigidity"] = round(
                self.moral["moral_rigidity"] * MORAL_REFLECTION_RIGIDITY_MULT, 3)
            if (self.moral["moral_rigidity"] < MORAL_VALUE_REMOVE_RIGIDITY
                    and value in self.moral["core_values"]):
                self.moral["core_values"].remove(value)
                self.log.record(tick, "M10.morality", "moral reflection",
                                f"'{value}' rigidity too low -> removed "
                                f"from core values")
                return
        elif path == "C narrative adjustment":
            self.identity["friction_count"] += 2
        self.log.record(tick, "M10.morality", "moral reflection",
                        f"[{value}] violated x3 -> {path}")
 
    def evolve_stage(self, tick: int, cause: str,
                     trauma_integration: float = 0.0) -> bool:
        """stage ascension (irreversible): (1) transcendence experience reorders core values (2) narrative reconstruction completes
                after identity threat (3) moral-injury integration >0.7 with a higher principle realized.        """
        if self.moral["stage"] >= 6:
            return False
        ok = (cause == "transcendental" or cause == "narrative_rebuilt"
              or (cause == "trauma_integrated"
                  and trauma_integration > MORAL_STAGE_TRAUMA_INTEGRATION))
        if ok:
            self.moral["stage"] += 1
            self.log.record(tick, "M10.morality", "stage evolution",
                            f"Kohlberg L{self.moral['stage'] - 1} -> "
                            f"L{self.moral['stage']} ({cause})")
            return True
        return False
 
    # ================= identity: narrative coherence check (lightweight, per tick) =================
    def check_narrative_coherence(self, tick: int, behavior_direction: str,
                                  denied_by_other: bool = False,
                                  attachment_broken: bool = False,
                                  story_conflict: bool = False) -> dict:
        """behavior direction vs core traits; <0.4 -> narrative friction written to the preconscious; accumulated breach -> identity threat."""
        result = {"friction": False, "threat": "", "level": 0.0}
        if self.alc_identity_check_paused:                    # alcohol L4: check suspended
            return result
        if story_conflict:                                    # three kinds of exogenous threats (priority)
            return self._trigger_threat(tick, "story_fractured", 1.0)
        if attachment_broken:
            return self._trigger_threat(tick, "relation_broken", 0.8)
        if denied_by_other:
            return self._trigger_threat(tick, "trait_challenged", 0.5)
        if self.identity["core_traits"] and behavior_direction:
            match = self._trait_match(behavior_direction)
            if match < IDENTITY_FRICTION_THRESHOLD:
                self.identity["friction_count"] += 1
                self.identity["friction_consecutive"] += 1
                result["friction"] = True
                if (self.identity["friction_consecutive"] >= IDENTITY_FRICTION_CONSEC
                        or self.identity["friction_count"] >= IDENTITY_FRICTION_WINDOW):
                    self.identity["friction_count"] = 0
                    self.identity["friction_consecutive"] = 0
                    return self._trigger_threat(tick, "trait_challenged", 0.5)
            else:
                self.identity["friction_consecutive"] = 0
        result["level"] = self.identity["threat_level"]
        return result
 
    def _trait_match(self, behavior_direction: str) -> float:
        hits, total = 0, len(self.identity["core_traits"])
        for trait in self.identity["core_traits"]:
            kws = _TRAIT_KEYWORDS.get(trait, (trait,))
            if any(kw in behavior_direction for kw in kws):
                hits += 1
        return hits / total if total else 1.0
 
    def _trigger_threat(self, tick: int, ttype: str, level: float) -> dict:
        self.identity["threat_type"] = ttype
        self.identity["threat_level"] = level
        self.identity["identity_coherence"] = _clamp(
            self.identity["identity_coherence"] - level * 0.3)
        if ttype == "story_fractured" and not self.identity["rewrite_phase"]:
            self.identity["rewrite_phase"] = "denial"
            self.identity["rewrite_ticks"] = 0
        self.log.record(tick, "M10.identity", f"identity threat [{ttype}]",
                        f"level={level:.1f} coherence->"
                        f"{self.identity['identity_coherence']:.2f}")
        return {"friction": False, "threat": ttype, "level": level}
 
    # ================= narrative rewrite mechanism =================
    def tick_rewrite(self, tick: int) -> str:
        """rewrite period: coherence 0.2~0.4; rupture: denial(10~30)->collapse(30~100)->rebuild(50~200);
                completion flag: coherence rebound >0.6.        """
        ph = self.identity["rewrite_phase"]
        if not ph:
            return ""
        self.identity["rewrite_ticks"] += 1
        t = self.identity["rewrite_ticks"]
        lo, hi = IDENTITY_REWRITE_COHERENCE
        target = self.rng.uniform(lo, hi)
        self.identity["identity_coherence"] += (
            target - self.identity["identity_coherence"]) * 0.2
        if ph == "denial" and t >= self._randint(*IDENTITY_DENIAL_TICKS):
            self.identity["rewrite_phase"], self.identity["rewrite_ticks"] = \
                "collapse", 0
        elif ph == "collapse" and t >= self._randint(*IDENTITY_COLLAPSE_TICKS):
            self.identity["rewrite_phase"], self.identity["rewrite_ticks"] = \
                "rebuild", 0
        elif ph == "rebuild":
            self.identity["identity_coherence"] += 0.02
            if (self.identity["identity_coherence"] > IDENTITY_RECOVER_COHERENCE
                    or t >= IDENTITY_REBUILD_TICKS[1]):
                self.identity["rewrite_phase"] = ""
                self.identity["rewrite_ticks"] = 0
                self.identity["threat_level"] = 0.0
                self.identity["threat_type"] = ""
                self.log.record(tick, "M10.identity",
                                "narrative refactoring complete",
                                f"coherence={self.identity['identity_coherence']:.2f}")
                return "completed"
        return self.identity["rewrite_phase"]
 
    # ================= moral emotion output =================
    def moral_emotion_offset(self) -> float:
        """moral-emotion offset on the emotion vector (x0.05~0.15; K.emotion board read)."""
        if self.active_emotion is None or self.active_emotion.resolved:
            return 0.0
        w = self.rng.uniform(*MORAL_EMOTION_VALENCE_WEIGHT)
        return round(_clamp(self.active_emotion.valence_effect * w, -1.0, 1.0), 3)
 
    def resolve_emotion(self, tick: int, pathway: str = "repair") -> bool:
        """guilt dissolves through reparative behavior; shame dissolves only through self-narrative reconstruction."""
        ev = self.active_emotion
        if ev is None or ev.resolved:
            return False
        if ev.emotion == "guilt" and pathway == "repair":
            ev.resolved = True
        elif ev.emotion == "shame" and pathway == "narrative":
            ev.resolved = True
        elif ev.emotion == "moral_pride":
            ev.resolved = True
        if ev.resolved:
            self.log.record(tick, "M10.morality", "moral emotion resolved",
                            f"{ev.emotion}[{pathway}]")
            self.active_emotion = None
            return True
        return False
 
    # ================= somatic reaction signal (path C terminal -> PSM_D1 priority 3) =================
    def somatic_signals(self) -> dict:
        tt = self.identity["threat_type"]
        if tt == "story_fractured":
            return {"hr_pattern": "chaotic",
                    "hormone": "cortisol + adrenaline double shock",
                    "intensity": 0.8}
        if tt == "relation_broken":
            return {"hr_pattern": "alternating", "muscle": "chronic tension",
                    "d8_appetite": -0.3, "hormone": "sustained cortisol",
                    "intensity": 0.65}
        if tt == "trait_challenged":
            return {"hr_offset": 0.2, "rr_offset": 0.15,
                    "muscle": "alert tension", "hormone": "cortisol",
                    "intensity": 0.45}
        ev = self.active_emotion
        if ev is None or ev.resolved:
            return {}
        if ev.emotion == "guilt":
            return {"hr_pattern": "heavy", "rr_pattern": "shallow (sighing)",
                    "d2_stomach": 0.3, "muscle": "tone slightly lowered",
                    "intensity": ev.intensity}
        if ev.emotion == "shame":
            return {"hr_offset": 0.25,
                    "muscle": "adduction (shoulders in / head down)",
                    "face_heat": 0.4, "speech_volume": -0.3,
                    "intensity": ev.intensity}
        if ev.emotion == "moral_pride":
            return {"hr_offset": 0.1,
                    "muscle": "expansion (chest out / head up)",
                    "speech_volume": 0.2, "intensity": ev.intensity}
        return {}
 
    # ================= alcohol degradation write (alcohol.degradation event) =================
    def apply_alcohol_degradation(self, d: Dict[str, Any]) -> None:
        self.alc_rigidity_delta = float(d.get("moral_rigidity_delta", 0.0))
        self.alc_identity_check_paused = bool(d.get("identity_check_paused", False))
 
    def effective_rigidity(self) -> float:
        return _clamp(self.moral["moral_rigidity"] + self.alc_rigidity_delta,
                      0.0, 1.0)
 
    # ================= background maintenance =================
    def background_maintenance(self, tick: int) -> None:
        if self._paralysis_ticks > 0:
            self._paralysis_ticks -= 1
        if self.active_emotion is not None:                   # active moral emotions decay naturally
            age = tick - self.active_emotion.created_tick
            if age > 30 and self.active_emotion.emotion != "shame":
                self.active_emotion = None
 
    # ================= publish (mirror -> sys.*) =================
    def _publish(self) -> None:
        ae = self.active_emotion
        self._board.publish("M10.morality.active_emotion",
                            ae.emotion if ae else "")
        self._board.publish("M10.morality.identity_coherence",
                            self.identity["identity_coherence"])
        self._board.publish("M10.morality.friction_consecutive",
                            self.identity["friction_consecutive"])
        self._board.publish("M10.morality.moral_emotion",
                            ae.emotion if ae else "")
        self._board.publish("M10.morality.identity_threat",
                            self.identity["threat_level"] >= 0.5)
        self._board.publish("M10.morality.decision_paralyzed",
                            self.decision_paralyzed)
        self._board.publish("M10.morality.valence_offset",
                            self.moral_emotion_offset())
        self._board.publish("M10.morality.behavior_impulse",
                            ae.behavior_impulse if ae else "")
 
    # ================= hook: P3 judgment + check + somatic signal =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        if not self._framework_inferred:                      # first-tick framework extrapolation (lazy)
            worldview = (None, None)
            if self._services is not None:
                worldview = self._services.call("m9.worldview",
                                                default=(None, None))
            card_odp = getattr(self._card, "odp", {}) if self._card else {}
            jp = self._btcs.letter("JP") if self._btcs is not None else None
            self.infer_framework(card_odp, jp,
                                 bool(worldview and worldview[0]),
                                 str(worldview[1]) if worldview and worldview[1]
                                 else "")
            self._framework_inferred = True
        board = self._board
        last_strategy = str(board.read("sys.last_strategy_name", "") or "")
        # moral judgment of the previous behavior (post-behavior trigger)
        if last_strategy and self.moral["core_values"]:
            theme_str = " ".join(str(x) for x in
                                 board.read("sys.last_scene_themes", ()) or ()) \
                + last_strategy
            touched = tuple(v for v in self.moral["core_values"]
                            if any(kw in theme_str for kw in str(v).split("/"))
                            or str(v) in theme_str)
            if touched:
                aggro = _STRATEGY_AGGRO.get(last_strategy, 0.5)
                intention = (0.2 if aggro < 0.3
                             else (-0.4 if aggro > 0.6 else 0.0))
                tier = int(board.read("M4.alcohol.tier", 0) or 0)
                self.judge_behavior(
                    tick, last_strategy, intention,
                    float(board.read("sys.prev_scene_valence", 0.0)), touched,
                    victim_is_other=True, intoxicated=(tier >= 2))
        # lightweight narrative coherence check (three exogenous threats picked from tick-data stimuli)
        stimuli = data.get("stimuli") or []
        cats = {str(st.get("category", "")) for st in stimuli
                if isinstance(st, dict)}
        coherence = self.check_narrative_coherence(
            tick, last_strategy,
            denied_by_other="trait denial" in cats,
            attachment_broken="attachment rupture" in cats,
            story_conflict="narrative conflict" in cats)
        if coherence.get("threat") and self._services is not None:
            self._services.call("m7.inject", tick, "identity_threat",
                                coherence["threat"], intensity=0.6,
                                valence=-0.5, source="moral",
                                layer="preconscious",
                                linkage_tags=["identity", coherence["threat"]],
                                default=None)
        elif coherence.get("friction") and self._services is not None:
            self._services.call("m7.inject", tick, "narrative_friction",
                                "behavior inconsistent with self traits",
                                intensity=0.35, valence=-0.2, source="moral",
                                layer="preconscious",
                                linkage_tags=["narrative friction"],
                                default=None)
        # somatic signal -> columnar PSM_D1 (priority 3)
        msig = self.somatic_signals()
        if msig and self._columnar is not None:
            self._columnar.route_psm_d1_signal(
                tick, msig.get("intensity", 0.4), "moral_somatic")
        self._publish()
 
    # ================= hook: P6 maintenance + narrative rewrite =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.background_maintenance(tick)
        self.tick_rewrite(tick)
        self._publish()
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"seq": self._seq,
                "moral": {k: (dict(v) if isinstance(v, dict) else
                              list(v) if isinstance(v, list) else v)
                          for k, v in self.moral.items()},
                "identity": dict(self.identity),
                "declared": (self._declared_stage, self._declared_rigidity,
                             self._declared_source),
                "framework_inferred": self._framework_inferred,
                "active_emotion": (self.active_emotion.to_dict()
                                   if self.active_emotion else None),
                "emotion_history": [e.to_dict() for e in self.emotion_history],
                "delayed_queue": [dict(q) for q in self._delayed_queue],
                "paralysis_ticks": self._paralysis_ticks,
                "alc_rigidity_delta": self.alc_rigidity_delta,
                "alc_identity_check_paused": self.alc_identity_check_paused,
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._seq = int(snap.get("seq", 0))
        for k, v in (snap.get("moral") or {}).items():
            self.moral[k] = (dict(v) if isinstance(v, dict) else
                             list(v) if isinstance(v, list) else v)
        self.identity.update(snap.get("identity") or {})
        declared = snap.get("declared") or (False, False, False)
        (self._declared_stage, self._declared_rigidity,
         self._declared_source) = (bool(declared[0]), bool(declared[1]),
                                   bool(declared[2]))
        self._framework_inferred = bool(snap.get("framework_inferred", False))
        ae = snap.get("active_emotion")
        self.active_emotion = (MoralEmotionEvent.from_dict(ae)
                               if isinstance(ae, dict) else None)
        self.emotion_history = [MoralEmotionEvent.from_dict(d)
                                for d in (snap.get("emotion_history") or [])]
        self._delayed_queue = [dict(q) for q in (snap.get("delayed_queue") or [])]
        self._paralysis_ticks = int(snap.get("paralysis_ticks", 0))
        self.alc_rigidity_delta = float(snap.get("alc_rigidity_delta", 0.0))
        self.alc_identity_check_paused = bool(
            snap.get("alc_identity_check_paused", False))
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return isinstance(self.moral, dict) and isinstance(self.identity, dict)
 
    def invariants(self) -> bool:
        return (self.moral["stage"] in KOHLBERG_STAGES
                and 0.0 <= self.moral["moral_rigidity"] <= 1.0
                and 0.0 <= self.identity["identity_coherence"] <= 1.0
                and self._paralysis_ticks >= 0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"stage": self.moral["stage"],
                "rigidity": round(self.effective_rigidity(), 2),
                "source": self.moral["moral_source"],
                "active_emotion": (self.active_emotion.emotion
                                   if self.active_emotion else None),
                "identity_coherence": round(
                    self.identity["identity_coherence"], 3),
                "threat": self.identity["threat_type"] or "none",
                "rewrite_phase": self.identity["rewrite_phase"] or "none"}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> MoralityAndIdentityEngine:
        warning = MoralityAndIdentityEngine.validate_identity(
            ctx.k.card.identity or {})
        if warning:
            ctx.log.record(0, "M10.morality", "card validation alarm", warning)
        engine = MoralityAndIdentityEngine(ctx.rng_for("m10_morality"), ctx.log,
                                           ctx.k.card.moral_framework,
                                           ctx.k.card.identity)
        engine._board = ctx.board
        engine._services = ctx.services
        engine._columnar = ctx.k.columnar
        engine._btcs = ctx.k.btcs
        engine._card = ctx.k.card
        return engine
 
    def bind(inst: MoralityAndIdentityEngine, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m10.judge_behavior", inst.judge_behavior)
        ctx.services.offer("m10.arbitrate", inst.arbitrate_value_conflict)
        ctx.services.offer("m10.resolve_emotion", inst.resolve_emotion)
        ctx.services.offer("m10.evolve_stage", inst.evolve_stage)
        ctx.bus.subscribe(
            "alcohol.degradation",
            lambda item: inst.apply_alcohol_degradation(
                item.get("payload") or {}),
            owner="M10.morality")
 
        def _settle(item: Dict[str, Any]) -> None:                # post-waking delayed settlement
            payload = item.get("payload") or {}
            settled = inst.settle_delayed_judgments(
                int(payload.get("tick", 0)))
            if ctx.services is not None:
                ctx.services.call("alcohol.clear_delayed", default=None)
            if settled:
                inst._publish()
        ctx.bus.subscribe("alcohol.delayed_settlement", _settle,
                          owner="M10.morality")
        return {
            "P3_cognition": inst.on_cognition,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "M10.morality",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain (CNS interface layer)
        "contract_keys": (                                          # mirror target contract key
            "sys.identity_coherence", "sys.moral_emotion",
            "sys.moral_active_emotion", "sys.identity_threat",
            "sys.decision_paralyzed", "sys.friction_consecutive"),
        "gear": {                                                   # lightweight per-tick check
            "P3_cognition": {"every": 1, "trigger": None},
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P3_cognition": 30,                          # before emotion (P3-40)
                       "P6_maintenance": 70},
        "factory": factory,
        "bind": bind,
        "provides": ("m10.judge_behavior", "m10.arbitrate",
                     "m10.resolve_emotion", "m10.evolve_stage"),
        "requires": {"soft": {"m7.inject": None, "m9.worldview": None,
                              "alcohol.clear_delayed": None}},
        "report_key": "morality",
        "snapshot_label": "m10_morality",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
