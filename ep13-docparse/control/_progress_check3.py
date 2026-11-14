# -*- coding: utf-8 -*-
import json, os, glob, statistics, sys, io, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:/study/ai-jms/ep13-docparse"
RUN  = "ep13-full-001"
CELLS = os.path.join(BASE, "cells", RUN)
man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
samples = man["samples"]
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]

# sha -> img
sha2img = {s["sha256"]: s["img"] for s in samples}
uuid2img = {s["sample_uuid"]: s["img"] for s in samples}

files = glob.glob(os.path.join(CELLS, "*.json"))
cells = [json.load(open(f, encoding="utf-8")) for f in files]

done_sha_eng = set()
for c in cells:
    done_sha_eng.add((c.get("input", {}).get("sha256"), c.get("engine")))

# tasks: 26 samples x engines present (oxr excluded -> confirm)
present_engines = sorted({c.get("engine") for c in cells})
print("engines in cells:", present_engines)

tasks = [(s["sha256"], s["img"], e) for s in samples for e in present_engines]
print("task total:", len(tasks), "samples:", len(samples))
missing = [(img, e) for sha, img, e in tasks if (sha, e) not in done_sha_eng]
print("missing cell files:", len(missing))
from collections import Counter
print("missing by engine:", dict(Counter(e for _, e in missing)))
print("missing list:")
for img, e in sorted(missing, key=lambda x: (x[1], x[0])):
    print("   %s x %s" % (img, e))

# files whose engine/sample not matching any task? extras
extra = [c for c in cells if (c.get("input", {}).get("sha256"), c.get("engine")) not in {(s["sha256"], e) for s in samples for e in present_engines}]
print("extra/unmatched cells:", len(extra))

# status dist per engine
per = {}
for c in cells:
    per.setdefault(c.get("engine"), Counter())[c.get("status")] += 1
print("\nstatus by engine:")
for e in sorted(per):
    print("  ", e, dict(per[e]), "total", sum(per[e].values()))

# CER
norm = []
outl = []
for c in cells:
    cer = c.get("cer_median")
    if cer is None: continue
    img = uuid2img.get(c.get("sample_id"), sha2img.get(c.get("input", {}).get("sha256"), c.get("sample_id")))
    if cer < 0.5: norm.append(cer)
    else: outl.append((cer, c.get("engine"), img))
print("\nCER normal n=%d median=%.4f" % (len(norm), statistics.median(norm)))
outl.sort(reverse=True)
print("CER>=0.5 count:", len(outl))
known = {("xiaomi_vl", "shot_01"), ("xiaomi_vl", "table_01")}
for cer, e, img in outl:
    tag = "KNOWN" if (e, img) in known else "NEW?"
    print("   %.4f %s %s [%s]" % (cer, e, img, tag))

# wall
walls = [c.get("wall_median") for c in cells if isinstance(c.get("wall_median"), (int, float))]
print("\nwall median=%.1fs n=%d p10=%.1f p90=%.1f max=%.1f" % (
    statistics.median(walls), len(walls),
    sorted(walls)[len(walls)//10], sorted(walls)[len(walls)*9//10], max(walls)))

# unstable / cell_success_rate
uns = [c for c in cells if c.get("unstable")]
print("unstable cells:", len(uns))
low = [(c.get("cell_success_rate"), uuid2img.get(c.get("sample_id"), c.get("sample_id")), c.get("engine")) for c in cells if (c.get("cell_success_rate") or 1) < 1.0]
low.sort()
print("cell_success_rate<1:", len(low))
for r, img, e in low[:15]:
    print("   %.3f %s x %s" % (r, img, e))

# mtime rate for last batch
mt = sorted(os.path.getmtime(os.path.join(CELLS, f)) for f in os.listdir(CELLS) if f.endswith(".json"))
def mins(a, b): return (b-a)/60.0
print("\nlast cell mtime:", datetime.datetime.fromtimestamp(mt[-1]).isoformat())
print("rate last10: %.2f min/cell" % (mins(mt[-11], mt[-1])/10))
print("rate last30: %.2f min/cell" % (mins(mt[-31], mt[-1])/30))
print("rate all106: %.2f min/cell" % (mins(mt[0], mt[-1])/len(mt)))
