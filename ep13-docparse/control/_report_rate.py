import json, os, glob, datetime, statistics
base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
uuid2img = {s["sample_uuid"]: s["img"] for s in man["samples"]}
files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
oxr = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    if d.get("engine") != "oxr":
        continue
    oxr.append((datetime.datetime.fromtimestamp(os.path.getmtime(f)),
                uuid2img.get(d.get("sample_id"), "?"),
                d.get("wall_median"), d.get("cer_median"), d.get("n_valid"), d.get("n_attempt")))
oxr.sort()
print("OXR_N:", len(oxr))
for t, img, w, c, nv, na in oxr[-6:]:
    print("  ", t.strftime("%m-%d %H:%M:%S"), img, "wall_med=%s cer=%s valid=%s att=%s" % (w, c, nv, na))
gaps = [(oxr[i][0] - oxr[i-1][0]).total_seconds()/60.0 for i in range(1, len(oxr))]
print("OXR_GAP_MIN n=%d median=%.1f mean=%.1f min=%.1f max=%.1f" % (len(gaps), statistics.median(gaps), sum(gaps)/len(gaps), min(gaps), max(gaps)))
last6 = gaps[-6:]
print("OXR_GAP_LAST6:", [round(g,1) for g in last6], "median=", round(statistics.median(last6),1))
walls = [w for _, _, w, _, _, _ in oxr if isinstance(w, (int, float))]
print("OXR_WALL_MEDIAN:", round(statistics.median(walls),1))
# recent 3 gaps (after 11-07 morning)
recent = [(t, img) for t, img, _, _, _, _ in oxr if t >= datetime.datetime(2026,11,7,5,0)]
print("OXR_TODAY_N:", len(recent))
g2 = [(recent[i][0]-recent[i-1][0]).total_seconds()/60 for i in range(1,len(recent))]
if g2:
    print("OXR_TODAY_GAPS:", [round(x,1) for x in g2], "median=", round(statistics.median(g2),1))
