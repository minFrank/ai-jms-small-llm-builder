import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
cell_dir = os.path.join(BASE, "cells", "ep13-full-001")
man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
sha2img, uuid2img, imgcat = {}, {}, {}
for s in man["samples"]:
    sha2img[s["sha256"]] = s["img"]
    uuid2img[s["sample_uuid"]] = s["img"]
    imgcat[s["img"]] = s.get("category")

files = glob.glob(os.path.join(cell_dir, "*.json"))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_file"] = os.path.basename(f)
    d["_mtime"] = os.path.getmtime(f)
    rows.append(d)

now = datetime.datetime.now()

# rate
mts = sorted(r["_mtime"] for r in rows)
first, last = mts[0], mts[-1]
print("FIRST", datetime.datetime.fromtimestamp(first), "LAST", datetime.datetime.fromtimestamp(last))
print("FULL_RUN_H", round((last - first) / 3600, 2), "MIN_PER_CELL_FULL", round(((last - first) / 60) / len(mts), 2))
d20 = [(mts[i + 1] - mts[i]) / 60 for i in range(len(mts) - 20, len(mts) - 1)]
print("LAST20_MIN_PER_CELL", round(sum(d20) / len(d20), 2))
today = [m for m in mts if datetime.datetime.fromtimestamp(m).date() == now.date()]
if today:
    span = (today[-1] - today[0]) / 60
    print("TODAY_N", len(today), "TODAY_FIRST", datetime.datetime.fromtimestamp(today[0]).strftime("%H:%M"),
          "TODAY_LAST", datetime.datetime.fromtimestamp(today[-1]).strftime("%H:%M"),
          "TODAY_MIN_PER_CELL", round(span / max(len(today) - 1, 1), 2), "TODAY_HOURS", round(span / 60, 2))
print("LAST_FILE_AGE_MIN", round((now.timestamp() - last) / 60, 1))

# status by engine
be = collections.defaultdict(collections.Counter)
for r in rows:
    be[r.get("engine")][r.get("status")] += 1
print("BY_ENGINE", json.dumps({k: dict(v) for k, v in sorted(be.items())}, ensure_ascii=False))

# walls
walls = [r["wall_median"] for r in rows if r.get("status") == "complete" and isinstance(r.get("wall_median"), (int, float))]
print("WALL_MED_ALL_S", round(statistics.median(walls), 1), "N", len(walls))
for e in sorted(be):
    w = [r["wall_median"] for r in rows if r.get("engine") == e and r.get("status") == "complete" and isinstance(r.get("wall_median"), (int, float))]
    if w:
        print("  WALL_MED", e, round(statistics.median(w), 1), "n", len(w))

# CER
def img_of(r):
    uuid = r["cell_key"].split("__")[0]
    return uuid2img.get(uuid) or sha2img.get((r.get("input") or {}).get("sha256")) or r["_file"]

comp = [r for r in rows if r.get("status") == "complete"]
norm = sorted(r["cer_median"] for r in comp if isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] < 0.5)
outl = [r for r in comp if isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] >= 0.5]
print("CER_MED_NORMAL", round(statistics.median(norm), 4), "NORMAL_N", len(norm), "OUTL_N", len(outl))
outl.sort(key=lambda r: -r["cer_median"])
byeng = collections.Counter(r["engine"] for r in outl)
print("OUTL_BY_ENGINE", dict(byeng))
print("OUTLIER_LIST:")
for r in outl:
    print("  %.4f | %-12s | %-16s | %s | mtime %s" % (
        r["cer_median"], r["engine"], img_of(r), imgcat.get(img_of(r), "?"),
        datetime.datetime.fromtimestamp(r["_mtime"]).strftime("%m-%d %H:%M")))

# failed cells detail
fails = [r for r in rows if r.get("status") != "complete"]
print("FAILED_N", len(fails))
print("FAILED_ENG", dict(collections.Counter(r["engine"] for r in fails)))
for r in sorted(fails, key=lambda r: r["_mtime"]):
    print("  FAIL", img_of(r), r["engine"], r.get("status"), "err=", str(r.get("err"))[:60],
          "mtime", datetime.datetime.fromtimestamp(r["_mtime"]).strftime("%m-%d %H:%M"))

# state consistency
st = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
print("STATE", json.dumps(st, ensure_ascii=False))
print("STATE_SUM", st["n_run"] + st["n_skip"] + st["n_fail"], "CELL_FILES", len(rows),
      "COMPLETE", len(comp), "FAILED", len(fails))
lp = datetime.datetime.fromisoformat(st["last_progress"])
print("LAST_PROGRESS_AGE_MIN", round((now - lp).total_seconds() / 60, 1))
la = datetime.datetime.fromisoformat(st["started_at"])
print("SEG_ELAPSED_MIN", round((now - la).total_seconds() / 60, 1))
