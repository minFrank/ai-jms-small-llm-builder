# -*- coding: utf-8 -*-
"""报告数字绑定：所有进报告的数字都带 metric id，供 assert_report 只读复算。"""
import json
import os
import statistics as st

BASE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.join(BASE, "progress.json")


def read_progress(path=PROG):
    rows, bad = [], 0
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


def select_cells(rows):
    by_cell = {}
    for r in rows:
        if r.get("burnin"):
            continue
        key, att = r.get("cell"), r.get("attempt", 1)
        if key not in by_cell or att > by_cell[key][0]:
            by_cell[key] = (att, [])
        if att == by_cell[key][0]:
            by_cell[key][1].append(r)
    return {k: v[1] for k, v in by_cell.items()}


def cell_stats(rs):
    r0 = rs[0]
    mode = r0["mode"]
    vals = [r.get("t_infer") if mode == "hot" else r.get("t_total") for r in rs]
    vals = [v for v in vals if v is not None]
    med = st.median(vals) if vals else None
    spread = ((max(vals) - min(vals)) / med * 100.0) if (vals and med) else None
    return {
        "engine": r0["engine"], "img": r0["img"], "mode": mode, "n": len(vals),
        "median": med, "min": min(vals) if vals else None,
        "max": max(vals) if vals else None, "spread_pct": spread,
        "status": r0.get("status"), "err": r0.get("err") or "",
        "seg_ok": r0.get("seg_ok"), "seg_residual_pct": r0.get("seg_residual_pct"),
        "seg": r0.get("seg"), "peak_rss_mb": r0.get("peak_rss_mb"),
        "cer_main": r0.get("cer_main"), "cer_ws": r0.get("cer_ws"),
        "gt_norm_len": r0.get("gt_norm_len"), "cell": r0.get("cell"),
        "model_bytes": (r0.get("extra_out") or {}).get("model_bytes"),
        "settings": (r0.get("extra_out") or {}).get("settings"),
        "attempt": r0.get("attempt"), "n_lines": r0.get("n_lines"),
        "session": r0.get("session"),
    }


def compute(progress=PROG):
    rows, bad = read_progress(progress)
    cells = {k: cell_stats(v) for k, v in select_cells(rows).items()}
    engines = sorted({c["engine"] for c in cells.values()})
    images = sorted({c["img"] for c in cells.values()})
    disp = {k: v["spread_pct"] for k, v in cells.items()
            if v["mode"] == "hot" and v["spread_pct"] is not None}
    over = {k: v for k, v in disp.items() if v and v > 5.0}
    colds = {k: v for k, v in cells.items() if v["mode"] == "cold"}
    seg_bad = {k: v["seg_residual_pct"] for k, v in colds.items()
               if v["seg_ok"] is False}
    fails = [{"cell": k, "engine": v["engine"], "img": v["img"], "err": v["err"]}
             for k, v in cells.items() if v["status"] != "ok"]
    return {"bad_lines": bad, "cells": cells, "engines": engines, "images": images,
            "disp_over": over, "disp_n": len(disp), "seg_bad": seg_bad,
            "seg_n": len(colds), "failures": fails}


def engine_img_median(cells, engine, img, mode, field="median"):
    for k, c in cells.items():
        if c["engine"] == engine and c["img"] == img and c["mode"] == mode:
            return c[field]
    return None


def _cold_group(cur, pre, eng, stem):
    """冷启动按 (engine,img) 聚合 r 格：返回 前/后 r 格数、中位、跨 r 极差%。"""
    import statistics as st

    def agg(cells):
        ks = sorted(k for k in cells
                    if k.startswith("%s__%s__cold__r" % (eng, stem)))
        meds = [cells[k]["median"] for k in ks if cells[k].get("median")]
        med = st.median(meds) if meds else None
        spr = ((max(meds) - min(meds)) / med * 100.0) if (med and len(meds) >= 2) else None
        return len(ks), med, spr
    nb, mb, sb = agg(pre)
    na, ma, sa = agg(cur)
    return nb, na, sb, sa, mb, ma


def topup_compare():
    """补跑前后对比：topup_task.json 的 23 项任务（去重 22 格）× 补跑前快照 × 当前值。

    补跑前快照 = result_pre_topup.json.bak（补跑开始前 summarize 的产物）。
    冷启动格按 (engine,img) 聚合 3 个 r 格；热态取整格最新 attempt。
    """
    pre_path = os.path.join(BASE, "result_pre_topup.json.bak")
    task_path = os.path.join(BASE, "topup_task.json")
    if not (os.path.exists(pre_path) and os.path.exists(task_path)):
        return None
    with open(pre_path, encoding="utf-8") as f:
        pre = json.load(f)["cells"]
    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)
    cur = compute()["cells"]
    rows, seen = [], set()
    for j in task["jobs"]:
        eng, stem, mode = j["engine"], j["img"].replace(".png", ""), j["mode"]
        if (eng, stem, mode) in seen:
            continue
        seen.add((eng, stem, mode))
        reason = "n<3" if j["reason"] == "n<3" else (
            "超时失败" if j["reason"] == "timeout_failure" else "离散超标")
        if mode == "hot":
            key = "%s__%s__hot" % (eng, stem)
            c, p = cur.get(key), pre.get(key)
            rows.append({
                "engine": eng, "img": stem, "mode": mode, "cell": key,
                "reason": reason,
                "n_b": (p or {}).get("n", 0), "n_a": (c or {}).get("n"),
                "sp_b": (p or {}).get("spread_pct"), "sp_a": (c or {}).get("spread_pct"),
                "md_b": (p or {}).get("median"), "md_a": (c or {}).get("median"),
                "status_a": (c or {}).get("status"), "err_a": (c or {}).get("err"),
            })
        else:
            nb, na, sb, sa, mb, ma = _cold_group(cur, pre, eng, stem)
            rows.append({
                "engine": eng, "img": stem, "mode": mode, "cell": "%s__%s__cold" % (eng, stem),
                "reason": reason, "n_b": nb, "n_a": na, "sp_b": sb, "sp_a": sa,
                "md_b": mb, "md_a": ma, "status_a": "ok", "err_a": "",
            })
    # 跨批一致性：n<3 热态格 + 冷启动组，重跑前后中位偏差（不含 skew_01：补跑前无值）
    devs = []
    for r in rows:
        if r["md_b"] and r["md_a"] and r["img"] != "skew_01":
            devs.append((abs(r["md_a"] - r["md_b"]) / r["md_b"] * 100.0,
                         min(r["md_b"], r["md_a"]), r["cell"]))
    devs.sort(reverse=True)
    drift_max = devs[0][0] if devs else None
    # 分层：中位 >=1s 的格单独算（亚秒级格的相对偏差会被毫秒级抖动放大）
    big = [d for d in devs if d[1] >= 1.0]
    drift_big = big[0][0] if big else None
    still_over = [r for r in rows if r["sp_a"] is not None and r["sp_a"] > 5.0]
    return {"rows": rows, "n_tasks": len(task["jobs"]), "n_unique": len(rows),
            "drift_max_pct": drift_max, "drift_big_pct": drift_big,
            "drift_top": devs[:3],
            "still_over": still_over,
            "n_lt3_fixed": len([r for r in rows if r["reason"] == "n<3"]),
            "timeout_cell": "gotocr__skew_01__hot",
            "disp_fixed": [r for r in rows if r["reason"] == "离散超标"]}


def fmt(v, nd=2, suffix=""):
    if v is None:
        return "失败"
    return ("%%.%df%%s" % nd) % (v, suffix)
