# -*- coding: utf-8 -*-
import json, os, glob, statistics, collections, datetime

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2id = {s["sha256"]: s["sample_id"] for s in man["samples"]}
ids = [s["sample_id"] for s in man["samples"]]

files = sorted(glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_file"] = f
    rows.append(d)

# show one row keys
print("KEYS:", sorted(rows[0].keys()))
print("SAMPLE ROW:", json.dumps({k: (v if not isinstance(v, str) or len(v) < 60 else v[:60]) for k, v in rows[0].items()}, ensure_ascii=False)[:1200])

# missing combos
engines = ["monkey_rec", "ovis_ocr2", "oxr", "paddleocr_vl", "surya_2_5", "xiaomi_vl"]
have = set()
for r in rows:
    sid = r.get("sample_id") or r.get("sample") or ""
    if not sid:
        # derive from filename uuid
        pass
    have.add((sid, r.get("engine")))
# derive sample_id via input sha
def sid_of(r):
    sha = None
    inp = r.get("input")
    if isinstance(inp, dict):
        sha = inp.get("sha256")
    sha = sha or r.get("input_sha256") or r.get("sha256")
    return sha2id.get(sha, None)

missing = []
for i in ids:
    for e in engines:
        if (i, e) not in have:
            missing.append((i, e))
print("MISSING combos (expect %d):" % len(missing))
for m in missing:
    print("   ", m)

# outliers with sample ids
print("OUTLIERS >=0.5:")
outl = []
for r in rows:
    c = r.get("cer_median")
    if isinstance(c, (int, float)) and c >= 0.5:
        outl.append((c, r.get("engine"), sid_of(r) or "?", r.get("status")))
for c, e, s, st in sorted(outl, key=lambda x: -x[0]):
    print("   %.3f | %s | %s | %s" % (c, e, s, st))

# CER median normal
cerc = [r["cer_median"] for r in rows if isinstance(r.get("cer_median"), (int, float))]
norm = [c for c in cerc if c < 0.5]
print("CER median normal n=%d: %.4f ; all n=%d median %.4f" % (len(norm), statistics.median(norm), len(cerc), statistics.median(cerc)))

# rate from mtimes
mts = sorted(os.path.getmtime(f) for f in files)
gaps = [(mts[i] - mts[i-1]) / 60 for i in range(1, len(mts))]
print("total cells:", len(mts))
if gaps:
    print("gap median all: %.2f min (n=%d)" % (statistics.median(gaps), len(gaps)))
    last = gaps[-20:]
    print("gap median last20: %.2f min" % statistics.median(last))
    last40 = gaps[-40:]
    print("gap median last40: %.2f min" % statistics.median(last40))
    print("first cell:", datetime.datetime.fromtimestamp(mts[0]), "last cell:", datetime.datetime.fromtimestamp(mts[-1]))
    span_h = (mts[-1] - mts[0]) / 3600
    print("span h: %.2f  avg min/cell: %.2f" % (span_h, (mts[-1]-mts[0])/60/(len(mts)-1)))

# state vs cells
st = json.load(open(os.path.join(base, "control", "batch_state.json"), encoding="utf-8"))
print("state:", st)
print("cells total=%d complete=%d failed=%d" % (
    len(rows),
    sum(1 for r in rows if r.get("status") == "complete"),
    sum(1 for r in rows if r.get("status") == "failed")))
# failed reasons
errs = collections.Counter()
for r in rows:
    if r.get("status") != "complete":
        errs[(r.get("engine"), (r.get("error") or r.get("message") or r.get("err") or "?")[:80])] += 1
for k, v in errs.items():
    print("FAIL:", k, v)

# wall per engine
byeng = collections.defaultdict(list)
for r in rows:
    w = r.get("wall_median")
    if isinstance(w, (int, float)):
        byeng[r.get("engine")].append(w)
for e in sorted(byeng, key=str):
    print("WALL %s: median %.1fs n=%d" % (e, statistics.median(byeng[e]), len(byeng[e])))
