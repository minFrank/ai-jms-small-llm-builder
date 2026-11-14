import json, os, glob, statistics, datetime

BASE = r"D:/study/ai-jms/ep13-docparse"
st = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
print("STATE", json.dumps(st, ensure_ascii=False))

cell_dir = os.path.join(BASE, "cells", st.get("run_id", "ep13-full-001"))
files = sorted(glob.glob(os.path.join(cell_dir, "*.json")))
print("NFILES", len(files))

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    rows.append({
        "file": os.path.basename(f),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "sample": d.get("sample") or d.get("img") or d.get("input_sample"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": (d.get("input") or {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("input_sha256") or (d.get("input") or {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("sha256"),
        "keys": list(d.keys()),
    })

# status distribution
from collections import Counter, defaultdict
print("STATUS", Counter(str(r["status"]) for r in rows))
eng = defaultdict(Counter)
for r in rows:
    eng[str(r["engine"])][str(r["status"])] += 1
for k, v in sorted(eng.items()):
    print("ENGINE", k, dict(v))

# show one sample record's keys
if rows:
    print("SAMPLE_KEYS", rows[0]["keys"])
    print("SAMPLE_REC", json.dumps({k: v for k, v in rows[0].items() if k != "keys"}, ensure_ascii=False)[:800])

# sha -> img map
man_path = os.path.join(BASE, "samples", "manifest.json")
sha2img = {}
if os.path.exists(man_path):
    man = json.load(open(man_path, encoding="utf-8"))
    def walk(o):
        if isinstance(o, dict):
            if "sha256" in o and ("img" in o or "file" in o or "name" in o):
                sha2img[o["sha256"]] = o.get("img") or o.get("file") or o.get("name")
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(man)
    if isinstance(man, dict) and not sha2img:
        # maybe direct mapping
        for k, v in man.items():
            if isinstance(k, str) and len(k) == 64:
                sha2img[k] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)[:100]
    print("MANIFEST_TOP", type(man), (list(man.keys())[:5] if isinstance(man, dict) else len(man)))
print("SHA2IMG_N", len(sha2img))

def imgname(r):
    sha = r.get("sha")
    if sha and sha in sha2img:
        return sha2img[sha]
    return r.get("sample") or r.get("file")

complete = [r for r in rows if r["status"] == "complete"]
others = [r for r in rows if r["status"] != "complete"]
print("NON_COMPLETE_N", len(others))
for r in others:
    print("  NON_COMPLETE", r["file"], r["status"], r.get("engine"), r.get("cer"), imgname(r))

cers = [(r, r["cer"]) for r in complete if isinstance(r.get("cer"), (int, float))]
norm = [(r, c) for r, c in cers if c < 0.5]
outl = [(r, c) for r, c in cers if c >= 0.5]
if norm:
    print("CER_MEDIAN_NORMAL", round(statistics.median([c for _, c in norm]), 4), "N", len(norm))
if outl:
    for r, c in sorted(outl, key=lambda x: -x[1]):
        print("OUTLIER", round(c, 4), r.get("engine"), imgname(r), r.get("wall"))

walls = [r["wall"] for r in complete if isinstance(r.get("wall"), (int, float))]
if walls:
    print("WALL_MEDIAN", round(statistics.median(walls), 1), "N", len(walls))

# per engine median
per_eng = defaultdict(list)
for r in complete:
    if isinstance(r.get("cer"), (int, float)):
        per_eng[r.get("engine")].append(r["cer"])
for k, v in sorted(per_eng.items()):
    print("CER_BY_ENGINE", k, round(statistics.median(v), 4), "N", len(v))

# progress rates from mtime
now = datetime.datetime.now()
print("NOW", now.isoformat(timespec="seconds"))
mtimes = [(os.path.getmtime(f), os.path.basename(f)) for f in files]
mtimes.sort()
print("LAST_MTIME", datetime.datetime.fromtimestamp(mtimes[-1][0]).isoformat(timespec="seconds"), mtimes[-1][1])
print("FIRST_MTIME", datetime.datetime.fromtimestamp(mtimes[0][0]).isoformat(timespec="seconds"), mtimes[0][1])
