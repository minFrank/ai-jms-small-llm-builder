import json, os, glob, statistics, collections, datetime

BASE = r"D:/study/ai-jms/ep13-docparse"
cells_dir = os.path.join(BASE, "cells", "ep13-full-001")
man_path = os.path.join(BASE, "samples", "manifest.json")

with open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8") as f:
    bs = json.load(f)

# manifest mapping
sha2img = {}
try:
    man = json.load(open(man_path, encoding="utf-8"))
    def walk(o):
        if isinstance(o, dict):
            s = o.get("sha256") or o.get("sha")
            img = o.get("img") or o.get("path") or o.get("name") or o.get("file")
            if s and img:
                sha2img[s] = img
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(man)
except Exception as e:
    print("manifest_err", e)

files = sorted(glob.glob(os.path.join(cells_dir, "*.json")))
rows = []
bad = []
for p in files:
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        bad.append((os.path.basename(p), str(e)))
        continue
    rows.append((os.path.basename(p), d))

def g(d, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    # nested
    return None

status_c = collections.Counter()
engine_stat = collections.defaultdict(collections.Counter)
engines = collections.Counter()
cers = []
outliers = []
noncomplete = []
walls = []
wall_by_engine = collections.defaultdict(list)

sample_keys = None
for name, d in rows:
    if sample_keys is None:
        sample_keys = sorted(d.keys())
    st = d.get("status")
    en = d.get("engine")
    status_c[st] += 1
    engines[en] += 1
    engine_stat[en][st] += 1
    cer = d.get("cer_median")
    w = d.get("wall_median")
    sha = (d.get("input") or {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("input.sha256")
    if sha is None and isinstance(d.get("input"), dict):
        sha = d["input"].get("sha256")
    if st != "complete":
        noncomplete.append((name, st))
    if isinstance(cer, (int, float)):
        cers.append((cer, en, sha, name))
    if isinstance(w, (int, float)):
        walls.append(w)
        if en:
            wall_by_engine[en].append(w)

print("== keys ==", json.dumps(sample_keys, ensure_ascii=False))
print("== batch_state ==", json.dumps(bs, ensure_ascii=False))
print("cell_files:", len(files), "parsed:", len(rows), "badjson:", len(bad))
for b in bad:
    print("  BAD", b)
print("status:", dict(status_c))
print("engines:", dict(engines))
print("per-engine status:")
for en, c in sorted(engine_stat.items()):
    print("  ", en, dict(c))

normal = sorted([c for c in cers if c[0] < 0.5])
print("cer_n_normal:", len(normal))
vals = [c[0] for c in normal]
if vals:
    print("cer_median_normal: %.4f" % statistics.median(vals))
    print("cer_min/max_normal: %.4f / %.4f" % (min(vals), max(vals)))

out = sorted([c for c in cers if c[0] >= 0.5], key=lambda x: -x[0])
print("outliers:", len(out))
for cer, en, sha, name in out:
    img = sha2img.get(sha, "?")
    print("   %.3f | %s | %s | %s" % (cer, en, img, name))

if walls:
    print("wall_median_all: %.1f" % statistics.median(walls))
    for en, ws in sorted(wall_by_engine.items()):
        print("   wall %s: %.1f (n=%d)" % (en, statistics.median(ws), len(ws)))

print("noncomplete:", len(noncomplete))
for n, s in noncomplete[:20]:
    print("   ", n, s)

# mtime freshness
now = datetime.datetime.now()
mt = max((os.path.getmtime(os.path.join(cells_dir, f)) for f in files), default=0)
mtd = datetime.datetime.fromtimestamp(mt)
print("newest_cell_mtime:", mtd.isoformat(), "age_min: %.1f" % ((now-mtd).total_seconds()/60))
print("now:", now.isoformat())
