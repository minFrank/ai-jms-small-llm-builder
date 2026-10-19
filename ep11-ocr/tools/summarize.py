# -*- coding: utf-8 -*-
"""聚合 progress.json -> result.json + 表格 markdown（禁止手打数字）。"""
import json
import os
import statistics as st

BASE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.join(BASE, "progress.json")
OUT = os.path.join(BASE, "result.json")
MD = os.path.join(BASE, "report_tables.md")
SPREAD_LIMIT = 5.0


def read_progress(path):
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


def sel(rows):
    """按 cell 取最新 attempt 的整组（评审 R24：整组重跑，不按 run 取 max）。"""
    by_cell = {}
    for r in rows:
        if r.get("burnin"):
            continue
        key = r.get("cell")
        att = r.get("attempt", 1)
        if key not in by_cell or att > by_cell[key][0]:
            by_cell[key] = (att, [])
        if att == by_cell[key][0]:
            by_cell[key][1].append(r)
    return {k: v[1] for k, v in by_cell.items()}


def main():
    rows, bad = read_progress(PROG)
    cells = sel(rows)
    data = {"schema": "ep11-result-v1", "bad_lines": bad, "cells": {},
            "engines": {}, "images": {}}

    for cell, rs in cells.items():
        r0 = rs[0]
        eng, img, mode = r0["engine"], r0["img"], r0["mode"]
        infers = [r.get("t_infer") for r in rs if r.get("t_infer") is not None]
        totals = [r.get("t_total") for r in rs if r.get("t_total") is not None]
        use = infers if mode == "hot" else totals
        med = st.median(use) if use else None
        spread = ((max(use) - min(use)) / med * 100.0) if (use and med) else None
        data["cells"][cell] = {
            "engine": eng, "img": img, "mode": mode, "n": len(use),
            "median": round(med, 4) if med else None,
            "min": round(min(use), 4) if use else None,
            "max": round(max(use), 4) if use else None,
            "spread_pct": round(spread, 2) if spread is not None else None,
            "status": r0.get("status"), "err": r0.get("err") or "",
            "seg_ok": r0.get("seg_ok"), "seg_residual_pct": r0.get("seg_residual_pct"),
            "seg": r0.get("seg"), "peak_rss_mb": r0.get("peak_rss_mb"),
            "cer_main": r0.get("cer_main"), "cer_ws": r0.get("cer_ws"),
            "gt_norm_len": r0.get("gt_norm_len"),
            "model_bytes": (r0.get("extra_out") or {}).get("model_bytes"),
            "settings": (r0.get("extra_out") or {}).get("settings"),
            "attempt": r0.get("attempt"), "burnin": False,
            "n_lines": r0.get("n_lines"), "session": r0.get("session"),
        }

    engines = sorted({c["engine"] for c in data["cells"].values()})
    images = sorted({c["img"] for c in data["cells"].values()})
    data["engines"] = engines
    data["images"] = images

    # 离散度按格判
    disp = {k: v["spread_pct"] for k, v in data["cells"].items()
            if v["mode"] == "hot" and v["spread_pct"] is not None}
    over = {k: v for k, v in disp.items() if v > SPREAD_LIMIT}
    data["dispersion"] = {"cells": len(disp), "over_limit": over,
                          "limit_pct": SPREAD_LIMIT}
    seg_bad = {k: v["seg_residual_pct"] for k, v in data["cells"].items()
               if v["mode"] == "cold" and v["seg_ok"] is False}
    data["seg_check"] = {"cold_cells": len([1 for v in data["cells"].values()
                                            if v["mode"] == "cold"]),
                         "over_5pct": seg_bad}
    fails = [{"cell": k, "engine": v["engine"], "img": v["img"], "err": v["err"],
              "status": v["status"]}
             for k, v in data["cells"].items() if v["status"] != "ok"]
    data["failures"] = fails

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # ---- markdown 表格 ----
    md = []
    def tbl(header, rows_):
        md.append("| " + " | ".join(header) + " |")
        md.append("|" + "|".join(["---"] * len(header)) + "|")
        for r in rows_:
            md.append("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
        md.append("")

    def fmt(v, nd=2, suffix=""):
        return ("%%.%df%%s" % nd) % (v, suffix) if v is not None else "失败"

    md.append("## 冷启动（t_spawn → 结果落盘前，含解释器启动/导入/建 session/首次执行）\n")
    tbl(["引擎", "图", "中位(s)", "n", "离散%", "分段残差%", "峰值内存(MB)"],
        [[c["engine"], c["img"], fmt(c["median"]), c["n"],
          fmt(c["spread_pct"]), fmt(c["seg_residual_pct"]), c["peak_rss_mb"]]
         for k, c in sorted(data["cells"].items()) if c["mode"] == "cold"])

    md.append("## 热态单页（session 已建好，同进程连续计时）\n")
    tbl(["引擎", "图", "中位(s)", "min", "max", "n", "离散%", "CER主口径"],
        [[c["engine"], c["img"], fmt(c["median"], 3), fmt(c["min"], 3),
          fmt(c["max"], 3), c["n"], fmt(c["spread_pct"]),
          fmt(c["cer_main"], 4)] for k, c in sorted(data["cells"].items())
         if c["mode"] == "hot"])

    md.append("## 覆盖矩阵（格数 = 数据点数；空 = 失败/缺测）\n")
    header = ["维度 \\ 引擎"] + engines
    rws = []
    for dim, mode in (("冷启动单页", "cold"), ("热态单页", "hot")):
        rws.append([dim] + [", ".join(
            "%s×%d" % (img, data["cells"]["%s__%s__%s" % (e, img, mode)]["n"])
            for img in images if "%s__%s__%s" % (e, img, mode) in data["cells"])
            or "失败" for e in engines])
    tbl(header, rws)

    md.append("## 数据密度自评\n")
    n_data = len([1 for c in data["cells"].values()])
    tbl(["项", "实测", "下限", "判定"],
        [["数据点(格)", n_data, 30, "达标" if n_data >= 30 else "不足"],
         ["真实样本(图)", len(images), 10,
          "达标" if len(images) >= 10 else "不足"],
         ["失败案例", len(fails), 3, "达标" if len(fails) >= 3 else "不足"]])
    md.append("坏行(截断/非法 JSON)：%d" % bad)

    with open(MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("cells=%d bad=%d disp_over=%d seg_bad=%d fails=%d"
          % (len(data["cells"]), bad, len(over), len(seg_bad), len(fails)))
    print("写出 %s / %s" % (OUT, MD))


if __name__ == "__main__":
    main()
