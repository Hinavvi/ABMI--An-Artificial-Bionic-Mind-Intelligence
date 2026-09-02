# -*- coding: utf-8 -*-
# =============================================================================
# blackboard.py — three-namespace shared state + event bus + service ports (V8 revised)
#
# namespaces: module-id.* (module-private data) / knob.* (knobs, arbitrated) / sys.* (engine-published).
#
# revision log:
# - removed the duplicate definition of publish (the file defined it twice; the mirror-less version was silently overridden by the mirrored one).
# - batch_publish now applies the contract mirror, consistent with publish semantics.
# - added restore_all / smoke / invariants: engine.restore used to call
# the nonexistent board.restore_all (restore chain broken); the four-piece set completed per constitutional rule 6.
# - doc fix: the implementation is a flat dict, not a "layered key tree".
# =============================================================================
from __future__ import annotations
import threading
from typing import Any, Callable, Dict, List, Tuple
 
from .engine_contracts import CONTRACT_MIRROR
 
 
class Blackboard:
    """flat key-value storage + knob arbitration + prefix operations. RLock thread-safe (reads in parallel zones, writes in commit zones)."""
 
    __slots__ = ("_data", "_knob", "_knob_owner", "_lock")
 
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._knob: Dict[str, Any] = {}
        self._knob_owner: Dict[str, Tuple[str, int]] = {}
        self._lock = threading.RLock()
 
    # ------------------------------------------------------------------
    # publish / read — module-id.* and sys.* namespaces
    # ------------------------------------------------------------------
    def publish(self, key: str, value: Any) -> None:
        """publish one key-value; legacy module keys are auto-mirrored to sys.* via CONTRACT_MIRROR."""
        with self._lock:
            if key.startswith("knob."):
                raise ValueError(f"knob key must use write_knob: {key}")
            self._data[key] = value
            mirror = CONTRACT_MIRROR.get(key)
            if mirror is not None:
                self._data[mirror] = value
 
    def batch_publish(self, mapping: Dict[str, Any]) -> None:
        """batch publish (single lock); mirror semantics consistent with publish."""
        with self._lock:
            for key, value in mapping.items():
                if key.startswith("knob."):
                    raise ValueError(f"knob key must use write_knob: {key}")
                self._data[key] = value
                mirror = CONTRACT_MIRROR.get(key)
                if mirror is not None:
                    self._data[mirror] = value
 
    def read(self, key: str, default: Any = None) -> Any:
        """soft read: missing returns the default (lazy, never pre-built)."""
        with self._lock:
            return self._data.get(key, default)
 
    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data
 
    # ------------------------------------------------------------------
    # knob.* namespace (arbitrated: higher priority wins; ties go first-come-first-served)
    # ------------------------------------------------------------------
    def write_knob(self, key: str, value: Any, owner: str,
                   priority: int = 0) -> bool:
        with self._lock:
            if not key.startswith("knob."):
                raise ValueError(f"knob keys must start with 'knob.': {key}")
            existing = self._knob_owner.get(key)
            if existing is not None and existing[1] > priority:
                return False
            self._knob[key] = value
            self._knob_owner[key] = (owner, priority)
            return True
 
    def read_knob(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._knob.get(key, default)
 
    # ------------------------------------------------------------------
    # prefix operations and cleanup (for rebirth / unload / snapshot)
    # ------------------------------------------------------------------
    def keys_with_prefix(self, prefix: str) -> List[str]:
        with self._lock:
            return [k for k in self._data if k.startswith(prefix)]
 
    def all_keys(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())
 
    def purge_module(self, module_id: str) -> int:
        prefix = f"{module_id}."
        with self._lock:
            victims = [k for k in self._data if k.startswith(prefix)]
            for k in victims:
                del self._data[k]
            return len(victims)
 
    # ------------------------------------------------------------------
    # four-piece set (constitutional rule 6)
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"data": dict(self._data), "knobs": dict(self._knob)}
 
    def restore_all(self, snap: Dict[str, Any]) -> None:
        """snapshot restore: wholesale replacement of the main table and knob table (called by engine.restore)."""
        if not isinstance(snap, dict):
            return
        data = snap.get("data", snap)  # compatible with plain data snapshots
        knobs = snap.get("knobs", {})
        with self._lock:
            if isinstance(data, dict):
                self._data = dict(data)
            if isinstance(knobs, dict):
                self._knob = dict(knobs)
 
    def smoke(self) -> bool:
        return isinstance(self._data, dict) and isinstance(self._knob, dict)
 
    def invariants(self) -> bool:
        return not any(k.startswith("knob.") for k in self._data)
 
 
# =============================================================================
# EventBus — phase-end dispatch + cross-tick mailbox (legacy semantics kept)
# =============================================================================
class EventBus:
    """emit(next_tick=False) enqueues for pending dispatch (handled by dispatch_pending at phase end);
        emit(next_tick=True) enqueues into the cross-tick mailbox (handled by next_tick()).    """
 
    __slots__ = ("_subs", "_pending", "_mailbox", "_lock")
 
    def __init__(self) -> None:
        self._subs: Dict[str, List[Tuple[int, str, Callable[[Any], None]]]] = {}
        self._pending: List[Tuple[str, Dict[str, Any]]] = []
        self._mailbox: List[Tuple[str, Dict[str, Any]]] = []
        self._lock = threading.RLock()
 
    def subscribe(self, event: str, handler: Callable[[Any], None],
                  owner: str, priority: int = 0) -> None:
        with self._lock:
            bucket = self._subs.setdefault(event, [])
            bucket.append((priority, owner, handler))
            bucket.sort(key=lambda x: x[0])
 
    def emit(self, event: str, payload: Dict[str, Any],
             source: str, next_tick: bool = False) -> None:
        item = (event, {"source": source, "payload": payload})
        with self._lock:
            (self._mailbox if next_tick else self._pending).append(item)
 
    def dispatch_pending(self) -> int:
        """phase-end dispatch; a single handler exception does not affect the others."""
        with self._lock:
            batch, self._pending = self._pending, []
        dispatched = 0
        for event, item in batch:
            for _, _, handler in self._subs.get(event, ()):
                try:
                    handler(item)
                    dispatched += 1
                except Exception:
                    continue
        return dispatched
 
    def next_tick(self) -> int:
        """cross-tick handoff: mailbox events merged into pending dispatch (handled at this beat's end)."""
        with self._lock:
            batch, self._mailbox = self._mailbox, []
            self._pending.extend(batch)
            return len(batch)
 
    # ---- four-piece-set addendum (ABMI 1.0 heavy-test revision: in-flight events must be saved with the snapshot) ----
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"pending": list(self._pending),
                    "mailbox": list(self._mailbox)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        with self._lock:
            self._pending = list(snap.get("pending") or [])
            self._mailbox = list(snap.get("mailbox") or [])
 
 
# =============================================================================
# ServicePorts — name -> callable capability registry (capabilities, not modules)
# =============================================================================
class ServicePorts:
    __slots__ = ("_services", "_lock")
 
    def __init__(self) -> None:
        self._services: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.RLock()
 
    def offer(self, name: str, fn: Callable[..., Any]) -> None:
        with self._lock:
            self._services[name] = fn
 
    def call(self, name: str, *args: Any, default: Any = None, **kwargs: Any) -> Any:
        with self._lock:
            fn = self._services.get(name)
        if fn is None:
            return default
        return fn(*args, **kwargs)
 
    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._services
