# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:/study/ai-jms/ep13-docparse"
RUN  = "ep13-full-001"
CELLS = os.path.join(BASE, "cells", RUN)

now = datetime.datetime.now()
print("NOW:", now.isoformat())

st = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
print("BATCH_STATE:", json.dumps(st, ensure_ascii=False))

manifest = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
# sha256 -> img mapping
if isinstance(manifest, dict):
    print("MANIFEST type dict, keys sample:", list(manifest.keys())[:3])
else:
    print("MANIFEST type list, len:", len(manifest), "sample:", json.dumps(manifest[0], ensure_ascii=False)[:300])

def sha_to_img(man):
    m = {}
    if isinstance(man, dict):
        # maybe {img: {sha256:...}} or {sha: img}
        for k, v in man.items():
            if isinstance(v, dict) and "sha256" in v:
                m[v["sha256"]] = k
            elif isinstance(v, str) and len(v) == 64:
                m[k] = v  # sha->img? unlikely
            elif isinstance(v, dict) and "img" in v:
                m[v.get("sha256") or v.get("sha") or ""] = v["img"]
    else:
        for item in man:
            img = item.get("img") or item.get("image") or item.get("path") or item.get("file")
            sha = item.get("sha256") or item.get("sha")
            if sha:
                m[sha] = img
    return m

s2i = sha_to_img(manifest)
print("sha2img entries:", len(s2i), "sample:", list(s2i.items())[:1])

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
print("cell files:", len(files))

cells = []
bad = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
        d["_file"] = os.path.basename(f)
        cells.append(d)
    except Exception as e:
        bad.append((os.path.basename(f), str(e)))
print("parsed:", len(cells), "bad:", bad)

if cells:
    keys = set()
    for c in cells: keys.update(c.keys())
    print("cell keys:", sorted(keys))
    print("sample cell:", json.dumps({k: cells[0][k] for k in list(cells[0])[:20]}, ensure_ascii=False)[:800])

# status distribution
from collections import Counter, defaultdict
stc = Counter(c.get("status") for c in cells)
print("STATUS:", dict(stc))

eng = defaultdict(Counter)
for c in cells:
    eng[c.get("engine")][c.get("status")] += 1
print("BY_ENGINE:")
for e, cc in sorted(eng.items(), key=lambda x: str(x[0])):
    print("  ", e, dict(cc))

# CER
cers = []
outliers = []
for c in cells:
    cer = c.get("cer_median")
    if cer is None:
        continue
    cers.append((cer, c))
normal = [(cer, c) for cer, c in cers if cer < 0.5]
vals = [cer for cer, c in normal]
if vals:
    print("CER normal n=%d median=%.4f" % (len(vals), statistics.median(vals)))
out = sorted([(cer, c) for cer, c in cers if cer >= 0.5], reverse=True)
print("CER outliers (>=0.5): %d" % len(out))
for cer, c in out:
    sha = c.get("input", {}).get("sha256") if isinstance(c.get("input"), dict) else c.get("input.sha256") or c.get("input_sha256")
    img = s2i.get(sha, "?")
    print("   cer=%.4f engine=%s sample=%s status=%s" % (cer, c.get("engine"), img, c.get("status")))

# wall
walls = [c.get("wall_median") for c in cells if isinstance(c.get("wall_median"), (int, float))]
if walls:
    print("WALL median=%.1fs n=%d min=%.1f max=%.1f" % (statistics.median(walls), len(walls), min(walls), max(walls)))

# timestamps for rate
ts_fields = ["started_at", "finished_at", "ts", "timestamp", "updated_at", "end_time", "start_time"]
tss = []
for c in cells:
    for f in ts_fields:
        if f in c:
            tss.append((f, c[f]))
print("timestamp fields sample:", tss[:6])
