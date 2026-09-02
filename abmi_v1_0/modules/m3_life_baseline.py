# -*- coding: utf-8 -*-
"""M3.life_baseline — physiology-domain DLC (systemic load index CIdx: ABMI 1.0 re-engineering of legacy pathology.py)

Role:
  - CIdx time curve: acute template (latency -> acute triangular wave -> recovery) + chronic..."""
from __future__ import annotations
from typing import Any, Dict, Optional
 
CIDX_SAFE_CAP = 0.9                     # CIdx safety ceiling (non-lethal, no irreversible state)
CIDX_MEMORY_DAYS = 90.0                 # immune memory window (days)
CIDX_MEMORY_LATENT_CUT = 0.5            # memory hit: latency x0.5
CIDX_MEMORY_PEAK_CUT = 0.7              # memory hit: peak x0.7
# acute template: latency/acute/recovery (hours) + peak
CIDX_ACUTE_TEMPLATES = {
    "common_cold":  {"latent_h": 36.0, "acute_h": 48.0, "recover_h": 72.0, "peak": 0.35},
    "flu":          {"latent_h": 24.0, "acute_h": 72.0, "recover_h": 96.0, "peak": 0.6},
    "food_poisoning": {"latent_h": 6.0, "acute_h": 24.0, "recover_h": 48.0, "peak": 0.55},
    "injury":       {"latent_h": 0.5, "acute_h": 36.0, "recover_h": 120.0, "peak": 0.5},
}
# chronic template: baseline/episode interval/episode peak
CIDX_CHRONIC_TEMPLATES = {
    "chronic_fatigue": {"baseline": 0.25, "flare_interval_h": 168.0, "flare_peak": 0.5},
    "migraine":        {"baseline": 0.1, "flare_interval_h": 240.0, "flare_peak": 0.65},
    "gastritis":       {"baseline": 0.15, "flare_interval_h": 120.0, "flare_peak": 0.45},
}
 
 
class SystemicLoadIndexModule:
    """M3 CIdx: acute triangular wave + chronic episodes + immune memory; pure local computation."""
 
    def __init__(self, log: Any, declaration: dict = None) -> None:
        self.log = log
        decl = declaration or {}
        self.cidx = 0.0                                             # current CIdx
        self.baseline = 0.0                                         # chronic baseline
        self.stage = "none"                                         # stage
        self.template_name = ""
        self.elapsed_hours = 0.0
        self.memory: Dict[str, float] = {}                          # immune memory: template->trigger day
        self._day = 0.0
        self._chronic: Dict[str, float] = {}
        self._acute: Optional[Dict[str, Any]] = None
        self._flare_timer = 0.0
        chronic_name = decl.get("chronic")
        if chronic_name and chronic_name in CIDX_CHRONIC_TEMPLATES:
            self._chronic = dict(CIDX_CHRONIC_TEMPLATES[chronic_name])
            self.baseline = self._chronic["baseline"]
            self.cidx = self.baseline
            self.template_name = chronic_name
            self.stage = "chronic baseline"
        if decl.get("acute"):
            self.trigger_acute(0, decl["acute"])
 
    @property
    def active(self) -> bool:
        return self.stage != "none" or bool(self._chronic)
 
    # ---- acute trigger (service port m3.trigger_acute) ----
    def trigger_acute(self, tick: int, template_name: str) -> bool:
        tpl = CIDX_ACUTE_TEMPLATES.get(template_name)
        if tpl is None:
            return False
        latent, peak = tpl["latent_h"], tpl["peak"]
        if (template_name in self.memory
                and (self._day - self.memory[template_name]) <= CIDX_MEMORY_DAYS):
            latent *= CIDX_MEMORY_LATENT_CUT                        # immune memory hit
            peak *= CIDX_MEMORY_PEAK_CUT
            self.log.record(tick, "M3.cidx", "immune memory hit", template_name)
        self.memory[template_name] = self._day
        self._acute = {"latent_h": latent, "acute_h": tpl["acute_h"],
                       "recover_h": tpl["recover_h"], "peak": peak}
        self.template_name = template_name
        self.stage = "latent period"
        self.elapsed_hours = 0.0
        self.log.record(tick, "M3.cidx", "acute triggered",
                        f"{template_name} (peak {peak:.2f})")
        return True
 
    # ---- time-curve advance ----
    def advance(self, tick: int, dt_minutes: float) -> None:
        dt_h = dt_minutes / 60.0
        self._day += dt_h / 24.0
        if not self.active:
            return
        self.elapsed_hours += dt_h
        if self._acute:
            a, e = self._acute, self.elapsed_hours
            if e < a["latent_h"]:
                self.stage, level = "latent period", 0.0
            elif e < a["latent_h"] + a["acute_h"]:
                self.stage = "acute phase"                          # triangular wave: rise then fall
                prog = (e - a["latent_h"]) / a["acute_h"]
                level = a["peak"] * (1.0 - abs(2.0 * prog - 1.0))
            elif e < a["latent_h"] + a["acute_h"] + a["recover_h"]:
                self.stage = "recovery phase"
                prog = (e - a["latent_h"] - a["acute_h"]) / a["recover_h"]
                level = a["peak"] * 0.3 * (1.0 - prog)
            else:
                self._acute = None
                self.stage = "chronic baseline" if self._chronic else "none"
                level = 0.0
            self.cidx = min(CIDX_SAFE_CAP, self.baseline + level)
        elif self._chronic:
            self._flare_timer += dt_h
            if self._flare_timer >= self._chronic["flare_interval_h"]:
                self._flare_timer = 0.0                             # chronic acute episode
                self.cidx = min(CIDX_SAFE_CAP, self._chronic["flare_peak"])
                self.stage = "chronic flare"
                self.log.record(tick, "M3.cidx", "chronic flare",
                                f"CIdx={self.cidx:.2f}")
            else:                                                   # regress toward baseline
                self.cidx += (self.baseline - self.cidx) * 0.05 * dt_h
                self.stage = "chronic baseline"
 
    # ---- soft coupling (M5 social pressure / M8 somatization) ----
    def apply_baseline_bias(self, bias: float) -> None:
        if bias:
            self.baseline = min(CIDX_SAFE_CAP * 0.8, self.baseline + bias)
 
    def apply_somatization(self, burden: float) -> None:
        if burden > 0.05:                                           # somatization pushes the baseline (tidal)
            target = min(CIDX_SAFE_CAP * 0.7, self.baseline + burden * 0.25)
            self.baseline += (target - self.baseline) * 0.02
 
    # ================= P1 hook =================
    def on_body(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        self.advance(tick, float(data.get("dt", 0.0)))
        bias = board.read("M5.governor.baseline_bias", 0.0)         # M5 soft coupling
        if bias:
            self.apply_baseline_bias(float(bias))
        if self._services is not None:
            burden = self._services.call("m8.somatization_burden", default=None)
            if burden is not None:
                self.apply_somatization(float(burden))
        board.publish("sys.cognitive_index", self.cidx)             # contract key published directly
        # modulation vector: shared channel rebuilt every tick (anti-accumulation), merging M1/M5 archived components
        m1v = float(board.read_knob("knob.m1.valence_bias", 0.0))   # M1 cyclic component
        m5c = float(board.read_knob("knob.m5.valence_contrib", 0.0))  # M5 social-status component
        board.write_knob("knob.s_pressure_mult", 1.0 + self.cidx, owner="M3.cidx")
        board.write_knob("knob.valence_bias", m1v + m5c - self.cidx * 0.3,
                         owner="M3.cidx")
        board.write_knob("knob.m3.pain_bias", 0.5 * self.cidx, owner="M3.cidx")
        board.write_knob("knob.m3.ssm_baseline_bias", self.cidx * 20.0, owner="M3.cidx")
        board.write_knob("knob.m3.temp_bias",
                         self.cidx * 0.3 if self.stage == "acute phase"
                         else -self.cidx * 0.1, owner="M3.cidx")
        # legacy modulation-vector remainder (archived soft key; cognitive sensitivity is now carried by contract key sys.cognitive_index)
        board.write_knob("knob.m3.cognitive_mult", 1.0 - self.cidx * 0.5,
                         owner="M3.cidx")
        board.write_knob("knob.m3.social_weight_mult", 1.0 - self.cidx,
                         owner="M3.cidx")
        board.write_knob("knob.m3.memory_r_mult", 1.0 - self.cidx * 0.3,
                         owner="M3.cidx")
        board.write_knob("knob.m3.verbosity_mult", 1.0 - self.cidx * 0.4,
                         owner="M3.cidx")
        # PSM_D1 offer (legacy psm_d1_offer: (cidx*0.5, "pathology"))
        if self._columnar is not None and self.cidx > 0.0:
            self._columnar.route_psm_d1_signal(tick, self.cidx * 0.5, "pathology")
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"cidx": self.cidx, "baseline": self.baseline,
                "stage": self.stage, "template": self.template_name,
                "elapsed": self.elapsed_hours, "memory": dict(self.memory),
                "day": self._day, "chronic": dict(self._chronic),
                "acute": dict(self._acute) if self._acute else None,
                "flare_timer": self._flare_timer}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        self.cidx = float(snap.get("cidx", 0.0))
        self.baseline = float(snap.get("baseline", 0.0))
        self.stage = str(snap.get("stage", "none"))
        self.template_name = str(snap.get("template", ""))
        self.elapsed_hours = float(snap.get("elapsed", 0.0))
        self.memory = dict(snap.get("memory") or {})
        self._day = float(snap.get("day", 0.0))
        self._chronic = dict(snap.get("chronic") or {})
        acute = snap.get("acute")
        self._acute = dict(acute) if isinstance(acute, dict) else None
        self._flare_timer = float(snap.get("flare_timer", 0.0))
 
    def smoke(self) -> bool:
        return self.cidx >= 0.0 and self.baseline >= 0.0
 
    def invariants(self) -> bool:
        return 0.0 <= self.cidx <= CIDX_SAFE_CAP and self.baseline <= CIDX_SAFE_CAP * 0.8
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"cidx": round(self.cidx, 3), "stage": self.stage,
                "template": self.template_name or "-"}
 
 
# =============================================================================
# dlc_spec — ABMI 1.0 installation spec (hot-plug)
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> SystemicLoadIndexModule:
        engine = SystemicLoadIndexModule(ctx.log, ctx.k.card.systemic_load)
        engine._board = ctx.board
        engine._services = ctx.services
        engine._columnar = ctx.k.columnar
        return engine
 
    def bind(inst: SystemicLoadIndexModule, ctx: Any) -> Dict[str, Any]:
        ctx.services.offer("m3.trigger_acute", inst.trigger_acute)  # acute trigger port
        return {
            "P1_body": inst.on_body,
            "report": inst.report,
        }
 
    return {
        "module_id": "M3.life_baseline",
        "version": "1.0",
        "zone": "physical",                                         # physiology domain
        "contract_keys": ("sys.cognitive_index",),                  # contract key committed write
        "gear": {
            "P1_body": {"every": 1, "trigger": None},
        },
        "priorities": {"P1_body": 10},                              # after PNS (0)
        "factory": factory,
        "bind": bind,
        "provides": ("sys.cognitive_index",),
        "requires": {"soft": {"M5.governor.baseline_bias": None,
                              "m8.somatization_burden": None}},
        "report_key": "cidx",
        "snapshot_label": "m3_pathology",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
    }
