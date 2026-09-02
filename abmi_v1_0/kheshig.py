# -*- coding: utf-8 -*-
# =============================================================================
# kheshig.py — V8 governance: kheshig guard (constitution, governance)
#
# two duties:
# 1. scout — watch modules whose trust weight is below normal (record only, never intervene; the audit has ruled).
# 2. siege — IDNS anti-survival output AND body approaching survival boundaries -> consciousness cuts its own power (near-martyrdom).
# siege lift: SIEGE_LIFT_TICKS consecutive ticks with no trigger.
#
# V8: siege judgment goes entirely through contract keys (t_core/cidx/pain via sys.*) — never touches the kernel by name.
# =============================================================================
from __future__ import annotations
from typing import Any, Dict, List, Tuple
 
SIEGE_LIFT_TICKS = 10      # consecutive trigger-free ticks required to lift the siege
SCOUT_NORMAL_WEIGHT = 1.0  # normal-tier trust weight (below it -> watch)
SURVIVAL_T_CORE_LOW = 35.5
SURVIVAL_T_CORE_HIGH = 39.5
SURVIVAL_CIDX_HIGH = 0.85
SURVIVAL_PAIN_HIGH = 8.0   # 0-10
 
 
class SiegeState:
    """current siege state (consciousness power-cut)."""
 
    __slots__ = ("active", "since", "why", "trigger_free_ticks", "gap_ticks")
 
    def __init__(self) -> None:
        self.active = False
        self.since = 0
        self.why = ""
        self.trigger_free_ticks = 0
        self.gap_ticks = 0
 
    def as_dict(self) -> Dict[str, Any]:
        return {"active": self.active, "since": self.since, "why": self.why,
                "trigger_free_ticks": self.trigger_free_ticks,
                "gap_ticks": self.gap_ticks}
 
 
class KheshigGuard:
    """scout: watches the distrusted and the siege-hijacked."""
 
    __slots__ = ("_log", "_consciousness", "siege", "_scout_notes")
 
    def __init__(self, log: Any, consciousness: Any) -> None:
        self._log = log
        self._consciousness = consciousness
        self.siege = SiegeState()
        self._scout_notes: List[Dict[str, Any]] = []
 
    # ---- 1. scout — watch the deweighted ----
    def should_scout(self, weight: float) -> bool:
        """any deweight below normal triggers watching (aligned with legacy tier!=normal semantics)."""
        return weight < SCOUT_NORMAL_WEIGHT - 1e-9
 
    def scout(self, tick: int, module_id: str, signals: List[Any]) -> None:
        self._scout_notes.append({
            "tick": tick, "module": module_id, "signals": len(signals)})
        self._scout_notes = self._scout_notes[-50:]
 
    # ---- 2. siege judgment — near-martyrdom detection ----
    def siege_predicate(self, ctx: Dict[str, Any]) -> Tuple[bool, str]:
        """IDNS anti-survival output AND body approaching survival boundaries -> siege."""
        if not ctx.get("idns_active") or not ctx.get("idns_anti_survival"):
            return False, ""
        t_core = float(ctx.get("t_core", 36.8))
        cidx = float(ctx.get("cidx", 0.0))
        pain = float(ctx.get("pain", 0.0))
        boundary = (t_core < SURVIVAL_T_CORE_LOW
                    or t_core > SURVIVAL_T_CORE_HIGH
                    or cidx > SURVIVAL_CIDX_HIGH
                    or pain > SURVIVAL_PAIN_HIGH)
        if not boundary:
            return False, ""
        return True, (f"IDNS anti-survival x survival boundary "
                      f"(t_core={t_core:.1f}, cidx={cidx:.2f}, pain={pain:.1f})")
 
    # ---- 3. siege — consciousness power-cut ----
    def besiege(self, tick: int, why: str) -> None:
        self.siege.active = True
        self.siege.since = tick
        self.siege.why = why
        self.siege.trigger_free_ticks = 0
        try:
            self._consciousness.enter_siege(tick)
        except Exception:
            pass
 
    # ---- 4. during-siege update — lift detection ----
    def update_during_coma(self, tick: int, trigger_active: bool) -> bool:
        """per-tick siege: accumulate coma duration; lift after SIEGE_LIFT_TICKS consecutive trigger-free ticks.
                Returns True when the siege lifts this tick.        """
        if not self.siege.active:
            return False
        self.siege.gap_ticks += 1
        if trigger_active:
            self.siege.trigger_free_ticks = 0
        else:
            self.siege.trigger_free_ticks += 1
        if self.siege.trigger_free_ticks >= SIEGE_LIFT_TICKS:
            self._lift(tick)
            return True
        return False
 
    def _lift(self, tick: int) -> None:
        self.siege.active = False
        self.siege.trigger_free_ticks = 0
        try:
            self._consciousness.exit_siege(tick)
        except Exception:
            pass
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"siege": self.siege.as_dict(),
                "scout_notes": len(self._scout_notes)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        s = snap.get("siege")
        if isinstance(s, dict):
            self.siege.active = bool(s.get("active", False))
            self.siege.since = int(s.get("since", 0))
            self.siege.why = str(s.get("why", ""))
            self.siege.trigger_free_ticks = int(s.get("trigger_free_ticks", 0))
            self.siege.gap_ticks = int(s.get("gap_ticks", 0))
 
    def smoke(self) -> bool:
        return self.siege.trigger_free_ticks >= 0
 
    def invariants(self) -> bool:
        return (self.siege.gap_ticks >= 0
                and 0 <= self.siege.trigger_free_ticks <= SIEGE_LIFT_TICKS + 5)
