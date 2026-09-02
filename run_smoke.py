# -*- coding: utf-8 -*-
"""ABMI 开源版装配冒烟入口:27 模块全装,100 tick 对话场景,确定性双跑校验。"""
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from abmi_v1_0 import KernelAssembler, MODE_DIALOGUE
from abmi_v1_0.kernel.persona import PersonaConfig

MODULE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "abmi_v1_0", "modules")

SCRIPT = {
    5: "你好,小钱。",
    20: "今天想喝点什么?",
    40: "有人骂了你一句很难听的。",
    60: "给你带了西湖龙井。",
    80: "我们去接水喝吧。",
}


def build(seed: int = 42):
    card = PersonaConfig(
        name="小钱",
        btcs={"IE": 62.0, "SN": 48.0, "TF": 41.0, "JP": 55.0},
        interests=["lovelive", "西湖龙井"],
    )
    asm = KernelAssembler(card=card, seed=seed, mode=MODE_DIALOGUE,
                          module_dir=MODULE_DIR)
    return asm.assemble()


def fingerprint(engine, ticks: int = 100) -> str:
    parts = []
    for t in range(ticks):
        r = engine.execute_computation_cycle(user_input=SCRIPT.get(t))
        parts.append(json.dumps(r, sort_keys=True, ensure_ascii=False, default=str))
    parts.append(json.dumps(engine.snapshot(), sort_keys=True,
                            ensure_ascii=False, default=str))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def main() -> None:
    e1 = build()
    ids = [m.module_id for m in e1.registry.all()]
    print(f"assembled: {len(ids)} modules")
    for mid in ids:
        print("  -", mid)
    h1 = fingerprint(e1)
    h2 = fingerprint(build())
    print("run1:", h1)
    print("run2:", h2)
    print("deterministic:", h1 == h2)


if __name__ == "__main__":
    main()
