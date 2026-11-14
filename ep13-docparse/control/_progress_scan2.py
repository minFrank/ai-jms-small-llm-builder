import json, os, glob, statistics, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
cells_dir = os.path.join(BASE, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(cells_dir, "*.json")))

with open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8") as fh:
    man = json.load(fh)
print("MANIFEST_KEYS", list(man.keys()))
for k, v in man.items():
    print("  ", k, type(v).__name__, len(v) if hasattr(v, "__len__") else v)
# dump a small preview
def preview(x, depth=0):
    if isinstance(x, dict):
        for i, (k, v) in enumerate(x.items()):
            if i > 3: print("   ...more"); break
            print("   " * depth, k, "=", (v if not isinstance(v, (dict, list)) else type(v).__name__))
            if isinstance(v, dict) and depth < 1: preview(v, depth + 1)
            if isinstance(v, list) and v and depth < 1:
                print("   " * (depth + 1), "item0:", v[0])
    return
preview(man)

# sha -> img mapping build
sha2img = {}
def walk(x):
    if isinstance(x, dict):
        s = x.get("sha256") or x.get("sha")
        img = x.get("img") or x.get("image") or x.get("path") or x.get("file") or x.get("name")
        sid = x.get("sample_id") or x.get("id")
        if s and img:
            sha2img[s] = img
        if sid and img:
            sha2img[sid] = img
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(man)
print("sha2img_size", len(sha2img))

# if manifest is a dict sha->img directly
if all(isinstance(v, str) for v in man.values()):
    sha2img.update(man)
    print("treated as direct sha->img, size", len(sha2img))

# cell analysis
allts = []
per_sample = collections.defaultdict(list)
nfail_cells = []
sum_cer = collections.defaultdict(list)
for f in files:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    sid = d.get("sample_id")
    sha = (d.get("input") or {}).get("sha256")
    img = sha2img.get(sha) or sha2img.get(sid) or "?"
    per_sample[img].append((d.get("engine"), d.get("cer_median")))
    if (d.get("n_fail") or 0) > 0:
        nfail_cells.append((d.get("cell_key"), d.get("n_fail"), d.get("n_attempt"), d.get("status")))
    for r in d.get("reps") or []:
        if r.get("ts"):
            allts.append(r["ts"])

allts.sort()
print("earliest_rep_ts", allts[0], "latest_rep_ts", allts[-1], "n_reps", len(allts))
import datetime as dt
fmt = "%Y-%m-%dT%H:%M:%S"
t0 = dt.datetime.strptime(allts[0], fmt)
t1 = dt.datetime.strptime(allts[-1], fmt)
span_min = (t1 - t0).total_seconds() / 60.0
print("span_minutes", round(span_min, 1), "=> min_per_cell_overall", round(span_min / len(files), 2))

print("CELLS_WITH_NFAIL", nfail_cells)

print("PER_SAMPLE (img: engine=cer)")
for img in sorted(per_sample):
    items = sorted(per_sample[img])
    cers = [c for _, c in items if isinstance(c, (int, float))]
    nout = sum(1 for c in cers if c >= 0.5)
    print("  %-46s n=%d outliers=%d median=%.4f max=%.4f" % (img, len(items), nout, statistics.median(cers), max(cers)))
