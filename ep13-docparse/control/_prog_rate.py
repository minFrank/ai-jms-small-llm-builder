# -*- coding: utf-8 -*-
import json, io, glob, os, datetime, collections, statistics

CELLDIR = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
P = lambda t: datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S")

cells = []
for p in glob.glob(os.path.join(CELLDIR, "*.json")):
    c = json.load(io.open(p, encoding="utf-8"))
    reps = [r for r in c.get("reps", []) if r.get("ts")]
    ts = sorted(r["ts"] for r in reps)
    if not ts:
        continue
    cells.append({
        "engine": c["engine"],
        "sample": c.get("sample_id"),
        "first": P(ts[0]),
        "last": P(ts[-1]),
        "n_attempt": c.get("n_attempt"),
        "span_min": (P(ts[-1]) - P(ts[0])).total_seconds() / 60.0,
        "wall": c.get("wall_median"),
        "cer": c.get("cer_median"),
    })

cells.sort(key=lambda r: r["last"])
first = min(c["first"] for c in cells)
last = max(c["last"] for c in cells)
span_h = (last - first).total_seconds() / 3600.0
n = len(cells)

# completion gaps
gaps = [(cells[i]["last"] - cells[i-1]["last"]).total_seconds() / 60.0 for i in range(1, n)]

# per-cell total cost (sum of walls of attempts)
tot_wall_min = sum(c["span_min"] for c in cells)

print("cells_with_ts =", n)
print("first_rep =", first, " last_rep =", last, " span_h = %.2f" % span_h)
print("avg_min_per_cell = %.2f" % (span_h * 60 / n))
print("median_cell_span_min = %.2f" % statistics.median(c["span_min"] for c in cells))
print("median_cell_span_min_last10 = %.2f" % statistics.median(c["span_min"] for c in cells[-10:]))
print("median_gap_min_last10 = %.2f" % statistics.median(gaps[-10:]))
print("median_gap_min_all = %.2f" % statistics.median(gaps))
print("sum_cell_span_h = %.2f" % (tot_wall_min / 60))
print("last5 completions:")
for c in cells[-5:]:
    print("   ", c["last"], c["engine"], c["sample"], "span=%.1fmin" % c["span_min"], "n_att=%s" % c["n_attempt"])

# hourly histogram of completions
hist = collections.Counter(c["last"].strftime("%m-%d %H") for c in cells)
print("completions_by_hour:", sorted(hist.items()))

# n_attempt distribution
print("n_attempt dist:", dict(collections.Counter(c["n_attempt"] for c in cells)))
