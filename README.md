# ABMI — Artificial Bionic Mind Intelligence

> **The soul is computed, not prompted.**

**Status:** Full module source code released.
*For Play, please refer to https://github.com/Hinavvi/ABMI-in-OpenCode-plugin.*

**License:** Business Source License 1.1 (BSL-1.1)

- Free for personal use, learning, testing, research, and non-commercial development.
- Commercial/production use by any enterprise or institution with **annual revenue > USD 100,000** or **a team of more than 10 people** requires a commercial license — contact **palette1919@qq.com** for commercial licensing inquiries.
- Automatically converts to **Apache License 2.0** on **2029-08-05**.

See `LICENSE` for the full text.

---

## What is ABMI?

ABMI is a deterministic, modular digital-mind engine. You provide a **persona card** and a **world**; the engine advances time tick-by-tick. A set of hot-swappable mind modules computes, at every tick, what this person feels, fears, represses, drinks, remembers, and becomes — from the physiological layer up to the moral layer.

ABMI's soul is not a "character sheet" with preset reactions. Anger, courage, trauma, intoxication, grief — all of these **emerge** from the interaction of 14 independent modules sharing a single blackboard. Each module simulates a different facet of the human mind.

### What It Is Not

- **Not an LLM wrapper.** No prompts, no tokens, no API calls. The soul runs entirely on local arithmetic.
- **Not a behavior tree or finite state machine.** No one "scripts" a character to "be angry now." States are computed, not assigned.
- **Not a chatbot framework.** There is no dialogue manager here; there is only a mind.

### What Can It Do?

- Virtual companions & LLM roleplay (easy to deploy; works with Web-LLM via the Glue layer)
- Bionic mind modeling for research
- Narrative content generation and reference
- Diverse NPC adaptation for game worlds
- Agent intelligence research

---

## How to Write a Persona Card

Creating a persona card is straightforward. The **bare minimum** requires only four fields:

- **Name**
- **Sex**
- **Personality traits** — e.g., introverted or extroverted, decisive or hesitant, sensitive or thick-skinned
- **Things they like to do** — hobbies, interests, obsessions

For a richer experience, write freely in **natural language**: add backstory, relationships, core memories, moral frameworks, fears, attachment figures, or anything else that defines the subject. There is no rigid template — ABMI ingests the card declaratively.

Once your description is ready, hand it to a **Web LLM** and ask it to encode the text into the structured `PersonaConfig` format (JSON or YAML). Then import the resulting card into your engine deployment. The engine will do the rest.

---

## Quick Start (Hello World)

```python
from abmi_v1_0.kernel.persona import PersonaConfig
from abmi_v1_0.assembly import KernelAssembler

# 1. Create a persona card — only name and BTCS coordinates are required
card = PersonaConfig(
    name="Alex",
    btcs={"IE": 35.0, "SN": 60.0, "TF": 45.0, "JP": 30.0},  # I-N-F-P tendency
    body_metrics={"sex": "M", "height_cm": 175, "weight_kg": 65},
)

# 2. Assemble the engine (seed determines the deterministic worldline)
assembler = KernelAssembler(card=card, seed=42, mode="dialogue")
engine = assembler.assemble()

# 3. Advance one tick: no external input, just autonomic physiology and cognition
result = engine.execute_computation_cycle(
    user_input=None,      # no dialogue input this turn
    stimuli=None,         # no external physical stimuli
    dt_minutes=1.0        # narrative time: 1 minute
)

# 4. Read the tick output (report dict auto-assembled by P8 readout)
print("Tick:", result["tick"])
print("Emotion:", result.get("emotion", {}).get("label"))
print("Strategy:", result.get("behavior", {}).get("strategy"))
print("Monologue:", result.get("monologue", {}).get("text"))
print("Voice prompt:\n", result.get("language", {}).get("prompt"))
```

Sample output:

```text
Tick: 1
Emotion: neutral
Strategy: low-arousal rest
Monologue: None
Voice prompt:
[speaking manner] normal · moderate rate · medium length · situation-dependent
[content hint] theme: default_scan_mode · affective state: neutral · register: generic
[taboos] keep persona consistency; do not leave the affective baseline
```

Key conventions:

- `mode="dialogue"`: one tick = one dialogue turn; `dt_minutes` is user-defined.
- `mode="server"`: one tick = 0.1 ms computation step; `dt_minutes` is fixed automatically.
- All downstream modules read only the blackboard and contract keys; they never import each other.

---

## System Requirements

| Item | Requirement | Notes |
|---|---|---|
| Python | ≥ 3.9 | Uses `from __future__ import annotations`, `TypedDict`, `dataclasses`, etc. Not verified below 3.9. |
| Dependencies | Zero third-party | Standard library only: `threading`, `random`, `dataclasses`, `typing`, `collections`, `math`, `hashlib`, `copy`, `json`, `re`, `importlib`, `os`, `sys`, `urllib` (optional, for Glue API backend). |
| Memory | 30–50 MB per instance | Single citizen, full 14-module stack, including capped decision log (50,000 entries). |
| Performance | 0.06–0.07 ms/tick | Desktop i5-13500 class, single-threaded. The 100-citizen × 100-tick Bastille demo completes in 2 seconds including interpreter startup. |
| Disk | None at runtime | Pure in-memory computation. Persist via `engine.snapshot()` if needed. |

Compatibility notes:

- Deterministic RNG uses `hashlib.sha256` for stream derivation — reproducible across processes (the older `hash()` was process-salted and has been retired).
- Thread-safe: `Blackboard` uses `threading.RLock`; `DecisionLog` uses `threading.Lock`. Safe to call from multi-threaded contexts (e.g., web services).

---

## Demo: Storming of the Bastille (1789-07-14)

100 Parisian citizens, each running a full, independent 14-module stack, share 100 minutes of history: bread prices, assembly, march, volley fire, fortress fall, dusk roll call.

No citizen's behavior is scripted. Who drinks for courage, who is hit, whose wounds degrade to clinical death (M5 life-support flatline), who merely watches a neighbor fall and carries that imprint for life (M8 vicarious trauma) — the engine decides citizen by citizen.

### How to Run

```bash
# Place the 14 module files (M1–M15) into ./modules/, or:
export ABMI_MODULE_DIR=/path/to/modules
python3 "ABMI Demo Bastille EN.py"
```

(Module source will land in this repository within 3 days — the demo is released now so you can verify the output below against the source when it arrives.)

### Sample Output

```text
[t= 10     bread] alive=100 dead= 0 hit= 0 avg_social_support=0.69 trauma_imprints= 0 drunk>=tier2= 0
[t= 20     bread] alive=100 dead= 0 hit= 0 avg_social_support=0.68 trauma_imprints= 0 drunk>=tier2= 0
[t= 30  assembly] alive=100 dead= 0 hit= 0 avg_social_support=0.67 trauma_imprints= 0 drunk>=tier2= 0
[t= 40  assembly] alive=100 dead= 0 hit= 0 avg_social_support=0.66 trauma_imprints= 0 drunk>=tier2=21
[t= 50     march] alive=100 dead= 0 hit= 0 avg_social_support=0.66 trauma_imprints= 0 drunk>=tier2=21
[t= 60     march] alive=100 dead= 0 hit= 0 avg_social_support=0.66 trauma_imprints= 0 drunk>=tier2=21
[t= 61   gunfire] alive=100 dead= 0 hit= 4 avg_social_support=0.65 trauma_imprints=100 drunk>=tier2= 0
[t= 70   gunfire] alive= 98 dead= 2 hit=26 avg_social_support=0.59 trauma_imprints=98 drunk>=tier2= 0
[t= 75   gunfire] alive= 93 dead= 7 hit=34 avg_social_support=0.58 trauma_imprints=93 drunk>=tier2= 0
[t= 76     storm] alive= 93 dead= 7 hit=34 avg_social_support=0.57 trauma_imprints=93 drunk>=tier2= 0
[t= 80     storm] alive= 88 dead=12 hit=34 avg_social_support=0.61 trauma_imprints=88 drunk>=tier2= 0
[t= 90     storm] alive= 88 dead=12 hit=34 avg_social_support=0.64 trauma_imprints=88 drunk>=tier2= 0
[t=100      dusk] alive= 88 dead=12 hit=34 avg_social_support=0.67 trauma_imprints=88 drunk>=tier2= 0

================ Dusk Roll Call ================
Dead: 12 — [1, 9, 36, 37, 45, 54, 66, 72, 75, 83, 87, 95]
Wounded survivors: 22 — [10, 11, 15, 21, 22, 25, 27, 28, 30, 32, 33, 48, 50, 55, 62, 69, 73, 76, 78, 88]...
Final average social support: 0.665
Citizens carrying trauma imprints: 88
Citizen #0 inner voice: a past state suddenly surfaced, overlapping with the current scene
Citizen #2 inner voice: a past state suddenly surfaced, overlapping with the current scene
Citizen #3 inner voice: a past state suddenly surfaced, overlapping with the current scene
```

Read the dusk roll call line again: every surviving citizen carries at least one trauma imprint. No one wrote that rule. Fifteen minutes of gunfire does this to a crowd — and the engine already knew.

---

## Why It Matters

- **Deterministic design.** Same seed, same worldline — exact to the byte. Two consecutive runs of the demo above produce identical output. Snapshot/restore replay is exact.
- **Tick sovereignty.** Only the engine owns time. Modules respond to ticks; no module can tamper with the clock.
- **No trigger, no run.** Every module hook is mounted on a gear with an explicit trigger. Silent-state computation costs zero.
- **Fully decoupled.** Modules never import or name each other. They read and write a shared blackboard via pre-registered contract keys and expose named service ports. The engine does not know any module's name.
- **Fast enough to ignore.** On a mainstream desktop (i5-13500 class), a full 14-module stack takes 0.06–0.07 ms per tick single-threaded — roughly 15,000 ticks/sec per core. The entire 100-citizen × 100-tick demo finishes in about 2 seconds including interpreter startup. (Cloud benchmark on AMD EPYC 9K65: 0.074 ms/tick; desktop figures are single-thread ratio estimates and will be updated with real hardware data at source release.)
- **Zero dependencies.** Pure Python standard library. If Python runs, ABMI runs.

---

## Architecture

```text
            ┌─────────────────────────────────────┐
            │   Core — tick loop & phase scheduler │
            │   P0 Input → P1 Body → P2 Boundary  │
            │   → P3 Cognition → P4 Decision      │
            │   → P6 Maintenance                  │
            └───────────────┬─────────────────────┘
                            │ tick only; clock ownership
            ┌───────────────▼─────────────────────┐
            │   Kernel — persona card, affective  │
            │   state, hormone/sleep/weight       │
            │   oracles                           │
            └───────────────┬─────────────────────┘
                            │ blackboard + service ports
   ┌────────┬────────┬──────▼─────┬────────┬────────┬────────┐
   │ M1     │ M2     │ M3 … M11   │ IDNS   │ M15    │  …     │
   │ Cycle  │ Mono-  │ Physiology │ Hub    │ Out-   │        │
   │        │ logue  │ & Cognition│ M12–14 │ post   │        │
   └────────┴────────┴────────────┴────────┴────────┴────────┘
        14 hot-swappable DLC modules installed via dlc_spec,
        unknown to the engine and to each other
```

---

## The 14 Modules (M1–M15)

| Module | Domain | One-line Description |
|---|---|---|
| M1.cycle | Physiology | Autonomic cycle state modulation |
| M2.monologue | Cognition | Inner voice — trigger arcs, repression, rumination |
| M3.life_baseline | Physiology | Systemic Load Index (CIdx) |
| M4.tmo | Physiology | Targeted metabolic onset |
| M4.alcohol | Physiology | Alcohol metabolism, tiers, withdrawal |
| M5.governor | Cognition | Life-support assessment, 8 dimensions; zero = clinical death |
| M6.odp | Cognition | Disposition conflict detection |
| M7.iceberg | Cognition | Conscious / preconscious / unconscious routing |
| M8.trauma | Cognition | Trauma encoding & imprints (including vicarious) |
| M9.epistemology | Cognition | Experience, a priori, transcendence |
| M10.morality | Cognition | Morality & identity |
| M11.thermal | Somatic | Core/skin dual-track thermodynamics |
| IDNS.hub (M12–M14) | Boundary | Introspective neuro-semantic system |
| M15.outpost | Boundary | Conduction block: frontier inspection & echo channel |

---

## Design Principles (Constitution, Excerpt)

1. The engine owns every tick; no module may write time.
2. No trigger, no run — idle modules consume zero resources.
3. Modules are fully decoupled: communicate only via blackboard + contract keys + service ports.
4. The engine never branches on module identity.
5. Determinism is a feature, not an accident: every module uses seeded RNG; snapshot/restore is a first-class citizen.

---

## Snapshot & Restore

ABMI's core guarantee is exact time travel. The engine aggregates the full internal state of every module (including RNG stream cursors, governance ledgers, and event-bus mailboxes) and deep-freezes it, ensuring historical saves are never polluted by live references.

```python
import json

# ---- Save ----
snap = engine.snapshot()          # returns a deeply frozen nested dict
with open("save.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, indent=2)

# ---- Load ----
with open("save.json", "r", encoding="utf-8") as f:
    snap = json.load(f)

engine.restore(snap)              # re-inject every module, clock, gear, board, bus, gov

# Verify: same seed + same snapshot -> byte-identical subsequent output
result1 = engine.execute_computation_cycle()
```

Assembler helper interface (recommended):

```python
from abmi_v1_0.assembly import KernelAssembler

assembler = KernelAssembler(card=card, seed=42)
engine = assembler.assemble()

# Quick save/load
snap = assembler.snapshot(engine)
assembler.restore(engine, snap)
```

What the snapshot contains:

- `time`: computation tick, narrative minutes, mode, epoch
- `gears`: gear-scheduler statistics (rebuilt from registry after restore)
- `board`: full blackboard data + knob table
- `bus`: pending event queue + cross-tick mailbox
- `gov`: consciousness state machine, trust ledger, audit record, kheshig siege state
- `modules`: each installed module's `snapshot()` output, indexed by `snapshot_label`

> **Important:** `restore` is an inter-tick operation. Calling `restore` inside `execute_computation_cycle` would rewind the clock/blackboard and violate tick sovereignty. Call it between ticks from the scene side.

---

## Error Handling & Debugging

ABMI does not use a traditional `ABMI_DEBUG=1` environment variable. Instead, it provides three layers of self-diagnosis.

### 1. Decision Log

The engine maintains an append-only log with a hard cap of 50,000 entries; oldest entries are dropped when the cap is exceeded.

```python
# Inspect the last 10 entries
for entry in engine._log.entries[-10:]:
    print(f"[t={entry['tick']}] {entry['module']} | {entry['event']} | {entry['payload']}")
```

Log fields: `tick`, `module`, `event`, `payload`, `rng_position` (for auditing RNG skips).

### 2. Dangling Contract Detection

Run automatically at startup; also callable manually:

```python
# Check for unprovided contract keys after assembly
dangling = engine.dangling_contracts()
if dangling:
    print("The following contract keys have no provider:", dangling)

# Full validation (type matches declared default)
status = engine.check_contracts()
# Returns: {"sys.pain": "ok", "sys.flatline": "missing", ...}
```

### 3. Startup Self-Check (Fail-Fast)

`KernelAssembler._verify()` runs automatically at the end of `assemble()`. Any failure raises `RuntimeError`:

- `engine.smoke()` fails → skeleton not initialized correctly
- `engine.invariants()` fails → time/gear/blackboard invariants violated
- `dangling_contracts` exist → logged as warning only, non-fatal (soft check per Constitution §24)

### 4. Module Installation Diagnostics

DLC installation errors are caught and written to the log without breaking hot-plug:

```python
# Typical log entries (search DecisionLog for these):
# module: "dlc.install", event: "factory_error", payload: "M4.tmo: TypeError"
# module: "dlc.install", event: "bind_error", payload: "M8.trauma: AttributeError"
# module: "dlc.install", event: "dormant", payload: "M6.odp: hard requirement unmet ['K.odp']"
```

### Quick Troubleshooting Guide

| Symptom | Check |
|---|---|
| `RuntimeError: V8 engine smoke failed at assembly` | Verify `KernelBundle` has fully assembled the governance quartet (`consciousness`, `trust`, `audit`, `kheshig`). |
| Module hook not executing | Verify `dlc_spec` `gear` phase names use `P0..P8` or legacy aliases; verify `trigger` returns `True`. |
| Contract key always reads default | Verify the provider module calls `board.publish(key, value)`; verify `CONTRACT_MIRROR` maps legacy keys to `sys.*`. |
| Output diverges after snapshot restore | Verify all modules implement `restore()`; verify `snapshot_label` is unique; verify RNG stream cursors are saved/restored. |
| Siege entered but never lifts | Verify `engine.py` `siege_predicate` reads `sys.idns_active` (V4.2 fix: older builds used P1 hook count as proxy, causing permanent lock). |

---

## Testing & Reproducibility

- Integration matrix: 46/46 green (module assembly, contract keys, trigger chains, snapshot-restore determinism).
- The demo output in this README is machine-generated, not hand-typed. It can be reproduced byte-for-byte from the released script plus module source.

---

## Roadmap

- **Within 3 days:** Full M1–M15 module source, right in this repository.
- **With the source drop:** Additional scenario demos (including a classic Chinese crosstalk scene you have to see to believe), benchmark scripts, and the full integration test suite.

---

## License

This project is licensed under the **Business Source License 1.1**. On **2029-08-05**, it converts to the **Apache License, Version 2.0**. See `LICENSE` for details.

- Free for personal use, learning, testing, research, and non-commercial development.
- Commercial/production use by any enterprise or institution with **annual revenue > USD 100,000** or **a team of more than 10 people** requires a commercial license — contact **palette1919@qq.com**.
