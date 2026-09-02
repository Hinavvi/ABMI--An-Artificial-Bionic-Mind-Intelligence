# -*- coding: utf-8 -*-
# =============================================================================
# kernel/__init__.py — V8 modular packaging of the non-M kernel components
# (aggregate entry point).
#
# Thirteen kernel modules, all bound by the eight constitutional rules:
#   1. The engine knows no module names — modules write K.* / sys.* only;
#      the engine reads sys.* only
#   2. Tick sovereignty belongs to the engine — modules receive (t, data)
#   3. No trigger, no run — gears declare every + trigger
#   4. The four-piece set is mandatory — snapshot/restore/smoke/invariants
#   5. Total decoupling — modules interact only via the data pipe /
#      blackboard / event bus / service ports
#   6. Code in English, with per-line comments
#   7. Determinism — always derive streams via ctx.rng_for(name)
#   8. Contract keys must be pre-registered in ENGINE_CONTRACTS
#
# Assembly order = dependency order (persona first, narrative last);
# factories backfill shared component instances through the ctx.k.*
# kernel ports (legacy DLC compatibility surface).
# =============================================================================
from __future__ import annotations
from typing import Any, Dict, List

from . import (persona, pns, columnar, attention, cognition, binder,
               emotion, hub, behavior, memory, language, safety, narrative)

# Assembly order IS dependency order: upstream installs first (backfilling
# ctx.k ports), downstream installs later (reading upstream ports).
_KERNEL_MODULES = (
    persona, pns, columnar,
    attention, cognition, binder, emotion,
    hub, behavior, memory, language,
    safety, narrative,
)


def kernel_specs() -> List[Dict[str, Any]]:
    """Produce the dlc_spec() dicts of all kernel modules, in dependency order."""
    return [m.dlc_spec() for m in _KERNEL_MODULES]


__all__ = ["kernel_specs"]
