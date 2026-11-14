import json, glob, os, collections, hashlib, datetime

BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
by_sha = {s["sha256"]: s for s in man["samples"]}
by_uuid = {s["sample_uuid"]: s for s in man["samples"]}
by_img = {s["img"]: s for s in man["samples"]}

rows = []
for f in sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    d["_f"] = os.path.basename(f)
    rows.append(d)

# orphan cell sha
orph = [r for r in rows if r["_f"].split("__")[0] not in by_uuid]
for r in orph:
    sha = r.get("input", {}).get("sha256")
    hit = by_sha.get(sha)
    print("ORPHAN", r["_f"], "sha=", sha[:16] if sha else None, "-> manifest:", hit["img"] if hit else "NO MATCH", hit["sample_uuid"] if hit else "")

# does that manifest sample have its own cells?
if orph:
    sha = orph[0].get("input", {}).get("sha256")
    hit = by_sha.get(sha)
    if hit:
        u = hit["sample_uuid"]
        cs = [r["_f"] for r in rows if r["_f"].startswith(u)]
        print("manifest sample", hit["img"], u, "cells:", len(cs), cs)

# d9412c21 cells sha
d_uid = "d9412c21-d612-4abf-a529-a2f5ac11929e"
cs = [r for r in rows if r["_f"].startswith(d_uid)]
for r in cs:
    sha = r.get("input", {}).get("sha256")
    hit = by_sha.get(sha)
    print("D9412", r["_f"], "sha->", hit["img"] if hit else "NOT IN MANIFEST")
print("d9412c21 in manifest?", d_uid in by_uuid, by_uuid.get(d_uid, {}).get("img"))

# expected matrix by manifest sha x engine (5 engines present)
ENGS = sorted(set(r.get("engine") for r in rows))
have = set()
for r in rows:
    sha = r.get("input", {}).get("sha256")
    have.add((sha, r.get("engine")))
missing = []
for s in man["samples"]:
    for e in ENGS:
        if (s["sha256"], e) not in have:
            missing.append((s["img"], e))
print("engines:", ENGS, "expected:", len(man["samples"])*len(ENGS), "covered by sha:", len(have))
print("MISSING (by sha):", missing)

# oxr cells anywhere?
oxr = glob.glob(os.path.join(BASE, "cells/*/*oxr*.json"))
print("oxr cells:", len(oxr), oxr[:5])

# failed cells: n_attempt / err
print("=== failed ===")
for r in rows:
    if r.get("status") != "complete":
        print("  ", r["_f"], r.get("status"), "err=", r.get("err"), "n_valid=", r.get("n_valid"), "attempt=", r.get("n_attempt"), "unstable=", r.get("unstable"))

# unstable / success rate <1 among complete
print("=== complete with unstable or success<1 ===")
for r in rows:
    if r.get("status") == "complete" and (r.get("unstable") or (isinstance(r.get("cell_success_rate"), (int, float)) and r["cell_success_rate"] < 1)):
        print("  ", r["_f"], "sr=", r.get("cell_success_rate"), "unstable=", r.get("unstable"), "n_valid=", r.get("n_valid"), "/", r.get("target_valid"), "attempt=", r.get("n_attempt"))

# recent rate: cells written in last 24h /48h
import time
mts = sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
now = time.time()
for h in (6, 12, 24, 48):
    n = sum(1 for t in mts if now - t < h*3600)
    print(f"cells written last {h}h: {n}")

# gaps between last 30 writes
last30 = mts[-30:]
gaps = [(last30[i+1]-last30[i])/60 for i in range(len(last30)-1)]
gaps_s = sorted(gaps)
print("last30 gap min: median=%.1f p90=%.1f max=%.1f" % (gaps_s[len(gaps_s)//2], gaps_s[int(len(gaps_s)*0.9)], gaps_s[-1]))
