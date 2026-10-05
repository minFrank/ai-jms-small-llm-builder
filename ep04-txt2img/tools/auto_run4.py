#!/usr/bin/env python
"""ep04 三方案扩样本自动续跑(Python 版外层循环)。

每轮:读 progress,找缺格的方案 → 子进程跑 bench4(断点续跑会跳过已有)→
死掉/超时就下一轮接着来,直到 18 格全 ok 或 60 轮上限。
"""
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
PY = r"D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
PROG = os.path.join(E, "logs", "bench4-progress.json")
SCHEMES = ["diffusers", "sdcpp-cpu", "sdcpp-vulkan"]


def status():
    try:
        d = json.load(open(PROG, encoding="utf-8"))
    except Exception:
        return {}, 0
    ok_sc = set()
    for sc in SCHEMES:
        n = len([r for r in d["rows"]
                 if r["scheme"] == sc and "_s" in r["cell"] and r["ok"]])
        if n >= 6:
            ok_sc.add(sc)
    total = len([r for r in d["rows"] if "_s" in r["cell"] and r["ok"]])
    return ok_sc, total


for rnd in range(1, 61):
    ok, total = status()
    missing = [s for s in SCHEMES if s not in ok]
    print(f"[round {rnd}] ok={total}/18 missing={missing} {time.strftime('%H:%M:%S')}",
          flush=True)
    if not missing:
        print("ALL 18 CELLS DONE", flush=True)
        break
    target = missing[0]
    log = os.path.join(E, "logs", f"auto_{target}.log")
    try:
        with open(log, "a", encoding="utf-8") as fh:
            subprocess.run([PY, os.path.join(E, "tools", "bench4.py"),
                            "--only", target],
                           cwd=E, stdout=fh, stderr=subprocess.STDOUT,
                           timeout=3600)
        print(f"  {target} 子进程返回", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  {target} 超时(3600s),重来", flush=True)
    except Exception as exc:
        print(f"  {target} 异常 {exc!r}", flush=True)
    time.sleep(10)
else:
    print("GAVE UP after 60 rounds", flush=True)
