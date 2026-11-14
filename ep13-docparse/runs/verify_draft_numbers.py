# -*- coding: utf-8 -*-
import json, os, collections, statistics, glob
BASE = "D:/study/ai-jms/ep13-docparse"
rs = json.load(open(os.path.join(BASE, "gates", "rank_set.json"), encoding="utf-8"))
rc = rs["cells"]
print("1)", dict(collections.Counter(x["engine"] for x in rc)), "note:", rs.get("note", "-"))
cells = [json.load(open(p, encoding="utf-8"))
         for p in glob.glob(os.path.join(BASE, "cells", "ep13-full-001", "*.json"))]
print("2) n=", len(cells), "unstable=", sum(1 for c in cells if c.get("unstable")))

cnt = collections.defaultdict(list)
for c in cells:
    if not c.get("unstable") and c.get("cer_median") is not N...[truncated]
