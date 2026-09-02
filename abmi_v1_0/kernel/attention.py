# -*- coding: utf-8 -*-
"""K.attention — cognition-domain kernel module (Station 1: perceptual salience competition, 7.1)

Role:
  - all perception must pass this competition to enter CNS: three-way signals (PNS raw / nine-column encoding / endogenous) register
  - three-step competition algorithm (1+1=2, only compare and map): quadrant pre-filter"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import (PERCEPTION_MATRIX_QUADRANTS, MATRIX_QUADRANT_CN,
                        CATEGORY_QUADRANT, MATRIX_INTERNAL_PHYSICAL,
                        MATRIX_INTERNAL_PERCEPTUAL, MATRIX_EXTERNAL_PHYSICAL,
                        MATRIX_EXTERNAL_PERCEPTUAL, ATTENTION_CAPACITY,
                        ATTENTION_DECAY, URGENCY_MULT_FLAG, INERTIA_STICKY,
                        TMO_CONSCIOUSNESS_T1, TMO_CONSCIOUSNESS_T2)
from .models import PerceptionSignal, SignalSourceEntry, clamp
 
 
def matrix_quadrant_of(sig: PerceptionSignal) -> str:
    """signal -> quadrant: category table first; interoceptor/internal types go internal-somatic; the rest external-somatic."""
    if sig.category in CATEGORY_QUADRANT:
        return CATEGORY_QUADRANT[sig.category]
    if sig.source == "interoceptor" or sig.type == "internal":
        return MATRIX_INTERNAL_PHYSICAL
    return MATRIX_EXTERNAL_PHYSICAL
 
 
class AttentionEngine:
    """perception-classification-matrix competition filter; default scan mode rotates every 3 ticks (E types scan outward, I types scan inward)."""
 
    _THREAT_CATS = ("threat", "sudden threat", "social threat",
                    "status challenge", "clashing blades", "loud noise")
    _SAFETY_CATS = ("safety", "comfort", "attachment presence", "rest point")
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.sources: Dict[str, SignalSourceEntry] = {}             # signal-source ledger
        self._seq = 0                                               # registration sequence number
        self._pending_decay: List[tuple] = []                       # loser delayed-decay queue
        self.last_winners: List[SignalSourceEntry] = []             # last round's winner
        self.capacity_cap: Optional[int] = None                     # M4 consciousness suppression: None=2, 1, 0
        self.cognitive_mult = 1.0                                   # M3: cognitive sensitivity
        self.food_check_weight_mult = 1.0                           # M5: low food security -> food signal x2
        self.trauma_threat_mult = 1.0                               # M8: threat weight amplification
        self.trauma_safety_mult = 1.0                               # M8: safety signal compression
        self.trauma_neutral_mult = 1.0                              # M8: neutral misjudgment amplification
        self.attention_jump_mult = 1.0                              # M4 L3: attention switching accelerated
 
    # ---- M8 perception-distortion injection (legacy compatibility surface; V8 hooks soft-read via the board) ----
    def apply_trauma_perception(self, layers: Optional[dict]) -> None:
        if not layers:
            self.trauma_threat_mult, self.trauma_safety_mult, self.trauma_neutral_mult = 1.0, 1.0, 1.0
            return
        pd = layers.get("perceptual distortion", {})
        self.trauma_threat_mult = pd.get("threat_weight_mult", 1.0)
        self.trauma_safety_mult = pd.get("safety_signal_mult", 1.0)
        self.trauma_neutral_mult = pd.get("neutral_misjudge_mult", 1.0)
 
    # ---- M4 alcohol-degradation injection (legacy compatibility surface) ----
    def apply_alcohol_degradation(self, jump_mult: float = 1.0,
                                  capacity: Optional[int] = None) -> None:
        self.attention_jump_mult = jump_mult
        if capacity is not None:
            self.capacity_cap = capacity
 
    # ---- signal registration (three-way confluence) ----
    def register_signals(self, tick: int, raw_signals: list,
                         columnar_signals: list, endogenous_signals: list) -> None:
        for sig in list(raw_signals) + list(columnar_signals) + list(endogenous_signals):
            self._upsert(tick, sig)
 
    def _upsert(self, tick: int, sig: PerceptionSignal) -> SignalSourceEntry:
        quadrant = matrix_quadrant_of(sig)
        sid = f"{quadrant}:{sig.category}:{sig.target or '-'}"
        if sid in self.sources:                                     # existing source: update intensity and novelty
            src = self.sources[sid]
            src.novelty = clamp(abs(sig.intensity - src.baseline) * 1.5, 0.05, 1.0)
            src.raw_intensity = sig.intensity
            src.urgency_flag = sig.urgency
            src.theme_hint = sig.theme_hint or src.theme_hint
            src.target = sig.target or src.target
        else:                                                       # new source: create a record
            self._seq += 1
            src = SignalSourceEntry(
                id=sid, quadrant=quadrant, raw_intensity=sig.intensity,
                novelty=clamp(abs(sig.intensity - 0.3) * 1.5, 0.05, 1.0),
                urgency_flag=sig.urgency, category=sig.category,
                theme_hint=sig.theme_hint, target=sig.target)
            self.sources[sid] = src
        return src
 
    # ---- three-step competition ----
    def execute_priority_competition(self, tick: int,
                                     bias_map: Dict[str, float]) -> List[SignalSourceEntry]:
        capacity = ATTENTION_CAPACITY if self.capacity_cap is None else self.capacity_cap
        if capacity <= 0:                                           # consciousness suppression: CNS receives no scene
            self.log.record(tick, "biomimetic.Station-1", "attention capacity=0",
                            "consciousness suppression")
            self.last_winners = []
            return []
        active = [s for s in self.sources.values() if s.raw_intensity > 0.01]
        if not active:
            return self.default_scan_mode(tick, bias_map)           # zero input -> default scan
        for s in active:
            urgency_mult = URGENCY_MULT_FLAG if s.urgency_flag else 1.0
            w = s.check_weight
            if s.category in ("hunger", "food"):
                w *= self.food_check_weight_mult                    # M5 food weight
            if s.last_attended_round == tick - 1:
                w *= INERTIA_STICKY                                 # inertia stickiness
            if s.category in self._THREAT_CATS:                     # M8 perception distortion
                w *= self.trauma_threat_mult
            elif s.category in self._SAFETY_CATS:
                w *= self.trauma_safety_mult
            elif self.trauma_neutral_mult > 1.0:
                w *= self.trauma_neutral_mult * 0.5
            if self.attention_jump_mult > 1.0 and s.last_attended_round != tick - 1:
                w *= self.attention_jump_mult                       # M4 L3 switching acceleration
            s.salience = (s.raw_intensity * (0.3 + 0.7 * s.novelty)
                          * urgency_mult * w
                          * bias_map.get(s.quadrant, 1.0)           # BTCS quadrant weights (board mirror)
                          * self.cognitive_mult)                    # M3 cognitive sensitivity
            s.won_quadrant = False
            s.won_global = False
        candidates = []
        for q in PERCEPTION_MATRIX_QUADRANTS:                       # quadrant pre-screen: top 2 per quadrant
            in_q = sorted((s for s in active if s.quadrant == q),
                          key=lambda s: s.salience, reverse=True)
            for s in in_q[:2]:
                s.won_quadrant = True
                candidates.append(s)
        candidates.sort(key=lambda s: s.salience, reverse=True)
        winners = candidates[:capacity]                             # cross-quadrant competition: capacity-capped
        for s in winners:
            s.won_global = True
            s.last_attended_round = tick
        losers = [s for s in candidates if not s.won_global]
        self._pending_decay = [(tick + 1, s.id) for s in losers]    # losers decay with one-tick delay
        self.last_winners = winners
        self.log.record(tick, "biomimetic.Station-1", "competition",
                        [(f"{MATRIX_QUADRANT_CN[s.quadrant]}/{s.category}",
                          round(s.salience, 3)) for s in winners])
        return winners
 
    # ---- default mode (at zero input) ----
    def default_scan_mode(self, tick: int,
                          bias_map: Dict[str, float]) -> List[SignalSourceEntry]:
        """endogenous scan: 3-tick rotation; E types scan the external more, I types focus inward (letters from the board mirror)."""
        ie = self._letters.get("IE")
        if ie == "E":
            quad = MATRIX_EXTERNAL_PHYSICAL if tick % 3 else MATRIX_EXTERNAL_PERCEPTUAL
            cat = "environmental scanning"
        else:
            quad = MATRIX_INTERNAL_PERCEPTUAL if tick % 3 else MATRIX_INTERNAL_PHYSICAL
            cat = "endogenous wandering"
        src = SignalSourceEntry(id=f"default:{tick}", quadrant=quad,
                                raw_intensity=0.25, novelty=0.2, category=cat)
        src.salience = 0.1
        src.won_global = True
        self.last_winners = [src]
        self.log.record(tick, "biomimetic.Station-1", "default mode", cat)
        return [src]
 
    # ---- CNS weight feedback (7.1; service-port entry) ----
    def apply_feedback(self, tick: int, source_id: str, condition: str) -> None:
        s = self.sources.get(source_id)
        if s is None:
            return
        if condition == "trigger behavior-goal action":
            s.check_weight = min(2.0, s.check_weight + 0.5)
        elif condition == "misjudgment":
            s.check_weight = max(0.3, s.check_weight - 0.3)
        elif condition == "active ignoring":
            s.check_weight = max(0.3, s.check_weight - 0.2)
        elif condition == "unattended":
            s.check_weight = max(0.3, s.check_weight - ATTENTION_DECAY)
        self.log.record(tick, "biomimetic.Station-1", f"feedback:{condition}",
                        f"{s.category} weight -> {s.check_weight:.2f}")
 
    # ---- background maintenance (P6 every tick) ----
    def background_maintenance(self, tick: int) -> None:
        for s in self.sources.values():
            if s.check_weight > 1.0:                                # weights regress toward 1.0
                s.check_weight = max(1.0, s.check_weight - ATTENTION_DECAY)
            elif s.check_weight < 1.0:
                s.check_weight = min(1.0, s.check_weight + ATTENTION_DECAY)
            s.baseline += (s.raw_intensity - s.baseline) * 0.1      # baseline tracking
            s.raw_intensity *= 0.6                                  # intensity natural decay
            if s.raw_intensity < 0.3:
                s.urgency_flag = False
        stale = [sid for sid, s in self.sources.items() if s.raw_intensity < 0.05]
        for sid in stale:                                           # residue cleanup
            del self.sources[sid]
        for due_tick, sid in self._pending_decay:                   # losers decay when due
            if due_tick <= tick and sid in self.sources:
                s = self.sources[sid]
                s.check_weight = max(0.3, s.check_weight - ATTENTION_DECAY)
        self._pending_decay = [(t, i) for t, i in self._pending_decay if t > tick]
 
    # ================= P3 hook (V8 module surface) =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board                                         # injected at install time
        # soft-key reads (DLC absent = neutral default)
        cidx = float(board.read("sys.cognitive_index", 0.0))
        self.cognitive_mult = 1.0 - cidx * 0.5                      # M3: x(1-CIdx x0.5)
        suppression = float(board.read_knob("knob.consciousness_suppression", 0.0))
        if board.read("sys.unconsciousness", False) or suppression > TMO_CONSCIOUSNESS_T2:
            self.capacity_cap = 0                                   # suppression >0.8: capacity 0
        elif suppression > TMO_CONSCIOUSNESS_T1:
            self.capacity_cap = 1                                   # suppression >0.5: capacity 1
        else:
            self.capacity_cap = None                                # default capacity 2
        self.attention_jump_mult = float(board.read("sys.alcohol_attention_jump", 1.0))
        self.food_check_weight_mult = float(board.read_knob("knob.food_check_weight_mult", 1.0))
        self.apply_trauma_perception(board.read("M8.trauma.perceptual_layers"))
        self._letters = board.read("K.persona.letters", {}) or {}   # persona-letter mirror
        bias_map = board.read("K.persona.bias", {}) or {}           # quadrant-weight mirror
        self.register_signals(tick, data.get("signals", ()),
                              data.get("columnar_signals", ()),
                              data.get("endogenous_signals", ()))
        winners = self.execute_priority_competition(tick, bias_map)
        data["winners"] = winners                                   # -> Station 2
        board.publish("K.attention.winners", [s.id for s in winners])
 
    # ---- P6 hook ----
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.background_maintenance(tick)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {
            "sources": {sid: dict(vars(s))                          # copy: vars is a live reference
                        for sid, s in self.sources.items()},
            "seq": self._seq,
            "pending_decay": list(self._pending_decay),
        }
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        sources = snap.get("sources")
        if isinstance(sources, dict):
            self.sources = {sid: SignalSourceEntry(**state)
                            for sid, state in sources.items()}
        self._seq = int(snap.get("seq", 0))
        pending = snap.get("pending_decay")
        if isinstance(pending, list):
            self._pending_decay = [tuple(p) for p in pending]
 
    def smoke(self) -> bool:
        return isinstance(self.sources, dict)
 
    def invariants(self) -> bool:
        return all(0.3 <= s.check_weight <= 2.0 for s in self.sources.values())
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"sources": len(self.sources),
                "winners": [s.category for s in self.last_winners]}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> AttentionEngine:
        engine = AttentionEngine(ctx.log)
        engine._board = ctx.board
        engine._letters = {}                                        # placeholder before the first tick
        ctx.k.attention = engine                                    # backfill kernel ports
        return engine
 
    def bind(inst: AttentionEngine, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("attention.feedback", inst.apply_feedback)  # CNS feedback service
        return {
            "P3_cognition": inst.on_cognition,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.attention",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P3_cognition": {"every": 1, "trigger": None},          # 1:1 always-on (default scan is indispensable)
            "P6_maintenance": {"every": 1, "trigger": None},        # 1:1 background maintenance
        },
        "priorities": {"P3_cognition": 10, "P6_maintenance": 0},    # after column encoding, before the interpreter
        "factory": factory,
        "bind": bind,
        "provides": ("K.attention.winners",),
        "requires": {},
        "report_key": "attention",
        "snapshot_label": "attention",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
