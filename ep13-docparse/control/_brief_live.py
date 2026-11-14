import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
now = datetime.datetime.now()
print("NOW", now.isoformat())

st = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
print("STATE", json.dumps(st, ensure_ascii=False))

hb_p = os.path.join(BASE, "control", "heartbeat.json")
if os.path.exists(hb_p):
    hb = json.load(open(hb_p, encoding="utf-8"))
    print("HEARTBEAT", json.dumps(hb, ensure_ascii=False))
    print("HEARTBEAT_MTIME", datetime.datetime.fromtimestamp(os.path.getmtime(hb_p)).isoformat())

cells = sorted(glob.glob(os.path.join(BASE, "cells", "ep13-full-001", "*.json")))
print("N_CELLS_FILES", len(cells))

recs = []
for p in cells:
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        recs.append({"file": os.path.basename(p), "status": "PARSE_ERR", "err": str(e)})
        continue
    d["_file"] = os.path.basename(p)
    recs.append(d)

def g(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default

# field inventory sample
print("SAMPLE_KEYS", sorted(recs[0].keys()))
by_status = collections.Counter(str(g(r, "status", default="NONE")) for r in recs)
print("STATUS_DIST", dict(by_status))

# per-engine status
eng_stat = collections.Counter()
for r in recs:
    eng_stat[(str(g(r, "engine", default="?")), str(g(r, "status", default="?")))] += 1
print("ENGINE_STATUS", dict(eng_stat))

# non-complete list
nonc = [r for r in recs if str(g(r, "status", default="")) != "complete"]
print("NON_COMPLETE", len(nonc))
for r in nonc:
    print("  NC", r["_file"], g(r, "status"), g(r, "engine"), g(r, "error", "err", "msg"))

# CER stats
cer_ok = []
outliers = []
for r in recs:
    if str(g(r, "status", default="")) != "complete":
        continue
    c = g(r, "cer_median", "cer")
    if c is None:
        continue
    try:
        c = float(c)
    except Exception:
        continue
    if c < 0.5:
        cer_ok.append(c)
    else:
        outliers.append((c, g(r, "engine"), g(r, "sample", "img", "input", "input_sha256"), r["_file"]))

if cer_ok:
    print("CER_N_OK", len(cer_ok), "CER_MEDIAN", round(statistics.median(cer_ok), 4))
outliers.sort(reverse=True)
for o in outliers:
    print("  OUTLIER", round(o[0], 4), o[1], o[2], o[3])

# wall median
walls = []
for r in recs:
    if str(g(r, "status", default="")) != "complete":
        continue
    w = g(r, "wall_median", "wall_s", "wall")
    if w is None:
        continue
    try:
        walls.append(float(w))
    except Exception:
        pass
if walls:
    print("WALL_N", len(walls), "WALL_MEDIAN", round(statistics.median(walls), 2), "min",
          round(min(walls), 2), "max", round(max(walls), 2))

# completion times from mtime for rate
times = []
for p in cells:
    times.append((os.path.getmtime(p), os.path.basename(p)))
times.sort()
done = [t for t in times if str(g(next(r for r in recs if r["_file"] == t[1]), "status", default="")) == "complete"]
print("N_COMPLETE", len(done))
if len(done) >= 2:
    span = done[-1][0] - done[0][0]
    print("RATE_SPAN_SEC", round(span, 1), "N_IN_SPAN", len(done) - 1,
          "MIN_PER_CELL", round(span / 60.0 / (len(done) - 1), 2))
    print("FIRST_DONE", datetime.datetime.fromtimestamp(done[0][0]).isoformat(),
          "LAST_DONE", datetime.datetime.fromtimestamp(done[-1][0]).isoformat())
