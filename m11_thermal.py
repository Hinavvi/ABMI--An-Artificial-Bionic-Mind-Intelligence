# -*- coding: utf-8 -*-
"""M11.thermal — somatic-domain DLC (thermal environment core-skin dual-track: ABMI 1.0 re-engineering of legacy thermal.py)

Role: core/skin dual-track temperature; three inputs (ambient temperature & humidity / clothing insulation / metabolic rate);
  scene auto-encoding (snow/desert/air...)"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
 
M11_CORE_LOW = 35.5                     # core hypothermia threshold (locked)
M11_CORE_HIGH = 39.5                    # core hyperthermia threshold (locked)
M11_ACUTE_HIGH_TICKS = 3                # core hyperthermia for 3 consecutive ticks -> acute heatstroke
M11_ACUTE_LOW_TICKS = 5                 # core hypothermia for 5 consecutive ticks -> acute hypothermia
 
# TMO acute-exposure template (neutral narrative parameters, not medical reference)
M11_ACUTE_TEMPLATES = {
    "heat_stroke_acute": {
        "dose": 0.8, "F": 1.0, "Vd": 1.0, "ke": 0.02, "EC50": 0.45,
        "effects": {"consciousness_suppression": 0.55,
                    "motor_impairment": 0.35, "amnesia": 0.20},
        "category": "M11 acute heatstroke equivalent"},
    "hypothermia_acute": {
        "dose": 0.7, "F": 1.0, "Vd": 1.0, "ke": 0.015, "EC50": 0.50,
        "effects": {"consciousness_suppression": 0.45,
                    "motor_impairment": 0.50},
        "category": "M11 acute hypothermia equivalent"},
}
 
 
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
 
 
class _ThermoSignal:
    """thermal signal object (duck-typed to the kernel PerceptionSignal fields; self-contained)."""
    __slots__ = ("source", "type", "intensity", "category", "theme_hint",
                 "target", "urgency", "payload", "source_tag")
 
    def __init__(self, category: str, intensity: float, column: str,
                 theme: str) -> None:
        self.source = "interoceptor"
        self.type = "internal"
        self.intensity = _clamp(intensity)
        self.category = category
        self.theme_hint = theme
        self.target = "self"
        self.urgency = intensity >= 0.8
        self.payload = {"m11": True, "column": column, "native": True}
        self.source_tag = "pns_autonomic"
 
 
class ThermalHomeostasisModule:
    """M11 human thermodynamics (simplified weighting) + scene encoding; pure local computation."""
 
    _ENV_RULES = (
        (("snow", "ice", "cold winter", "sub-zero"),
         {"t_env": -10.0, "rh": 70.0, "v_air": 3.0}),
        (("desert", "scorching sun", "extreme heat"),
         {"t_env": 40.0, "rh": 15.0, "q_rad": 1000.0}),
        (("air-condition", "indoor"), {"t_env": 24.0, "rh": 50.0, "v_air": 0.1}),
        (("fireplace", "bonfire"), {"t_env": 28.0, "q_rad": 300.0}),
        (("rain", "wet", "drenched", "sweat-soaked"),
         {"rh": 90.0, "wet": True}),
    )
    _CLO_RULES = (
        (("down jacket", "padded coat"), 1.8),
        (("sweater", "jacket", "overcoat"), 1.0),
        (("short sleeves", "light clothing", "shirt"), 0.4),
        (("nude", "bare"), 0.0),
    )
    _MET_RULES = (
        (("run", "chase", "combat", "strenuous"), 3.5),
        (("stand", "walk", "stroll"), 1.3),
        (("sit", "lying", "sleep"), 0.9),
    )
 
    def __init__(self, log: Any, profile: Optional[dict] = None,
                 body_metrics: Optional[dict] = None) -> None:
        self.log = log
        prof = profile or {}
        bm = body_metrics or {}
        # ---- state (ThermalState flattened into plane fields) ----
        self.t_env = 24.0
        self.rh = 50.0                    # relative humidity %
        self.v_air = 0.1                  # wind speed m/s
        self.q_rad = 0.0                  # radiant heat W/m^2 equivalent
        self.clo = float(prof.get("clo", 0.6))
        self.met = float(prof.get("met", 1.0))
        self.fat_pct = float(prof.get("fat_pct", bm.get("fat_pct", 20.0)))
        self.t_skin = float(prof.get("t_skin", 33.5))
        self.t_core = float(prof.get("t_core", 36.8))
        self.sweat = 0.0
        self.dehydration = 0.0            # accumulated dehydration [0,1]
        self.evap_block = 0.0             # evaporation blockage [0,1]
        self.core_low_ticks = 0
        self.core_high_ticks = 0
        self.active_cooling: list = []    # narrative injection: {"site":"palm","medium":"ice"}
        self.thermal_modifiers: dict = {} # TMO downstream modifier
        self._last_drives: list = []
 
    # ================= scene auto-encoding =================
    def infer_from_text(self, text: str = "", stimuli: Optional[list] = None
                        ) -> dict:
        """infer environment/clothing/activity from user text and stimulus labels. Conflicts: cold/heat takes the largest absolute value,
                clothing takes the thickest, activity takes the highest metabolism.        """
        s = self
        found = {"env": [], "clo": [], "met": []}
        blob = text or ""
        for st in stimuli or []:
            if isinstance(st, dict):
                blob += " " + str(st.get("category", "")) + " " \
                    + str(st.get("theme_hint", ""))
            else:
                blob += " " + str(getattr(st, "category", "")) + " " \
                    + str(getattr(st, "theme_hint", ""))
        env_candidates = []
        for keys, patch in self._ENV_RULES:
            if any(k in blob for k in keys):
                env_candidates.append(patch)
                found["env"].append(keys[0])
        if env_candidates:
            cold = [p for p in env_candidates if p.get("t_env", 24.0) < 24.0]
            hot = [p for p in env_candidates if p.get("t_env", 24.0) > 24.0]
            chosen = None
            if cold and hot:
                chosen = max(cold + hot,
                             key=lambda p: abs(p.get("t_env", 24.0) - 24.0))
            elif cold:
                chosen = min(cold, key=lambda p: p.get("t_env", 24.0))
            elif hot:
                chosen = max(hot, key=lambda p: p.get("t_env", 24.0))
            if chosen:
                for k, v in chosen.items():
                    if k == "wet":
                        s.clo *= 0.3
                    else:
                        setattr(s, k, float(v))
            for p in env_candidates:
                if p.get("wet"):
                    s.rh = max(s.rh, 90.0)
                    s.clo *= 0.3
        for keys, clo in self._CLO_RULES:
            if any(k in blob for k in keys):
                found["clo"].append(keys[0])
                s.clo = max(s.clo, float(clo)) if clo > 0 else 0.0
        for keys, met in self._MET_RULES:
            if any(k in blob for k in keys):
                found["met"].append(keys[0])
                s.met = max(s.met, float(met))
        return found
 
    # ================= thermodynamic advance =================
    def advance(self, tick: int, dt_minutes: float = 1.0) -> dict:
        s = self
        tau = 2.5 + s.clo * 0.8
        met_eff = s.met * (1.0 - 0.1 * s.fat_pct / 100.0)
        if s.thermal_modifiers.get("shivering_suppress"):
            shiver_bonus = 0.0
        else:
            shiver_bonus = max(0.0, 36.5 - s.t_core) * 0.8
        q_met = met_eff * 58.0 + shiver_bonus * 58.0
        r_total = 1.0 / (8.3 * math.sqrt(max(0.05, s.v_air)) + 4.0) \
            + s.clo * 0.155
        if s.thermal_modifiers.get("vasodilation"):
            r_total *= 0.75
        h_total = 1.0 / max(0.05, r_total)
        q_conv = (s.t_skin - s.t_env) * h_total
        q_rad = s.q_rad * 0.06
        humidity_block = _clamp((s.rh - 60.0) / 40.0)
        sweat_max = 1.0 * (0.4 if s.thermal_modifiers.get("sweat_suppress")
                           else 1.0)
        s.sweat = _clamp((s.t_core - 37.0) * 0.8 + (s.t_skin - 34.5) * 0.2,
                         0.0, sweat_max)
        q_evap_max = 240.0 * sweat_max
        q_evap = min(s.sweat * 240.0, q_evap_max * (1.0 - humidity_block * 0.75))
        if s.sweat < 0.05:
            s.evap_block = _clamp(humidity_block * 0.2)     # no evaporation demand, no stuffiness penalty
        else:
            s.evap_block = 1.0 - (q_evap / q_evap_max if q_evap_max > 0 else 0.0)
        q_active = 0.0
        for cool in s.active_cooling:
            eff = {"head/neck": 0.35, "palm": 0.20, "sole": 0.15,
                   "armpit": 0.15, "groin": 0.12,
                   "forearm/calf": 0.10}.get(cool.get("site"), 0.10)
            medium = cool.get("medium", "water")
            h_contact = {"water": 50.0, "rain": 50.0, "fan": 15.0,
                         "ice": 200.0, "snow": 200.0}.get(medium, 50.0)
            q_active += eff * abs(s.t_skin - s.t_env) * h_contact * 0.01
        q_net = q_met - q_conv - q_rad - q_evap - q_active
        alpha = 1.0 - math.exp(-dt_minutes / max(0.5, tau))
        setpoint_shift = float(s.thermal_modifiers.get("setpoint_shift", 0.0))
        # skin temperature != ambient temperature: anchored at 33.5 neutral; ambient shifts only via exposure/clothing/wind-humidity
        skin_anchor = 33.5 + _clamp((s.t_env - 24.0) * 0.10, -8.0, 6.0) \
            - _clamp(s.v_air * 0.25, 0.0, 2.0) \
            - _clamp((s.rh - 60.0) / 40.0) * 0.8
        s.t_skin = skin_anchor + (s.t_skin - skin_anchor) \
            * math.exp(-dt_minutes / max(1.5, tau)) \
            + (q_net / max(1.0, h_total)) * alpha * 0.002
        # core temperature has greater inertia: only sustained extreme skin shift / heat-production-vs-dissipation imbalance can move it
        core_drive = (s.t_skin - 33.5) * 0.006 \
            + (q_met - q_evap - q_conv) * 0.00008
        s.t_core = 36.8 + setpoint_shift \
            + (s.t_core - 36.8 - setpoint_shift + core_drive * dt_minutes) \
            * math.exp(-dt_minutes / 30.0)
        s.dehydration = _clamp(
            s.dehydration + s.sweat * dt_minutes / 120.0
            - (0.02 if "drinking water" in str(self._last_drives) else 0.0))
        s.core_low_ticks = s.core_low_ticks + 1 if s.t_core < M11_CORE_LOW else 0
        s.core_high_ticks = s.core_high_ticks + 1 \
            if s.t_core > M11_CORE_HIGH else 0
        return self.signals(tick)
 
    # ================= core-skin dual-track output =================
    def signals(self, tick: int) -> dict:
        s = self
        csi = max(0.0, 33.0 - s.t_skin) / 8.0
        hsi = max(0.0, s.t_skin - 35.0) / 5.0
        cri = max(0.0, M11_CORE_LOW - s.t_core) / 5.0
        chi = max(0.0, s.t_core - M11_CORE_HIGH) / 5.0
        dhy = _clamp(s.dehydration / 2.0)
        evb = _clamp(s.evap_block)
        out: List[_ThermoSignal] = []
        if csi > 0.05:
            out.append(_ThermoSignal("thermo_skin_cold", csi, "PSM_D7",
                                     "physical discomfort"))
        if hsi > 0.05:
            out.append(_ThermoSignal("thermo_skin_hot", hsi, "PSM_D7",
                                     "physical discomfort"))
        if cri > 0.05:
            out.append(_ThermoSignal("thermo_core_low", cri, "PSM_D1",
                                     "system load"))
        if chi > 0.05:
            out.append(_ThermoSignal("thermo_core_high", chi, "PSM_D1",
                                     "system load"))
        if dhy > 0.05:
            out.append(_ThermoSignal("thermo_dehydration", dhy, "PSM_D3",
                                     "physical discomfort"))
        if evb > 0.05:
            out.append(_ThermoSignal("thermo_evap_block", evb, "PSM_D7",
                                     "physical discomfort"))
        drives = []
        if csi > 0.5:
            drives.append(("seek heat source / curl up / add clothing", 1))
        if hsi > 0.6:
            drives.append(("find shade / reduce activity / remove clothing", 1))
        if dhy > 0.3:
            drives.append(("seek drinking water", 2))
        if s.t_core < M11_CORE_LOW or s.t_core > M11_CORE_HIGH:
            drives.append(("seek shelter (survival level)", 3))
        if evb > 0.7:
            drives.append(("tear at clothing / irritable", 2))
        self._last_drives = drives
        acute = None
        if s.core_high_ticks >= M11_ACUTE_HIGH_TICKS:
            acute = "heat_stroke_acute"
        elif s.core_low_ticks >= M11_ACUTE_LOW_TICKS:
            acute = "hypothermia_acute"
        return {"signals": out, "drives": drives, "acute": acute,
                "csi": csi, "hsi": hsi, "cri": cri, "chi": chi,
                "dhy": dhy, "evb": evb}
 
    def modulation(self) -> Dict[str, float]:
        """legacy modulation_vector: all archived as knob.m11.* (shared-channel arbitration avoided)."""
        s = self
        return {
            "temp_bias": _clamp((s.t_skin - 33.5) / 10.0, -1.0, 1.0),
            "risk_aversion": _clamp(max(0.0, 35.8 - s.t_core) * 0.2
                                    + s.dehydration * 0.2),
            "verbosity_mult": 1.0 - _clamp(
                max(0.0, s.t_core - 38.5) * 0.2
                + max(0.0, 35.8 - s.t_core) * 0.2, 0.0, 0.6),
            "sleep_quality_mult": 1.0 - _clamp(abs(s.t_core - 36.8) * 0.2,
                                               0.0, 0.5),
        }
 
    # ================= TMO thermal downstream (service port m11.apply_thermal_modifiers) =================
    def apply_tmo_thermal_modifiers(self, modifiers: dict) -> None:
        self.thermal_modifiers = dict(modifiers or {})
 
    # ================= hook: P0 scene encoding =================
    def on_input(self, tick: int, data: Dict[str, Any]) -> None:
        found = self.infer_from_text(data.get("user_input") or "",
                                     data.get("stimuli") or [])
        if any(found.values()):
            self.log.record(tick, "M11.thermal", "scene encoding",
                            f"{found} -> env/clothing/metabolism updated")
 
    # ================= hook: P1 advance + signal confluence =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        out = self.advance(tick, float(data.get("dt", 1.0)))
        board = self._board
        # ---- thermal signals merged straight into tick data (K.columnar P3-0 routing; engine-merged in legacy versions) ----
        sigs = data.setdefault("signals", [])
        for st in out["signals"]:
            sigs.append(st)
        # ---- publish: mirror -> sys.thermo_signals / sys.thermal_t_core ----
        board.publish("M11.thermo_signals",
                      [{"category": st.category, "intensity": st.intensity,
                        "column": st.payload["column"]}
                       for st in out["signals"]])
        board.publish("M11.thermal.t_core", self.t_core)
        # ---- acute exposure -> TMO dosing port ----
        if out["acute"] and self._services is not None:
            if self._services.call("m4.administer", tick, out["acute"], 1.0,
                                   default=False):
                self.log.record(tick, "M11.thermal", "acute exposure",
                                f"{out['acute']} -> TMO administered")
        # ---- modulation vector archiving (prevents shared-channel overwrite/accumulation) ----
        for key, val in self.modulation().items():
            board.write_knob(f"knob.m11.{key}", val, owner="M11.thermal")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in
                ("t_env", "rh", "v_air", "q_rad", "clo", "met", "fat_pct",
                 "t_skin", "t_core", "sweat", "dehydration", "evap_block",
                 "core_low_ticks", "core_high_ticks")} | {
            "active_cooling": [dict(c) for c in self.active_cooling],
            "thermal_modifiers": dict(self.thermal_modifiers),
            "last_drives": [list(d) for d in self._last_drives]}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        for k in ("t_env", "rh", "v_air", "q_rad", "clo", "met", "fat_pct",
                  "t_skin", "t_core", "sweat", "dehydration", "evap_block"):
            if k in snap:
                setattr(self, k, float(snap[k]))
        self.core_low_ticks = int(snap.get("core_low_ticks", 0))
        self.core_high_ticks = int(snap.get("core_high_ticks", 0))
        self.active_cooling = [dict(c) for c in
                               (snap.get("active_cooling") or [])]
        self.thermal_modifiers = dict(snap.get("thermal_modifiers") or {})
        self._last_drives = [tuple(d) for d in (snap.get("last_drives") or [])]
 
    def smoke(self) -> bool:
        return 20.0 <= self.t_core <= 45.0 and 0.0 <= self.clo <= 5.0
 
    def invariants(self) -> bool:
        return (20.0 <= self.t_core <= 45.0 and 0.0 <= self.dehydration <= 1.0
                and 0.0 <= self.evap_block <= 1.0 and self.core_low_ticks >= 0
                and self.core_high_ticks >= 0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"T_env": round(self.t_env, 1), "RH": round(self.rh, 1),
                "clo": round(self.clo, 2), "met": round(self.met, 2),
                "T_skin": round(self.t_skin, 2),
                "T_core": round(self.t_core, 2),
                "sweat": round(self.sweat, 3),
                "dehydration": round(self.dehydration, 3),
                "evap_block": round(self.evap_block, 3),
                "drives": list(self._last_drives)}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> ThermalHomeostasisModule:
        engine = ThermalHomeostasisModule(ctx.log, ctx.k.card.thermal_profile,
                                          ctx.k.card.body_metrics)
        engine._board = ctx.board
        engine._services = ctx.services
        return engine
 
    def bind(inst: ThermalHomeostasisModule, ctx: Any) -> Dict[str, Any]:
        # acute-exposure template registered into the M4 port (m04a sorts first by filename, bind already ready)
        for name, tpl in M11_ACUTE_TEMPLATES.items():
            ctx.services.call("m4.register_template", name, tpl, default=None)
        ctx.services.offer("m11.apply_thermal_modifiers",
                           inst.apply_tmo_thermal_modifiers)
        return {
            "P0_input": inst.on_input,
            "P1_body": inst.on_body,
            "report": inst.report,
        }
 
    return {
        "module_id": "M11.thermal",
        "version": "1.0",
        "zone": "physical",                                         # somatic domain (resident)
        "contract_keys": ("sys.thermo_signals", "sys.thermal_t_core"),
        "gear": {
            "P0_input": {"every": 1, "trigger": None},
            "P1_body": {"every": 1, "trigger": None},
        },
        "priorities": {"P0_input": 50, "P1_body": 40},              # after PNS/alcohol
        "factory": factory,
        "bind": bind,
        "provides": ("m11.apply_thermal_modifiers",),
        "requires": {"soft": {"m4.register_template": None,
                              "m4.administer": False}},
        "report_key": "thermal",
        "snapshot_label": "m11_thermal",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
