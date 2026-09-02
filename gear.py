# -*- coding: utf-8 -*-
# =============================================================================
# gear.py — gear scheduler: gear ratio, trigger dormancy, event wake (V8, chapter 5, revised)
#
# constitutional rules 18-20:
# 18. gears: a module declares a gear ratio (tick divisor); it enters the meshing window only when tick divides evenly.
# 19. dormancy without trigger: inside the window, with no trigger condition, the module sleeps and is skipped (zero cost).
# 20. event wake: a bus event can immediately mesh a dormant module (no waiting for the cycle).
#
# revision log:
# - fixed the wake() base-tick bug: the original _now_for() returned entry.wake_until itself,
# effectively a no-op of wake_until += for_ticks; run_phase now records the current tick,
# and wake uses it as the base (wake_until = current tick + for_ticks).
# - fixed the stats bug: the original did stat["ran"] += ran (cumulative value) inside the loop,
# inflating numbers quadratically; now +1 per hook run.
# - registration sorting moved out of the entry loop (the original re-sorted the whole bucket per entry, O(n^2)).
# - removed the dead placeholder _lock = None.
# - added PHASE_ALIAS: legacy hook names -> P0..P8 logical-phase compatibility mapping,
# so old DLCs (zone1/zone4/pre_sense/sense/post_maintain/...) mount on gears unchanged.
# =============================================================================
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
 
# =============================================================================
# legacy hook names -> P0..P8 logical-phase mapping (compatibility period; new modules declare P* phase names directly)
# compiled from legacy phase semantics and actual legacy DLC mount points.
# =============================================================================
PHASE_ALIAS: Dict[str, str] = {
    "input": "P0_input", "sense_text": "P0_input",
    "zone1": "P1_body", "body": "P1_body", "pre_sense": "P1_body",
    "trigger_eval": "P2_boundary", "intercept": "P2_boundary",
    "boundary": "P2_boundary",
    "zone2": "P3_cognition", "zone3": "P3_cognition",
    "sense": "P3_cognition", "cognition": "P3_cognition",
    "zone4": "P4_decision", "decision": "P4_decision",
    "deposit": "P5_deposit",
    "zone5": "P6_maintenance", "maintain": "P6_maintenance",
    "post_maintain": "P6_maintenance",
    "archive": "P7_archive",
    "readout": "P8_readout",
}
 
 
def canonical_phase(name: str) -> str:
    """map legacy hook names to P0..P8; names already in P* form or unknown are returned as-is."""
    return PHASE_ALIAS.get(name, name)
 
 
class GearEntry:
    """a single gear of one module phase: divisor + optional trigger."""
 
    __slots__ = ("module_id", "phase", "divisor", "priority",
                 "trigger_fn", "hook", "wake_until")
 
    def __init__(self, module_id: str, phase: str, divisor: int,
                 priority: int, trigger_fn: Optional[Callable[[int, Any], bool]],
                 hook: Optional[Callable[[int, Any], None]]) -> None:
        self.module_id = module_id
        self.phase = phase
        self.divisor = max(1, int(divisor))  # zero-guard: at least 1
        self.priority = priority
        self.trigger_fn = trigger_fn
        self.hook = hook
        self.wake_until = 0  # event-wake deadline tick (0 = no wake)
 
    def window_open(self, tick: int) -> bool:
        return tick % self.divisor == 0 or tick <= self.wake_until
 
    def triggered(self, tick: int, data: Any) -> bool:
        if self.trigger_fn is None:
            return True
        try:
            return bool(self.trigger_fn(tick, data))
        except Exception:
            return False  # rather stay still than move wrong
 
    def run(self, tick: int, data: Any) -> bool:
        if self.hook is None:
            return False
        try:
            self.hook(tick, data)
            return True
        except Exception:
            return False  # hook exceptions isolated; scheduling never crashes
 
 
class GearScheduler:
    """gear-based phase dispatcher: double gate (window AND trigger); dormancy = zero cost."""
 
    __slots__ = ("_entries", "_stats", "_last_tick")
 
    def __init__(self) -> None:
        self._entries: Dict[str, List[GearEntry]] = {}
        self._stats: Dict[str, Dict[str, int]] = {}
        self._last_tick = 0  # current tick (wake base, updated by run_phase)
 
    # ---- registration ----
    def register_module(self, module_id: str, gear: Dict[str, Dict[str, Any]],
                        priorities: Dict[str, int],
                        hooks: Dict[str, Callable[[int, Any], None]]) -> None:
        """register a module's gears. gear = {phase: {"every": N, "trigger": fn}}.
                Phase names support P0..P8 and legacy hook names (mapped via PHASE_ALIAS).        """
        for phase, cfg in gear.items():
            canon = canonical_phase(phase)
            hook = hooks.get(phase) or hooks.get(canon)
            if hook is None:
                continue  # no hooks, no gear installation
            entry = GearEntry(
                module_id, canon,
                int(cfg.get("every", 1)),
                priorities.get(phase, priorities.get(canon, 0)),
                cfg.get("trigger") if callable(cfg.get("trigger")) else None,
                hook)
            self._entries.setdefault(canon, []).append(entry)
        for bucket in self._entries.values():
            bucket.sort(key=lambda e: e.priority)
 
    def purge_module(self, module_id: str) -> None:
        for phase in list(self._entries.keys()):
            self._entries[phase] = [
                e for e in self._entries[phase] if e.module_id != module_id]
            if not self._entries[phase]:
                del self._entries[phase]
 
    # ---- event wake (constitutional rule 20) ----
    def wake(self, module_id: str, for_ticks: int = 1) -> None:
        """a bus event immediately meshes a dormant module: extends the wake window based on the current tick."""
        for bucket in self._entries.values():
            for e in bucket:
                if e.module_id == module_id:
                    e.wake_until = max(e.wake_until, self._last_tick + for_ticks)
 
    # ---- dispatch (constitutional rules 18+19) ----
    def run_phase(self, phase: str, tick: int, data: Any) -> Dict[str, int]:
        """execute one phase: window AND trigger, otherwise dormant (zero cost)."""
        self._last_tick = tick
        ran = 0
        slept = 0
        for e in self._entries.get(phase, ()):
            if not e.window_open(tick) or not e.triggered(tick, data):
                slept += 1
                continue
            if e.run(tick, data):
                ran += 1
        stat = self._stats.setdefault(phase, {"ran": 0, "slept": 0})
        stat["ran"] += ran
        stat["slept"] += slept
        return {"ran": ran, "slept": slept}
 
    # ---- stats and four-piece set ----
    def stats(self) -> Dict[str, Dict[str, int]]:
        return dict(self._stats)
 
    def snapshot(self) -> Dict[str, Any]:
        return {
            "gears": {phase: [{"module": e.module_id, "divisor": e.divisor,
                               "wake_until": e.wake_until} for e in bucket]
                      for phase, bucket in self._entries.items()},
            "stats": dict(self._stats),
        }
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        stats = snap.get("stats")
        if isinstance(stats, dict):
            self._stats = dict(stats)  # gear table rebuilt from module registration
 
    def smoke(self) -> bool:
        return isinstance(self._entries, dict)
 
    def invariants(self) -> bool:
        return all(e.divisor >= 1
                   for bucket in self._entries.values() for e in bucket)
