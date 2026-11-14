import os, glob, datetime, statistics, json, collections
BASE = r"D:/study/ai-jms/ep13-docparse"
files = sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
mts = sorted(os.path.getmtime(f) for f in files)
now = datetime.datetime.now().timestamp()
span_min = (mts[-1] - mts[0]) / 60
print("N", len(files), "SPAN_MIN", round(span_min, 1), "AVG_MIN_PER_CELL", round(span_min / (len(mts) - 1), 2))
w24 = [t for t in mts if t > now - 24 * 3600]
w6 = [t for t in mts if t > now - 6 * 3600]
print("LAST24H_N", len(w24), "MIN_PER_CELL_24H", round(1440 / len(w24), 1) if w24 else None)
print("LAST6H_N", len(w6))
# last 20 cells rate
if len(mts) >= 21:
    print("LAST20_SPAN_MIN", round((mts[-1] - mts[-21]) / 60, 1), "MIN_PER_CELL", round((mts[-1] - mts[-21]) / 60 / 20, 2))
# active window: from first cell today to last
today = datetime.datetime(2026, 11, 6).timestamp()
t = [x for x in mts if x > today]
print("TODAY_N", len(t), "TODAY_SPAN_MIN", round((t[-1] - t[0]) / 60, 1) if t else None,
      "MIN_PER_CELL", round((t[-1] - t[0]) / 60 / (len(t) - 1), 2) if len(t) > 1 else None)
# remaining: failed cells
fails = 0
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    if d.get("status") != "complete":
        fails += 1
print("FAIL_N", fails, "REMAIN_N", fails)
print("ETA_H_AT_16MIN", round(fails * span_min / (len(mts) - 1) / 60, 1))
print("LAST_WRITE", datetime.datetime.fromtimestamp(mts[-1]).isoformat(timespec="seconds"))
print("NOW", datetime.datetime.now().isoformat(timespec="seconds"))
st = json.load(open(os.path.join(BASE, "control/batch_state.json"), encoding="utf-8"))
lp = datetime.datetime.fromisoformat(st["last_progress"])
print("MIN_SINCE_LP", round((datetime.datetime.now() - lp).total_seconds() / 60, 1))
print("STATE_MTIME", datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(BASE, "control/batch_state.json"))).isoformat(timespec="seconds"))
