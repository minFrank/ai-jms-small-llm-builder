# -*- coding: utf-8 -*-
import json, os, glob, sys, io, collections, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
samples = man["samples"]
shas = [s["sha256"] for s in samples]
print("samples:", len(samples), "unique sha:", len(set(shas)))
dups = [k for k, v in collections.Counter(shas).items() if v > 1]
print("dup shas:", [(k[:12], [s["img"] for s in samples if s["sha256"] == k]) for k in dups])
uuids = [s.get("sample_uuid") for s in samples]
print("unique uuid:", len(set(uuids)))

files = glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json"))
pairs = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    pairs.append(((d.get("input") or {}).get("sha256"), d.get("engine"), os.path.basename(f)))
c = collections.Counter((a, b) for a, b, _ in pairs)
print("files:", len(files), "unique pairs:", len(c))
print("dup pairs:", [(k[0][:12], k[1], v) for k, v in c.items() if v > 1])
# files with same sample+engine diff name?
byse = collections.Counter()
print("statuses:", collections.Counter(json.load(open(f, encoding='utf-8')).get('status') for f in files))

# check gap: run+skip vs present tasks
present_tasks = set()
alltasks = set()
for s in samples:
    for e in ["paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]:
        alltasks.add((s["sha256"], e))
        if (s["sha256"], e) in c:
            present_tasks.add((s["sha256"], e))
print("alltasks:", len(alltasks), "present:", len(present_tasks), "missing:", len(alltasks - present_tasks))

# outlier mtimes
uuid2img = {s["sample_uuid"]: s["img"] for s in samples}
sha2img = {s["sha256"]: s["img"] for s in samples}
outs = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    cer = d.get("cer_median")
    if isinstance(cer, (int, float)) and cer >= 0.5:
        img = uuid2img.get(d.get("sample_id")) or sha2img.get((d.get("input") or {}).get("sha256"), "?")
        outs.append((cer, d.get("engine"), img, datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%m-%d %H:%M")))
outs.sort(reverse=True)
print("\noutlier mtimes:")
for o in outs:
    print("  %.4f %s %s %s" % o)

# engine gaps detail
eng_done = collections.Counter()
for (sha, e), v in c.items():
    eng_done[e] += v
print("\nper-engine done:", dict(eng_done))
