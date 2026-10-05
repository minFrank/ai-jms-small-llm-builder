# -*- coding: utf-8 -*-
"""ep4 单格 driver:每轮跑恰好 1 格(--once,正常退出不留孤儿),直到 18 格全 ok。

轮间 sleep 2s;每轮打印进度。任何一格失败也继续轮换(断点续跑兜底)。
"""
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
PY = r"D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
PROG = E + "/logs/bench4-progress.json"
SCHEMES = ["diffusers", "sdcpp-cpu", "sdcpp-vulkan"]


def status():
    try:
        d = json.load(open(PROG, encoding="utf-8"))
    except Exception:
        return set(), 0
    ok_sc = set()
    for sc in SCHEMES:
        n = len([r for r in d["rows"]
                 if r["scheme"] == sc and "_s" in r["cell"] and r["ok"]])
        if n >= 6:
            ok_sc.add(sc)
    total = len([r for r in d["rows"] if "_s" in r["cell"] and r["ok"]])
    return ok_sc, total


for rnd in range(1, 80):
    ok_sc, total = status()
    missing = [s for s in SCHEMES if s not in ok_sc]
    print(f"[round {rnd}] {total}/18 missing={missing} {time.strftime('%H:%M:%S')}",
          flush=True)
    if not missing:
        print("ALL 18 CELLS DONE", flush=True)
        break
    target = missing[0]
    t0 = time.time()
    try:
        subprocess.run([PY, "tools/bench4.py", "--only", target, "--once"],
                       cwd=E, timeout=400)
    except subprocess.TimeoutExpired:
        print(f"  {target} 超时 400s(下一格会重跑此格)", flush=True)
    except Exception as exc:
        print(f"  {target} 异常 {exc!r}", flush=True)
    print(f"  {target} 轮耗时 {time.time()-t0:.0f}s", flush=True)
    time.sleep(2)
else:
    print("GAVE UP after 80 rounds", flush=True)
