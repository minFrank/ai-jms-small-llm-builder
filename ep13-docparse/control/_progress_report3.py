# -*- coding: utf-8 -*-
import json, os, glob, statistics, collections, datetime

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2id = {s["sha256"]: s["sample_id"] for s in man["samples"]}

files = sorted(glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")))
st = json.load(open(os.path.join(base, "control", "batch_state.json"), encoding="utf-8"))
started = datetime.datetime.fromisoformat(st["started_at"])
now = datetime.datetime.now()
print("state:", json.dumps(st, ensure_ascii=False))
print("now:", now.isoformat(timespec="seconds"))

rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_mt"] = os.path.getmtime(f)
    rows.append(d)

thisrun = [r for r in rows if datetime.datetime.fromtimestamp(r["_mt"]) >= started]
prev = [r for r in rows if datetime.datetime.fromtimestamp(r["_mt"]) < started]
print("cells total=%d | thisrun=%d | prior=%d" % (len(rows), len(thisrun), len(prev)))
print("thisrun status:", collections.Counter(r["status"] for r in thisrun))
print("prior status:", collections.Counter(r["status"] for r in prev))
print("thisrun by engine:", {e: dict(c) for e, c in
      ((e, collections.Counter(r["status"] for r in thisrun if r["engine"] == e)) for e in sorted({r["engine"] for r in thisrun}))})

# rate this run
elapsed_h = (now - started).total_seconds() / 3600
print("elapsed h: %.2f | thisrun cells: %d | min/cell (run avg): %.2f" % (
    elapsed_h, len(thisrun), elapsed_h * 60 / max(1, len(thisrun))))

# recent window rate: cells finished in last 30 / 60 min
for w in (30, 60):
    cut = (now - datetime.timedelta(minutes=w)).timestamp()
    n = sum(1 for r in rows if r["_mt"] >= cut)
    print("cells finished in last %d min: %d -> %.2f min/cell" % (w, n, w / n if n else float("nan")))

# gaps of last 20 completions
mts = sorted(r["_mt"] for r in rows)
gaps = [(mts[i] - mts[i - 1]) / 60 for i in range(1, len(mts))]
print("gap median last10/20/40: %.2f / %.2f / %.2f min" % (
    statistics.median(gaps[-10:]), statistics.median(gaps[-20:]), statistics.median(gaps[-40:])))

# remaining & ETA
seq_cur, seq_tot = (int(x) for x in st["seq"].split("/"))
remaining = seq_tot - seq_cur
rate_run = elapsed_h * 60 / max(1, len(thisrun))
rate_recent = statistics.median(gaps[-20:])
print("seq %s remaining=%d" % (st["seq"], remaining))
print("ETA h @ run-avg rate: %.2f | @ last20-gap rate: %.2f" % (
    remaining * rate_run / 60, remaining * rate_recent / 60))

# state vs cells
print("state n_run+n_skip+n_fail = %d ; cells on disk = %d (complete %d / failed %d)" % (
    st["n_run"] + st["n_skip"] + st["n_fail"], len(rows),
    sum(1 for r in rows if r["status"] == "complete"),
    sum(1 for r in rows if r["status"] == "failed")))

# outliers
outl = []
for r in rows:
    c = r.get("cer_median")
    if isinstance(c, (int, float)) and c >= 0.5:
        sha = r["input"]["sha256"]
        outl.append((c, r["engine"], sha2id.get(sha, "?"),
                     datetime.datetime.fromtimestamp(r["_mt"]).strftime("%m-%d %H:%M")))
print("OUTLIERS n=%d" % len(outl))
for c, e, s, t in sorted(outl, key=lambda x: -x[0]):
    print("   %.3f | %-13s | %-11s | %s" % (c, e, s, t))

cerc = [r["cer_median"] for r in rows if isinstance(r.get("cer_median"), (int, float))]
norm = [c for c in cerc if c < 0.5]
print("CER median normal(<0.5) n=%d: %.4f" % (len(norm), statistics.median(norm)))
walls = [r["wall_median"] for r in rows if isinstance(r.get("wall_median"), (int, float))]
print("wall median all n=%d: %.1fs" % (len(walls), statistics.median(walls)))

# engine distribution
print("engine status:", {e: dict(c) for e, c in
      ((e, collections.Counter(r["status"] for r in rows if r["engine"] == e)) for e in sorted({r["engine"] for r in rows}))})
