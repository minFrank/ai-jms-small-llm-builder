# -*- coding: utf-8 -*-
"""断网批聚合 -> result_offline.json（与在线批同口径，供报告第十一节引用）。"""
import json
import os

import metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    data = M.compute(os.path.join(BASE, "progress_offline.json"))
    cells = {}
    for k, c in data["cells"].items():
        cells[k] = {f: c[f] for f in
                    ("engine", "img", "mode", "n", "median", "status", "err",
                     "cer_main", "peak_rss_mb", "seg_residual_pct")}
    net = {}
    p = os.path.join(BASE, "logs", "net_selftest.json")
    if os.path.exists(p):
        net = json.load(open(p, encoding="utf-8"))
    blocked = []
    p2 = os.path.join(BASE, "logs", "net_blocked.jsonl")
    if os.path.exists(p2):
        for line in open(p2, encoding="utf-8"):
            line = line.strip()
            if line:
                blocked.append(json.loads(line))
    out = {"cells": cells, "net_selftest": net,
           "net_blocked_attempts": len(blocked),
           "net_blocked_kinds": sorted({b["kind"] for b in blocked}),
           "failures": data["failures"], "bad_lines": data["bad_lines"]}
    with open(os.path.join(BASE, "result_offline.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("offline cells=%d fails=%d net_blocked=%d kinds=%s selftest_blocked=%s"
          % (len(cells), len(data["failures"]), len(blocked),
             out["net_blocked_kinds"], net.get("blocked")))


if __name__ == "__main__":
    main()
