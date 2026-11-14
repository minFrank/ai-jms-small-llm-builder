import json, os, glob, statistics, collections, datetime as dt

BASE = r"D:/study/ai-jms/ep13-docparse"
cells_dir = os.path.join(BASE, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(cells_dir, "*.json")))

with open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8") as fh:
    man = json.load(fh)

sha2img, sid2img, uu2img = {}, {}, {}
for s in man["samples"]:
    sha2img[s["sha256"]] = s["img"]
    sid2img[s["sample_id"]] = s["img"]
    uu2img[s.get("sample_uuid")] = s["img"]

fmt = "%Y-%m-%dT%H:%M:%S"
cells = []
for f in files:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    sha = (d.get("input") or {}).get("sha256")
    sid = d.get("sample_id")
    img = sha2img.get(sha) or sid2img.get(sid) or uu2img.get(sid) or ("UUID:" + str(sid))
    last_ts = max((r["ts"] for r in d.get("reps") or [] if r.get("ts")), default=None)
    first_ts = min((r["ts"] for r in d.get("reps") or [] if r.get("ts")), default=None)
    cells.append({
        "engine": d.get("engine"), "img": img, "status": d.get("status"),
        "cer": d.get("cer_median"), "wall": d.get("wall_median"),
        "last": last_ts, "first": first_ts, "cell": d.get("cell_key"),
        "n_fail": d.get("n_fail") or 0, "n_attempt": d.get("n_attempt"),
    })

# completion timeline
cells_sorted = sorted([c for c in cells if c["last"]], key=lambda c: c["last"])
ts = [dt.datetime.strptime(c["last"], fmt) for c in cells_sorted]
gaps = [(ts[i] - ts[i - 1]).total_seconds() / 60.0 for i in range(1, len(ts))]
active = [g for g in gaps if 0 < g <= 180]
print("n_cells_with_ts", len(ts), "span", ts[0], "->", ts[-1])
print("gaps_all_median=%.1f  gaps_active(<=180min) n=%d median=%.2f mean=%.2f" % (
    statistics.median(gaps), len(active),
    statistics.median(active) if active else -1,
    statistics.mean(active) if active else -1))

# completions per rolling hour in the last 24h of the run
last24 = [t for t in ts if (ts[-1] - t).total_seconds() <= 24 * 3600]
print("cells_completed_in_final_24h", len(last24),
      "=> min/cell (final 24h)", round(24 * 60 / len(last24), 2) if last24 else "-")

# per-cell elapsed = last - first (its own run time)
el = [(dt.datetime.strptime(c["last"], fmt) - dt.datetime.strptime(c["first"], fmt)).total_seconds() / 60
      for c in cells if c["first"] and c["last"] and c["last"] >= c["first"]]
print("per_cell_first_to_last_median_min", round(statistics.median(el), 1))

# outlier list with img
out = [c for c in cells if isinstance(c["cer"], (int, float)) and c["cer"] >= 0.5]
out.sort(key=lambda c: -c["cer"])
print("OUTLIERS n=%d" % len(out))
for c in out:
    print("   %.4f | %-14s | %-16s | %s" % (c["cer"], c["engine"], c["img"], c["cell"]))

# outliers by engine
print("outliers_by_engine", dict(collections.Counter(c["engine"] for c in out)))
norm = [c["cer"] for c in cells if isinstance(c["cer"], (int, float)) and c["cer"] < 0.5]
print("normal_n", len(norm), "median", round(statistics.median(sorted(norm)), 4))
print("walls_median", round(statistics.median([c["wall"] for c in cells if isinstance(c["wall"], (int, float))]), 2))
print("n_fail_cells", [(c["cell"], c["n_fail"], c["n_attempt"]) for c in cells if c["n_fail"]])
print("status_all", dict(collections.Counter(c["status"] for c in cells)))
# per engine status
per = collections.defaultdict(collections.Counter)
for c in cells:
    per[c["engine"]][c["status"]] += 1
for e in sorted(per):
    eng_out = [c for c in out if c["engine"] == e]
    eng_norm = [c["cer"] for c in cells if c["engine"] == e and isinstance(c["cer"], (int, float)) and c["cer"] < 0.5]
    print("  %-14s %s outlier=%d med_norm=%s wall_med=%s" % (
        e, dict(per[e]), len(eng_out),
        round(statistics.median(eng_norm), 4) if eng_norm else "-",
        round(statistics.median([c["wall"] for c in cells if c["engine"] == e]), 1)))
