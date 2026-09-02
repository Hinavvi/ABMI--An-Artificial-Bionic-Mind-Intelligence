# -*- coding: utf-8 -*-
"""M7.iceberg — cognition-domain DLC (iceberg structure: ABMI 1.0 re-engineering of legacy iceberg.py)

Role:
  - three-layer content management: conscious layer (fine-grained, capacity 6, forced override stretches to 9) /
    preconscious layer (mixed granularity, capacity 50...)"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
 
ICEBERG_CONSCIOUS_CAPACITY = 6                # conscious capacity (forced override can stretch to 9)
ICEBERG_CONSCIOUS_OVERRIDE_MAX = 9
ICEBERG_PRECONSCIOUS_CAPACITY = 50            # preconscious capacity hard cap
ICEBERG_SINK_INTENSITY = 0.05                 # natural decay sinking threshold
ICEBERG_BASE_ACTIVATION_THRESHOLD = 0.55      # default activation for one-level surfacing
ICEBERG_BASE_DECAY_RATE = 0.01                # per-tick natural decay baseline
ICEBERG_BASE_PERMEABILITY = (0.1, 0.3)        # normal boundary permeability interval
ICEBERG_CHAOS_PERMEABILITY = (0.6, 0.9)       # chaos-period boundary permeability
ICEBERG_TRIGGER_BOOST = (0.3, 0.7)            # scene-similarity trigger bonus
ICEBERG_RESONANCE_BOOST = (0.1, 0.3)          # emotional resonance bonus
ICEBERG_DRIVE_BOOST = (0.2, 0.5)              # drive pressure bonus
ICEBERG_REPRESSION_ODP_AVOID = (0.2, 0.4)     # ODP avoidance suppression increment
ICEBERG_REPRESSION_TRAUMA_EXTRA = 0.2         # extra suppression for trauma fragments
ICEBERG_REPRESSION_MORAL = 0.15               # moral self-conflict suppression
ICEBERG_REPRESSION_SAFE_EXPOSURE = 0.01       # safe exposure -0.01/tick
ICEBERG_REPRESSION_REPAIR = (0.03, 0.05)      # reparative experience interval
ICEBERG_MONITOR_BASE = {"J": 0.7, "P": 0.5, None: 0.6}   # self-monitoring baseline
ICEBERG_MONITOR_FATIGUE = 0.15
ICEBERG_MONITOR_STRONG_EMOTION = 0.2
ICEBERG_MONITOR_SAFE = 0.05
ICEBERG_MONITOR_SOCIAL = 0.1
ICEBERG_LEAK_MONITOR_CAP = 0.6                # behavior leakage monitoring ceiling
ICEBERG_LEAK_INTENSITY_MIN = 0.3              # leakage intensity floor
ICEBERG_TONE_STAIN_MIN = 0.2                  # emotion dyeing threshold
ICEBERG_TONE_STAIN = (0.1, 0.3)
ICEBERG_DREAM_INTENSITY_MIN = 0.2
ICEBERG_DREAM_TOP_N = 3
ICEBERG_DREAM_HALFLIFE_TICKS = 30
ICEBERG_OVERRIDE_A_SRF = 70.0                 # A stress breakthrough
ICEBERG_OVERRIDE_B_VALENCE = 0.85             # B emotional tsunami
ICEBERG_OVERRIDE_B_AROUSAL = 0.75
ICEBERG_OVERRIDE_C_SEVERITY = 0.7             # C trauma detonation
ICEBERG_OVERRIDE_D_DAMAGE = 0.8               # D somatic violence
ICEBERG_OVERRIDE_COUNT = {"A": 1, "B": (1, 2), "C": (1, 3), "D": (1, 2)}
ICEBERG_RECOVER_CAPACITY_TICKS = 3            # three-stage recovery (ticks)
ICEBERG_RECOVER_BOUNDARY_TICKS = 10
ICEBERG_RECOVER_INTEGRATE_TICKS = 30
ICEBERG_RECOVER_AFTERSHOCK = (0.1, 0.2)
ICEBERG_MERGE_SIMILARITY = 0.7
ICEBERG_MERGE_COEF = {"generic": 1.2, "fear": 1.3,
                      "trauma": (1.4, 1.5), "transcendental": 1.2}
 
_LAYER_ORDER = ("unconscious", "preconscious", "conscious")   # deep -> shallow
_LAYER_UP = {"unconscious": "preconscious", "preconscious": "conscious"}
_LAYER_DOWN = {"conscious": "preconscious", "preconscious": "unconscious"}
# column-layer coupling query table (column -> query layer/label)
COLUMN_ICEBERG_QUERY = {
    "PSM_D1": ("unconscious", ("body", "drive", "trauma_fragment")),
    "PSM_D2": ("preconscious", ("emotion_tone", "moral_emotion")),
    "PSM_D3": ("conscious", ("current perceived theme",)),
    "PSM_D4": ("preconscious", ("current perceived theme",)),
    "PSM_D5": ("preconscious", ("current perceived theme", "worry")),
    "PSM_D6": ("unconscious", ("drive", "trauma_fragment")),
    "PSM_D7": ("unconscious", ("drive", "desire")),
    "PSM_D8": ("preconscious", ("pressure", "excretion", "worry")),
    "PSM_D9": ("preconscious", ("pressure", "excretion", "worry")),
}
# dream symbolization table (trauma->chased/falling/trapped; desire->flying/gaining; fear->monsters/lost)
_DREAM_SYMBOLS = {
    "trauma_fragment": ("being chased", "falling", "trapped"),
    "worry": ("monsters", "getting lost"),
    "desire": ("flying", "obtaining"),
    "drive": ("flying", "obtaining"),
}
# behavior intent -> direction value (leakage mismatch judgment)
_INTENT_DIRECTION = {"negative avoidance": -1.0, "positive interaction": 1.0,
                     "information sampling": 0.3, "information output": 0.5,
                     "state maintenance": 0.0}
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class MentalContent:
    """psychological content entry (self-contained, no dependence on the shared type library)."""
    __slots__ = ("content_id", "content_type", "summary", "intensity", "valence",
                 "source", "created_tick", "last_activated_tick", "current_layer",
                 "repression_weight", "activation_threshold", "natural_decay_rate",
                 "linkage_tags", "odp_direction", "chaos_displaced")
 
    def __init__(self, content_id: str, content_type: str, summary: str,
                 intensity: float, valence: float, source: str, created_tick: int,
                 layer: str, repression_weight: float, decay_rate: float,
                 linkage_tags: list, odp_direction: str) -> None:
        self.content_id = content_id
        self.content_type = content_type
        self.summary = summary
        self.intensity = intensity
        self.valence = valence
        self.source = source
        self.created_tick = created_tick
        self.last_activated_tick = created_tick
        self.current_layer = layer
        self.repression_weight = repression_weight
        self.activation_threshold = ICEBERG_BASE_ACTIVATION_THRESHOLD
        self.natural_decay_rate = decay_rate
        self.linkage_tags = list(linkage_tags)
        self.odp_direction = odp_direction
        self.chaos_displaced = False
 
    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}
 
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MentalContent":
        mc = cls(str(d.get("content_id", "MC-0000")),
                 str(d.get("content_type", "memory")),
                 str(d.get("summary", "")),
                 float(d.get("intensity", 0.5)), float(d.get("valence", 0.0)),
                 str(d.get("source", "experience")),
                 int(d.get("created_tick", 0)),
                 str(d.get("current_layer", "preconscious")),
                 float(d.get("repression_weight", 0.0)),
                 float(d.get("natural_decay_rate", ICEBERG_BASE_DECAY_RATE)),
                 list(d.get("linkage_tags") or []),
                 str(d.get("odp_direction", "")))
        mc.last_activated_tick = int(d.get("last_activated_tick", mc.created_tick))
        mc.activation_threshold = float(d.get("activation_threshold",
                                              ICEBERG_BASE_ACTIVATION_THRESHOLD))
        mc.chaos_displaced = bool(d.get("chaos_displaced", False))
        return mc
 
 
class IcebergStructure:
    """M7 iceberg structure: three-layer content management + permeability rule engine; pure local computation."""
 
    def __init__(self, rng: Any, log: Any, declaration: Optional[dict] = None) -> None:
        self.rng = rng                                            # derived deterministic substream
        self.log = log
        self._seq = 0
        self.layers: Dict[str, List[MentalContent]] = {
            "unconscious": [], "preconscious": [], "conscious": []}
        self.boundary_permeability = (ICEBERG_BASE_PERMEABILITY[0]
                                      + ICEBERG_BASE_PERMEABILITY[1]) / 2.0
        self.self_monitoring = 0.6
        # alcohol degradation (written by M4 event)
        self.alc_monitor_delta = 0.0
        self.alc_permeability_mult = 1.0
        self.alc_override_threshold_mult = 1.0
        self.alc_leak_mult = 1.0
        self.alc_surface_capacity: Optional[int] = None
        # forced override state
        self.override_active = False
        self.override_type = ""
        self._override_recover_tick = -1
        self._chaos_monitor_delta = 0.0
        self._pending_stimuli: List[Dict[str, Any]] = []          # path C staging
        self._load_declaration(declaration or {})
 
    # ================= config card loading =================
    def _load_declaration(self, decl: dict) -> None:
        for layer in _LAYER_ORDER:
            for item in (decl.get(layer) or []):
                self.inject(0,
                            content_type=item.get("content_type", "memory"),
                            summary=item.get("summary", ""),
                            intensity=float(item.get("intensity", 0.5)),
                            valence=float(item.get("valence", 0.0)),
                            source=item.get("source", "innate"
                                            if layer == "unconscious" else "experience"),
                            layer=layer,
                            repression_weight=float(item.get("repression_weight", 0.0)),
                            linkage_tags=list(item.get("linkage_tags", [])),
                            odp_direction=item.get("odp_direction", ""))
 
    # ================= content injection (service port m7.inject) =================
    def inject(self, tick: int, content_type: str, summary: str,
               intensity: float = 0.5, valence: float = 0.0,
               source: str = "experience", layer: str = "preconscious",
               repression_weight: float = 0.0, linkage_tags: list = None,
               odp_direction: str = "", decay_rate: float = ICEBERG_BASE_DECAY_RATE,
               ei_gate: float = 0.0) -> MentalContent:
        if layer not in self.layers:
            layer = "preconscious"
        self._seq += 1
        intensity = _clamp(intensity + ei_gate * 0.5)
        mc = MentalContent(f"MC-{self._seq:04d}", content_type, summary,
                           round(_clamp(intensity), 3),
                           round(_clamp(valence, -1.0, 1.0), 3),
                           source, tick, layer,
                           round(_clamp(repression_weight), 3), decay_rate,
                           list(linkage_tags or []), odp_direction)
        self.layers[layer].append(mc)
        return mc
 
    # ================= semantic similarity =================
    @staticmethod
    def _similarity(a: MentalContent, themes: tuple, tags: tuple) -> float:
        score = 0.0
        pool = set(tags) | set(themes)
        for t in a.linkage_tags:
            if t in pool:
                score += 0.35
        for th in themes:
            if th and (th in a.summary or a.summary in th):
                score += 0.65
            elif any(th and th in tag for tag in a.linkage_tags):
                score += 0.4
        if a.content_type in pool:
            score += 0.3
        return _clamp(score)
 
    # ================= path C: direct perceptual stimulation =================
    def receive_perception_stimulus(self, tick: int, themes: tuple, tags: tuple,
                                    intensity: float, valence: float) -> None:
        self._pending_stimuli.append({
            "themes": tuple(themes), "tags": tuple(tags),
            "intensity": _clamp(intensity),
            "valence": _clamp(valence, -1.0, 1.0)})
 
    def _external_trigger_boost(self, mc: MentalContent) -> float:
        best = 0.0
        for st in self._pending_stimuli:
            sim = self._similarity(mc, st["themes"], st["tags"])
            if sim > 0.0:
                lo, hi = ICEBERG_TRIGGER_BOOST
                best = max(best, sim * (lo + (hi - lo) * st["intensity"]))
        return best
 
    def _emotional_resonance_boost(self, mc: MentalContent,
                                   current_valence: float) -> float:
        if mc.valence == 0.0 or current_valence == 0.0:
            return 0.0
        if mc.valence * current_valence <= 0.0:                   # resonance requires the same sign
            return 0.0
        lo, hi = ICEBERG_RESONANCE_BOOST
        match = min(abs(mc.valence), abs(current_valence))
        return match * (lo + (hi - lo) * match)
 
    # ================= normal surfacing/sinking (lightweight per-tick swap) =================
    def tick_exchange(self, tick: int, current_valence: float = 0.0,
                      relaxation: float = 0.0, drive_pressure: float = 0.0) -> None:
        rose, sank = [], []
        for layer in _LAYER_ORDER:
            for mc in list(self.layers[layer]):
                mc.intensity = round(_clamp(mc.intensity - mc.natural_decay_rate), 3)
                drive_boost = 0.0
                if layer == "unconscious" and mc.content_type == "drive":
                    lo, hi = ICEBERG_DRIVE_BOOST
                    drive_boost = drive_pressure * (lo + (hi - lo) * drive_pressure)
                effective = (mc.intensity * (1.0 - mc.repression_weight)
                             + self._external_trigger_boost(mc)
                             + self._emotional_resonance_boost(mc, current_valence)
                             + drive_boost + relaxation)
                threshold = mc.activation_threshold * (
                    1.0 - self.boundary_permeability
                    * self.alc_permeability_mult * 0.5)
                if layer != "conscious" and effective > threshold:
                    self._move(mc, _LAYER_UP[layer])
                    mc.last_activated_tick = tick
                    rose.append(mc.summary)
                    continue
                if layer != "unconscious" and mc.intensity < ICEBERG_SINK_INTENSITY:
                    self._move(mc, _LAYER_DOWN[layer])
                    sank.append(mc.summary)
        self._pending_stimuli = []
        cap = self.alc_surface_capacity or ICEBERG_CONSCIOUS_CAPACITY
        if self.override_active:
            cap = ICEBERG_CONSCIOUS_OVERRIDE_MAX
        surface = self.layers["conscious"]
        while len(surface) > cap:                                 # capacity squeeze
            evicted = min(surface, key=lambda m: m.last_activated_tick)
            self._move(evicted, "preconscious")
            sank.append(f"{evicted.summary}(evicted)")
        pre = self.layers["preconscious"]
        while len(pre) > ICEBERG_PRECONSCIOUS_CAPACITY:           # preconscious hard cap
            evicted = min(pre, key=lambda m: (m.last_activated_tick, m.intensity))
            self._move(evicted, "unconscious")
        if rose or sank:
            self.log.record(tick, "M7.iceberg", "content exchange",
                            f"surfacing={rose or 'none'} sinking={sank or 'none'}")
 
    def _move(self, mc: MentalContent, target: str) -> None:
        if mc in self.layers[mc.current_layer]:
            self.layers[mc.current_layer].remove(mc)
        mc.current_layer = target
        self.layers[target].append(mc)
 
    # ================= suppression dynamics =================
    def adjust_repression(self, tick: int, odp_avoid_directions: tuple = (),
                          moral_conflict: bool = False) -> None:
        for mc in self.layers["unconscious"] + self.layers["preconscious"]:
            delta = 0.0
            if mc.odp_direction and mc.odp_direction in odp_avoid_directions:
                lo, hi = ICEBERG_REPRESSION_ODP_AVOID
                delta += self.rng.uniform(lo, hi)
            if mc.content_type == "trauma_fragment" and delta > 0.0:
                delta += ICEBERG_REPRESSION_TRAUMA_EXTRA
            if moral_conflict and mc.source == "moral":
                delta += ICEBERG_REPRESSION_MORAL
            if delta > 0.0:
                mc.repression_weight = round(
                    _clamp(mc.repression_weight + delta), 3)
                self.log.record(tick, "M7.iceberg", "repression increase",
                                f"{mc.summary} -> w={mc.repression_weight:.2f}")
 
    def relax_repression(self, tick: int,
                         amount: float = ICEBERG_REPRESSION_SAFE_EXPOSURE,
                         content_id: Optional[str] = None,
                         repair: bool = False) -> None:
        for mc in self.layers["unconscious"] + self.layers["preconscious"]:
            if content_id and mc.content_id != content_id:
                continue
            step = self.rng.uniform(*ICEBERG_REPRESSION_REPAIR) if repair else amount
            mc.repression_weight = round(_clamp(mc.repression_weight - step), 3)
 
    def sleep_global_relaxation(self) -> None:
        for layer in _LAYER_ORDER:
            for mc in self.layers[layer]:
                mc.repression_weight = round(
                    _clamp(mc.repression_weight - 0.005), 3)
 
    # ================= self-monitoring level =================
    def compute_self_monitoring(self, jp_letter: Optional[str],
                                sleep_pressure: float = 0.0,
                                strong_emotion: bool = False, srf: float = 0.0,
                                safe_environment: bool = False,
                                social_context: bool = False) -> float:
        level = ICEBERG_MONITOR_BASE.get(jp_letter, ICEBERG_MONITOR_BASE[None])
        if sleep_pressure > 0.6:
            level -= ICEBERG_MONITOR_FATIGUE
        level += self.alc_monitor_delta                          # alcohol degradation (negative)
        if strong_emotion:
            level -= ICEBERG_MONITOR_STRONG_EMOTION
        if srf > 50.0:
            level += 0.1                                          # surface reinforcement
        if safe_environment:
            level += ICEBERG_MONITOR_SAFE
        if social_context:
            level += ICEBERG_MONITOR_SOCIAL
        if self.override_active:
            level += self._chaos_monitor_delta                    # chaos effect 4
        self.self_monitoring = round(_clamp(level, 0.0, 1.0), 3)
        return self.self_monitoring
 
    # ================= path A: columnar query =================
    def query_by_column(self, tick: int, column_id: str,
                        scene_themes: tuple = (),
                        scene_intensity: float = 0.5) -> list:
        layer_hint, tags = COLUMN_ICEBERG_QUERY.get(column_id,
                                                    ("preconscious", ()))
        resolved = tuple(scene_themes) if "current perceived theme" in tags else tags
        hits = []
        for mc in self.layers[layer_hint]:
            sim = self._similarity(mc, resolved, tags)
            leak = mc.intensity * mc.repression_weight
            activation = sim * 0.6 + leak * 0.4
            if activation > 0.25 * scene_intensity + 0.1:
                mc.last_activated_tick = tick
                hits.append({"content_id": mc.content_id, "summary": mc.summary,
                             "layer": mc.current_layer,
                             "activation": round(activation, 3),
                             "leak_intensity": round(leak, 3)})
        if hits:
            hits.sort(key=lambda h: -h["activation"])
            self.log.record(tick, "M7.iceberg",
                            f"columnar query [{column_id}]",
                            f"hit x{len(hits)}: {hits[0]['summary']}")
        return hits
 
    # ================= three leakage paths =================
    def behavior_leak_check(self, tick: int, current_objective_direction: float,
                            content_direction: float,
                            content: MentalContent) -> float:
        misalignment = _clamp(abs(current_objective_direction
                                  - content_direction) / 2.0)
        if misalignment <= 0.5:                                   # angle >90 normalized criterion
            return 0.0
        if self.self_monitoring >= ICEBERG_LEAK_MONITOR_CAP:
            return 0.0
        leak = content.intensity * content.repression_weight * self.alc_leak_mult
        if leak <= ICEBERG_LEAK_INTENSITY_MIN:
            return 0.0
        prob = _clamp(misalignment * (1.0 - self.self_monitoring) * leak)
        self.log.record(tick, "M7.iceberg", "behavior leak",
                        f"{content.summary} probability={prob:.2f}")
        return prob
 
    def unconscious_valence_tone(self) -> float:
        pool = self.layers["unconscious"]
        if not pool:
            return 0.0
        num = sum(mc.valence * mc.intensity for mc in pool)
        den = sum(mc.intensity for mc in pool) or 1.0
        return round(_clamp(num / den, -1.0, 1.0), 3)
 
    def emotion_stain_offset(self) -> float:
        tone = self.unconscious_valence_tone()
        if abs(tone) <= ICEBERG_TONE_STAIN_MIN:
            return 0.0
        lo, hi = ICEBERG_TONE_STAIN
        return round(tone * (lo + (hi - lo) * abs(tone)), 3)
 
    # ================= dream processing (REM deep processing; driven by the sleep.settle event) =================
    def dream_process(self, tick: int) -> list:
        pool = [mc for mc in self.layers["preconscious"] + self.layers["unconscious"]
                if mc.intensity > ICEBERG_DREAM_INTENSITY_MIN]
        if not pool:
            return []
        pool.sort(key=lambda m: m.intensity * abs(m.valence)
                  * (0.5 + m.repression_weight), reverse=True)
        produced = []
        for mc in pool[:ICEBERG_DREAM_TOP_N]:
            symbols = _DREAM_SYMBOLS.get(mc.content_type, ("a strange room",))
            symbol = self.rng.choice(list(symbols))
            frag = self.inject(tick, "dream_fragment",
                               f"dream: {symbol}({mc.summary})",
                               intensity=mc.intensity * 0.6, valence=mc.valence,
                               source="dream", layer="preconscious",
                               decay_rate=1.0 / ICEBERG_DREAM_HALFLIFE_TICKS)
            produced.append(frag.summary)
        if produced:
            self.log.record(tick, "M7.iceberg", "dream processing", produced)
        return produced
 
    # ================= forced override mechanism =================
    def check_forced_override(self, tick: int, srf: float = 0.0,
                              valence: float = 0.0, arousal: float = 0.0,
                              trauma_severity: float = 0.0,
                              damage_signal: float = 0.0) -> Optional[str]:
        threshold_mult = self.alc_override_threshold_mult
        trigger, count_key = None, None
        if trauma_severity > ICEBERG_OVERRIDE_C_SEVERITY * threshold_mult:
            trigger, count_key = "C trauma detonation", "C"
        elif srf > ICEBERG_OVERRIDE_A_SRF * threshold_mult:
            trigger, count_key = "A stress breakthrough", "A"
        elif damage_signal > ICEBERG_OVERRIDE_D_DAMAGE * threshold_mult:
            trigger, count_key = "D somatic violence", "D"
        elif (abs(valence) > ICEBERG_OVERRIDE_B_VALENCE * threshold_mult
              and arousal > ICEBERG_OVERRIDE_B_AROUSAL * threshold_mult):
            trigger, count_key = "B emotional tsunami", "B"
        if trigger is None or self.override_active:
            return None
        cnt_spec = ICEBERG_OVERRIDE_COUNT[count_key]
        n = cnt_spec if isinstance(cnt_spec, int) else self._randint(*cnt_spec)
        self._enter_chaos(tick, trigger, n)
        return trigger
 
    def _randint(self, lo: int, hi: int) -> int:
        """deterministic integer draw (the derived stream has no randint; implemented via random)."""
        return lo + min(hi - lo, int(self.rng.random() * (hi - lo + 1)))
 
    def _enter_chaos(self, tick: int, trigger: str, n: int) -> None:
        self.override_active = True
        self.override_type = trigger
        self._override_recover_tick = tick
        # effect 3: boundary permeability 0.1~0.3 -> 0.6~0.9
        self.boundary_permeability = self.rng.uniform(*ICEBERG_CHAOS_PERMEABILITY)
        # effect 4: self-monitoring collapse
        self._chaos_monitor_delta = -self.rng.uniform(0.3, 0.5)
        # effects 1+2: pull n items from the deep layer and force them to the surface (capacity violation) + unordered eviction
        deep = self.layers["unconscious"] + self.layers["preconscious"]
        if deep:
            picked = self.rng.choice(deep)
            candidates = [picked]
            for _ in range(min(n - 1, len(deep) - 1)):
                c = self.rng.choice(deep)
                if c not in candidates:
                    candidates.append(c)
            for mc in candidates[:n]:
                self._move(mc, "conscious")
                mc.last_activated_tick = tick
                mc.chaos_displaced = False
        surface = list(self.layers["conscious"])
        if len(surface) > ICEBERG_CONSCIOUS_OVERRIDE_MAX:
            victim = self.rng.choice(surface)
            self._move(victim, "unconscious")
            victim.chaos_displaced = True
        self.log.record(tick, "M7.iceberg", f"forced overwrite [{trigger}]",
                        f"permeability {self.boundary_permeability:.2f} "
                        f"monitoring {self._chaos_monitor_delta:.2f}")
 
    def recover_from_chaos(self, tick: int) -> str:
        """three-stage recovery: capacity recovery(0~3) -> boundary repair(3~10, aftershock 0.1~0.2) -> integration(10~30)."""
        if not self.override_active:
            return ""
        elapsed = tick - self._override_recover_tick
        if elapsed <= ICEBERG_RECOVER_CAPACITY_TICKS:
            surface = self.layers["conscious"]
            while len(surface) > ICEBERG_CONSCIOUS_CAPACITY:
                victim = min(surface, key=lambda m: m.last_activated_tick)
                self._move(victim, "preconscious")
                victim.chaos_displaced = True
            return "capacity recovery"
        if elapsed <= ICEBERG_RECOVER_BOUNDARY_TICKS:
            target = ICEBERG_BASE_PERMEABILITY[1] + self.rng.uniform(
                *ICEBERG_RECOVER_AFTERSHOCK)
            self.boundary_permeability += (target
                                           - self.boundary_permeability) * 0.3
            self._chaos_monitor_delta *= 0.7
            return "boundary repair"
        if elapsed <= ICEBERG_RECOVER_INTEGRATE_TICKS:
            self.boundary_permeability += (ICEBERG_BASE_PERMEABILITY[0]
                                           - self.boundary_permeability) * 0.2
            self._chaos_monitor_delta *= 0.5
            for layer in ("preconscious", "unconscious"):
                for mc in self.layers[layer]:
                    if mc.chaos_displaced:
                        mc.repression_weight = round(
                            _clamp(mc.repression_weight + 0.1), 3)
                        mc.chaos_displaced = False
            return "integration"
        self.override_active = False
        self.override_type = ""
        self._chaos_monitor_delta = 0.0
        self.log.record(tick, "M7.iceberg", "forced override restore complete",
                        f"permeability={self.boundary_permeability:.2f}")
        return "completed"
 
    # ================= unconscious merge =================
    def merge_unconscious(self, tick: int) -> list:
        pool = self.layers["unconscious"]
        merged_pairs, used = [], set()
        for i, a in enumerate(pool):
            if a.content_id in used:
                continue
            for b in pool[i + 1:]:
                if b.content_id in used:
                    continue
                if (a.odp_direction != b.odp_direction
                        or a.content_type != b.content_type):
                    continue
                sim = self._pair_similarity(a, b)
                if sim <= ICEBERG_MERGE_SIMILARITY:
                    continue
                coef = self._merge_coefficient(a)
                a.intensity = round(
                    _clamp(max(a.intensity, b.intensity) * coef), 3)
                a.repression_weight = max(a.repression_weight, b.repression_weight)
                a.linkage_tags = list(set(a.linkage_tags) | set(b.linkage_tags))
                pool.remove(b)
                used.add(b.content_id)
                merged_pairs.append(f"{a.summary}<-{b.summary}(x{coef:.2f})")
                break
        if merged_pairs:
            self.log.record(tick, "M7.iceberg", "unconscious merging", merged_pairs)
        return merged_pairs
 
    @staticmethod
    def _pair_similarity(a: MentalContent, b: MentalContent) -> float:
        if not a.linkage_tags or not b.linkage_tags:
            return 0.5 if a.summary == b.summary else 0.0
        inter = len(set(a.linkage_tags) & set(b.linkage_tags))
        union = len(set(a.linkage_tags) | set(b.linkage_tags)) or 1
        return inter / union
 
    def _merge_coefficient(self, mc: MentalContent) -> float:
        if mc.source == "trauma":
            return self.rng.uniform(*ICEBERG_MERGE_COEF["trauma"])
        if mc.source == "transcendental":
            return ICEBERG_MERGE_COEF["transcendental"]
        if mc.content_type in ("worry", "trauma_fragment") or mc.valence < -0.4:
            return ICEBERG_MERGE_COEF["fear"]
        return ICEBERG_MERGE_COEF["generic"]
 
    # ================= alcohol degradation write (alcohol.degradation event) =================
    def apply_alcohol_degradation(self, d: Dict[str, Any]) -> None:
        self.alc_monitor_delta = float(d.get("self_monitoring_delta", 0.0))
        self.alc_permeability_mult = float(d.get("boundary_permeability_mult", 1.0))
        self.alc_override_threshold_mult = float(
            d.get("override_threshold_mult", 1.0))
        self.alc_leak_mult = float(d.get("behavior_leak_mult", 1.0))
        cap = d.get("surface_capacity", 6)
        self.alc_surface_capacity = int(cap) if cap != 6 else None
 
    # ================= hook: P2 swap + query + leakage =================
    def on_boundary(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        # path C: perceptual stimulus intake (tick data or last tick's scene themes)
        themes = tuple(data.get("themes") or
                       board.read("sys.last_scene_themes", ()) or ())
        if themes:
            stimuli = data.get("stimuli") or []
            self.receive_perception_stimulus(
                tick, themes, themes,
                intensity=max((float(st.get("intensity", 0.5))
                               for st in stimuli if isinstance(st, dict)),
                              default=0.5),
                valence=float(data.get("prev_scene_valence",
                                       board.read("sys.prev_scene_valence", 0.0))))
        # drive pressure: the lower the discharge-liquid fullness, the weaker the drive (legacy semantics)
        drive_pressure = 0.0
        if self._discharge is not None:
            drive_pressure = 1.0 - min(1.0,
                                       float(self._discharge.liquid) + 0.5)
        valence = float(board.read("sys.prev_scene_valence", 0.0))
        self.tick_exchange(tick, current_valence=valence,
                           drive_pressure=drive_pressure)
        # self-monitoring: J/P baseline + fatigue/strong-emotion/stress correction
        jp = self._btcs.letter("JP") if self._btcs is not None else None
        srf = 0.0
        if self._hormones is not None:
            srf = float(self._hormones.compute_effective_levels().get("SM_SRF", 0.0))
        sleep_info = board.read("K.pns.sleep", {}) or {}
        self.compute_self_monitoring(
            jp, sleep_pressure=float(sleep_info.get("pressure", 0.0)),
            strong_emotion=abs(valence) > 0.7, srf=srf,
            social_context=bool(themes))
        # path A: columnar query -> K.columnar P3-0 board read
        hits = {}
        for cid in ("PSM_D1", "PSM_D2", "PSM_D4", "PSM_D5",
                    "PSM_D6", "PSM_D7", "PSM_D8", "PSM_D9"):
            h = self.query_by_column(tick, cid, themes,
                                     float(data.get("scene_intensity", 0.3)))
            if h:
                hits[cid] = h
        board.publish("M7.iceberg.column_hits", hits)
        # emotion dyeing -> K.emotion P3-40 board read
        board.publish("M7.iceberg.tone_stain", self.emotion_stain_offset())
        # forced override check (four trigger kinds)
        trauma_severity = float(board.read("sys.trauma_match", 0.0))
        damage = float(board.read("sys.pain", 0.0)) / 10.0
        emotion = board.read("K.emotion.state", {}) or {}
        trigger = self.check_forced_override(
            tick, srf=srf, valence=float(emotion.get("valence", valence)),
            arousal=float(emotion.get("arousal", 0.0)),
            trauma_severity=trauma_severity, damage_signal=damage)
        if trigger:
            board.publish("M7.iceberg.override", trigger)
        # behavior leakage scan -> mirrored to sys.iceberg_leak (read by K.behavior P4-10)
        leak_ret = None
        direction_now = _INTENT_DIRECTION.get(
            str(board.read("sys.last_strategy_name", "")), 0.0)
        best, best_p = None, 0.0
        for layer in ("unconscious", "preconscious"):
            for mc in self.layers[layer]:
                if mc.repression_weight < 0.3:
                    continue
                content_dir = 1.0 if mc.valence > 0 else -1.0
                prob = self.behavior_leak_check(tick, direction_now,
                                                content_dir, mc)
                if prob > best_p:
                    best, best_p = mc, prob
        if best is not None and self.rng.random() < best_p:
            leak_ret = f"inadvertently revealing [{best.summary}]"
        board.publish("M7.iceberg.zone4_leak_ret", leak_ret)      # per-tick overwrite = read-then-clear
        board.publish("M7.iceberg.state", {
            "surface": len(self.layers["conscious"]),
            "preconscious": len(self.layers["preconscious"]),
            "unconscious": len(self.layers["unconscious"]),
            "permeability": round(self.boundary_permeability, 3),
            "self_monitoring": self.self_monitoring,
            "override": self.override_type or "none"})
 
    # ================= hook: P3 suppression adjustment + chaos recovery =================
    def on_cognition_adjust(self, tick: int, data: Dict[str, Any]) -> None:
        avoid: tuple = ()
        if self._odp is not None:
            snap = self._odp.snapshot()
            if isinstance(snap, dict):
                avoid = tuple(d for d, v in snap.items()
                              if isinstance(v, (int, float)) and v < 3.0)
        moral_conflict = bool(self._board.read("M10.morality.active_emotion"))
        self.adjust_repression(tick, odp_avoid_directions=avoid,
                               moral_conflict=moral_conflict)
        self.recover_from_chaos(tick)
 
    # ================= hook: P6 unconscious merge =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.merge_unconscious(tick)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"seq": self._seq,
                "layers": {layer: [mc.to_dict() for mc in self.layers[layer]]
                           for layer in _LAYER_ORDER},
                "boundary_permeability": self.boundary_permeability,
                "self_monitoring": self.self_monitoring,
                "alc": {"monitor_delta": self.alc_monitor_delta,
                        "permeability_mult": self.alc_permeability_mult,
                        "override_threshold_mult": self.alc_override_threshold_mult,
                        "leak_mult": self.alc_leak_mult,
                        "surface_capacity": self.alc_surface_capacity},
                "override": {"active": self.override_active,
                             "type": self.override_type,
                             "recover_tick": self._override_recover_tick,
                             "chaos_monitor_delta": self._chaos_monitor_delta},
                "pending_stimuli": [dict(st) for st in self._pending_stimuli],
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._seq = int(snap.get("seq", 0))
        for layer in _LAYER_ORDER:
            self.layers[layer] = [MentalContent.from_dict(d)
                                  for d in (snap.get("layers", {}).get(layer) or [])]
        self.boundary_permeability = float(snap.get("boundary_permeability", 0.2))
        self.self_monitoring = float(snap.get("self_monitoring", 0.6))
        alc = snap.get("alc") or {}
        self.alc_monitor_delta = float(alc.get("monitor_delta", 0.0))
        self.alc_permeability_mult = float(alc.get("permeability_mult", 1.0))
        self.alc_override_threshold_mult = float(
            alc.get("override_threshold_mult", 1.0))
        self.alc_leak_mult = float(alc.get("leak_mult", 1.0))
        cap = alc.get("surface_capacity")
        self.alc_surface_capacity = int(cap) if cap is not None else None
        ov = snap.get("override") or {}
        self.override_active = bool(ov.get("active", False))
        self.override_type = str(ov.get("type", ""))
        self._override_recover_tick = int(ov.get("recover_tick", -1))
        self._chaos_monitor_delta = float(ov.get("chaos_monitor_delta", 0.0))
        self._pending_stimuli = [dict(st) for st in
                                 (snap.get("pending_stimuli") or [])]
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return all(layer in self.layers for layer in _LAYER_ORDER)
 
    def invariants(self) -> bool:
        for layer, mcs in self.layers.items():
            for mc in mcs:
                if mc.current_layer != layer:                     # layer membership consistent
                    return False
                if not (0.0 <= mc.intensity <= 1.0
                        and 0.0 <= mc.repression_weight <= 1.0):
                    return False
        return 0.0 <= self.self_monitoring <= 1.0
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"conscious": [mc.summary for mc in self.layers["conscious"]],
                "boundary_permeability": round(
                    self.boundary_permeability * self.alc_permeability_mult, 3),
                "self_monitoring": self.self_monitoring,
                "override_active": self.override_active,
                "unconscious_tone": self.unconscious_valence_tone()}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> IcebergStructure:
        engine = IcebergStructure(ctx.rng_for("m7_iceberg"), ctx.log,
                                  ctx.k.card.ice_box)
        engine._board = ctx.board
        engine._bus = ctx.bus
        engine._discharge = ctx.k.discharge
        engine._btcs = ctx.k.btcs
        engine._odp = ctx.k.odp
        engine._hormones = ctx.k.hormones
        # install-time pickup: core memories -> initial preconscious content (not delivered by the hub)
        for cm in ctx.k.card.core_memories:
            engine.inject(0, "memory", str(cm), intensity=0.5,
                          source="experience", layer="preconscious",
                          linkage_tags=[str(cm)])
        return engine
 
    def bind(inst: IcebergStructure, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m7.inject", inst.inject)              # content delivery port
        # alcohol degradation sync (M4 event, dict payload)
        ctx.bus.subscribe(
            "alcohol.degradation",
            lambda item: inst.apply_alcohol_degradation(
                item.get("payload") or {}),
            owner="M7.iceberg")
        # sleep settlement: dream processing + global slight relaxation
        def _on_sleep(item: Dict[str, Any]) -> None:
            payload = item.get("payload") or {}
            inst.dream_process(int(payload.get("tick", 0)))
            inst.sleep_global_relaxation()
        ctx.bus.subscribe("sleep.settle", _on_sleep, owner="M7.iceberg")
        return {
            "P2_boundary": inst.on_boundary,
            "P3_cognition": inst.on_cognition_adjust,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "M7.iceberg",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.iceberg_leak",),                     # contract key committed write
        "gear": {                                                   # resident lightweight, no trigger
            "P2_boundary": {"every": 1, "trigger": None},
            "P3_cognition": {"every": 1, "trigger": None},
            "P6_maintenance": {"every": 1, "trigger": None},
        },
        "priorities": {"P2_boundary": 0,                            # before columnar encoding (P3-0)
                       "P3_cognition": 60,                          # tail of the cognition phase
                       "P6_maintenance": 40},
        "factory": factory,
        "bind": bind,
        "provides": ("sys.iceberg_leak", "m7.inject",
                     "M7.iceberg.column_hits", "M7.iceberg.tone_stain"),
        "requires": {"soft": {"sys.prev_scene_valence": None,
                              "sys.last_scene_themes": None,
                              "sys.trauma_match": None,
                              "alcohol.degradation": None,
                              "sleep.settle": None}},
        "report_key": "iceberg",
        "snapshot_label": "m7_iceberg",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
