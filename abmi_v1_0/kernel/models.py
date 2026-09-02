# -*- coding: utf-8 -*-
# =============================================================================
# kernel/models.py — kernel shared data classes (trimmed legacy models.py)
#
# the single authoritative definition of cross-module data structures: modules pass these objects via the data pipe / blackboard;
# modules never redefine them themselves (constitutional rule 5: a shared type library does not count as inter-module import).
# =============================================================================
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
 
 
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """numeric truncation to [lo, hi] (the kernel-wide boundary function)."""
    return max(lo, min(hi, x))
 
 
# -----------------------------------------------------------------------------
# perceptual signal (4.1): a raw signal not yet "understood", carrying only source + type + intensity
# -----------------------------------------------------------------------------
@dataclass
class PerceptionSignal:
    source: str                     # receptor: "ear"/"eye"/"skin"/"nose"/"interoceptor"
    type: str                       # channel: "auditory"/"visual"/"tactile"/"olfactory"/"internal"
    intensity: float                # raw intensity [0, 1]
    category: str = "generic"       # semantic category (external world / downstream injection)
    theme_hint: Optional[str] = None  # theme hint (for scene binding)
    target: Optional[str] = None    # target object person_id
    urgency: bool = False           # urgency flag (competition x2.0)
    payload: dict = field(default_factory=dict)  # remaining payload (pass-through)
    source_tag: str = "pns_autonomic"  # PSM_D1 multi-source arbitration label
 
 
# -----------------------------------------------------------------------------
# Station 1 signal-source entry (7.1): one row of the competition ledger
# -----------------------------------------------------------------------------
@dataclass
class SignalSourceEntry:
    id: str                         # source ID: "quadrant:category:object"
    quadrant: str                   # perception-classification-matrix quadrant
    raw_intensity: float = 0.0      # raw intensity (x0.6 decay per tick)
    baseline: float = 0.30          # adaptation baseline (novelty reference)
    novelty: float = 0.50           # novelty [0.05, 1]
    urgency_flag: bool = False      # urgency flag
    check_weight: float = 1.0       # inspection weight (feedback-adjusted [0.3, 2.0])
    last_attended_round: int = -10  # last winning tick (inertia-stickiness judgment)
    salience: float = 0.0           # this round's salience (competition result)
    won_quadrant: bool = False      # quadrant qualifier
    won_global: bool = False        # global winner
    category: str = "generic"       # semantic category
    theme_hint: Optional[str] = None
    target: Optional[str] = None
 
 
# -----------------------------------------------------------------------------
# Station 2 perceptual fragment (7.2): attribution + depth + time projection + intent suggestion
# -----------------------------------------------------------------------------
@dataclass
class CognitiveFragment:
    signal: SignalSourceEntry       # originating signal source
    attribution: str                # T/F attribution text
    depth_level: str                # processing depth: shallow / mid / deep
    time_projection: Optional[str]  # J-type forward projection (None for non-J)
    emotional_tag: Optional[str]    # emotion label (theme-hint pass-through)
    recommended_intent: str         # recommended behavior goal (category->goal mapping)
    urgency: int                    # urgency 0-3
 
 
# -----------------------------------------------------------------------------
# Station 3 perceptual scene (7.3): <=2 fragments bound into 1 scene
# -----------------------------------------------------------------------------
@dataclass
class PerceptionScene:
    scene_id: str                   # scene ID: "SCN-NNNN"
    perception_fragments: list = field(default_factory=list)  # bound fragments
    integrated_theme: str = "daily chores"  # integrated theme
    urgency: int = 0                # scene urgency (max of fragments)
    source_attribution: str = "default_scan_mode"  # internal/external/mixed/default scan
    emotional_tone: Optional[str] = None  # emotion tone (Chapter 8 final binding)
 
 
# -----------------------------------------------------------------------------
# emotion state encoding (Chapter 8): valence x arousal -> one of nine labels
# -----------------------------------------------------------------------------
@dataclass
class AffectiveStateEncoding:
    valence: float                  # valence [-1, 1]
    arousal: float                  # arousal [-1, 1]
    label: str                      # one of the nine labels
 
 
# -----------------------------------------------------------------------------
# single-column encoding (9.1): one column's encoding-layer output
# -----------------------------------------------------------------------------
@dataclass
class PhysiologicalStateEncoding:
    column_id: str                  # "PSM_D1"~"PSM_D9"
    encoded_level: float            # encoding level [0, 1]
    trend: str                      # stable / rising / falling / fluctuating
    urgency_level: int              # 0 none / 1 attention / 2 urgent / 3 critical
    discomfort_level: int           # discomfort level 0-4
    descriptive_tag: str            # description label: "domain:level"
 
 
# -----------------------------------------------------------------------------
# internal state report (9.1): the body report uploaded to CNS
# -----------------------------------------------------------------------------
@dataclass
class PhysiologicalStateReport:
    encodings: dict = field(default_factory=dict)   # active column encodings
    hormones: dict = field(default_factory=dict)    # effective hormone levels after antagonism
    heart_rate: float = 72.0        # heart rate
    hr_baseline: float = 72.0       # heart-rate baseline
    breath_rate: float = 14.0       # breathing rate
    br_baseline: float = 14.0       # breathing-rate baseline
    deep_slow_breath: bool = False  # deep-slow-breathing flag
    muscle_tone: float = 4.0        # muscle tone 0-10
    stress_level: float = 0.0       # stress level 0-10
    pain_level: float = 0.0         # pain level 0-10
    hunger: float = 0.0             # hunger 0-10
    discharge_liquid: float = 0.0   # liquid-content fullness [0,1]
    discharge_solid: float = 0.0    # solid-content fullness [0,1]
 
 
# -----------------------------------------------------------------------------
# motor directive (9.1): column -> PNS skeletal muscle (via pathway compression)
# -----------------------------------------------------------------------------
@dataclass
class MotorActionCommand:
    pathway: str                    # pathway: motor_fine/motor_gross/...
    command: str                    # directive text
    magnitude: float                # raw force
    source_column: str = ""         # originating column
    compressed: float = 0.0         # compressed force (filled at egress)
 
 
# -----------------------------------------------------------------------------
# behavior-goal directive (Chapter 11): CNS -> behavior decision engine
# -----------------------------------------------------------------------------
@dataclass
class BehaviorObjectiveCommand:
    intent: str                     # one of the five goals
    strength: int                   # intensity 0-3
    continuity: str                 # CONTINUE / BREAK
    compute_behavior_activation_coefficient: float  # hormone agitation index (CNS pre-settlement)
    scene_summary: str              # scene summary (theme)
    conflict_mark: str = ""         # M6 fracture mark: mild/moderate/severe
    sse_risk_bias: float = 0.0      # M5 survival-security risk bias
    motor_impairment: float = 0.0   # M4 motor impairment [0,1]
 
 
# -----------------------------------------------------------------------------
# behavior-strategy template output (Chapter 11): chosen strategy + four-channel hints
# -----------------------------------------------------------------------------
@dataclass
class BehaviorStrategyTemplate:
    strategy_name: str              # strategy name (one of the 20-strategy library)
    intent: str                     # owning behavior goal
    body_hint: str                  # body hint
    face_hint: str                  # face hint
    voice_hint: str                 # voice hint
    stance: str                     # stance: active/passive/neutral/hesitant
 
 
# -----------------------------------------------------------------------------
# language output directive (13.1): CNS -> natural language generation interface
# -----------------------------------------------------------------------------
@dataclass
class VoiceOutputDirective:
    speech_mode: str                # speaking mode: normal / silent
    topic_hint: str = ""            # topic hint
    volume: str = "normal"          # volume
    compression_level: float = 0.0  # pathway-compression level
    conflict_mark: str = ""         # M6 fracture -> register alternation
    sse_politeness_bias: float = 0.0      # M5 honorific bias
    consciousness_suppression: float = 0.0  # M4 consciousness suppression -> talkativeness lowered
    trauma_mode: str = ""           # M8 trauma speech pattern
    alcohol_disinhibited: bool = False    # M4 alcohol disinhibition
 
 
# -----------------------------------------------------------------------------
# voice feature profile (13.2): final voice parameters from hard decoding + extrapolation
# -----------------------------------------------------------------------------
@dataclass
class VoiceFeatureProfile:
    speech_rate: float = 0.5            # speech rate
    avg_sentence_length: float = 0.5    # average sentence length
    pause_frequency: float = 0.5        # pause frequency
    pause_position: str = "between sentences"  # pause position
    sentence_complexity: float = 0.5    # syntactic complexity
    filler_density: float = 0.3         # filler-word density
    repetition_tendency: float = 0.2    # repetition tendency
    register_tags: list = field(default_factory=list)   # register label
    particle_set: list = field(default_factory=list)    # particle set
    dialect_hint: str = ""              # dialect/accent hint
    profanity_level: float = 0.0        # profanity level
    politeness_level: float = 0.5       # honorific level
    internet_slang_level: float = 0.3   # internet-slang level
    verbosity: float = 0.5              # talkativeness
    initiation_tendency: float = 0.5    # initiation tendency
    volume: str = "normal"              # volume
 
 
# -----------------------------------------------------------------------------
# state-cache entry (12.2): generic entry for the four pools
# -----------------------------------------------------------------------------
@dataclass
class StateCacheEntry:
    entry_id: str                   # entry ID: "MEM-NNNN"
    pool: str                       # pool: A/B/C/D
    scene_signature: str            # scene signature (dedup key)
    integrated_theme: str           # integrated theme
    emotional_tone: str             # emotion tone
    urgency: int                    # urgency
    target_person_id: Optional[str] = None  # target object (D pool)
    location: str = ""              # location
    AS: int = 1                     # availability level 1-5
    f: float = 0.2                  # fuzziness f (higher = fuzzier; deleted above 0.5)
    r: float = 0.6                  # retrievability r (higher = surfaces more easily)
    occurrence_count: int = 1       # re-encoding count
    retrieval_count: int = 0        # retrieval count
    consolidated: bool = False      # consolidated
    consolidation_round: int = 0    # consolidation rounds (>=3 and AS=5 -> promote to L3)
    anchor_id: Optional[str] = None  # anchor ID (L3 never forgotten)
    fragmented: bool = False        # M8 fragment encoding (temporal order lost)
    temporal_order_lost: bool = False
    blackout: bool = False          # M4 blackout encoding (unrecoverable)
    alcohol_affected: bool = False  # in-drunkenness encoding (marked at reorganization)
 
 
# -----------------------------------------------------------------------------
# aggregate modulation vector (10.4): DLC -> hub modulation contribution (compatibility surface; mostly knob.* soft keys in V8)
# -----------------------------------------------------------------------------
@dataclass
class ModulationVector:
    source: str = ""                    # source-module mark
    pain_bias: float = 0.0              # PSM_D6 pain bias (additive)
    temp_bias: float = 0.0              # PSM_D7 thermal-discomfort bias (additive)
    ssm_baseline_bias: float = 0.0      # SM_SSM baseline bias (additive)
    s_pressure_mult: float = 1.0        # S-pressure accumulation rate (multiplicative)
    cognitive_mult: float = 1.0         # cognitive sensitivity rate (multiplicative)
    social_weight_mult: float = 1.0     # social weight rate (multiplicative)
    memory_r_mult: float = 1.0          # cache r rate (multiplicative)
    verbosity_mult: float = 1.0         # talkativeness rate (multiplicative)
    valence_bias: float = 0.0           # valence bias (additive)
    sleep_quality_mult: float = 1.0     # reset quality rate (multiplicative)
    gut_mult: float = 1.0               # gastrointestinal motility rate (multiplicative)
    discharge_d9_sensitivity: float = 1.0  # D9 reception gain rate (multiplicative)
    motor_impairment: float = 0.0       # motor impairment [0,1]
    consciousness_suppression: float = 0.0  # consciousness suppression [0,1]
    respiratory_suppression: float = 0.0    # respiratory suppression [0,1]
    amnesia: float = 0.0                # forgetting effect [0,1]
    pain_relief: float = 0.0            # pain downregulation [0,1]
    risk_aversion: float = 0.0          # risk-aversion bias
    politeness_bias: float = 0.0        # honorific bias
    apology_bias: float = 0.0           # apology bias
    self_disclosure_bias: float = 0.0   # self-disclosure bias (negative = reduce)
    food_check_weight_mult: float = 1.0  # food signal weight rate
    hunger_threshold_mult: float = 1.0  # hunger urgency threshold rate
    cidx_baseline_bias: float = 0.0     # CIdx baseline bias
    odp_nudges: dict = field(default_factory=dict)  # ODP direction fine-tune
 
 
def to_dict(obj: Any) -> Any:
    """recursively convert dataclasses to serializable dicts (decision log / snapshot use)."""
    return asdict(obj)
