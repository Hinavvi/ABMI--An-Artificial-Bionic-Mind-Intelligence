# -*- coding: utf-8 -*-
# =============================================================================
# engine_contracts.py — the engine's only input surface (V8 revised)
# The engine's only input surface. The engine knows no module names, only sys.* semantic keys.
#
# revision log (aligned with legacy modules):
# - removed the duplicated read_contract (the file defined the same function twice; the later silently overrode the former).
# - provider field annotated with the provider, to help missing_contracts locate alarms.
# =============================================================================
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
 
# =============================================================================
# contract-key master catalog — the engine reads only these keys. Four elements: default / desc / provider.
# =============================================================================
ENGINE_CONTRACTS: Dict[str, Dict[str, Any]] = {
    # ---- 1. consciousness & physiology (engine reads every tick) ----
    "sys.unconsciousness":        {"default": False, "desc": "unconscious (L7 / siege / coma)", "provider": "M4/kheshig"},
    "sys.alcohol_bac":            {"default": 0.0,   "desc": "blood alcohol concentration", "provider": "M4A"},
    "sys.alcohol_tier":           {"default": 0,     "desc": "drunk tier 0..4", "provider": "M4A"},
    "sys.alcohol_blackout":       {"default": False, "desc": "alcohol blackout", "provider": "M4A"},
    "sys.alcohol_behavior_random":{"default": False, "desc": "alcohol behavior randomization", "provider": "M4A"},
    "sys.alcohol_response_delay": {"default": 1.0,   "desc": "alcohol response delay multiplier", "provider": "M4A"},
    "sys.alcohol_attention_jump": {"default": 1.0,   "desc": "alcohol attention jump multiplier", "provider": "M4A"},
    "sys.alcohol_station2_off":   {"default": False, "desc": "alcohol Station-2 disconnection", "provider": "M4A"},
    "sys.alcohol_columnar_cut":   {"default": False, "desc": "alcohol columnar query cut", "provider": "M4A"},
    "sys.alcohol_language_free":  {"default": False, "desc": "alcohol language disinhibition", "provider": "M4A"},
    "sys.cognitive_index":        {"default": 0.5,   "desc": "system cognitive load index", "provider": "M3"},
    "sys.social_support":         {"default": 0.5,   "desc": "social support reserve", "provider": "M5"},
    "sys.flatline":               {"default": False, "desc": "life-support flatline (clinical death)", "provider": "M5"},
    "sys.thermo_signals":         {"default": {},    "desc": "thermal core-skin dual-track signals", "provider": "M11"},
    "sys.thermal_t_core":         {"default": 36.8,  "desc": "core body temperature", "provider": "M11"},
    "sys.pain":                   {"default": 0.0,   "desc": "pain level 0-10 (kernel physio)", "provider": "K.columnar"},
    # ---- 2. trauma & identity ----
    "sys.trauma_active":      {"default": False, "desc": "trauma activation flag", "provider": "M8"},
    "sys.trauma_match":       {"default": 0.0,   "desc": "trauma match score", "provider": "M8"},
    "sys.trauma_type":        {"default": "",    "desc": "trauma 4F type (fight/flight/freeze/fawn)", "provider": "M8"},
    "sys.trauma_integration": {"default": 0.0,   "desc": "trauma integration degree", "provider": "M8"},
    "sys.trauma_theme":       {"default": "",    "desc": "trauma theme label", "provider": "M8"},
    "sys.identity_coherence": {"default": 0.7,   "desc": "identity coherence", "provider": "M10"},
    "sys.moral_emotion":      {"default": "",    "desc": "moral emotion label (guilt/shame/...)", "provider": "M10"},
    "sys.moral_active_emotion": {"default": "",  "desc": "active moral emotion (with behavior impulse)", "provider": "M10"},
    "sys.identity_threat":    {"default": False, "desc": "identity threat flag", "provider": "M10"},
    "sys.decision_paralyzed": {"default": False, "desc": "decision paralysis (core-value conflict)", "provider": "M10"},
    "sys.friction_consecutive": {"default": 0,   "desc": "consecutive identity-friction count", "provider": "M10"},
    # ---- 3. cognition & state ----
    "sys.fail_streak":   {"default": 0,     "desc": "consecutive epistemic failure count", "provider": "M9"},
    "sys.gate_t":        {"default": 0.5,   "desc": "epistemic prior gate threshold", "provider": "M9"},
    "sys.odp_mark":      {"default": "",    "desc": "ODP disposition-conflict mark", "provider": "M6"},
    "sys.idns_active":   {"default": False, "desc": "IDNS pathology layer active", "provider": "IDNS"},
    "sys.iceberg_leak":  {"default": None,  "desc": "iceberg leak signal (push, read-then-clear)", "provider": "M7"},
    # ---- 4. engine-published facts (published every tick, modules read-only) ----
    "sys.tick":               {"default": 0,    "desc": "computation beat (dialogue=user turn, server=0.1ms)", "provider": "engine"},
    "sys.dt":                 {"default": 0.0,  "desc": "narrative minutes per beat", "provider": "engine"},
    "sys.mode":               {"default": "dialogue", "desc": "scene mode ('dialogue' / 'server')", "provider": "engine"},
    "sys.hour":               {"default": 8.0,  "desc": "world clock hour 0-24 (circadian)", "provider": "engine"},
    "sys.last_scene_themes":  {"default": (),   "desc": "last tick's integrated scene themes", "provider": "K.binder"},
    "sys.last_strategy_name": {"default": "",   "desc": "last tick's behavior strategy name", "provider": "K.behavior"},
    "sys.prev_scene_valence": {"default": 0.0,  "desc": "previous scene valence", "provider": "K.emotion"},
}
 
# =============================================================================
# contract mirror table: legacy module keys -> sys.* contract keys (auto-mirrored at board publish, zero module changes).
# the mirror retires once migration completes (constitutional rule 23).
# =============================================================================
CONTRACT_MIRROR: Dict[str, str] = {
    # M4 alcohol
    "M4.alcohol.bac":                          "sys.alcohol_bac",
    "M4.alcohol.tier":                         "sys.alcohol_tier",
    "M4.alcohol.deg_start.unconscious":        "sys.unconsciousness",
    "M4.alcohol.deg.blackout":                 "sys.alcohol_blackout",
    "M4.alcohol.deg.behavior_random":          "sys.alcohol_behavior_random",
    "M4.alcohol.deg.response_delay_mult":      "sys.alcohol_response_delay",
    "M4.alcohol.deg.attention_jump_mult":      "sys.alcohol_attention_jump",
    "M4.alcohol.deg.station2_disconnected":    "sys.alcohol_station2_off",
    "M4.alcohol.deg.columnar_query_cut":       "sys.alcohol_columnar_cut",
    "M4.alcohol.deg.language_disinhibited":    "sys.alcohol_language_free",
    # M8 trauma
    "M8.trauma.active":      "sys.trauma_active",
    "M8.trauma.match":       "sys.trauma_match",
    "M8.trauma.type":        "sys.trauma_type",
    "M8.trauma.integration": "sys.trauma_integration",
    "M8.trauma.theme":       "sys.trauma_theme",
    # M10 morality
    "M10.morality.identity_coherence":  "sys.identity_coherence",
    "M10.morality.friction_consecutive": "sys.friction_consecutive",
    "M10.morality.moral_emotion":       "sys.moral_emotion",
    "M10.morality.identity_threat":     "sys.identity_threat",
    "M10.morality.active_emotion":      "sys.moral_active_emotion",
    "M10.morality.decision_paralyzed":  "sys.decision_paralyzed",
    # M9 / M5 / M11 / M3 / M6 / IDNS / M7
    "M9.epistemology.fail_streak": "sys.fail_streak",
    "M9.epistemology.gate_t":      "sys.gate_t",
    "M5.governor.social_support":  "sys.social_support",
    "M5.life_support.flatline":    "sys.flatline",
    "M11.thermo_signals":          "sys.thermo_signals",
    "M11.thermal.t_core":          "sys.thermal_t_core",
    "M3.life_baseline.cidx":       "sys.cognitive_index",
    "M6.odp.mark":                 "sys.odp_mark",
    "IDNS.active":                 "sys.idns_active",
    "M7.iceberg.zone4_leak_ret":   "sys.iceberg_leak",
}
 
# =============================================================================
# provider detection & validation — soft check, never fatal (constitutional rule 24)
# =============================================================================
def detect_providers(board: Any) -> Dict[str, bool]:
    """scan the board: contract key -> whether a provider has written it."""
    found: Dict[str, bool] = {}
    for key in ENGINE_CONTRACTS:
        try:
            found[key] = board.read(key, None) is not None
        except Exception:
            found[key] = False
    return found
 
 
def missing_contracts(board: Any) -> List[str]:
    """return the list of contract keys currently without providers (dangling) — for boot/maintenance alarms."""
    detection = detect_providers(board)
    return [k for k, ok in detection.items() if not ok]
 
 
def validate_contracts(board: Any) -> Dict[str, str]:
    """validate each contract key: does the board's current value match the declared default's type (soft check).
        Returns: contract key -> ok / type_mismatch / missing.    """
    status: Dict[str, str] = {}
    for key, contract in ENGINE_CONTRACTS.items():
        default = contract["default"]
        try:
            value = board.read(key, None)
        except Exception:
            value = None
        if value is None:
            status[key] = "missing"
        elif isinstance(default, type(value)):
            status[key] = "ok"
        else:
            status[key] = "type_mismatch"
    return status
 
 
def read_contract(board: Any, key: str,
                  cast: Optional[Callable[[Any], Any]] = None) -> Any:
    """read a contract key: with declared default + optional type cast.
        Revision: the original file defined this function twice; this is the only definition.    """
    contract = ENGINE_CONTRACTS.get(key, {"default": None})
    default = contract["default"]
    try:
        value = board.read(key, default)
    except Exception:
        value = default
    if cast is not None and value is not None:
        try:
            return cast(value)
        except (TypeError, ValueError):
            return default
    return value
