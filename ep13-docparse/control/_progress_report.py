import json, glob, os, statistics, collections, datetime

base = r"D:/study/ai-jms/ep13-docparse"
cells = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
uuid2img = {s["sample_uuid"]: s["img"] for s in man["samples"]}

rows = []
for p in cells:
    d = json.load(open(p, encoding="utf-8"))
    sha = d.get("input", {}).get("sha256")
    img = sha2img.get(sha, uuid2img.get(d.get("sample_id"), d.get("sample_id")))
    reps = d.get("reps") or []
    ts = [r.get("ts") for r in reps if r.get("ts")]
    rows.append(dict(cell=d.get("cell_key"), eng=d.get("engine"), st=d.get("status"),
                     cer=d.get("cer_median"), wall=d.get("wall_median"), img=img,
                     first=min(ts) if ts else None, last=max(ts) if ts else None))

print("n", len(rows), "all_complete", all(r["st"] == "complete" for r in rows))
alls = sorted(r["first"] for r in rows if r["first"])
alle = sorted(r["last"] for r in rows if r["last"])
print("RUN_FIRST_TS", alls[0], "RUN_LAST_TS", alle[-1])
t0 = datetime.datetime.fromisoformat(alls[0]); t1 = datetime.datetime.fromisoformat(alle[-1])
span_min = (t1 - t0).total_seconds() / 60
print("SPAN_MIN", round(span_min, 1), "per_cell_min", round(span_min / len(rows), 2))
# completion order gaps
gaps = [(datetime.datetime.fromisoformat(alle[i]) - datetime.datetime.fromisoformat(alle[i-1])).total_seconds()/60 for i in range(1, len(alle))]
print("GAP_MEDIAN_MIN", round(statistics.median(gaps), 2), "GAP_MEAN_MIN", round(statistics.mean(gaps), 2))

cers = [r["cer"] for r in rows if isinstance(r["cer"], (int, float))]
normal = [c for c in cers if c < 0.5]
print("CER_MED_NORMAL", round(statistics.median(normal), 4), "n_normal", len(normal), "n_cer", len(cers))
out = sorted([r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5], key=lambda r: -r["cer"])
print("OUTLIERS n", len(out))
for r in out:
    print("  OUT", round(r["cer"], 3), r["eng"], r["img"])
walls = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
print("WALL_MEDIAN", round(statistics.median(walls), 1), "WALL_MEAN", round(statistics.mean(walls), 1))
# per engine cer median
by = collections.defaultdict(list)
for r in rows:
    if isinstance(r["cer"], (int, float)):
        by[r["eng"]].append(r["cer"])
for e in sorted(by):
    print("CER_MED_BY_ENGINE", e, round(statistics.median(by[e]), 4), "n", len(by[e]))
