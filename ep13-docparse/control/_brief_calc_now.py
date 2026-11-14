# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
uuid2sample = {s["sample_uuid"]: s for s in man["samples"]}
sha2sample = {s["sha256"]: s for s in man["samples"]}

files = sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    inp = d.get("input")
    sha = inp.get("sha256") if isinstance(inp, dict) else inp
    uuid = os.path.basename(f).split("__")[0]
    samp = uuid2sample.get(uuid) or sha2sample.get(sha) or {}
    rows.append({
        "f": os.path.basename(f), "mt": os.path.getmtime(f),
        "uuid": uuid,
        "sample_id": d.get("sample_id") or samp.get("sample_id") or "?",
        "img": samp.get("img", "?"),
        "engine": d.get("engine"), "status": d.get("status"),
        "cer": d.get("cer_median"), "wall": d.get("wall_median"),
        "n_fail": d.get("n_fail"), "run_id": d.get("run_id"),
        "unstable": d.get("unstable"), "err": d.get("err"),
    })

print("TOTAL_CELLS:", len(rows))
print("RUN_IDS:", dict(collections.Counter(r["run_id"] for r in rows)))
print("STATUS:", dict(collections.Counter(r["status"] for r in rows)))

# expected coverage over manifest 26 samples x 6 engines
engines = sorted(set(r["engine"] for r in rows))
have = collections.defaultdict(set)
for r in rows:
    have[r["uuid"]].add(r["engine"])
missing = []
for u, s in uuid2sample.items():
    for e in engines:
        if e not in have[u]:
            missing.append((s["sample_id"], e))
print("ENGINES:", engines)
print("MISSING_CELLS:", len(missing), missing)
extra = [u for u in have if u not in uuid2sample]
print("EXTRA_UUIDS:", [(u, sorted(have[u])) for u in extra])
print("SAMPLES_COVERED:", sum(1 for u in uuid2sample if have[u]), "/", len(uuid2sample))

# outliers >= 0.5
outl = [r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5]
norm = [r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] < 0.5]
print("NORM_N:", len(norm), "CER_MEDIAN_NORMAL:", round(statistics.median([r["cer"] for r in norm]), 4))
print("OUTLIERS_N:", len(outl))
for r in sorted(outl, key=lambda x: -x["cer"]):
    print("   %.4f | %s | %s | %s | unstable=%s" % (r["cer"], r["engine"], r["sample_id"], r["img"], r["unstable"]))

walls = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
print("WALL_MEDIAN_S:", round(statistics.median(walls), 1), "n=", len(walls))
print("WALL_BY_ENGINE:")
for e in engines:
    w = [r["wall"] for r in rows if r["engine"] == e and isinstance(r["wall"], (int, float))]
    if w:
        print("   %s: %.1fs n=%d" % (e, statistics.median(w), len(w)))

# per-engine status
print("STATUS_BY_ENGINE:")
for e in engines:
    print("   %s: %s" % (e, dict(collections.Counter(r["status"] for r in rows if r["engine"] == e))))

# timing: cells modified today
today = [r for r in rows if datetime.datetime.fromtimestamp(r["mt"]).strftime("%Y-%m-%d") == "2026-11-07"]
print("CELLS_WRITTEN_TODAY:", len(today))
if today:
    lo = datetime.datetime.fromtimestamp(min(r["mt"] for r in today))
    hi = datetime.datetime.fromtimestamp(max(r["mt"] for r in today))
    span_min = (hi - lo).total_seconds() / 60
    print("TODAY_WINDOW:", lo.strftime("%H:%M"), "->", hi.strftime("%H:%M"), "span_min=%.1f" % span_min)
    if span_min > 0:
        print("RATE_MIN_PER_CELL: %.2f" % (span_min / len(today)))
# all cells window
lo = datetime.datetime.fromtimestamp(min(r["mt"] for r in rows))
hi = datetime.datetime.fromtimestamp(max(r["mt"] for r in rows))
print("ALL_WINDOW:", lo.strftime("%m-%d %H:%M"), "->", hi.strftime("%m-%d %H:%M"))

# remaining: 130 target? count complete vs 130
print("STALE_MIN: last cell -> now = %.1f" % ((datetime.datetime.now() - hi).total_seconds() / 60))

# cells with n_fail>0 or err
bad = [r for r in rows if (r["n_fail"] or 0) > 0 or r["err"]]
print("CELLS_WITH_ERR_OR_NFAIL:", len(bad))
for r in bad[:10]:
    print("   ", r["f"], r["n_fail"], str(r["err"])[:80])
