# -*- coding: utf-8 -*-
# =============================================================================
# consciousness.py — V8 governance: consciousness state machine (constitution, governance)
#
# states: awake / sleep / t3 therapeutic inhibition / l7 alcohol hard power-cut /
# coma siege coma (consciousness cuts its own power, leaving IDNS nothing to hijack).
#
# revision log:
# - constructor signature fixed to no-arg; the original assembly called ConsciousnessStateMachine(log)
# which raises TypeError — fixed on the assembly side.
# - enter/exit now keep history-residency count consistency (exit also counts into _history).
# =============================================================================
from __future__ import annotations
from typing import Any, Dict
 
STATE_AWAKE = "awake"
STATE_SLEEP = "sleep"
STATE_T3 = "t3"
STATE_L7 = "l7"
STATE_COMA = "coma"
ALL_STATES = (STATE_AWAKE, STATE_SLEEP, STATE_T3, STATE_L7, STATE_COMA)
 
 
class ConsciousnessStateMachine:
    """consciousness state machine with guarded transitions (illegal state names rejected)."""
 
    __slots__ = ("_state", "_since", "_reason", "_coma_gap_ticks", "_history")
 
    def __init__(self) -> None:
        self._state = STATE_AWAKE
        self._since = 0
        self._reason = ""
        self._coma_gap_ticks = 0
        self._history: Dict[str, int] = {}
 
    # ---- state queries ----
    @property
    def state(self) -> str:
        return self._state
 
    @property
    def coma_gap_ticks(self) -> int:
        return self._coma_gap_ticks
 
    def is_conscious(self) -> bool:
        return self._state in (STATE_AWAKE, STATE_SLEEP)
 
    # ---- guarded transitions ----
    def _switch(self, tick: int, state: str, reason: str) -> bool:
        if state not in ALL_STATES or state == self._state:
            return False
        self._state = state
        self._since = tick
        self._reason = reason
        self._history[state] = self._history.get(state, 0) + 1
        return True
 
    def enter(self, tick: int, state: str, reason: str = "") -> bool:
        return self._switch(tick, state, reason)
 
    def exit(self, tick: int, target: str, reason: str = "") -> bool:
        return self._switch(tick, target, reason)
 
    # ---- siege linkage — called by KheshigGuard ----
    def enter_siege(self, tick: int) -> bool:
        if self._state == STATE_COMA:
            return False
        self._state = STATE_COMA
        self._since = tick
        self._reason = "kheshig siege"
        self._history[STATE_COMA] = self._history.get(STATE_COMA, 0) + 1
        self._coma_gap_ticks = 0
        return True
 
    def exit_siege(self, tick: int) -> bool:
        if self._state != STATE_COMA:
            return False
        self._state = STATE_AWAKE
        self._since = tick
        self._reason = "siege lifted"
        return True
 
    # ---- coma timing (called as siege beats advance) ----
    def tick_gap(self, tick: int) -> None:
        if self._state == STATE_COMA:
            self._coma_gap_ticks += 1
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"state": self._state, "since": self._since,
                "reason": self._reason, "coma_gap_ticks": self._coma_gap_ticks,
                "history": dict(self._history)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        state = snap.get("state")
        if state in ALL_STATES:
            self._state = state
        self._since = int(snap.get("since", 0))
        self._reason = str(snap.get("reason", ""))
        self._coma_gap_ticks = int(snap.get("coma_gap_ticks", 0))
        h = snap.get("history")
        if isinstance(h, dict):
            self._history = dict(h)
 
    def smoke(self) -> bool:
        return self._state in ALL_STATES
 
    def invariants(self) -> bool:
        return (self._state in ALL_STATES
                and self._coma_gap_ticks >= 0
                and self._since >= 0)
