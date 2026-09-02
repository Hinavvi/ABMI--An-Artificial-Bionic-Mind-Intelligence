# -*- coding: utf-8 -*-
"""M6.odp — cognition-domain DLC (disposition conflict detection: ABMI 1.0 re-engineering of legacy odp.py)

Role:
  - dormant by default; woken by five trigger kinds (direction-value change / external stimulus touching a conflict direction /
    two consecutive contradictory behavior strategies / state cache...)"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
 
# predefined conflict direction pairs (21 pairs, index distance 8~10): within-AB / within-BC / cross-domain opposition
ODP_CONFLICT_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("A01", "A09"), ("A02", "A10"), ("A03", "A11"), ("A05", "A13"),
    ("A06", "A14"), ("A07", "A15"), ("A08", "A16"),
    ("B17", "B25"), ("B18", "B26"), ("B19", "B27"), ("B20", "B28"),
    ("B21", "B29"),
    ("C33", "C41"), ("C34", "C42"), ("C35", "C43"), ("C36", "C44"),
    ("D49", "D57"), ("D50", "D58"), ("D51", "D59"), ("D53", "D61"),
    ("D55", "D63"),
)
ODP_CONFLICT_VALUE_MIN = 2.5    # both direction values >= 2.5 for a fracture to be possible
ODP_CONFLICT_DIFF_MAX = 1.0     # and difference <= 1.0
# fracture grading: (distance lower bound, distance upper bound, difference upper bound, grade)
ODP_CONFLICT_GRADES = (
    (9.5, 64.0, 0.05, "severe"),
    (8.5, 9.5, 0.5, "moderate"),
    (8.0, 8.5, 1.0, "mild"),
)
_ODP_MARK_ORDER = {"mild": 1, "moderate": 2, "severe": 3}
 
 
class DispositionConflictDetector:
    """M6 disposition conflict detection: wake-detect-sleep; pure local computation."""
 
    def __init__(self, log: Any, odp: Any) -> None:
        self.log = log
        self._odp = odp                                           # kernel ODP port
        self.dormant = True
        self.last_events: List[Dict[str, Any]] = []
        self._wake_requests: List[Tuple[str, Optional[tuple]]] = []
 
    @staticmethod
    def _index(direction_id: str) -> int:
        return int(direction_id[1:])
 
    # ---- wake entry (service port m6.detect enqueue; gear hook executes) ----
    def request_wake(self, trigger: str, context_pairs: tuple = None) -> None:
        self._wake_requests.append((str(trigger), context_pairs))
 
    def wake_and_detect(self, tick: int, trigger: str,
                        context_pairs: tuple = None) -> List[Dict[str, Any]]:
        """detects only situation-relevant conflict pairs; sleeps immediately after detection."""
        self.dormant = False
        pairs = context_pairs or ODP_CONFLICT_PAIRS
        events: List[Dict[str, Any]] = []
        for a, b in pairs:
            va, vb = self._odp.get(a), self._odp.get(b)
            if va < ODP_CONFLICT_VALUE_MIN or vb < ODP_CONFLICT_VALUE_MIN:
                continue
            diff = abs(va - vb)
            if diff > ODP_CONFLICT_DIFF_MAX:
                continue
            distance = abs(self._index(a) - self._index(b))
            level = self._grade(distance, diff)
            if level:
                events.append({"pair": (a, b), "level": level,
                               "value_a": va, "value_b": vb, "context": trigger})
        self.last_events = events
        self.dormant = True                                       # detection done -> sleep immediately
        if events:
            self.log.record(tick, "M6.odp", f"wake [{trigger}]",
                            [(f"{e['pair'][0]}<->{e['pair'][1]}", e["level"])
                             for e in events])
        else:
            self.log.record(tick, "M6.odp", f"wake [{trigger}]",
                            "no conflict -> dormant")
        return events
 
    @staticmethod
    def _grade(distance: float, diff: float) -> str:
        for lo, hi, dmax, level in ODP_CONFLICT_GRADES:
            if lo <= distance <= hi and diff <= dmax:
                return level
        if 8.0 <= distance < 8.5 and diff <= ODP_CONFLICT_DIFF_MAX:  # distance-8 fallback
            return "mild"
        return ""
 
    # ---- fracture-grade aggregation (K.hub/K.language read via sys.odp_mark) ----
    def current_mark(self) -> str:
        if not self.last_events:
            return ""
        return max((e["level"] for e in self.last_events),
                   key=lambda lv: _ODP_MARK_ORDER[lv])
 
    # ---- reparative experience: direction-value fine-tune -> gap widens -> fracture subsides (service port m6.repair) ----
    def repair(self, tick: int, amount: float = 0.3) -> bool:
        if not self.last_events:
            return False
        for e in self.last_events:
            a, b = e["pair"]
            if e["value_a"] >= e["value_b"]:
                self._odp.nudge(a, +amount / 2.0)
                self._odp.nudge(b, -amount / 2.0)
            else:
                self._odp.nudge(a, -amount / 2.0)
                self._odp.nudge(b, +amount / 2.0)
        self.log.record(tick, "M6.odp", "reparative fine-tuning",
                        f"direction-value gap widened +{amount}")
        self.last_events = []
        return True
 
    # ================= P3 hook =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        # scene-direct marking (data flag) also enqueues — one of the five conditions may arrive via tick data
        if data.get("odp_detect"):
            self.request_wake(str(data.get("odp_detect")),
                              data.get("odp_pairs"))
        while self._wake_requests:
            trigger, pairs = self._wake_requests.pop(0)
            events = self.wake_and_detect(tick, trigger, pairs)
            self._board.publish("M6.odp.mark", self.current_mark() or None)
            if events and self._bus is not None:                  # fracture narrative effect dispatch
                self._bus.emit("odp.conflict",
                               {"mark": self.current_mark(),
                                "pairs": [e["pair"] for e in events]},
                               source="M6.odp")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"dormant": self.dormant,
                "last_events": [dict(e, pair=list(e["pair"]))
                                for e in self.last_events],
                "wake_requests": [(t, list(p) if p else None)
                                  for t, p in self._wake_requests]}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.dormant = bool(snap.get("dormant", True))
        self.last_events = [
            dict(e, pair=tuple(e.get("pair", ("A01", "A09"))))
            for e in (snap.get("last_events") or [])]
        self._wake_requests = [
            (str(t), tuple(p) if p else None)
            for t, p in (snap.get("wake_requests") or [])]
 
    def smoke(self) -> bool:
        return isinstance(self.last_events, list)
 
    def invariants(self) -> bool:
        return self.current_mark() in ("", "mild", "moderate", "severe")
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"dormant": self.dormant, "mark": self.current_mark() or "-"}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug; instance-aware trigger injected at bind time)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    spec: Dict[str, Any] = {
        "module_id": "M6.odp",
        "version": "1.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.odp_mark",),                         # contract key committed write
        "gear": {
            "P3_cognition": {"every": 1, "trigger": None},          # rewritten at bind time
        },
        "priorities": {"P3_cognition": 50},                         # tail of the decision chain
        "provides": ("sys.odp_mark", "m6.detect", "m6.repair"),
        "requires": {},
        "report_key": "odp",
        "snapshot_label": "m6_odp",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
 
    def factory(ctx: Any) -> DispositionConflictDetector:
        engine = DispositionConflictDetector(ctx.log, ctx.k.odp)
        engine._board = ctx.board
        engine._bus = ctx.bus
        return engine
 
    def bind(inst: DispositionConflictDetector, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m6.detect", inst.request_wake)          # CNS wake entry
        ctx.services.offer("m6.repair", inst.repair)                # reparative experience entry
        # instance-aware trigger: zero-cost sleep when the wake queue is empty and no tick-data flag
        spec["gear"]["P3_cognition"]["trigger"] = (
            lambda t, d: bool(inst._wake_requests) or bool(d.get("odp_detect")))
        return {"P3_cognition": inst.on_cognition, "report": inst.report}
 
    spec["factory"] = factory
    spec["bind"] = bind
    return spec
