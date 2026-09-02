# -*- coding: utf-8 -*-
"""K.binder — cognition-domain kernel module (Station 3: scene binder, 7.3)

Role:
  - bind <=2 perceptual fragments into 1 perceptual scene: same object -> bind; internal-external resonance -> bind; neither -> take the most urgent
  - theme judgment: priority-table scan (attachment/threat/separation/status...)"""
from __future__ import annotations
from typing import Any, Dict, List
 
from ..infrastructure import DecisionLog
from .constants import (MATRIX_INTERNAL_PHYSICAL, MATRIX_INTERNAL_PERCEPTUAL,
                        MATRIX_EXTERNAL_PHYSICAL, MATRIX_EXTERNAL_PERCEPTUAL)
from .models import CognitiveFragment, PerceptionScene
 
 
class BinderEngine:
    """scene binder: integrates perceptual fragments into one scene with theme, urgency, and attribution."""
 
    _THEME_PRIORITY = (                                             # theme priority (first come, first served)
        "attachment figure present", "sudden threat", "social threat",
        "separation", "status challenge", "competitive rivalry",
        "warm interaction", "physical discomfort", "excretion pressure",
        "system load", "novel exploration")
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self._theme_history: List[str] = []                         # theme history (<=4, cross-tick fact)
 
    # ---- binding main flow (legacy compatibility surface) ----
    def bind_scene(self, tick: int, fragments: List[CognitiveFragment]) -> PerceptionScene:
        scene_id = f"SCN-{tick:04d}"
        if not fragments:                                           # empty fragment -> default scan scene
            return PerceptionScene(scene_id=scene_id,
                                   integrated_theme="default_scan_mode",
                                   source_attribution="default_scan_mode")
        bound = list(fragments)
        if len(fragments) == 2:                                     # dual-fragment binding judgment
            a, b = fragments
            same_object = a.signal.target and a.signal.target == b.signal.target
            echo = self._internal_external_echo(a, b)
            if not (same_object or echo):
                bound = [max(fragments, key=lambda f: f.urgency)]   # no association -> take the most urgent
        theme = self._theme_of(bound)
        scene = PerceptionScene(
            scene_id=scene_id,
            perception_fragments=bound,
            integrated_theme=theme,
            urgency=max(f.urgency for f in bound),
            source_attribution=self._attribution(bound))
        self.log.record(tick, "biomimetic.binder", "binding",
                        f"{theme} | urgency={scene.urgency} | {scene.source_attribution}")
        return scene
 
    def _internal_external_echo(self, a: CognitiveFragment, b: CognitiveFragment) -> bool:
        """internal-external resonance: external perception x internal somatic pairing."""
        pair = {a.signal.quadrant, b.signal.quadrant}
        return pair == {MATRIX_EXTERNAL_PERCEPTUAL, MATRIX_INTERNAL_PHYSICAL}
 
    def _theme_of(self, fragments: List[CognitiveFragment]) -> str:
        hints = [f.signal.theme_hint for f in fragments if f.signal.theme_hint]
        cats = [f.signal.category for f in fragments]
        for t in self._THEME_PRIORITY:                              # priority table scanned first
            if t in hints or t in cats:
                return t
        if hints:
            return hints[0]
        if "endogenous wandering" in cats or "environmental scanning" in cats:
            return "default_scan_mode"
        return "daily chores"
 
    def _attribution(self, fragments: List[CognitiveFragment]) -> str:
        external = any(f.signal.quadrant in (MATRIX_EXTERNAL_PHYSICAL,
                                             MATRIX_EXTERNAL_PERCEPTUAL)
                       for f in fragments)
        internal = any(f.signal.quadrant in (MATRIX_INTERNAL_PHYSICAL,
                                             MATRIX_INTERNAL_PERCEPTUAL)
                       for f in fragments)
        if external and internal:
            return "mixed"
        if external:
            return "external"
        if internal:
            return "internal"
        return "default_scan_mode"
 
    # ================= P3 hook (V8 module surface) =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        scene = self.bind_scene(tick, data.get("fragments", ()))
        data["scene"] = scene                                       # -> emotion generation / decision chain
        self._theme_history.append(scene.integrated_theme)
        self._theme_history = self._theme_history[-4:]              # keep only the last 4 ticks
        self._board.batch_publish({
            "K.binder.scene": {"theme": scene.integrated_theme,
                               "urgency": scene.urgency,
                               "attribution": scene.source_attribution},
            "sys.last_scene_themes": tuple(self._theme_history[:-1]),  # last tick and earlier (contract key)
        })
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"theme_history": list(self._theme_history)}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if isinstance(snap, dict) and isinstance(snap.get("theme_history"), list):
            self._theme_history = list(snap["theme_history"])[-4:]
 
    def smoke(self) -> bool:
        return isinstance(self._theme_history, list)
 
    def invariants(self) -> bool:
        return len(self._theme_history) <= 4
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"last_theme": self._theme_history[-1] if self._theme_history else ""}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> BinderEngine:
        engine = BinderEngine(ctx.log)
        engine._board = ctx.board
        ctx.k.binder = engine                                       # backfill kernel ports
        return engine
 
    def bind(inst: BinderEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P3_cognition": inst.on_cognition,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.binder",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.last_scene_themes",),                # contract keys committed for write
        "gear": {
            "P3_cognition": {"every": 1, "trigger": None},          # 1:1 always-on (downstream depends on the scene)
        },
        "priorities": {"P3_cognition": 30},                         # after interpretation, before emotion
        "factory": factory,
        "bind": bind,
        "provides": ("K.binder.scene",),
        "requires": {},
        "report_key": "binder",
        "snapshot_label": "binder",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
