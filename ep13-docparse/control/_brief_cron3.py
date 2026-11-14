import json, glob, os, collections, datetime, time

BASE = r"D:/study/ai-jms/ep13-docparse"

files = sorted(glob.glob(os.path.join(BASE, "cells/*/*.json")))
bydir = collections.Counter()
mt = {}
for f in files:
    d = os.path.basename(os.path.dirname(f))
    bydir[d] += 1
    mt[d] = max(mt.get(d, 0), os.path.getmtime(f))
print("CELLS_DIRS")
for d in sorted(bydir):
    print("  ", d, bydir[d], "newest=", datetime.datetime.fromtimestamp(mt[d]).strftime("%m-%d %H:%M"))

rows = []
for f in sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json"))):
    rows.append(json.load(open(f, encoding="utf-8")))
print("run_id dist:", dict(collections.Counter(r.get("run_id") for r in rows)))
print("status dist:", dict(collections.Counter(r.get("status") for r in rows)))
print("engine dist:", dict(collections.Counter(r.get("engine") for r in rows)))
print("layer dist:", dict(collections.Counter(r.get("layer") for r in rows)))
print("set dist:", dict(collections.Counter(r.get("set") for r in rows)))
print("max_attempts dist:", dict(collections.Counter(r.get("max_attempts") for r in rows)))
print("unstable:", dict(collections.Counter(r.get("unstable") for r in rows)))

# any cell with status other than complete/failed
odd = [r.get("cell_key") for r in rows if r.get("status") not in ("complete", "failed")]
print("odd status:", odd)

# cell_success_rate / trunc stats
sr = [r.get("cell_success_rate") for r in rows if isinstance(r.get("cell_success_rate"), (int, float))]
print("cell_success_rate median:", sorted(sr)[len(sr)//2] if sr else None, "n<1:", sum(1 for x in sr if x < 1))
tr = [r.get("trunc_rate") for r in rows if isinstance(r.get("trunc_rate"), (int, float))]
print("trunc_rate >0:", sum(1 for x in tr if x > 0), "max:", max(tr) if tr else None)

# incomplete matrix check: 26 samples x 5 engines
sids = set(r.get("sample_id") for r in rows)
engs = set(r.get("engine") for r in rows)
print("n_samples", len(sids), "n_engines", len(engs), "expected", len(sids)*len(engs), "actual", len(rows))
missing = []
have = set((r.get("sample_id"), r.get("engine")) for r in rows)
for s in sids:
    for e in engs:
        if (s, e) not in have:
            missing.append((s, e))
print("missing pairs:", missing)

# timeline: per-day per-engine
print("=== last cell write ===")
mx = max(os.path.getmtime(f) for f in glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
print(datetime.datetime.fromtimestamp(mx).strftime("%Y-%m-%d %H:%M:%S"), "age_min=", round((time.time()-mx)/60, 1))

# batch_state / heartbeat / task mtimes
for n in ("batch_state.json", "heartbeat.json", "task.json"):
    p = os.path.join(BASE, "control", n)
    print(n, "mtime", datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S"),
          "age_min=", round((time.time()-os.path.getmtime(p))/60, 1))
    print("   ", open(p, encoding="utf-8").read().strip())
