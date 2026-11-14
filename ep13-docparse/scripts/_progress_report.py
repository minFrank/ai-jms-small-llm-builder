import json, glob, os, statistics, hashlib, datetime

ROOT = r"D:/study/ai-jms/ep13-docparse"
cells = sorted(glob.glob(os.path.join(ROOT, "cells/ep13-full-001/*.json")))

man = json.load(open(os.path.join(ROOT, "samples/manifest.json"), encoding="utf-8"))
# sha256 -> img mapping; manifest may be list or dict
sha2img = {}
if isinstance(man, dict):
    for k, v in man.items():
        if isinstance(v, dict):
            sha2img[k] = v.get("img") or v.get("name") or str(v)
        else:
            sha2img[k] = v
elif isinstance(man, list):
    for v in man:
        sha2img[v.get("sha256")] = v.get("img") or v.get("name")

rows = []
for f in cells:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    rows.append({
        "file": os.path.basename(f),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": d.get("input", {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("input_sha256"),
    })

print("TOTAL_CELLS", len(rows))
from collections import Counter
print("STATUS", dict(Counter(r["status"] for r in rows)))
print("ENGINE", dict(Counter(r["engine"] for r in rows)))
print("STATUSxENGINE", dict(Counter((r["engine"], r["status"]) for r in rows)))

# per engine distribution of status
byeng = {}
for r in rows:
    byeng.setdefault(r["engine"], Counter())[r["status"]] += 1
for e, c in sorted(byeng.items()):
    print("ENG", e, dict(c))

# rates: use file mtime as completion time
mtimes = sorted(os.path.getmtime(f) for f in cells)
now = datetime.datetime.now().timestamp()
print("N_MTIMES", len(mtimes))
if mtimes:
    print("OLDEST_CELL", datetime.datetime.fromtimestamp(mtimes[0]).isoformat())
    print("NEWEST_CELL", datetime.datetime.fromtimestamp(mtimes[-1]).isoformat())

# CER stats on complete cells with cer<0.5
cers_ok = [r["cer"] for r in rows if r["status"] == "complete" and isinstance(r["cer"], (int, float)) and r["cer"] < 0.5]
print("CER_OK_N", len(cers_ok), "MEDIAN", statistics.median(cers_ok) if cers_ok else None)

# outliers
known = {("xiaomi_vl", "shot_01"), ("xiaomi_vl", "table_01")}
outs = []
for r in rows:
    if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5:
        img = sha2img.get(r["sha"], "?")
        outs.append((round(r["cer"], 3), r["engine"], img, r["status"]))
outs.sort(reverse=True)
print("OUTLIERS")
for o in outs:
    print("  ", o, "KNOWN" if (o[1], o[2]) in known or ("shot_01" in str(o[2]) or "table_01" in str(o[2])) and o[1] == "xiaomi_vl" else "NEW")

# wall median on complete
walls = [r["wall"] for r in rows if r["status"] == "complete" and isinstance(r["wall"], (int, float))]
print("WALL_N", len(walls), "MEDIAN", statistics.median(walls) if walls else None)
print("WALL_MEDIAN_MIN", round(statistics.median(walls)/60, 2) if walls else None)

# non-complete detail
nc = [r for r in rows if r["status"] != "complete"]
print("NON_COMPLETE_N", len(nc))
for r in nc[:40]:
    print("  NC", r["file"], r["status"], r["engine"], r["cer"])

# rate from mtimes over last window
if len(mtimes) >= 2:
    span = (mtimes[-1] - mtimes[0]) / 60.0
    print("SPAN_MIN_ALL", round(span, 1), "PER_CELL", round(span/len(mtimes), 2) if mtimes else None)
    # last 20 cells
    if len(mtimes) >= 21:
        s20 = (mtimes[-1] - mtimes[-21]) / 60.0
        print("LAST20_SPAN_MIN", round(s20, 1), "PER_CELL", round(s20/20, 2))
