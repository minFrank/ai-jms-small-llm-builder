import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
state = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
print("STATE:", json.dumps(state, ensure_ascii=False))

cell_dir = os.path.join(BASE, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(cell_dir, "*.json")))
print("CELL_FILES:", len(files))

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("BADJSON", os.path.basename(f), e)
        continue
    rows.append((os.path.basename(f), d))

print("PARSED:", len(rows))

# status / engine distribution
st = collections.Counter()
eng = collections.Counter()
st_eng = collections.Counter()
by_engine = collections.defaultdict(collections.Counter)
for name, d in rows:
    s = d.get("status")
    e = d.get("engine")
    st[s] += 1
    eng[e] += 1
    st_eng[(s, e)] += 1
    by_engine[e][s] += 1

print("STATUS:", dict(st))
print("ENGINE:", dict(eng))
print("STATUS_X_ENGINE:", {f"{k[0]}|{k[1]}": v for k, v in st_eng.items()})
print("BY_ENGINE:", {str(k): dict(v) for k, v in by_engine.items()})

noncomplete = [n for n, d in rows if d.get("status") != "complete"]
print("NON_COMPLETE:", noncomplete)

def g(d, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None

# CER
cers = []
outliers = []
for name, d in rows:
    cer = g(d, "cer_median", "cer")
    if cer is None:
        continue
    try:
        cer = float(cer)
    except Exception:
        continue
    cers.append((cer, d.get("engine"), name, d.get("status")))
    if cer > 0.5:
        outliers.append((cer, d.get("engine"), name, d.get("status")))

norm = sorted(c[0] for c in cers if c[0] < 0.5 and c[3] == "complete")
print("CER_N:", len(cers), "NORMAL_N:", len(norm))
if norm:
    print("CER_MED_NORMAL:", round(statistics.median(norm), 4))

# sample mapping
man_path = os.path.join(BASE, "samples", "manifest.json")
sha2img = {}
if os.path.exists(manifest := man_path) or True:
    try:
        man = json.load(open(man_path, encoding="utf-8"))
        if isinstance(man, dict):
            # could be sha->img or list of records
            for k, v in man.items():
                if isinstance(v, str):
                    sha2img[k] = v
                elif isinstance(v, dict):
                    sha = v.get("sha256") or v.get("sha") or k
                    img = v.get("img") or v.get("file") or v.get("path") or v.get("name")
                    sha2img[sha] = img
        elif isinstance(man, list):
            for v in man:
                sha = v.get("sha256") or v.get("sha")
                img = v.get("img") or v.get("file") or v.get("path") or v.get("name")
                if sha:
                    sha2img[sha] = img
    except Exception as e:
        print("MANIFEST_ERR", e)
print("MANIFEST_KEYS:", len(sha2img))

def sample_of(d):
    sha = g(d, "input.sha256", "input_sha256", "sha256")
    if sha is None:
        inp = d.get("input")
        if isinstance(inp, dict):
            sha = inp.get("sha256")
        elif isinstance(inp, str):
            sha = inp
    if sha and sha in sha2img:
        return sha2img[sha]
    # fallback: cell name
    return g(d, "sample", "img", "image") or os.path.splitext(name)[0]

for cer, e, name, s in sorted(outliers, reverse=True):
    d = dict(rows)[name]
    print("OUTLIER:", round(cer, 4), "|", e, "|", sample_of(d), "|", name, "|", s)

# walls
walls = []
for name, d in rows:
    w = g(d, "wall_median", "wall", "wall_s")
    if w is None:
        continue
    try:
        w = float(w)
    except Exception:
        continue
    if d.get("status") == "complete":
        walls.append(w)
if walls:
    print("WALL_MED_S:", round(statistics.median(walls), 1), "N:", len(walls))

# timing / rate
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
print("NOW:", now.isoformat())
try:
    started = datetime.datetime.fromisoformat(state["started_at"])
    lp = datetime.datetime.fromisoformat(state["last_progress"])
    print("ELAPSED_MIN:", round((now - started).total_seconds() / 60, 1))
    print("SINCE_PROGRESS_MIN:", round((now - lp).total_seconds() / 60, 1))
except Exception as e:
    print("TIME_ERR", e)

# keys of one cell for schema awareness
print("SAMPLE_KEYS:", sorted(rows[0][1].keys()))
print("FIRST_ROW:", json.dumps(rows[0][1], ensure_ascii=False)[:800])
