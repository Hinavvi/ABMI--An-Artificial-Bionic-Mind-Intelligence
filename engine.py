# -*- coding: utf-8 -*-
# =============================================================================
# engine.py — V8 skeleton main loop (constitution, chapters 2 & 5, revised)
#
# the engine does only six things: scheduling (gears P0..P8) / communication (blackboard, bus, service ports) /
# governance (audit, trust, siege, consciousness) / contracts (reads sys.* only, never names a module) /
# time (TimeKeeper exclusively) / snapshot-restore (four-piece set).
#
# revision log:
# - fixed self.kheshig -> self.kernel.kheshig (the siege branch would raise AttributeError as-is).
# - removed duplicate dispatch of P1_body / P2_boundary (they ran twice; hook side effects doubled).
# - __slots__ gained "_log" / "_rng" (the original _wire_shared assignment raised AttributeError).
# - wired the event bus: next_tick() at beat start, dispatch_pending() at each phase end
# (legacy mailbox semantics; the original skeleton bus never delivered at all).
# - governance audit made real: uploaded is now read from the board's provides keys (arrival surface),
# compared against audit_probe's local settlement; the original uploaded/probe came from the same source, so audit always passed.
# - removed double deweighting: trust.reject's single entry is AuditAuthority.
# - mode consolidated into TimeKeeper (removed the engine-side duplicate self.mode).
# =============================================================================
from __future__ import annotations
import copy
from typing import Any, Dict, List, Optional
 
from .time import TimeKeeper, MODE_DIALOGUE
from .gear import GearScheduler
from .engine_contracts import read_contract, missing_contracts, validate_contracts
from .registry import ModuleRegistry
from .blackboard import Blackboard, EventBus, ServicePorts
 
 
class V8Engine:
    """V8 skeleton engine: P0..P8 gear-driven main loop, dual clocks, read-only contracts, four-piece-set snapshot/restore.
        Kernel components (physiology/attention/emotion/governance-four etc.) are injected via KernelBundle.    """
 
    __slots__ = ("time", "gears", "registry", "board", "bus", "services",
                 "kernel", "_phase_order", "_log", "_rng")
 
    def __init__(self, kernel: Any, mode: str = MODE_DIALOGUE,
                 start_hour: float = 8.0) -> None:
        self.time = TimeKeeper(start_hour=start_hour, mode=mode)
        self.gears = GearScheduler()
        self.registry = ModuleRegistry()
        self.board = Blackboard()
        self.bus = EventBus()
        self.services = ServicePorts()
        self.kernel = kernel
        self._phase_order = (
            "P0_input", "P1_body", "P2_boundary",
            "P3_cognition", "P4_decision",
            "P5_deposit", "P6_maintenance",
            "P7_archive", "P8_readout",
        )
        self._log = None   # injected by assembly._wire_shared
        self._rng = None
 
    @property
    def mode(self) -> str:
        return self.time.mode
 
    # =====================================================================
    # main loop — one computation beat
    # =====================================================================
    def execute_computation_cycle(self, user_input: Optional[str] = None,
                                  stimuli: Optional[List[Any]] = None,
                                  dt_minutes: Optional[float] = None) -> Dict[str, Any]:
        # ---- time sovereignty: advance the tick (the only place, constitutional rule 5) ----
        tick = self.time.tick_advance(dt_minutes)
        self.time.publish(self.board)
        self.bus.next_tick()  # cross-tick mailbox handoff (legacy mailbox semantics)
 
        data: Dict[str, Any] = {
            "user_input": user_input,
            "stimuli": list(stimuli or ()),
            "dt": self.time.last_dt,
            "tick": tick,
            "mode": self.mode,
        }
        result: Dict[str, Any] = {"tick": tick, "blocked": False}
 
        # ---- siege branch: consciousness powered down; only body phase + maintenance phase (black-box semantics) ----
        if self.kernel.kheshig.siege.active:
            return self._siege_beat(tick, data, result)
 
        # ---- P0 input: content fuse / narrative safety / text encoding ----
        self._run_phase("P0_input", tick, data)
        if data.get("blocked"):
            result.update(blocked=True,
                          response=data.get("safe_response", "(Blocked.)"))
            self._readout(tick, result)
            return result
 
        # ---- P1 body: PNS senses / physiology / hormones / alcohol ----
        self._run_phase("P1_body", tick, data)
 
        # ---- governance orchestration: audit / trust rebound / consciousness resolution / siege judgment ----
        self._governance(tick, data)
 
        # ---- P2 boundary: audit / trigger_eval / interception ----
        self._run_phase("P2_boundary", tick, data)
        # ---- P3 cognition: nine columns / attention / emotion ----
        self._run_phase("P3_cognition", tick, data)
        # ---- P4 decision: scene finalization / behavior goals / strategy ----
        self._run_phase("P4_decision", tick, data)
        # ---- P5 deposit: memory serialization ----
        self._run_phase("P5_deposit", tick, data)
        # ---- P6 maintenance: metabolism / sleep / rumination / sealing ----
        self._run_phase("P6_maintenance", tick, data)
        # ---- P7 archive: epoch-boundary snapshot ----
        if self.time.epoch_boundary_reached():
            self._run_phase("P7_archive", tick, data)
        # ---- P8 wrap-up ----
        self._readout(tick, result)
        return result
 
    # =====================================================================
    # phase dispatch — gear double-gate + phase-end event delivery
    # =====================================================================
    def _run_phase(self, phase: str, tick: int, data: Any) -> Dict[str, int]:
        stats = self.gears.run_phase(phase, tick, data)
        self.bus.dispatch_pending()  # phase-end delivery (legacy semantics)
        return stats
 
    def _siege_beat(self, tick: int, data: Any,
                    result: Dict[str, Any]) -> Dict[str, Any]:
        """siege coma beat: only P1 body + P6 maintenance; coma timing; lift detected via the scout."""
        self.kernel.consciousness.tick_gap(tick)
        body = self._run_phase("P1_body", tick, data)
        lifted = self.kernel.kheshig.update_during_coma(
            tick, trigger_active=body["ran"] > 0)
        self._run_phase("P6_maintenance", tick, data)
        self._readout(tick, result)
        result.update(coma=True, lifted=lifted,
                      response="(Awakening.)" if lifted else "(Coma.)")
        return result
 
    # =====================================================================
    # governance orchestration — engine-level explicit logic (constitution, governance)
    # =====================================================================
    def _governance(self, tick: int, data: Any) -> None:
        k = self.kernel
 
        # 1. audit loop: local settlement (audit_probe) vs board arrival surface (provides keys)
        for m in self.registry.all():
            if m.audit_probe is None:
                continue
            try:
                probe = m.audit_probe()
            except Exception:
                continue
            if not isinstance(probe, dict) or not probe:
                continue  # no probe / signal-list probe: skip (legacy DLCs return [])
            uploaded = {key: self.board.read(key) for key in m.provides}
            verdict = k.audit.audit_at_egress(tick, m.module_id, uploaded, probe)
            if verdict.passed:
                k.trust.mark_clean(m.module_id)
            else:
                # deweight already triggered by AuditAuthority; trust below threshold -> scout watches
                if k.kheshig.should_scout(k.trust.weight(m.module_id)):
                    k.kheshig.scout(tick, m.module_id, [])
 
        # 2. trust rebound (gradual recovery after 20 consecutive clean ticks)
        for mid in list(k.trust.clean_counts()):
            k.trust.rebound(tick, mid)
 
        # 3. consciousness resolution (L7 resolved only outside siege)
        if k.consciousness.state != "coma":
            if self.read("sys.unconsciousness", False):
                k.consciousness.enter(tick, "l7", "alcohol hard power-cut")
            elif k.consciousness.state == "l7":
                k.consciousness.exit(tick, "awake", "below L7")
 
        # 4. siege judgment (all via contract keys, never touching the kernel by name)
        if not k.kheshig.siege.active:
            should, why = k.kheshig.siege_predicate({
                "idns_active": self.read("sys.idns_active", False),
                "idns_anti_survival": data.get("idns_anti_survival", False),
                "t_core": self.read("sys.thermal_t_core", 36.8),
                "cidx": self.read("sys.cognitive_index", 0.0),
                "pain": self.read("sys.pain", 0.0),
            })
            if should:
                k.kheshig.besiege(tick, why)
 
    # =====================================================================
    # wrap-up — P8: package module reports (generic mechanism, no module names)
    # =====================================================================
    def _readout(self, tick: int, result: Dict[str, Any]) -> None:
        for m in self.registry.all():
            if m.report_key and "report" in m.hooks:
                try:
                    result[m.report_key] = m.hooks["report"]()
                except Exception:
                    pass  # a single report exception does not crash the wrap-up
 
    # =====================================================================
    # contract hygiene — constitutional rule 24
    # =====================================================================
    def check_contracts(self) -> Dict[str, str]:
        return validate_contracts(self.board)
 
    def dangling_contracts(self) -> List[str]:
        return missing_contracts(self.board)
 
    def read(self, key: str, default: Any = None) -> Any:
        """contract strongly-typed read: declared default wins; undeclared keys fall back to the caller's default.
                Revision: the original passed default as read_contract's cast positional argument;
                non-callable raised a swallowed TypeError, so contract reads always fell back to defaults        """
        value = read_contract(self.board, key)
        return default if value is None else value
 
    # =====================================================================
    # four-piece set
    # =====================================================================
    def snapshot(self) -> Dict[str, Any]:
        # heavy-test revision: aggregate the four-piece-set snapshots of all installed modules (snapshot_label finally consumed),
        # otherwise restore only rewinds clock/gears/board while module internals keep moving -> time-travel divergence.
        modules: Dict[str, Any] = {}
        for m in self.registry.all():
            inst = getattr(m, "instance", None)
            if inst is None or not hasattr(inst, "snapshot"):
                continue
            label = m.snapshot_label or m.module_id
            try:
                modules[label] = inst.snapshot()
            except Exception:
                pass  # a single module's snapshot exception does not crash the whole snapshot
        # the governance four (consciousness/trust/audit/kheshig) are stateful too; missing any means time-travel divergence
        gov: Dict[str, Any] = {}
        for name in ("consciousness", "trust", "audit", "kheshig"):
            comp = getattr(self.kernel, name, None)
            if comp is not None and hasattr(comp, "snapshot"):
                try:
                    gov[name] = comp.snapshot()
                except Exception:
                    pass
        # deep freeze: a snapshot is an immutable checkpoint (live references pollute historical archives, confirmed in heavy testing)
        return copy.deepcopy({"time": self.time.snapshot(),
                              "gears": self.gears.snapshot(),
                              "board": self.board.snapshot(),
                              "bus": self.bus.snapshot(),
                              "gov": gov,
                              "modules": modules})
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        t = snap.get("time")
        if isinstance(t, dict):
            self.time.restore(t)
        g = snap.get("gears")
        if isinstance(g, dict):
            self.gears.restore(g)
        b = snap.get("board")
        if isinstance(b, dict):
            self.board.restore_all(b)
        ev = snap.get("bus")
        if isinstance(ev, dict):
            self.bus.restore(ev)
        gv = snap.get("gov")
        if isinstance(gv, dict):
            for name, state in gv.items():
                comp = getattr(self.kernel, name, None)
                if comp is not None and hasattr(comp, "restore"):
                    try:
                        comp.restore(state)
                    except Exception:
                        pass
        mods = snap.get("modules")
        if isinstance(mods, dict):                                  # per-module refill
            for m in self.registry.all():
                inst = getattr(m, "instance", None)
                label = m.snapshot_label or m.module_id
                if inst is None or label not in mods:
                    continue
                try:
                    inst.restore(mods[label])
                except Exception:
                    pass  # a single module's restore exception does not crash the whole restore
 
    def smoke(self) -> bool:
        return (self.time.smoke() and self.gears.smoke()
                and self.registry is not None and self.board.smoke())
 
    def invariants(self) -> bool:
        return (self.time.invariants() and self.gears.invariants()
                and self.board.invariants())
