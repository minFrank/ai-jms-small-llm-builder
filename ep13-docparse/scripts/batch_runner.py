# -*- coding: utf-8 -*-
"""ep13 全量调度器 —— 26 样本 × 6 引擎 = 156 格，协议 A 每格 6-12 rep
- seeded 随机序（seed=1301，规格 §2.2：引擎+样本随机序）
- 断点续跑：cells/<run_id>/ 已有终态 cell（complete/partial/failed 且无 schema_err）→ skip
- 格间控制：control/batch_state.json 的 desired=running|paused（格边界才生效，规格 F-13）
- 每格独立 runner 子进程（天然隔离、超时 kill 双保险）
- 进度心跳：batch_state.json 每格更新 last_progress + 第 n/156
用法: python scripts/batch_runner.py [--run-id ep13-full-001] [--engine 只跑某引擎] [--limit N]
暂停: 改 control/batch_state.json 的 desired=paused（当前格跑完即停）
"""
from __future__ import annotations
import argparse, glob, json, os, random, subprocess, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
RUNNER = os.path.join(HERE, "runner.py")
IMG_DIR = os.path.join(EP, "samples")
CELLS = os.path.join(EP, "cells")
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]
SEED = 1301
PER_CELL_TIMEOUT = 7200      # 单格硬顶 2h（12×1800s 理论最坏 6h——超时即杀+记 failed）
PY = sys.executable

def log(msg: str) -> None:
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)

def load_tasks(run_id: str, only_engine: str | None) -> list[tuple[str, str]]:
    man = json.load(open(os.path.join(IMG_DIR, "manifest.json"), encoding="utf-8"))
    tasks = [(s["sample_id"] + ".png", e) for s in man["samples"] for e in ENGINES]
    if only_engine:
        tasks = [t for t in tasks if t[1] == only_engine]
    random.Random(SEED).shuffle(tasks)          # seeded 随机序
    return tasks

def cell_done(run_id: str, sample: str, engine: str) -> bool:
    pat = os.path.join(CELLS, run_id, "*__%s__p1.json" % engine)
    for p in glob.glob(pat):
        try:
            c = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        # 按 input.sha256 匹配（对旧 uuid 格与新 manifest 格都可靠）
        if c.get("status") in ("complete", "partial", "failed") and \
           "schema_err" not in str(c.get("err") or "") and \
           c.get("input", {}).get("sha256") == _sha_of(sample):
            return True
    return False

_SHA_CACHE = None
def _sha_of(sample_file: str) -> str:
    global _SHA_CACHE
    if _SHA_CACHE is None:
        man = json.load(open(os.path.join(IMG_DIR, "manifest.json"), encoding="utf-8"))
        _SHA_CACHE = {s["img"]: s["sha256"] for s in man["samples"]}
    return _SHA_CACHE.get(sample_file, "")

def read_batch_state(path: str) -> dict:
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return dict(desired="running")

def write_batch_state(path: str, st: dict) -> None:
    tmp = path + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="ep13-full-001")
    ap.add_argument("--engine", default=None)
    ap.add_argument("--skip-engine", default=None, help="排除引擎（如 oxr 等 D-FINE）")
    ap.add_argument("--limit", type=int, default=None, help="本轮最多跑 N 格（分批用）")
    args = ap.parse_args()

    os.makedirs(os.path.join(CELLS, args.run_id), exist_ok=True)
    state_path = os.path.join(EP, "control", "batch_state.json")
    tasks = load_tasks(args.run_id, args.engine)
    if args.skip_engine:
        tasks = [t for t in tasks if t[1] != args.skip_engine]
    total = len(tasks)
    # 断点续跑：已完成计数
    done_before = sum(1 for s, e in tasks if cell_done(args.run_id, s, e))
    log("全量开始 run_id=%s 任务 %d 格，已完成 %d（跳过），本批 limit=%s" %
        (args.run_id, total, done_before, args.limit))

    n_run = n_skip = n_fail = 0
    for i, (img, eng) in enumerate(tasks, 1):
        # 格间控制（F-13：只在格边界查）
        st = read_batch_state(state_path)
        if st.get("desired") == "paused":
            log("batch_state=paused → 格边界停（已跑 %d）" % n_run)
            break
        if cell_done(args.run_id, img, eng):
            n_skip += 1
            continue
        if args.limit and n_run >= args.limit:
            log("limit=%d 达到，本批结束" % args.limit)
            break

        write_batch_state(state_path, dict(
            desired=st.get("desired", "running"), run_id=args.run_id,
            seq="%d/%d" % (i, total), current="%s×%s" % (img, eng),
            last_progress=datetime.datetime.now().isoformat(timespec="seconds"),
            n_run=n_run, n_skip=n_skip, n_fail=n_fail,
            started_at=st.get("started_at") or datetime.datetime.now().isoformat(timespec="seconds")))
        log("▶ [%d/%d] %s × %s" % (i, total, img, eng))
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, RUNNER, "--engine", eng,
                 "--img", os.path.join(IMG_DIR, img),
                 "--run-id", args.run_id],
                cwd=EP, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=PER_CELL_TIMEOUT)
            ok = (r.returncode == 0)
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]
            log("  exit=%s %.0fs | %s" % (r.returncode, time.time() - t0, " / ".join(tail)[:220]))
        except subprocess.TimeoutExpired:
            ok = False
            n_fail += 1
            log("  ⏰ 单格 %.0fs 超时被杀（> %ds）" % (time.time() - t0, PER_CELL_TIMEOUT))
        if ok: n_run += 1
        elif "⏰" not in (r.stdout or ""): n_fail += 1

    write_batch_state(state_path, dict(
        desired="running", run_id=args.run_id, seq="done",
        last_progress=datetime.datetime.now().isoformat(timespec="seconds"),
        n_run=n_run, n_skip=n_skip, n_fail=n_fail,
        finished_at=datetime.datetime.now().isoformat(timespec="seconds")))
    log("本批结束：跑 %d、跳过 %d、失败/超时 %d" % (n_run, n_skip, n_fail))
    return 0

if __name__ == "__main__":
    sys.exit(main())
