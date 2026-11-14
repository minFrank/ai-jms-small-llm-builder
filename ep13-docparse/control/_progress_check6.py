# -*- coding: utf-8 -*-
import json, glob, os, sys, io, statistics, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = r"D:/study/ai-jms/ep13-docparse"
files = glob.glob(B + "/cells/ep13-full-001/*.json")
mts = sorted(os.path.getmtime(f) for f in files)
gaps = [(mts[i+1]-mts[i])/60 for i in range(len(mts)-1)]
g30 = gaps[-30:]
print("last30 gaps: median=%.2f mean=%.2f max=%.2f min=%.2f min/cell" % (
    statistics.median(g30), statistics.mean(g30), max(g30), min(g30)))
print("last10 gaps:", [round(g,1) for g in gaps[-10:]])
print("gaps>30min in last 30:", [(datetime.datetime.fromtimestamp(mts[-30+i]).strftime('%H:%M'), round(g,1)) for i, g in enumerate(g30) if g > 30])
# err fields
errs = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    if d.get("err") or d.get("err_kind"):
        errs.append((os.path.basename(f), str(d.get("err"))[:80], d.get("err_kind")))
print("cells with err:", len(errs))
for e in errs[:10]: print("  ", e)
# unstable
uns = [(os.path.basename(f), json.load(open(f, encoding='utf-8')).get('cell_success_rate')) for f in files if json.load(open(f, encoding='utf-8')).get('unstable')]
print("unstable:", uns)
