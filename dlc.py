# -*- coding: utf-8 -*-
# =============================================================================
# dlc.py — DLC installation spec, kernel/engine ports, hot-plug (V8 revised)
#
# revision log (aligned with how legacy modules actually call):
# - ctx gained the .k attribute alias -> kernel. All legacy DLC factories access kernel ports via ctx.k.card /
# ctx.k.xxx; the original _EngineContext had only .kernel, so every DLC would crash.
# - install_spec's rng_for closure was lambda s, name: ... (two args), while legacy
# modules uniformly call ctx.rng_for("m1") with one arg — signature mismatch, factories would crash. Changed to single-arg.
# - provided the install_one convenience entry besides load_hotplug_specs; spec internal fields
# (_board/_bus/_services/_data/_kernel) are injected by assembly; documentation added.
# =============================================================================
from __future__ import annotations
from typing import Any, Callable, Dict, List, Set, Tuple
 
from .engine_contracts import ENGINE_CONTRACTS
from .registry import ModuleManifest, PhaseHook
 
 
# =============================================================================
# 1. port whitelist — the surface a module may touch (kept consistent with legacy)
# =============================================================================
class KernelPorts:
    _ALLOWED: Set[str] = {
        "card", "btcs", "odp", "hormones", "sleep", "discharge", "columnar",
        "attention", "hub", "memory", "language", "persona_if", "muscles",
        "senses", "log",
    }
 
 
class EnginePorts:
    _ALLOWED: Set[str] = {
        "board", "bus", "services", "log", "data", "rng_for", "kernel",
    }
 
 
# =============================================================================
# 2. context builder — assemble the ctx passed to factories
# =============================================================================
class _EngineContext:
    """runtime context passed to module factories. k is the alias for kernel (legacy compatibility surface)."""
 
    __slots__ = ("board", "bus", "services", "log", "data", "rng_for", "kernel")
 
    def __init__(self, board: Any, bus: Any, services: Any, log: Any,
                 data: Any, rng_for: Callable[[str], Any], kernel: Any) -> None:
        self.board = board
        self.bus = bus
        self.services = services
        self.log = log
        self.data = data
        self.rng_for = rng_for
        self.kernel = kernel
 
    @property
    def k(self) -> Any:
        """legacy compatibility: modules access kernel ports via ctx.k.card / ctx.k.hub."""
        return self.kernel
 
 
def make_engine_ctx(board: Any, bus: Any, services: Any, log: Any,
                    data: Any, rng_for: Callable[[str], Any],
                    kernel: Any) -> _EngineContext:
    return _EngineContext(board, bus, services, log, data, rng_for, kernel)
 
 
# =============================================================================
# 3. contract validation — install-time soft check (unknown keys only warn, never reject)
# =============================================================================
def validate_contract_keys(contract_keys: Tuple[str, ...]) -> List[str]:
    warnings: List[str] = []
    for key in contract_keys:
        if not isinstance(key, str):
            warnings.append(f"contract key not a str: {key!r}")
        elif key not in ENGINE_CONTRACTS:
            warnings.append(f"undeclared contract key: {key}")
    return warnings
 
 
# =============================================================================
# 4. installation spec — spec dict -> module manifest
# =============================================================================
def install_spec(spec: Dict[str, Any], log: Any, seed: int,
                 card: Any) -> ModuleManifest:
    """install one module from a dlc_spec() dict.
        spec internal fields (injected by assembly): _board / _bus / _services / _data / _kernel.
        Returns: the bound manifest (dormant when hard dependencies are unmet).    """
    module_id = str(spec.get("module_id", ""))
    if not module_id:
        raise ValueError("dlc_spec must declare module_id")
    factory = spec.get("factory")
    if not callable(factory):
        raise ValueError(f"{module_id}: factory must be callable")
 
    raw_keys = spec.get("contract_keys") or ()
    contract_keys = tuple(raw_keys) if isinstance(raw_keys, (tuple, list)) else ()
    for warn in validate_contract_keys(contract_keys):
        log.record(0, "dlc.install", "contract_warning", f"{module_id}: {warn}")
 
    manifest = ModuleManifest(spec)
    manifest.contract_keys = contract_keys
 
    # hard dependency check: unmet -> dormant (no hooks, no instance, not dispatched)
    requires = manifest.requires
    hard = requires.get("hard") if isinstance(requires, dict) else None
    if hard:
        missing = [k for k in hard if hard.get(k) is None]
        if missing:
            manifest.hooks.clear()
            log.record(0, "dlc.install", "dormant",
                       f"{module_id}: hard requirement unmet {missing}")
            return manifest
 
    ctx = make_engine_ctx(
        board=spec.get("_board"),
        bus=spec.get("_bus"),
        services=spec.get("_services"),
        log=log,
        data=spec.get("_data"),
        # ABMI 1.0 heavy-test revision: stream cache is now isolated PER INSTALLATION — the old global
        # lru_cache let multiple engines in one process (dual-subject Stage/replay tests) share cursors and trample each other;
        # same-name calls within one installation still continue the cursor (legacy-compatible semantics unchanged).
        rng_for=lambda name, _s={}: _s.setdefault(name, _derive_rng(seed, name)),
        kernel=spec.get("_kernel"))
 
    try:
        instance = factory(ctx)
    except Exception:
        log.record(0, "dlc.install", "factory_error", f"{module_id}: {_exc_name()}")
        return manifest
 
    hooks: Dict[str, PhaseHook] = {}
    bind_fn = spec.get("bind")
    if callable(bind_fn):
        try:
            bound = bind_fn(instance, ctx)
            if isinstance(bound, dict):
                hooks.update(bound)
        except Exception:
            log.record(0, "dlc.install", "bind_error", f"{module_id}: {_exc_name()}")
 
    audit = spec.get("audit_probe")
    if callable(audit):
        try:
            manifest.audit_probe = audit(instance)
        except Exception:
            manifest.audit_probe = None
 
    manifest.instance = instance
    manifest.hooks.update(hooks)
    return manifest
 
 
def _derive_rng(master_seed: int, stream_name: str) -> Any:
    from .infrastructure import DerivedRNGStream
    return DerivedRNGStream(master_seed, stream_name)      # new stream (bypasses the global cache)
 
 
def _exc_name() -> str:
    import sys
    exc = sys.exc_info()[1]
    return type(exc).__name__ if exc is not None else "Unknown"
 
 
# =============================================================================
# 5. hot-plug — load specs from the modules/ directory (constitution: hot-pluggable module directory, zero engine changes)
# =============================================================================
def load_hotplug_specs(module_path: str) -> List[Dict[str, Any]]:
    """import dlc_spec() from every module file in a directory; bad files are skipped without crashing hot-plug."""
    import importlib.util
    import os
    import sys
    specs: List[Dict[str, Any]] = []
    if not os.path.isdir(module_path):
        return specs
    for fname in sorted(os.listdir(module_path)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        path = os.path.join(module_path, fname)
        mod_name = f"abmi_dlc_{fname[:-3]}"
        try:
            spec_mod = importlib.util.spec_from_file_location(mod_name, path)
            module = importlib.util.module_from_spec(spec_mod)
            sys.modules[mod_name] = module
            spec_mod.loader.exec_module(module)
            dlc = getattr(module, "dlc_spec", None)
            if callable(dlc):
                specs.append(dlc())
        except Exception:
            continue
    return specs
