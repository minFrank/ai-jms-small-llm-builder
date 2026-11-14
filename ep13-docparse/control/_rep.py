import json, os, statistics, glob, datetime

base = r"D:/study/ai-jms/ep13-docparse"
cell_dir = os.path.join(base, "cells", "ep13-full-001")
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
# sha256 -> img map
sha2img = {}
if isinstance(man, dict):
    for k, v in man.items():
        if isinstance(v, str) and v.endswith((".png", ".jpg", ".jpeg")):
            sha2img[k] = v
        elif isinstance(v, dict):
            s = v.get("sha256"); i = v.get("img") or v.get("path") or v.get("file")
            if s: sha2img[s] = i or "?"
elif isinstance(man, list):
    for v in man:
        s = v.get("sha256"); i = v.get("img") or v.get("path") or v.get("file")
        if s: sha2img[s] = i or "?"

files = sorted(glob.glob(os.path.join(cell_dir, "*.json")))
now = datetime.datetime.now()
recs = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        recs.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    sha = d.get("input", {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("input_sha256")
    recs.append({
        "name": os.path.basename(f),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": sha,
        "img": sha2img.get(sha, "?"),
        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)),
    })

print("TOTAL_CELLS", len(files))
from collections import Counter
print("STATUS", dict(Counter(str(r["status"]) for r in recs)))
print("STATUS_ENGINE")
for k, v in sorted(Counter((str(r["engine"]), str(r["status"])) for r in recs).items()):
    print("  ", k, v)

# wall-mtime ordering for rate
mt = sorted([r["mtime"] for r in recs if r["mtime"]])
print("MTIME_MIN", mt[0], "MTIME_MAX", mt[-1])

cers = [r["cer"] for r in recs if isinstance(r["cer"], (int, float))]
normal = [c for c in cers if c < 0.5]
print("CER_COUNT", len(cers), "NORMAL", len(normal))
if normal:
    print("CER_MED_NORMAL", round(statistics.median(normal), 4))
if cers:
    print("CER_MED_ALL", round(statistics.median(cers), 4))

outliers = [r for r in recs if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5]
outliers.sort(key=lambda r: -r["cer"])
print("OUTLIERS", len(outliers))
for r in outliers:
    print("   %.4f | %s | %s | %s" % (r["cer"], r["engine"], r["name"], r["img"]))

walls = [r["wall"] for r in recs if isinstance(r["wall"], (int, float))]
if walls:
    print("WALL_MED", round(statistics.median(walls), 3), "WALL_N", len(walls))

nonc = [r for r in recs if r["status"] != "complete"]
print("NON_COMPLETE", len(nonc))
for r in nonc[:20]:
    print("   ", r["name"], r["status"], r["engine"], r["cer"])

# recent cells by mtime for rate
recent = sorted(recs, key=lambda r: r["mtime"])[-15:]
print("RECENT15")
for r in recent:
    print("   ", r["mtime"], r["name"], r["status"], r["engine"], r["cer"], r["wall"])
