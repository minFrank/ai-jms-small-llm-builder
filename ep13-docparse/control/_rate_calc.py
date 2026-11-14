# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime
from collections import Counter

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")
now = datetime.datetime.now()

files = glob.glob(os.path.join(CELLS, "*.json"))
info = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    info.append((datetime.datetime.fromtimestamp(os.path.getmtime(f)), d.get("status"), d.get("engine"), d.get("wall_median")))

info.sort()
# per hour counts
by_hour = Counter()
for m, s, e, w in info:
    by_hour[m.strftime("%m-%d %H")] += 1
print("cells_per_hour:")
for k in sorted(by_hour):
    print("  ", k, by_hour[k])

start = datetime.datetime(2026, 11, 6, 14, 7, 23)
print("cells_written_since_batch_started_at =", sum(1 for m, *_ in info if m >= start))
print("last_cell_write =", info[-1][0].isoformat(timespec="seconds"), "age_min=%.1f" % ((now - info[-1][0]).total_seconds()/60))

# productive window rate: last 6 hours of writes
win_start = info[-1][0] - datetime.timedelta(hours=6)
w = [x for x in info if x[0] >= win_start]
if len(w) > 1:
    span = (w[-1][0] - w[0][0]).total_seconds()/60
    print("last6h_window: n=%d span_min=%.1f rate=%.2f min/cell" % (len(w), span, span/(len(w)-1)))

# per-engine wall median
by_eng = {}
for m, s, e, wall in info:
    if s == "complete" and isinstance(wall, (int, float)):
        by_eng.setdefault(e, []).append(wall)
print("wall_median_by_engine(complete):")
for e in sorted(by_eng):
    print("  ", e, "n=%d med=%.2fs" % (len(by_eng[e]), statistics.median(by_eng[e])))

# per-sample completeness
bysample = {}
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    bysample.setdefault(d.get("sample_id"), []).append(d.get("status"))
allc = [k for k, v in bysample.items() if all(x == "complete" for x in v)]
print("samples_all5_complete = %d / %d" % (len(allc), len(bysample)))
print("samples_not_all_complete = %d" % (len(bysample) - len(allc)))
