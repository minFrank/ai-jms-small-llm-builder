import json, os, glob, statistics, collections, datetime

base = r"D:/study/ai-jms/ep13-docparse"
cell_root = os.path.join(base, "cells")
print("RUN_DIRS", sorted(os.listdir(cell_root)))

run = os.path.join(cell_root, "ep13-full-001")
files = sorted(glob.glob(os.path.join(run, "*.json")))

man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
samples = man["samples"]
print("MANIFEST_KEYS", sorted(samples[0].keys()), "N", len(samples))
sha2img = {s["sha256"]: s["img"] for s in samples}
sha2id = {s["sha256"]: s.get("sample_id", "?") for s in samples}
img2sha = {s["img"]: s["sha256"] for s in samples}

rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_file"] = os.path.basename(f)
    rows.append(d)

def sha_of(d):
    inp = d.get("input") or {}
    return inp.get("sha256", "") if isinstance(inp, dict) else ""

# status per engine
st = collections.Counter((d.get("engine"), d.get("status")) for d in rows)
print("STATUS_TOTAL", dict(collections.Counter(d.get("status") for d in rows)))
for k in sorted(st):
    print("  ENG", k[0], k[1], st[k])

# failed details
fails = [d for d in rows if d.get("status") != "complete"]
print("NONCOMPLETE_N", len(fails))
for d in fails[:15]:
    print("  FAIL", d["_file"], "|err=", str(d.get("err"))[:80], "|kind=", d.get("err_kind"),
          "|n_attempt=", d.get("n_attempt"), "|n_fail=", d.get("n_fail"),
          "|sha=", sha_of(d)[:12], sha2img.get(sha_of(d), "?"))

# CER
cer = [(d.get("cer_median"), d.get("engine"), sha2img.get(sha_of(d), d.get("sample_id", "?")), sha2id.get(sha_of(d), "?"))
       for d in rows if isinstance(d.get("cer_median"), (int, float))]
normal = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print("CER_N", len(cer), "NORMAL_N", len(normal), "MED", round(statistics.median([c[0] for c in normal]), 4))
print("OUTLIERS")
for c in out:
    print("   ", round(c[0], 3), c[1], c[2], c[3])

# CER median by engine (all normal cells of engine)
byeng = collections.defaultdict(list)
for c in normal:
    byeng[c[1]].append(c[0])
print("CER_MED_BY_ENGINE", {k: f"{round(statistics.median(v), 4)}(n={len(v)})" for k, v in byeng.items()})

# wall
walls = [(d.get("wall_median"), d.get("engine")) for d in rows if isinstance(d.get("wall_median"), (int, float))]
print("WALL_MED_ALL", round(statistics.median([w[0] for w in walls]), 1), "n=", len(walls))
wby = collections.defaultdict(list)
for w, e in walls:
    wby[e].append(w)
print("WALL_MED_BY_ENGINE", {k: f"{round(statistics.median(v), 1)}(n={len(v)})" for k, v in wby.items()})

# mtimes: recent 20
mts = [(os.path.getmtime(f), os.path.basename(f)) for f in files]
mts.sort()
print("LAST_5_MTIME")
for t, n in mts[-5:]:
    print("   ", datetime.datetime.fromtimestamp(t).isoformat(timespec="seconds"), n)

# rate: cells completed in last 6h window etc
now = datetime.datetime.now().timestamp()
recent = [t for t, _ in mts if t > now - 6 * 3600]
print("CELLS_FINISHED_LAST_6H", len(recent))
recent24 = [t for t, _ in mts if t > now - 24 * 3600]
print("CELLS_FINISHED_LAST_24H", len(recent24))
# overall span rate
span = (mts[-1][0] - mts[0][0]) / 60
print("SPAN_MIN", round(span, 1), "AVG_MIN_PER_CELL", round(span / (len(mts) - 1), 2))

# oxr cells?
print("OXR_CELLS", len(glob.glob(os.path.join(run, "*__oxr__p1.json"))))
print("ALL_ENGINE_FILES", dict(collections.Counter(os.path.basename(f).split("__")[1] for f in files)))

# state
stt = json.load(open(os.path.join(base, "control/batch_state.json"), encoding="utf-8"))
lp = datetime.datetime.fromisoformat(stt["last_progress"])
print("MIN_SINCE_LP", round((datetime.datetime.now() - lp).total_seconds() / 60, 1))

# batch_state vs cells consistency: how many cells have failed status (should be counted?)
print("STATE_NFAIL", stt.get("n_fail"), "STATE_SEQ", stt.get("seq"), "STATE_NRUN", stt.get("n_run"), "STATE_NSKIP", stt.get("n_skip"))
