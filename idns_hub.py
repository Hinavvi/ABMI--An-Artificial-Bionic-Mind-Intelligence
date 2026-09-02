# -*- coding: utf-8 -*-
"""IDNS.hub — boundary-domain DLC (introspective neuro-semantic system: ABMI 1.0 re-engineering of legacy idns.py)

Role: the conditional third hub — dormant by default, woken by M12 mimicry / M13 mirror filtering / M14 sanctification triggers."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
 
# ---- M12 mimicry (lock thresholds, per legacy reference) ----
IDNS_M12_PRIOR_FAIL = 3                 # prior stubbornness: fail streak >= 3
IDNS_M12_SRF_HIGH = 70.0                # hormonal imbalance: srf > 70 and arf < 15
IDNS_M12_ARF_LOW = 15.0
IDNS_M12_DRUNK_BAC = 0.15               # drunk L4+: bac > 0.15 or tier >= 4
IDNS_M12_DRUNK_TIER = 4
IDNS_M12_TRAUMA_MATCH = 0.6             # trauma activation: match > 0.6 and integration < 0.3
IDNS_M12_TRAUMA_INTEG = 0.3
IDNS_M12_COHERENCE_LOW = 0.4            # identity collapse: coherence < 0.4 and friction >= 5
IDNS_M12_FRICTION = 5
IDNS_M12_MIN_INTENSITY = 0.35           # mimicry intensity floor (locked)
IDNS_M12_LOOP_CAP = 2                   # loop count cap (locked)
IDNS_M12_EXIT_HMF = 50.0                # exit: loop==0 and hmf > 50
IDNS_M12_FADE = 0.2                     # intensity decay step on exit
# ---- M13 mirror filtering ----
IDNS_M13_OVERLOAD_LOOP = 2              # trigger A: cognitive overload (loop>=2 or intensity>0.8)
IDNS_M13_OVERLOAD_INTENSITY = 0.8
IDNS_M13_SOCIAL_SUPPORT_LOW = 0.3       # trigger B: helplessness trauma + social support < 0.3 + no ally
# ---- M13-E dissolution ----
IDNS_M13E_SOF_THRESHOLD = 0.55          # dissolution override threshold (locked)
IDNS_M13E_VACUUM_TICKS = 10             # vacuum period > 10 ticks -> terminate (locked)
# ---- M14 sanctification ----
IDNS_M14_BASE_CAP = 0.45                # fervor probability cap (locked)
IDNS_M14_GATE_T = 0.6                   # prior gate threshold > 0.6 -> x0.75
IDNS_M14_ODP_HIGH = 3.5                 # B19/C37 > 3.5 -> x0.80 / x0.85
IDNS_M14_POLITICS = 80.0                # politics score > 80 -> x0.90
IDNS_M14_JP = 70.0                      # JP > 70 -> x0.95
IDNS_M14_MARTYR_FAITH = 0.85            # near-martyrdom faith threshold (locked)
IDNS_FAITH_CHECK_GAIN = 0.3             # inspection weight x(1 + 0.3*faith)
# ---- HMF high-level steady suppression (full exit) ----
IDNS_HMF_SUPPRESS = 60.0                # hmf > 60 for 3 consecutive ticks -> full exit
IDNS_HMF_SUPPRESS_TICKS = 3
# ---- modulation (archived knobs) ----
IDNS_DISSONANCE_HIGH = 1.0              # dysregulation > 1.0 -> ssm baseline bias
IDNS_DISSONANCE_SSM_BIAS = 0.005
IDNS_FANATIC_SOCIAL_GAIN = 0.2          # fervor: social weight x(1 + 0.2*faith)
IDNS_FANATIC_VALENCE_BIAS = 0.1         # fervor: valence +0.1*faith
 
POSITIVE_WORDS = ("warm", "attachment", "safety", "love", "care",
                  "companionship", "success", "achieved", "shipped", "favor")
NEGATIVE_WORDS = ("criticism", "threat", "wrong", "betrayal", "abandonment",
                  "rejection", "leave me alone", "unloved", "die", "never")
SUCCESS_WORDS = ("success", "achieved", "shipped", "experiment succeeded",
                 "won", "came true", "favor")
_RETREAT_TOKENS = ("retreat", "withdraw", "increase physical distance",
                   "avoidance", "escape")
_ALLY_THEMES = ("attachment figure present", "rest point", "safety")
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class _IDNSSignal:
    """IDNS forged-signal object (duck-typed to the kernel PerceptionSignal fields; self-contained)."""
    __slots__ = ("source", "type", "intensity", "category", "theme_hint",
                 "target", "urgency", "payload", "source_tag")
 
    def __init__(self, intensity: float, category: str,
                 theme_hint: Optional[str], target: Optional[str],
                 urgency: bool, payload: dict) -> None:
        self.source = "idns"
        self.type = "internal"
        self.intensity = _clamp(intensity)
        self.category = category
        self.theme_hint = theme_hint
        self.target = target
        self.urgency = urgency
        self.payload = payload
        self.source_tag = "idns"
 
 
class IDNSHub:
    """IDNS-P/N object/subject division bus. Not a global negative-pressure switch: M11 stays resident; the root bus only
        governs the semantic-tampering layer (M12 mimicry / M13 mirror / M13-E dissolution / M14 sanctification).    """
 
    def __init__(self, log: Any, card: Any, rng: Any) -> None:
        self.log = log
        self.card = card
        self.rng = rng
        phil = getattr(card, "philosophy", {}) or {}
        self.sacred_object = (getattr(card, "sacred_object", "")
                              or phil.get("sacred_object") or "")
        self.idns_profile = dict(getattr(card, "idns_profile", {}) or {})
        # ---- state (IDNSState flattened into plane fields) ----
        self.m12_active: bool = False
        self.mimetic_intensity: float = 0.0
        self.loop_count: int = 0
        self.m13_active: bool = False
        self.idealization: float = 0.0
        self.dissolution: bool = False
        self.vacuum_ticks: int = 0
        self.faith_intensity: float = _clamp(float(
            getattr(card, "faith_intensity",
                    phil.get("faith_intensity", 0.0)) or 0.0))
        self.fanatic_mode: bool = False
        self.fanatic_probability: float = 0.0
        self.last_dissonance: float = 0.0
        self.repressed_negatives: float = 0.0
        self._hmf_high_ticks: int = 0
        self._anti_survival: bool = False      # near-martyrdom flag (set at P2, reported at P1)
 
    # ================= context assembly (contract keys + kernel ports, read-only) =================
    def _build_ctx(self) -> Dict[str, Any]:
        board = self._board
        k = self._k
        card = self.card
        eff = k.hormones.compute_effective_levels()
        themes = tuple(board.read("sys.last_scene_themes", ()) or ())
        strategy = str(board.read("sys.last_strategy_name", "") or "")
        attach = getattr(card, "attachment_figure", None)
        rels = getattr(card, "relationships", {}) or {}
        base_attach = rels.get(attach, 0.5) if attach else 0.5
        if not isinstance(base_attach, (int, float)):
            base_attach = 0.5
        phil = getattr(card, "philosophy", {}) or {}
        return {
            "srf": float(eff.get("SM_SRF", 0.0)),
            "arf": float(eff.get("SM_ARF", 10.0)),
            "hmf": float(eff.get("SM_HMF", 40.0)),
            "ssm": float(eff.get("SM_SSM", 20.0)),
            "bac": float(board.read("sys.alcohol_bac", 0.0) or 0.0),
            "alcohol_tier": int(board.read("sys.alcohol_tier", 0) or 0),
            "trauma_active": bool(board.read("sys.trauma_active", False)),
            "trauma_match": float(board.read("sys.trauma_match", 0.0) or 0.0),
            "trauma_integration": float(
                board.read("sys.trauma_integration", 1.0) or 0.0),
            "trauma_type": str(board.read("sys.trauma_type", "") or ""),
            "trauma_theme": str(board.read("sys.trauma_theme", "") or "")
                or "betrayal",
            "identity_coherence": float(
                board.read("sys.identity_coherence", 0.7) or 0.0),
            "friction_consecutive": int(
                board.read("sys.friction_consecutive", 0) or 0),
            "prior_fail_streak": int(board.read("sys.fail_streak", 0) or 0),
            "attachment_figure": attach,
            "close_relationships": tuple(rels.keys()),
            "base_attachment": float(base_attach),
            "ally_present": any(t in themes for t in _ALLY_THEMES),
            "social_support": float(
                board.read("sys.social_support", 0.5) or 0.0),
            "gate_t": float(board.read("sys.gate_t", 0.5) or 0.0),
            "odp_b19": float(k.odp.get("B19")) if k.odp is not None else 0.5,
            "odp_c37": float(k.odp.get("C37")) if k.odp is not None else 0.5,
            "politics_score": float(phil.get("politics_score", 0.0) or 0.0),
            "jp": float(k.btcs.get("JP")) if k.btcs is not None else 0.5,
            "separation_from_attachment": "separation" in themes,
            "retreat_theme": any(tok in strategy for tok in _RETREAT_TOKENS),
            "personality_multiplier": float(
                self.idns_profile.get("personality_multiplier", 1.0)),
        }
 
    def _active(self) -> bool:
        return bool(self.m12_active or self.m13_active or self.fanatic_mode)
 
    # ================= triggers and global state =================
    def update_triggers(self, tick: int, ctx: Dict[str, Any]) -> None:
        s = self
        srf = float(ctx.get("srf", 0.0))
        arf = float(ctx.get("arf", 10.0))
        hmf = float(ctx.get("hmf", 40.0))
        bac = float(ctx.get("bac", 0.0))
        tier = int(ctx.get("alcohol_tier", 0))
        trauma_active = bool(ctx.get("trauma_active", False))
        trauma_match = float(ctx.get("trauma_match", 0.0))
        trauma_integration = float(ctx.get("trauma_integration", 1.0))
        coherence = float(ctx.get("identity_coherence", 0.7))
        friction = int(ctx.get("friction_consecutive", 0))
        prior_fail = int(ctx.get("prior_fail_streak", 0))
        # ---- M12 negative-state judgment ----
        cond = {
            "prior stubbornness": prior_fail >= IDNS_M12_PRIOR_FAIL,
            "hormonal imbalance": (srf > IDNS_M12_SRF_HIGH
                                   and arf < IDNS_M12_ARF_LOW),
            "drunk L4+": (bac > IDNS_M12_DRUNK_BAC
                          or tier >= IDNS_M12_DRUNK_TIER),
            "trauma activation": (trauma_active
                                  and trauma_match > IDNS_M12_TRAUMA_MATCH
                                  and trauma_integration < IDNS_M12_TRAUMA_INTEG),
            "identity collapse": (coherence < IDNS_M12_COHERENCE_LOW
                                  and friction >= IDNS_M12_FRICTION),
        }
        if any(cond.values()):
            s.m12_active = True
            s.mimetic_intensity = _clamp(max(
                prior_fail / 5.0 if cond["prior stubbornness"] else 0.0,
                (srf - 70.0) / 30.0 if cond["hormonal imbalance"] else 0.0,
                bac / 0.25 if cond["drunk L4+"] else 0.0,
                trauma_match * (1.0 - trauma_integration)
                    if cond["trauma activation"] else 0.0,
                (0.4 - coherence) * 2.0 if cond["identity collapse"] else 0.0,
                IDNS_M12_MIN_INTENSITY,
            ))
            s.loop_count = min(IDNS_M12_LOOP_CAP, s.loop_count + 1)
        else:
            s.loop_count = max(0, s.loop_count - 1)
            if s.loop_count == 0 and hmf > IDNS_M12_EXIT_HMF:
                s.m12_active = False
                s.mimetic_intensity = max(0.0, s.mimetic_intensity
                                          - IDNS_M12_FADE)
        # ---- M13: A = attached after two M12 overload rounds; B = helpless trauma + isolation ----
        attach = bool(ctx.get("attachment_figure")) \
            or bool(ctx.get("close_relationships"))
        cognitive_overload = (s.loop_count >= IDNS_M13_OVERLOAD_LOOP
                              or s.mimetic_intensity > IDNS_M13_OVERLOAD_INTENSITY)
        trig_a = cognitive_overload and attach
        trig_b = (ctx.get("trauma_type") == "helplessness" and trauma_active
                  and float(ctx.get("social_support", 1.0))
                      < IDNS_M13_SOCIAL_SUPPORT_LOW
                  and not ctx.get("ally_present", False))
        if (trig_a or trig_b) and not s.m13_active:
            s.m13_active = True
            self.log.record(tick, "IDNS.M13", "mirror filter activated",
                            "trigger A" if trig_a else "trigger B")
        if s.m13_active:
            s.idealization = _clamp(
                float(ctx.get("base_attachment", 0.5)) * 0.5
                + (1.0 - trauma_integration) * 0.4
                + float(ctx.get("ssm", 20.0)) / 200.0 * 0.3
                + s.mimetic_intensity * 0.2
                - hmf / 100.0 * 0.4, 0.0, 1.0)
        # ---- M14: fervor mechanism, final version; per-tick judgment; persona only down-weights one-way ----
        if self.sacred_object and s.faith_intensity > 0.0:
            base = min(IDNS_M14_BASE_CAP, s.faith_intensity * 0.6)
            if float(ctx.get("gate_t", 0.5)) > IDNS_M14_GATE_T:
                base *= 0.75
            if float(ctx.get("odp_b19", 0.0)) > IDNS_M14_ODP_HIGH:
                base *= 0.80
            if float(ctx.get("odp_c37", 0.0)) > IDNS_M14_ODP_HIGH:
                base *= 0.85
            if float(ctx.get("politics_score", 0.0)) > IDNS_M14_POLITICS:
                base *= 0.90
            if float(ctx.get("jp", 50.0)) > IDNS_M14_JP:
                base *= 0.95
            s.fanatic_probability = min(IDNS_M14_BASE_CAP, base)
            s.fanatic_mode = self.rng.random() < s.fanatic_probability
        else:
            s.fanatic_probability = 0.0
            s.fanatic_mode = False
        # ---- exit: HMF high-level steady suppression (sleep/external interruption settled by the engine) ----
        self._hmf_high_ticks = (self._hmf_high_ticks + 1
                                if hmf > IDNS_HMF_SUPPRESS else 0)
        if self._hmf_high_ticks >= IDNS_HMF_SUPPRESS_TICKS:
            s.m12_active = False
            s.m13_active = False
            s.fanatic_mode = False
            s.mimetic_intensity = 0.0
            s.loop_count = 0
            s._anti_survival = False
 
    # ================= signal pipeline: PNS->CNS->IDNS->CNS =================
    def process_signals(self, tick: int, signals: List[Any],
                        ctx: Dict[str, Any]) -> Tuple[List[Any], List[Any],
                                                      List[str]]:
        """returns (original signal, new forged signal, event log). Only dyes/appends; never deletes the original signal."""
        s = self
        forged: List[Any] = []
        events: List[str] = []
        if not (s.m12_active or s.m13_active or self.sacred_object):
            return signals, forged, events
        attach = ctx.get("attachment_figure")
        close = set(ctx.get("close_relationships", ()))
        trauma_theme = ctx.get("trauma_theme") or "betrayal"
        for sig in signals:
            payload = getattr(sig, "payload", None)
            if payload is None:
                continue
            # M11 native thermal signals are not IDNS products; when core temperature is abnormally tampered by alcohol, M15 arbitrates — not modified here
            if payload.get("m11") and payload.get("native"):
                continue
            target = getattr(sig, "target", None)
            theme = getattr(sig, "theme_hint", None) \
                or getattr(sig, "category", "")
            text = f"{getattr(sig, 'category', '')} {theme}"
            in_mirror_scope = s.m13_active and (
                target == attach or target in close or target == "self")
            in_faith_scope = bool(self.sacred_object) and (
                self.sacred_object in text
                or any(w in text for w in SUCCESS_WORDS))
            # M12: kind words distorted / hostile words amplified / neutral words stigmatized. Sleeps when sharing the object with M13
            if s.m12_active and not in_mirror_scope:
                payload["idns"] = "mimetic"
                payload["reality_tag"] = "suspect"
                if any(w in text for w in POSITIVE_WORDS):
                    sig.category = "distorted intent"
                    sig.theme_hint = f"{trauma_theme}/exploitation/hypocrisy"
                    sig.intensity = _clamp(sig.intensity
                                           + 0.15 * s.mimetic_intensity)
                elif any(w in text for w in NEGATIVE_WORDS):
                    sig.category = "survival-level threat"
                    sig.theme_hint = f"{trauma_theme}/utter negation"
                    sig.intensity = _clamp(sig.intensity
                                           + 0.35 * s.mimetic_intensity)
                    sig.urgency = sig.urgency or sig.intensity > 0.85
                else:
                    sig.category = "conspiracy poisoning"
                    sig.theme_hint = f"{trauma_theme}/targeting me"
                    sig.intensity = _clamp(sig.intensity
                                           + 0.10 * s.mimetic_intensity)
                events.append("M12 keyword replacement")
            # M13: beautification filter (kind words sanctified / hostile words rationalized / silence read as tacit agreement)
            if in_mirror_scope:
                payload["idns"] = "mirror"
                payload["idealization"] = s.idealization
                raw_valence = (-0.6 if any(w in text for w in NEGATIVE_WORDS)
                               else (0.4 if any(w in text for w in POSITIVE_WORDS)
                                     else 0.0))
                filtered_valence = _clamp(
                    raw_valence if raw_valence > 0
                    else abs(raw_valence) * 0.8 + 0.2, -1.0, 1.0)
                s.last_dissonance = abs(filtered_valence - raw_valence) \
                    * s.idealization
                s.repressed_negatives += max(0.0, -raw_valence) \
                    * s.idealization
                if raw_valence < 0:
                    sig.category = "attachment-filter rationalization"
                    sig.theme_hint = "he is protecting me / not on purpose"
                    sig.intensity = _clamp(sig.intensity
                                           * (1.0 + s.idealization))
                events.append("M13 beautification filter")
            # M14: sanctification re-modulation (original signal kept, only sacred weight added)
            if in_faith_scope and (s.faith_intensity > 0.0 or s.fanatic_mode):
                payload["idns"] = "sacred"
                payload["sacred"] = self.sacred_object
                payload["check_weight"] = float(
                    payload.get("check_weight", 1.0)) \
                    * (1.0 + IDNS_FAITH_CHECK_GAIN * s.faith_intensity)
                sig.theme_hint = f"{theme} [sacred:{self.sacred_object}]"
                events.append("M14 sanctification redirection")
        # ---- signal forgery: M12 black-box production model (internalized whispers + environmental noise) ----
        if s.m12_active:
            forged.append(_IDNSSignal(
                _clamp(0.8 + s.mimetic_intensity * 0.2),
                "satanic whisper",
                f"{trauma_theme}: this is not real", "self", True,
                {"idns": "mimetic", "forged": True,
                 "reality_tag": "suspect"}))
            noise_n = int(s.mimetic_intensity * 3)
            for i in range(noise_n):
                forged.append(_IDNSSignal(
                    _clamp(0.3 + 0.1 * i),
                    "environmental noise forgery",
                    "someone is laughing / the temperature is dropping / "
                    "the air grows heavy", None, False,
                    {"idns": "mimetic", "forged": True, "noise": True}))
            events.append(f"M12 signal forgery x{1 + noise_n}")
        return signals, forged, events
 
    # ================= M13-E / M14 behavior override candidates =================
    def behavior_overlay(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        s = self
        if s.m13_active and ctx.get("separation_from_attachment") \
                and s.idealization > IDNS_M13E_SOF_THRESHOLD:
            s.dissolution = True
            sof = _clamp(s.idealization
                         * float(ctx.get("personality_multiplier", 1.0)),
                         0.0, 1.5)
            return {"intent": "express", "strength": 3, "source": "M13-E",
                    "strategy_pool": ["physical interception",
                                      "boundary infiltration",
                                      "existential blackmail",
                                      "self-harm proof"],
                    "sof_effective": round(sof, 3),
                    "voice": "freeze+flight blend, talkativeness locked high, "
                             "compulsive repetition"}
        if s.fanatic_mode and s.faith_intensity >= IDNS_M14_MARTYR_FAITH \
                and ctx.get("retreat_theme"):
            # retains the ability to re-modulate disposition in extreme P states; completing martyrdom is not guaranteed — physiological limits/
            # residual core values / external interruption pull back to the "unreached point".
            return {"intent": "express", "strength": 3, "source": "M14",
                    "relabel": "sacred suffering", "near_martyr": True,
                    "voice": "high-arousal piety; pain interpreted as a trial"}
        return {}
 
    # ================= background maintenance: dissolution vacuum period =================
    def background_maintenance(self, tick: int) -> None:
        s = self
        if s.dissolution:
            s.vacuum_ticks += 1
            if s.vacuum_ticks > IDNS_M13E_VACUUM_TICKS:
                s.dissolution = False
                s.m13_active = False
                s.idealization = 0.0
                s.vacuum_ticks = 0
                self.log.record(tick, "IDNS.M13-E", "vacuum period ended",
                                "M12 hostile takeover and rebuilding allowed")
 
    # ================= modulation vector (all archived as knob.idns.*) =================
    def modulation(self) -> Dict[str, float]:
        s = self
        return {
            "ssm_baseline_bias": (IDNS_DISSONANCE_SSM_BIAS
                                  if s.last_dissonance > IDNS_DISSONANCE_HIGH
                                  else 0.0),
            "social_weight_mult": (1.0 + IDNS_FANATIC_SOCIAL_GAIN
                                   * s.faith_intensity
                                   if s.fanatic_mode else 1.0),
            "valence_bias": (IDNS_FANATIC_VALENCE_BIAS * s.faith_intensity
                             if s.fanatic_mode else 0.0),
        }
 
    # ================= hook: P1 trigger evaluation (siege-beat normal — evaluation continues during coma) =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        ctx = self._build_ctx()
        self.update_triggers(tick, ctx)
        self._board.publish("IDNS.active", self._active())
        # anti-survival flag report: the governance siege predicate reads between P1 and P2 (1-tick delay)
        if not self.fanatic_mode:
            self._anti_survival = False
        data["idns_anti_survival"] = self._anti_survival
 
    # ================= hook: P2 interception (dyeing + forgery + behavior override; skipped in siege -> output paralysis) =================
    def on_boundary(self, tick: int, data: Dict[str, Any]) -> None:
        ctx = self._build_ctx()
        signals = data.setdefault("signals", [])
        signals, forged, events = self.process_signals(tick, signals, ctx)
        if forged:
            signals.extend(forged)
        if events:
            self.log.record(tick, "IDNS.hub", "intercept",
                            "; ".join(sorted(set(events))))
        overlay = self.behavior_overlay(ctx)
        if overlay:
            self._board.publish("IDNS.behavior_overlay", overlay)
            if overlay.get("near_martyr"):
                self._anti_survival = True
                self.log.record(tick, "IDNS.M14", "near-martyr overlay",
                                "anti-survival flag set for siege predicate")
        else:
            self._board.publish("IDNS.behavior_overlay", None)
 
    # ================= hook: P6 maintenance (vacuum period + knob archiving) =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.background_maintenance(tick)
        for key, val in self.modulation().items():
            self._board.write_knob(f"knob.idns.{key}", val, owner="IDNS.hub")
 
    # ================= report =================
    def report(self) -> Dict[str, Any]:
        s = self
        return {"M12": {"active": s.m12_active,
                        "intensity": round(s.mimetic_intensity, 3),
                        "loop": s.loop_count},
                "M13": {"active": s.m13_active,
                        "idealization": round(s.idealization, 3),
                        "dissonance": round(s.last_dissonance, 3),
                        "dissolution": s.dissolution},
                "M14": {"sacred_object": self.sacred_object or "—",
                        "faith": round(s.faith_intensity, 3),
                        "fanatic": s.fanatic_mode,
                        "p": round(s.fanatic_probability, 3)},
                "anti_survival": s._anti_survival}
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"m12_active": self.m12_active,
                "mimetic_intensity": self.mimetic_intensity,
                "loop_count": self.loop_count,
                "m13_active": self.m13_active,
                "idealization": self.idealization,
                "dissolution": self.dissolution,
                "vacuum_ticks": self.vacuum_ticks,
                "faith_intensity": self.faith_intensity,
                "fanatic_mode": self.fanatic_mode,
                "fanatic_probability": self.fanatic_probability,
                "last_dissonance": self.last_dissonance,
                "repressed_negatives": self.repressed_negatives,
                "hmf_high_ticks": self._hmf_high_ticks,
                "anti_survival": self._anti_survival,
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.m12_active = bool(snap.get("m12_active", False))
        self.mimetic_intensity = float(snap.get("mimetic_intensity", 0.0))
        self.loop_count = int(snap.get("loop_count", 0))
        self.m13_active = bool(snap.get("m13_active", False))
        self.idealization = float(snap.get("idealization", 0.0))
        self.dissolution = bool(snap.get("dissolution", False))
        self.vacuum_ticks = int(snap.get("vacuum_ticks", 0))
        self.faith_intensity = float(snap.get("faith_intensity", 0.0))
        self.fanatic_mode = bool(snap.get("fanatic_mode", False))
        self.fanatic_probability = float(snap.get("fanatic_probability", 0.0))
        self.last_dissonance = float(snap.get("last_dissonance", 0.0))
        self.repressed_negatives = float(snap.get("repressed_negatives", 0.0))
        self._hmf_high_ticks = int(snap.get("hmf_high_ticks", 0))
        self._anti_survival = bool(snap.get("anti_survival", False))
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return 0.0 <= self.mimetic_intensity <= 1.0 \
            and 0.0 <= self.idealization <= 1.0 \
            and 0.0 <= self.faith_intensity <= 1.0
 
    def invariants(self) -> bool:
        return (0.0 <= self.mimetic_intensity <= 1.0
                and 0.0 <= self.idealization <= 1.0
                and 0.0 <= self.faith_intensity <= 1.0
                and 0.0 <= self.fanatic_probability <= IDNS_M14_BASE_CAP
                and self.loop_count >= 0
                and self.vacuum_ticks >= 0
                and self._hmf_high_ticks >= 0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> IDNSHub:
        hub = IDNSHub(ctx.log, ctx.k.card, ctx.rng_for("idns"))
        hub._board = ctx.board
        hub._k = ctx.k
        return hub
 
    def bind(inst: IDNSHub, ctx: Any) -> Dict[str, Any]:
        return {
            "P1_body": inst.on_body,
            "P2_boundary": inst.on_boundary,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "IDNS.hub",
        "version": "1.0",
        "zone": "boundary",                                         # boundary domain (conditional hub)
        "contract_keys": ("sys.idns_active",),
        "gear": {
            "P1_body": {"every": 1, "trigger": None},
            "P2_boundary": {"every": 1, "trigger": None},
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P1_body": 30, "P2_boundary": 15,
                       "P6_maintenance": 65},
        "factory": factory,
        "bind": bind,
        "provides": ("sys.idns_active",),
        "requires": {},
        "report_key": "idns",
        "snapshot_label": "idns_hub",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
