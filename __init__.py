# -*- coding: utf-8 -*-
"""ABMI V1.0 kernel & core (safety + skeleton + core) — V8 revised series."""
from .time import TimeKeeper, MODE_DIALOGUE, MODE_SERVER
from .gear import GearScheduler, PHASE_ALIAS, canonical_phase
from .engine import V8Engine
from .engine_contracts import (ENGINE_CONTRACTS, CONTRACT_MIRROR,
                               read_contract, missing_contracts,
                               validate_contracts, detect_providers)
from .registry import ModuleRegistry, ModuleManifest
from .blackboard import Blackboard, EventBus, ServicePorts
from .infrastructure import SeededRNG, DerivedRNGStream, DecisionLog, rng_for
from .dlc import install_spec, load_hotplug_specs
from .assembly import KernelAssembler, KernelBundle
 
__version__ = "1.0"
__author__ = "孔祥齐 (Kong Xiangqi)"
