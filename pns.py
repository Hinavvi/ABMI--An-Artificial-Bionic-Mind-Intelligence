# -*- coding: utf-8 -*-
"""K.pns — physiology-domain kernel module (peripheral perception & execution layer: Chapter 4 five-piece set)

Role:
  - sensory acquisition: external stimuli -> raw signals (no semantic understanding); silence = sleep
  - skeletal muscle: execute motor directives (force after pathway compression); hold posture tone when no directives
  - state modulation factors: seven..."""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
 
from ..infrastructure import DecisionLog
from .constants import (STATE_MODULATOR_IDS, STATE_MODULATOR_TABLE,
                        MODULATOR_BASELINES, MODULATOR_SYNERGY,
                        MODULATOR_ANTAGONISTS)
from .models import PerceptionSignal, MotorActionCommand, clamp
 
 
# =============================================================================
# 4.1 sensory acquisition: external physical stimuli -> raw signal intensities (no understanding; silence = sleep)
# =============================================================================
class PeripheralSensingLayer:
    """zero coupling with skeletal muscle and modulation factors; silent when no stimuli (pushes no information flow)."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
 
    def acquire_perception_signals(self, tick: int,
                                   stimuli: Optional[list]) -> List[PerceptionSignal]:
        if not stimuli:
            return []                                               # sleep: no stimuli, no push
        signals = []
        for st in stimuli:
            signals.append(PerceptionSignal(                        # wrap each stimulus as a raw signal
                source=st.get("sense", "interoceptor"),
                type=st.get("type", "internal"),
                intensity=clamp(float(st.get("intensity", 0.5))),
                category=st.get("category", "generic"),
                theme_hint=st.get("theme_hint"),
                target=st.get("target"),
                urgency=bool(st.get("urgency", False)),
                payload={k: v for k, v in st.items()                # pass-through payload beyond the known keys
                         if k not in ("sense", "type", "intensity", "category",
                                      "theme_hint", "target", "urgency")},
            ))
        self.log.record(tick, "PNS.sensory_collection", "perception",
                        f"{len(signals)} raw signals")
        return signals
 
 
# =============================================================================
# 4.2 skeletal muscle: execute motor directives; with no directives, hold current posture tone (dormant)
# =============================================================================
class MotorExecutionLayer:
    """CNS direct drive + internal-state encoding-layer motor directives; gross-pathway directives update posture."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.posture = "relaxed standing"                           # current posture
        self.executed: List[str] = []                               # executed records
 
    def execute_motor_commands(self, tick: int,
                               commands: List[MotorActionCommand]) -> List[str]:
        if not commands:
            return []                                               # hold posture muscle tone
        done = []
        for cmd in commands:
            done.append(f"{cmd.command}(pathway={cmd.pathway}, intensity={cmd.compressed:.2f})")
            if cmd.pathway == "motor_gross":
                self.posture = cmd.command                          # gross directive changes posture
        self.executed.extend(done)
        self.log.record(tick, "PNS.skeletal_muscle", "execution", done)
        return done
 
 
# =============================================================================
# 4.3 state-modulation-factor scheduling: seven endogenous factors release / synergy / antagonism / autonomous metabolism
# =============================================================================
class StateModulatorScheduler:
    """environmental release handled as pure physiological reflex (bypassing CNS); autonomous metabolism runs in the background producing no information flow."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.levels = dict(MODULATOR_BASELINES)                     # current level
        self.baselines = dict(MODULATOR_BASELINES)                  # baseline
 
    def release_modulator(self, tick: int, hid: str, amount: float,
                          reason: str = "") -> float:
        amount = max(0.0, amount)
        self.levels[hid] = min(100.0, self.levels[hid] + amount)    # release (capped at 100)
        for partner in MODULATOR_SYNERGY.get(hid, ()):              # synergy factor +25%
            self.levels[partner] = min(100.0, self.levels[partner] + amount * 0.25)
        self.log.record(tick, "PNS.state_modulator", "release",
                        f"{STATE_MODULATOR_TABLE[hid]['name']}+{amount:.1f} "
                        f"→ {self.levels[hid]:.1f} {reason}")
        return self.levels[hid]
 
    def environmental_modulator_release(self, tick: int, hid: str,
                                        amount: float, reason: str = "") -> float:
        return self.release_modulator(tick, hid, amount,
                                      reason=f"[environmental reflex] {reason}")
 
    def metabolic_decay(self, dt_minutes: float) -> None:
        """autonomous metabolism: exponential decay toward baseline by half-life (background, no information flow)."""
        for hid in STATE_MODULATOR_IDS:
            hl = STATE_MODULATOR_TABLE[hid]["half_life_min"]
            base = self.baselines[hid]
            self.levels[hid] = base + (self.levels[hid] - base) * (0.5 ** (dt_minutes / hl))
 
    def level(self, hid: str) -> float:
        return self.levels[hid]
 
    def compute_effective_levels(self) -> Dict[str, float]:
        """effective level after antagonism (4.3 antagonism table: subtract antagonist sum x0.5)."""
        eff = dict(self.levels)
        for hid, antagonists in MODULATOR_ANTAGONISTS.items():
            suppress = sum(self.levels[a] for a in antagonists) * 0.5
            eff[hid] = max(0.0, self.levels[hid] - suppress)
        return eff
 
    def set_baseline(self, hid: str, v: float) -> None:
        self.baselines[hid] = clamp(v, 0.0, 100.0)
 
    def reset_to_baseline(self, hid: str) -> None:
        self.levels[hid] = self.baselines[hid]
 
 
# =============================================================================
# 4.4 sleep-rhythm regulation (S-pressure + C-rhythm two-process model)
# =============================================================================
class ResourceSchedulerAndStateReset:
    """PNS accumulates sleep pressure; CNS decides whether to enter state reset; vetoes lower the threshold, debt accumulates."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.wake_minutes = 6.0 * 60.0      # awake duration (starts in the morning by default)
        self.sleep_debt_hours = 0.0         # sleep debt
        self.veto_count = 0                 # CNS veto count
        self.phase_shift_hours = 0.0        # C-rhythm phase delay (+0.5h per consecutive all-nighter)
        self.asleep = False                 # whether in state reset
        self.base_threshold = 0.75          # sleepiness threshold baseline
        self.last_quality = 1.0             # last reset quality
        self.s_pressure_mult = 1.0          # M3 CIdx accelerates S-pressure accumulation (knob injection)
 
    def compute_resource_pressure(self) -> float:
        """S pressure: awake-duration driven, nonlinear rise + debt bonus."""
        h = self.wake_minutes / 60.0
        curve = clamp((max(0.0, h - 3.0) / 16.0) ** 1.5)
        return clamp((curve + 0.03 * self.sleep_debt_hours) * self.s_pressure_mult)
 
    def compute_circadian_rhythm(self, hour_of_day: float) -> float:
        """C rhythm: 24h sine, 2-4 AM trough, 2-4 PM peak."""
        t = (hour_of_day - 9.0 - self.phase_shift_hours) % 24.0
        return 0.5 + 0.5 * math.sin(2.0 * math.pi * t / 24.0)
 
    def compute_system_fatigue(self, hour_of_day: float) -> float:
        """sleepiness = S pressure x0.7 + (1-C rhythm) x0.3."""
        return (self.compute_resource_pressure() * 0.7
                + (1.0 - self.compute_circadian_rhythm(hour_of_day)) * 0.3)
 
    def threshold(self) -> float:
        return max(0.30, self.base_threshold - 0.09 * self.veto_count)  # veto lowers the threshold (floor 0.30)
 
    def can_enter_reset_state(self, hour_of_day: float) -> bool:
        return self.compute_system_fatigue(hour_of_day) > self.threshold()
 
    def veto_reset_state(self, tick: int) -> None:
        self.veto_count += 1
        self.sleep_debt_hours += 0.5
        self.log.record(tick, "PNS.sleep_rhythm", "veto",
                        f"veto #{self.veto_count} -> threshold {self.threshold():.2f}")
 
    def check_forced_reset(self, c5_stress_level: float,
                           c5_stress_minutes: float) -> Optional[str]:
        """four forced-reset conditions (returns the reason if any is met, else None)."""
        s = self.compute_resource_pressure()
        if s > 0.95 and self.veto_count > 5:
            return "S pressure>0.95 and vetoes>5"
        if self.sleep_debt_hours > 12.0:
            return "sleep_debt>12h"
        if self.wake_minutes > 24.0 * 60.0:
            return "awake>24h"
        if c5_stress_level >= 3.0 and c5_stress_minutes >= 30.0:
            return "PSM_D5 stress>=3 for 30min"
        return None
 
    def update(self, dt_minutes: float) -> None:
        if not self.asleep:
            self.wake_minutes += dt_minutes                          # accumulated only while awake
 
    def overnight_shift(self) -> None:
        self.phase_shift_hours += 0.5                                # consecutive all-nighters shift the phase later
 
    def settle_after_reset(self, tick: int, duration_hours: float,
                           quality: float) -> Dict[str, Any]:
        """sleep-wake settlement: S pressure cleared, debt repaid, veto count cleared."""
        self.last_quality = clamp(quality)
        debt_paid = duration_hours * self.last_quality
        self.sleep_debt_hours = max(0.0, self.sleep_debt_hours - debt_paid)
        self.wake_minutes = 0.0
        self.veto_count = 0
        self.asleep = False
        settlement = {"debt_paid": round(debt_paid, 2),
                      "debt_remaining": round(self.sleep_debt_hours, 2),
                      "quality": self.last_quality}
        self.log.record(tick, "PNS.sleep_rhythm", "wake settlement", settlement)
        return settlement
 
    def state(self, hour_of_day: float) -> Dict[str, Any]:
        return {"S": round(self.compute_resource_pressure(), 3),
                "C": round(self.compute_circadian_rhythm(hour_of_day), 3),
                "sleepiness": round(self.compute_system_fatigue(hour_of_day), 3),
                "threshold": round(self.threshold(), 2),
                "debt_h": round(self.sleep_debt_hours, 1),
                "vetoes": self.veto_count}
 
 
# =============================================================================
# 4.5 discharge-pressure accumulation (M2 PNS side: liquid/solid content fullness, capacity weighted by height/weight)
# =============================================================================
class DischargePressureAccumulator:
    """background resident continuous accumulation, producing no information-flow signals — enters perception competition after encoding by the internal-state encoding layer."""
 
    BASE_RATE_LIQUID = 1.0 / 240.0   # liquid fullness rate: full in ~4h
    BASE_RATE_SOLID = 1.0 / 720.0    # solid fullness rate: full in ~12h
 
    def __init__(self, log: DecisionLog,
                 body_metrics: Optional[dict] = None) -> None:
        self.log = log
        bm = body_metrics or {}
        sex = bm.get("sex", "M")
        h0, w0 = (172.0, 70.0) if sex == "M" else (165.0, 55.0)     # reference build
        h = float(bm.get("height_cm", h0))
        w = float(bm.get("weight_kg", w0))
        capacity = 1.0 + (h - h0) / 10.0 * 0.01 + (w - w0) / 8.0 * 0.01
        self.capacity_mult = max(0.5, capacity)                     # capacity rate (larger = fills slower)
        self.liquid = 0.15                                          # initial liquid fullness
        self.solid = 0.10                                           # initial solid fullness
        self.liquid_rate_mult = 1.0                                 # intake/load modulation (knob injection)
        self.solid_rate_mult = 1.0
 
    def accumulate(self, dt_minutes: float) -> None:
        self.liquid = clamp(self.liquid + self.BASE_RATE_LIQUID
                            * self.liquid_rate_mult * dt_minutes / self.capacity_mult)
        self.solid = clamp(self.solid + self.BASE_RATE_SOLID
                           * self.solid_rate_mult * dt_minutes / self.capacity_mult)
 
    def relieve(self, kind: str) -> float:
        """discharge completed: cleared and returns the pre-discharge peak (for SM_PIF pulse judgment)."""
        if kind == "liquid":
            peak, self.liquid = self.liquid, 0.0
        else:
            peak, self.solid = self.solid, 0.0
        return peak
 
    def state(self) -> Dict[str, float]:
        return {"liquid": round(self.liquid, 3), "solid": round(self.solid, 3),
                "capacity_mult": round(self.capacity_mult, 3)}
 
 
# =============================================================================
# PnsEngine — V8 module shell: P1 per-tick body / P5 draining / sleep-settlement service
# =============================================================================
class PnsEngine:
    """beat orchestration of the peripheral five-piece set: P1 acquisition+metabolism+mirror publish; P5 draining (dormancy-first)."""
 
    def __init__(self, log: DecisionLog, body_metrics: Optional[dict]) -> None:
        self.log = log
        self.senses = PeripheralSensingLayer(log)                   # 4.1 senses
        self.muscles = MotorExecutionLayer(log)                     # 4.2 skeletal muscle
        self.hormones = StateModulatorScheduler(log)                # 4.3 modulation factors
        self.sleep = ResourceSchedulerAndStateReset(log)            # 4.4 sleep rhythm
        self.discharge = DischargePressureAccumulator(log, body_metrics)  # 4.5 discharge pressure
 
    # ---- P1 body-phase hook (every tick) ----
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board                                         # injected at install time
        dt = float(data.get("dt", 0.0))
        data["signals"] = self.senses.acquire_perception_signals(   # stimuli -> raw signals
            tick, data.get("stimuli"))
        self.hormones.metabolic_decay(dt)                           # autonomous metabolism
        self.discharge.accumulate(dt)                               # fullness accumulation
        self.sleep.update(dt)                                       # awake-duration accumulation
        # DLC modulation knobs (unwritten = neutral default; unplugged and still runs)
        self.sleep.s_pressure_mult = float(board.read_knob("knob.s_pressure_mult", 1.0))
        self.discharge.liquid_rate_mult = float(board.read_knob("knob.liquid_rate_mult", 1.0))
        self.discharge.solid_rate_mult = float(board.read_knob("knob.solid_rate_mult", 1.0))
        hour = float(board.read("sys.hour", 8.0))                   # engine-published world clock
        body = board.read("K.columnar.body", {}) or {}              # last tick's body report (forced-reset judgment)
        forced = self.sleep.check_forced_reset(
            float(body.get("stress_level", 0.0)),
            float(board.read("K.columnar.c5_stress_minutes", 0.0)))
        if forced and not self.sleep.asleep:
            data["forced_sleep"] = forced                           # hand over to the decision chain
            self._bus.emit("sleep.forced", {"reason": forced}, source="K.pns")
        board.batch_publish({                                       # three mirrors (downstream read-only)
            "K.pns.hormones": self.hormones.compute_effective_levels(),
            "K.pns.discharge": self.discharge.state(),
            "K.pns.sleep": {**self.sleep.state(hour), "asleep": self.sleep.asleep},
        })
 
    # ---- P5 deposit-phase hook (draining: wakes only when there's work) ----
    def on_deposit(self, tick: int, data: Dict[str, Any]) -> None:
        for hid, amount, reason in data.get("hormone_requests", ()):  # column -> factor release
            self.hormones.release_modulator(tick, hid, amount, reason)
        for kind, _peak in data.get("discharge_events", ()):          # discharge completed -> cleared
            self.discharge.relieve(kind)
        commands = data.get("motor_commands", ())                     # compressed motor directives
        if commands:
            self.muscles.execute_motor_commands(tick, commands)
 
    # ---- sleep-settlement service (external trigger: consciousness layer / scene side calls via service port) ----
    def svc_settle_sleep(self, tick: int, duration_hours: float,
                         quality: float) -> Dict[str, Any]:
        settlement = self.sleep.settle_after_reset(tick, duration_hours, quality)
        self._bus.emit("sleep.settle", {"tick": tick, "quality": quality,
                                        "duration_h": duration_hours},
                       source="K.pns")                                # subscribers: memory consolidation / nine-column reset
        return settlement
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {
            "hormone_levels": dict(self.hormones.levels),
            "hormone_baselines": dict(self.hormones.baselines),
            "sleep": {"wake_minutes": self.sleep.wake_minutes,
                      "sleep_debt_hours": self.sleep.sleep_debt_hours,
                      "veto_count": self.sleep.veto_count,
                      "phase_shift_hours": self.sleep.phase_shift_hours,
                      "asleep": self.sleep.asleep,
                      "last_quality": self.sleep.last_quality},
            "discharge": {"liquid": self.discharge.liquid, "solid": self.discharge.solid},
            "posture": self.muscles.posture,
        }
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        if isinstance(snap.get("hormone_levels"), dict):
            self.hormones.levels.update(snap["hormone_levels"])     # write back levels
        if isinstance(snap.get("hormone_baselines"), dict):
            self.hormones.baselines.update(snap["hormone_baselines"])
        s = snap.get("sleep")
        if isinstance(s, dict):
            for key, value in s.items():                            # field-by-field sleep write-back
                setattr(self.sleep, key, value)
        d = snap.get("discharge")
        if isinstance(d, dict):
            self.discharge.liquid = clamp(float(d.get("liquid", 0.0)))
            self.discharge.solid = clamp(float(d.get("solid", 0.0)))
        if snap.get("posture"):
            self.muscles.posture = str(snap["posture"])
 
    def smoke(self) -> bool:
        return all(unit is not None for unit in
                   (self.senses, self.muscles, self.hormones,
                    self.sleep, self.discharge))
 
    def invariants(self) -> bool:
        return (all(0.0 <= v <= 100.0 for v in self.hormones.levels.values())
                and 0.0 <= self.discharge.liquid <= 1.0
                and 0.0 <= self.discharge.solid <= 1.0
                and self.sleep.wake_minutes >= 0.0
                and self.sleep.sleep_debt_hours >= 0.0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"posture": self.muscles.posture,
                "discharge": self.discharge.state()}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> PnsEngine:
        engine = PnsEngine(ctx.log, ctx.k.card.body_metrics)        # build comes from the persona card
        engine._board = ctx.board                                   # for in-hook board reads
        engine._bus = ctx.bus                                       # for event emission
        # backfill five kernel ports (legacy DLCs access the originals via ctx.k.*)
        ctx.k.senses = engine.senses
        ctx.k.muscles = engine.muscles
        ctx.k.hormones = engine.hormones
        ctx.k.sleep = engine.sleep
        ctx.k.discharge = engine.discharge
        return engine
 
    def bind(inst: PnsEngine, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("pns.settle_sleep", inst.svc_settle_sleep)  # sleep-settlement service
        return {
            "P1_body": inst.on_body,
            "P5_deposit": inst.on_deposit,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.pns",
        "version": "8.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P1_body": {"every": 1, "trigger": None},               # 1:1 always-on (body every tick)
            "P5_deposit": {"every": 1, "trigger": lambda t, d: bool(  # wakes only when there's work
                d.get("hormone_requests") or d.get("motor_commands")
                or d.get("discharge_events"))},
        },
        "priorities": {"P1_body": 0, "P5_deposit": 10},
        "factory": factory,
        "bind": bind,
        "provides": ("K.pns.hormones", "K.pns.discharge", "K.pns.sleep"),
        "requires": {},
        "report_key": "pns",
        "snapshot_label": "pns",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
