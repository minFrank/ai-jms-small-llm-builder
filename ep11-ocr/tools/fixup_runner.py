# -*- coding: utf-8 -*-
"""GT 口径修正后的定向重跑：只重跑 shot_01 / shot_02 / lc_01。

原因：这两张网页样本早期用 DOM 整页文本当 GT（20 万字符），CER 无意义；
改用「真实网页打印成 PDF 后渲染 + PDF 文本层 GT」后，图与 GT 逐字对应。
重跑走 --force（attempt+1），聚合按最新 attempt 取值，旧行留在文件里可审计。
"""
import os
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
S = os.path.join(BASE, "output", "samples")
FIX = [os.path.join(S, n + ".png") for n in ("shot_01", "shot_02", "lc_01")]

PHASES = [
    ("fix_online_rapid", ["--engines", "rapidocr", "--imgs"] + FIX +
     ["--cold-runs", "3", "--hot-runs", "3", "--warmup", "2", "--session", "fixA",
      "--force", "1", "--allow-busy", "--skip-burnin"]),
    ("fix_online_paddle", ["--engines", "paddleocr", "--imgs"] + FIX +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "1", "--session", "fixB",
      "--force", "1", "--allow-busy", "--skip-burnin"]),
    ("fix_offline_both", ["--engines", "rapidocr", "paddleocr", "--imgs"] + FIX +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "0", "--session", "fixOff",
      "--force", "1", "--offline", "1", "--allow-busy", "--skip-burnin",
      "--progress", os.path.join(BASE, "progress_offline.json"),
      "--out-root", os.path.join(BASE, "output", "cells_offline"),
      "--log-dir", os.path.join(BASE, "logs_offline")]),
]

if __name__ == "__main__":
    for name, args in PHASES:
        logp = os.path.join(BASE, "logs", "phase_%s.log" % name)
        cmd = [PY, "-u", os.path.join(BASE, "driver.py")] + args
        t0 = time.time()
        with open(logp, "w", encoding="utf-8") as lf:
            lf.write("# cmd: %s\n" % " ".join(cmd))
            lf.flush()
            rc = subprocess.run(cmd, cwd=BASE, stdout=lf,
                                stderr=subprocess.STDOUT).returncode
        print("[fix %s] rc=%d dur=%.0fs" % (name, rc, time.time() - t0), flush=True)
    print("FIX DONE %s" % time.strftime("%H:%M:%S"), flush=True)
