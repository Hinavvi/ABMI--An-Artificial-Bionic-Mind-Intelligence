# -*- coding: utf-8 -*-
"""M15.outpost — boundary-domain DLC (conduction block: outpost-network border check & echo channel; ABMI 1.0 re-engineering of legacy outpost.py)

Role: the border checkpoint for IDNS forged packets. Outpost registries at all levels are trust anchors: IDNS forged packets can pass
  CNS format"""
from __future__ import annotations
import copy
from typing import Any, Dict, List, Optional, Tuple
 
M15_PERFECT_REPAIR_PROB = 0.10          # locked: no module may modulate this value
M15_SRF_SHUTDOWN = 60.0                 # capacity cutoff: srf > 60
M15_SLEEP_DEBT_SHUTDOWN = 6.0           # capacity cutoff: sleep debt > 6h
M15_HMF_FULL = 60.0                     # full capacity: hmf > 60 for 3 consecutive ticks
M15_HMF_FULL_TICKS = 3
M15_EVENT_DENSITY_HIGH = 6              # high event density: signals this tick >= 6 (locally derived)
M15_DOUBT_BASE = 0.25                   # doubt seed -> m7.inject intensity base
M15_DOUBT_GAIN = 0.3                    # doubt seed gain
M15_FRAG_MAX = 12                       # max original-frame fragment length
_M15_PAYLOAD_STRIP = ("idns", "mimetic", "sacred", "mirror",
                      "forged", "reality_tag")
 
 
class _DelayedSignal:
    """signal object in the delay queue (carrier of snapshot restore; duck-typed to kernel signal fields)."""
    __slots__ = ("source", "type", "intensity", "category", "theme_hint",
                 "target", "urgency", "payload", "source_tag")
 
 
def _sig_to_dict(sig: Any) -> Dict[str, Any]:
    return {k: copy.deepcopy(getattr(sig, k, None)) for k in
            ("source", "type", "intensity", "category", "theme_hint",
             "target", "urgency", "payload", "source_tag")}
 
 
def _sig_from_dict(d: Dict[str, Any]) -> _DelayedSignal:
    sig = _DelayedSignal()
    for k in ("source", "type", "intensity", "category", "theme_hint",
              "target", "urgency", "payload", "source_tag"):
        setattr(sig, k, copy.deepcopy(d.get(k)))
    return sig
 
 
class OutpostConnection:
    """echo calibration from CNS to the PNS<->CNS boundary, synchronized by the root hub."""
 
    PERFECT_REPAIR_PROB = M15_PERFECT_REPAIR_PROB   # locked: not modulatable
 
    def __init__(self, rng: Any, log: Any) -> None:
        self.rng = rng
        self.log = log
        self._delayed: List[Any] = []
        self._last_events: List[Dict[str, Any]] = []
        self._no_repair_ticks: Dict[Tuple[str, Any], int] = {}
        self._hmf_high_ticks: int = 0
 
    # ================= capacity arbitration =================
    def capacity(self, ctx: Dict[str, Any]) -> int:
        if float(ctx.get("srf", 0.0)) > M15_SRF_SHUTDOWN \
                or float(ctx.get("sleep_debt_h", 0.0)) > M15_SLEEP_DEBT_SHUTDOWN:
            return 0
        if float(ctx.get("hmf", 40.0)) > M15_HMF_FULL \
                and int(ctx.get("hmf_high_ticks", 0)) >= M15_HMF_FULL_TICKS:
            return 3
        if ctx.get("event_density") == "high":
            return 1
        return 2
 
    @staticmethod
    def _eligible(sig: Any) -> bool:
        payload = getattr(sig, "payload", {}) or {}
        return bool(payload.get("idns") or payload.get("mimetic")
                    or payload.get("sacred") or payload.get("mirror")
                    or payload.get("forged")
                    or payload.get("reality_tag") == "suspect"
                    or getattr(sig, "source", "") == "idns")
 
    @staticmethod
    def _fragment(sig: Any) -> str:
        theme = getattr(sig, "theme_hint", None) \
            or getattr(sig, "category", "")
        if not theme:
            return ""
        if " [sacred:" in theme:
            theme = theme.split(" [sacred:", 1)[0]
        for sep in ("/", ":", "：", " ", "·", ","):
            if sep in theme:
                return theme.split(sep)[0][:M15_FRAG_MAX]
        return theme[:M15_FRAG_MAX]
 
    # ================= delay queue =================
    def pop_delayed(self, tick: int) -> List[Any]:
        out, self._delayed = self._delayed, []
        for sig in out:
            payload = getattr(sig, "payload", None)
            if payload is not None:
                payload["arrived_late"] = True
        return out
 
    # ================= border check =================
    def inspect(self, tick: int, signals: List[Any], link: str,
                ctx: Dict[str, Any]) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """returns (deliverable signals this round, event list). Delayed signals return next tick, still tampered."""
        cap = self.capacity(ctx)
        delivered: List[Any] = []
        events: List[Dict[str, Any]] = []
        for idx, sig in enumerate(signals):
            payload = getattr(sig, "payload", None)
            if payload is None or not self._eligible(sig) \
                    or bool(payload.get("arrived_late")):
                delivered.append(sig)
                continue
            sid = str(payload.get("signal_id")
                      or f"{link}:{tick}:{idx}:{getattr(sig, 'category', '')}")
            source_tag = str(payload.get("idns")
                             or ("sacred" if payload.get("sacred")
                                 else "idns_generic"))
            if cap <= 0:
                delivered.append(sig)
                continue
            cap -= 1
            roll = self.rng.random()
            if roll < self.PERFECT_REPAIR_PROB:
                for k in _M15_PAYLOAD_STRIP:
                    payload.pop(k, None)
                payload["outpost"] = "perfect"
                events.append({"signal_id": sid, "link": link,
                               "mode": "perfect", "source_tag": source_tag,
                               "target": getattr(sig, "target", None),
                               "repaired_span": "", "doubt_seed": 1.0,
                               "visible_cue": "clear_flash"})
                delivered.append(sig)
                self.log.record(tick, "M15.Outpost", "beachhead",
                                f"{sid} genuine frame landed first")
                continue
            frag = self._fragment(sig)
            if frag:
                payload["outpost"] = "patch_word"
                payload["repaired_span"] = frag
                events.append({"signal_id": sid, "link": link,
                               "mode": "patch_word", "source_tag": source_tag,
                               "target": getattr(sig, "target", None),
                               "repaired_span": frag, "doubt_seed": 0.45,
                               "visible_cue": "word_glitch"})
                delivered.append(sig)   # semantics remain tampered; only one phase fragment leaks through
                self.log.record(tick, "M15.Outpost", "frame aliasing",
                                f"{sid} leaked the original fragment [{frag}]")
            else:
                key = (sid, getattr(sig, "target", None))
                last = self._no_repair_ticks.get(key, -99)
                if tick - last <= 1 or getattr(sig, "urgency", False):
                    delivered.append(sig)   # anti-deadlock / physiological limit: never delayed twice in a row
                    continue
                self._no_repair_ticks[key] = tick
                stalled = copy.deepcopy(sig)
                sp = getattr(stalled, "payload", None)
                if sp is not None:
                    sp["delay_ticks"] = 1
                    sp["stagnation_flag"] = True
                self._delayed.append(stalled)
                events.append({"signal_id": sid, "link": link,
                               "mode": "stagnation", "source_tag": source_tag,
                               "target": getattr(sig, "target", None),
                               "repaired_span": "", "doubt_seed": 0.25,
                               "visible_cue": "lag_one_tick"})
                self.log.record(tick, "M15.Outpost", "delay",
                                f"{sid} delayed by 1 TICK")
        self._last_events = events
        return delivered, events
 
    # ================= hook: P2 border check (delayed return -> inspection -> doubt seed) =================
    def on_boundary(self, tick: int, data: Dict[str, Any]) -> None:
        signals = data.setdefault("signals", [])
        delayed = self.pop_delayed(tick)
        if delayed:
            signals[:0] = delayed                       # late packets returned to the front
        eff = (self._k.hormones.compute_effective_levels()
               if self._k.hormones is not None else {})   # kernel-absent guard (A1 revision)
        hmf = float(eff.get("SM_HMF", 40.0))
        self._hmf_high_ticks = (self._hmf_high_ticks + 1
                                if hmf > M15_HMF_FULL else 0)
        ctx = {"srf": float(eff.get("SM_SRF", 0.0)),
               "hmf": hmf,
               "hmf_high_ticks": self._hmf_high_ticks,
               "sleep_debt_h": (float(self._k.sleep.sleep_debt_hours)
                                if self._k.sleep is not None else 0.0),
               "event_density": ("high" if len(signals)
                                 >= M15_EVENT_DENSITY_HIGH else "normal")}
        delivered, events = self.inspect(tick, signals, "up", ctx)
        data["signals"] = delivered
        for ev in events:
            if ev["doubt_seed"] > 0 and self._services is not None:
                self._services.call(
                    "m7.inject", tick, "chaos_gap",
                    "something felt wrong just now",
                    intensity=M15_DOUBT_BASE + M15_DOUBT_GAIN * ev["doubt_seed"],
                    valence=-0.1, source="chaos", layer="preconscious",
                    linkage_tags=["fissure", ev["source_tag"]], default=None)
 
    # ================= report =================
    def report(self) -> Dict[str, Any]:
        if not self._last_events:
            return {"state": "passthrough/dormant",
                    "delayed": len(self._delayed)}
        return {"events": [dict(e) for e in self._last_events],
                "delayed": len(self._delayed),
                "dominant_cue": self._last_events[0]["visible_cue"]}
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"delayed": [_sig_to_dict(s) for s in self._delayed],
                "last_events": [dict(e) for e in self._last_events],
                "no_repair_ticks": {str(k): v
                                    for k, v in self._no_repair_ticks.items()},
                "hmf_high_ticks": self._hmf_high_ticks,
                "rng": self.rng.snapshot()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self._delayed = [_sig_from_dict(d)
                         for d in (snap.get("delayed") or [])]
        self._last_events = [dict(e)
                             for e in (snap.get("last_events") or [])]
        nrt: Dict[Tuple[str, Any], int] = {}
        for k, v in (snap.get("no_repair_ticks") or {}).items():
            # keys are the serialized form str((sid, target)); decoded back into a pair
            try:
                sid, target = eval(k, {"__builtins__": {}}, {})  # literals only
            except Exception:
                continue
            nrt[(sid, target)] = int(v)
        self._no_repair_ticks = nrt
        self._hmf_high_ticks = int(snap.get("hmf_high_ticks", 0))
        if isinstance(snap.get("rng"), dict):
            self.rng.restore(snap["rng"])
 
    def smoke(self) -> bool:
        return len(self._delayed) >= 0 and self._hmf_high_ticks >= 0
 
    def invariants(self) -> bool:
        return (len(self._delayed) >= 0
                and self._hmf_high_ticks >= 0
                and all(int(v) >= 0
                        for v in self._no_repair_ticks.values()))
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> OutpostConnection:
        conn = OutpostConnection(ctx.rng_for("outpost"), ctx.log)
        conn._k = ctx.k
        conn._services = ctx.services
        return conn
 
    def bind(inst: OutpostConnection, ctx: Any) -> Dict[str, Any]:
        return {
            "P2_boundary": inst.on_boundary,
            "report": inst.report,
        }
 
    return {
        "module_id": "M15.outpost",
        "version": "1.0",
        "zone": "boundary",                                         # boundary domain (border check)
        "contract_keys": (),
        "gear": {
            "P2_boundary": {"every": 1, "trigger": None},
        },
        "priorities": {"P2_boundary": 20},                          # after IDNS P2-15
        "factory": factory,
        "bind": bind,
        "provides": (),
        "requires": {"soft": {"m7.inject": None}},
        "report_key": "outpost",
        "snapshot_label": "m15_outpost",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
