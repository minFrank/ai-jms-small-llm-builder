# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r"D:/study/ai-jms/ep13-docparse"
CELLD = f"{BASE}/cells/ep13-full-001"
files = sorted(glob.glob(f"{CELLD}/*.json"))
rows = []
for p in files:
    d = json.load(open(p, encoding="utf-8"))
    rows.append((os.path.getmtime(p), d, p))
rows.sort()
cut = datetime.datetime(2026, 11, 6, 8, 0).timestamp()
inb = [(m, d, p) for m, d, p in rows if m >= cut]
print("cells mtime >= 11-06 08:00 :", len(inb))
print("window:", datetime.datetime.fromtimestamp(inb[0][0]).strftime("%H:%M:%S"),
      "->", datetime.datetime.fromtimestamp(inb[-1][0]).strftime("%H:%M:%S"))
span = (inb[-1][0] - inb[0][0]) / 60.0
print("span_min=%.1f rate=%.2f min/cell" % (span, span / len(inb)))
from collections import Counter
print("status in window:", dict(Counter(d.get("status") for _, d, _ in inb)))
print("engine in window:", dict(Counter(d.get("engine") for _, d, _ in inb)))
okw = [(m, d) for m, d, _ in inb if d.get("status") == "complete"]
if len(okw) >= 2:
    s = (okw[-1][0] - okw[0][0]) / 60.0
    print("complete-in-window n=%d span=%.1f min rate=%.2f min/cell" % (len(okw), s, s / max(1, len(okw) - 1)))
# inter-cell gap of last 8 touched cells
g = [(rows[i][0] - rows[i-1][0]) / 60.0 for i in range(len(rows) - 7, len(rows))]
print("last 8 gaps min:", [round(x, 1) for x in g])
print("age of last cell min: %.1f" % ((time.time() - rows[-1][0]) / 60.0))
# overall
print("overall span: %s -> %s = %.1f h for %d cells" % (
    datetime.datetime.fromtimestamp(rows[0][0]).strftime("%m-%d %H:%M"),
    datetime.datetime.fromtimestamp(rows[-1][0]).strftime("%m-%d %H:%M"),
    (rows[-1][0] - rows[0][0]) / 3600.0, len(rows)))
# state vs cells
st = json.load(open(f"{BASE}/control/batch_state.json", encoding="utf-8"))
print("state:", json.dumps(st, ensure_ascii=False))
comp = sum(1 for _, d, _ in rows if d.get("status") == "complete")
fail = sum(1 for _, d, _ in rows if d.get("status") != "complete")
print("complete=%d fail=%d total=%d | n_run+n_skip=%d n_run+n_skip+n_fail=%d" % (
    comp, fail, len(rows), st["n_run"] + st["n_skip"], st["n_run"] + st["n_skip"] + st["n_fail"]))
# last_progress age
lp = datetime.datetime.fromisoformat(st["last_progress"])
print("last_progress age_min=%.1f  finished_at=%s" % ((datetime.datetime.now() - lp).total_seconds() / 60.0, st.get("finished_at")))
