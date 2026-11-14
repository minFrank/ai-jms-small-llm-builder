# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, collections, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")
man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}

rows = []
for f in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    d["_f"] = f
    rows.append(d)

def lastts(r):
    ts = [x["ts"] for x in r.get("reps", []) if x.get("ts")]
    return max(ts) if ts else None

print("NOW:", datetime.datetime.now().isoformat(timespec="seconds"))
out = [(r["cer_median"], r["engine"], sha2img.get(r["input"]["sha256"], "?"), lastts(r))
       for r in rows if isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] >= 0.5]
out.sort(reverse=True)
KNOWN = {("xiaomi_vl", "shot_01.png"), ("xiaomi_vl", "table_01.png")}
print("OUTLIERS total=%d known=%d outside_known=%d" % (
    len(out), sum(1 for _, e, i, _ in out if (e, i) in KNOWN),
    sum(1 for _, e, i, _ in out if (e, i) not in KNOWN)))
for c, e, i, ts in out:
    print("   %s %.4f %-12s %s last=%s" % ("KNOW" if (e, i) in KNOWN else "NEW ", c, e, i, ts))

by_img = collections.defaultdict(list)
for c, e, i, ts in out:
    by_img[i].append(e)
print("OUT_BY_SAMPLE:", {k: len(v) for k, v in sorted(by_img.items(), key=lambda kv: -len(kv[1]))})

# new cells / progress staleness
last_ts = max(lastts(r) for r in rows)
now = datetime.datetime.now()
lp = datetime.datetime(2026, 11, 7, 18, 3, 45)
print("LAST_CELL_TS:", last_ts, "age_h=%.2f" % ((now - datetime.datetime.fromisoformat(last_ts)).total_seconds() / 3600))
print("LAST_PROGRESS age_min=%.1f" % ((now - lp).total_seconds() / 60))

# cells finished in last 90 min
cut = now - datetime.timedelta(minutes=90)
fmt = "%Y-%m-%dT%H:%M:%S"
print("cells finished last 90min:", sum(1 for r in rows if datetime.datetime.strptime(lastts(r), fmt) >= cut))

# rate: last batch (n_run=4) and last 10
dated = sorted([(datetime.datetime.strptime(lastts(r), fmt), r) for r in rows])
for k in (4, 10, 26):
    sel = dated[-k:]
    span = (sel[-1][0] - sel[0][0]).total_seconds() / 60.0
    print("RATE_last%d: span=%.1fmin cells=%d -> %.2f min/cell" % (k, span, k, span / k))
tot = (dated[-1][0] - datetime.datetime.strptime("2026-11-04T21:18:39", fmt)).total_seconds() / 60.0
print("RATE_overall: %.1f min / %d = %.2f min/cell" % (tot, len(dated), tot / len(dated)))

# wall
w = [r["wall_median"] for r in rows if isinstance(r.get("wall_median"), (int, float))]
print("WALL median=%.1fs p25=%.1f p75=%.1f n=%d" % (
    statistics.median(w), statistics.quantiles(w, n=4)[0], statistics.quantiles(w, n=4)[2], len(w)))

# reps total / n_fail
print("reps_total=%d cell_n_fail>0=%d unstable=%d" % (
    sum(r.get("n_attempt", 0) for r in rows),
    sum(1 for r in rows if r.get("n_fail", 0) > 0),
    sum(1 for r in rows if r.get("unstable"))))
print("attempt_stats:", collections.Counter((r.get("n_attempt"), r.get("n_valid")) for r in rows).most_common(6))
