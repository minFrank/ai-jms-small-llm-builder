import json, glob, os, statistics, datetime, collections

base = r"D:/study/ai-jms/ep13-docparse"
state = json.load(open(os.path.join(base, "control/batch_state.json"), encoding="utf-8"))
print("STATE:", json.dumps(state, ensure_ascii=False))

manifest = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
print("MANIFEST_TYPE:", type(manifest).__name__)
if isinstance(manifest, dict):
    print("MANIFEST_KEYS:", list(manifest.keys())[:8])
    # try sha->img
    sha2img = {}
    for k, v in manifest.items():
        if isinstance(v, dict):
            img = v.get("img") or v.get("path") or v.get("file")
            if img:
                sha2img[k] = img
    if not sha2img:
        # maybe list under some key
        for v in manifest.values():
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict) and (it.get("img") or it.get("path")):
                        sha2img[it.get("sha256") or it.get("sha") or it.get("input_sha256")] = it.get("img") or it.get("path")
elif isinstance(manifest, list):
    sha2img = {}
    for it in manifest:
        if isinstance(it, dict):
            sha2img[it.get("sha256") or it.get("sha") or it.get("input_sha256")] = it.get("img") or it.get("path")
print("SHA2IMG_N:", len(sha2img))
if sha2img:
    print("SHA2IMG_SAMPLE:", list(sha2img.items())[:2])

files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
print("CELL_FILES:", len(files))

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("READ_ERR", f, e)
        continue
    rows.append(d)

print("ROWS:", len(rows))
if rows:
    print("KEYS_SAMPLE:", sorted(rows[0].keys()))

# status / engine distribution
st = collections.Counter(r.get("status") for r in rows)
print("STATUS_DIST:", dict(st))

eng = collections.Counter(r.get("engine") for r in rows)
print("ENGINE_DIST:", dict(eng))

# engine x status
es = collections.Counter((r.get("engine"), r.get("status")) for r in rows)
print("ENGINE_STATUS:", {f"{k[0]}|{k[1]}": v for k, v in sorted(es.items())})

# CER
cers = []
for r in rows:
    c = r.get("cer_median")
    if c is None:
        continue
    cers.append((c, r.get("engine"), r.get("status"), os.path.basename(r.get("_file", "")) or r.get("cell") or r.get("id") or r.get("sample") or "", r.get("input_sha256") or r.get("input.sha256")))

print("CER_COUNT:", len(cers))
normal = [c for c in cers if c[0] < 0.5 and c[2] == "complete"]
print("NORMAL_N:", len(normal))
if normal:
    print("CER_MEDIAN_NORMAL:", statistics.median([c[0] for c in normal]))
    print("CER_MIN_MAX:", min(c[0] for c in normal), max(c[0] for c in normal))

out = [c for c in cers if c[0] >= 0.5]
print("OUTLIERS_N:", len(out))
for c in sorted(out, key=lambda x: -x[0]):
    name = c[3]
    sha = c[4]
    img = sha2img.get(sha, "?") if sha else "?"
    print("OUTLIER: %.4f | %s | %s | status=%s | img=%s" % (c[0], c[1], name, c[2], img))

# wall
walls = [r.get("wall_median") for r in rows if r.get("wall_median") is not None]
print("WALL_N:", len(walls))
if walls:
    print("WALL_MEDIAN:", statistics.median(walls), "min", min(walls), "max", max(walls))

# non-complete cells
nc = [r for r in rows if r.get("status") != "complete"]
print("NON_COMPLETE_N:", len(nc))
for r in nc[:20]:
    print("NON_COMPLETE:", os.path.basename(r.get("_file", "")), r.get("status"), r.get("engine"), r.get("cer_median"), r.get("wall_median"))

# per-cell completeness: expect 6 engines per sample?
by_sample = collections.defaultdict(list)
for r in rows:
    key = r.get("input_sha256") or r.get("input.sha256") or r.get("sample") or r.get("id") or "?"
    by_sample[key].append(r.get("engine"))
print("SAMPLES_WITH_CELLS:", len(by_sample))
sizes = collections.Counter(len(v) for v in by_sample.values())
print("CELLS_PER_SAMPLE_DIST:", dict(sizes))

# timing
lp = state.get("last_progress")
st0 = state.get("started_at")
now = datetime.datetime.now()
def pt(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None
lpd = pt(lp); std = pt(st0)
print("NOW:", now.isoformat(timespec="seconds"))
if lpd:
    print("MIN_SINCE_PROGRESS:", round((now - lpd).total_seconds() / 60.0, 1))
if std and lpd:
    mins = (lpd - std).total_seconds() / 60.0
    print("START_TO_LASTPROGRESS_MIN:", round(mins, 1))
