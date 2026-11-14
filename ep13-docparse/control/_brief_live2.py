import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")

man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
# build sha256 -> img
sha2img = {}
items = man if isinstance(man, list) else man.get("items") or man.get("samples") or list(man.values())
if isinstance(man, dict) and not any(k in man for k in ("items", "samples")):
    items = list(man.values())
for it in items:
    if not isinstance(it, dict):
        continue
    s = it.get("sha256") or (it.get("image") or {}).get("sha256")
    img = it.get("img") or it.get("name") or it.get("path") or it.get("file") or it.get("id")
    if s:
        sha2img[s] = img
print("MANIFEST_KEYS_TYPE", type(man).__name__, "N_SHA", len(sha2img))
if isinstance(man, dict):
    print("MANIFEST_TOP_KEYS", list(man.keys())[:8])

recs = []
for p in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    d["_file"] = os.path.basename(p)
    d["_mtime"] = os.path.getmtime(p)
    recs.append(d)

def sha_of(r):
    inp = r.get("input")
    if isinstance(inp, dict):
        return inp.get("sha256")
    return None

done = sorted([r for r in recs if r.get("status") == "complete"], key=lambda r: r["_mtime"])
print("COMPLETE", len(done), "TOTAL", len(recs))

def rate(n):
    if len(done) < 2:
        return None
    sel = done[-n:] if n else done
    span = sel[-1]["_mtime"] - sel[0]["_mtime"]
    k = len(sel) - 1
    if k <= 0:
        return None
    return span / 60.0 / k

for n in (5, 10, 20, len(done)):
    r_ = rate(n)
    if r_:
        print("RATE_last%d_min_per_cell=%.2f" % (n, r_))

last = done[-1]["_mtime"]
print("LAST_DONE", datetime.datetime.fromtimestamp(last).isoformat())
print("HOURS_SINCE_LAST_DONE", round((datetime.datetime.now().timestamp() - last) / 3600.0, 2))

# pending cells (status not present at all): count expected = 130 (5 engines x 26)
engines = collections.Counter(r.get("engine") for r in recs)
print("ENGINE_COUNT", dict(engines))
samples = set()
for r in recs:
    samples.add(sha_of(r))
print("N_SAMPLES_SEEN", len(samples))

# CER
ok = []
out = []
for r in recs:
    if r.get("status") != "complete":
        continue
    c = r.get("cer_median")
    if c is None:
        continue
    c = float(c)
    if c < 0.5:
        ok.append(c)
    else:
        out.append((c, r.get("engine"), sha2img.get(sha_of(r), sha_of(r)), r.get("sample_id"), r["_mtime"]))
out.sort(reverse=True)
print("CER_OK_N", len(ok), "MEDIAN", round(statistics.median(ok), 4))
print("OUTLIERS", len(out))
for c, e, img, sid, mt in out:
    print("  OUT %.4f %-12s img=%s sample_id=%s mtime=%s" % (c, e, img, sid, datetime.datetime.fromtimestamp(mt).strftime("%m-%d %H:%M")))

# outliers grouped by sample image (how many engines flag same sample)
by_img = collections.defaultdict(list)
for c, e, img, sid, mt in out:
    by_img[img].append((e, round(c, 3)))
print("OUTLIER_BY_IMG")
for img, lst in sorted(by_img.items(), key=lambda kv: -len(kv[1])):
    print("   ", img, sorted(lst, key=lambda x: -x[1]))

# wall
walls = [float(r["wall_median"]) for r in recs if r.get("status") == "complete" and r.get("wall_median") is not None]
print("WALL_MEDIAN", round(statistics.median(walls), 1), "s; p10", round(sorted(walls)[len(walls)//10], 1),
      "p90", round(sorted(walls)[len(walls)*9//10], 1))

# failed cells detail
fails = [r for r in recs if r.get("status") != "complete"]
print("FAILED", len(fails))
for r in sorted(fails, key=lambda r: r["_mtime"]):
    print("   FAIL", r.get("engine"), "img=", sha2img.get(sha_of(r), sha_of(r)), "err=", r.get("err"),
          "n_valid=", r.get("n_valid"), "n_attempt=", r.get("n_attempt"),
          "mtime=", datetime.datetime.fromtimestamp(r["_mtime"]).strftime("%m-%d %H:%M"))
