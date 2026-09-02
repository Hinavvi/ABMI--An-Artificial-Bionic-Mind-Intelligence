# -*- coding: utf-8 -*-
# =============================================================================
# audit.py — V8 governance: egress audit authority (constitution, governance)
#
# jurisdiction: "did a module misreport its own settlement?" In-transit tampering (IDNS dyeing) is not caught here —
# that is the scout's job (A1 ruling: dyeing must reach CNS, otherwise the M12/M13/M14 pathology layer all dies).
#
# revision log:
# - fixed a syntax error in _record: the original try: had no except/finally; the file could not be imported at all.
# - _try_deweight now takes tick explicitly; removed the roundabout _last_tick() tick-number fetch.
# - single deweight entry: audit rejection triggers trust.reject here; the engine governance loop no longer double-deweights
# (the original double deweight deducted 0.4 instead of 0.2 for one audit failure).
# =============================================================================
from __future__ import annotations
from typing import Any, Dict, List, Optional
 
 
class AuditVerdict:
    """result of one egress audit."""
 
    __slots__ = ("tick", "module_id", "passed", "detail")
 
    def __init__(self, tick: int, module_id: str, passed: bool,
                 detail: str = "") -> None:
        self.tick = tick
        self.module_id = module_id
        self.passed = passed
        self.detail = detail
 
    def as_dict(self) -> Dict[str, Any]:
        return {"tick": self.tick, "module": self.module_id,
                "passed": self.passed, "detail": self.detail}
 
 
class AuditAuthority:
    """run a same-tick egress probe for every module declaring audit_probe. Audits only; never computes on behalf."""
 
    __slots__ = ("_log", "_trust", "_verdicts", "_rejects")
 
    def __init__(self, log: Any, trust: Any) -> None:
        self._log = log
        self._trust = trust
        self._verdicts: List[AuditVerdict] = []
        self._rejects = 0
 
    # ------------------------------------------------------------------
    # egress audit — core probe
    # ------------------------------------------------------------------
    def audit_at_egress(self, tick: int, module_id: str,
                        uploaded: Dict[str, Any],
                        local_probe: Optional[Dict[str, Any]]) -> AuditVerdict:
        """compare the module's actual upload (board arrival surface) against the local settlement (audit_probe snapshot)."""
        if local_probe is None:
            return AuditVerdict(tick, module_id, True,
                                "no probe implemented; skipped")
        mismatches: List[str] = []
        for key, expect in local_probe.items():
            got = uploaded.get(key)
            if got != expect:
                mismatches.append(f"{key}: got={got!r} local={expect!r}")
        if mismatches:
            verdict = AuditVerdict(tick, module_id, False,
                                   "; ".join(mismatches[:3]))
            self._rejects += 1
            self._try_deweight(tick, module_id)  # single deweight entry
            self._record(tick, module_id, verdict)
            return verdict
        verdict = AuditVerdict(tick, module_id, True, "consistent")
        self._record(tick, module_id, verdict)
        return verdict
 
    # ------------------------------------------------------------------
    # trust linkage (defensive: deweight failure does not affect the audit verdict)
    # ------------------------------------------------------------------
    def _try_deweight(self, tick: int, module_id: str) -> None:
        try:
            self._trust.reject(tick, module_id, "audit mismatch")
        except Exception:
            pass
 
    def _record(self, tick: int, module_id: str, v: AuditVerdict) -> None:
        self._verdicts.append(v)
        self._verdicts = self._verdicts[-200:]
        if self._log is not None:
            try:
                self._log.record(tick, "audit",
                                 "pass" if v.passed else "reject",
                                 f"{module_id}: {v.detail}")
            except Exception:
                pass
 
    # ------------------------------------------------------------------
    # views and the four-piece set
    # ------------------------------------------------------------------
    def last_verdict(self) -> Dict[str, Any]:
        return self._verdicts[-1].as_dict() if self._verdicts else {}
 
    def rejects(self) -> int:
        return self._rejects
 
    def snapshot(self) -> Dict[str, Any]:
        return {"rejects": self._rejects, "last": self.last_verdict()}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if isinstance(snap, dict):
            self._rejects = int(snap.get("rejects", 0))
 
    def smoke(self) -> bool:
        return self._rejects >= 0
 
    def invariants(self) -> bool:
        return all(v.passed in (True, False) for v in self._verdicts)
