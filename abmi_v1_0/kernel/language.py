# -*- coding: utf-8 -*-
"""K.language — cognition-domain kernel module (natural language generation interface: Chapter 13)

Role:
  - dual-node extrapolation: node 1 hard decoding (persona-card speech_hard direct override);
    node 2 extrapolation (BTCS/ODP -> structural natural voice parameters 70% + ...)"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, Optional
 
from ..infrastructure import DecisionLog
from .constants import (LINGUISTIC_FEATURE_KEYWORDS, LINGUISTIC_FEATURE_STYLE,
                        SM_SRF, SM_SSM, SM_CRF, SM_ARF)
from .models import (VoiceOutputDirective, VoiceFeatureProfile,
                     PerceptionScene, AffectiveStateEncoding, clamp)
 
 
class LanguageEngine:
    """voice-profile construction + per-tick prompt generation; silent mode skips directly (dormancy semantics)."""
 
    def __init__(self, card: Any, log: DecisionLog) -> None:
        self.card = card
        self.log = log
        self.profile = VoiceFeatureProfile()                        # voice profile (lazy-built on first tick)
        self._profile_built = False                                 # lazy-build flag
        self._register_alternate = False                            # M6: register-alternation state
 
    # ================= initialization assembly (node-2 extrapolation + node-1 override) =================
    def build_voice_profile(self, coords: Dict[str, float],
                            jp_letter: Optional[str],
                            pool_b_keywords: list,
                            odp_values: Optional[Dict[str, float]] = None
                            ) -> VoiceFeatureProfile:
        p = VoiceFeatureProfile()
        # ---- node 2: BTCS -> structural natural voice parameters (70%) ----
        p.verbosity = clamp(1.0 - (coords["IE"] - 20.0) / 60.0)
        p.speech_rate = clamp(1.0 - (coords["IE"] - 20.0) / 60.0)
        p.sentence_complexity = clamp((coords["SN"] - 20.0) / 60.0)
        p.avg_sentence_length = p.sentence_complexity
        p.pause_frequency = clamp((coords["IE"] - 20.0) / 60.0)
        p.filler_density = clamp((1.0 - (coords["TF"] - 20.0) / 60.0) * 0.6
                                 + (1.0 - (coords["JP"] - 20.0) / 60.0) * 0.4)
        p.pause_position = "between sentences" if jp_letter == "J" else "free"
        p.initiation_tendency = clamp(1.0 - (coords["IE"] - 20.0) / 60.0)
        # ODP-priority correction (6.2): A02 affinity / D49 security-motivation corrects assertiveness
        if odp_values:
            p.initiation_tendency = clamp(p.initiation_tendency
                                          + (odp_values.get("A02", 2.5) - 2.5) * 0.1
                                          - (odp_values.get("D49", 2.5) - 2.5) * 0.05)
        # ---- node 2: B pool -> register extrapolation (30%) ----
        hits = {}
        for tag, keywords in LINGUISTIC_FEATURE_KEYWORDS.items():
            n = sum(1 for kw in keywords
                    if any(kw in item for item in pool_b_keywords))
            if n:
                hits[tag] = n / len(keywords)
        if hits:
            total = sum(hits.values())
            p.register_tags = [t for t, _ in sorted(hits.items(), key=lambda kv: -kv[1])]
            p.internet_slang_level = clamp(sum(
                (hits.get(t, 0) / total) * (0.9 if t in ("ACGN", "fandom", "gaming") else 0.2)
                for t in hits))
            particles = []
            for t in p.register_tags:
                particles.extend(LINGUISTIC_FEATURE_STYLE[t]["particles"])
            p.particle_set = particles
        # ---- node 1: hard-decoding override (13.1) ----
        hard = self.card.speech_hard
        if "talkativeness" in hard:
            p.verbosity = 0.2 if hard["talkativeness"] == "taciturn" else (
                0.9 if hard["talkativeness"] == "talkative" else p.verbosity)
        if "rate" in hard:
            p.speech_rate = {"slow": 0.2, "fast": 0.8,
                             "hurried": 0.95}.get(hard["rate"], p.speech_rate)
        if "volume" in hard:
            p.volume = hard["volume"]
        if "sentence pattern" in hard:
            p.avg_sentence_length = {"short": 0.2, "long": 0.8, "fragmented": 0.1}.get(
                hard["sentence pattern"], p.avg_sentence_length)
        if "particles" in hard:
            p.particle_set = p.particle_set + [hard["particles"]]
        if "dialect/accent" in hard:
            p.dialect_hint = hard["dialect/accent"]
        if "profanity" in hard:
            p.profanity_level = 0.0 if hard["profanity"] == "no profanity" else 0.4
        if "honorifics" in hard:
            p.politeness_level = 0.8 if hard["honorifics"] == "polite" else 0.3
        if "internet slang" in hard:
            p.internet_slang_level = 0.9 if hard["internet slang"] == "heavy" \
                else p.internet_slang_level
        self.profile = p
        return p
 
    # ================= 13.3 per-tick processing =================
    def generate_voice_prompt(self, tick: int, directive: VoiceOutputDirective,
                              hormones: Dict[str, float], scene: PerceptionScene,
                              emotion: AffectiveStateEncoding,
                              verbosity_mult: float = 1.0) -> str:
        if directive.speech_mode == "silent":                       # silent mode: sleep and skip
            self.log.record(tick, "NaturalLanguageInterface", "silent", "skipped")
            return ""
        p = self.profile
        notes = []
        rate, verbosity = p.speech_rate, p.verbosity
        filler = p.filler_density
        # ---- pathway-compression interaction (register/dialect unchanged; only the extra modifiers compressed) ----
        if hormones.get(SM_SRF, 0) > 60:
            rate, filler = 0.95, 0.0
            notes.append("speech rate locked fast / verbal tics emptied")
        if hormones.get(SM_SSM, 0) > 60:
            verbosity *= 0.5
            notes.append("talkativeness down, sentences shorter and more cautious")
        if hormones.get(SM_CRF, 0) > 40:
            notes.append("profanity temporarily up, honorifics down")
        if hormones.get(SM_ARF, 0) > 40:
            verbosity = clamp(verbosity + 0.2)
            notes.append("talkativeness up, repetition up, voice softer")
        # ---- M6: fracture -> register alternation ----
        register_display = "/".join(p.register_tags) or "generic"
        if directive.conflict_mark:
            self._register_alternate = not self._register_alternate
            if len(p.register_tags) >= 2 and self._register_alternate:
                register_display = "/".join(reversed(p.register_tags))
            notes.append(f"register alternation ({directive.conflict_mark})")
        # ---- M5: SSE -> honorific/apology/self-disclosure offsets ----
        if directive.sse_politeness_bias > 0.05:
            notes.append("honorifics up, apologies up, self-disclosure down")
        # ---- M4: consciousness suppression -> talkativeness force-lowered ----
        if directive.consciousness_suppression > 0.5:
            verbosity *= max(0.1, 1.0 - directive.consciousness_suppression)
            notes.append("consciousness suppression: talkativeness forcibly lowered")
        # ---- M8: trauma speech pattern ----
        if directive.trauma_mode:
            tnotes = {"freeze": "terse single words, almost never speaks first, trembling endings",
                      "flight": "fast speech wanting to escape, looking for excuses to leave",
                      "fight": "short hard sentences, provocative, volume raised",
                      "fawn": "echoes the counterpart, over-apologizes",
                      "somatic_freeze": "long silences, heavy breathing, answering off-point"}
            note = tnotes.get(directive.trauma_mode)
            if note:
                verbosity *= 0.4 if directive.trauma_mode in ("freeze", "somatic_freeze") else 0.7
                notes.append(f"trauma mode [{directive.trauma_mode}]: {note}")
        # ---- M4 alcohol L2~L3: disinhibition ----
        if directive.alcohol_disinhibited:
            verbosity = clamp(verbosity * 1.4)
            notes.append("alcohol disinhibition: talkativeness up, logic down, no filter")
        verbosity = clamp(verbosity * verbosity_mult)               # M3: CIdx talkativeness modulation
        # ---- generate voice prompt text (<=3 lines) ----
        speed = "fast" if rate > 0.65 else ("slow" if rate < 0.35 else "moderate")
        length = "long sentences" if p.avg_sentence_length > 0.6 else (
            "short sentences" if p.avg_sentence_length < 0.35 else "medium length")
        talk = "talkative and active" if verbosity > 0.6 else (
            "taciturn and passive" if verbosity < 0.35 else "situation-dependent")
        particles = ", ".join(p.particle_set[:4]) if p.particle_set else "none"
        lines = [
            f"[speaking manner] {directive.speech_mode} · {speed} rate · {length} · {talk}"
            f" · particles({particles}) · volume {p.volume}"
            + (f" · {p.dialect_hint} accent" if p.dialect_hint else ""),
            f"[content hint] theme: {directive.topic_hint or scene.integrated_theme}"
            f" · affective state: {emotion.label} · register: {register_display}",
            f"[taboos] {';'.join(notes) if notes else 'keep persona consistency; do not leave the affective baseline'}",
        ]
        prompt = "\n".join(lines[:3])
        self.log.record(tick, "NaturalLanguageInterface", "voice prompt", lines[0])
        return prompt
 
    # ================= P4 hook (V8 module surface) =================
    def on_decision(self, tick: int, data: Dict[str, Any]) -> None:
        board = self._board
        if not self._profile_built:                                 # voice profile lazy-built on first tick
            coords = board.read("K.persona.coords", {}) or {}
            letters = board.read("K.persona.letters", {}) or {}
            odp_values = board.read("K.persona.odp", {}) or {}
            if coords:                                              # built only when the persona mirror is ready
                self.build_voice_profile(coords, letters.get("JP"),
                                         list(self.card.interests), odp_values)
                self._profile_built = True
        strategy = data["strategy"]                                 # trigger guarantees non-empty
        scene = data.get("scene") or PerceptionScene(scene_id=f"SCN-{tick:04d}")
        emotion = data.get("emotion") or AffectiveStateEncoding(0.0, 0.0, "neutral")
        hormones = board.read("K.pns.hormones", {}) or {}
        speech_mode = "silent" if board.read("sys.unconsciousness", False) else "normal"
        directive = VoiceOutputDirective(
            speech_mode=speech_mode,
            topic_hint=scene.integrated_theme,
            conflict_mark=str(board.read("sys.odp_mark", "") or ""),
            sse_politeness_bias=float(board.read_knob("knob.politeness_bias", 0.0)),
            consciousness_suppression=float(
                board.read_knob("knob.consciousness_suppression", 0.0)),
            trauma_mode=str(board.read("sys.trauma_type", "") or "")
            if board.read("sys.trauma_active", False) else "",
            alcohol_disinhibited=bool(board.read("sys.alcohol_language_free", False)))
        cidx = float(board.read("sys.cognitive_index", 0.0))
        prompt = self.generate_voice_prompt(
            tick, directive, hormones, scene, emotion,
            verbosity_mult=1.0 - cidx * 0.5)                        # M3: x(1-CIdx x0.5)
        data["voice_prompt"] = prompt                               # -> scene side / narration backend
        board.publish("K.language.prompt", prompt)
 
    # ---- four-piece set ----
    def snapshot(self) -> Dict[str, Any]:
        return {"profile": asdict(self.profile),
                "profile_built": self._profile_built,
                "register_alternate": self._register_alternate}
 
    def restore(self, snap: Dict[str, Any]) -> None:
        if not isinstance(snap, dict):
            return
        if isinstance(snap.get("profile"), dict):
            self.profile = VoiceFeatureProfile(**snap["profile"])
        self._profile_built = bool(snap.get("profile_built", False))
        self._register_alternate = bool(snap.get("register_alternate", False))
 
    def smoke(self) -> bool:
        return self.profile is not None
 
    def invariants(self) -> bool:
        p = self.profile
        return all(0.0 <= v <= 1.0 for v in
                   (p.verbosity, p.speech_rate, p.sentence_complexity,
                    p.filler_density, p.initiation_tendency))
 
    def audit_probe(self) -> list:
        return []                                                   # not audited
 
    def report(self) -> Dict[str, Any]:
        return {"register": "/".join(self.profile.register_tags) or "generic",
                "verbosity": round(self.profile.verbosity, 2)}
 
 
# =============================================================================
# dlc_spec — V8 installation spec
# =============================================================================
def dlc_spec() -> Dict[str, Any]:
    def factory(ctx: Any) -> LanguageEngine:
        engine = LanguageEngine(ctx.k.card, ctx.log)
        engine._board = ctx.board
        ctx.k.language = engine                                     # backfill kernel ports
        return engine
 
    def bind(inst: LanguageEngine, ctx: Any) -> Dict[str, Any]:
        return {
            "P4_decision": inst.on_decision,
            "report": inst.report,
        }
 
    return {
        "module_id": "K.language",
        "version": "8.0",
        "zone": "cognitive",                                        # cognition domain
        "contract_keys": (),                                        # does not write sys.*
        "gear": {
            "P4_decision": {"every": 1,
                            "trigger": lambda t, d: d.get("strategy") is not None},
        },
        "priorities": {"P4_decision": 20},                          # decision-phase wrap-up
        "factory": factory,
        "bind": bind,
        "provides": ("K.language.prompt",),
        "requires": {},
        "report_key": "language",
        "snapshot_label": "language",
        "audit_probe": lambda inst: inst.audit_probe,
        "card_schema": None, "card_manifest": None,
        "built_in": True,
    }
