# -*- coding: utf-8 -*-
"""串行编排全部测量阶段：同一时刻只有一个测量进程（评审铁律 8）。

用法：python -u runner.py   （后台跑，日志见 logs/runner.log）
每个阶段独立日志：logs/phase_<name>.log
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
S = os.path.join(BASE, "output", "samples")


def imgs(names):
    return [os.path.join(S, n + ".png") for n in names]


ALL = sorted(os.path.splitext(f)[0] for f in os.listdir(S) if f.endswith(".png"))

PHASES = [
    # (name, args)
    ("1_rapid_full", ["--engines", "rapidocr", "--imgs"] + imgs(ALL) +
     ["--cold-runs", "3", "--hot-runs", "3", "--warmup", "2", "--session", "cleanA"]),
    ("2a_paddle_rep", ["--engines", "paddleocr", "--imgs"] +
     imgs(["invoice_01", "book_01", "table_01"]) +
     ["--cold-runs", "3", "--hot-runs", "3", "--warmup", "2", "--session", "cleanB1",
      "--skip-burnin"]),
    ("2b_paddle_big", ["--engines", "paddleocr", "--imgs"] +
     imgs(["book_02", "skew_01", "skew_02", "shot_02", "hard_01"]) +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "1", "--session", "cleanB2",
      "--skip-burnin"]),
    ("2c_paddle_small", ["--engines", "paddleocr", "--imgs"] +
     imgs(["hard_02", "invoice_02", "lc_01", "lc_02", "shot_01", "table_02"]) +
     ["--cold-runs", "0", "--hot-runs", "2", "--warmup", "1", "--session", "cleanB3",
      "--skip-burnin"]),
    ("3a_got_hot", ["--engines", "gotocr", "--imgs"] +
     imgs(["invoice_01", "table_01", "book_01", "shot_01", "skew_01", "lc_01"]) +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "1", "--session", "cleanG1",
      "--skip-burnin"]),
    ("3b_got_cold", ["--engines", "gotocr", "--imgs"] + imgs(["invoice_01"]) +
     ["--cold-runs", "1", "--hot-runs", "0", "--warmup", "0", "--session", "cleanG2",
      "--skip-burnin"]),
    ("4a_offline_hot", ["--engines", "rapidocr", "paddleocr", "--imgs"] + imgs(ALL) +
     ["--cold-runs", "0", "--hot-runs", "1", "--warmup", "0", "--offline", "1",
      "--session", "offA", "--skip-burnin"]),
    ("4b_offline_cold", ["--engines", "rapidocr", "paddleocr", "--imgs"] +
     imgs(["invoice_01", "book_01"]) +
     ["--cold-runs", "1", "--hot-runs", "0", "--warmup", "0", "--offline", "1",
      "--session", "offB", "--skip-burnin"]),
    ("4c_offline_got", ["--engines", "gotocr", "--imgs"] + imgs(["invoice_01", "table_01"]) +
     ["--cold-runs", "1", "--hot-runs", "1", "--warmup", "0", "--offline", "1",
      "--session", "offC", "--skip-burnin"]),
]


def run_phase(name, args):
    logp = os.path.join(BASE, "logs", "phase_%s.log" % name)
    cmd = [PY, "-u", os.path.join(BASE, "driver.py")] + args + ["--allow-busy"]
    t0 = time.time()
    with open(logp, "w", encoding="utf-8") as lf:
        lf.write("# cmd: %s\n" % " ".join(cmd))
        lf.flush()
        rc = subprocess.run(cmd, cwd=BASE, stdout=lf,
                            stderr=subprocess.STDOUT).returncode
    print("[phase %s] rc=%d dur=%.0fs" % (name, rc, time.time() - t0), flush=True)
    return rc


def run_batch(engine, pages):
    logp = os.path.join(BASE, "logs", "batch_%s_%d.log" % (engine, pages))
    cmd = [PY, "-u", os.path.join(BASE, "batch_throughput.py"),
           "--engine", engine, "--pages", str(pages)]
    t0 = time.time()
    with open(logp, "w", encoding="utf-8") as lf:
        rc = subprocess.run(cmd, cwd=BASE, stdout=lf,
                            stderr=subprocess.STDOUT).returncode
    print("[batch %s %d] rc=%d dur=%.0fs" % (engine, pages, rc, time.time() - t0),
          flush=True)
    return rc


def main():
    for name, args in PHASES:
        print("=== 开始阶段 %s %s ===" % (name, time.strftime("%H:%M:%S")), flush=True)
        run_phase(name, args)
    for eng, pages in (("rapidocr", 10), ("rapidocr", 100), ("paddleocr", 10)):
        print("=== 吞吐 %s %d ===" % (eng, pages), flush=True)
        run_batch(eng, pages)
    print("ALL PHASES DONE %s" % time.strftime("%H:%M:%S"), flush=True)


if __name__ == "__main__":
    main()
