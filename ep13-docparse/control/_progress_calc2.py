import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")

man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
sha2img, sha2sid = {}, {}
for s in man.get("samples", []):
    sha2img[s["sha256"]] = s["img"]
    sha2sid[s["sha256"]] = s["sample_id"]
print("manifest count:", man.get("count"), "samples:", len(man.get("samples", [])))

rows = []
for p in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    sha = d.get("input", {}).get("sha256")
    reps = d.get("reps") or []
    ts = [r.get("ts") for r in reps if isinstance(r, dict) and r.get("ts")]
    rows.append({
        "file": os.path.basename(p),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": sha,
        "sid": d.get("sample_id"),
        "img": sha2img.get(sha),
        "msid": sha2sid.get(sha),
        "ts_min": min(ts) if ts else None,
        "ts_max": max(ts) if ts else None,
        "n_rep": len(reps),
    })

# ts span
tmin = min(r["ts_min"] for r in rows if r["ts_min"])
tmax = max(r["ts_max"] for r in rows if r["ts_max"])
print("cell rep ts span:", tmin, "->", tmax)
d1 = datetime.datetime.fromisoformat(tmin)
d2 = datetime.datetime.fromisoformat(tmax)
hours = (d2 - d1).total_seconds() / 3600
print("span hours: %.2f" % hours, " cells:", len(rows))
if hours > 0:
    print("rate: %.2f min/cell (span/cells)" % (hours * 60 / len(rows)))

# per-day cell completion (by ts_max)
byday = collections.Counter(r["ts_max"][:10] for r in rows if r["ts_max"])
print("cells by last-ts day:", dict(sorted(byday.items())))

# today only (Nov 7 / Nov 8) rate
def rate_for(day):
    sel = [r for r in rows if r["ts_max"] and r["ts_max"].startswith(day)]
    if not sel:
        return
    lo = min(r["ts_min"] for r in sel)
    hi = max(r["ts_max"] for r in sel)
    h = (datetime.datetime.fromisoformat(hi) - datetime.datetime.fromisoformat(lo)).total_seconds() / 3600
    print("day %s: cells=%d span=%.2fh rate=%.2f min/cell" % (day, len(sel), h, (h * 60 / len(sel)) if h else 0))

for day in sorted(byday):
    rate_for(day)

# status dist by engine
eng = collections.Counter(r["engine"] for r in rows)
print("cells per engine:", dict(sorted(eng.items())))
st = collections.Counter(r["status"] for r in rows)
print("status:", dict(st))
engst = collections.Counter((r["engine"], r["status"]) for r in rows)
for k in sorted(engst):
    print("   ", k, engst[k])

cers = [r["cer"] for r in rows if r["cer"] is not None]
normal = [c for c in cers if c < 0.5]
print("cer n=%d normal(<0.5) n=%d median=%.4f  all_median=%.4f" %
      (len(cers), len(normal), statistics.median(normal), statistics.median(cers)))

# per engine cer median (normal only) - context
print("per-engine CER median (normal cells):")
for e in sorted(eng):
    v = [r["cer"] for r in rows if r["engine"] == e and r["cer"] is not None and r["cer"] < 0.5]
    a = [r["cer"] for r in rows if r["engine"] == e and r["cer"] is not None]
    if v:
        print("   %-12s normal n=%2d med=%.4f | all n=%2d med=%.4f" % (e, len(v), statistics.median(v), len(a), statistics.median(a)))

outs = sorted([r for r in rows if r["cer"] is not None and r["cer"] >= 0.5], key=lambda r: -r["cer"])
print("outliers >=0.5: %d" % len(outs))
byimg = collections.Counter(r["img"] for r in outs)
print("outlier imgs:", dict(byimg))
for r in outs:
    print("   %.3f | %-12s | %s | %s | ts=%s" % (r["cer"], r["engine"], r["img"], r["msid"], r["ts_max"]))

walls = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
print("wall median: %.2f s (n=%d); min=%.2f max=%.2f" % (statistics.median(walls), len(walls), min(walls), max(walls)))
print("per-engine wall median:")
for e in sorted(eng):
    v = [r["wall"] for r in rows if r["engine"] == e and isinstance(r["wall"], (int, float))]
    print("   %-12s %.2f s (n=%d)" % (e, statistics.median(v), len(v)))

# cell success / attempts sanity
print("cells with n_fail>0:", sum(1 for p in glob.glob(os.path.join(CELLS, '*.json'))
      if (json.load(open(p, encoding='utf-8')).get('n_fail') or 0) > 0))
