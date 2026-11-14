# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime

EP = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(EP, "cells", "ep13-full-001")
man = json.load(open(os.path.join(EP, "samples", "manifest.json"), encoding="utf-8"))
uuid2id = {s["sample_uuid"]: s["sample_id"] for s in man["samples"]}
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}

rows = []
for f in glob.glob(os.path.join(CELLS, "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    base = os.path.basename(f)
    uid = base.split("__")[0]
    d["_file"] = base
    d["_sample"] = uuid2id.get(uid) or d.get("sample_id") or uid
    rows.append(d)

out = [r for r in rows if isinstance(r.get("cer_median"), float) and r["cer_median"] > 0.5]
out.sort(key=lambda r: -r["cer_median"])
print("TOTAL_CELLS", len(rows), "OUTLIERS", len(out))
for r in out:
    print("  %-14s %-11s cer=%.4f n_valid=%s unstable=%s n_fail=%s" % (
        r["engine"], r["_sample"], r["cer_median"], r.get("n_valid"),
        r.get("unstable"), r.get("n_fail")))

# per-engine median of normal cells
eng = {}
for r in rows:
    c = r.get("cer_median")
    if isinstance(c, float):
        eng.setdefault(r["engine"], []).append(c)
print("PER_ENGINE (n, med_all, n_out):")
for k, v in sorted(eng.items()):
    norm = [x for x in v if x < 0.5]
    print("  %-13s n=%d med_all=%.4f med_norm=%.4f out=%d" % (
        k, len(v), statistics.median(v), statistics.median(norm) if norm else -1,
        len(v) - len(norm)))

normal = sorted(c for v in eng.values() for c in v if c < 0.5)
print("GLOBAL_NORMAL_MED", round(statistics.median(normal), 6), "n", len(normal))

# wall
walls = [r["wall_median"] for r in rows if isinstance(r.get("wall_median"), float)]
print("WALL_MED_ALL", round(statistics.median(walls), 1), "n", len(walls))

# mtimes for overall rate
mts = sorted(os.path.getmtime(os.path.join(CELLS, f)) for f in os.listdir(CELLS) if f.endswith(".json"))
span = (mts[-1] - mts[0]) / 60.0
print("CELL_MTIME_SPAN_MIN", round(span, 1), "cells", len(mts),
      "min_per_cell", round(span / max(1, len(mts) - 1), 2))
print("LAST_MTIME", datetime.datetime.fromtimestamp(mts[-1]).isoformat(timespec="seconds"))

st = json.load(open(os.path.join(EP, "control", "batch_state.json"), encoding="utf-8"))
now = datetime.datetime.now()
lp = datetime.datetime.fromisoformat(st["last_progress"])
sa = datetime.datetime.fromisoformat(st["started_at"])
done_this_batch = st["n_run"]
rate = (now - sa).total_seconds() / 60.0 / max(1, done_this_batch)
print("BATCH_RATE_MIN_PER_CELL", round(rate, 1))
total = 156
done = len(rows)
rem = total - done
print("REMAINING_CELLS", rem, "ETA_H", round(rem * rate / 60.0, 2))
print("MIN_SINCE_LP", round((now - lp).total_seconds() / 60.0, 1))
print("SEQ", st["seq"], "CURRENT", st["current"], "NOW", now.isoformat(timespec="seconds"))
