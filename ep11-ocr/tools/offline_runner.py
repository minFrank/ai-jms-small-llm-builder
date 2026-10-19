# -*- coding: utf-8 -*-
"""断网批编排：独立 progress / 独立产物目录 / 独立日志，避免与在线批互相跳过。"""
import os
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
S = os.path.join(BASE, "output", "samples")
ALL = sorted(os.path.splitext(f)[0] for f in os.listdir(S) if f.endswith(".png"))


def imgs(names):
    return [os.path.join(S, n + ".png") for n in names]


COMMON = ["--progress", os.path.join(BASE, "progress_offline.json"),
          "--out-root", os.path.join(BASE, "output", "cells_offline"),
          "--log-dir", os.path.join(BASE, "logs_offline"),
          "--offline", "1", "--allow-busy", "--skip-burnin"]

PHASES = [
    ("offA_hot", ["--engines", "rapidocr", "paddleocr", "--imgs"] + imgs(ALL) +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "0", "--session", "offA"]),
    ("offB_cold", ["--engines", "rapidocr", "paddleocr", "--imgs"] +
     imgs(["invoice_01", "book_01"]) +
     ["--cold-runs", "1", "--hot-runs", "0", "--warmup", "0", "--session", "offB"]),
    ("offC_got", ["--engines", "gotocr", "--imgs"] + imgs(["invoice_01", "table_01"]) +
     ["--cold-runs", "1", "--hot-runs", "1", "--warmup", "0", "--session", "offC"]),
]

if __name__ == "__main__":
    # guard 自检（与引擎尝试分开计数）
    with open(os.path.join(BASE, "logs", "phase_offline_selftest.log"), "w",
              encoding="utf-8") as lf:
        subprocess.run([PY, "-u", os.path.join(BASE, "probe_offline.py")],
                       cwd=BASE, stdout=lf, stderr=subprocess.STDOUT)
    for name, args in PHASES:
        logp = os.path.join(BASE, "logs", "phase_%s.log" % name)
        cmd = [PY, "-u", os.path.join(BASE, "driver.py")] + args + COMMON
        t0 = time.time()
        with open(logp, "w", encoding="utf-8") as lf:
            lf.write("# cmd: %s\n" % " ".join(cmd))
            lf.flush()
            rc = subprocess.run(cmd, cwd=BASE, stdout=lf,
                                stderr=subprocess.STDOUT).returncode
        print("[offline %s] rc=%d dur=%.0fs" % (name, rc, time.time() - t0), flush=True)
    print("OFFLINE DONE %s" % time.strftime("%H:%M:%S"), flush=True)
