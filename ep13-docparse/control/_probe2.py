import json, glob, os, statistics, collections, datetime

BASE = "D:/study/ai-jms/ep13-docparse"
man = json.load(open(BASE + "/samples/manifest.json", encoding="utf-8"))["samples"]
img_by_uuid = {s["sample_uuid"]: s["img"] for s in man}
img_by_sha = {s["sha256"]: s["img"] for s in man}

cells = sorted(glob.glob(BASE + "/cells/ep13-full-001/*.json"))
rows = []
for p in cells:
    d = json.load(open(p, encoding="utf-8"))
    d["_f"] = os.path.basename(p)
    d["_mt"] = datetime.datetime.fromtimestamp(os.path.getmtime(p))
    d["_img"] = img_by_sha.get(d.get("input", {}).get("sha256")) or img_by_uuid.get(d.get("sample_id")) or d.get("sample_id")
    rows.append(d)

# outliers
out = [r for r in rows if isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] >= 0.5]
out.sort(key=lambda r: (r["_img"], r["engine"]))
print("OUTLIERS", len(out))
for r in out:
    print("  %.4f  %-12s %-11s  mtime=%s" % (r["cer_median"], r["engine"], r["_img"], r["_mt"].strftime("%m-%d %H:%M")))

by_sample = collections.Counter(r["_img"] for r in out)
print("by_sample", dict(by_sample.most_common()))
newer = [r for r in out if r["_mt"] >= datetime.datetime(2026, 11, 6, 10, 0)]
print("outliers_written_after_10:00", len(newer))

# rate: completion timestamps (max rep ts per cell)
latest = []
for r in rows:
    ts = [x.get("ts") for x in r.get("reps", []) if x.get("ts")]
    if ts:
        latest.append(max(datetime.datetime.fromisoformat(t) for t in ts))
latest.sort()
now = datetime.datetime.now()
for h in (6, 12, 24, 48):
    win = [t for t in latest if (now - t).total_seconds() <= h * 3600]
    if len(win) >= 2:
        span = (win[-1] - win[0]).total_seconds() / 60
        print("window %2dh: n=%d span=%.1fmin rate=%.2f min/cell" % (h, len(win), span, span / (len(win) - 1) if len(win) > 1 else 0))
    else:
        print("window %2dh: n=%d" % (h, len(win)))
print("last_completion", latest[-1].isoformat(), "age_min", round((now - latest[-1]).total_seconds() / 60, 1))

# wall stats
walls = [r["wall_median"] for r in rows if isinstance(r.get("wall_median"), (int, float))]
print("wall_median_all %.1f n=%d  min=%.1f max=%.1f" % (statistics.median(walls), len(walls), min(walls), max(walls)))
wper = collections.defaultdict(list)
for r in rows:
    if isinstance(r.get("wall_median"), (int, float)):
        wper[r["engine"]].append(r["wall_median"])
for e in sorted(wper):
    print("  wall_med %-13s n=%d %.1f" % (e, len(wper[e]), statistics.median(wper[e])))

# status by engine with counts of attempts for failed
print("failed cells:")
for r in rows:
    if r.get("status") != "complete":
        print("  %-13s %-12s n_attempt=%s err=%s mtime=%s" % (
            r["engine"], r["_img"], r.get("n_attempt"), str(r.get("err"))[:40], r["_mt"].strftime("%m-%d %H:%M")))
