# -*- coding: utf-8 -*-
"""只读断言：把报告 HTML 里每个 data-metric 数字对 progress.json 重算比对。"""
import json
import os
import re
import sys
from html.parser import HTMLParser

import metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "report_ep11.html")


class Grab(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._cur = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "data-metric" in d:
            self._cur = d["data-metric"]
            self.items.append([self._cur, ""])

    def handle_data(self, data):
        if self._cur and self.items:
            self.items[-1][1] += data

    def handle_endtag(self, tag):
        self._cur = None


def expected():
    """从 progress.json 重算每个 metric 的期望值。"""
    data = M.compute()
    cells = data["cells"]
    exp = {}
    exp["cells_total"] = len(cells)
    exp["engines_n"] = len(data["engines"])
    exp["images_n"] = len(data["images"])
    exp["disp_over_n"] = len(data["disp_over"])
    exp["seg_bad_n"] = len(data["seg_bad"])
    exp["density_cells"] = len(cells)
    exp["density_images"] = len(data["images"])
    exp["density_fails"] = len(data["failures"])
    for k, c in cells.items():
        if c["mode"] == "cold":
            pre = "cold_%s_%s_" % (c.get("cell"), c["img"])
        else:
            pre = "hot_%s_%s_" % (c["engine"], c["img"])
        exp[pre + "median"] = c["median"]
        exp[pre + "min"] = c["min"]
        exp[pre + "max"] = c["max"]
        exp[pre + "spread"] = c["spread_pct"]
        exp[pre + "resid"] = c["seg_residual_pct"]
        exp[pre + "rss"] = c["peak_rss_mb"]
        exp[pre + "cer"] = c["cer_main"]
    # 体积 / 内存（报告第九节）
    for e in data["engines"]:
        mb = [c["model_bytes"] for c in cells.values()
              if c["engine"] == e and c["model_bytes"]]
        rss = [c["peak_rss_mb"] for c in cells.values()
               if c["engine"] == e and c["peak_rss_mb"]]
        exp["mb_%s" % e] = (max(mb) / 1048576.0) if mb else 0
        exp["rss_%s" % e] = max(rss) if rss else 0
    # 断网批（报告第十一节）
    offp = os.path.join(BASE, "result_offline.json")
    if os.path.exists(offp):
        off = json.load(open(offp, encoding="utf-8"))
        for k, c in off.get("cells", {}).items():
            pre = "off_%s_%s_%s_" % (c["engine"], c["img"], c["mode"])
            exp[pre + "cer"] = c.get("cer_main")
            exp[pre + "median"] = c.get("median")
    meta = os.path.join(BASE, "gt", "samples_meta.json")
    if os.path.exists(meta):
        for x in json.load(open(meta, encoding="utf-8")):
            exp["bytes_%s" % x["name"]] = x["bytes"]
    bdir = os.path.join(BASE, "output", "batch")
    if os.path.isdir(bdir):
        for f in os.listdir(bdir):
            if f.endswith(".json"):
                v = json.load(open(os.path.join(bdir, f), encoding="utf-8"))
                k = f[:-5]
                exp["batch_%s_load" % k] = v.get("load_s")
                exp["batch_%s_wall" % k] = v.get("wall_s")
                exp["batch_%s_spp" % k] = v.get("s_per_page")
                exp["batch_%s_ppm" % k] = v.get("pages_per_min")
    # 分类 CER 中位
    import statistics as st
    catm = os.path.join(BASE, "gt", "samples_meta.json")
    if os.path.exists(catm):
        cat = {x["name"]: x["category"] for x in json.load(open(catm, encoding="utf-8"))}
        byc = {}
        for c in cells.values():
            if c["mode"] == "hot" and c["cer_main"] is not None:
                byc.setdefault((c["engine"],
                                cat.get(c["img"].replace(".png", ""), "?")),
                               []).append(c["cer_main"])
        for (e, cname), vals in byc.items():
            vals = sorted(vals)
            exp["cer_%s_%s_med" % (e, cname)] = st.median(vals)
            exp["cer_%s_%s_min" % (e, cname)] = vals[0]
            exp["cer_%s_%s_max" % (e, cname)] = vals[-1]
    # 补跑批次（报告第十四节）
    tu = M.topup_compare()
    if tu:
        exp["tu_tasks"] = tu["n_tasks"]
        exp["tu_unique"] = tu["n_unique"]
        exp["tu_nlt3_fixed"] = tu["n_lt3_fixed"]
        exp["tu_drift_max"] = tu["drift_max_pct"]
        exp["tu_drift_big"] = tu["drift_big_pct"]
        sk = cells.get(tu["timeout_cell"], {})
        exp["tu_skew_median"] = sk.get("median")
        exp["tu_skew_spread"] = sk.get("spread_pct")
        exp["tu_skew_cer"] = sk.get("cer_main")
        for r in tu["rows"]:
            pre_id = "tu_%s_" % r["cell"]
            exp[pre_id + "n_b"] = r["n_b"]
            exp[pre_id + "n_a"] = r["n_a"]
            exp[pre_id + "sp_b"] = r["sp_b"]
            exp[pre_id + "sp_a"] = r["sp_a"]
            exp[pre_id + "md_b"] = r["md_b"]
            exp[pre_id + "md_a"] = r["md_a"]
            if r["mode"] == "cold":
                exp["tu_cold_spr_%s_%s" % (r["engine"], r["img"])] = r["sp_a"]
        for r in tu["still_over"]:
            c = cells.get(r["cell"], {})
            exp["tu_abs_%s" % r["cell"]] = (
                (c["max"] - c["min"])
                if c.get("max") is not None and c.get("min") is not None else None)
    return exp


def main():
    if not os.path.exists(HTML):
        print("报告不存在：", HTML)
        return 1
    html = open(HTML, encoding="utf-8").read()
    g = Grab()
    g.feed(html)
    exp = expected()
    ok, bad, missing = 0, [], []
    for name, text in g.items:
        text = text.strip()
        if name not in exp:
            missing.append(name)
            continue
        want = exp[name]
        if want is None:
            if text == "失败":
                ok += 1
            else:
                bad.append((name, text, "失败"))
            continue
        try:
            got = float(text.replace(",", ""))
        except ValueError:
            bad.append((name, text, want))
            continue
        # 容忍度按「报告里显示几位小数」给：2 位小数的显示误差上限是 0.005
        if abs(got - float(want)) > max(abs(float(want)) * 0.005, 0.005):
            bad.append((name, text, want))
        else:
            ok += 1
    total = ok + len(bad)
    print("断言：共 %d 项 / 通过 %d / 不符 %d / 无对应重算项 %d"
          % (total, ok, len(bad), len(missing)))
    for b in bad[:30]:
        print("  不符 %s: html=%s recomputed=%s" % b)
    if missing:
        print("  未覆盖（HTML 有但重算集没有）:", ", ".join(missing[:20]))
    if total == 0:
        print("  FATAL: 断言项为 0，属假绿")
        return 2
    return 0 if not bad else 3


if __name__ == "__main__":
    sys.exit(main())
