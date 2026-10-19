# -*- coding: utf-8 -*-
"""外层驱动 v2：逐格拉起子进程、串行、断点续跑、append-only 进度。

进程模型（评审 R22）：
  cold = 每 (engine,image,run) 一个进程；hot = 每 (engine,image) 一个进程，
  进程内先做 --warmup 次不计时预热，再跑 --hot-runs 次计时（progress 每次一行）。
引擎顺序按图片下标轮换（R17），每引擎 cold 块前跑一个丢弃的 burn-in。
"""
import argparse
import json
import os
import shutil
import subprocess
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY_MAIN = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
PY_GOT = "D:/models/ocr/got-venv/Scripts/python.exe"
PY_BY_ENGINE = {"gotocr": PY_GOT}
SCHEMA = "ep11-progress-v2"


def py_for(e):
    p = PY_BY_ENGINE.get(e, PY_MAIN)
    return p if os.path.exists(p) else PY_MAIN


def read_progress(path):
    rows, bad = [], 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    bad += 1
    return rows, bad


def append_row(path, row):
    s = json.dumps(row, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(s + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_cells_done(path):
    rows, bad = read_progress(path)
    done = set()
    for r in rows:
        if r.get("burnin"):
            continue
        if r.get("status") in ("ok", "fail") and r.get("run_idx") is not None:
            done.add((r.get("cell"), r.get("attempt", 1)))
    return done, bad


def kill_tree(proc):
    try:
        import psutil
        p = psutil.Process(proc.pid)
        for c in p.children(recursive=True):
            try:
                c.kill()
            except Exception:
                pass
        p.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def idle_gate(path, min_idle=90.0, samples=3):
    """返回 (ok, note)。CPU 空闲率低于 min_idle 判忙。"""
    import psutil
    vals = []
    for _ in range(samples):
        vals.append(psutil.cpu_percent(interval=1.0))
    busy = [v for v in vals if v > (100 - min_idle)]
    note = "cpu_percent=%s" % vals
    with open(path, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%F %T"), note))
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent"]):
        try:
            if p.info["name"] and any(k in p.info["name"].lower()
                                      for k in ("python", "paddle", "llama", "chrome")):
                procs.append("%s(%s)" % (p.info["name"], p.pid))
        except Exception:
            pass
    with open(path, "a", encoding="utf-8") as f:
        f.write("  procs: %s\n" % ", ".join(procs[:25]))
    return (len(busy) == 0, note)


def run_cell(eng, stem, img_path, mode, runs, run_idx, attempt, out_root, log_dir,
             progress, session, offline, burnin=False, timeout=1200, a_warmup=2):
    cell = "%s__%s__%s" % (eng, stem, mode)
    if mode == "cold":
        cell += "__r%d" % run_idx
    cdir = os.path.join(out_root, cell, "a%d" % attempt)
    shutil.rmtree(cdir, ignore_errors=True)          # 铁律 4：只清本 attempt
    os.makedirs(cdir, exist_ok=True)
    jp = os.path.join(cdir, "result.json")
    logp = os.path.join(log_dir, "%s_a%d.txt" % (cell, attempt))
    gt = os.path.join(BASE, "gt", stem + ".txt")
    env = dict(os.environ)
    env["EP11_T_SPAWN"] = repr(time.perf_counter())
    env["PYTHONPATH"] = BASE + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [py_for(eng), "-u", os.path.join(BASE, "bench_cell.py"),
           "--engine", eng, "--img", img_path, "--mode", mode,
           "--runs", str(runs), "--out", jp, "--gt", gt, "--cell", cell,
           "--attempt", str(attempt), "--session", session,
           "--offline", "1" if offline else "0",
           "--warmup", str(0 if mode == "cold" else a_warmup)]
    t_spawn = time.perf_counter()
    env["EP11_T_SPAWN"] = repr(t_spawn)
    with open(logp, "w", encoding="utf-8") as lf:
        lf.write("# cmd: %s\n# t_spawn=%.6f\n" % (" ".join(cmd), t_spawn))
        lf.flush()
        proc = subprocess.Popen(cmd, cwd=BASE, env=env, stdout=lf,
                                stderr=subprocess.STDOUT)
        try:
            proc.wait(timeout=timeout)
            t_exit = time.perf_counter()
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            t_exit = time.perf_counter()
            with open(logp, "a", encoding="utf-8") as f:
                f.write("\n# TIMEOUT %.1fs -> killed tree\n" % (t_exit - t_spawn))
    wall = t_exit - t_spawn

    rec = None
    if os.path.exists(jp):
        try:
            with open(jp, encoding="utf-8") as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            rec = {"status": "fail", "err": "bad json: %s" % e}
    else:
        rec = {"status": "fail", "err": "no_result_json" if wall < timeout - 1
               else "timeout_killed"}
    rec.setdefault("engine", eng)
    rec.setdefault("img", os.path.basename(img_path))
    rec.setdefault("mode", mode)
    rec.setdefault("t_total", None)
    rec.setdefault("t_infer_list", [])
    rec.setdefault("status", "fail")
    rec["cell"] = cell
    rec["attempt"] = attempt
    rec["burnin"] = bool(burnin)
    rec["wall_s"] = round(wall, 3)
    rec["t_popen_return_s"] = None
    rec["log"] = logp
    rec["schema_version"] = SCHEMA
    rec["session"] = session

    rows = []
    tl = rec.get("t_infer_list") or []
    if mode == "hot":
        for i, dt in enumerate(tl):
            r2 = dict(rec)
            r2["run_idx"] = i
            r2["t_infer"] = dt
            r2["t_total"] = rec.get("t_total")
            rows.append(r2)
        if not tl:
            rec["run_idx"] = 0
            rows.append(rec)
    else:
        rec["run_idx"] = run_idx
        rec["t_infer"] = tl[0] if tl else None
        rows.append(rec)
    for r in rows:
        append_row(progress, r)
    print("[%s a%d] %s wall=%.1fs status=%s err=%s"
          % (cell, attempt, mode, wall, rec.get("status"), rec.get("err") or "-"),
          flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["rapidocr", "paddleocr", "gotocr"])
    ap.add_argument("--imgs", nargs="+", required=True)
    ap.add_argument("--cold-runs", type=int, default=3)
    ap.add_argument("--hot-runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--out-root", default=os.path.join(BASE, "output", "cells"))
    ap.add_argument("--log-dir", default=os.path.join(BASE, "logs"))
    ap.add_argument("--progress", default=os.path.join(BASE, "progress.json"))
    ap.add_argument("--offline", type=int, default=0)
    ap.add_argument("--force", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-busy", action="store_true")
    ap.add_argument("--skip-burnin", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--session", default="s1")
    ap.add_argument("--cold-max-images", type=int, default=0,
                    help=">0 时只对前 N 张图跑冷启动（GOT 单页 175s，用于控时间盒）")
    a = ap.parse_args()

    os.makedirs(a.out_root, exist_ok=True)
    os.makedirs(a.log_dir, exist_ok=True)
    img_map = {os.path.splitext(os.path.basename(p))[0]: p for p in a.imgs}
    stems = sorted(img_map)

    # 只读数一遍任务清单
    n_cold = len(a.engines) * len(stems) * a.cold_runs
    n_hot = len(a.engines) * len(stems)
    if a.cold_max_images:
        n_cold = len(a.engines) * min(a.cold_max_images, len(stems)) * a.cold_runs
    total = n_cold + n_hot
    done, bad = load_cells_done(a.progress)
    pending = 0
    for e in a.engines:
        for st in stems:
            for i in range(a.cold_runs):
                if ("%s__%s__cold__r%d" % (e, st, i), 1) not in done:
                    pending += 1
            if ("%s__%s__hot" % (e, st), 1) not in done:
                pending += 1
    print("任务清单：总格 %d（cold %d + hot %d）/ 已完成 %d / 剩余 %d / 坏行 %d"
          % (total, n_cold, n_hot, total - pending, pending, bad), flush=True)
    if a.dry_run:
        return

    ok, note = idle_gate(os.path.join(a.log_dir, "idle_check.txt"))
    if not ok and not a.allow_busy:
        print("空载门未通过（%s）→ 中止。确认空载后加 --allow-busy 重跑。" % note)
        return 2
    print("空载门通过：%s" % note, flush=True)

    if a.offline == 0 and not a.force and not a.skip_burnin:
        for e in a.engines:                      # 每引擎一个丢弃的 burn-in
            run_cell(e, "warm_" + stems[0], img_map[stems[0]], "hot", 1, 0, 90,
                     a.out_root, a.log_dir, a.progress, a.session + "-burnin",
                     a.offline, burnin=True, timeout=a.timeout, a_warmup=a.warmup)

    n_ok = 0
    for idx, st in enumerate(stems):
        order = a.engines[idx % len(a.engines):] + a.engines[:idx % len(a.engines)]
        n_cold_here = 0
        if a.cold_max_images == 0 or idx < a.cold_max_images:
            n_cold_here = a.cold_runs
        for e in order:
            for i in range(n_cold_here):
                cell = "%s__%s__cold__r%d" % (e, st, i)
                if not a.force and (cell, 1) in done:
                    continue
                att = 1
                if a.force:
                    prev = [r for r in read_progress(a.progress)[0]
                            if r.get("cell") == cell and not r.get("burnin")]
                    att = (max([r.get("attempt", 1) for r in prev]) if prev else 0) + 1
                    if att > 3:
                        print("跳过 %s：attempt 上限" % cell)
                        continue
                run_cell(e, st, img_map[st], "cold", 1, i, att, a.out_root,
                         a.log_dir, a.progress, a.session, a.offline,
                         timeout=a.timeout, a_warmup=a.warmup)
                n_ok += 1
            cell = "%s__%s__hot" % (e, st)
            if a.force or (cell, 1) not in done:
                att = 1
                if a.force:
                    prev = [r for r in read_progress(a.progress)[0]
                            if r.get("cell") == cell and not r.get("burnin")]
                    att = (max([r.get("attempt", 1) for r in prev]) if prev else 0) + 1
                    if att > 3:
                        print("跳过 %s：attempt 上限" % cell)
                        continue
                run_cell(e, st, img_map[st], "hot", a.hot_runs, 0, att, a.out_root,
                         a.log_dir, a.progress, a.session, a.offline,
                         timeout=a.timeout, a_warmup=a.warmup)
                n_ok += 1
    print("本轮完成 %d 格" % n_ok)


if __name__ == "__main__":
    main()
