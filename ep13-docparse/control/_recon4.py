# -*- coding: utf-8 -*-
"""Reconcile batch_state counts vs actual cell files. ASCII output only."""
import json, os, glob, random, datetime
from collections import Counter, defaultdict

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]

man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
img2sha = {s["img"]: s["sha256"] for s in man["samples"]}
tasks = [(s["img"], e) for s in man["samples"] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != "oxr"]
print("TOTAL_TASKS", len(tasks), "SAMPLES", len(man["samples"]))

have = {}
for p in glob.glob(os.path.join(CELLS, "*.json")):
    d = json.load(open(p, encoding="utf-8"))
    have[((d.get("input") or {}).get("sha256"), d.get("engine"))] = os.path.basename(p)

missing = [(img, eng) for img, eng in tasks if (img2sha[img], eng) not in have]
print("MISSING", len(missing))
byeng = defaultdict(list)
for img, eng in missing:
    byeng[eng].append(img)
for e in sorted(byeng):
    print("   ", e, len(byeng[e]), sorted(byeng[e]))

# engine totals in cells
cnt = Counter()
for (sha, eng) in have:
    cnt[eng] += 1
print("HAVE_BY_ENGINE", dict(sorted(cnt.items())))

# check runs dir for failure logs
for sub in ("runs", "outputs", "sessions"):
    d = os.path.join(ROOT, sub)
    if os.path.isdir(d):
        names = sorted(os.listdir(d))
        print(sub, "n=", len(names), names[-12:])

# any state/log file mentioning fail
for pat in ("control/*.json", "control/*.log", "*.log"):
    for p in sorted(glob.glob(os.path.join(ROOT, pat))):
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "fail" in txt.lower() and os.path.basename(p) not in ("batch_state.json", "task.json"):
            print("FAILISH", os.path.relpath(p, ROOT), len(txt))
