import json, glob, os, datetime, collections
EP = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(EP, "samples/manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
rows = []
for p in sorted(glob.glob(os.path.join(EP, "cells/ep13-full-001/*.json"))):
    c = json.load(open(p, encoding="utf-8"))
    sha = c.get("input", {}).get("sha256")
    if sha not in sha2img:
        continue
    img = sha2img[sha]
    cer = c.get("cer_median")
    if isinstance(cer, (int, float)) and cer >= 0.5:
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        rows.append((cer, c.get("engine"), img, mt.strftime("%m-%d %H:%M")))
rows.sort(reverse=True)
for r in rows:
    print("%.3f  %-13s %-14s %s" % r)
print("n_outlier=", len(rows))
# batch start
BATCH = datetime.datetime(2026, 11, 7, 5, 42, 6)
print("in_current_batch=", sum(1 for r in rows if datetime.datetime.strptime("2026-" + r[3], "%Y-%m-%d %H:%M") >= BATCH))
