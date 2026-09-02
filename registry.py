# -*- coding: utf-8 -*-
# =============================================================================
# registry.py — contract-aware module registry and manifests (V8 revised)
#
# the registry handles installation, phase dispatch, zone grouping, and contract indexing (who provides which sys.* key).
# phase pre-indexing: phase -> hooks arrays built at registration; run_phase no longer scans all modules every tick.
#
# revision log: logic unchanged, comments only trimmed; all legacy indexing and defensive semantics kept.
# =============================================================================
from __future__ import annotations
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
 
PhaseHook = Callable[[int, Any], None]  # unified phase-hook signature: hook(tick, data) -> None
 
 
class ModuleManifest:
    """metadata and bound hooks of an installed module (produced from the dlc_spec() dict)."""
 
    __slots__ = (
        "module_id", "version", "zone", "commit_priority", "priorities",
        "hooks", "provides", "requires", "report_key", "snapshot_label",
        "audit_probe", "card_schema", "card_manifest", "card_order",
        "instance", "always_on", "serial", "coma_allowed", "vital",
        "built_in", "trigger_declared", "contract_keys",
    )
 
    def __init__(self, spec: Dict[str, Any]) -> None:
        self.module_id = str(spec.get("module_id", "?"))
        self.version = str(spec.get("version", "0"))
        self.zone = str(spec.get("zone", "main"))
        self.commit_priority = int(spec.get("commit_priority", 0))
        self.priorities: Dict[str, int] = dict(spec.get("priorities") or {})
        self.hooks: Dict[str, PhaseHook] = {}
        self.provides: Tuple[str, ...] = tuple(spec.get("provides") or ())
        self.requires: Dict[str, Any] = dict(spec.get("requires") or {})
        self.report_key = spec.get("report_key")
        self.snapshot_label = spec.get("snapshot_label")
        self.audit_probe = spec.get("audit_probe")
        self.card_schema = spec.get("card_schema")
        self.card_manifest = spec.get("card_manifest")
        self.card_order = int(spec.get("card_order", 100))
        self.instance: Optional[Any] = None
        self.always_on = bool(spec.get("always_on", False))
        self.serial = bool(spec.get("serial", False))
        self.coma_allowed = bool(spec.get("coma_allowed", False))
        self.vital = bool(spec.get("vital", False))
        self.built_in = bool(spec.get("built_in", False))
        self.trigger_declared = spec.get("trigger_declared")
        self.contract_keys: Tuple[str, ...] = tuple(spec.get("contract_keys") or ())
 
    def priority_of(self, phase: str) -> int:
        return self.priorities.get(phase, self.commit_priority)
 
    def call_hook(self, phase: str, tick: int, data: Any) -> None:
        hook = self.hooks.get(phase)
        if hook is not None:
            hook(tick, data)
 
 
class ModuleRegistry:
    """registry with phase pre-indexing and contract lookup."""
 
    __slots__ = ("_manifests", "_phase_index", "_zone_index",
                 "_contract_index", "_lock")
 
    def __init__(self) -> None:
        self._manifests: Dict[str, ModuleManifest] = {}
        self._phase_index: Dict[str, List[Tuple[int, str, ModuleManifest]]] = {}
        self._zone_index: Dict[str, List[str]] = {}
        self._contract_index: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
 
    # ---- registration and binding ----
    def register(self, manifest: ModuleManifest) -> bool:
        with self._lock:
            if manifest.module_id in self._manifests:
                return False
            self._manifests[manifest.module_id] = manifest
            self._rebuild_indices()
            return True
 
    def bind_instance(self, module_id: str, instance: Any,
                      hooks: Optional[Dict[str, PhaseHook]] = None) -> bool:
        with self._lock:
            manifest = self._manifests.get(module_id)
            if manifest is None:
                return False
            manifest.instance = instance
            if hooks is not None:
                manifest.hooks.update(hooks)
            self._rebuild_indices()
            return True
 
    # ---- dispatch ----
    def hook_list(self, phase: str) -> List[ModuleManifest]:
        with self._lock:
            return [m for _, _, m in self._phase_index.get(phase, ())]
 
    def run_phase(self, phase: str, tick: int, data: Any) -> int:
        """execute all hooks of a phase in priority order (defensive: a single hook exception does not crash the phase)."""
        with self._lock:
            entries = list(self._phase_index.get(phase, ()))
        executed = 0
        for _, _, manifest in entries:
            hook = manifest.hooks.get(phase)
            if hook is None:
                continue
            try:
                hook(tick, data)
                executed += 1
            except Exception:
                continue
        return executed
 
    # ---- queries ----
    def all(self) -> List[ModuleManifest]:
        with self._lock:
            return list(self._manifests.values())
 
    def instance(self, module_id: str) -> Optional[Any]:
        with self._lock:
            m = self._manifests.get(module_id)
            return m.instance if m else None
 
    def manifest_of(self, module_id: str) -> Optional[ModuleManifest]:
        with self._lock:
            return self._manifests.get(module_id)
 
    def zone_members(self, zone: str) -> List[str]:
        with self._lock:
            return list(self._zone_index.get(zone, ()))
 
    def providers_of(self, contract_key: str) -> List[str]:
        with self._lock:
            return list(self._contract_index.get(contract_key, ()))
 
    # ---- unload and rebuild ----
    def purge(self, module_id: str) -> bool:
        with self._lock:
            if module_id not in self._manifests:
                return False
            del self._manifests[module_id]
            self._rebuild_indices()
            return True
 
    def _rebuild_indices(self) -> None:
        self._phase_index.clear()
        self._zone_index.clear()
        self._contract_index.clear()
        for mid, manifest in self._manifests.items():
            for phase in manifest.hooks:
                bucket = self._phase_index.setdefault(phase, [])
                bucket.append((manifest.priority_of(phase), mid, manifest))
            self._zone_index.setdefault(manifest.zone, []).append(mid)
            for key in manifest.contract_keys:
                self._contract_index.setdefault(key, []).append(mid)
        for bucket in self._phase_index.values():
            bucket.sort(key=lambda e: e[0])
