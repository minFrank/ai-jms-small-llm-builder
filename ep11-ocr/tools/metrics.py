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


def fmt(v, nd=2, suffix=""):
    if v is None:
        return "失败"
    return ("%%.%df%%s" % nd) % (v, suffix)
