# -*- coding: utf-8 -*-
"""ep11 补跑编排器：只跑 topup_task.json 列出的 23 格（去重后 22 格）。

设计（照 fixup_runner 的形态，不改 driver.py/bench_cell.py）：
  - 逐阶段串行调 driver.py，同一时刻只有一个测量进程。
  - 每阶段完成写标记文件 logs/topup_phase_<name>.done；重跑本脚本会跳过已完成阶段
    （断点续跑入口）。阶段内 driver 自身按 progress 断点（force 阶段按 attempt+1）。
  - force=1 的阶段 = 整格重跑为新 attempt（聚合按最新 attempt 取整组，n 由新组给足 3）。
  - gotocr cold 补格用 force=0：r0 已完成会被 driver 跳过，只跑缺的 r1/r2。

阶段：
  R  rapidocr 离散定向重跑（invoice_01/table_01/table_02，hot 3 次 + 预热 2，原配置）
  B  paddleocr 11 格 hot 补到 n=3（hot 3 次 + 预热 1，与原 2b/2c 预热一致）
  GC gotocr cold 补格（invoice_01/table_01 的 r1/r2，force=0 只补缺）
  GH gotocr 5 格 hot 补到 n=3（book_01/invoice_01/lc_01/shot_01/table_01）
  GS gotocr skew_01 hot 单独一阶段（上轮 1200s 超时被杀；本轮放宽到 5400s，仍失败则如实标失败）
"""
import os
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
S = os.path.join(BASE, "output", "samples")
MARK = os.path.join(BASE, "logs")


def imgs(names):
    return [os.path.join(S, n + ".png") for n in names]


PHASES = [
    ("R_disp_rapid", ["--engines", "rapidocr",
                      "--imgs"] + imgs(["invoice_01", "table_01", "table_02"]) +
     ["--cold-runs", "0", "--hot-runs", "3", "--warmup", "2", "--force", "1",
      "--session", "topupR", "--timeout", "900", "--allow-busy", "--skip-burnin"]),
    ("B_hot_paddle", ["--engines", "paddleocr",
                      "--imgs"] + imgs(["book_02", "hard_01", "hard_02", "invoice_02",
                                        "lc_01", "lc_02", "shot_01", "shot_02",
                                        "skew_01", "skew_02", "table_02"]) +
     ["--cold-runs", "0", "--hot-runs", "3", "--warmup", "1", "--force", "1",
      "--session", "topupB", "--timeout", "1500", "--allow-busy", "--skip-burnin"]),
    ("GC_cold_got", ["--engines", "gotocr",
                     "--imgs"] + imgs(["invoice_01", "table_01"]) +
     ["--cold-runs", "3", "--hot-runs", "0", "--warmup", "0", "--force", "0",
      "--session", "topupG1", "--timeout", "2400", "--allow-busy", "--skip-burnin"]),
    ("GH_hot_got", ["--engines", "gotocr",
                    "--imgs"] + imgs(["book_01", "invoice_01", "lc_01",
                                      "shot_01", "table_01"]) +
     ["--cold-runs", "0", "--hot-runs", "3", "--warmup", "1", "--force", "1",
      "--session", "topupG2", "--timeout", "2400", "--allow-busy", "--skip-burnin"]),
    ("GS_hot_skew", ["--engines", "gotocr", "--imgs"] + imgs(["skew_01"]) +
     ["--cold-runs", "0", "--hot-runs", "3", "--warmup", "1", "--force", "1",
      "--session", "topupG3", "--timeout", "5400", "--allow-busy", "--skip-burnin"]),
]


def run_phase(name, args):
    done_mark = os.path.join(MARK, "topup_phase_%s.done" % name)
    if os.path.exists(done_mark):
        print("[phase %s] 已完成（标记存在），跳过" % name, flush=True)
        return 0
    logp = os.path.join(MARK, "topup_phase_%s.log" % name)
    cmd = [PY, "-u", os.path.join(BASE, "driver.py")] + args
    t0 = time.time()
    with open(logp, "w", encoding="utf-8") as lf:
        lf.write("# cmd: %s\n" % " ".join(cmd))
        lf.flush()
        rc = subprocess.run(cmd, cwd=BASE, stdout=lf,
                            stderr=subprocess.STDOUT).returncode
    dur = time.time() - t0
    print("[phase %s] rc=%d dur=%.0fs" % (name, rc, dur), flush=True)
    if rc == 0:
        with open(done_mark, "w", encoding="utf-8") as f:
            f.write("rc=0 dur=%.0fs at %s\n" % (dur, time.strftime("%F %T")))
    return rc


if __name__ == "__main__":
    with open(os.path.join(MARK, "topup_runner.pid"), "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    print("TOPUP START %s phases=%d pid=%d" % (time.strftime("%F %T"),
                                               len(PHASES), os.getpid()),
          flush=True)
    bad = []
    for name, args in PHASES:
        print("=== 开始阶段 %s %s ===" % (name, time.strftime("%H:%M:%S")),
              flush=True)
        rc = run_phase(name, args)
        if rc != 0:
            bad.append((name, rc))
            print("[phase %s] rc=%d -> 终止后续阶段" % (name, rc), flush=True)
            break
    print("TOPUP END %s bad=%s" % (time.strftime("%F %T"), bad), flush=True)
