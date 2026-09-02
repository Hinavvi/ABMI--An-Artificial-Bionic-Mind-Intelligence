# -*- coding: utf-8 -*-
"""K.emotion — cognition-domain kernel module (emotion state vector generator: Chapter 8)

Role:
  - internal state report + perceptual scene snapshot -> nine-label emotion tone (valence x arousal)
  - outputs only to CNS; not directly coupled with the behavior decision engine or the state cache system
  - multi-source superposition (soft...)"""
from __future__ import annotations
from typing import Any, Dict, Optional
 
from ..infrastructure import DecisionLog
from .constants import (AFFECTIVE_STATE_GRID, THEME_POLARITY_MAP,
                        SM_SRF, SM_SSM, SM_ARF, SM_HMF)
from .models import AffectiveStateEncoding, PerceptionScene, clamp
 
 
class EmotionEngine:
    """nine-label emotion-tone generation: valence band x arousal band -> AFFECTIVE_STATE_GRID lookup."""
 
    def __init__(self, log: DecisionLog) -> None:
        self.log = log
        self.last_encoding: Optional[AffectiveStateEncoding] = None  # last round's encoding
 
    # ---- main generation flow (legacy compatibility surface) ----
    def generate_affective_encoding(self, tick: int, body: Dict[str, Any],
                                    scene: PerceptionScene,
                                    valence_bias: float = 0.0,
                                    trauma_lock: Optional[tuple] = None,
                                    moral_offset: float = 0.0,
                                    iceberg_stain: float = 0.0,
                                    alcohol_amplification: float = 1.0) -> AffectiveStateEncoding:
        arousal = self._compute_activation_intensity(body)          # arousal: somatically driven
        valence = self._compute_affective_polarity(scene)           # valence: scene-theme driven
        valence += valence_bias                                     # aggregate modulation bias (M1/M3)
        sources = []
        if trauma_lock is not None:                                 # M8 trauma lock: direct override
            valence, arousal = trauma_lock
            sources.append(f"M8 lock V{valence:+.2f}A{arousal:+.2f}")
        if moral_offset:                                            # M10 moral-emotion offset
            valence += moral_offset
            sources.append(f"M10{moral_offset:+.2f}")
        if iceberg_stain:                                           # M7 subconscious dyeing (valence only)
            valence += iceberg_stain
            sources.append(f"M7 stain{iceberg_stain:+.2f}")
        if alcohol_amplification != 1.0:                            # M4 alcohol amplification (BAC>0.06)
            valence *= alcohol_amplification
            sources.append(f"M4 amplify×{alcohol_amplification:.2f}")
        valence = clamp(valence, -1.0, 1.0)
        v_band = "positive" if valence > 0.15 else ("negative" if valence < -0.15 else "neutral")
        a_band = "high" if arousal > 0.35 else ("low" if arousal < -0.15 else "mid")
        label = AFFECTIVE_STATE_GRID[(v_band, a_band)]              # nine-grid lookup
        result = AffectiveStateEncoding(valence=round(valence, 3),
                                        arousal=round(arousal, 3), label=label)
        self.last_encoding = result
        self.log.record(tick, "AffectiveStateVectorGenerator", "9-label",
                        f"V={valence:+.2f} A={arousal:+.2f} → {label}"
                        + (f" [{' '.join(sources)}]" if sources else ""))
        return result
 
    def _compute_activation_intensity(self, body: Dict[str, Any]) -> float:
        """arousal intensity: cardiopulmonary deviation / muscle tone / stress / hormones, weighted composition."""
        a = 0.0
        if body.get("heart_rate", 0) > body.get("hr_baseline", 72.0) * 1.2:
            a += 0.3
        if body.get("breath_rate", 0) > body.get("br_baseline", 14.0) * 1.3:
            a += 0.2
        if body.get("muscle_tone", 0) > 6.0:
            a += 0.2
        if body.get("stress_level", 0) >= 2.0:
            a += 0.3
        h = body.get("hormones", {}) or {}
        if h.get(SM_SRF, 0) > 40:
            a += 0.2
        if h.get(SM_SSM, 0) > 50:
            a += 0.1
        if body.get("deep_slow_breath"):
            a -= 0.2
        if h.get(SM_ARF, 0) > 40:
            a -= 0.2
        if h.get(SM_HMF, 0) > 50:
            a -= 0.2
        return clamp(a, -1.0, 1.0)
 
    def _compute_affective_polarity(self, scene: PerceptionScene) -> float:
        """valence polarity: theme polarity table; default scan mode x0.3 faded."""
        v = THEME_POLARITY_MAP.get(scene.integrated_theme, 0.0)
        if scene.source_attribution == "default_scan_mode" \
                or scene.integrated_theme == "default_scan_mode":
            v *= 0.3
        return clamp(v, -1.0, 1.0)
 
    # ================= P3 hook (V8 module surface) =================
    def on_cognition(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        scene = data["scene"]                                       # trigger guarantees non-empty
        body = board.read("K.columnar.body", {}) or {}              # same-tick body report (already published at P3 order 0)
        bac = float(board.read("sys.alcohol_bac", 0.0))
        amplification = 1.0 + bac * 0.05 if bac > 0.06 else 1.0     # M4: x(1+BAC x0.05)
        trauma_lock = None
        if board.read("sys.trauma_active", False):                  # M8: lock read only on trauma activation
            lock = board.read("M8.trauma.affect_lock")
            if isinstance(lock, (list, tuple)) and len(lock) == 2:
                trauma_lock = (float(lock[0]), float(lock[1]))
        emotion = self.generate_affective_encoding(
            tick, body, scene,
            valence_bias=float(board.read_knob("knob.valence_bias", 0.0)),
            trauma_lock=trauma_lock,
            moral_offset=float(board.read("M10.morality.valence_offset", 0.0)),
            iceberg_stain=float(board.read("M7.iceberg.tone_stain", 0.0)),
            alcohol_amplification=amplification)
        data["emotion"] = emotion                                   # -> decision chain / memory encoding
        board.batch_publish({
            "K.emotion.state": {"valence": emotion.valence,
                                "arousal": emotion.arousal,
                                "label": emotion.label},
            "sys.prev_scene_valence": emotion.valence,              # contract keys: cross-tick facts
        })
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        if self.last_encoding is None:
            return {}
        return {"valence": self.last_encoding.valence,
                "arousal": self.last_encoding.arousal,
                "label": self.last_encoding.label}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if isinstance(snap, dict) and "label" in snap:
            self.last_encoding = AffectiveStateEncoding(
                valence=float(snap["valence"]),
                arousal=float(snap["arousal"]),
                label=str(snap["label"]))
 
    def smoke(self) -> bool:
        return True                                                 # no required state
 
    def invariants(self) -> bool:
        if self.last_encoding is None:
            return True
        return (-1.0 <= self.last_encoding.valence <= 1.0
                and -1.0 <= self.last_encoding.arousal <= 1.0)
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        if self.last_encoding is None:
            return {"label": "neutral"}
        return {"label": self.last_encoding.label,
                "valence": self.last_encoding.valence,
                "arousal": self.last_encoding.arousal}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> EmotionEngine:
        engine = EmotionEngine(ctx.log)
        engine._board = ctx.board
        ctx.k.emotion_gen = engine                                  # backfill kernel ports
        return engine
 
    def bind(inst: EmotionEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P3_cognition": inst.on_cognition,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.emotion",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": ("sys.prev_scene_valence",),               # contract keys committed for write
        "gear": {
            "P3_cognition": {"every": 1,
                             "trigger": lambda t, d: d.get("scene") is not None},  # no scene -> sleep
        },
        "priorities": {"P3_cognition": 40},                         # after binding, before decision
        "factory": factory,
        "bind": bind,
        "provides": ("K.emotion.state",),
        "requires": {},
        "report_key": "emotion",
        "snapshot_label": "emotion",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
