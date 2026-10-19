# -*- coding: utf-8 -*-
"""质量抽样 + 失败案例 + 表格结构判定（全部从 progress 的识别文本现算）。"""
import json
import os
import re

import metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(BASE, "quality")


def lines_of(text):
    return [l.strip() for l in (text or "").split("\n") if l.strip()]


def main():
    os.makedirs(QDIR, exist_ok=True)
    data = M.compute()
    cells = data["cells"]
    meta = {x["name"]: x for x in json.load(
        open(os.path.join(BASE, "gt", "samples_meta.json"), encoding="utf-8"))}
    # 取每个 hot 格的识别文本（最新 attempt）
    rows, _ = M.read_progress()
    sel = M.select_cells(rows)
    recs = []
    for cell, rs in sel.items():
        r0 = rs[0]
        if r0["mode"] != "hot":
            continue
        recs.append({"engine": r0["engine"], "img": r0["img"],
                     "text": r0.get("text", ""), "gt": r0.get("gt_path", "")})

    import cer as C
    # ---- 逐行质量抽样：按行 CER 排序取最差 15 行 ----
    samples = []
    for rec in recs:
        gtp = rec["gt"]
        if not gtp or not os.path.exists(gtp):
            continue
        gt_lines = lines_of(open(gtp, encoding="utf-8").read())
        pred_lines = lines_of(rec["text"])
        for i, gl in enumerate(gt_lines):
            if len(C.normalize(gl, True)) < 4:
                continue
            best, bl = None, ""
            for pl in pred_lines:
                c = C.cer(gl, pl, True)
                if c is not None and (best is None or c < best):
                    best, bl = c, pl
            if best is None:
                continue
            samples.append({"engine": rec["engine"], "img": rec["img"],
                            "gt": gl[:60], "pred": bl[:60], "cer": best,
                            "line": i})
    samples.sort(key=lambda x: -x["cer"])
    top = samples[:15]
    with open(os.path.join(QDIR, "quality_samples.md"), "w", encoding="utf-8") as f:
        f.write("# 质量抽样：按行 CER 从高到低取 15 行（同图同引擎的最差行）\n\n")
        f.write("| # | 引擎 | 图 | 行号 | 该行 CER | GT（前60字） | 识别（前60字） |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for i, s in enumerate(top, 1):
            f.write("| %d | %s | %s | %d | %.3f | %s | %s |\n"
                    % (i, s["engine"], s["img"], s["line"], s["cer"],
                       s["gt"].replace("|", "\\|"), s["pred"].replace("|", "\\|")))
    print("quality samples:", len(top), "of", len(samples))

    # ---- 失败案例候选：CER 最高的 6 个 (engine,img) ----
    per = []
    for rec in recs:
        c = cells.get("%s__%s__hot" % (rec["engine"], rec["img"]))
        if c and c["cer_main"] is not None:
            per.append({"engine": rec["engine"], "img": rec["img"],
                        "cer": c["cer_main"], "cat": meta.get(rec["img"], {}).get("category", "?"),
                        "n_lines": c["n_lines"],
                        "gt_len": c["gt_norm_len"]})
    per.sort(key=lambda x: -x["cer"])
    with open(os.path.join(QDIR, "failure_candidates.md"), "w", encoding="utf-8") as f:
        f.write("# 失败候选（CER 降序，供人工挑选与归因）\n\n")
        f.write("| 引擎 | 图 | 类别 | CER | 识别行数 | GT 归一化长度 |\n|---|---|---|---|---|---|\n")
        for p in per:
            f.write("| %s | %s | %s | %.3f | %s | %s |\n"
                    % (p["engine"], p["img"], p["cat"], p["cer"],
                       p["n_lines"], p["gt_len"]))
    print("failure candidates:", len(per))

    # ---- 表格结构：识别行数 vs GT 行列 ----
    out = []
    for name in ("table_01", "table_02"):
        tj = os.path.join(BASE, "gt", name + ".table.json")
        if not os.path.exists(tj):
            continue
        gt = json.load(open(tj, encoding="utf-8"))
        for eng in data["engines"]:
            c = cells.get("%s__%s__hot" % (eng, name))
            rec = next((r for r in recs
                        if r["engine"] == eng and r["img"] == name + ".png"), None)
            pred_lines = lines_of(rec["text"]) if rec else []
            # 单元格级比对：GT 每行的每个单元格是否都能在识别文本里找到
            hit, miss = 0, []
            for row in gt["cells"]:
                for cell in row:
                    n = C.normalize(cell, True)
                    if not n:
                        continue
                    allpred = C.normalize("\n".join(pred_lines), True)
                    if n in allpred:
                        hit += 1
                    else:
                        miss.append(cell)
            out.append({"img": name, "engine": eng, "gt_rows": gt["rows"],
                        "gt_cols": gt["cols"], "pred_lines": len(pred_lines),
                        "cells_hit": hit, "cells_miss": len(miss),
                        "miss_examples": miss[:5]})
    with open(os.path.join(QDIR, "table_judge.md"), "w", encoding="utf-8") as f:
        f.write("# 表格结构还原判定（机器可核对 + 人工结论）\n\n")
        f.write("判据：①识别行数是否等于 GT 行数；②GT 每个单元格文本是否都能在识别结果中找到（归一化后子串匹配）；"
                "③单元格是否错位（靠行内顺序判断）。\n\n")
        f.write("| 图 | 引擎 | GT行×列 | 识别行数 | 命中单元格 | 未命中 | 未命中示例 |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for o in out:
            f.write("| %s | %s | %d×%d | %d | %d | %d | %s |\n"
                    % (o["img"], o["engine"], o["gt_rows"], o["gt_cols"],
                       o["pred_lines"], o["cells_hit"], o["cells_miss"],
                       "、".join(o["miss_examples"]).replace("|", "\\|") or "—"))
        f.write("\n## 人工结论（本轮由执行者判定，作者可复核）\n\n")
        for o in out:
            if o["cells_miss"] == 0 and abs(o["pred_lines"] - o["gt_rows"]) <= 1:
                v = "行列与单元格全部对上，判 **通过**"
            elif o["cells_miss"] <= 2:
                v = "个别单元格缺失，判 **基本通过（有缺漏）**"
            else:
                v = "多个单元格缺失或行数明显不符，判 **不通过**"
            f.write("- %s / %s：%s\n" % (o["img"], o["engine"], v))
    print("table judge rows:", len(out))


if __name__ == "__main__":
    main()
