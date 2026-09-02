# -*- coding: utf-8 -*-
"""M4.alcohol — physiology-domain DLC (alcohol metabolism submodule: ABMI 1.0 re-engineering of legacy metabolic.py AlcoholSubsystem)

Role:
  - zero-order kinetics: constant-rate elimination ~0.015% BAC/h x liver metabolism"""
from __future__ import annotations
from typing import Any, Dict, Optional
 
ALC_ELIMINATION_RATE_PER_HOUR = 0.015       # zero-order elimination rate (%BAC/h)
ALC_VD_MALE = 0.7                           # volume of distribution: male
ALC_VD_FEMALE = 0.6                         # volume of distribution: female
ALC_LIVER_CAPACITY = {"never": 0.8, "occasional": 1.0,
                      "frequent": 1.3, "dependent": 1.4}
ALC_DRINK_TO_BAC = 0.025                    # 1 standard drink -> baseline BAC% (70kg/Vd=0.7 equivalent)
ALC_TOLERANCE_FROM_HISTORY = {"never": 0.0, "occasional": 0.3,
                              "frequent": 0.6, "dependent": 0.85}
ALC_TIER_BOUNDARIES = (0.03, 0.06, 0.10, 0.15, 0.20, 0.25, 0.30)  # L1~L7 lower bounds
ALC_EMOTION_AMPLIFY_BASE = 0.06           # emotion-amplification onset BAC baseline
ALC_RESPIRATORY_DANGER = 0.35               # >0.35 respiratory-center suppression -> life-threatening
ALC_HANGOVER_HOURS = (6.0, 12.0)            # hangover-equivalent duration window
ALC_HANGOVER_FATIGUE_MULT = 1.3             # hangover: fatigue +30%
ALC_HANGOVER_COGNITIVE_DELAY = 0.2          # hangover: cognitive delay +20%
ALC_HANGOVER_VALENCE_BIAS = (-0.2, -0.1)    # hangover: valence depression interval
ALC_EMOTION_AMPLIFY_BASE = 0.06             # emotion amplification starts at BAC>0.06
# withdrawal monitoring (dependents only): (start h, end h, stage)
ALC_WITHDRAWAL_STAGES = (
    (6.0, 12.0, "mild"),        # anxiety valence -0.2, tremor fine motor x0.8
    (12.0, 24.0, "moderate"),   # ODP aggression direction +0.2, social function decline
    (24.0, 72.0, "severe"),     # consciousness-suppression level-one risk, hallucination-like signal
)
# pull-model self-selection: drinking keywords (module-selected, no dependence on upstream pushes)
ALC_DRINK_WORDS = frozenset((
    "喝", "酒", "醉", "干杯", "啤", "白酒", "红酒", "威士忌", "伏特加", "清酒",
    "drink", "drinking", "drunk", "beer", "wine", "whiskey", "vodka",
))
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class AlcoholSubsystem:
    """M4 alcohol: zero-order elimination + seven-tier power-down + hangover + withdrawal; pure local computation."""
 
    def __init__(self, log: Any, profile: Optional[dict] = None,
                 body_metrics: Optional[dict] = None) -> None:
        self.log = log
        prof = profile or {}
        bm = body_metrics or {}
        self.history = prof.get("drinking_history", "occasional")
        if self.history not in ALC_LIVER_CAPACITY:
            self.history = "occasional"
        self.tolerance = _clamp(float(prof.get(
            "tolerance_level", ALC_TOLERANCE_FROM_HISTORY.get(self.history, 0.3))))
        self.sensitivity = _clamp(float(prof.get("alcohol_sensitivity", 0.5)))
        self.behavioral_profile = prof.get("behavioral_profile", "social")
        sex = bm.get("sex", "M")
        self.vd = ALC_VD_MALE if sex == "M" else ALC_VD_FEMALE
        self.weight_kg = float(bm.get("weight_kg", 70.0 if sex == "M" else 55.0))
        # ---- state ----
        self.bac = 0.0                      # blood alcohol concentration %
        self.tier = 0                       # seven-tier power-down level
        self.unconscious = False
        self.respiratory_danger = False
        self.drinks_consumed = 0.0
        self.hours_since_last_drink = 0.0
        self.hangover = False
        self.hangover_hours_left = 0.0
        self.withdrawal_stage = ""
        self._last_drink_tick = -1
        self._was_drunk = False             # once reached L2+ -> delayed settlement triggered after waking
        self.pending_delayed_settlement = False
        # word-pool signature dedup: no upstream input -> sleep; word pool lingers on the board; the same pool is ingested only once;
        # any pool change (even an old sentence reappearing) counts as new input
        self._last_words_sig: tuple = ()
 
    # ================= ingestion =================
    def ingest(self, tick: int, drinks: float = 1.0, reason: str = "") -> float:
        """standard drinks ingested -> BAC rise (corrected by distribution volume/weight/sensitivity/tolerance)."""
        if drinks <= 0:
            return self.bac
        weight_factor = 70.0 / max(40.0, self.weight_kg)
        vd_factor = ALC_VD_MALE / max(0.45, self.vd)
        sens_factor = 0.6 + 0.8 * self.sensitivity
        tol_factor = 1.0 - 0.4 * self.tolerance
        delta = drinks * ALC_DRINK_TO_BAC * weight_factor * vd_factor \
            * sens_factor * tol_factor
        self.bac = round(max(0.0, self.bac + delta), 4)
        self.drinks_consumed += drinks
        self.hours_since_last_drink = 0.0
        self._last_drink_tick = tick
        if self.hangover:                   # drinking again during hangover -> hangover lifted (BAC dominates again)
            self.hangover = False
            self.hangover_hours_left = 0.0
        self.log.record(tick, "M4.alcohol", "intake",
                        f"{drinks} drinks -> BAC={self.bac:.3f}% {reason}")
        return self.bac
 
    # ================= metabolism advance (zero-order kinetics) =================
    def advance(self, tick: int, dt_minutes: float) -> None:
        dt_h = dt_minutes / 60.0
        if self.bac > 0.0:
            self.bac = round(max(0.0, self.bac - ALC_ELIMINATION_RATE_PER_HOUR
                                 * ALC_LIVER_CAPACITY.get(self.history, 1.0)
                                 * dt_h), 4)
        else:
            self.hours_since_last_drink += dt_h
        old_tier = self.tier
        self.tier = self._tier_of(self.bac)
        self.unconscious = self.tier >= 7
        self.respiratory_danger = self.bac > ALC_RESPIRATORY_DANGER
        if self.tier >= 2:
            self._was_drunk = True
        # BAC cleared -> hangover phase (for the once-drunk)
        if self.bac <= 0.0 and self._was_drunk and not self.hangover:
            self.hangover = True
            self.hangover_hours_left = ALC_HANGOVER_HOURS[1]
            if not self.pending_delayed_settlement:
                self.pending_delayed_settlement = True            # post-waking delayed moral settlement
            self.log.record(tick, "M4.alcohol", "entering hangover phase",
                            "fatigue +30%, cognitive delay +20%, lower valence")
        if self.hangover:
            self.hangover_hours_left = max(0.0, self.hangover_hours_left - dt_h)
            if self.hangover_hours_left <= 0.0:
                self.hangover = False
                self._was_drunk = False
                self.log.record(tick, "M4.alcohol", "hangover subsides",
                                "alcohol submodule going dormant")
        if self.tier != old_tier:
            self.log.record(tick, "M4.alcohol", "tier switch",
                            f"L{old_tier} -> L{self.tier} (BAC={self.bac:.3f}%)")
        self.withdrawal_stage = self._withdrawal_stage_of(self.hours_since_last_drink)
 
    @staticmethod
    def _tier_of(bac: float) -> int:
        tier = 0
        for i, bound in enumerate(ALC_TIER_BOUNDARIES):
            if bac >= bound:
                tier = i + 1
        return tier
 
    def _withdrawal_stage_of(self, hours: float) -> str:
        if self.history != "dependent" or self.bac > 0.0:
            return ""
        for lo, hi, name in ALC_WITHDRAWAL_STAGES:
            if lo <= hours < hi:
                return name
        return ""
 
    # ================= seven-tier progressive power-down effect table =================
    def degradation(self) -> Dict[str, Any]:
        """emit the module function-degradation vector for the current tier (published to the board; the kernel reads sys.* via the mirror)."""
        t = self.tier
        d: Dict[str, Any] = {
            "tier": t, "unconscious": t >= 7,
            "respiratory_danger": self.respiratory_danger,
            "self_monitoring_delta": 0.0, "fine_motor_mult": 1.0,
            "boundary_permeability_mult": 1.0, "override_threshold_mult": 1.0,
            "behavior_leak_mult": 1.0, "emotion_amplify_mult": 1.0,
            "language_disinhibited": False, "moral_rigidity_delta": 0.0,
            "trigger_sensitivity_mult": 1.0, "attention_jump_mult": 1.0,
            "gross_motor_impairment": 0.0, "blackout": False,
            "identity_check_paused": False, "experience_induction_paused": False,
            "behavior_random": False, "trauma_integration_paused": False,
            "transcendental_blocked": False, "experience_personality_paused": False,
            "station2_disconnected": False, "consciousness_suppression": 0.0,
            "surface_capacity": 6, "columnar_query_cut": False,
            "response_delay_mult": 1.0,
        }
        if t >= 1:   # L1: self-monitoring down, fine motor mildly degraded
            d["self_monitoring_delta"] = -0.15
            d["fine_motor_mult"] = 0.9
        if t >= 2:   # L2: prior gate loosened, permeability +30%, override threshold -25%, leakage x1.5, emotion amplification x1.2
            d.update(self_monitoring_delta=-0.25,
                     boundary_permeability_mult=1.3,
                     override_threshold_mult=0.75,
                     behavior_leak_mult=1.5,
                     emotion_amplify_mult=1.2,
                     language_disinhibited=True)
        if t >= 3:   # L3: moral rigidity -0.3, trigger sensitivity +20%, attention jump x2, gross motor impaired
            d.update(self_monitoring_delta=-0.35, moral_rigidity_delta=-0.3,
                     trigger_sensitivity_mult=1.2, attention_jump_mult=2.0,
                     gross_motor_impairment=0.4)
        if t >= 4:   # L4: memory encoding fragmented (blackout), identity check suspended, behavior near-random
            d.update(self_monitoring_delta=-0.55, blackout=True,
                     identity_check_paused=True,
                     experience_induction_paused=True, behavior_random=True)
        if t >= 5:   # L5: trauma integration suspended, transcendence untriggerable, Station 2 near-disconnected
            d.update(trauma_integration_paused=True, transcendental_blocked=True,
                     experience_personality_paused=True, station2_disconnected=True)
        if t >= 6:   # L6: consciousness suppression level one, surface capacity 6->2, columnar queries mostly cut, delay x4
            d.update(consciousness_suppression=0.6, surface_capacity=2,
                     columnar_query_cut=True, response_delay_mult=4.0)
        if t >= 7:   # L7: hard unconsciousness threshold
            d.update(unconscious=True, consciousness_suppression=0.99)
        if self.withdrawal_stage == "mild":   # withdrawal tremor: fine motor x0.8
            d["fine_motor_mult"] = min(d["fine_motor_mult"], 0.8)
        return d
 
    @property
    def active(self) -> bool:
        return self.bac > 0.0 or self.hangover or bool(self.withdrawal_stage)
 
    def emotion_amplification(self) -> float:
        """V4.2 emotion_amplification: BAC>0.06 -> 1.0 + BAC x0.05 x10."""
        if self.bac > ALC_EMOTION_AMPLIFY_BASE:
            return round(1.0 + self.bac * 0.05 * 10.0, 4)
        return 1.0
 
    # ================= P1 hook =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        self._pull_ingest(tick)                                 # pull model: self-selected drinking words
        self.advance(tick, float(data.get("dt", 0.0)))
        board, d = self._board, self.degradation()
        # ---- publish: legacy keys auto-mirrored to sys.* via the contract mirror (kernel untouched) ----
        board.publish("M4.alcohol.deg_start.unconscious",
                      d["unconscious"] if self.active else False)
        board.publish("M4.alcohol.bac", self.bac)
        board.publish("M4.alcohol.tier", self.tier)
        board.publish("M4.alcohol.degradation", d)
        for k in ("unconscious", "columnar_query_cut", "language_disinhibited",
                  "behavior_random", "response_delay_mult", "attention_jump_mult",
                  "station2_disconnected", "blackout"):
            board.publish(f"M4.alcohol.deg.{k}", d[k])
        # ---- shared soft keys: recompute the baseline from scratch (M1 archive + M3 contract key), then add own component ----
        # never reads the shared channel's current value — this module may be absent/asleep; reading the live value would accumulate across ticks (not idempotent)
        cidx = float(board.read("sys.cognitive_index", 0.0))
        m1v = float(board.read_knob("knob.m1.valence_bias", 0.0))
        m5c = float(board.read_knob("knob.m5.valence_contrib", 0.0))  # M5 social-status component
        pressure = 1.0 + cidx
        valence = m1v + m5c - 0.3 * cidx
        if self.hangover:                                       # hangover: fatigue + valence depression
            pressure *= ALC_HANGOVER_FATIGUE_MULT
            valence += sum(ALC_HANGOVER_VALENCE_BIAS) / 2.0
            board.write_knob("knob.m4.hangover_cognitive_mult",
                             1.0 - ALC_HANGOVER_COGNITIVE_DELAY, owner="M4.alcohol")
        elif self.withdrawal_stage:                             # withdrawal: valence depression
            valence += {"mild": -0.2, "moderate": -0.25,
                        "severe": -0.4}.get(self.withdrawal_stage, 0.0)
            if self.withdrawal_stage == "moderate":             # moderate withdrawal: aggression direction +0.2
                board.publish("M4.alcohol.odp_nudges", {"A09": 0.2})
        board.write_knob("knob.s_pressure_mult", pressure, owner="M4.alcohol")
        board.write_knob("knob.valence_bias", valence, owner="M4.alcohol")
        # emotion amplification multiplier (legacy emotion_amplification: BAC>0.06 -> 1+BAC*0.5)
        board.publish("M4.alcohol.emotion_amplification",
                      self.emotion_amplification())
        # ---- consciousness suppression / motor impairment (read directly by K.attention/K.language/K.hub; rewritten every active tick to prevent residue) ----
        suppression = d["consciousness_suppression"]
        if self.withdrawal_stage == "severe":                   # severe withdrawal: suppression >= 0.5
            suppression = max(suppression, 0.5)
        board.write_knob("knob.consciousness_suppression",
                         suppression, owner="M4.alcohol")
        board.write_knob("knob.motor_impairment",
                         d["gross_motor_impairment"], owner="M4.alcohol")
        # ---- degradation vector dispatch: subscribed by M7 iceberg etc. (event bus, dict payload) ----
        if self._bus is not None:
            self._bus.emit("alcohol.degradation", d, source="M4.alcohol")
        # ---- delayed moral settlement: mailbox semantics, subscribed by M10 ----
        if self.pending_delayed_settlement and self._bus is not None:
            self._bus.emit("alcohol.delayed_settlement",
                           {"tick": tick, "bac_peak_tier": self.tier},
                           source="M4.alcohol")
 
    # ---- pull-model ingestion: pick drinking words from the language word pool (the publisher knows no module) ----
    def _pull_ingest(self, tick: int) -> None:
        words = tuple(self._board.read("K.language.words", ()) or ())
        if words == self._last_words_sig:                       # residual word pool is not re-ingested
            return
        self._last_words_sig = words
        hits = [w for w in words if w in ALC_DRINK_WORDS]
        if not hits:
            return
        drinks = 1.0                                            # one drink by default
        for w in words:                                         # pool number -> drink count
            if isinstance(w, str) and w.isdigit():
                drinks = max(1.0, min(10.0, float(int(w))))
                break
        self.ingest(tick, drinks, "pulled from language words")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"bac": self.bac, "tier": self.tier,
                "unconscious": self.unconscious,
                "respiratory_danger": self.respiratory_danger,
                "drinks_consumed": self.drinks_consumed,
                "hours_since_last_drink": self.hours_since_last_drink,
                "hangover": self.hangover,
                "hangover_hours_left": self.hangover_hours_left,
                "withdrawal_stage": self.withdrawal_stage,
                "last_drink_tick": self._last_drink_tick,
                "was_drunk": self._was_drunk,
                "pending_delayed_settlement": self.pending_delayed_settlement,
                "last_words_sig": list(self._last_words_sig),
                "history": self.history, "tolerance": self.tolerance,
                "sensitivity": self.sensitivity, "vd": self.vd,
                "weight_kg": self.weight_kg,
                "behavioral_profile": self.behavioral_profile}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.bac = float(snap.get("bac", 0.0))
        self.tier = int(snap.get("tier", 0))
        self.unconscious = bool(snap.get("unconscious", False))
        self.respiratory_danger = bool(snap.get("respiratory_danger", False))
        self.drinks_consumed = float(snap.get("drinks_consumed", 0.0))
        self.hours_since_last_drink = float(snap.get("hours_since_last_drink", 0.0))
        self.hangover = bool(snap.get("hangover", False))
        self.hangover_hours_left = float(snap.get("hangover_hours_left", 0.0))
        self.withdrawal_stage = str(snap.get("withdrawal_stage", ""))
        self._last_drink_tick = int(snap.get("last_drink_tick", -1))
        self._was_drunk = bool(snap.get("was_drunk", False))
        self.pending_delayed_settlement = bool(
            snap.get("pending_delayed_settlement", False))
        self._last_words_sig = tuple(snap.get("last_words_sig") or ())
        hist = str(snap.get("history", self.history))
        if hist in ALC_LIVER_CAPACITY:
            self.history = hist
        self.tolerance = _clamp(float(snap.get("tolerance", self.tolerance)))
        self.sensitivity = _clamp(float(snap.get("sensitivity", self.sensitivity)))
        self.vd = float(snap.get("vd", self.vd))
        self.weight_kg = float(snap.get("weight_kg", self.weight_kg))
        self.behavioral_profile = str(snap.get("behavioral_profile",
                                               self.behavioral_profile))
 
    def smoke(self) -> bool:
        return self.bac >= 0.0 and 0 <= self.tier <= 7
 
    def invariants(self) -> bool:
        return (self.bac >= 0.0 and 0 <= self.tier <= 7
                and self.hangover_hours_left >= 0.0
                and self.hours_since_last_drink >= 0.0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"bac_level": round(self.bac, 4),
                "intoxication_tier": self.tier,
                "hangover": self.hangover,
                "withdrawal": self.withdrawal_stage or "none"}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug; instance-aware trigger injected at bind time)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    spec: Dict[str, Any] = {
        "module_id": "M4.alcohol",
        "version": "1.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": (                                          # mirror target contract key
            "sys.alcohol_bac", "sys.alcohol_tier", "sys.unconsciousness",
            "sys.alcohol_blackout", "sys.alcohol_behavior_random",
            "sys.alcohol_response_delay", "sys.alcohol_attention_jump",
            "sys.alcohol_station2_off", "sys.alcohol_columnar_cut",
            "sys.alcohol_language_free"),
        "gear": {
            "P1_body": {"every": 1, "trigger": None},               # rewritten at bind time
        },
        "priorities": {"P1_body": 20},                              # after M3 (10)
        "provides": ("alcohol.ingest", "alcohol.clear_delayed"),
        "requires": {"soft": {"K.language.words": None}},
        "report_key": "alcohol",
        "snapshot_label": "m4_alcohol",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
 
    def factory(ctx: Any) -> AlcoholSubsystem:
        engine = AlcoholSubsystem(ctx.log, ctx.k.card.alcohol_profile,
                                  ctx.k.card.body_metrics)
        engine._board = ctx.board
        engine._bus = ctx.bus
        return engine
 
    def bind(inst: AlcoholSubsystem, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("alcohol.ingest", inst.ingest)
 
        def _clear_delayed() -> None:                               # flag cleared after M10 settlement
            inst.pending_delayed_settlement = False
        ctx.services.offer("alcohol.clear_delayed", _clear_delayed)
        # instance-aware trigger: sleeps when sober with no hangover/withdrawal; withdrawal monitoring stays resident for dependents;
        # self-wakes when drinking words appear in the language pool (P1 evaluates later than the P0 publish)
        def _trigger(t: int, d: Dict[str, Any]) -> bool:
            if inst.active or inst.history == "dependent" or d.get("alcohol_intake"):
                return True
            words = tuple(inst._board.read("K.language.words", ()) or ())
            if words == inst._last_words_sig:                   # residual word pool does not wake it
                return False
            return any(w in ALC_DRINK_WORDS for w in words)
        spec["gear"]["P1_body"]["trigger"] = _trigger
        return {"P1_body": inst.on_body, "report": inst.report}
 
    spec["factory"] = factory
    spec["bind"] = bind
    return spec
