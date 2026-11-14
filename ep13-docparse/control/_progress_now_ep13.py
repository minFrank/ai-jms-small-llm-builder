# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")
MANI = os.path.join(BASE, "samples", "manifest.json")

rows = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(CELLS, "*.json")))]

# manifest sha256 -> img
man = json.load(open(MANI, encoding="utf-8"))
print("manifest type:", type(man).__name__)
s2i = {}
def walk(o):
    if isinstance(o, dict):
        sh = o.get("sha256") or o.get("input_sha256")
        img = o.get("img") or o.get("path") or o.get("file")
        if sh and img:
            s2i[sh] = img
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
walk(man)
print("manifest sha->img entries:", len(s2i))

# status
st = collections.Counter(r["status"] for r in rows)
print("STATUS:", dict(st))
# per engine
eng_status = collections.defaultdict(collections.Counter)
for r in rows:
    eng_status[r["engine"]][r["status"]] += 1
print("PER_ENGINE_STATUS:")
for e in sorted(eng_status):
    print("  ", e, dict(eng_status[e]))

# non-complete list
nc = [r for r in rows if r["status"] != "complete"]
print("NON_COMPLETE:", len(nc))
for r in nc:
    print("  ", r["cell_key"], r["status"], r.get("err_kind"), r.get("err"))

# CER stats
def g(r, k):
    v = r.get(k)
    return v if isinstance(v, (int, float)) else None

normal = [r for r in rows if g(r, "cer_median") is not None and r["cer_median"] < 0.5]
cvals = sorted(r["cer_median"] for r in normal)
print("NORMAL_CELLS(<0.5):", len(cvals), "median:", round(statistics.median(cvals), 4))
# all cells with cer
allcer = [r for r in rows if g(r, "cer_median") is not None]
print("CELLS_WITH_CER:", len(allcer))
out = sorted([r for r in allcer if r["cer_median"] >= 0.5], key=lambda r: -r["cer_median"])
print("OUTLIERS(>=0.5):", len(out))
for r in out:
    img = s2i.get(r["input"].get("sha256"), "?")
    print("   %.4f | %s | %s | %s | %s" % (r["cer_median"], r["engine"], r["sample_id"], img, r["set"]))

# missing cer among complete
miss = [r for r in rows if r["status"] == "complete" and g(r, "cer_median") is None]
print("COMPLETE_BUT_NO_CER:", len(miss), [r["cell_key"] for r in miss][:10])

# wall median
walls = [r["wall_median"] for r in rows if g(r, "wall_median") is not None]
print("WALL_CELLS:", len(walls), "median:", round(statistics.median(walls), 2),
      "p25:", round(statistics.quantiles(walls, n=4)[0], 2), "p75:", round(statistics.quantiles(walls, n=4)[2], 2))

# per engine wall + cer
print("PER_ENGINE (n, cer_med, wall_med):")
for e in sorted(set(r["engine"] for r in rows)):
    sub = [r for r in rows if r["engine"] == e and g(r, "cer_median") is not None]
    sw = [r["wall_median"] for r in rows if r["engine"] == e and g(r, "wall_median") is not None]
    if sub:
        print("   %-14s n=%2d cer_med=%.4f wall_med=%s" % (e, len(sub), statistics.median([r["cer_median"] for r in sub]),
              round(statistics.median(sw), 2) if sw else None))
    else:
        print("   %-14s n=0" % e)

# timestamps -> rate
def maxts(r):
    ts = [rep.get("ts") for rep in r.get("reps", []) if rep.get("ts")]
    return max(ts) if ts else None
def mints(r):
    ts = [rep.get("ts") for rep in r.get("reps", []) if rep.get("ts")]
    return min(ts) if ts else None

dated = [(maxts(r), mints(r), r["cell_key"]) for r in rows]
dated = [d for d in dated if d[0]]
dated.sort()
print("CELLS_WITH_TS:", len(dated))
print("FIRST_TS:", dated[0][0], " LAST_TS:", dated[-1][0])
if dated:
    last_start = dated[-1][1] or dated[-1][0]
    # last batch = cells whose max ts within last N; use n_run=4
    n_run = 4
    lastN = dated[-n_run:]
    t0 = min(d[1] for d in lastN if d[1]) or lastN[0][1]
    t1 = max(d[0] for d in lastN)
    fmt = "%Y-%m-%dT%H:%M:%S"
    a = datetime.datetime.strptime(t0, fmt); b = datetime.datetime.strptime(t1, fmt)
    mins = (b - a).total_seconds() / 60.0
    print("LAST_BATCH window:", t0, "->", t1, "span_min=%.2f" % mins, "cells=", n_run,
          "min/Cell=%.2f" % (mins / n_run))
    # overall rate: total span / cells
    a0 = datetime.datetime.strptime(dated[0][1] or dated[0][0], fmt)
    b0 = datetime.datetime.strptime(dated[-1][0], fmt)
    total_min = (b0 - a0).total_seconds() / 60.0
    print("OVERALL span:", dated[0][1] or dated[0][0], "->", dated[-1][0],
          "min=%.1f" % total_min, "cells=", len(dated), "avg_min/cell=%.2f" % (total_min / len(dated)))
    # hourly throughput last 24h
    now = datetime.datetime(2026, 11, 8, 2, 55)
    for h in (6, 12, 24):
        cut = now - datetime.timedelta(hours=h)
        n = sum(1 for d in dated if datetime.datetime.strptime(d[0], fmt) >= cut)
        print("  cells finished last %dh: %d (%.2f min/cell)" % (h, n, (h * 60.0 / n) if n else -1))
