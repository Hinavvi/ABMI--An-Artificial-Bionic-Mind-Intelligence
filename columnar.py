# -*- coding: utf-8 -*-
"""K.columnar — physiology-domain kernel module (nine functional columns in parallel + pathway compression register: 9.1~9.4)

Role:
  - receive PNS internal somatic signals -> the corresponding column's reception layer (prior filter applied first, M9 service port)
  - PSM_D1 multi-source arbitration (trauma > metabolic toxicity > moral-somatic...)"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import (PSM_DIMENSION_SPECS, URGENCY_THRESHOLDS, ACTION_THRESHOLD,
                        DISCHARGE_WAKE_LEVEL, DISCHARGE_FORCE_LEVEL,
                        DISCHARGE_EP_PEAK, DISCHARGE_EP_SCALE, DISCHARGE_EP_CAP,
                        DISCHARGE_D9_COUPLING, PSM_D1_PRIORITY,
                        TRAUMA_PRIORITY_SHIELD_TICKS, PATHWAYS, PATHWAY_MOTOR_FINE,
                        PATHWAY_MOTOR_GROSS, PATHWAY_DIGESTION, PATHWAY_EXCRETORY,
                        COMPRESSION_TABLE, SM_SRF, SM_SSM, SM_ARF, SM_HMF, SM_PIF,
                        TMO_CONSCIOUSNESS_T2)
from .models import (PerceptionSignal, PhysiologicalStateEncoding,
                     PhysiologicalStateReport, MotorActionCommand, clamp)
 
 
# =============================================================================
# physiological state vector (current state of each column's processing domain)
# =============================================================================
class PhysiologicalStateVector:
    """internal somatic quantities: heart rate/breathing/muscle tone/stress/pain/hunger/thermal discomfort/discharge dual fullness."""
 
    __slots__ = ("heart_rate", "hr_baseline", "breath_rate", "br_baseline",
                 "deep_slow_breath", "muscle_tone", "stress_level", "pain_level",
                 "hunger", "temp_discomfort", "discharge_liquid", "discharge_solid")
 
    def __init__(self, hr_baseline: float = 72.0, br_baseline: float = 14.0,
                 muscle_tone: float = 4.0, hunger: float = 2.0) -> None:
        self.heart_rate = hr_baseline       # heart rate (from baseline)
        self.hr_baseline = hr_baseline      # heart-rate baseline
        self.breath_rate = br_baseline      # breathing rate (from baseline)
        self.br_baseline = br_baseline      # breathing-rate baseline
        self.deep_slow_breath = False       # deep-slow-breathing flag
        self.muscle_tone = muscle_tone      # muscle tone 0-10
        self.stress_level = 0.0             # stress level 0-10 (PSM_D5)
        self.pain_level = 0.0               # pain level 0-10 (PSM_D6)
        self.hunger = hunger                # hunger 0-10 (PSM_D3)
        self.temp_discomfort = 0.0          # thermal discomfort 0-1 (PSM_D7)
        self.discharge_liquid = 0.0         # liquid-fullness mirror 0-1 (PSM_D8)
        self.discharge_solid = 0.0          # solid-fullness mirror 0-1 (PSM_D9)
 
 
# =============================================================================
# single-column monitor (9.1: reception layer -> encoding layer -> action decision layer)
# =============================================================================
class PhysiologicalStateMonitor:
    """reception-layer bandwidth constant 1.0 (compression acts only on motor output; perception is fully preserved)."""
 
    def __init__(self, column_id: str, inertia_bias: float = 0.0) -> None:
        spec = PSM_DIMENSION_SPECS[column_id]
        self.id = column_id
        self.domain = spec["domain"]                                # processing domain
        self.alpha, self.beta, self.gamma = spec["alpha"], spec["beta"], spec["gamma"]
        self.dormant_default = spec["dormant_default"]              # dormant by default
        self.direct = spec["direct_passthrough"]                    # pass-through column
        self.active = not self.dormant_default                      # active flag
        self.inertia_bias = inertia_bias                            # inertia bias (persona card)
        self.prev_effective = 0.0                                   # last round's effective signal
        self.prev_delta = 0.0                                       # last round's delta
        self.inertia = 0.0                                          # action inertia (<=0.3)
        self.last_encoding: Optional[PhysiologicalStateEncoding] = None
        self.last_action: Optional[MotorActionCommand] = None
        self.fatigue = 0.0                                          # fatigue (PSM_D5 stress fatigue)
        self.stress_minutes = 0.0                                   # stress duration minutes (forced-reset judgment)
 
    def receive(self, raw: float, hormone_bias: float) -> tuple:
        """reception layer: effective signal = raw x hormone bias; returns (effective, delta, rate)."""
        effective = clamp(raw * hormone_bias)
        delta = effective - self.prev_effective
        delta_rate = delta - self.prev_delta
        self.prev_effective, self.prev_delta = effective, delta
        return effective, delta, delta_rate
 
    def serialize_state_snapshot(self, level: float, delta: float,
                                 force_urgency3: bool = False) -> PhysiologicalStateEncoding:
        """encoding layer: level -> urgency 0-3 + trend + description label."""
        level = clamp(level)
        t1, t2, t3 = URGENCY_THRESHOLDS
        urgency = 0 if level < t1 else (1 if level < t2 else (2 if level < t3 else 3))
        if force_urgency3:
            urgency = 3                                             # fullness >0.85 forces attention
        if abs(delta) < 0.02:
            trend = "stable"
        elif abs(delta) > 0.3:
            trend = "fluctuating"
        else:
            trend = "rising" if delta > 0 else "falling"
        self.last_encoding = PhysiologicalStateEncoding(
            column_id=self.id, encoded_level=round(level, 3), trend=trend,
            urgency_level=urgency, discomfort_level=round(level * 4),
            descriptive_tag=f"{self.domain}:{level:.2f}")
        return self.last_encoding
 
    def judge(self, level: float, delta: float, delta_rate: float,
              intent_pull: float, pathway: str, command: str,
              threshold_override: Optional[float] = None) -> Optional[MotorActionCommand]:
        """action decision layer: signal push (alpha/beta/gamma weighted) + intent pull (toward threshold) - inertia resistance; critical clears inertia."""
        f1 = clamp(level)
        f2 = clamp(abs(delta) * 2.0)
        f3 = clamp(abs(delta_rate) * 3.0)
        push = self.alpha * f1 + self.beta * f2 + self.gamma * f3
        inertia = self.inertia + self.inertia_bias
        urgency = self.last_encoding.urgency_level if self.last_encoding else 0
        if urgency >= 3:
            inertia = 0.0                                           # critical -> inertia cleared
        threshold = (ACTION_THRESHOLD - intent_pull * 0.15
                     if threshold_override is None else threshold_override)
        net_force = push - inertia
        self.last_action = None
        if net_force > threshold:
            self.last_action = MotorActionCommand(
                pathway=pathway, command=command,
                magnitude=round(clamp(net_force), 3), source_column=self.id)
            self.inertia = min(0.3, self.inertia + 0.1)             # post-action inertia accumulation
        return self.last_action
 
 
# =============================================================================
# ColumnarEngine — V8 module shell: nine parallel columns + compression register + body report
# =============================================================================
class ColumnarEngine:
    """inter-column coupling iron rule: except the D1<->D2 cardiopulmonary coupling, all inter-column influence must
        travel the full loop upload encoding -> perception integration layer -> CNS -> downlink behavior goal; no shortcuts.    """
 
    _ACTION_MAP = {                                                 # column -> (pathway, directive)
        "PSM_D1": (PATHWAY_MOTOR_FINE, "regulate heart rate"),
        "PSM_D2": (PATHWAY_MOTOR_FINE, "switch breathing pattern"),
        "PSM_D3": (PATHWAY_DIGESTION, "feeding drive"),
        "PSM_D4": (PATHWAY_MOTOR_GROSS, "tonus regulation / posture switching"),
        "PSM_D5": (PATHWAY_MOTOR_GROSS, "sympathetic activation"),
        "PSM_D6": (PATHWAY_MOTOR_GROSS, "avoidance / protective movement"),
        "PSM_D7": (PATHWAY_MOTOR_FINE, "trembling / sweating"),
        "PSM_D8": (PATHWAY_EXCRETORY, "excretion request (liquid contents)"),
        "PSM_D9": (PATHWAY_EXCRETORY, "excretion request (solid contents)"),
    }
 
    def __init__(self, card: Any, hormones: Any, log: DecisionLog) -> None:
        self.log = log
        self.hormones = hormones                                    # kernel port wiring (PNS modulation factors)
        c = 0.075                                                   # hard-coded fine-tune coefficient: offset = C x full range
        phys = card.physiology
        self.physio = PhysiologicalStateVector(
            hr_baseline=72.0 + phys.get("resting_hr", 0.0) * c * 40.0,
            br_baseline=14.0 + phys.get("breath_baseline", 0.0) * c * 8.0,
            muscle_tone=4.0 + phys.get("default_muscle_tone", 0.0) * c * 10.0,
            hunger=2.0 + phys.get("hunger_sensitivity", 0.0) * c * 10.0)
        self.stress_threshold_bias = phys.get("stress_threshold", 0.0) * c * 10.0
        self.pain_sensitivity = 1.0 + phys.get("pain_sensitivity", 0.0) * c * 5.0
        inertia_bias = phys.get("action_inertia", 0.0) * c * 2.0
        self.columns = {cid: PhysiologicalStateMonitor(cid, inertia_bias)
                        for cid in PSM_DIMENSION_SPECS}             # nine column instances
        self._raws = {cid: 0.0 for cid in PSM_DIMENSION_SPECS}      # this tick's reception-layer raw values
        self._pending_actions: List[MotorActionCommand] = []        # motor directives pending egress
        self._hormone_requests: List[tuple] = []                    # factor requests pending egress
        self.bandwidths = {p: 1.0 for p in PATHWAYS}                # pathway compression register
        self.discharge_hold = False                                 # M2: fight-or-flight -> discharge threshold +0.3
        self.discharge_d9_sensitivity = 1.0                         # M1: D9 reception gain
        self.gut_mult = 1.0                                         # M1: gastrointestinal motility rate
        self.discharge_events: List[tuple] = []                     # this tick's discharge-completed events
        self._d1_tagged: Dict[str, float] = {}                      # D1 multi-source signal buffer
        self._d1_trauma_shield_until = -1                           # trauma-shield deadline tick
        self.priori_filter_fn = None                                # M9 prior filter (service-port injection)
        self.iceberg_hits: Dict[str, list] = {}                     # M7 iceberg hit (board injection)
        self.alcohol_query_cut = False                              # M4 L6: columnar queries largely cut
        self.alcohol_hard_suppress = False                          # M4 L7: only D1/D2/D8/D9 remain
 
    # ================= PSM_D1 multi-source signal arbitration (V3.0) =================
    def route_psm_d1_signal(self, tick: int, raw: float, source_tag: str,
                            trauma_shield: bool = False) -> None:
        """multi-source write to D1 reception layer: trauma bioelectricity (no decay for the first 3 ticks) > metabolic toxicity > moral somatic > autonomic rhythm > cycle > pathology."""
        if source_tag not in PSM_D1_PRIORITY:
            source_tag = "pns_autonomic"
        self._d1_tagged[source_tag] = max(self._d1_tagged.get(source_tag, 0.0), clamp(raw))
        if trauma_shield:
            self._d1_trauma_shield_until = tick + TRAUMA_PRIORITY_SHIELD_TICKS
 
    def _arbitrate_psm_d1(self, tick: int) -> None:
        """winner takes all: the highest-priority source with raw>0.01 wins this tick's D1 reception layer."""
        if not self._d1_tagged:
            return
        winner, winner_raw = None, 0.0
        for tag in PSM_D1_PRIORITY:
            raw = self._d1_tagged.get(tag, 0.0)
            if raw > 0.01:
                winner, winner_raw = tag, raw
                break
        if tick <= self._d1_trauma_shield_until:                    # trauma always wins during the shield period
            t_raw = self._d1_tagged.get("trauma", 0.0)
            if t_raw > 0.01:
                winner, winner_raw = "trauma", t_raw
        if winner is not None:
            self._raws["PSM_D1"] = max(self._raws["PSM_D1"], winner_raw)
            if winner != "pns_autonomic":
                self.log.record(tick, "columnar.PSM_D1", "multi-source arbitration",
                                f"{winner} wins (raw={winner_raw:.2f})")
        self._d1_tagged = {}
 
    # ================= input routing =================
    def route_internal_signal(self, sig: PerceptionSignal) -> None:
        """PNS internal somatic signals -> corresponding column (Chapter 5 sorting; M9 prior filter applied first)."""
        cat, intensity = sig.category, sig.intensity
        if self.priori_filter_fn is not None:
            intensity = self.priori_filter_fn(cat, intensity)       # prior gating
        if cat in ("threat", "sudden threat", "social threat",
                   "loud noise", "status challenge", "clashing blades"):
            self._raws["PSM_D5"] = max(self._raws["PSM_D5"], intensity)
            self.route_psm_d1_signal(0, intensity * 0.8, sig.source_tag)  # startle reflex
        elif cat in ("pain", "injury"):
            self._raws["PSM_D6"] = max(self._raws["PSM_D6"], intensity)
            self.physio.pain_level = clamp(
                self.physio.pain_level + intensity * 8.0 * self.pain_sensitivity, 0, 10)
        elif cat == "hunger":
            self._raws["PSM_D3"] = max(self._raws["PSM_D3"], intensity)
        elif cat in ("cold", "heat"):
            self._raws["PSM_D7"] = max(self._raws["PSM_D7"], intensity)
            self.physio.temp_discomfort = intensity
        elif cat == "own heart rate rising":
            self.route_psm_d1_signal(0, intensity, sig.source_tag)
 
    def set_drive(self, column_id: str, raw: float) -> None:
        """engine-level drive writes (hunger accumulating over time, discharge fullness mirrors, etc.)."""
        self._raws[column_id] = max(self._raws[column_id], clamp(raw))
 
    # ================= hormone bias (each column's reception layer) =================
    def _hormone_bias(self, cid: str, eff: Dict[str, float]) -> float:
        if cid == "PSM_D1":
            return 1.0 + 1.5 * eff.get(SM_SRF, 0) / 100.0 - 0.3 * eff.get(SM_ARF, 0) / 100.0
        if cid == "PSM_D2":
            return 1.0 + 0.8 * eff.get(SM_SRF, 0) / 100.0
        if cid == "PSM_D5":
            return 1.0 + 0.5 * eff.get(SM_SSM, 0) / 100.0
        if cid == "PSM_D6":
            return 1.0 - 0.6 * eff.get(SM_PIF, 0) / 100.0           # pain-suppression factor naturally compresses pain signals
        if cid == "PSM_D9":
            return self.discharge_d9_sensitivity                    # M1 phase-I gain
        return 1.0
 
    # ================= V2.0 aggregate modulation (somatic part, compatibility surface) =================
    def apply_modulation(self, mv: Any, dt_minutes: float) -> None:
        p = self.physio
        if mv.pain_bias:
            p.pain_level = clamp(p.pain_level + mv.pain_bias * dt_minutes, 0, 10)
        if mv.pain_relief:
            p.pain_level = max(0.0, p.pain_level - mv.pain_relief * 4.0 * dt_minutes)
        if mv.temp_bias:
            p.temp_discomfort = clamp(p.temp_discomfort + mv.temp_bias)
        if mv.respiratory_suppression:
            p.breath_rate = max(6.0, p.breath_rate
                                - p.br_baseline * 0.3 * mv.respiratory_suppression * dt_minutes)
        if mv.gut_mult != 1.0:
            self.gut_mult = mv.gut_mult
        if mv.discharge_d9_sensitivity != 1.0:
            self.discharge_d9_sensitivity = mv.discharge_d9_sensitivity
 
    # ================= main processing (P3 every tick) =================
    def process_columns(self, tick: int, dt_minutes: float,
                        intent_pulls: Dict[str, float]) -> None:
        """one round of nine columns: arbitration -> mirrors -> per-column three layers -> cardiopulmonary coupling -> compression register -> homeostasis."""
        eff = self.hormones.compute_effective_levels()              # effective hormones after antagonism
        p = self.physio
        self._arbitrate_psm_d1(tick)                                # D1 multi-source arbitration (decided first)
        self._raws["PSM_D4"] = max(self._raws["PSM_D4"], p.stress_level / 10.0 * 0.5)
        self._raws["PSM_D8"] = max(self._raws["PSM_D8"], p.discharge_liquid)  # fullness mirror
        self._raws["PSM_D9"] = max(self._raws["PSM_D9"], p.discharge_solid)
        for cid, hits in (self.iceberg_hits or {}).items():         # M7 iceberg hit raises the column
            if cid in self._raws and hits:
                boost = max(h["activation"] for h in hits) * 0.3
                self._raws[cid] = max(self._raws[cid], clamp(boost))
        self.iceberg_hits = {}
        self.discharge_events = []
        for cid, col in self.columns.items():
            if self.alcohol_hard_suppress and cid not in ("PSM_D1", "PSM_D2",
                                                          "PSM_D8", "PSM_D9"):
                continue                                            # M4 L7 hard power-cut keeps only heart/lungs + discharge
            raw = self._raws[cid]
            if raw > 0.01 or not col.dormant_default:
                col.active = True                                   # any signal wakes the column
            if cid in ("PSM_D8", "PSM_D9") and raw > DISCHARGE_WAKE_LEVEL:
                col.active = True                                   # fullness >0.3 wakes
            if not col.active:
                continue                                            # dormant columns cost zero
            bias = self._hormone_bias(cid, eff)
            effective, delta, delta_rate = col.receive(raw, bias)
            level = self._level_of(cid, effective)
            force3 = ((cid == "PSM_D8" and p.discharge_liquid > DISCHARGE_FORCE_LEVEL)
                      or (cid == "PSM_D9" and p.discharge_solid > DISCHARGE_FORCE_LEVEL))
            col.serialize_state_snapshot(level, delta, force_urgency3=force3)
            pull = intent_pulls.get(cid, 0.0)                       # CNS behavior-goal pull
            pathway, command = self._ACTION_MAP[cid]
            override = None
            if cid in ("PSM_D8", "PSM_D9"):                         # discharge-column threshold shift
                urgency = col.last_encoding.urgency_level
                override = (ACTION_THRESHOLD + (0.3 if self.discharge_hold else 0.0)
                            - (0.5 if urgency >= 3 else 0.0))
            action = col.judge(level, delta, delta_rate, pull, pathway, command,
                               threshold_override=override)
            if action:
                self._apply_action(tick, cid, action, effective)
        self._apply_cardiopulmonary_coupling(tick)                  # the only direct inter-column coupling
        self._update_compression_register(tick, eff)                # compression register
        self._homeostasis(dt_minutes)                               # homeostatic return
        self._raws = {cid: 0.0 for cid in PSM_DIMENSION_SPECS}      # reception layer cleared (rewritten next tick)
 
    # legacy compatibility alias (old kernel-port call surface)
    def generate_voice_prompt(self, tick: int, dt_minutes: float,
                              intent_pulls: Dict[str, float]) -> None:
        self.process_columns(tick, dt_minutes, intent_pulls)
 
    def _level_of(self, cid: str, effective: float) -> float:
        """encoding level: column-specific formulas (physiological quantities normalized + effective-signal mixing)."""
        p = self.physio
        if cid == "PSM_D1":
            return clamp(abs(p.heart_rate - p.hr_baseline) / 50.0 + effective * 0.3)
        if cid == "PSM_D2":
            return clamp(abs(p.breath_rate - p.br_baseline) / 15.0 + effective * 0.3)
        if cid == "PSM_D3":
            return clamp(p.hunger / 10.0)
        if cid == "PSM_D4":
            return clamp(p.muscle_tone / 10.0)
        if cid == "PSM_D5":
            return clamp(p.stress_level / 10.0 + effective * 0.5)
        if cid == "PSM_D6":
            return clamp(p.pain_level / 10.0)
        if cid == "PSM_D7":
            return clamp(p.temp_discomfort)
        if cid == "PSM_D8":
            return clamp(p.discharge_liquid)
        if cid == "PSM_D9":
            return clamp(p.discharge_solid)
        return effective
 
    # ---- action execution (changes physiological quantities + records egress) ----
    def _apply_action(self, tick: int, cid: str, action: MotorActionCommand,
                      effective: float) -> None:
        p = self.physio
        if cid == "PSM_D1":
            p.heart_rate = clamp(p.heart_rate + effective * 30.0, 45.0, 200.0)
        elif cid == "PSM_D2":
            p.breath_rate = clamp(p.breath_rate + effective * 12.0, 6.0, 45.0)
            p.deep_slow_breath = False
        elif cid == "PSM_D5":
            p.stress_level = clamp(p.stress_level + effective * 4.0
                                   + self.stress_threshold_bias, 0.0, 10.0)
            col = self.columns["PSM_D5"]
            factor = 1.0
            if col.fatigue > 80:                                    # fatigue >80: release halved + SSM baseline raised
                factor = 0.5
                self.hormones.set_baseline(SM_SSM, self.hormones.baselines[SM_SSM] + 5.0)
            elif col.fatigue > 50:
                factor = 0.8
            self._hormone_requests.append((SM_SRF, 30.0 * factor, "PSM_D5 sympathetic activation"))
            self._hormone_requests.append((SM_SSM, 15.0, "PSM_D5 sympathetic activation"))
            col.fatigue += 10.0
        elif cid == "PSM_D6":
            self._hormone_requests.append((SM_PIF, 20.0, "PSM_D6 pain protection"))
        elif cid == "PSM_D4":
            p.muscle_tone = clamp(p.muscle_tone + effective * 3.0, 0.0, 10.0)
        elif cid == "PSM_D8":
            self.discharge_events.append(("liquid", p.discharge_liquid))  # discharge event (peak feeds SM_PIF)
            self._raws["PSM_D9"] = max(self._raws["PSM_D9"],          # D8->D9 parasympathetic linkage
                                       p.discharge_solid + DISCHARGE_D9_COUPLING)
        elif cid == "PSM_D9":
            self.discharge_events.append(("solid", p.discharge_solid))
        self._pending_actions.append(action)
        self.log.record(tick, f"columnar.{cid}", "action decision",
                        f"{action.command} net={action.magnitude:.2f}")
 
    # ---- PSM_D1<->PSM_D2 cardiopulmonary coupling (the only direct coupling of life-sustenance) ----
    def _apply_cardiopulmonary_coupling(self, tick: int) -> None:
        p = self.physio
        c1, c2 = self.columns["PSM_D1"], self.columns["PSM_D2"]
        if c1.active and c2.active:
            hr_dev = max(0.0, p.heart_rate - p.hr_baseline)
            p.breath_rate = clamp(p.breath_rate + hr_dev * 0.3 * 0.1, 6.0, 45.0)
            if p.deep_slow_breath:
                p.heart_rate = max(p.hr_baseline, p.heart_rate - 0.5 * hr_dev)
                self.log.record(tick, "columnar.PSM_D1<->PSM_D2",
                                "cardiopulmonary coupling", "deep breath -> heart rate down")
 
    # ---- pathway compression register (9.4: compresses motor output only; discharge pathways withheld at SRF peaks) ----
    def _update_compression_register(self, tick: int, eff: Dict[str, float]) -> None:
        ser_relief = 1.0 - 0.5 * eff.get(SM_HMF, 0) / 100.0         # HMF decompression
        for pathway in PATHWAYS:
            compress, expand = 0.0, 0.0
            for hid, k in COMPRESSION_TABLE[pathway].items():
                lv = eff.get(hid, 0.0) / 100.0
                if k >= 0:
                    compress += k * lv
                else:
                    expand += -k * lv
            bw = (1.0 - min(0.95, compress * ser_relief)) * (1.0 + expand)
            self.bandwidths[pathway] = round(clamp(bw, 0.05, 2.0), 3)
        srf = eff.get(SM_SRF, 0.0)                                  # discharge-pathway special rule
        if srf > 80.0:
            self.bandwidths[PATHWAY_EXCRETORY] = min(self.bandwidths[PATHWAY_EXCRETORY], 0.3)
        elif srf > 60.0:
            self.bandwidths[PATHWAY_EXCRETORY] = min(self.bandwidths[PATHWAY_EXCRETORY], 0.5)
 
    # ---- egress aggregation (compression + SM_PIF pulse judgment) ----
    def collect_outputs(self, tick: int) -> tuple:
        compressed_actions = []
        for a in self._pending_actions:
            a.compressed = round(a.magnitude * self.bandwidths.get(a.pathway, 1.0), 3)
            compressed_actions.append(a)
        for kind, peak in self.discharge_events:                    # discharge completed -> SM_PIF pulse
            if peak >= DISCHARGE_EP_PEAK:
                amount = min(DISCHARGE_EP_CAP, (peak - DISCHARGE_EP_PEAK) * DISCHARGE_EP_SCALE)
                self._hormone_requests.append(
                    (SM_PIF, amount, f"excretion complete SM_PIF pulse (peak {peak:.2f})"))
        requests = list(self._hormone_requests)
        self._pending_actions, self._hormone_requests = [], []
        return compressed_actions, requests
 
    # ---- homeostatic return (every tick) ----
    def _homeostasis(self, dt: float) -> None:
        p = self.physio
        p.heart_rate += (p.hr_baseline - p.heart_rate) * 0.15 * dt
        p.breath_rate += (p.br_baseline - p.breath_rate) * 0.2 * dt
        p.stress_level = max(0.0, p.stress_level - 0.4 * dt)
        p.pain_level = max(0.0, p.pain_level * (0.85 ** dt))
        p.muscle_tone += (4.0 - p.muscle_tone) * 0.1 * dt
        c5 = self.columns["PSM_D5"]
        if p.stress_level >= 3.0:
            c5.stress_minutes += dt                                 # stress duration timing
        else:
            c5.stress_minutes = 0.0
 
    def add_hunger(self, amount: float) -> None:
        self.physio.hunger = clamp(self.physio.hunger + amount * self.gut_mult, 0.0, 10.0)
 
    # ================= report =================
    def encodings(self) -> Dict[str, PhysiologicalStateEncoding]:
        return {cid: c.last_encoding for cid, c in self.columns.items()
                if c.last_encoding is not None and c.active}
 
    def body_report(self) -> PhysiologicalStateReport:
        p = self.physio
        return PhysiologicalStateReport(
            encodings=self.encodings(),
            hormones={k: round(v, 1) for k, v in self.hormones.compute_effective_levels().items()},
            heart_rate=round(p.heart_rate, 1), hr_baseline=round(p.hr_baseline, 1),
            breath_rate=round(p.breath_rate, 1), br_baseline=round(p.br_baseline, 1),
            deep_slow_breath=p.deep_slow_breath, muscle_tone=round(p.muscle_tone, 1),
            stress_level=round(p.stress_level, 1), pain_level=round(p.pain_level, 1),
            hunger=round(p.hunger, 1),
            discharge_liquid=round(p.discharge_liquid, 3),
            discharge_solid=round(p.discharge_solid, 3))
 
    def settle_after_sleep(self, tick: int, quality: float) -> None:
        """sleep settlement (4.4): D5 fatigue cleared; SRF/SSM return to baseline; HMF raised by quality."""
        self.columns["PSM_D5"].fatigue = 0.0
        self.hormones.reset_to_baseline(SM_SRF)
        self.hormones.reset_to_baseline(SM_SSM)
        self.hormones.release_modulator(tick, SM_HMF, 20.0 * quality,
                                        "sleep settlement: HMF rises by quality")
        self.physio.stress_level = 0.0
        self.log.record(tick, "columnar", "sleep settlement",
                        "PSM_D5 fatigue cleared, SRF/SSM baseline, HMF raised")
 
    # ================= P3 hook (V8 module surface) =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board                                         # injected at install time
        dt = float(data.get("dt", 0.0))
        # soft-key reads (DLC absent = neutral default; unplugged and still runs)
        self.alcohol_query_cut = bool(board.read("sys.alcohol_columnar_cut", False))
        self.alcohol_hard_suppress = bool(board.read("sys.unconsciousness", False))
        self.discharge_hold = bool(board.read_knob("knob.discharge_hold", False))
        self.gut_mult = float(board.read_knob("knob.gut_mult", 1.0))
        self.discharge_d9_sensitivity = float(board.read_knob("knob.d9_sensitivity", 1.0))
        self.iceberg_hits = board.read("M7.iceberg.column_hits", {}) or {}
        self.priori_filter_fn = self._services.call(                # M9 prior-filter service
            "m9.priori_filter", default=None)
        discharge = board.read("K.pns.discharge", {}) or {}         # fullness mirror published at P1
        self.physio.discharge_liquid = float(discharge.get("liquid", 0.0))
        self.physio.discharge_solid = float(discharge.get("solid", 0.0))
        for sig in data.get("signals", ()):                         # internal signals routed to columns
            if sig.source == "interoceptor" or sig.type == "internal":
                self.route_internal_signal(sig)
        intent_pulls = board.read("K.hub.pulls", {}) or {}          # last tick's CNS pull
        self.process_columns(tick, dt, intent_pulls)                # one round of the nine columns
        actions, requests = self.collect_outputs(tick)              # egress aggregation
        data["motor_commands"] = actions                            # -> K.pns P5 execute
        data["hormone_requests"] = requests                         # -> K.pns P5 release
        data["discharge_events"] = list(self.discharge_events)      # -> K.pns P5 clear
        enc = self.encodings()
        data["encodings"] = enc                                     # -> K.hub push-pull
        data["columnar_signals"] = [                                # column encoding -> perception competition
            PerceptionSignal(source="interoceptor", type="internal",
                             intensity=e.encoded_level, category="physical discomfort"
                             if e.urgency_level >= 2 else "system load",
                             urgency=e.urgency_level >= 3)
            for e in enc.values() if e.encoded_level > 0.01]
        report = self.body_report()
        board.batch_publish({                                       # body report onto the board
            "K.columnar.body": asdict(report),
            "K.columnar.bandwidths": dict(self.bandwidths),
            "K.columnar.c5_stress_minutes": self.columns["PSM_D5"].stress_minutes,
            "sys.pain": report.pain_level,                          # contract key: read by the siege predicate
        })
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {
            "physio": {k: getattr(self.physio, k) for k in self.physio.__slots__},
            "columns": {cid: {"active": c.active,
                              "prev_effective": c.prev_effective,
                              "prev_delta": c.prev_delta,
                              "inertia": c.inertia,
                              "fatigue": c.fatigue,
                              "stress_minutes": c.stress_minutes,
                              "last_encoding": asdict(c.last_encoding)
                              if c.last_encoding else None}
                        for cid, c in self.columns.items()},
            "bandwidths": dict(self.bandwidths),
            "discharge_hold": self.discharge_hold,
            "discharge_d9_sensitivity": self.discharge_d9_sensitivity,
            "gut_mult": self.gut_mult,
        }
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        phys = snap.get("physio")
        if isinstance(phys, dict):
            for key, value in phys.items():                         # field-by-field write-back of the physiological vector
                if key in self.physio.__slots__:
                    setattr(self.physio, key, value)
        cols = snap.get("columns")
        if isinstance(cols, dict):
            for cid, state in cols.items():
                col = self.columns.get(cid)
                if col is None or not isinstance(state, dict):
                    continue
                for key in ("active", "prev_effective", "prev_delta",
                            "inertia", "fatigue", "stress_minutes"):
                    if key in state:
                        setattr(col, key, state[key])
                enc = state.get("last_encoding")
                if isinstance(enc, dict):                           # encoding rebuild
                    col.last_encoding = PhysiologicalStateEncoding(**enc)
        if isinstance(snap.get("bandwidths"), dict):
            self.bandwidths.update(snap["bandwidths"])
        self.discharge_hold = bool(snap.get("discharge_hold", False))
        self.discharge_d9_sensitivity = float(snap.get("discharge_d9_sensitivity", 1.0))
        self.gut_mult = float(snap.get("gut_mult", 1.0))
 
    def smoke(self) -> bool:
        return len(self.columns) == len(PSM_DIMENSION_SPECS) and self.physio is not None
 
    def invariants(self) -> bool:
        p = self.physio
        return (45.0 <= p.heart_rate <= 200.0 and 6.0 <= p.breath_rate <= 45.0
                and 0.0 <= p.pain_level <= 10.0 and 0.0 <= p.stress_level <= 10.0
                and 0.0 <= p.discharge_liquid <= 1.0 and 0.0 <= p.discharge_solid <= 1.0
                and all(0.05 <= bw <= 2.0 for bw in self.bandwidths.values()))
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        r = self.body_report()
        return {"hr": r.heart_rate, "br": r.breath_rate,
                "stress": r.stress_level, "pain": r.pain_level,
                "hunger": r.hunger,
                "active_columns": [c for c in self.columns if self.columns[c].active]}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> ColumnarEngine:
        # hormone scheduler wired via kernel port (K.pns installs first, so it is already backfilled)
        engine = ColumnarEngine(ctx.k.card, ctx.k.hormones, ctx.log)
        engine._board = ctx.board
        engine._services = ctx.services
        ctx.k.columnar = engine                                     # backfill kernel ports
        # sleep-settlement subscription: bus-event driven (decoupled from K.pns)
        ctx.bus.subscribe("sleep.settle",
                          lambda item: engine.settle_after_sleep(
                              item["payload"]["tick"], item["payload"]["quality"]),
                          owner="K.columnar")
        return engine
 
    def bind(inst: ColumnarEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P3_cognition": inst.on_cognition,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.columnar",
        "version": "8.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": ("sys.pain",),                             # contract keys committed for write
        "gear": {
            "P3_cognition": {"every": 1, "trigger": None},          # 1:1 always-on (homeostasis cannot sleep)
        },
        "priorities": {"P3_cognition": 0},                          # front of the cognition phase (encoding feeds the perception chain)
        "factory": factory,
        "bind": bind,
        "provides": ("K.columnar.body", "K.columnar.bandwidths"),
        "requires": {"hard": {}},
        "report_key": "columnar",
        "snapshot_label": "columnar",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
