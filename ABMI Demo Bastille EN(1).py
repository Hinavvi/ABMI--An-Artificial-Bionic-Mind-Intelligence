# -*- coding: utf-8 -*-
"""ABMI Version 1.0 crowd demo: The Storming of the Bastille (100 citizens x 100 ticks).

Call surface: the core tick loop (demo stub) + kernel persona card / emotion
state (demo stubs) + all 14 real M1-M15 modules. 100 citizens = 100 fully
independent module stacks living through one shared script — the anger, the
assembly, the charge, the shooting and the mourning are all computed by the
engine. None of it is scripted per citizen.

Script (1789-07-14, one tick = one minute):
  1-20    Bread prices rise again. Hungry citizens take to the streets;
          resentment accumulates.
  21-40   Assembly in the square. Speeches, rumors ("the garrison will fire
          the cannons") — the crowd sets itself alight.
  41-60   The march on the Bastille. They demand the gunpowder; talks fail.
  61-75   The garrison opens fire. Some are hit and fall (M5 life-support
          flatline = clinical death); bystanders witness it (M8 vicarious
          trauma).
  76-90   The crowd overruns the fortress. Anger becomes a flood.
  91-100  Dusk roll call: the dead, the survivors, what will be remembered.

Run: place the 14 M1-M15 module .py files into ./modules/ or point the
ABMI_MODULE_DIR environment variable at their directory, then:
    python3 "ABMI Demo Bastille EN.py"
"""
import importlib
import json
import os
import random
import sys
import types
import zlib

MODULE_DIR = os.environ.get(
    "ABMI_MODULE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))
if not os.path.isdir(MODULE_DIR):
    sys.exit("Module directory not found: put the M1-M15 module .py files "
             "into ./modules/ or set ABMI_MODULE_DIR.")
sys.path.insert(0, MODULE_DIR)

MOD_NAMES = ["m1_cycle", "m2_monologue", "m3_life_baseline", "m4_tmo",
             "m4_alcohol", "m5_governor", "m6_odp", "m7_iceberg",
             "m8_trauma", "m9_epistemology", "m10_morality", "m11_thermal",
             "idns_hub", "m15_outpost"]
# The engine's phase order for the M1-M15 generation (P5/P7 are engine-owned
# in this generation, so they do not appear here).
PHASE_ORDER = ["P0_input", "P1_body", "P2_boundary", "P3_cognition",
               "P4_decision", "P6_maintenance"]

N_CITIZENS = 100
GUNFIRE_START, GUNFIRE_END = 61, 75     # the garrison's firing window


# ---------------- Core/kernel demo stubs ----------------
# The real ABMI core and kernel are replaced here by a minimal harness that
# implements ONLY the contract surface the M1-M15 modules actually touch:
# board, bus, services, per-module RNG, and the persona card. This keeps the
# demo self-contained while exercising the genuine module code end to end.
class DemoRNG:
    """Deterministic per-module RNG with a cursor-style snapshot.

    Implements BOTH generations of the ABMI RNG contract: random()/uniform()/
    choice()/gauss() plus snapshot()/restore() (M1-M15 aliases) and
    snapshot_cursor()/restore_cursor() (M26+ names). A cursor restores by
    re-seeding and replaying draws, so replays are byte-exact.
    """
    def __init__(self, seed=0):
        self._seed = seed
        self._r = random.Random(seed)
        self._c = 0
    def random(self):
        self._c += 1
        return self._r.random()
    def uniform(self, a, b):
        return a + (b - a) * self.random()
    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1)) % (b - a + 1)
    def choice(self, seq):
        return seq[int(self.random() * len(seq)) % len(seq)]
    def gauss(self, mu, sigma):
        # Cheap triangular-ish approximation; modules only need determinism.
        return mu + sigma * (self.random() + self.random()
                             + self.random() - 1.5) * 2.0
    def snapshot(self):                # M1-M15-generation alias for the cursor
        return self._c
    def restore(self, c):
        self.restore_cursor(c)
    def snapshot_cursor(self):
        return self._c
    def restore_cursor(self, c):
        self._c = int(c)
        self._r = random.Random(self._seed)
        for _ in range(self._c):
            self._r.random()


class DemoBoard:
    """Blackboard: the single decoupled data channel between modules."""
    def __init__(self):
        self.store = {}
        self.knobs = {}
    def read(self, key, default=None):
        return self.store.get(key, default)
    def write(self, key, value, owner=None):
        self.store[key] = value
    def publish(self, key, value):
        self.store[key] = value
    def write_knob(self, key, value, owner=None, priority=0):
        self.knobs[key] = value
    def read_knob(self, key, default=0.0):
        return self.knobs.get(key, default)
    def all_keys(self):
        return list(self.store.keys())


class DemoBus:
    def __init__(self):
        self.subs = {}
        self.events = []
    def subscribe(self, name, fn, owner=None, priority=0):
        self.subs.setdefault(name, []).append(fn)
    def emit(self, name, payload, source=None, next_tick=False):
        self.events.append((name, payload))
        for fn in self.subs.get(name, []):
            fn(payload)


class DemoServices:
    """Named service ports (offer/call). The demo relies on two of them:
    m5.apply_event (life-support deltas) and alcohol.ingest (drinks)."""
    def __init__(self):
        self.ports = {}
    def offer(self, name, fn):
        self.ports[name] = fn
    def call(self, name, *args, default=None, **kwargs):
        fn = self.ports.get(name)
        if fn is None:
            return default
        return fn(*args, **kwargs)


class DemoLog:
    def __init__(self):
        self.records = []
    def record(self, *args, **kwargs):
        self.records.append((args, kwargs))


class DemoCard:
    """Persona card: a Parisian laborer, 1789. Empty fields mean full
    defaults; individual differences come from each citizen's own seed."""
    social_sensitivity = "sensitive"
    tribe = "laborer"
    pyramid_position = {"objective_position": 0.15, "initial_mode": "survival_drive"}
    legacy = {"parenting_style": "authoritative", "has_children": True}
    character_name = "Citizen"
    cyclic_modulation = {}
    alcohol_profile = {}
    body_metrics = {}
    core_memories = []
    ice_box = {}
    identity = {}
    life_support = {}
    moral_framework = {}
    philosophy = {}
    systemic_load = {}
    thermal_profile = {}
    trauma_imprints = []
    a_priori_plasticity = 0.5


class _Hormones:
    def compute_effective_levels(self):
        return {}


class _Odp:
    """Kernel-absent stand-in for the ODP weight oracle: deterministic
    pseudo-weights derived from the query, in the 0.55-0.90 band."""
    def get(self, *args):
        if not args:
            return 0.0
        return 0.55 + 0.35 * ((hash(str(args[0])) % 100) / 100.0)
    def nudge(self, *args, **kwargs):
        return None
    def snapshot(self):
        return {}


class _Btcs:
    def get(self, key, default=0.0):
        return default
    def letter(self, key):
        return None
    def copy_coords(self):
        return {}
    def drift(self, *args, **kwargs):
        return None


class _Sleep:
    sleep_debt_hours = 0.0


class DemoK:
    """Kernel port bundle. Ports that are genuinely absent (memory, language,
    columnar, discharge) are None — modules are contract-bound to guard for
    that, and the demo quietly verifies they do."""
    card = DemoCard()
    memory = None
    language = None
    columnar = None
    btcs = _Btcs()
    hormones = _Hormones()
    odp = _Odp()
    sleep = _Sleep()
    discharge = None


class DemoCtx:
    """Per-citizen context: each citizen gets its OWN board/bus/services/RNG,
    so 100 stacks evolve 100 different inner lives under one script."""
    def __init__(self, seed=0):
        self._seed = seed
        self.board = DemoBoard()
        self.bus = DemoBus()
        self.services = DemoServices()
        self.log = DemoLog()
        self.k = DemoK()
    def rng_for(self, mid):
        return DemoRNG(hash((self._seed, mid)) & 0x7FFFFFFF)


# ---------------- Script ----------------
def scenario(tick):
    """The environment shared by the whole city: returns (data, env, beat).

    Every citizen receives the same scene each tick, but each module stack
    metabolizes it through its own accumulated state — that is where the
    crowd's diversity comes from.
    """
    data = {"dt": 1.0, "user_input": "", "stimuli": [], "themes": [],
            "speaker": "crowd", "scene": None, "emotion": None}
    env = {"sys.last_strategy_name": "gather",
           "sys.last_scene_themes": [], "sys.prev_scene_valence": 0.0}

    def feel(v, a, label=""):
        data["emotion"] = types.SimpleNamespace(valence=v, arousal=a,
                                                label=label)

    def scene(t):
        data["scene"] = types.SimpleNamespace(integrated_theme=t)

    if tick <= 20:                                # bread and hunger
        beat = "bread"
        data["user_input"] = "Bread is up again. Third time this month."
        data["stimuli"] = [{"category": "hunger", "text": "empty stomach"}]
        data["themes"] = ["hunger", "price hike"]
        data["urgency"] = 1
        scene("Faubourg Saint-Antoine streets"); feel(-0.5, 0.4, "resentment")
        env["sys.last_strategy_name"] = "endure"
        env["sys.prev_scene_valence"] = -0.5
    elif tick <= 40:                              # assembly in the square
        beat = "assembly"
        data["user_input"] = ("Someone is shouting: the Third Estate is "
                              "nothing; the Third Estate is everything!")
        data["stimuli"] = [{"category": "speech", "text": "oration"},
                           {"category": "rumor", "text": "the garrison will fire the cannons"}]
        data["themes"] = ["assembly", "oration", "rumor"]
        data["scene_intensity"] = 0.6
        data["urgency"] = 2
        scene("Place de l'Hotel de Ville"); feel(-0.3, 0.7, "inflamed")
        env["sys.last_strategy_name"] = "assemble"
        env["sys.prev_scene_valence"] = -0.3
    elif tick <= 60:                              # the march on the Bastille
        beat = "march"
        data["user_input"] = "To the Bastille! Hand over the gunpowder!"
        data["stimuli"] = [{"category": "march", "text": "the crowd surges"}]
        data["themes"] = ["march", "gunpowder"]
        data["objective_cmd"] = "storm_the_fortress"
        data["odp_detect"] = "crowd_vs_guard"
        data["scene_intensity"] = 0.8
        data["urgency"] = 3
        scene("before the Bastille gates"); feel(-0.2, 0.9, "fury")
        env["sys.last_strategy_name"] = "charge"
        env["sys.prev_scene_valence"] = -0.2
    elif tick <= 75:                              # the garrison opens fire
        beat = "gunfire"
        data["user_input"] = "They're firing! They're firing into the crowd!"
        data["stimuli"] = [{"category": "gunfire", "text": "volley fire"},
                           {"category": "scream", "text": "screams"}]
        data["themes"] = ["gunfire", "the fallen"]
        data["scene_intensity"] = 1.0
        data["urgency"] = 3
        scene("gun smoke"); feel(-0.9, 1.0, "terror_rage")
        env["sys.last_strategy_name"] = "fight_or_fall"
        env["sys.prev_scene_valence"] = -0.9
    elif tick <= 90:                              # the fortress falls
        beat = "storm"
        data["user_input"] = "The drawbridge is down! Get in! The Bastille has fallen!"
        data["stimuli"] = [{"category": "surge", "text": "the human flood breaks through"}]
        data["themes"] = ["the fall"]
        data["scene_intensity"] = 0.9
        data["urgency"] = 2
        scene("fortress courtyard"); feel(0.3, 1.0, "fevered_triumph")
        env["sys.last_strategy_name"] = "overrun"
        env["sys.prev_scene_valence"] = 0.3
    else:                                         # dusk roll call
        beat = "dusk"
        data["user_input"] = "Carry the dead home. Remember their names."
        data["themes"] = ["roll call", "mourning"]
        data["memory_resurfaced"] = True
        scene("dusk"); feel(-0.4, 0.3, "mourning")
        env["sys.last_strategy_name"] = "mourn"
        env["sys.prev_scene_valence"] = -0.4
    return data, env, beat


def main():
    master = random.Random(17890714)

    # ---- 100 independent module stacks ----
    # Installation goes through the same dlc_spec protocol the real engine
    # uses: factory(ctx) builds the instance, bind(inst, ctx) returns the
    # per-phase hooks. From here on the demo only calls hooks + services.
    citizens = []
    for i in range(N_CITIZENS):
        ctx = DemoCtx(seed=1000 + i)
        installed = []
        for n in MOD_NAMES:
            spec = importlib.import_module(n).dlc_spec()
            inst = spec["factory"](ctx)
            hooks = spec["bind"](inst, ctx)
            installed.append((n, spec, inst, hooks))
        citizens.append({
            "id": i, "ctx": ctx, "installed": installed,
            "hunger": master.uniform(0.6, 1.0),      # household poverty varies
            "drinker": master.random() < 0.25,       # a quarter of them drink
            "hit": False, "mortal": False, "dead": False,
        })

    trace = []
    LAST = 100
    for tick in range(1, LAST + 1):
        data, env, beat = scenario(tick)
        for c in citizens:
            if c["dead"]:
                continue
            ctx = c["ctx"]
            for k, v in env.items():
                ctx.board.store[k] = v
            # Hunger erodes life support (every 10 ticks for the first 40)
            if tick <= 40 and tick % 10 == 0:
                ctx.services.call("m5.apply_event", tick, "food",
                                  -0.08 * c["hunger"], "bread price hike")
            # Drinkers fortify themselves during the assembly
            if c["drinker"] and 21 <= tick <= 40 and tick % 5 == 0:
                ctx.services.call("alcohol.ingest", tick, 0.8, "liquid courage")
            # Firing window: a per-tick lottery decides who gets hit.
            # 0.035/tick across 15 ticks with 30% of hits mortal lands the
            # death toll near the historical proportion (~10-15%).
            if beat == "gunfire" and not c["hit"] \
                    and master.random() < 0.035:
                c["hit"] = True
                c["mortal"] = master.random() < 0.30   # 30% of hits are lethal
                for dim, d in (("medical care", -0.45), ("food", -0.2),
                               ("economy", -0.25), ("social status", -0.2),
                               ("housing", -0.2), ("clothing", -0.2),
                               ("transportation", -0.25), ("water", -0.2)):
                    ctx.services.call("m5.apply_event", tick, dim, d, "gunshot wound")
                data_hit = dict(data)
                data_hit["trauma_event"] = {
                    "passive_victim": True, "action_success": 0.0,
                    "event_intensity": 0.95, "social_support": 0.5,
                    "valence": -0.9, "srf_peak": 70.0, "theme": "shot by the garrison"}
                for n, spec, inst, hooks in c["installed"]:
                    for phase in PHASE_ORDER:
                        hk = hooks.get(phase)
                        if hk is None:
                            continue
                        g = (spec.get("gear") or {}).get(phase)
                        trig = (g or {}).get("trigger")
                        # No-trigger-no-run: a hook fires only when its gear
                        # trigger passes (or the gear defines none).
                        if trig is None or trig(tick, data_hit):
                            hk(tick, data_hit)
                continue
            # Witness trauma for the un-hit within the firing window
            if beat == "gunfire" and master.random() < 0.20:
                data = dict(data)
                data["trauma_event"] = {
                    "witnessed_target": True, "witnessed_relation": 0.8,
                    "action_success": 0.1, "event_intensity": 0.85,
                    "social_support": 0.5, "valence": -0.8,
                    "srf_peak": 55.0, "theme": "watched a neighbor get shot"}
            for n, spec, inst, hooks in c["installed"]:
                for phase in PHASE_ORDER:
                    hk = hooks.get(phase)
                    if hk is None:
                        continue
                    g = (spec.get("gear") or {}).get(phase)
                    trig = (g or {}).get("trigger")
                    if trig is None or trig(tick, data):
                        hk(tick, data)
            # Mortal wounds keep deteriorating toward flatline; the lightly
            # wounded receive mutual aid once the fortress falls — this is
            # what separates "wounded" from "dead".
            if c["mortal"]:
                for dim in ("medical care", "food", "water", "economy",
                            "housing", "clothing", "transportation",
                            "social status"):
                    ctx.services.call("m5.apply_event", tick, dim, -0.10,
                                      "mortal wound festering")
            elif c["hit"] and beat in ("storm", "dusk") \
                    and master.random() < 0.7:
                for dim in ("medical care", "food", "water"):
                    ctx.services.call("m5.apply_event", tick, dim, +0.10,
                                      "citizen mutual aid")
            # M5 flatline = all eight life-support dimensions <= 0.05
            # simultaneously = clinical death.
            if ctx.board.read("M5.life_support.flatline"):
                c["dead"] = True

        if tick % 10 == 0 or tick in (61, 75, 76):
            stats = crowd_stats(citizens)
            stats["tick"] = tick
            stats["beat"] = beat
            trace.append(stats)
            print(f"[t={tick:>3} {beat:>9}] alive={stats['alive']:>3} "
                  f"dead={stats['dead']:>2} hit={stats['hit']:>2} "
                  f"avg_social_support={stats['avg_social_support']:.2f} "
                  f"trauma_imprints={stats['trauma_active']:>2} "
                  f"drunk>=tier2={stats['drunk']:>2}")

    # ---- Epilogue ----
    dead = [c["id"] for c in citizens if c["dead"]]
    hit_alive = [c["id"] for c in citizens if c["hit"] and not c["dead"]]
    print("\n================ Dusk Roll Call ================")
    print(f"Dead: {len(dead)} — {dead}")
    print(f"Wounded survivors: {len(hit_alive)} — {hit_alive[:20]}{'...' if len(hit_alive) > 20 else ''}")
    print(f"Final average social support: {trace[-1]['avg_social_support']:.3f}")
    print(f"Citizens carrying trauma imprints: {trace[-1]['trauma_active']}")
    # The inner voice of three survivors, straight from M2's monologue buffer
    shown = 0
    for c in citizens:
        if not c["dead"] and shown < 3:
            utt = c["ctx"].board.read("M2.monologue.utterance") or {}
            if utt.get("text"):
                print(f"Citizen #{c['id']} inner voice: {utt['text'][:90]}")
                shown += 1

    with open("demo_bastille_trace.json", "w", encoding="utf-8") as f:
        json.dump({"trace": trace, "dead": dead, "hit_alive": hit_alive},
                  f, ensure_ascii=False, indent=1, default=str)
    print("\nSamples written to demo_bastille_trace.json")


def crowd_stats(citizens):
    alive = [c for c in citizens if not c["dead"]]
    sse, trauma, drunk = [], 0, 0
    for c in alive:
        v = c["ctx"].board.read("M5.governor.social_support")
        if isinstance(v, (int, float)):
            sse.append(v)
        m8 = next(i2 for n2, s2, i2, h2 in c["installed"]
                  if n2 == "m8_trauma")
        if len(getattr(m8, "imprints", []) or []) > 0:
            trauma += 1
        tier = c["ctx"].board.read("M4.alcohol.tier") or 0
        if isinstance(tier, (int, float)) and tier >= 2:
            drunk += 1
    return {"alive": len(alive),
            "dead": len(citizens) - len(alive),
            "hit": sum(1 for c in citizens if c["hit"]),
            "avg_social_support": sum(sse) / len(sse) if sse else 0.0,
            "trauma_active": trauma, "drunk": drunk}


if __name__ == "__main__":
    main()
