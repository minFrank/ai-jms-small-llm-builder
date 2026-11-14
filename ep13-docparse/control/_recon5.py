# -*- coding: utf-8 -*-
"""Check cell/task mismatch details. ASCII output only."""
import json, os, glob, random
from collections import Counter

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]

man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
img2sha = {s["img"]: s["sha256"] for s in man["samples"]}
tasks = [(s["img"], e) for s in man["samples"] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != "oxr"]
task_keys = {(img2sha[img], eng) for img, eng in tasks}

cells = []
for p in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    sha = (d.get("input") or {}).get("sha256")
    cells.append((os.path.basename(p), sha, d.get("engine"), d.get("status"),
                  sha in img2sha.values()))

print("cells", len(cells))
dups = [k for k, v in Counter((s, e) for _, s, e, _, _ in cells).items() if v > 1]
print("dup (sha,eng) in cells:", dups)
orphan = [f for f, s, e, st, known in cells if (s, e) not in task_keys]
print("cells not matching any task:", len(orphan), orphan[:10])
unknown_sha = [(f, s) for f, s, e, st, known in cells if not known]
print("cells with sha not in manifest:", unknown_sha[:10])

have = {(s, e) for _, s, e, _, _ in cells}
missing = [(img, eng) for img, eng in tasks if (img2sha[img], eng) not in have]
print("missing tasks", len(missing))
byeng = Counter(e for _, e in missing)
print("missing by engine", dict(byeng))
# are missing cells 'failures' per state? state n_fail=23
print("state n_fail=23 vs missing", len(missing))

# check per-engine completeness vs sets.yaml reference (25 per engine)
for e in ENGINES:
    n = sum(1 for _, s, ee, _, _ in cells if ee == e)
    print("engine", e, "cells", n, "/26")
