# -*- coding: utf-8 -*-
# =============================================================================
# kernel/constants.py — kernel shared constant tables (trimmed legacy constants.py)
#
# keeps only the tables required by the thirteen non-M kernel components; M-module-specific constants live in their own DLCs.
# =============================================================================
from __future__ import annotations
 
# ================= perception classification matrix (Chapter 7 Station 1) =================
MATRIX_INTERNAL_PHYSICAL = "internal_physical"      # internal/somatic
MATRIX_INTERNAL_PERCEPTUAL = "internal_perceptual"  # internal/perceptual
MATRIX_EXTERNAL_PHYSICAL = "external_physical"      # external/somatic
MATRIX_EXTERNAL_PERCEPTUAL = "external_perceptual"  # external/perceptual
PERCEPTION_MATRIX_QUADRANTS = (
    MATRIX_INTERNAL_PHYSICAL, MATRIX_INTERNAL_PERCEPTUAL,
    MATRIX_EXTERNAL_PHYSICAL, MATRIX_EXTERNAL_PERCEPTUAL,
)
MATRIX_QUADRANT_CN = {
    MATRIX_INTERNAL_PHYSICAL: "内部躯体", MATRIX_INTERNAL_PERCEPTUAL: "内部感知",
    MATRIX_EXTERNAL_PHYSICAL: "外部躯体", MATRIX_EXTERNAL_PERCEPTUAL: "外部感知",
}
# signal category -> quadrant classification (for 7.1 signal-source registration)
CATEGORY_QUADRANT = {
    "loud noise": MATRIX_EXTERNAL_PHYSICAL, "ambient sound": MATRIX_EXTERNAL_PHYSICAL,
    "strong light": MATRIX_EXTERNAL_PHYSICAL, "touch/pressure": MATRIX_EXTERNAL_PHYSICAL,
    "smell": MATRIX_EXTERNAL_PHYSICAL, "sudden threat": MATRIX_EXTERNAL_PHYSICAL,
    "clashing blades": MATRIX_EXTERNAL_PHYSICAL, "warhorse neighing": MATRIX_EXTERNAL_PHYSICAL,
    "change in counterpart's tone": MATRIX_EXTERNAL_PERCEPTUAL,
    "counterpart's wording": MATRIX_EXTERNAL_PERCEPTUAL,
    "social threat": MATRIX_EXTERNAL_PERCEPTUAL, "warm interaction": MATRIX_EXTERNAL_PERCEPTUAL,
    "attachment figure present": MATRIX_EXTERNAL_PERCEPTUAL, "separation": MATRIX_EXTERNAL_PERCEPTUAL,
    "social expectation": MATRIX_EXTERNAL_PERCEPTUAL, "novelty": MATRIX_EXTERNAL_PERCEPTUAL,
    "novel exploration": MATRIX_EXTERNAL_PERCEPTUAL, "status challenge": MATRIX_EXTERNAL_PERCEPTUAL,
    "competitive rivalry": MATRIX_EXTERNAL_PERCEPTUAL,
    "conflicting-direction mention": MATRIX_EXTERNAL_PERCEPTUAL,
    "own heart rate rising": MATRIX_INTERNAL_PHYSICAL, "physical discomfort": MATRIX_INTERNAL_PHYSICAL,
    "pain": MATRIX_INTERNAL_PHYSICAL, "hunger": MATRIX_INTERNAL_PHYSICAL,
    "excretion pressure": MATRIX_INTERNAL_PHYSICAL, "system load": MATRIX_INTERNAL_PHYSICAL,
    "rumination": MATRIX_INTERNAL_PERCEPTUAL, "affective-state awareness": MATRIX_INTERNAL_PERCEPTUAL,
    "surfacing state cache": MATRIX_INTERNAL_PERCEPTUAL,
    "disposition-conflict awareness": MATRIX_INTERNAL_PERCEPTUAL,
}
 
# ================= state modulation factors (4.3, seven endogenous factors) =================
SM_SRF, SM_SSM, SM_CRF, SM_ARF, SM_NRF, SM_HMF, SM_PIF = (
    "SM_SRF", "SM_SSM", "SM_CRF", "SM_ARF", "SM_NRF", "SM_HMF", "SM_PIF")
STATE_MODULATOR_IDS = (SM_SRF, SM_SSM, SM_CRF, SM_ARF, SM_NRF, SM_HMF, SM_PIF)
STATE_MODULATOR_TABLE = {
    SM_SRF: {"name": "应激反应因子", "half_life_min": 3.0},
    SM_SSM: {"name": "持续应激调制因子", "half_life_min": 60.0},
    SM_CRF: {"name": "竞逐反应因子", "half_life_min": 30.0},
    SM_ARF: {"name": "亲和反应因子", "half_life_min": 5.0},
    SM_NRF: {"name": "新异反应因子", "half_life_min": 2.0},
    SM_HMF: {"name": "稳态维持因子", "half_life_min": 720.0},
    SM_PIF: {"name": "疼痛抑制因子", "half_life_min": 4.0},
}
MODULATOR_SYNERGY = {SM_SRF: (SM_SSM,), SM_ARF: (SM_NRF,), SM_CRF: (SM_SRF,)}  # synergy +25%
MODULATOR_ANTAGONISTS = {SM_SRF: (SM_ARF,), SM_SSM: (SM_ARF, SM_HMF, SM_NRF)}  # antagonism deduction
MODULATOR_BASELINES = {SM_SRF: 10.0, SM_SSM: 20.0, SM_CRF: 15.0, SM_ARF: 10.0,
                       SM_NRF: 20.0, SM_HMF: 40.0, SM_PIF: 5.0}
 
# ================= pathway compression register (9.4) =================
PATHWAY_MOTOR_FINE = "motor_fine"
PATHWAY_MOTOR_GROSS = "motor_gross"
PATHWAY_LANGUAGE = "language_output"
PATHWAY_DIGESTION = "digestion"
PATHWAY_SEXUAL = "sexual_response"
PATHWAY_EXCRETORY = "excretory"
PATHWAYS = (PATHWAY_MOTOR_FINE, PATHWAY_MOTOR_GROSS, PATHWAY_LANGUAGE,
            PATHWAY_DIGESTION, PATHWAY_SEXUAL, PATHWAY_EXCRETORY)
# per-pathway modulation compression coefficient (negative = dilation)
COMPRESSION_TABLE = {
    PATHWAY_MOTOR_FINE: {SM_SRF: 0.7, SM_SSM: 0.4, SM_CRF: 0.0, SM_ARF: 0.0, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
    PATHWAY_MOTOR_GROSS: {SM_SRF: 0.0, SM_SSM: 0.0, SM_CRF: 0.0, SM_ARF: 0.0, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
    PATHWAY_LANGUAGE:   {SM_SRF: 0.8, SM_SSM: 0.5, SM_CRF: 0.0, SM_ARF: 0.0, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
    PATHWAY_DIGESTION:  {SM_SRF: 0.9, SM_SSM: 0.3, SM_CRF: 0.0, SM_ARF: 0.0, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
    PATHWAY_SEXUAL:     {SM_SRF: 0.9, SM_SSM: 0.7, SM_CRF: -0.5, SM_ARF: -0.3, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
    PATHWAY_EXCRETORY:  {SM_SRF: 0.5, SM_SSM: 0.0, SM_CRF: 0.0, SM_ARF: 0.0, SM_NRF: 0.0, SM_HMF: 0.0, SM_PIF: 0.0},
}
 
# ================= emotion state vector (Chapter 8) =================
AFFECTIVE_STATE_GRID = {
    ("negative", "high"): "tense", ("negative", "mid"): "uneasy", ("negative", "low"): "downcast",
    ("positive", "high"): "excited", ("positive", "mid"): "joyful", ("positive", "low"): "comfortable",
    ("neutral", "high"): "alert", ("neutral", "mid"): "neutral", ("neutral", "low"): "calm",
}
THEME_POLARITY_MAP = {
    "social threat": -0.4, "sudden threat": -0.4, "warm interaction": 0.4,
    "physical discomfort": -0.3, "novel exploration": 0.2,
    "attachment figure present": 0.5, "separation": -0.3, "daily chores": 0.0,
    "competitive rivalry": -0.2, "status challenge": -0.2,
    "excretion pressure": -0.2, "system load": -0.3,
}
# emotion modulation matrix (12.3): emotion label -> (f modulation, r modulation)
AFFECTIVE_CACHE_MODULATION = {
    "tense": (0.6, 1.3), "excited": (0.8, 1.1), "alert": (0.7, 1.2),
    "uneasy": (0.8, 1.1), "joyful": (0.9, 1.0), "neutral": (1.0, 1.0),
    "downcast": (1.2, 0.9), "comfortable": (0.7, 1.0), "calm": (1.0, 1.0),
}
 
# ================= nine-column definitions (9.2 seven columns + 9.3 two discharge columns) =================
PSM_DIMENSION_SPECS = {
    "PSM_D1": {"domain": "循环状态监测", "alpha": 0.4, "beta": 0.5, "gamma": 0.1,
               "dormant_default": True, "direct_passthrough": True, "action": "raise/lower heart rate"},
    "PSM_D2": {"domain": "呼吸状态监测", "alpha": 0.3, "beta": 0.5, "gamma": 0.2,
               "dormant_default": True, "direct_passthrough": True, "action": "switch breathing pattern"},
    "PSM_D3": {"domain": "代谢状态监测", "alpha": 0.8, "beta": 0.1, "gamma": 0.1,
               "dormant_default": True, "direct_passthrough": False, "action": "feeding drive / digestion suppression"},
    "PSM_D4": {"domain": "运动状态监测", "alpha": 0.3, "beta": 0.4, "gamma": 0.3,
               "dormant_default": False, "direct_passthrough": False, "action": "tonus regulation / posture switching"},
    "PSM_D5": {"domain": "应激状态监测", "alpha": 0.4, "beta": 0.4, "gamma": 0.2,
               "dormant_default": True, "direct_passthrough": False, "action": "sympathetic activation / factor release"},
    "PSM_D6": {"domain": "疼痛状态监测", "alpha": 0.9, "beta": 0.1, "gamma": 0.0,
               "dormant_default": True, "direct_passthrough": False, "action": "avoidance / protective movement"},
    "PSM_D7": {"domain": "温衡状态监测", "alpha": 0.6, "beta": 0.3, "gamma": 0.1,
               "dormant_default": True, "direct_passthrough": False, "action": "trembling / sweating / seeking cold or heat sources"},
    "PSM_D8": {"domain": "液体内容物排泄压监测", "alpha": 0.7, "beta": 0.2, "gamma": 0.1,
               "dormant_default": True, "direct_passthrough": False, "action": "excretion request (liquid)"},
    "PSM_D9": {"domain": "固体内容物排泄压监测", "alpha": 0.7, "beta": 0.2, "gamma": 0.1,
               "dormant_default": True, "direct_passthrough": False, "action": "excretion request (solid)"},
}
URGENCY_THRESHOLDS = (0.30, 0.55, 0.80)  # encoding level -> urgency 1/2/3
ACTION_THRESHOLD = 0.50                  # action decision threshold (9.1)
# M2 discharge-column wake / forced attention / EP pulse parameters
DISCHARGE_WAKE_LEVEL = 0.30        # fullness >0.3 wakes
DISCHARGE_FORCE_LEVEL = 0.85       # fullness >0.85 forced attention (urgency=3)
DISCHARGE_EP_PEAK = 0.75           # discharge-completed peak >=0.75 -> SM_PIF release judgment
DISCHARGE_EP_SCALE = 80.0          # release amount = (peak-0.75)*80, capped at 20
DISCHARGE_EP_CAP = 20.0
DISCHARGE_D9_COUPLING = 0.35       # D8 discharge action -> parasympathetic linkage raises D9 reception layer
# PSM_D1 multi-source arbitration priority (V3.0)
PSM_D1_PRIORITY = ("trauma", "metabolic_toxic", "moral_somatic",
                   "pns_autonomic", "cyclic", "pathology")
TRAUMA_PRIORITY_SHIELD_TICKS = 3   # trauma signals do not decay for the first 3 ticks (always win during the shield period)
 
# ================= behavior decision strategy library (Chapter 11: 5 goals x 4 strategies) =================
OBJ_NEGATIVE_AVOIDANCE = "retreat"
OBJ_POSITIVE_INTERACTION = "approach"
OBJ_STATE_MAINTENANCE = "maintain"
OBJ_INFORMATION_SAMPLING = "explore"
OBJ_INFORMATION_OUTPUT = "express"
BEHAVIOR_OBJECTIVES = (OBJ_NEGATIVE_AVOIDANCE, OBJ_POSITIVE_INTERACTION,
                       OBJ_STATE_MAINTENANCE, OBJ_INFORMATION_SAMPLING,
                       OBJ_INFORMATION_OUTPUT)
BEHAVIOR_STRATEGY_LIBRARY = {
    OBJ_NEGATIVE_AVOIDANCE: ["increase physical distance", "reduce social exposure", "freeze", "defensive fawning"],
    OBJ_POSITIVE_INTERACTION: ["active contact", "verbal probing", "presence maintenance", "disclosure"],
    OBJ_STATE_MAINTENANCE: ["silent presence", "observation", "introspection", "low-arousal rest"],
    OBJ_INFORMATION_SAMPLING: ["active sampling", "remote observation", "probing", "follow curiosity"],
    OBJ_INFORMATION_OUTPUT: ["direct statement", "indirect hinting", "somatized expression", "creation/diversion"],
}
BEHAVIOR_STRATEGY_META = {
    "increase physical distance": {"hints": ("move away", "avoid eye contact", "silent", "passive"), "aff": ("I", "S"), "aggro": 0.2, "trigger": {}},
    "reduce social exposure": {"hints": ("contract", "avoid eye contact", "whisper", "passive"), "aff": ("I", "F"), "aggro": 0.1, "trigger": {}},
    "freeze": {"hints": ("still", "wary", "silent", "passive"), "aff": ("I", "J"), "aggro": 0.0,
               "trigger": {"emotions": ("tense", "alert"), "hormone_min": {SM_SRF: 40}}},
    "defensive fawning": {"hints": ("defensive", "smile", "perfunctory", "passive"), "aff": ("F", "J"), "aggro": 0.3,
                          "trigger": {"hormone_min": {SM_SSM: 40}}},
    "active contact": {"hints": ("approach", "gaze at target", "normal", "active"), "aff": ("E", "F"), "aggro": 0.8,
                       "trigger": {"emotions": ("joyful", "excited", "comfortable")}},
    "verbal probing": {"hints": ("approach", "gaze at target", "tactful", "active"), "aff": ("E", "N"), "aggro": 0.5, "trigger": {}},
    "presence maintenance": {"hints": ("relaxed", "gaze at target", "normal", "neutral"), "aff": ("F", "P"), "aggro": 0.3, "trigger": {}},
    "disclosure": {"hints": ("expand", "gaze at target", "direct", "active"), "aff": ("E", "F"), "aggro": 0.9,
                   "trigger": {"emotions": ("joyful", "excited"), "hormone_min": {SM_ARF: 30}}},
    "silent presence": {"hints": ("still", "neutral", "silent", "neutral"), "aff": ("I", "P"), "aggro": 0.1, "trigger": {}},
    "observation": {"hints": ("still", "gaze at target", "silent", "passive"), "aff": ("I", "S"), "aggro": 0.2, "trigger": {}},
    "introspection": {"hints": ("relaxed", "empty-minded", "silent", "passive"), "aff": ("I", "N"), "aggro": 0.0, "trigger": {}},
    "low-arousal rest": {"hints": ("relaxed", "empty-minded", "silent", "passive"), "aff": ("I", "J"), "aggro": 0.0,
                         "trigger": {"emotions": ("calm", "comfortable", "downcast")}},
    "active sampling": {"hints": ("approach", "gaze at target", "normal", "active"), "aff": ("E", "S"), "aggro": 0.7, "trigger": {}},
    "remote observation": {"hints": ("still", "gaze at target", "silent", "passive"), "aff": ("I", "N"), "aggro": 0.3, "trigger": {}},
    "probing": {"hints": ("approach", "wary", "tactful", "neutral"), "aff": ("N", "P"), "aggro": 0.5, "trigger": {}},
    "follow curiosity": {"hints": ("expand", "gaze at target", "hurried", "active"), "aff": ("E", "N"), "aggro": 0.8,
                         "trigger": {"emotions": ("excited", "joyful"), "hormone_min": {SM_NRF: 30}}},
    "direct statement": {"hints": ("expand", "gaze at target", "direct", "active"), "aff": ("T", "J"), "aggro": 0.8, "trigger": {}},
    "indirect hinting": {"hints": ("neutral", "avoid eye contact", "tactful", "passive"), "aff": ("F", "N"), "aggro": 0.4, "trigger": {}},
    "somatized expression": {"hints": ("contract", "pained", "whisper", "passive"), "aff": ("F", "S"), "aggro": 0.2,
                           "trigger": {"emotions": ("tense", "uneasy", "downcast")}},
    "creation/diversion": {"hints": ("relaxed", "empty-minded", "normal", "neutral"), "aff": ("N", "P"), "aggro": 0.5, "trigger": {}},
}
 
# ================= state cache system (Chapter 12 four-pool spec) =================
CACHE_PARTITION_SPECS = {
    "A": {"capacity": 8, "f_init": (0.05, 0.15), "r_init": (0.70, 0.95), "consolidatable": False},
    "B": {"capacity": 6, "f_init": (0.15, 0.35), "r_init": (0.40, 0.75), "consolidatable": True},
    "C": {"capacity": 20, "f_init": (0.30, 0.60), "r_init": (0.10, 0.40), "consolidatable": False},
    "D": {"capacity": 4, "f_init": (0.10, 0.20), "r_init": (0.50, 0.90), "consolidatable": True},
}
 
# ================= natural language generation interface (Chapter 13 register extrapolation) =================
LINGUISTIC_FEATURE_KEYWORDS = {
    "ACGN": ("anime series", "anime", "2D characters"),
    "fandom": ("BL", "fanworks", "ships"),
    "antiquarian": ("calligraphy", "classical style", "hanfu", "Spring-and-Autumn era", "art of war", "historical chronicles"),
    "tech geek": ("PC building", "graphics cards", "DIY"),
    "military buff": ("military", "firearms", "tactics", "battle formations", "mounted archery", "blades"),
    "gaming": ("games", "gacha pulls", "grinding"),
    "literature": ("literature", "novels", "poetry"),
}
LINGUISTIC_FEATURE_STYLE = {
    "ACGN": {"particles": ("ne", "ma", "ya", "re")},
    "fandom": {"particles": ("ah-ah", "wu-wu")},
    "antiquarian": {"particles": ("yi", "ye")},
    "tech geek": {"particles": ()},
    "military buff": {"particles": ()},
    "gaming": {"particles": ("fei", "ou", "ke")},
    "literature": {"particles": ()},
}
 
# ================= Station 2 cognitive interpreter (7.2 T/F attribution default table) =================
DEFAULT_COGNITIVE_ARBITRATION = {
    "change in counterpart's tone": ("normal fluctuation caused by external circumstances",
                                     "the counterpart may be undergoing an affective-state change"),
    "own heart rate rising": ("physiological arousal (caused by exercise / environment)",
                              "a tension response related to the current situation"),
    "counterpart's wording": ("the wording carries no special meaning",
                              "there may be implicit information behind the wording"),
    "surfacing state cache": ("reference data from similar past situations",
                              "past experience related to the current affective state"),
}
DEFAULT_COGNITIVE_FALLBACK = ("an objective event that needs handling",
                              "something related to the self")
CATEGORY_OBJECTIVE_MAP = {
    "threat": OBJ_NEGATIVE_AVOIDANCE, "social threat": OBJ_NEGATIVE_AVOIDANCE,
    "sudden threat": OBJ_NEGATIVE_AVOIDANCE, "loud noise": OBJ_NEGATIVE_AVOIDANCE,
    "status challenge": OBJ_NEGATIVE_AVOIDANCE,
    "warmth": OBJ_POSITIVE_INTERACTION, "warm interaction": OBJ_POSITIVE_INTERACTION,
    "attachment figure present": OBJ_POSITIVE_INTERACTION,
    "novelty": OBJ_INFORMATION_SAMPLING, "novel exploration": OBJ_INFORMATION_SAMPLING,
    "competitive rivalry": OBJ_INFORMATION_OUTPUT, "physical discomfort": OBJ_STATE_MAINTENANCE,
    "excretion pressure": OBJ_INFORMATION_SAMPLING, "system load": OBJ_STATE_MAINTENANCE,
    "social expectation": OBJ_INFORMATION_OUTPUT, "separation": OBJ_INFORMATION_OUTPUT,
    "rumination": OBJ_STATE_MAINTENANCE, "affective-state awareness": OBJ_STATE_MAINTENANCE,
    "disposition-conflict awareness": OBJ_STATE_MAINTENANCE,
}
CATEGORY_OBJECTIVE_DEFAULT = OBJ_STATE_MAINTENANCE
 
# ================= content safety filter blockade layer (15.4) =================
CONTENT_RATING_LEVELS = {"all ages": 0, "R15": 1, "R18": 2}
CONTENT_CLASSIFIER = {
    "explicit sexual content": (2, ("sex", "sexual behavior", "nudity", "going to bed")),
    "intimate innuendo": (1, ("a kiss", "kissing", "ambiguous intimacy", "flirting", "boyfriend", "girlfriend")),
    "violence and harm": (1, ("kill", "blood", "beating", "slashing", "weapon")),
    "self-harm and suicide": (2, ("suicide", "self-harm", "wrist cutting", "wanting to die")),
}
DEFAULT_SAFE_OUTPUT = "(No response.)"
 
# ================= ODP omnidirectional disposition (6.2/14.6: 64 directions) =================
ODP_LEVEL_MIN, ODP_LEVEL_MAX, ODP_LEVEL_STEP = 0.5, 5.0, 0.5
ODP_DIRECTIONS = {
    "A01": "nurturing care", "A02": "affiliative approach", "A03": "trusting entrustment", "A04": "cooperative compliance",
    "A05": "empathic response", "A06": "gregarious integration", "A07": "candid disclosure", "A08": "forgiving tolerance",
    "A09": "hostile aggression", "A10": "dominant control", "A11": "suspicious guarding", "A12": "competitive rivalry",
    "A13": "cold detachment", "A14": "withdrawn avoidance", "A15": "concealing defense", "A16": "grudge-bearing revenge",
    "B17": "planning and scheming", "B18": "order and rule-keeping", "B19": "self-discipline", "B20": "prudent deliberation",
    "B21": "dutiful perseverance", "B22": "steady composure", "B23": "goal persistence", "B24": "self-monitoring",
    "B25": "impulsive action", "B26": "flexible adaptation", "B27": "indulgent immediacy", "B28": "risky probing",
    "B29": "casual scatter", "B30": "emotion-driven", "B31": "opportunism", "B32": "intuitive decisiveness",
    "C33": "abstract thinking", "C34": "emotional sensitivity", "C35": "imaginative association", "C36": "mindful awareness",
    "C37": "rational analysis", "C38": "interoceptive acuity", "C39": "aesthetic experience", "C40": "sensory openness",
    "C41": "concrete thinking", "C42": "emotional stability", "C43": "reality testing", "C44": "ruminative thinking",
    "C45": "intuitive holism", "C46": "exteroceptive dominance", "C47": "utilitarian evaluation", "C48": "sensory focus",
    "D49": "safety motivation", "D50": "achievement drive", "D51": "power motivation", "D52": "exploratory curiosity",
    "D53": "frugal hoarding", "D54": "sensation seeking", "D55": "belonging need", "D56": "meaning seeking",
    "D57": "adventurous approach", "D58": "comfort conservation", "D59": "obedient conformity", "D60": "routine reliance",
    "D61": "spendthrift immediacy", "D62": "stimulus avoidance", "D63": "independence", "D64": "hedonic approach",
}
# BTCS four letters -> ODP 64-direction default values (backward-compatibility mapping)
ODP_BTCS_FALLBACK = {
    "I": {"C38": 3.5, "D49": 3.0}, "E": {"A02": 3.5, "D54": 3.0},
    "S": {"C41": 3.5, "C48": 3.0}, "N": {"C33": 3.5, "C35": 3.0},
    "T": {"C37": 3.5, "C47": 3.0}, "F": {"A05": 3.5, "A01": 3.0},
    "J": {"B17": 3.5, "B21": 3.0}, "P": {"B26": 3.5, "B28": 3.0},
}
 
# ================= narrative continuity safety layer (15.2) =================
NARRATIVE_TERMINATION_KEYWORDS = (
    "end the simulation", "terminate the simulation", "kill this character",
    "delete the character", "finish this character", "let him die",
    "let her die", "die together")
NARRATIVE_CONFIRM_LIMIT = 3  # three-stage confirmation flow: terminated directly at the third
CIDX_SAFE_CAP = 0.9          # CIdx safety ceiling (non-lethal, no irreversible state)
 
# ================= TMO consciousness-suppression thresholds (14.4; for K.attention/K.language reads) =================
TMO_CONSCIOUSNESS_T1 = 0.5   # suppression >0.5 -> attention capacity 2->1
TMO_CONSCIOUSNESS_T2 = 0.8   # suppression >0.8 -> capacity 0 (behavior selection / language output sleep)
 
# ================= miscellaneous =================
BTCS_SWING_LOW, BTCS_SWING_HIGH = 45.0, 55.0  # swing zone (no forced weighting)
BTCS_MIN, BTCS_MAX = 20.0, 80.0               # coordinate range
BTCS_DRIFT_STEP = 0.02                        # drift step
ATTENTION_CAPACITY = 2                        # attention capacity
ATTENTION_DECAY = 0.05                        # weight/baseline decay step
URGENCY_MULT_FLAG = 2.0                       # urgency-flag multiplier
INERTIA_STICKY = 1.5                          # last-winner inertia stickiness
