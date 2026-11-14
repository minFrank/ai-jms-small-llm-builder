import json, os, glob, statistics, collections, datetime, hashlib

BASE = r"D:/study/ai-jms/ep13-docparse"
cells_dir = os.path.join(BASE, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(cells_dir, "*.json")))

rows = []
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "READ_ERR", "err": str(e)})
        continue
    rows.append({
        "cell": d.get("cell_key"),
        "engine": d.get("engine"),
        "status": d.get("status"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "n_attempt": d.get("n_attempt"),
        "n_valid": d.get("n_valid"),
        "n_fail": d.get("n_fail"),
        "sample": d.get("sample_id"),
        "sha": (d.get("input") or {}).get("sha256"),
        "layer": d.get("layer"),
        "set": d.get("set"),
    })

print("total_cells", len(rows))
st = collections.Counter(r["status"] for r in rows)
print("status", dict(st))

# engine distribution by status
by_eng = collections.defaultdict(collections.Counter)
for r in rows:
    by_eng[r.get("engine")][r["status"]] += 1
print("engine_status")
for e in sorted(by_eng, key=lambda x: str(x)):
    print("  ", e, dict(by_eng[e]))

# sample counts
print("n_samples", len(set(r.get("sample") for r in rows)))
print("n_engines", len(set(r.get("engine") for r in rows)))
print("layers", dict(collections.Counter(r.get("layer") for r in rows)))
print("sets", dict(collections.Counter(r.get("set") for r in rows)))

# CER stats among complete cells
comp = [r for r in rows if r["status"] == "complete" and isinstance(r.get("cer"), (int, float))]
norm = [r for r in comp if r["cer"] < 0.5]
out = [r for r in comp if r["cer"] >= 0.5]
print("complete_with_cer", len(comp), "normal(<0.5)", len(norm), "outlier(>=0.5)", len(out))
if norm:
    cers = sorted(r["cer"] for r in norm)
    print("median_cer_normal", round(statistics.median(cers), 4))
if comp:
    print("median_cer_all_complete", round(statistics.median(sorted(r["cer"] for r in comp)), 4))
if out:
    print("OUTLIERS:")
    for r in sorted(out, key=lambda x: -x["cer"]):
        print("   cer=%.4f engine=%s sample=%s cell=%s" % (r["cer"], r["engine"], r["sample"], r["cell"]))

# wall
walls = [r["wall"] for r in comp if isinstance(r.get("wall"), (int, float))]
if walls:
    print("median_wall_complete", round(statistics.median(walls), 2))

# non-complete detail
nc = [r for r in rows if r["status"] != "complete"]
print("non_complete_count", len(nc))
for r in nc[:40]:
    print("   NC", r.get("status"), r.get("engine"), r.get("cell"), "err=", r.get("err"), "n_valid=", r.get("n_valid"), "n_fail=", r.get("n_fail"))

# sum n_fail
print("sum_cell_n_fail", sum(r.get("n_fail") or 0 for r in rows))

# timestamps: latest rep ts
latest_ts = None
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        continue
    for rep in d.get("reps") or []:
        t = rep.get("ts")
        if t and (latest_ts is None or t > latest_ts):
            latest_ts = t
print("latest_rep_ts", latest_ts)

# manifest
mpath = os.path.join(BASE, "samples", "manifest.json")
if os.path.exists(mpath):
    with open(mpath, encoding="utf-8") as fh:
        man = json.load(fh)
    print("manifest_type", type(man).__name__, "len", len(man) if hasattr(man, "__len__") else "-")
else:
    print("manifest MISSING")
