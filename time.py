# -*- coding: utf-8 -*-
# =============================================================================
# time.py — dual-clock time sovereignty (V8 skeleton, chapter 4, revised)
#
# computation clock (tick): one beat = one experienced unit, not a time quantity.
# dialogue mode: tick = one conversation turn (dt content-driven, may jump).
# server mode: tick = 0.1ms (dt fixed).
# narrative clock (dt): story time (minutes), fully decoupled from tick.
#
# constitutional rules 5/16: tick sovereignty lives here, nowhere else. Modules only receive (t, data);
# whoever writes tick outside TimeKeeper breaks the constitution.
# =============================================================================
from __future__ import annotations
from typing import Any, Dict, Optional
 
MODE_DIALOGUE = "dialogue"
MODE_SERVER = "server"
SERVER_DT_MS = 0.1
SERVER_DT_MINUTES = SERVER_DT_MS / 60000.0
DEFAULT_EPOCH_TICKS = 5000  # default epoch length (ticks; scene-configurable)
 
 
class TimeKeeper:
    """dual-clock sovereignty: computation beats + narrative minutes. Publishes sys.tick / sys.dt / sys.mode every tick."""
 
    __slots__ = ("_tick", "_minutes", "_mode", "_start_hour",
                 "_epoch_ticks", "_last_dt")
 
    def __init__(self, start_hour: float = 8.0, mode: str = MODE_DIALOGUE,
                 epoch_ticks: int = DEFAULT_EPOCH_TICKS) -> None:
        self._tick = 0
        self._minutes = 0.0
        self._mode = mode
        self._start_hour = start_hour
        self._epoch_ticks = max(1, int(epoch_ticks))
        self._last_dt = 0.0
 
    # ---- read-only properties ----
    @property
    def tick(self) -> int:
        return self._tick
 
    @property
    def minutes(self) -> float:
        return self._minutes
 
    @property
    def mode(self) -> str:
        return self._mode
 
    @property
    def last_dt(self) -> float:
        return self._last_dt
 
    def current_hour(self) -> float:
        return (self._start_hour + self._minutes / 60.0) % 24.0
 
    # ---- beat advance: the only place tick moves forward ----
    def tick_advance(self, dt_minutes: Optional[float] = None) -> int:
        self._tick += 1
        if self._mode == MODE_SERVER:
            self._last_dt = SERVER_DT_MINUTES
        else:
            self._last_dt = dt_minutes if dt_minutes is not None else 0.0
        self._minutes += self._last_dt
        return self._tick
 
    # ---- narrative fast-forward (sleep/time jumps): consumes no computation beats ----
    def advance_narrative(self, minutes: float) -> None:
        if minutes > 0.0:
            self._minutes += minutes
            self._last_dt = minutes
 
    # ---- mode switching ----
    def set_mode(self, mode: str) -> None:
        if mode in (MODE_DIALOGUE, MODE_SERVER):
            self._mode = mode
 
    # ---- epochs and snapshot points ----
    def epoch_of(self) -> int:
        return self._tick // self._epoch_ticks
 
    def ticks_into_epoch(self) -> int:
        return self._tick % self._epoch_ticks
 
    def epoch_boundary_reached(self) -> bool:
        return self._tick > 0 and self._tick % self._epoch_ticks == 0
 
    # ---- publish engine facts to the board ----
    def publish(self, board: Any) -> None:
        board.publish("sys.tick", self._tick)
        board.publish("sys.dt", self._last_dt)
        board.publish("sys.mode", self._mode)
        board.publish("sys.hour", self.current_hour())   # circadian rhythm (read by K.pns etc.)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"tick": self._tick, "minutes": self._minutes,
                "mode": self._mode, "start_hour": self._start_hour,
                "epoch_ticks": self._epoch_ticks, "last_dt": self._last_dt}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._tick = int(snap.get("tick", 0))
        self._minutes = float(snap.get("minutes", 0.0))
        self._mode = str(snap.get("mode", MODE_DIALOGUE))
        self._start_hour = float(snap.get("start_hour", 8.0))
        self._epoch_ticks = max(1, int(snap.get("epoch_ticks", DEFAULT_EPOCH_TICKS)))
        self._last_dt = float(snap.get("last_dt", 0.0))
 
    def smoke(self) -> bool:
        return (self._tick >= 0 and self._minutes >= 0.0
                and self._mode in (MODE_DIALOGUE, MODE_SERVER))
 
    def invariants(self) -> bool:
        return (self._tick >= 0 and self._minutes >= 0.0
                and self._last_dt >= 0.0 and self._epoch_ticks >= 1)
