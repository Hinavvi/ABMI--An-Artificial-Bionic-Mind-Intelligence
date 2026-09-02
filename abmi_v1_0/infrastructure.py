# -*- coding: utf-8 -*-
# =============================================================================
# infrastructure.py — determinism foundation: random streams and decision log (V8 revised)
#
# three pillars: SeededRNG (same seed, same sequence) / DerivedRNGStream (module-private stream derived from the master seed,
# lru_cache cached) / DecisionLog (typed + capacity-capped + thread-safe).
#
# revision log:
# - DecisionLog constructor signature fixed to (cap=50000); the original assembly called with the enabled= keyword
# which raises TypeError — fixed on the assembly side (enabled parameter removed, see assembly.py).
# - rng_for's lru_cache returns the same stream instance: same-named streams across modules share the cursor; documented.
# =============================================================================
from __future__ import annotations
import hashlib
import random
import threading
from functools import lru_cache
from typing import Any, Dict, List, TypedDict
 
 
class SeededRNG:
    """deterministic RNG with a cursor (position supports audit verification of skipped draws)."""
 
    __slots__ = ("_rng", "_position")
 
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._position = 0
 
    @property
    def position(self) -> int:
        return self._position
 
    def random(self) -> float:
        self._position += 1
        return self._rng.random()
 
    def uniform(self, a: float, b: float) -> float:
        self._position += 1
        return self._rng.uniform(a, b)
 
    def randint(self, a: int, b: int) -> int:
        self._position += 1
        return self._rng.randint(a, b)
 
    def choice(self, seq: List[Any]) -> Any:
        self._position += 1
        return self._rng.choice(seq)
 
    def shuffle_in_place(self, seq: List[Any]) -> None:
        self._position += 1
        self._rng.shuffle(seq)
 
    def sample(self, seq: List[Any], k: int) -> List[Any]:
        self._position += 1
        return self._rng.sample(seq, k)
 
 
class DerivedRNGStream:
    """module-private random stream derived from the master seed (same master seed + same stream name -> same sequence)."""
 
    __slots__ = ("_rng", "_stream_name", "_position")
 
    def __init__(self, master_seed: int, stream_name: str) -> None:
        # ABMI 1.0 heavy-test revision: hash() is salted per process and not reproducible across processes;
        # switched to sha256 stable derivation (same master seed + same stream name -> same sequence across processes)
        digest = hashlib.sha256(stream_name.encode("utf-8")).digest()
        derived_seed = (int.from_bytes(digest[:4], "big") ^ master_seed) & 0xFFFFFFFF
        self._rng = random.Random(derived_seed)
        self._stream_name = stream_name
        self._position = 0
 
    # ---- four-piece-set addendum (stream cursors saved with the snapshot; time travel is replayable) ----
    def snapshot(self) -> Dict[str, Any]:
        return {"position": self._position, "state": self._rng.getstate()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict) or "state" not in snap:
            return
        self._rng.setstate(snap["state"])
        self._position = int(snap.get("position", 0))
 
    @property
    def position(self) -> int:
        return self._position
 
    def random(self) -> float:
        self._position += 1
        return self._rng.random()
 
    def uniform(self, a: float, b: float) -> float:
        self._position += 1
        return self._rng.uniform(a, b)
 
    def choice(self, seq: List[Any]) -> Any:
        self._position += 1
        return self._rng.choice(seq)
 
    def shuffle_in_place(self, seq: List[Any]) -> None:
        self._position += 1
        self._rng.shuffle(seq)
 
    def sample(self, seq: List[Any], k: int) -> List[Any]:
        self._position += 1
        return self._rng.sample(seq, k)
 
 
@lru_cache(maxsize=256)
def _make_stream(master_seed: int, stream_name: str) -> DerivedRNGStream:
    return DerivedRNGStream(master_seed, stream_name)
 
 
def rng_for(master_seed: int, stream_name: str) -> DerivedRNGStream:
    """cached stream factory: same (master_seed, stream_name) returns the same stream instance.
        Note: same-named streams share cursor and sequence position — stream names must be unique across modules (convention: use module_id).    """
    return _make_stream(master_seed, stream_name)
 
 
class LogEntry(TypedDict):
    tick: int
    module: str
    event: str
    payload: Any
    rng_position: int
 
 
class DecisionLog:
    """append-only decision log: tick-indexed + hard capacity cap + write lock (thread-safe in parallel zones)."""
 
    __slots__ = ("_lock", "_entries", "_by_tick", "_cap", "_dropped")
 
    def __init__(self, cap: int = 50000) -> None:
        self._lock = threading.Lock()
        self._entries: List[LogEntry] = []
        self._by_tick: Dict[int, List[LogEntry]] = {}
        self._cap = cap
        self._dropped = 0
 
    @property
    def entries(self) -> List[LogEntry]:
        return self._entries
 
    @property
    def by_tick(self) -> Dict[int, List[LogEntry]]:
        return self._by_tick
 
    @property
    def dropped(self) -> int:
        return self._dropped
 
    def record(self, tick: int, module: str, event: str,
               payload: Any = None, rng_position: int = -1) -> None:
        entry: LogEntry = {
            "tick": tick, "module": module, "event": event,
            "payload": payload, "rng_position": rng_position,
        }
        with self._lock:
            if len(self._entries) >= self._cap:
                self._entries.pop(0)
                self._dropped += 1
            self._entries.append(entry)
            self._by_tick.setdefault(tick, []).append(entry)
 
    def entries_of(self, tick: int) -> List[LogEntry]:
        with self._lock:
            return list(self._by_tick.get(tick, []))
 
    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._by_tick.clear()
            self._dropped = 0
