# -*- coding: utf-8 -*-
"""单格测量 v2（一格一子进程）。

计时（评审 R15/R16 后的口径）：
  时钟 = time.perf_counter（Windows QPC，跨进程同 epoch）
  t_spawn  由父进程在 Popen **之前**写入环境变量 EP11_T_SPAWN
  t_total = t_end(结果落盘之前) − t_spawn
  互斥段  t_boot(解释器启动) / t_import / t_session / t_first / t_infer_rest / t_post
  残差    residual = t_total − sum(各段)，>5%% 判 seg_ok=False（DP-02）

用法：bench_cell.py --engine E --img X.png --mode cold|hot --runs 3 \
     --out result.json --gt gt/X.txt --cell name --attempt 1 --session S --offline 0|1
"""
import argparse
import json
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "ep11-progress-v2"


def _sampler(stop_evt, agg):
    try:
        import psutil
        p = psutil.Process(os.getpid())
    except Exception:
        return
    n = 0
    while not stop_evt.is_set():
        try:
            m = p.memory_info()
            rss = getattr(m, "rss", 0)
            agg["max_rss"] = max(agg["max_rss"], rss)
            n += 1
        except Exception:
            pass
        time.sleep(0.05)
    agg["samples"] = n
    try:
        agg["peak_wset"] = p.memory_info().peak_wset
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--img", required=True)
    ap.add_argument("--mode", choices=["cold", "hot"], required=True)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gt", default="")
    ap.add_argument("--cell", required=True)
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--session", default="s0")
    ap.add_argument("--offline", type=int, default=0)
    ap.add_argument("--warmup", type=int, default=2)
    a = ap.parse_args()

    t_spawn = float(os.environ.get("EP11_T_SPAWN", "0") or 0)
    t_entry = time.perf_counter()

    agg = {"max_rss": 0, "samples": 0, "peak_wset": 0}
    stop_evt = threading.Event()
    th = threading.Thread(target=_sampler, args=(stop_evt, agg), daemon=True)
    th.start()

    rec = {
        "schema_version": SCHEMA, "session": a.session, "cell": a.cell,
        "attempt": a.attempt, "engine": a.engine, "img": os.path.basename(a.img),
        "imgpath": a.img, "mode": a.mode, "runs": a.runs,
        "offline": bool(a.offline), "warmup": bool(a.warmup),
        "gt_path": a.gt, "ts": time.time(), "py": sys.version.split()[0],
    }
    err = ""
    text, lines, eng_extra = "", [], {}
    t_infers = []
    guard_active = False
    seg = {}
    t_end = t_entry

    try:
        t_imp0 = time.perf_counter()
        if a.offline:
            sys.path.insert(0, BASE)
            import offline_guard
            guard_active = bool(getattr(offline_guard, "ACTIVE", False))
        sys.path.insert(0, BASE)
        import engine_base
        t_imp1 = time.perf_counter()

        t_s0 = time.perf_counter()
        eng = engine_base.make_engine(a.engine)
        eng.load()
        t_s1 = time.perf_counter()

        if a.mode == "hot" and a.warmup > 0:
            # 同进程预热，不计时；最后两轮相差 <2% 才算收敛（评审 R23）
            wt = []
            for i in range(a.warmup):
                tw = time.perf_counter()
                eng.infer(a.img)
                wt.append(time.perf_counter() - tw)
            if len(wt) >= 2:
                conv = abs(wt[-1] - wt[-2]) / max(wt[-2], 1e-9) < 0.02
                if not conv:
                    tw = time.perf_counter()
                    eng.infer(a.img)
                    wt.append(time.perf_counter() - tw)
                    conv = abs(wt[-1] - wt[-2]) / max(wt[-2], 1e-9) < 0.02
            else:
                conv = True
            rec["warmup_times"] = [round(x, 4) for x in wt]
            rec["warmup_converged"] = bool(conv)

        t_first = 0.0
        n_runs = 1 if a.mode == "cold" else a.runs
        for i in range(n_runs):
            t0 = time.perf_counter()
            r = eng.infer(a.img)
            dt = time.perf_counter() - t0
            t_infers.append(dt)
            if i == 0:
                t_first = dt
                text, lines = r.text, r.lines
                eng_extra = r.extra or {}
            if r.err:
                err = r.err
                break
        t_after_infer = time.perf_counter()
        t_end = t_after_infer                       # 出字即截止：冷启动头条不含元数据统计
        if not err and "r" in locals():
            text, lines = r.text, r.lines
            eng_extra = r.extra or {}
        try:                                        # 这段在计时窗口外（评审 R15）
            eng_extra["model_bytes"] = eng.model_bytes()
            eng_extra["model_dir"] = eng.model_dir()
            eng_extra["settings"] = eng.settings()
        except Exception as e:  # noqa
            eng_extra["size_err"] = str(e)
        seg = {
            "t_boot": round(t_imp0 - (t_spawn or t_entry), 6),
            "t_import": round(t_imp1 - t_imp0, 6),
            "t_session": round(t_s1 - t_s0, 6),
            "t_first": round(t_first, 6),
            "t_infer_rest": round(sum(t_infers[1:]), 6),
            "t_post": 0.0,
        }
    except Exception as e:  # noqa
        err = "%s: %s" % (type(e).__name__, e)
        t_end = time.perf_counter()
        seg = {"t_boot": round(t_entry - (t_spawn or t_entry), 6),
               "t_import": 0.0, "t_session": 0.0, "t_first": 0.0,
               "t_infer_rest": 0.0, "t_post": 0.0}

    stop_evt.set()
    th.join(timeout=2)

    t_total = (t_end - t_spawn) if t_spawn else (t_end - t_entry)
    segsum = sum(seg.values())
    resid_pct = (abs(segsum - t_total) / t_total * 100.0) if t_total > 0 else 0.0
    # 热态的 t_total 还包含同进程预热与全部计时 run，段和只覆盖 load+首次推理，
    # 残差对热态无意义 —— 只对冷启动判 DP-02。
    if a.mode != "cold":
        resid_pct, segsum = None, None

    status = "ok"
    if err:
        status = "fail"
    if not text and not err:
        status = "fail"
        err = "empty_text"

    gt_text = ""
    cer_main, cer_ws, gt_len = None, None, 0
    if a.gt and os.path.exists(a.gt):
        gt_text = open(a.gt, encoding="utf-8").read()
        import cer as cermod
        gt_len = len(cermod.normalize(gt_text, True))
        cer_main = cermod.cer(gt_text, text, True)
        cer_ws = cermod.cer(gt_text, text, False)
        rec["norm_version"] = cermod.NORM_VERSION
        rec["gt_sha256_16"] = __import__("hashlib").sha256(
            gt_text.encode("utf-8")).hexdigest()[:16]

    rec.update({
        "status": status, "err": err, "text": text, "n_lines": len(lines),
        "t_total": round(t_total, 6), "t_infer_list": [round(x, 6) for x in t_infers],
        "seg": seg, "seg_sum": round(segsum, 6) if segsum is not None else None,
        "seg_residual_pct": round(resid_pct, 3) if resid_pct is not None else None,
        "seg_ok": (resid_pct <= 5.0) if resid_pct is not None else None,
        "peak_rss_mb": round(max(agg["max_rss"], agg["peak_wset"]) / 1048576.0, 1),
        "peak_rss_mb_raw": round(agg["max_rss"] / 1048576.0, 1),
        "peak_wset_mb": round(agg["peak_wset"] / 1048576.0, 1),
        "sample_count": agg["samples"],
        "cer_main": cer_main, "cer_ws": cer_ws, "gt_norm_len": gt_len,
        "guard_active": guard_active, "extra_out": eng_extra,
        "threads": {"cpu_count": os.cpu_count()},
    })
    try:
        import torch
        rec["threads"]["torch_num_threads"] = torch.get_num_threads()
    except Exception:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, a.out)
    print("CELL_DONE %s status=%s total=%.2fs resid=%s cer=%s err=%s"
          % (a.cell, status, t_total,
             ("%.2f%%" % resid_pct) if resid_pct is not None else "-",
             ("%.3f" % cer_main) if cer_main is not None else "-", err or "-"),
          flush=True)


if __name__ == "__main__":
    main()
