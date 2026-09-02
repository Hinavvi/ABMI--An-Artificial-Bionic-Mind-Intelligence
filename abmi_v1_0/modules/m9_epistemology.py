# -*- coding: utf-8 -*-
"""M9.epistemology — cognition-domain DLC (experience, priors, transcendence: ABMI 1.0 re-engineering of legacy epistemology.py)

Role: defines how the subject knows and what the subject knows. Three subsystems:
  - prior layer (metacognitive format): prior regulators S/N/T/F coordinates"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
EPI_MATERIALISM_SCORE = 80            # high-school politics required-course-4 >80 -> materialism (mid)
EPI_META_RELAX = 0.85                 # meta-layer relaxation coefficient
EPI_META_TIGHTEN = 1.15               # meta-layer tightening coefficient
EPI_META_INVASION = 0.10              # materialism (mid band): physics->value intrusion +10% (legacy constant kept)
EPI_INDUCTION_MIN_SAMPLES = 3         # >=3 similar snapshots -> induction
EPI_RULE_CONFIDENCE_MIN = 0.6         # rule confidence threshold (path B start)
EPI_RULE_CONFIRM_DELTA = (0.02, 0.05)     # consistent outcome: confidence rises slightly
EPI_RULE_CONTRADICT_DELTA = (0.08, 0.15)  # contradictory outcome: confidence drops moderately
EPI_CONSOLIDATION_THRESHOLD = (5, 8)      # experience->persona: threshold breach 5~8
EPI_TRIAL_TICKS = 5                       # observation period 5 ticks
EPI_TRIAL_SHIFT = 0.5                     # trial shift = 0.5 x sign
EPI_TRIAL_MIN_EVENTS = 3                  # >=3 similar events judged positive within the observation period -> permanent write
EPI_FIXATION_RANGE = (0.25, 0.40)         # permanent-write interval
EPI_COUNTER_KEEP_ON_FAIL = 0.5            # permanent-write failure: accumulated count keeps 50%
EPI_TRANSCENDENTAL_DIMS_MIN = 3           # transcendence: >=3 prior dimensions with intensity>0.7 in the same tick
EPI_TRANSCENDENTAL_INTENSITY = 0.7
EPI_TRANSCENDENTAL_VERIFY_TICKS = (5, 15)
EPI_TRANSCENDENTAL_COOLDOWN = 200
# prior-filtered somatic category table (under S-gate jurisdiction)
_PHYSICAL_CATEGORIES = frozenset((
    "loud noise", "ambient sound", "strong light", "touch/pressure", "smell",
    "sudden threat", "clashing blades", "warhorse neighing",
    "own heart rate rising", "physical discomfort", "pain", "hunger",
    "excretion pressure", "system load"))
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class ExperientialRule:
    """experience rule (self-contained)."""
    __slots__ = ("rule_id", "condition_pattern", "expected_outcome", "confidence",
                 "sample_count", "last_updated_tick", "source_experiences",
                 "domain", "odp_direction")
 
    def __init__(self, rule_id: str, theme: str, outcome_valence: float,
                 intent: str, confidence: float, sample_count: int, tick: int,
                 sources: list, domain: str, odp_direction: str) -> None:
        self.rule_id = rule_id
        self.condition_pattern = {"theme": theme}
        self.expected_outcome = {"valence": outcome_valence, "intent": intent}
        self.confidence = confidence
        self.sample_count = sample_count
        self.last_updated_tick = tick
        self.source_experiences = list(sources)
        self.domain = domain
        self.odp_direction = odp_direction
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperientialRule":
        r = cls(str(d.get("rule_id", "ER-0000")),
                str((d.get("condition_pattern") or {}).get("theme", "")),
                float((d.get("expected_outcome") or {}).get("valence", 0.0)),
                str((d.get("expected_outcome") or {}).get("intent", "")),
                float(d.get("confidence", 0.4)), int(d.get("sample_count", 0)),
                int(d.get("last_updated_tick", 0)),
                list(d.get("source_experiences") or []),
                str(d.get("domain", "physical")),
                str(d.get("odp_direction", "")))
        return r
 
 
class ConsolidationEvent:
    """persona permanent-write event (path B)."""
    __slots__ = ("event_id", "odp_direction", "theme", "stage", "trial_shift",
                 "trial_start_tick", "trial_successes", "trial_failures",
                 "fixated_value")
 
    def __init__(self, event_id: str, odp_direction: str, theme: str,
                 trial_shift: float, tick: int) -> None:
        self.event_id = event_id
        self.odp_direction = odp_direction
        self.theme = theme
        self.stage = "trial"
        self.trial_shift = trial_shift
        self.trial_start_tick = tick
        self.trial_successes = 0
        self.trial_failures = 0
        self.fixated_value = 0.0
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConsolidationEvent":
        ev = cls(str(d.get("event_id", "PC-0000")),
                 str(d.get("odp_direction", "")), str(d.get("theme", "")),
                 float(d.get("trial_shift", 0.0)),
                 int(d.get("trial_start_tick", 0)))
        ev.stage = str(d.get("stage", "trial"))
        ev.trial_successes = int(d.get("trial_successes", 0))
        ev.trial_failures = int(d.get("trial_failures", 0))
        ev.fixated_value = float(d.get("fixated_value", 0.0))
        return ev
 
 
class TranscendentalEvent:
    """transcendence event (candidate -> verification -> permanent write)."""
    __slots__ = ("event_id", "involved_dimensions", "predictive_judgment",
                 "tension_description", "created_tick", "verify_deadline_tick",
                 "verified", "fixated")
 
    def __init__(self, event_id: str, dimensions: list, judgment: str,
                 tick: int, deadline: int) -> None:
        self.event_id = event_id
        self.involved_dimensions = list(dimensions)
        self.predictive_judgment = judgment
        self.tension_description = ("if A then B, yet A and B were once "
                                    "thought independent")
        self.created_tick = tick
        self.verify_deadline_tick = deadline
        self.verified: Optional[bool] = None
        self.fixated = False
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TranscendentalEvent":
        ev = cls(str(d.get("event_id", "TE-0000")),
                 list(d.get("involved_dimensions") or []),
                 str(d.get("predictive_judgment", "")),
                 int(d.get("created_tick", 0)),
                 int(d.get("verify_deadline_tick", 0)))
        ev.tension_description = str(d.get("tension_description",
                                           ev.tension_description))
        ev.verified = d.get("verified")
        ev.fixated = bool(d.get("fixated", False))
        return ev
 
 
class EpistemologyEngine:
    """M9 experience-prior-transcendence engine; pure local computation."""
 
    def __init__(self, rng: Any, log: Any, philosophy: Optional[dict] = None,
                 a_priori_plasticity: float = 0.5) -> None:
        self.rng = rng                                            # derived deterministic substream
        self.log = log
        self.plasticity = _clamp(float(a_priori_plasticity))
        # ---- unit layer: naive materialism-idealism fragmented state (global default); the two axes may coexist ----
        phil = philosophy or {}
        score = float(phil.get("politics_score", 0) or 0)
        religion = str(phil.get("religious_belief") or "").strip()
        self.meta_materialism_mid = score > EPI_MATERIALISM_SCORE
        self.meta_idealism_mid = bool(religion)
        self.religious_belief = religion
        # ---- prior regulator state ----
        self.priori = {
            "materialism_level": ("materialism (mid)" if self.meta_materialism_mid
                                  else "naive materialism (low)"),
            "idealism_level": ("idealism (mid)" if self.meta_idealism_mid
                               else "naive idealism (low)"),
            "split_state": not (self.meta_materialism_mid
                                and self.meta_idealism_mid
                                and self.plasticity > 0.7),
            "gate_s": 0.5, "gate_n": 0.5, "gate_t": 0.5, "gate_f": 0.5,
        }
        # ---- experience layer ----
        self.rules: List[ExperientialRule] = []
        self._rule_seq = 0
        self.rule_fail_streak = 0                                 # consecutive epistemic failure count
        self._pending_snapshots: Dict[str, List[Dict[str, Any]]] = {}
        # ---- path B: experience -> persona transfer ----
        self._accumulators: Dict[tuple, int] = {}
        self._thresholds: Dict[tuple, int] = {}
        self.consolidation_events: List[ConsolidationEvent] = []
        self._cons_seq = 0
        self.pending_fixations: List[ConsolidationEvent] = []
        # ---- transcendence layer ----
        self.transcendental_events: List[TranscendentalEvent] = []
        self._trans_seq = 0
        self.last_transcendental_tick = -EPI_TRANSCENDENTAL_COOLDOWN
        self.transcendental_blocked = False                       # alcohol L2+/trauma activation
        self._pending_trans: Optional[TranscendentalEvent] = None  # candidates pending verification
        # alcohol degradation (written by M4 event)
        self.alc_gate_relaxed = False                             # L2 regulator relaxed
        self.alc_induction_paused = False                         # L4 induction suspended
        self.alc_experience_personality_paused = False            # L5 transfer suspended
 
    # ================= unit-layer description =================
    def framework_description(self) -> str:
        if self.meta_materialism_mid and self.meta_idealism_mid:
            base = "materialism (mid) + idealism (mid) coexist"
        elif self.meta_materialism_mid:
            base = "materialism (mid)"
        elif self.meta_idealism_mid:
            base = "idealism (mid)"
        else:
            base = "naive idealist-materialist fragmented state (default)"
        return f"{base}{'[fragmented]' if self.priori['split_state'] else '[integrated]'}"
 
    # ================= prior regulator =================
    def compute_priori_gates(self, btcs_coords: dict) -> Dict[str, Any]:
        """BTCS coordinates extrapolate S/N/T/F moderation values; unit-layer stance fine-tuning; alcohol L2 global x0.85."""
        sn = float(btcs_coords.get("SN", 50.0))
        tf = float(btcs_coords.get("TF", 50.0))
        g_s = _clamp(1.0 - (sn - 20.0) / 60.0)    # SN high(N) -> S gate small
        g_n = _clamp((sn - 20.0) / 60.0)          # SN high(N) -> N gate large
        g_t = _clamp((tf - 20.0) / 60.0)          # TF high(T) -> T gate large
        g_f = _clamp(1.0 - (tf - 20.0) / 60.0)    # TF high(T) -> F gate small
        if self.meta_materialism_mid and self.meta_idealism_mid:
            g_t *= EPI_META_RELAX
            g_f *= EPI_META_RELAX
        elif self.meta_materialism_mid:
            g_t *= EPI_META_RELAX
            g_f *= EPI_META_TIGHTEN
        elif self.meta_idealism_mid:
            g_f *= EPI_META_RELAX
            g_t *= EPI_META_TIGHTEN
        if self.alc_gate_relaxed:                             # alcohol L2: regulator relaxed
            g_s, g_n = g_s * EPI_META_RELAX, g_n * EPI_META_RELAX
            g_t, g_f = g_t * EPI_META_RELAX, g_f * EPI_META_RELAX
        self.priori["gate_s"] = round(_clamp(g_s), 3)
        self.priori["gate_n"] = round(_clamp(g_n), 3)
        self.priori["gate_t"] = round(_clamp(g_t), 3)
        self.priori["gate_f"] = round(_clamp(g_f), 3)
        return self.priori
 
    def priori_filter(self, category: str, intensity: float,
                      emotional: bool = False) -> float:
        """prior filter (service port m9.priori_filter; K.columnar P3-0 picks up)."""
        physical = category in _PHYSICAL_CATEGORIES
        if emotional and self.priori["gate_t"] > 0.6:       # T high -> filters emotional content
            return intensity * (1.0 - (self.priori["gate_t"] - 0.6))
        if not emotional and self.priori["gate_f"] > 0.6:   # F high -> filters non-personalized information
            return intensity * (1.0 - (self.priori["gate_f"] - 0.6) * 0.5)
        if physical:
            return intensity * (0.7 + 0.6 * self.priori["gate_s"])
        return intensity * (0.7 + 0.6 * self.priori["gate_n"])
 
    # ================= experience layer: snapshot accumulation and induction =================
    def feed_snapshot(self, tick: int, theme: str, valence: float, intent: str,
                      memory_id: str = "", odp_direction: str = "",
                      domain: str = "physical") -> None:
        if self.alc_induction_paused:                         # alcohol L4: induction suspended
            return
        sig = f"{theme}:{odp_direction or '-'}"
        buf = self._pending_snapshots.setdefault(sig, [])
        buf.append({"tick": tick, "theme": theme, "valence": valence,
                    "intent": intent, "memory_id": memory_id,
                    "domain": domain, "odp_direction": odp_direction})
        if len(buf) >= EPI_INDUCTION_MIN_SAMPLES:
            self._induce_rule(tick, sig, buf)
 
    def _induce_rule(self, tick: int, sig: str, buf: list) -> None:
        """induction trigger: same kind >=3 and same-direction valence share >=2/3 (statistically significant)."""
        pos = sum(1 for s in buf if s["valence"] > 0.1)
        neg = sum(1 for s in buf if s["valence"] < -0.1)
        if max(pos, neg) < len(buf) * 2 / 3:
            self._pending_snapshots[sig] = buf[-1:]         # no salience -> keep the newest and re-accumulate
            return
        outcome_valence = 0.5 if pos >= neg else -0.5
        theme = buf[0]["theme"]
        existing = next((r for r in self.rules
                         if r.condition_pattern.get("theme") == theme
                         and r.odp_direction == buf[0]["odp_direction"]), None)
        if existing is not None:
            same_sign = ((existing.expected_outcome.get("valence", 0.0) > 0)
                         == (outcome_valence > 0))
            if same_sign:
                existing.confidence = round(_clamp(
                    existing.confidence
                    + self.rng.uniform(*EPI_RULE_CONFIRM_DELTA)), 3)
                self.rule_fail_streak = 0
            else:
                existing.confidence = round(_clamp(
                    existing.confidence
                    - self.rng.uniform(*EPI_RULE_CONTRADICT_DELTA)), 3)
                self.rule_fail_streak += 1                  # consecutive epistemic failures
            existing.sample_count += len(buf)
            existing.last_updated_tick = tick
            existing.source_experiences.extend(s["memory_id"] for s in buf
                                               if s["memory_id"])
            self._pending_snapshots[sig] = []
            self.log.record(tick, "M9.experience", "rule update",
                            f"{existing.rule_id} confidence={existing.confidence:.2f} "
                            f"n={existing.sample_count}")
            return
        self._rule_seq += 1
        rule = ExperientialRule(
            f"ER-{self._rule_seq:04d}", theme, outcome_valence,
            buf[-1]["intent"],
            0.4 + 0.1 * min(3, len(buf) - EPI_INDUCTION_MIN_SAMPLES),
            len(buf), tick,
            [s["memory_id"] for s in buf if s["memory_id"]],
            buf[0]["domain"], buf[0]["odp_direction"])
        self.rules.append(rule)
        self._pending_snapshots[sig] = []
        self.log.record(tick, "M9.experience", "rule induction",
                        f"{rule.rule_id} '{theme}' confidence={rule.confidence:.2f} "
                        f"n={rule.sample_count}")
 
    def query_rules(self, tick: int, theme: str,
                    odp_direction: str = "") -> list:
        hits = [r for r in self.rules
                if r.condition_pattern.get("theme") == theme
                or (odp_direction and r.odp_direction == odp_direction)]
        hits = [r for r in hits if r.confidence >= 0.3]
        hits.sort(key=lambda r: -r.confidence)
        if hits:
            self.log.record(tick, "M9.experience", "rule hit",
                            [f"{r.rule_id}(c={r.confidence:.2f})" for r in hits[:2]])
        return hits[:2]
 
    def danger_assessment(self, tick: int, theme: str) -> float:
        """M8 cascade retrieval (2): experience and priors -> danger assessment [0,1]."""
        hits = self.query_rules(tick, theme)
        if not hits:
            return 0.3
        worst = min(r.expected_outcome.get("valence", 0.0) for r in hits)
        return round(_clamp(0.5 + abs(worst) * 0.5 if worst < 0 else 0.2), 3)
 
    # ================= path B: experience -> persona transfer =================
    def tick_consolidation(self, tick: int) -> None:
        """background maintenance: accumulate -> breach (5~8) -> observation (5 ticks) -> permanent write / rollback; alcohol L5 suspends."""
        if self.alc_experience_personality_paused:
            return
        for r in self.rules:                                  # stage 1: accumulation
            if (r.confidence <= EPI_RULE_CONFIDENCE_MIN
                    or r.sample_count < EPI_INDUCTION_MIN_SAMPLES):
                continue
            key = (r.odp_direction or r.rule_id,
                   r.condition_pattern.get("theme", ""))
            if any(e.stage == "trial" and e.odp_direction == key[0]
                   and e.theme == key[1] for e in self.consolidation_events):
                continue
            self._accumulators[key] = self._accumulators.get(key, 0) + 1
            threshold = self._thresholds.setdefault(
                key, self._randint(*EPI_CONSOLIDATION_THRESHOLD))
            if self._accumulators[key] >= threshold:            # stage 2: threshold breach -> observation period
                self._begin_trial(tick, key, r)
        for ev in self.consolidation_events:                    # stages 3~4: permanent-write judgment
            if ev.stage != "trial":
                continue
            if tick - ev.trial_start_tick >= EPI_TRIAL_TICKS:
                self._judge_fixation(tick, ev)
 
    def _randint(self, lo: int, hi: int) -> int:
        """deterministic integer draw (the derived stream has no randint; implemented via random)."""
        return lo + min(hi - lo, int(self.rng.random() * (hi - lo + 1)))
 
    def _begin_trial(self, tick: int, key: tuple,
                     rule: ExperientialRule) -> None:
        sign = 1.0 if rule.expected_outcome.get("valence", 0.0) > 0 else -1.0
        self._cons_seq += 1
        ev = ConsolidationEvent(f"PC-{self._cons_seq:04d}", key[0], key[1],
                                EPI_TRIAL_SHIFT * sign, tick)
        self.consolidation_events.append(ev)
        self._accumulators[key] = 0
        self.log.record(tick, "M9.pathway B", "threshold breach -> trial",
                        f"{ev.event_id} direction={key[0]} theme '{key[1]}' "
                        f"shift={ev.trial_shift:+.1f} (5 ticks)")
 
    def feed_trial_outcome(self, tick: int, odp_direction: str, theme: str,
                           positive: bool,
                           trauma_activated: bool = False) -> None:
        """outcome-correction assessment of similar events within the observation period (service port m9.feed_trial_outcome)."""
        for ev in self.consolidation_events:
            if (ev.stage == "trial" and ev.odp_direction == odp_direction
                    and ev.theme == theme):
                if positive and not trauma_activated:
                    ev.trial_successes += 1
                else:
                    ev.trial_failures += 1
 
    def _judge_fixation(self, tick: int, ev: ConsolidationEvent) -> None:
        """stage 4: >=3 corrections judged positive within the observation period -> permanent write (x0.5~0.8);
                failure -> no permanent write, accumulated count keeps 50%.        """
        if ev.trial_successes >= EPI_TRIAL_MIN_EVENTS and ev.trial_failures == 0:
            ev.stage = "fixated"
            ev.fixated_value = round(_clamp(
                ev.trial_shift * self.rng.uniform(*EPI_FIXATION_RANGE) / 0.5,
                -0.40, 0.40), 3)
            self.pending_fixations.append(ev)
            self.log.record(tick, "M9.pathway B", "personality consolidation",
                            f"{ev.event_id} direction={ev.odp_direction} "
                            f"permanent write {ev.fixated_value:+.2f}")
        else:
            ev.stage = "rolled_back"
            key = (ev.odp_direction, ev.theme)
            self._accumulators[key] = int(
                self._thresholds.get(key, 6) * EPI_COUNTER_KEEP_ON_FAIL)
            self.log.record(tick, "M9.pathway B", "consolidation failure rollback",
                            f"{ev.event_id} shift zeroed, counter kept 50%")
 
    def trial_shift_for(self, odp_direction: str) -> float:
        return sum(ev.trial_shift for ev in self.consolidation_events
                   if ev.stage == "trial" and ev.odp_direction == odp_direction)
 
    # ---- permanent write-back (ABMI 1.0 localized: persona port direct write + M6 wake, not via the hub) ----
    def _apply_fixations(self, tick: int) -> None:
        while self.pending_fixations:
            ev = self.pending_fixations.pop(0)
            if self._odp is not None and ev.odp_direction:
                self._odp.drift(ev.odp_direction, ev.fixated_value)
            if self._services is not None:                      # M6 persona-permanent-write wake
                self._services.call("m6.detect", "persona fixation write-back",
                                    None, default=None)
            self.log.record(tick, "M9.pathway B", "fixation written back",
                            f"{ev.event_id} {ev.odp_direction} "
                            f"{ev.fixated_value:+.2f}")
 
    # ================= transcendence layer =================
    def check_transcendental(self, tick: int, active_dimensions: list,
                             tension: bool, predictive_judgment: str,
                             trauma_active: bool = False
                             ) -> Optional[TranscendentalEvent]:
        """trigger conditions (all required): (1) >=3 prior dimensions with intensity>0.7 in the same tick (2) associative tension (3) predictive judgment
                (4) verification within 5~15 ticks; cooldown >=200 ticks; not triggerable under alcohol L2+/trauma activation.        """
        if self.transcendental_blocked or trauma_active:
            return None
        if tick - self.last_transcendental_tick < EPI_TRANSCENDENTAL_COOLDOWN:
            return None
        strong = [d for d in active_dimensions
                  if float(d.get("intensity", 0.0)) >= EPI_TRANSCENDENTAL_INTENSITY]
        if (len(strong) < EPI_TRANSCENDENTAL_DIMS_MIN or not tension
                or not predictive_judgment):
            return None
        self._trans_seq += 1
        ev = TranscendentalEvent(
            f"TE-{self._trans_seq:04d}",
            [d["name"] for d in strong], predictive_judgment, tick,
            tick + self._randint(*EPI_TRANSCENDENTAL_VERIFY_TICKS))
        self.transcendental_events.append(ev)
        self.log.record(tick, "M9.transcendence", "candidate event",
                        f"{ev.event_id} dimensions={ev.involved_dimensions} "
                        f"prediction [{predictive_judgment}] pending (T+"
                        f"{ev.verify_deadline_tick})")
        return ev
 
    def verify_transcendental(self, tick: int, event_id: str,
                              verified: bool) -> bool:
        """verification passed -> permanent write: multi-dimensional prior-association write + fragmented state may temporarily integrate (plasticity>0.7 -> permanent)."""
        for ev in self.transcendental_events:
            if ev.event_id != event_id or ev.verified is not None:
                continue
            if tick > ev.verify_deadline_tick:
                ev.verified = False
                return False
            ev.verified = verified
            if verified:
                ev.fixated = True
                self.last_transcendental_tick = tick
                if self.plasticity > 0.7:
                    self.priori["split_state"] = False      # philosophical training -> permanent integration
                self.log.record(tick, "M9.transcendence",
                                "verified -> prior rewrite",
                                f"{event_id} fixated "
                                f"(split={self.priori['split_state']})")
                return True
            return False
        return False
 
    # ================= alcohol degradation write (alcohol.degradation event) =================
    def apply_alcohol_degradation(self, d: Dict[str, Any]) -> None:
        self.alc_gate_relaxed = int(d.get("tier", 0)) >= 2
        self.alc_induction_paused = bool(d.get("experience_induction_paused", False))
        self.transcendental_blocked = bool(d.get("transcendental_blocked", False))
        self.alc_experience_personality_paused = bool(
            d.get("experience_personality_paused", False))
 
    # ================= hook: P2 gate estimation =================
    def on_boundary(self, tick: int, data: Dict[str, Any]) -> None:
        coords = self._btcs.copy_coords() if self._btcs is not None else {}
        gates = self.compute_priori_gates(coords)
        self._board.publish("M9.epistemology.gate_t", gates["gate_t"])  # mirror
        self._board.publish("M9.epistemology.gates", dict(gates))
 
    # ================= hook: P4 snapshot/rule query/transcendence =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        emotion = board.read("K.emotion.state", {}) or {}
        themes = tuple(data.get("themes") or
                       board.read("sys.last_scene_themes", ()) or ())
        theme = themes[0] if themes else ""
        valence = float(emotion.get("valence", 0.0))
        intent = str(board.read("sys.last_strategy_name", ""))
        if theme:
            self.feed_snapshot(tick, theme, valence, intent)
            self.query_rules(tick, theme)
        # ---- transcendence layer: pending-verification advance / new-candidate check ----
        if self._pending_trans is not None:
            ev = self._pending_trans
            if valence > 0.3:
                if self.verify_transcendental(tick, ev.event_id, True):
                    if self._services is not None:              # trauma integration advance
                        self._services.call("m8.integrate", tick,
                                            pathway="transcendental",
                                            default=None)
                    if self._btcs is not None:                  # persona permanent shift
                        self._btcs.drift("JP",
                                         -0.5 if valence > 0 else 0.5)
                    self._pending_trans = None
            elif tick > ev.verify_deadline_tick:
                self.verify_transcendental(tick, ev.event_id, False)
                self._pending_trans = None
        else:
            srf = 0.0
            if self._hormones is not None:
                srf = float(self._hormones.compute_effective_levels().get(
                    "SM_SRF", 0.0))
            urgency = float(data.get("urgency", 0.0))
            dims = [
                {"name": "emotional intensity", "intensity": abs(valence)},
                {"name": "arousal intensity",
                 "intensity": float(emotion.get("arousal", 0.0))},
                {"name": "stress intensity", "intensity": srf / 100.0},
                {"name": "scene urgency", "intensity": urgency / 3.0},
            ]
            tension = bool(data.get("objective_conflict")) or bool(
                board.read("M6.odp.mark"))
            if tension and urgency >= 2.0 and theme:
                judgment = f"the course of [{theme}] harbors a hidden structure"
                ev2 = self.check_transcendental(
                    tick, dims, tension, judgment,
                    trauma_active=bool(board.read("M8.trauma.active", False)))
                if ev2 is not None:
                    self._pending_trans = ev2
        board.publish("M9.epistemology.fail_streak", self.rule_fail_streak)
 
    # ================= hook: P6 path-B permanent write + write-back =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.tick_consolidation(tick)
        self._apply_fixations(tick)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"plasticity": self.plasticity,
                "meta_materialism_mid": self.meta_materialism_mid,
                "meta_idealism_mid": self.meta_idealism_mid,
                "religious_belief": self.religious_belief,
                "priori": dict(self.priori),
                "rules": [r.to_dict() for r in self.rules],
                "rule_seq": self._rule_seq,
                "rule_fail_streak": self.rule_fail_streak,
                "pending_snapshots": {k: [dict(s) for s in v]
                                      for k, v in self._pending_snapshots.items()},
                "accumulators": {f"{k[0]}|{k[1]}": v
                                 for k, v in self._accumulators.items()},
                "thresholds": {f"{k[0]}|{k[1]}": v
                               for k, v in self._thresholds.items()},
                "consolidation_events": [e.to_dict()
                                         for e in self.consolidation_events],
                "cons_seq": self._cons_seq,
                "pending_fixations": [e.to_dict() for e in self.pending_fixations],
                "transcendental_events": [e.to_dict()
                                          for e in self.transcendental_events],
                "trans_seq": self._trans_seq,
                "last_transcendental_tick": self.last_transcendental_tick,
                "transcendental_blocked": self.transcendental_blocked,
                "pending_trans": (self._pending_trans.to_dict()
                                  if self._pending_trans else None),
                "alc": {"gate_relaxed": self.alc_gate_relaxed,
                        "induction_paused": self.alc_induction_paused,
                        "experience_personality_paused":
                            self.alc_experience_personality_paused},
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.plasticity = _clamp(float(snap.get("plasticity", 0.5)))
        self.meta_materialism_mid = bool(snap.get("meta_materialism_mid", False))
        self.meta_idealism_mid = bool(snap.get("meta_idealism_mid", False))
        self.religious_belief = str(snap.get("religious_belief", ""))
        self.priori.update(snap.get("priori") or {})
        self.rules = [ExperientialRule.from_dict(d)
                      for d in (snap.get("rules") or [])]
        self._rule_seq = int(snap.get("rule_seq", 0))
        self.rule_fail_streak = int(snap.get("rule_fail_streak", 0))
        self._pending_snapshots = {
            str(k): [dict(s) for s in v]
            for k, v in (snap.get("pending_snapshots") or {}).items()}
        self._accumulators = {tuple(str(k).split("|", 1)): int(v)
                              for k, v in (snap.get("accumulators") or {}).items()}
        self._thresholds = {tuple(str(k).split("|", 1)): int(v)
                            for k, v in (snap.get("thresholds") or {}).items()}
        self.consolidation_events = [ConsolidationEvent.from_dict(d)
                                     for d in (snap.get("consolidation_events") or [])]
        self._cons_seq = int(snap.get("cons_seq", 0))
        self.pending_fixations = [ConsolidationEvent.from_dict(d)
                                  for d in (snap.get("pending_fixations") or [])]
        self.transcendental_events = [TranscendentalEvent.from_dict(d)
                                      for d in (snap.get("transcendental_events")
                                                or [])]
        self._trans_seq = int(snap.get("trans_seq", 0))
        self.last_transcendental_tick = int(
            snap.get("last_transcendental_tick", -EPI_TRANSCENDENTAL_COOLDOWN))
        self.transcendental_blocked = bool(snap.get("transcendental_blocked", False))
        pt = snap.get("pending_trans")
        self._pending_trans = (TranscendentalEvent.from_dict(pt)
                               if isinstance(pt, dict) else None)
        alc = snap.get("alc") or {}
        self.alc_gate_relaxed = bool(alc.get("gate_relaxed", False))
        self.alc_induction_paused = bool(alc.get("induction_paused", False))
        self.alc_experience_personality_paused = bool(
            alc.get("experience_personality_paused", False))
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return isinstance(self.rules, list) and isinstance(self.priori, dict)
 
    def invariants(self) -> bool:
        gates = (self.priori.get("gate_s", 0.5), self.priori.get("gate_n", 0.5),
                 self.priori.get("gate_t", 0.5), self.priori.get("gate_f", 0.5))
        if not all(0.0 <= g <= 1.0 for g in gates):
            return False
        return all(0.0 <= r.confidence <= 1.0 for r in self.rules)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"rules": [f"{r.rule_id} '{r.condition_pattern.get('theme', '')}' "
                          f"c={r.confidence:.2f}" for r in self.rules[:3]],
                "framework": self.framework_description(),
                "fail_streak": self.rule_fail_streak}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> EpistemologyEngine:
        engine = EpistemologyEngine(ctx.rng_for("m9_epistemology"), ctx.log,
                                    ctx.k.card.philosophy,
                                    ctx.k.card.a_priori_plasticity)
        engine._board = ctx.board
        engine._services = ctx.services
        engine._btcs = ctx.k.btcs
        engine._odp = ctx.k.odp
        engine._hormones = ctx.k.hormones
        return engine
 
    def bind(inst: EpistemologyEngine, ctx: Any) -> Dict[str, Any]:
        # K.columnar is called with zero args to fetch the filter body (fn(cat, intensity) is called at the use site),
        # so the provider is a factory lambda; external modules may also call with zero args to obtain the filter.
        ctx.services.offer("m9.priori_filter", lambda: inst.priori_filter)  # K.columnar picks up itself
        ctx.services.offer("m9.danger_assessment", inst.danger_assessment)
        ctx.services.offer("m9.feed_trial_outcome", inst.feed_trial_outcome)
        ctx.services.offer("m9.check_transcendental", inst.check_transcendental)
        ctx.services.offer("m9.verify_transcendental", inst.verify_transcendental)
        ctx.services.offer("m9.worldview",
                           lambda: (inst.meta_materialism_mid,
                                    inst.religious_belief))
        ctx.bus.subscribe(
            "alcohol.degradation",
            lambda item: inst.apply_alcohol_degradation(
                item.get("payload") or {}),
            owner="M9.epistemology")
        return {
            "P2_boundary": inst.on_boundary,
            "P4_decision": inst.on_decision,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "M9.epistemology",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.gate_t", "sys.fail_streak"),         # contract key committed write
        "gear": {
            "P2_boundary": {"every": 1, "trigger": None},           # gates run constantly
            "P4_decision": {"every": 1, "trigger": None},
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P2_boundary": 5,                            # before columnar encoding (P3-0)
                       "P4_decision": 30, "P6_maintenance": 60},
        "factory": factory,
        "bind": bind,
        "provides": ("m9.priori_filter", "m9.danger_assessment",
                     "m9.worldview", "sys.gate_t", "sys.fail_streak"),
        "requires": {"soft": {"m8.integrate": None, "m6.detect": None,
                              "K.emotion.state": None}},
        "report_key": "epistemology",
        "snapshot_label": "m9_epistemology",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
