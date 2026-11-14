import json, os, glob, datetime
base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
rows = []
for f in glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")):
    c = json.load(open(f, encoding="utf-8"))
    cer = c.get("cer_median")
    if isinstance(cer, (int, float)) and cer >= 0.5:
        sha = (c.get("input") or {}).get("sha256")
        rows.append((datetime.datetime.fromtimestamp(os.path.getmtime(f)),
                     c["engine"], sha2img.get(sha, "?"), round(cer, 3)))
rows.sort()
for r in rows:
    print(r[0].strftime("%m-%d %H:%M"), r[1], r[2], r[3])
print("n=", len(rows))
