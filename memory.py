# -*- coding: utf-8 -*-
"""K.memory — cognition-domain kernel module (state cache system: Chapter 12, four levels and four pools)

Role:
  - four levels: L0 perceptual afterimage / L1 active cache (AS1-4) / L2 consolidated cache (AS5) / L3 core anchor (never forgotten)
  - four pools: A interaction patterns / B interests..."""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import (CACHE_PARTITION_SPECS, AFFECTIVE_CACHE_MODULATION, SM_SRF)
from .models import PerceptionScene, StateCacheEntry, clamp
 
 
class MemoryEngine:
    """four-pool state cache: dormancy-first — with no encoding/retrieval/consolidation requests, forgetting runs silently in the background."""
 
    def __init__(self, card: Any, rng: Any, log: DecisionLog) -> None:
        self.card = card
        self.rng, self.log = rng, log
        self.pools: Dict[str, List[StateCacheEntry]] = {"A": [], "B": [], "C": [], "D": []}
        self._seq = 0
        self.memory_r_mult = 1.0            # M3: r x(1-CIdx x0.3)
        self.amnesia = 0.0                  # M4: forgetting effect
        self._trauma_fragmented = False     # M8: fragment encoding flag
        self._alcohol_blackout = False      # M4 L4: blackout encoding flag
        self._seed_from_card()              # persona-card level-3 anchor seeds
 
    # ---- seeds: interests -> B pool L2; relationships -> D pool L3; core memories -> B pool anchors ----
    def _seed_from_card(self) -> None:
        for kw in self.card.interests:
            self._insert(self._make_entry("B", f"interest:{kw}",
                                          "warm interaction", "calm", 1, None, 2))
        for pid, impression in self.card.relationships.items():
            self._insert(self._make_entry("D", f"relationship:{impression}",
                                          "warm interaction", "calm", 1, pid, 3))
        for i, mem in enumerate(self.card.core_memories):
            e = self._make_entry("B", f"core cache:{mem}", "social threat", "tense",
                                 3, None, 5)
            e.consolidated = True
            e.consolidation_round = 3
            e.anchor_id = f"anchor-{i}"                             # L3 anchored, never forgotten
            self._insert(e)
 
    def _make_entry(self, pool: str, signature: str, theme: str, tone: str,
                    urgency: int, target: Optional[str], as_level: int) -> StateCacheEntry:
        self._seq += 1
        spec = CACHE_PARTITION_SPECS[pool]
        f = self.rng.uniform(*spec["f_init"])                       # deterministic derived stream
        r = self.rng.uniform(*spec["r_init"])
        return StateCacheEntry(entry_id=f"MEM-{self._seq:04d}", pool=pool,
                               scene_signature=signature, integrated_theme=theme,
                               emotional_tone=tone, urgency=urgency,
                               target_person_id=target, AS=as_level,
                               f=round(f, 3), r=round(r, 3))
 
    def _insert(self, entry: StateCacheEntry) -> None:
        pool = self.pools[entry.pool]
        pool.append(entry)
        cap = CACHE_PARTITION_SPECS[entry.pool]["capacity"]
        if len(pool) > cap:                                         # over capacity: evict the non-anchor entry with the lowest r
            removable = [e for e in pool if e.anchor_id is None]
            if removable:
                pool.remove(min(removable, key=lambda e: e.r))
 
    # ================= 12.4 encoding =================
    def set_v3_encoding_flags(self, trauma_fragmented: bool = False,
                              alcohol_blackout: bool = False) -> None:
        """V3.0 flag injection (legacy compatibility surface): M8 fragment encoding / M4 blackout intermittent encoding."""
        self._trauma_fragmented = trauma_fragmented
        self._alcohol_blackout = alcohol_blackout
 
    def serialize_state_snapshot(self, tick: int, scene: PerceptionScene,
                                 hormones: Dict[str, float],
                                 pool_hint: str = "B") -> Optional[StateCacheEntry]:
        """encoding: same-signature dedup counting; emotion modulation matrix; flashbulb effect; blackout intermittency (unrecoverable)."""
        if not scene.perception_fragments:
            return None
        if self._alcohol_blackout and self.rng.random() < 0.5:      # M4 L4: 50% encoding interruption
            self.log.record(tick, "StateCacheSystem", "blackout",
                            "alcohol L4: encoding interrupted (memory gap)")
            return None
        frag = max(scene.perception_fragments, key=lambda f: f.urgency)
        target = frag.signal.target
        signature = f"{scene.integrated_theme}:{frag.signal.category}:{target or '-'}"
        tone = scene.emotional_tone or "neutral"
        pool = "D" if target else pool_hint                         # objects go to the D pool
        for e in self.pools[pool]:                                  # dedup: same signature -> count +r
            if e.scene_signature == signature:
                e.occurrence_count += 1
                e.r = clamp(e.r + 0.05)
                return e
        as_level = min(5, 1 + scene.urgency + (1 if tone != "neutral" else 0))
        if not CACHE_PARTITION_SPECS[pool]["consolidatable"] and as_level >= 5 \
                and pool in ("A", "C"):
            as_level = 4                                            # A/C stay at L1 forever
        entry = self._make_entry(pool, signature, scene.integrated_theme,
                                 tone, scene.urgency, target, as_level)
        f_mod, r_mod = AFFECTIVE_CACHE_MODULATION.get(tone, (1.0, 1.0))
        entry.f = round(clamp(entry.f * f_mod), 3)
        entry.r = round(clamp(entry.r * r_mod), 3)
        if hormones.get(SM_SRF, 0) > 60:
            entry.r = round(clamp(entry.r * 1.3), 3)                # flashbulb effect
        entry.r = round(clamp(entry.r * self.memory_r_mult), 3)     # M3 modulation
        if self._trauma_fragmented:                                 # M8: temporal order lost
            entry.fragmented = True
            entry.temporal_order_lost = True
        if self._alcohol_blackout:                                  # M4: in-drunkenness encoding mark
            entry.alcohol_affected = True
            entry.r = round(clamp(entry.r * 0.7), 3)
        self._insert(entry)
        self.log.record(tick, "StateCacheSystem", "encode",
                        f"[Pool {pool}] {signature} AS={as_level} f={entry.f} r={entry.r}")
        return entry
 
    # ================= M4: sleep-period memory reorganization (blackout fragments self-padded) =================
    def reorganize_after_blackout(self, tick: int) -> List[str]:
        """blackout is unrecoverable; fragments may be padded during reorganization (content not faithful, only narrative coherence maintained)."""
        filled = []
        for pool in self.pools.values():
            for e in pool:
                if e.alcohol_affected and e.r > 0.3 and self.rng.random() < 0.3:
                    e.integrated_theme = f"{e.integrated_theme}(reorganization padding)"
                    e.alcohol_affected = False
                    filled.append(e.entry_id)
        if filled:
            self.log.record(tick, "StateCacheSystem", "reorganization padding", filled)
        return filled
 
    # ================= retrieval =================
    def recall_historical_state(self, tick: int,
                                person_id: Optional[str] = None,
                                signature_keywords: tuple = (),
                                emotional_tone: Optional[str] = None) -> List[StateCacheEntry]:
        """surfacing retrieval: hard match + soft match, AS*r descending top-2; anterograde amnesia keeps only anchors."""
        hits = []
        for pool in self.pools.values():
            for e in pool:
                hard = (person_id and e.target_person_id == person_id) or \
                       any(k in e.scene_signature for k in signature_keywords)
                soft = emotional_tone and e.emotional_tone == emotional_tone
                if hard or soft:
                    hits.append(e)
        hits.sort(key=lambda e: e.AS * e.r, reverse=True)
        top = hits[:2]
        if self.amnesia > 0.3:                                      # M4: new encodings cannot consolidate
            top = [e for e in top if e.anchor_id is not None]
        for e in top:
            e.retrieval_count += 1
        self.log.record(tick, "StateCacheSystem", "recall",
                        [f"{e.scene_signature}(AS×r={e.AS * e.r:.2f})" for e in top])
        return top
 
    def compute_familiarity_score(self, tick: int, person_id: str) -> float:
        """familiarity cross-query: peak AS*r of this object's D-pool entries / 5."""
        entries = [e for e in self.pools["D"] if e.target_person_id == person_id]
        if not entries:
            return 0.0
        score = max(e.AS * e.r for e in entries) / 5.0
        return round(clamp(score), 3)
 
    # ================= 12.4 F2 adjudication (four paths) =================
    def execute_cache_arbitration(self, tick: int) -> Dict[str, int]:
        stats = {"A fuzzy retain": 0, "B stable maintain": 0,
                 "C accelerated forgetting": 0, "D delete": 0}
        for pool_name, pool in self.pools.items():
            survivors = []
            for e in pool:
                if e.anchor_id is not None:                         # anchor exemption
                    survivors.append(e)
                    continue
                if e.r > 0.6 and e.AS >= 2:                         # A: ambiguous keep
                    e.f = round(clamp(e.f * 1.2), 3)
                    e.r = round(clamp(e.r * 0.95), 3)
                    stats["A fuzzy retain"] += 1
                elif e.r > 0.4 and e.AS >= 2:                       # B: stable maintain
                    stats["B stable maintain"] += 1
                elif e.r <= 0.4:                                    # C: accelerated forgetting
                    e.f = round(clamp(e.f * 1.8), 3)
                    e.r = round(clamp(e.r * 0.7), 3)
                    stats["C accelerated forgetting"] += 1
                if e.r <= 0.2 or e.f > 0.5:                         # D: delete
                    stats["D delete"] += 1
                    continue
                survivors.append(e)
            self.pools[pool_name] = survivors
        self.log.record(tick, "StateCacheSystem", "F2 arbitration", stats)
        return stats
 
    # ================= 12.4 sleep consolidation =================
    def execute_cache_persistence(self, tick: int, quality: float) -> Dict[str, Any]:
        """B/D sampled consolidation (rounds>=3 and AS=5 promote to L3); A/C full adjudication for accelerated cleanup."""
        upgraded, reinforced = [], 0
        for pool_name in ("B", "D"):
            candidates = [e for e in self.pools[pool_name]
                          if e.AS >= 2 and e.anchor_id is None]
            sample = [e for e in candidates if self.rng.random() < 0.5 * quality + 0.2]
            for e in sample:
                e.consolidation_round += 1
                if e.consolidation_round >= 3 and e.AS == 5:
                    e.consolidated = True
                    e.anchor_id = f"anchor-{e.entry_id}"            # promote to L3 anchor
                    upgraded.append(e.scene_signature)
                elif e.AS < 5:
                    e.f = round(clamp(e.f * 0.8), 3)                # light reinforcement
                    reinforced += 1
        for pool_name in ("A", "C"):
            for e in list(self.pools[pool_name]):
                e.f = round(clamp(e.f * 1.5), 3)
                e.r = round(clamp(e.r * 0.8), 3)
                if e.r <= 0.2 or e.f > 0.5:
                    self.pools[pool_name].remove(e)
        result = {"upgraded_to_L3": upgraded, "reinforced": reinforced}
        self.log.record(tick, "StateCacheSystem", "sleep consolidation", result)
        return result
 
    def pool_snapshot(self) -> Dict[str, list]:
        return {p: [f"{e.scene_signature}(AS={e.AS},r={e.r:.2f}"
                    f"{'*' if e.anchor_id else ''})" for e in entries]
                for p, entries in self.pools.items()}
 
    # ================= P5 hook (encoding) =================
    def on_deposit(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        cidx = float(board.read("sys.cognitive_index", 0.0))
        self.memory_r_mult = 1.0 - cidx * 0.3                       # M3: r x(1-CIdx x0.3)
        self.amnesia = float(board.read_knob("knob.amnesia", 0.0))
        self.set_v3_encoding_flags(
            trauma_fragmented=bool(board.read("sys.trauma_active", False)),
            alcohol_blackout=bool(board.read("sys.alcohol_blackout", False)))
        hormones = board.read("K.pns.hormones", {}) or {}
        self.serialize_state_snapshot(tick, data["scene"], hormones)  # trigger guarantees the scene is non-empty
        board.publish("K.memory.pools",
                      {p: len(entries) for p, entries in self.pools.items()})
 
    # ================= P6 hook (F2 adjudication, 20:1) =================
    def on_maintenance(self, tick: int, data: Dict[str, Any]) -> None:
        self.execute_cache_arbitration(tick)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"pools": {p: [asdict(e) for e in entries]
                          for p, entries in self.pools.items()},
                "seq": self._seq,
                "rng": self.rng.snapshot()}                 # stream cursor saved with the snapshot (ABMI 1.0)
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        pools = snap.get("pools")
        if isinstance(pools, dict):
            for name, entries in pools.items():
                if name in self.pools and isinstance(entries, list):
                    self.pools[name] = [StateCacheEntry(**e) for e in entries]
        self._seq = int(snap.get("seq", self._seq))
        self.rng.restore(snap.get("rng"))                   # cursor rewind (silent when absent)
 
    def smoke(self) -> bool:
        return set(self.pools.keys()) == {"A", "B", "C", "D"}
 
    def invariants(self) -> bool:
        for name, pool in self.pools.items():
            cap = CACHE_PARTITION_SPECS[name]["capacity"]
            anchored = sum(1 for e in pool if e.anchor_id is not None)
            if len(pool) > cap + anchored:                          # over-capacity only allows anchor overflow
                return False
            if any(not (0.0 <= e.f <= 1.0 and 0.0 <= e.r <= 1.0) for e in pool):
                return False
        return True
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {p: len(entries) for p, entries in self.pools.items()}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> MemoryEngine:
        engine = MemoryEngine(ctx.k.card, ctx.rng_for("memory"), ctx.log)
        engine._board = ctx.board
        ctx.k.memory = engine                                       # backfill kernel ports
        ctx.bus.subscribe("sleep.settle",                           # sleep consolidation: bus-driven
                          lambda item: engine.execute_cache_persistence(
                              item["payload"]["tick"], item["payload"]["quality"]),
                          owner="K.memory")
        ctx.bus.subscribe("sleep.settle",                           # blackout reorganization: same event
                          lambda item: engine.reorganize_after_blackout(
                              item["payload"]["tick"]),
                          owner="K.memory", priority=10)
        return engine
 
    def bind(inst: MemoryEngine, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("memory.recall", inst.recall_historical_state)      # retrieval service
        ctx.services.offer("memory.familiarity", inst.compute_familiarity_score)
        return {
            "P5_deposit": inst.on_deposit,
            "P6_maintenance": inst.on_maintenance,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.memory",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P5_deposit": {"every": 1,
                           "trigger": lambda t, d: d.get("scene") is not None},
            "P6_maintenance": {"every": 20},                        # 20:1 epistemic rhythm
        },
        "priorities": {"P5_deposit": 0, "P6_maintenance": 20},
        "factory": factory,
        "bind": bind,
        "provides": ("K.memory.pools",),
        "requires": {},
        "report_key": "memory",
        "snapshot_label": "memory",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
