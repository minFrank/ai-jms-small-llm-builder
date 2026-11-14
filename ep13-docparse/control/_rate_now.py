# -*- coding: utf-8 -*-
import os, glob, datetime, statistics
files = glob.glob(r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001/*.json")
mts = sorted(os.path.getmtime(f) for f in files)
today = [m for m in mts if datetime.datetime.fromtimestamp(m).strftime("%Y-%m-%d") == "2026-11-07"]
gaps = [(b - a) / 60 for a, b in zip(today, today[1:])]
print("TODAY_CELLS:", len(today))
print("GAPS_MIN: median=%.2f mean=%.2f max=%.1f" % (statistics.median(gaps), statistics.mean(gaps), max(gaps)))
# window excluding gaps > 60min (idle)
active = [g for g in gaps if g <= 60]
if active:
    print("ACTIVE_GAPS: n=%d median=%.2f" % (len(active), statistics.median(active)))
print("LAST3:", [datetime.datetime.fromtimestamp(m).strftime("%H:%M") for m in today[-5:]])
# count cells completed after 13:00
print("AFTER_1300:", sum(1 for m in today if datetime.datetime.fromtimestamp(m).strftime("%H:%M") >= "13:00"))
