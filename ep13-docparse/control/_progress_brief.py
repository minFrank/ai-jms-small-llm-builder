import json, os, glob, statistics, datetime

base = r"D:/study/ai-jms/ep13-docparse"
state = json.load(open(os.path.join(base, "control", "batch_state.json"), encoding="utf-8"))
print("STATE:", json.dumps(state, ensure_ascii=False))

cell_dir = os.path.join(base, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(cell_dir, "*.json")))

cells = []
for f in files:
    try:
        c = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("READFAIL", os.path.basename(f), e)
        continue
    c["_file"] = os.path.basename(f)
    cells.append(c)

print("CELL_FILES:", len(cells))
if cells:
    print("KEYS:", sorted(cells[0].keys()))

# status/engine distributions
from collections import Counter, defaultdict
st = Counter()
eng = Counter()
eng_status = defaultdict(Counter)
noncomplete = []
for c in cells:
    s = c.get("status", "?")
    e = c.get("engine", "?")
    st[s] += 1
    eng[e] += 1
    eng_status[e][s] += 1
    if s != "complete":
        noncomplete.append((c["_file"], s, e))
print("STATUS:", dict(st))
print("ENGINE:", dict(eng))
print("ENG_STATUS:", {k: dict(v) for k, v in eng_status.items()})
print("NONCOMPLETE:", noncomplete)

# manifest sha->img
man_path = os.path.join(base, "samples", "manifest.json")
man = json.load(open(man_path, encoding="utf-8"))
if isinstance(man, dict):
    items = man.get("samples") or man.get("items") or man
else:
    items = man
sha2img = {}
def walk(o):
    if isinstance(o, dict):
        sha = o.get("sha256") or o.get("input_sha256")
        img = o.get("img") or o.get("file") or o.get("name") or o.get("path")
        if sha and img:
            sha2img[sha] = img
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
walk(items)
print("SHA2IMG:", len(sha2img))

# CER stats
def num(v):
    try:
        return float(v)
    except Exception:
        return None

normal_cers = []
outliers = []
walls = []
for c in cells:
    cer = num(c.get("cer_median"))
    wall = num(c.get("wall_median"))
    if wall is not None:
        walls.append((wall, c.get("engine"), c.get("input_sha256")))
    if cer is None:
        continue
    if cer < 0.5:
        normal_cers.append(cer)
    else:
        img = sha2img.get(c.get("input_sha256"), c.get("input_sha256", "?")[:12])
        outliers.append((cer, c.get("engine"), img, c.get("status")))

print("N_NORMAL_CER:", len(normal_cers))
if normal_cers:
    print("CER_MEDIAN_NORMAL:", round(statistics.median(normal_cers), 4))
outliers.sort(reverse=True)
print("OUTLIERS:")
for o in outliers:
    print("  ", round(o[0], 3), o[1], o[2], o[3])

if walls:
    print("WALL_MEDIAN_ALL:", round(statistics.median([w[0] for w in walls]), 2))
    print("WALL_MIN_MAX:", round(min(w[0] for w in walls),2), round(max(w[0] for w in walls),2))

# time analysis
now = datetime.datetime.now()
lp = datetime.datetime.fromisoformat(state["last_progress"])
st0 = datetime.datetime.fromisoformat(state["started_at"])
print("NOW:", now.isoformat(timespec="seconds"))
print("MIN_SINCE_PROGRESS:", round((now-lp).total_seconds()/60,1))
nrun = state["n_run"]
done_min = (lp - st0).total_seconds()/60
print("ELAPSED_MIN:", round(done_min,1), "PER_CELL:", round(done_min/max(nrun,1),2))
print("SEQ:", state["seq"])
