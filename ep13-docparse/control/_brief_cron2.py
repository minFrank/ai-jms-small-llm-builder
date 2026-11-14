import json, glob, os, time, datetime, statistics, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
u2img = {}
u2sid = {}
for s in man["samples"]:
    u2img[s["sample_uuid"]] = s["img"]
    u2sid[s["sample_uuid"]] = s["sample_id"]

files = sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    b = os.path.basename(f)
    uid = b.split("__")[0]
    d["_f"] = b
    d["_img"] = u2img.get(uid, "?")
    d["_sid"] = u2sid.get(uid, "?")
    d["_mt"] = os.path.getmtime(f)
    rows.append(d)

# outliers with img names
known = {("xiaomi_vl", "shot_01"), ("xiaomi_vl", "table_01")}
print("=== OUTLIERS (cer>=0.5) ===")
outs = []
for r in rows:
    if r.get("status") == "complete" and isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] >= 0.5:
        outs.append(r)
for r in sorted(outs, key=lambda x: -x["cer_median"]):
    tag = "KNOWN" if (r["engine"], r["_sid"]) in known else "NEW?"
    print(f"  {r['cer_median']:.3f} {r['engine']:14s} {r['_sid']:12s} {r['_img']:22s} {tag}")

# timeline
print("=== TIMELINE ===")
mts = sorted(r["_mt"] for r in rows)
def fmt(t): return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M")
print("first cell:", fmt(mts[0]), " last cell:", fmt(mts[-1]))
now = time.time()
print("now:", fmt(now), " last cell age(min):", round((now - mts[-1]) / 60, 1))

# per-cell completion sequence: rate over recent N cells
seq = sorted(rows, key=lambda r: r["_mt"])
print("=== LAST 15 CELL MTIMES ===")
for r in seq[-15:]:
    print("  ", fmt(r["_mt"]), r["_f"], r["status"])

# rate windows: last 10, last 20, last 50
def rate(n):
    s = seq[-n:]
    if len(s) < 2: return None
    span = (s[-1]["_mt"] - s[0]["_mt"]) / 60.0
    return span / (len(s) - 1), span, len(s)
for n in (10, 20, 50, 100, len(seq)):
    r = rate(n)
    if r: print(f"RATE last{n}: {r[0]:.2f} min/cell over {r[1]:.1f} min ({r[2]} cells)")

# batch progress by day
byday = collections.Counter(datetime.datetime.fromtimestamp(r["_mt"]).strftime("%m-%d") for r in rows)
print("BY_DAY", dict(sorted(byday.items())))

# remaining
done = sum(1 for r in rows if r["status"] == "complete")
failed = sum(1 for r in rows if r["status"] != "complete")
print("done", done, "failed", failed, "total", len(rows))

# batch_state seq parse
st = json.load(open(os.path.join(BASE, "control/batch_state.json"), encoding="utf-8"))
print("state", json.dumps(st, ensure_ascii=False))

# engine wall median
by_eng_wall = collections.defaultdict(list)
by_eng_cer = collections.defaultdict(list)
for r in rows:
    if r.get("status") == "complete":
        if isinstance(r.get("wall_median"), (int, float)): by_eng_wall[r["engine"]].append(r["wall_median"])
        if isinstance(r.get("cer_median"), (int, float)): by_eng_cer[r["engine"]].append(r["cer_median"])
print("=== PER ENGINE ===")
for e in sorted(by_eng_wall):
    w = by_eng_wall[e]
    c = sorted(x for x in by_eng_cer[e] if x < 0.5)
    print(f"  {e:14s} n={len(w):3d} wall_med={statistics.median(w):7.1f}s cer_med(<0.5)={statistics.median(c):.4f} n_cer_ok={len(c)}")

# global CER median normal
allcer = sorted(x for e in by_eng_cer for x in by_eng_cer[e] if x < 0.5)
print("GLOBAL CER MEDIAN (<0.5):", round(statistics.median(allcer), 4), "n=", len(allcer))
allw = [x for e in by_eng_wall for x in by_eng_wall[e]]
print("GLOBAL WALL MEDIAN:", round(statistics.median(allw), 1), "s")

# status counts by engine for failed
print("=== FAILED DETAIL ===")
for r in rows:
    if r.get("status") != "complete":
        print("  ", r["engine"], r["_sid"], r["_img"], r.get("err"), r.get("err_kind"), "n_valid=", r.get("n_valid"), "attempt=", r.get("n_attempt"), fmt(r["_mt"]))
