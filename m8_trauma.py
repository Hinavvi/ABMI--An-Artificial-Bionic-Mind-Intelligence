# -*- coding: utf-8 -*-
"""M8.trauma — cognition-domain DLC (trauma mechanism: ABMI 1.0 re-engineering of legacy trauma.py)

Role:
  - trauma is a deep-structural imprint of a complete neural response pattern: after encoding, under specific inducing conditions
    the subject re-enters the encoded state rather than recalling it
  - eight encoding pathways (sudden bereavement / prolonged abuse / betrayal / humiliation / threat / accident / loss / witness)"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
 
TRAUMA_TYPES = ("victimization", "helplessness", "injustice", "uncanny",
                "loss", "moral_injury", "microtrauma", "vicarious")
TRAUMA_TYPES_CN = {"victimization": "victimizing", "helplessness": "helplessness-type",
                   "injustice": "injustice-type", "uncanny": "uncanny-valley",
                   "loss": "loss-type", "moral_injury": "moral injury",
                   "microtrauma": "cumulative", "vicarious": "vicarious"}
# severity: 0.3*event intensity + 0.25*(1-action success) + 0.2*(1-social support) + 0.15*|valence| + 0.1*SRF peak/100
TRAUMA_SEVERITY_WEIGHTS = (0.30, 0.25, 0.20, 0.15, 0.10)
TRAUMA_ENCODE_MIN = 0.3                       # final severity <0.3 -> not encoded
TRAUMA_MOD_ATTACHMENT = 1.5                   # attachment figure involved
TRAUMA_MOD_MORAL = 1.3                        # moral injury
TRAUMA_MOD_UNCANNY = 1.2                      # uncanny valley
TRAUMA_MOD_VULNERABLE = 1.1                   # vulnerability window
TRAUMA_MOD_SUPPORT_BUFFER = 0.8               # post-event social-support buffering
TRAUMA_JUSTICE_WINDOW_TICKS = 40              # injustice-trauma vindication window
TRAUMA_ACTIVATION_THRESHOLD = 0.35            # match-intensity activation threshold
TRAUMA_4F_FREEZE_SRF = 80.0                   # SRF>80 forces freeze
TRAUMA_4F_SUPPORT_FAWN = (0.6, 0.3)           # support>0.6 + ally -> fawn +30%
TRAUMA_4F_TYPE_BIAS = {"moral_injury": ("fawn", 0.4),
                       "victimization": ("fight", 0.2),
                       "helplessness": ("freeze", 0.3)}
TRAUMA_4F_INERTIA = 0.2                       # same mode in the last 3 times -> inertia +20%
TRAUMA_4F_FAILURE_PENALTY = 0.1               # repeated-failure mode -10% each time
TRAUMA_UNCANNY_RR = (0.30, 0.60)              # uncanny-valley somatic tetrad
TRAUMA_UNCANNY_SRF = (20.0, 40.0)
TRAUMA_UNCANNY_SSM = (15.0, 25.0)
TRAUMA_UNCANNY_HR = (0.25, 0.45)
TRAUMA_UNCANNY_VALENCE_LOCK = 0.1
TRAUMA_UNCANNY_SUPPRESS_LINGER = (10, 30)     # emotional suppression persists
TRAUMA_STORM_SRF = (40.0, 70.0)               # six-layer multi-stress: autonomic storm
TRAUMA_STORM_SSM = (20.0, 40.0)
TRAUMA_STORM_HR = (0.30, 0.60)
TRAUMA_STORM_RR = (0.20, 0.40)
TRAUMA_STORM_GUT = (0.2, 0.4)
TRAUMA_STORM_PUPIL = 0.30
TRAUMA_PERCEPT_THREAT_MULT = (2.0, 3.0)       # perception distortion: threat weight x2~3
TRAUMA_PERCEPT_SAFETY_MULT = 0.3
TRAUMA_PERCEPT_NEUTRAL_MISJUDGE = 2.0
TRAUMA_COG_NEGATIVE_ATTRIBUTION = 0.4         # cognitive narrowing: negative-table attribution +40%
TRAUMA_COG_WORKING_MEMORY = (3, 4)            # working memory 6->3~4
# trauma type -> PSM_D1 shift template (heart rate/breathing/muscle tone/hormone routing)
TRAUMA_SOMATIC_ROUTING = {
    "victimization":  {"hr": (0.30, 0.50), "rr": (0.20, 0.30), "tone": (0.25, 0.40), "hormone": "adrenaline_srf"},
    "helplessness":   {"hr": (0.15, 0.25), "rr": (0.10, 0.20), "tone": (0.15, 0.25), "hormone": "cortisol_ssm"},
    "injustice":      {"hr": (0.20, 0.35), "rr": (0.15, 0.25), "tone": (0.20, 0.30), "hormone": "adrenaline_cortisol"},
    "uncanny":        {"hr": (0.25, 0.45), "rr": (0.30, 0.60), "tone": (0.10, 0.20), "hormone": "adrenaline_low_srf"},
    "loss":           {"hr": (0.10, 0.20), "rr": (0.05, 0.15), "tone": (0.10, 0.15), "hormone": "cortisol_chronic"},
    "moral_injury":   {"hr": (0.15, 0.25), "rr": (0.10, 0.20), "tone": (0.05, 0.10), "hormone": "cortisol_ssm"},
    "microtrauma":    {"hr": (0.05, 0.15), "rr": (0.05, 0.10), "tone": (0.10, 0.20), "hormone": "cortisol_baseline"},
    "vicarious":      {"hr": (0.10, 0.20), "rr": (0.10, 0.15), "tone": (0.10, 0.15), "hormone": "cortisol_ssm"},
}
TRAUMA_INTEGRATION_SAFE = 0.01                # safe exposure +0.01/tick
TRAUMA_INTEGRATION_RELATION = (0.03, 0.05)
TRAUMA_INTEGRATION_NARRATIVE = (0.05, 0.10)
TRAUMA_INTEGRATION_TRANSCENDENTAL = (0.10, 0.30)
TRAUMA_DEINTEGRATION_REACTIVATE = (0.02, 0.05)
TRAUMA_DEINTEGRATION_BETRAYAL = (0.15, 0.25)
TRAUMA_MICRO_COUNT_MIN = 3                    # cumulative type: >=3 similar light events
TRAUMA_VICARIOUS_RELATION_MIN = 0.6
TRAUMA_VICARIOUS_SUCCESS_MAX = 0.4
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class TraumaImprint:
    """trauma imprint (self-contained, no dependence on the shared type library)."""
    __slots__ = ("imprint_id", "source_event_summary", "encoded_theme",
                 "trauma_type", "severity_at_encoding", "trigger_themes",
                 "trigger_odp_directions", "trigger_sensitivity",
                 "dominant_response", "somatization_profile",
                 "integration_level", "reactivation_count",
                 "last_reactivation_tick", "elapsed_ticks",
                 "response_history", "iceberg_content_ids")
 
    def __init__(self, imprint_id: str, source_event: str, theme: str,
                 ttype: str, severity: float) -> None:
        self.imprint_id = imprint_id
        self.source_event_summary = source_event
        self.encoded_theme = theme
        self.trauma_type = ttype
        self.severity_at_encoding = severity
        self.trigger_themes = [theme]
        self.trigger_odp_directions: List[str] = []
        self.trigger_sensitivity = severity
        self.dominant_response = "somatic_freeze" if ttype == "uncanny" else "freeze"
        self.somatization_profile = dict(TRAUMA_SOMATIC_ROUTING.get(ttype, {}))
        self.integration_level = 0.0
        self.reactivation_count = 0
        self.last_reactivation_tick = -1
        self.elapsed_ticks = 0
        self.response_history: List[Dict[str, Any]] = []
        self.iceberg_content_ids: List[str] = []
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TraumaImprint":
        imp = cls(str(d.get("imprint_id", "TI-0000")),
                  str(d.get("source_event_summary", "")),
                  str(d.get("encoded_theme", "")),
                  str(d.get("trauma_type", "helplessness")),
                  float(d.get("severity_at_encoding", 0.5)))
        imp.trigger_themes = list(d.get("trigger_themes") or [])
        imp.trigger_odp_directions = list(d.get("trigger_odp_directions") or [])
        imp.trigger_sensitivity = float(d.get("trigger_sensitivity", 0.5))
        imp.dominant_response = str(d.get("dominant_response", "freeze"))
        imp.somatization_profile = dict(d.get("somatization_profile") or {})
        imp.integration_level = float(d.get("integration_level", 0.0))
        imp.reactivation_count = int(d.get("reactivation_count", 0))
        imp.last_reactivation_tick = int(d.get("last_reactivation_tick", -1))
        imp.elapsed_ticks = int(d.get("elapsed_ticks", 0))
        imp.response_history = [dict(r) for r in (d.get("response_history") or [])]
        imp.iceberg_content_ids = list(d.get("iceberg_content_ids") or [])
        return imp
 
 
class TraumaMechanism:
    """M8 trauma mechanism: encoding/cascade/4F/somatization/integration; pure local computation."""
 
    def __init__(self, rng: Any, log: Any,
                 declarations: Optional[list] = None) -> None:
        self.rng = rng                                            # derived deterministic substream
        self.log = log
        self._seq = 0
        self.imprints: List[TraumaImprint] = []
        self.active_signal: Optional[Dict[str, Any]] = None
        self._active_ticks = 0                                    # current activation consecutive ticks
        self._uncanny_linger = 0                                  # uncanny-valley emotional-suppression residue
        self._micro_events: Dict[str, List[Tuple[int, float]]] = {}
        self.somatic_baseline_offset = 0.0                        # permanent somatic baseline raise
        # alcohol degradation (written by M4 event): L3 trigger sensitivity +20% / L5 integration suspended
        self.alc_sensitivity_mult = 1.0
        self.alc_integration_paused = False
        for d in (declarations or []):
            self.encode_from_declaration(d)
 
    # ================= config-card direct declaration =================
    def encode_from_declaration(self, d: dict) -> TraumaImprint:
        severity = _clamp(float(d.get("severity", 0.5)))
        ttype = d.get("trauma_type", "helplessness")
        if ttype not in TRAUMA_TYPES:
            ttype = "helplessness"
        return self._create_imprint(0, d.get("source_event", ""),
                                    d.get("encoded_theme", ""), ttype, severity)
 
    @property
    def dormant(self) -> bool:
        return not self.imprints                                  # no imprints -> fully asleep
 
    @property
    def trauma_active(self) -> bool:
        return self.active_signal is not None
 
    # ================= eight encoding-condition judgments =================
    def classify_event(self, tick: int, ev: Dict[str, Any]) -> Optional[str]:
        g = ev.get
        if g("passive_victim") and float(g("action_success", 1.0)) < 0.3:
            return "victimization"
        if g("repeated_failure") and float(g("social_support", 1.0)) < 0.4:
            return "helplessness"
        if g("unjust_treatment") and g("cost_irreversible"):
            return "injustice"
        if g("uncanny_stimulus"):
            return "uncanny"
        if g("attachment_loss"):
            return "loss"
        if (g("moral_violation_self") and g("cost_irreversible")
                and float(g("event_intensity", 0.0)) > 0.7):
            return "moral_injury"
        if g("cumulative_theme"):
            return "microtrauma"
        if (g("witnessed_target")
                and float(g("witnessed_relation", 0.0)) > TRAUMA_VICARIOUS_RELATION_MIN
                and float(g("action_success", 1.0)) < TRAUMA_VICARIOUS_SUCCESS_MAX):
            return "vicarious"
        return None
 
    # ================= severity computation =================
    def compute_severity(self, ev: Dict[str, Any], ttype: str,
                         attachment_involved: bool = False,
                         vulnerable_phase: bool = False) -> float:
        w = TRAUMA_SEVERITY_WEIGHTS
        base = (w[0] * float(ev.get("event_intensity", 0.0))
                + w[1] * (1.0 - float(ev.get("action_success", 1.0)))
                + w[2] * (1.0 - float(ev.get("social_support", 1.0)))
                + w[3] * abs(float(ev.get("valence", 0.0)))
                + w[4] * (float(ev.get("srf_peak", 0.0)) / 100.0))
        mod = 1.0
        if attachment_involved:
            mod *= TRAUMA_MOD_ATTACHMENT
        if ttype == "moral_injury":
            mod *= TRAUMA_MOD_MORAL
        if ttype == "uncanny":
            mod *= TRAUMA_MOD_UNCANNY
        if vulnerable_phase:
            mod *= TRAUMA_MOD_VULNERABLE
        if float(ev.get("social_support", 0.0)) > 0.6:
            mod *= TRAUMA_MOD_SUPPORT_BUFFER
        return round(_clamp(base * mod), 3)
 
    # ================= encoding entry (service port m8.evaluate_event) =================
    def evaluate_event(self, tick: int, ev: Dict[str, Any],
                       attachment_involved: bool = False,
                       vulnerable_phase: bool = False) -> Optional[TraumaImprint]:
        ttype = self.classify_event(tick, ev)
        if ttype is None:
            return None
        if ttype == "microtrauma":
            return self._evaluate_micro(tick, ev, attachment_involved,
                                        vulnerable_phase)
        severity = self.compute_severity(ev, ttype, attachment_involved,
                                         vulnerable_phase)
        if severity < TRAUMA_ENCODE_MIN:
            self.log.record(tick, "M8.trauma", "not encoded",
                            f"{TRAUMA_TYPES_CN[ttype]} severity={severity:.2f}<0.3")
            return None
        # injustice-trauma vindication window (<=40 ticks -> contradiction intensifies, integration gets harder)
        vindicated_tick = ev.get("vindicated_tick")
        if (ttype == "injustice" and ev.get("vindicated")
                and vindicated_tick is not None
                and 0 <= (tick - int(vindicated_tick)) <= TRAUMA_JUSTICE_WINDOW_TICKS):
            severity = _clamp(severity + 0.05)          # "I was right, but the cost is irreversible"
        imp = self._create_imprint(tick, str(ev.get("event_summary", "")),
                                   self._theme_of(ev, ttype), ttype, severity)
        self._post_encode(tick, imp)
        return imp
 
    def _evaluate_micro(self, tick: int, ev: Dict[str, Any], attachment: bool,
                        vulnerable: bool) -> Optional[TraumaImprint]:
        theme = str(ev.get("cumulative_theme", ""))
        buf = self._micro_events.setdefault(theme, [])
        buf.append((tick, float(ev.get("event_intensity", 0.0))))
        if len(buf) < TRAUMA_MICRO_COUNT_MIN:
            return None
        avg = sum(i for _, i in buf) / len(buf)
        if len(buf) * avg <= 1.2:                                 # cumulative threshold
            return None
        severity = self.compute_severity(ev, "microtrauma", attachment, vulnerable)
        if severity < TRAUMA_ENCODE_MIN:
            return None
        self._micro_events[theme] = []
        imp = self._create_imprint(tick, str(ev.get("event_summary", "")),
                                   theme, "microtrauma", severity)
        self._post_encode(tick, imp)
        return imp
 
    @staticmethod
    def _theme_of(ev: Dict[str, Any], ttype: str) -> str:
        table = {
            "victimization": "invaded / safety boundary broken",
            "helplessness": "powerless / trapped / abandoned",
            "injustice": "betrayed / unfair / cost irreversible",
            "uncanny": "untrustworthy / danger beneath the surface",
            "loss": "lost / vacant / irreplaceable",
            "moral_injury": "polluted / unforgivable / I am evil",
            "microtrauma": str(ev.get("cumulative_theme", "")),
            "vicarious": "unable to save / bearing it together",
        }
        return table.get(ttype, str(ev.get("event_summary", "")))
 
    def _create_imprint(self, tick: int, source_event: str, theme: str,
                        ttype: str, severity: float) -> TraumaImprint:
        self._seq += 1
        imp = TraumaImprint(f"TI-{self._seq:04d}", source_event, theme,
                            ttype, severity)
        self.imprints.append(imp)
        self.log.record(tick, "M8.trauma", "imprint encoded",
                        f"{TRAUMA_TYPES_CN[ttype]}[{imp.imprint_id}] "
                        f"theme '{theme}' severity={severity:.2f}")
        return imp
 
    def _post_encode(self, tick: int, imp: TraumaImprint) -> None:
        """after encoding: trauma fragments delivered to the iceberg unconscious layer (via service port, soft dependency)."""
        if self._services is not None:
            self._services.call(
                "m7.inject", tick, "trauma_fragment", imp.encoded_theme,
                intensity=imp.severity_at_encoding,
                valence=-imp.severity_at_encoding, source="trauma",
                layer="unconscious", repression_weight=0.3,
                linkage_tags=list(imp.trigger_themes), default=None)
 
    # ================= columnar query: activation scan =================
    def scan_and_match(self, tick: int, scene_themes: tuple,
                       scene_intensity: float = 0.5,
                       odp_touched: tuple = ()) -> Optional[Dict[str, Any]]:
        if self.dormant:
            return None
        if self.active_signal is not None:
            self._active_ticks += 1
            return self.active_signal
        best_imp, best_strength = None, 0.0
        for imp in self.imprints:
            sim = 0.0
            for th in scene_themes:
                if not th:
                    continue
                for trig in imp.trigger_themes:
                    if trig and (trig in th or th in trig):
                        sim = max(sim, 0.9)
                    elif any(trig and trig in part for part in str(th).split("/")):
                        sim = max(sim, 0.7)
            for d in odp_touched:
                if d in imp.trigger_odp_directions:
                    sim = max(sim, 0.6)
            strength = (sim * imp.trigger_sensitivity * self.alc_sensitivity_mult
                        * (1.0 - imp.integration_level) * scene_intensity)
            if strength > best_strength:
                best_imp, best_strength = imp, strength
        if best_imp is None or best_strength < TRAUMA_ACTIVATION_THRESHOLD:
            return None
        return self._activate(tick, best_imp, best_strength)
 
    def _activate(self, tick: int, imp: TraumaImprint,
                  strength: float) -> Dict[str, Any]:
        imp.reactivation_count += 1
        imp.last_reactivation_tick = tick
        imp.trigger_sensitivity = _clamp(imp.trigger_sensitivity + 0.05)  # sensitization
        if not self.alc_integration_paused:                       # reactivation -> integration drops
            imp.integration_level = _clamp(
                imp.integration_level
                - self.rng.uniform(*TRAUMA_DEINTEGRATION_REACTIVATE))
        layers = {                                                # six-layer multi-stress
            "autonomic storm": {
                "srf_push": self.rng.uniform(*TRAUMA_STORM_SRF),
                "ssm_push": self.rng.uniform(*TRAUMA_STORM_SSM),
                "hr_mult": self.rng.uniform(*TRAUMA_STORM_HR),
                "rr_mult": self.rng.uniform(*TRAUMA_STORM_RR),
                "gut_mult": self.rng.uniform(*TRAUMA_STORM_GUT),
                "pupil": TRAUMA_STORM_PUPIL},
            "perceptual distortion": {
                "threat_weight_mult": self.rng.uniform(*TRAUMA_PERCEPT_THREAT_MULT),
                "safety_signal_mult": TRAUMA_PERCEPT_SAFETY_MULT,
                "neutral_misjudge_mult": TRAUMA_PERCEPT_NEUTRAL_MISJUDGE},
            "cognitive narrowing": {
                "negative_attribution": TRAUMA_COG_NEGATIVE_ATTRIBUTION,
                "working_memory": self._randint(*TRAUMA_COG_WORKING_MEMORY),
                "priori_gate_disabled": True},
            "behavior lock": {"forced_objective": "DEFENSE/AVOIDANCE",
                              "m6_paused": True},
            "emotional overload": {"locked": True},
            "memory distortion": {"fragmented": True,
                                  "temporal_order_lost": True},
        }
        tpl = imp.somatization_profile                            # somatic routing: PSM_D1 only
        routing = {
            "primary_target": "PSM_D1",
            "hr_offset": self.rng.uniform(*tpl.get("hr", (0.1, 0.2))),
            "rr_offset": self.rng.uniform(*tpl.get("rr", (0.05, 0.15))),
            "muscle_tone_offset": self.rng.uniform(*tpl.get("tone", (0.1, 0.2))),
            "hormone_routing": tpl.get("hormone", "cortisol_ssm"),
        }
        # emotion lock (highest priority): uncanny valence force-pulled to neutral +/-0.1, arousal kept high
        if imp.trauma_type == "uncanny":
            locked_v = _clamp(self.rng.uniform(-TRAUMA_UNCANNY_VALENCE_LOCK,
                                               TRAUMA_UNCANNY_VALENCE_LOCK),
                              -1.0, 1.0)
            locked_a = 0.75
            self._uncanny_linger = self._randint(*TRAUMA_UNCANNY_SUPPRESS_LINGER)
        else:
            locked_v = _clamp(-0.5 - 0.3 * imp.severity_at_encoding, -1.0, 1.0)
            locked_a = _clamp(0.6 + 0.3 * strength, -1.0, 1.0)
        signal = {"imprint_id": imp.imprint_id,
                  "match_strength": round(strength, 3),
                  "dominant_response": imp.dominant_response,
                  "somatic_routing": routing,
                  "redirected_query_targets": ["hormone_profile",
                                               "experience_prior",
                                               "iceberg_unconscious"],
                  "locked_valence": round(locked_v, 3),
                  "locked_arousal": round(locked_a, 3),
                  "stress_layers": layers}
        self.active_signal = signal
        self._active_ticks = 0
        self.log.record(tick, "M8.trauma", "activation",
                        f"{imp.imprint_id}({TRAUMA_TYPES_CN[imp.trauma_type]}) "
                        f"match={strength:.2f} response={imp.dominant_response} "
                        f"-> PSM_D1 routing")
        return signal
 
    def _randint(self, lo: int, hi: int) -> int:
        """deterministic integer draw (the derived stream has no randint; implemented via random)."""
        return lo + min(hi - lo, int(self.rng.random() * (hi - lo + 1)))
 
    def uncanny_somatic_freeze(self, tick: int) -> Dict[str, Any]:
        """uncanny-valley somatic tetrad (legacy public API kept): breathing +30~60% / SRF+20~40 /
                SSM+15~25 / heart rate +25~45% / emotional suppression (+/-0.1). Values share the source with the somatic routing table.        """
        return {"rr_offset": self.rng.uniform(*TRAUMA_UNCANNY_RR),
                "srf_push": self.rng.uniform(*TRAUMA_UNCANNY_SRF),
                "ssm_push": self.rng.uniform(*TRAUMA_UNCANNY_SSM),
                "hr_offset": self.rng.uniform(*TRAUMA_UNCANNY_HR),
                "valence_lock": TRAUMA_UNCANNY_VALENCE_LOCK}
 
    # ================= cascade commit (kernel ports: PSM_D1 routing + hormone push) =================
    def _commit_cascade(self, tick: int, signal: Dict[str, Any]) -> None:
        rt = signal["somatic_routing"]
        if self._columnar is not None:
            self._columnar.route_psm_d1_signal(
                tick, _clamp(0.5 + rt.get("hr_offset", 0.2)),
                "trauma", trauma_shield=True)
        if self._hormones is not None:
            hormone = rt.get("hormone_routing", "")
            if "adrenaline" in hormone:
                self._hormones.release_modulator(
                    tick, "SM_SRF", 25.0, "M8 trauma cascade -> SM_SRF")
            if "cortisol" in hormone or "ssm" in hormone:
                self._hormones.release_modulator(
                    tick, "SM_SSM", 20.0, "M8 trauma cascade -> SM_SSM")
            storm = signal["stress_layers"].get("autonomic storm", {})
            if storm:
                self._hormones.release_modulator(
                    tick, "SM_SRF", storm.get("srf_push", 40.0) * 0.5,
                    "M8 autonomic storm")
        # perception-distortion layer board publish: K.attention P3 picks up (pull model)
        self._board.publish("M8.trauma.perceptual_layers",
                            signal["stress_layers"])
        self._board.publish("M8.trauma.affect_lock",
                            (signal["locked_valence"], signal["locked_arousal"]))
        # cascade retrieval target: experiential-prior danger assessment (M9 service, soft dependency)
        danger = 0.0
        if self._services is not None:
            for th in self._board.read("sys.last_scene_themes", ()) or ():
                danger = max(danger, float(self._services.call(
                    "m9.danger_assessment", tick, th, default=0.0) or 0.0))
        self._board.publish("M8.trauma.danger_assessment", danger)
 
    # ================= 4F decision tree (service port m8.behavior_mode) =================
    def four_f_response(self, tick: int, has_escape: bool,
                        opponent_defeatable: bool, opponent_is_attachment: bool,
                        srf: float, social_support: float = 0.0,
                        ally_present: bool = False) -> str:
        if self.active_signal is None:
            return ""
        imp = next((i for i in self.imprints
                    if i.imprint_id == self.active_signal["imprint_id"]), None)
        if imp is None or imp.dominant_response == "somatic_freeze":
            return "somatic_freeze"
        scores = {"fight": 0.25, "flight": 0.25, "freeze": 0.25, "fawn": 0.25}
        if has_escape:                                            # 1 environment assessment
            scores["flight"] += 0.35
        elif opponent_defeatable:
            scores["fight"] += 0.35
        else:
            scores["freeze"] += 0.35
        if opponent_is_attachment:
            scores["fawn"] += 0.35
        if srf > TRAUMA_4F_FREEZE_SRF:                            # 2 internal correction
            scores = {"fight": 0.0, "flight": 0.0, "freeze": 1.0, "fawn": 0.0}
        elif social_support > TRAUMA_4F_SUPPORT_FAWN[0] and ally_present:
            scores["fawn"] += TRAUMA_4F_SUPPORT_FAWN[1]
        bias = TRAUMA_4F_TYPE_BIAS.get(imp.trauma_type)           # 3 type correction
        if bias:
            scores[bias[0]] += bias[1]
        recent = imp.response_history[-3:]                        # 4 historical inertia
        if len(recent) >= 3 and len({r["mode"] for r in recent}) == 1:
            scores[recent[0]["mode"]] += TRAUMA_4F_INERTIA
        for mode in scores:
            fails = sum(1 for r in imp.response_history
                        if r["mode"] == mode and not r.get("success", True))
            scores[mode] -= TRAUMA_4F_FAILURE_PENALTY * fails
        chosen = max(scores, key=scores.get)
        imp.dominant_response = chosen
        self.active_signal["dominant_response"] = chosen
        self.log.record(tick, "M8.trauma", "4F decision",
                        f"{chosen}(fight={scores['fight']:.2f} "
                        f"flight={scores['flight']:.2f} "
                        f"freeze={scores['freeze']:.2f} fawn={scores['fawn']:.2f})")
        return chosen
 
    def record_response_outcome(self, mode: str, success: bool) -> None:
        if self.active_signal is None:
            return
        imp = next((i for i in self.imprints
                    if i.imprint_id == self.active_signal["imprint_id"]), None)
        if imp is not None:
            imp.response_history.append({"mode": mode, "success": success})
 
    # ================= extinction judgment =================
    def check_fade(self, tick: int, stimulus_resolved: bool = False,
                   ticks_threshold: int = 5) -> bool:
        """trigger source gone for ticks_threshold consecutive ticks -> extinction; the baseline may rise permanently after repeated activations."""
        if self.active_signal is None:
            return False
        if stimulus_resolved and self._active_ticks >= ticks_threshold:
            imp = next((i for i in self.imprints
                        if i.imprint_id == self.active_signal["imprint_id"]), None)
            if imp is not None and imp.reactivation_count >= 3:
                self.somatic_baseline_offset = _clamp(
                    self.somatic_baseline_offset + 0.02, 0.0, 0.3)
            self.log.record(tick, "M8.trauma", "activation extinction",
                            f"{self.active_signal['imprint_id']} for "
                            f"{self._active_ticks} consecutive ticks, baseline "
                            f"shift={self.somatic_baseline_offset:.2f}")
            self.active_signal = None
            self._active_ticks = 0
            self._board.publish("M8.trauma.affect_lock", None)    # unlock
            self._board.publish("M8.trauma.perceptual_layers", None)
            return True
        return False
 
    # ================= somatization (eight symptom kinds, tidal rise and fall) =================
    def somatization_burden(self) -> float:
        burden = self.somatic_baseline_offset
        for imp in self.imprints:
            if imp.integration_level < 0.5:
                burden += (imp.severity_at_encoding * 0.15
                           * (1.0 - imp.integration_level))
        if self.active_signal is not None:
            imp = next((i for i in self.imprints
                        if i.imprint_id == self.active_signal["imprint_id"]), None)
            if imp is not None:
                burden += (imp.severity_at_encoding
                           * self.rng.uniform(0.8, 1.0) * 0.5)
        return round(_clamp(burden), 3)
 
    def somatic_symptoms(self) -> Dict[str, float]:
        b = self.somatization_burden()
        return {"chronic pain": round(b * 0.8, 3),
                "gastrointestinal": round(b * 0.6, 3),
                "cardiopulmonary": round(b * 0.9, 3),
                "muscle": round(b * 0.7, 3), "sleep": round(b * 0.75, 3),
                "attention awareness": round(b * 0.85, 3),
                "skin sensation": round(b * 0.5, 3),
                "immune metabolism": round(b * 0.55, 3)}
 
    # ================= integration and repair (service port m8.integrate) =================
    def integrate(self, tick: int, imprint_id: Optional[str] = None,
                  pathway: str = "safe_exposure") -> float:
        """integration rises via: safe exposure / reparative relationships / narrative reconstruction / transcendence; alcohol L5 suspends. Integration != suppression (orthogonal)."""
        if self.alc_integration_paused:
            return 0.0
        deltas = {"safe_exposure": TRAUMA_INTEGRATION_SAFE,
                  "relation": self.rng.uniform(*TRAUMA_INTEGRATION_RELATION),
                  "narrative": self.rng.uniform(*TRAUMA_INTEGRATION_NARRATIVE),
                  "transcendental": self.rng.uniform(
                      *TRAUMA_INTEGRATION_TRANSCENDENTAL)}
        delta = deltas.get(pathway, TRAUMA_INTEGRATION_SAFE)
        touched = []
        for imp in self.imprints:
            if imprint_id and imp.imprint_id != imprint_id:
                continue
            imp.integration_level = round(
                _clamp(imp.integration_level + delta), 3)
            imp.elapsed_ticks += 1
            touched.append(f"{imp.imprint_id}->{imp.integration_level:.2f}")
        if touched and pathway != "safe_exposure":
            self.log.record(tick, "M8.trauma", f"integration [{pathway}]", touched)
        return delta
 
    def secondary_trauma(self, tick: int, imprint_id: str) -> None:
        for imp in self.imprints:
            if imp.imprint_id == imprint_id:
                imp.integration_level = _clamp(
                    imp.integration_level
                    - self.rng.uniform(*TRAUMA_DEINTEGRATION_BETRAYAL))
                self.log.record(tick, "M8.trauma", "secondary trauma",
                                f"{imprint_id} integration -> "
                                f"{imp.integration_level:.2f}")
 
    def delayed_vindication(self, tick: int, imprint_id: str,
                            event_tick: int) -> bool:
        """vindication beyond the window: the imprint is already independently encoded -> vindication promotes integration (+0.03~0.05) but does not erase the imprint."""
        for imp in self.imprints:
            if imp.imprint_id == imprint_id and imp.trauma_type == "injustice":
                if tick - event_tick > TRAUMA_JUSTICE_WINDOW_TICKS:
                    self.integrate(tick, imprint_id, "relation")
                    return True
        return False
 
    # ================= alcohol degradation write (alcohol.degradation event) =================
    def apply_alcohol_degradation(self, d: Dict[str, Any]) -> None:
        self.alc_sensitivity_mult = float(d.get("trigger_sensitivity_mult", 1.0))
        self.alc_integration_paused = bool(d.get("trauma_integration_paused", False))
 
    # ================= background maintenance =================
    def background_maintenance(self, tick: int) -> None:
        for imp in self.imprints:
            imp.elapsed_ticks += 1
        if self._uncanny_linger > 0:
            self._uncanny_linger -= 1
 
    # ================= publish (mirror -> sys.trauma_*) =================
    def _publish(self) -> None:
        theme, integration, ttype = "", 1.0, ""
        if not self.dormant and self.imprints:
            imp = self.imprints[0]
            theme, integration, ttype = (imp.encoded_theme,
                                         imp.integration_level, imp.trauma_type)
        sig = self.active_signal
        if sig is not None:
            imp = next((i for i in self.imprints
                        if i.imprint_id == sig["imprint_id"]), None)
            if imp is not None:
                theme, integration, ttype = (imp.encoded_theme,
                                             imp.integration_level, imp.trauma_type)
        self._board.publish("M8.trauma.active", self.trauma_active)
        self._board.publish("M8.trauma.match",
                            sig["match_strength"] if sig else 0.0)
        self._board.publish("M8.trauma.integration", integration)
        self._board.publish("M8.trauma.type", ttype)
        self._board.publish("M8.trauma.theme", theme)
 
    # ================= hook: P2 scan + cascade =================
    def on_boundary(self, tick: int, data: Dict[str, Any]) -> None:
        # scene-direct marking: tick data carries trauma_event -> encoding entry (second channel besides the service port)
        ev = data.get("trauma_event")
        if isinstance(ev, dict):
            tier = int(self._board.read("M4.alcohol.tier", 0) or 0)
            self.evaluate_event(tick, ev,
                                attachment_involved=bool(
                                    data.get("attachment_involved")),
                                vulnerable_phase=(tier >= 2))
        themes = tuple(data.get("themes") or
                       self._board.read("sys.last_scene_themes", ()) or ())
        signal = self.scan_and_match(
            tick, themes, float(data.get("scene_intensity", 0.3)),
            tuple(data.get("conflict_pairs") or ()))
        if signal is not None and self._active_ticks == 0:        # new activation -> cascade
            self._commit_cascade(tick, signal)
        self._publish()
 
    # ================= hook: P4 integration/extinction/publish =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        if not self.dormant:
            if not self.trauma_active:
                self.integrate(tick, pathway="safe_exposure")     # no activation: tidal healing
            else:
                themes = tuple(data.get("themes") or
                               self._board.read("sys.last_scene_themes",
                                                ()) or ())
                sig = self.active_signal
                imp = next((i for i in self.imprints
                            if i.imprint_id == sig["imprint_id"]), None)
                still = False                                     # trigger source still present?
                if imp is not None:
                    for th in themes:
                        if any(trig and (trig in str(th) or str(th) in trig)
                               for trig in imp.trigger_themes):
                            still = True
                            break
                self.check_fade(tick, stimulus_resolved=not still,
                                ticks_threshold=5)
        self._publish()
 
    # ================= hook: P6 lightweight maintenance =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.background_maintenance(tick)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"seq": self._seq,
                "imprints": [imp.to_dict() for imp in self.imprints],
                "active_signal": (dict(self.active_signal)
                                  if self.active_signal else None),
                "active_ticks": self._active_ticks,
                "uncanny_linger": self._uncanny_linger,
                "micro_events": {k: list(v)
                                 for k, v in self._micro_events.items()},
                "somatic_baseline_offset": self.somatic_baseline_offset,
                "alc_sensitivity_mult": self.alc_sensitivity_mult,
                "alc_integration_paused": self.alc_integration_paused,
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._seq = int(snap.get("seq", 0))
        self.imprints = [TraumaImprint.from_dict(d)
                         for d in (snap.get("imprints") or [])]
        sig = snap.get("active_signal")
        self.active_signal = dict(sig) if isinstance(sig, dict) else None
        self._active_ticks = int(snap.get("active_ticks", 0))
        self._uncanny_linger = int(snap.get("uncanny_linger", 0))
        self._micro_events = {str(k): [tuple(p) for p in v]
                              for k, v in (snap.get("micro_events") or {}).items()}
        self.somatic_baseline_offset = float(
            snap.get("somatic_baseline_offset", 0.0))
        self.alc_sensitivity_mult = float(snap.get("alc_sensitivity_mult", 1.0))
        self.alc_integration_paused = bool(
            snap.get("alc_integration_paused", False))
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return isinstance(self.imprints, list)
 
    def invariants(self) -> bool:
        for imp in self.imprints:
            if not (0.0 <= imp.integration_level <= 1.0
                    and 0.0 <= imp.trigger_sensitivity <= 1.0
                    and 0.0 <= imp.severity_at_encoding <= 1.0):
                return False
        return 0.0 <= self.somatic_baseline_offset <= 0.3
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"active_imprints": ([self.active_signal["imprint_id"]]
                                    if self.active_signal else []),
                "somatization_level": self.somatization_burden(),
                "match_strength": (self.active_signal["match_strength"]
                                   if self.active_signal else 0.0),
                "imprint_count": len(self.imprints)}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug; instance-aware trigger injected at bind time)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    spec: Dict[str, Any] = {
        "module_id": "M8.trauma",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (                                          # mirror target contract key
            "sys.trauma_active", "sys.trauma_match", "sys.trauma_type",
            "sys.trauma_integration", "sys.trauma_theme"),
        "gear": {
            "P2_boundary": {"every": 1, "trigger": None},           # rewritten at bind time
            "P4_decision": {"every": 1, "trigger": None},
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P2_boundary": 10,                           # after iceberg (0)
                       "P4_decision": 20, "P6_maintenance": 50},
        "provides": ("m8.evaluate_event", "m8.integrate",
                     "m8.somatization_burden", "m8.behavior_mode"),
        "requires": {"soft": {"m7.inject": None,
                              "m9.danger_assessment": None,
                              "sys.last_scene_themes": None}},
        "report_key": "trauma",
        "snapshot_label": "m8_trauma",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
 
    def factory(ctx: Any) -> TraumaMechanism:
        engine = TraumaMechanism(ctx.rng_for("m8_trauma"), ctx.log,
                                 ctx.k.card.trauma_imprints)
        engine._board = ctx.board
        engine._bus = ctx.bus
        engine._services = ctx.services
        engine._columnar = ctx.k.columnar
        engine._hormones = ctx.k.hormones
        return engine
 
    def bind(inst: TraumaMechanism, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m8.evaluate_event", inst.evaluate_event)
        ctx.services.offer("m8.integrate", inst.integrate)
        ctx.services.offer("m8.behavior_mode", inst.four_f_response)
 
        def _burden() -> Optional[float]:                         # M3 somatization load port
            return None if inst.dormant else inst.somatization_burden()
        ctx.services.offer("m8.somatization_burden", _burden)
        ctx.bus.subscribe(
            "alcohol.degradation",
            lambda item: inst.apply_alcohol_degradation(
                item.get("payload") or {}),
            owner="M8.trauma")
        ctx.bus.subscribe(
            "sleep.settle",                                       # sleep: safe-exposure integration
            lambda item: inst.integrate(
                int((item.get("payload") or {}).get("tick", 0)),
                pathway="safe_exposure"),
            owner="M8.trauma")
        # instance-aware trigger: fully asleep when no imprints and no tick-data trauma event
        spec["gear"]["P2_boundary"]["trigger"] = (
            lambda t, d: not inst.dormant
            or isinstance(d.get("trauma_event"), dict))
        spec["gear"]["P4_decision"]["trigger"] = (
            lambda t, d: not inst.dormant)
        spec["gear"]["P6_maintenance"]["trigger"] = (
            lambda t, d: not inst.dormant)
        return {
            "P2_boundary": inst.on_boundary,
            "P4_decision": inst.on_decision,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    spec["factory"] = factory
    spec["bind"] = bind
    return spec
