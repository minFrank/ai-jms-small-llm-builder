import json, os, glob, datetime, collections, statistics
base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
sha2img, uuid2img = {}, {}
for s in man["samples"]:
    sha2img[s["sha256"]] = s["img"]
    uuid2img[s["sample_uuid"]] = s["img"]
print("MAP:", len(sha2img), len(uuid2img))

files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    inp = d.get("input") or {}
    sha = inp.get("sha256") if isinstance(inp, dict) else inp
    rows.append({
        "file": os.path.basename(f),
        "img": uuid2img.get(d.get("sample_id"), sha2img.get(sha, d.get("sample_id"))),
        "sample_id": d.get("sample_id"),
        "engine": d.get("engine"),
        "status": d.get("status"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)),
        "sha": sha,
    })

print("TOTAL:", len(rows))
started = datetime.datetime.fromisoformat("2026-11-07T17:01:40")
print("MTIME >= start:", sum(1 for r in rows if r["mtime"] >= started))

# mtime range per engine
for e in sorted(set(r["engine"] for r in rows)):
    ms = sorted(r["mtime"] for r in rows if r["engine"] == e)
    print("ENG %-13s n=%d  mtime %s .. %s" % (e, len(ms), ms[0].strftime("%m-%d %H:%M"), ms[-1].strftime("%m-%d %H:%M")))

# last 12 newest cells
print("-- newest 12 --")
for r in sorted(rows, key=lambda x: -x["mtime"].timestamp())[:12]:
    print("  ", r["mtime"].strftime("%m-%d %H:%M:%S"), r["engine"], r["img"], "cer=%.4f" % (r["cer"] or -1))

# outliers with img
out = [r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5]
print("OUTLIERS:", len(out))
for r in sorted(out, key=lambda x: -x["cer"]):
    print("  %.4f | %s | %s | %s" % (r["cer"], r["engine"], r["img"], r["mtime"].strftime("%m-%d %H:%M")))

norm = [r["cer"] for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] < 0.5]
print("NORMAL_N:", len(norm), "MEDIAN:", round(statistics.median(norm), 4))
walls = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
print("WALL_MEDIAN:", round(statistics.median(walls), 2), "n=", len(walls))

# per engine cer median
for e in sorted(set(r["engine"] for r in rows)):
    cs = [r["cer"] for r in rows if r["engine"] == e and isinstance(r["cer"], (int, float))]
    nrm = [c for c in cs if c < 0.5]
    print("CER %-13s n=%d med_all=%.4f med_normal=%s out=%d" % (e, len(cs), statistics.median(cs),
          round(statistics.median(nrm), 4) if nrm else None, sum(1 for c in cs if c >= 0.5)))

# cells per sample / missing
per_sample = collections.Counter(r["img"] for r in rows)
print("SAMPLES:", len(per_sample), "DIST:", dict(collections.Counter(per_sample.values())))
allimg = [s["img"] for s in man["samples"]]
for e in sorted(set(r["engine"] for r in rows)):
    got = set(r["img"] for r in rows if r["engine"] == e)
    miss = [i for i in allimg if i not in got]
    if miss:
        print("MISSING", e, miss)

# newest mtime overall vs now
print("NEWEST_CELL:", max(r["mtime"] for r in rows).strftime("%F %T"))
