# -*- coding: utf-8 -*-
# =============================================================================
# assembly.py — kernel assembly and bootstrapping (V8, skeleton domain, revised)
#
# build the kernel bundle in dependency order, inject it into V8Engine, install DLCs (registry + gears),
# then run the constitutional boot self-check (fail fast: better to fail at boot than to run on a broken skeleton).
#
# revision log:
# - DecisionLog(enabled=...) -> DecisionLog(): the core layer has no enabled parameter;
# the original call must raise TypeError.
# - ConsciousnessStateMachine(log) -> ConsciousnessStateMachine():
# the safety-agency layer constructs with no args; the original call must raise TypeError.
# - _install_dlc used to import the nonexistent builtin_specs / hotplug_specs; switched to
# install_spec + load_hotplug_specs (dlc.py's actual output surface); built-in specs are injected via
# the constructor parameter builtin_specs, hot-plug specs are loaded from the module_dir directory.
# - _install_one now injects spec internal fields (_board/_bus/_services/_data/_kernel):
# install_spec used to read all None; every DLC's ctx was an empty shell.
# - kernel consolidation (legacy non-M modules -> the kernel/ package): _build_kernel dropped
# the lazy imports pointing to nonexistent files (from .persona / .pns / .biomimetic ...),
# keeping only the governance four + card/log/rng; the 13 kernel modules are installed via kernel_specs()
# through the DLC spec surface (before built-in/hot-plug; factories backfill the ctx.k.* kernel ports).
# =============================================================================
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
from .time import MODE_DIALOGUE
from .engine import V8Engine
from .registry import ModuleManifest
from .infrastructure import SeededRNG, DecisionLog
from .dlc import install_spec, load_hotplug_specs
 
 
class KernelBundle:
    """kernel component bundle used by the engine (loose container).
        The kernel keeps legacy components as-is internally; only skeleton scheduling is V8. This bundle is the assembly bridge.    """
 
    __slots__ = ("card", "fuse", "safety", "narrative", "senses", "muscles",
                 "hormones", "sleep", "discharge", "attention", "persona_if",
                 "binder", "emotion_gen", "columnar", "hub", "behavior",
                 "memory", "language",
                 "consciousness", "audit", "trust", "kheshig",
                 "btcs", "odp", "log", "rng")
 
    def __init__(self) -> None:
        self.card = None          # persona card (PersonaConfig)
        self.fuse = None          # content fuse (= safety alias, legacy compatibility)
        self.safety = None        # content safety (backfilled by K.safety)
        self.narrative = None     # narrative safety
        self.senses = None        # PNS senses
        self.muscles = None       # motor execution
        self.hormones = None      # hormone state
        self.sleep = None         # sleep
        self.discharge = None     # discharge pressure
        self.attention = None     # attention
        self.persona_if = None    # cognitive interpretation
        self.binder = None        # scene binding
        self.emotion_gen = None   # emotion generation
        self.columnar = None      # nine-column physiology
        self.hub = None           # behavior hub
        self.behavior = None      # behavior decision
        self.memory = None        # memory
        self.language = None      # language
        self.consciousness = None  # consciousness state machine
        self.audit = None         # audit authority
        self.trust = None         # trust ledger
        self.kheshig = None       # kheshig guard
        self.btcs = None          # behavior tendency
        self.odp = None           # omnidirectional disposition
        self.log = None           # decision log
        self.rng = None           # seeded RNG
 
 
class KernelAssembler:
    """dependency-order assembly + boot self-check."""
 
    __slots__ = ("_card", "_seed", "_mode", "_start_hour",
                 "_builtin_specs", "_module_dir")
 
    def __init__(self, card: Any, seed: int = 42, mode: str = MODE_DIALOGUE,
                 start_hour: float = 8.0,
                 builtin_specs: Optional[List[Dict[str, Any]]] = None,
                 module_dir: Optional[str] = None) -> None:
        """Args:
                    card: persona card (PersonaConfig).
                    seed: master random seed.
                    mode: scene mode (dialogue / server).
                    start_hour: world start hour.        """
        self._card = card
        self._seed = seed
        self._mode = mode
        self._start_hour = start_hour
        self._builtin_specs = list(builtin_specs or ())
        self._module_dir = module_dir
 
    # =====================================================================
    # assembly — full pipeline
    # =====================================================================
    def assemble(self) -> V8Engine:
        log = DecisionLog()              # single decision log (shared)
        rng = SeededRNG(self._seed)      # single master RNG (shared)
        bundle = self._build_kernel(log, rng)          # 1. kernel bundle
        engine = V8Engine(kernel=bundle, mode=self._mode,
                          start_hour=self._start_hour)  # 2. inject
        self._wire_shared(engine, log, rng)            # 3. wire shared components
        self._install_dlc(engine)                      # 4. install DLCs
        self._verify(engine)                           # 5. constitutional boot self-check
        return engine
 
    # =====================================================================
    # kernel bundle — skeleton parts (governance four + card/log/rng)
    # legacy non-M modules are no longer hand-installed here: the 13 kernel modules are mounted
    # via kernel_specs() through the DLC install surface (see _install_dlc); factories backfill ctx.k.* in dependency order.
    # =====================================================================
    def _build_kernel(self, log: DecisionLog, rng: SeededRNG) -> KernelBundle:
        b = KernelBundle()
        b.card = self._card       # persona-card port (kernel factories fetch it via ctx.k.card)
        b.log, b.rng = log, rng
 
        # governance four (skeleton domain; constructor signatures aligned with the safety-agency layer)
        from .consciousness import ConsciousnessStateMachine
        from .trust import TrustLedger
        from .audit import AuditAuthority
        from .kheshig import KheshigGuard
        b.consciousness = ConsciousnessStateMachine()
        b.trust = TrustLedger()
        b.audit = AuditAuthority(log, b.trust)
        b.kheshig = KheshigGuard(log, b.consciousness)
        return b
 
    # =====================================================================
    # wire shared components
    # =====================================================================
    def _wire_shared(self, engine: V8Engine, log: DecisionLog,
                     rng: SeededRNG) -> None:
        engine._log = log
        engine._rng = rng
 
    # =====================================================================
    # DLC install — registry + gears
    # =====================================================================
    def _install_dlc(self, engine: V8Engine) -> None:
        from .kernel import kernel_specs
        # assembly order = dependency order: 13 kernel modules -> built-in DLCs -> hot-plug
        specs = list(kernel_specs())
        specs.extend(self._builtin_specs)
        if self._module_dir:
            specs.extend(load_hotplug_specs(self._module_dir))
        for spec in specs:
            self._install_one(engine, spec)
        # legacy compatibility alias: ctx.k.fuse points to the content-safety module
        if engine.kernel.safety is not None:
            engine.kernel.fuse = engine.kernel.safety
        # narrative snapshot-preservation wiring: bus event -> engine snapshot sovereignty (modules never call the engine directly)
        # post-denial recovery is done by the scene side between ticks via restore() (in-tick rollback violates tick sovereignty)
        if engine.kernel.narrative is not None:
            narrative = engine.kernel.narrative
            engine.bus.subscribe(
                "narrative.snapshot_request",
                lambda item: narrative.save_snapshot(engine.snapshot()),
                owner="assembly", priority=0)
 
    def _install_one(self, engine: V8Engine, spec: Dict[str, Any]) -> None:
        """install a single spec: inject internal fields -> install_spec -> registry -> gears."""
        # inject the engine surface required by install_spec (without these, every DLC's ctx is an empty shell)
        spec["_board"] = engine.board
        spec["_bus"] = engine.bus
        spec["_services"] = engine.services
        spec["_data"] = None          # this tick's data is passed into hooks by the engine at runtime
        spec["_kernel"] = engine.kernel
 
        try:
            manifest = install_spec(spec, engine._log, self._seed, self._card)
        except (ValueError, TypeError) as exc:
            engine._log.record(0, "assembly", "install_rejected", str(exc))
            return
        if manifest.module_id in ("", "?"):
            return
        engine.registry.register(manifest)
 
        gear = spec.get("gear") or {}
        engine.gears.register_module(
            manifest.module_id, gear, manifest.priorities, manifest.hooks)
 
    # =====================================================================
    # boot self-check — constitutional fail-fast
    # =====================================================================
    def _verify(self, engine: V8Engine) -> None:
        if not engine.smoke():
            raise RuntimeError("V8 engine smoke failed at assembly")
        if not engine.invariants():
            raise RuntimeError("V8 engine invariants violated at assembly")
        dangling = engine.dangling_contracts()
        if dangling:
            engine._log.record(0, "assembly", "dangling_contracts",
                               f"{len(dangling)} contracts pending providers")
 
    # =====================================================================
    # snapshot/restore helpers
    # =====================================================================
    def snapshot(self, engine: V8Engine) -> Dict[str, Any]:
        return engine.snapshot()
 
    def restore(self, engine: V8Engine, snap: Dict[str, Any]) -> bool:
        try:
            engine.restore(snap)
            return True
        except Exception:
            return False
