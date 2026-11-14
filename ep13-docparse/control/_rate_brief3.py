import json, os, glob, datetime, statistics
base = r"D:/study/ai-jms/ep13-docparse"
# recent cell completion rate: mtimes in last 6h
mts = sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")))
now = datetime.datetime.now().timestamp()
recent = [t for t in mts if now - t <= 6*3600]
print("cells_last6h", len(recent))
if len(recent) >= 2:
    span = (recent[-1] - recent[0]) / 60
    print("span_min", round(span, 1), "per_cell", round(span / (len(recent) - 1), 2) if len(recent) > 1 else None)
# oxr-only rate (this batch): oxr cell mtimes
oxr = []
for f in glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")):
    c = json.load(open(f, encoding="utf-8"))
    if c.get("engine") == "oxr":
        oxr.append(os.path.getmtime(f))
oxr.sort()
print("oxr_cells", len(oxr), "first", datetime.datetime.fromtimestamp(oxr[0]).strftime("%m-%d %H:%M"),
      "last", datetime.datetime.fromtimestamp(oxr[-1]).strftime("%m-%d %H:%M"))
if len(oxr) > 1:
    print("oxr_per_cell_min", round((oxr[-1]-oxr[0])/60/(len(oxr)-1), 2))
# overall engine median CER
from collections import defaultdict
by = defaultdict(list)
for f in glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")):
    c = json.load(open(f, encoding="utf-8"))
    if isinstance(c.get("cer_median"), (int, float)):
        by[c["engine"]].append(c["cer_median"])
for k in sorted(by):
    print("CER_MED", k, len(by[k]), round(statistics.median(by[k]), 4))
