import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells/ep13-full-001")
MAN = os.path.join(BASE, "samples/manifest.json")

state = json.load(open(os.path.join(BASE, "control/batch_state.json"), encoding="utf-8"))
print("STATE:", json.dumps(state, ensure_ascii=False))

now = datetime.datetime.now()
lp = datetime.datetime.fromisoformat(state.get("last_progress", "2000-01-01T00:00:00"))
print("now:", now.isoformat(timespec="seconds"), "last_progress age(min):", round((now-lp).total_seconds()/60,1))

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
print("cell files:", len(files))

manifest = json.load(open(MAN, encoding="utf-8"))
# build sha->img
sha2img = {}
if isinstance(manifest, dict):
    items = manifest.get("items") or manifest.get("samples") or manifest
else:
    items = manifest
if isinstance(items, dict):
    items = list(items.values())
for it in items:
    if isinstance(it, dict):
        s = it.get("sha256") or it.get("sha")
        img = it.get("img") or it.get("image") or it.get("file") or it.get("name")
        if s and img:
            sha2img[s] = img
print("manifest sha entries:", len(sha2img))

status_ct = collections.Counter()
engine_ct = collections.Counter()
engine_status = collections.defaultdict(collections.Counter)
cers = []          # (cer, engine, sample)
wall = []
sha_of = {}
bad = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        bad.append((f, str(e)))
        continue
    st = d.get("status")
    en = d.get("engine")
    status_ct[st] += 1
    engine_ct[en] += 1
    engine_status[en][st] += 1
    cer = d.get("cer_median")
    wm = d.get("wall_median")
    if wm is not None:
        try:
            wall.append(float(wm))
        except Exception:
            pass
    sha = None
    inp = d.get("input")
    if isinstance(inp, dict):
        sha = inp.get("sha256")
    if sha is None:
        sha = d.get("input_sha256") or (d.get("input") if isinstance(d.get("input"), str) else None)
    sample = d.get("sample") or d.get("input_name") or d.get("name") or ""
    if not sample and sha:
        sample = sha2img.get(sha, sha[:12])
    if cer is not None:
        try:
            cers.append((float(cer), en, sample, os.path.basename(f), d.get("wall_median")))
        except Exception:
            pass
    if st != "complete":
        bad.append((os.path.basename(f), st, en))

print("status:", dict(status_ct))
print("engine totals:", dict(engine_ct))
print("engine x status:")
for e, c in sorted(engine_status.items()):
    print("   ", e, dict(c))

norm = sorted([c for c in cers if c[0] < 0.5])
if norm:
    vals = sorted(c[0] for c in norm)
    med = statistics.median(vals)
    print("CER normal(<0.5) n=%d median=%.4f" % (len(vals), med))
outl = [c for c in cers if c[0] >= 0.5]
outl.sort(reverse=True)
print("CER outliers(>=0.5): %d" % len(outl))
for c in outl:
    print("   %.3f | %s | %s | %s" % (c[0], c[1], c[2], c[3]))

if wall:
    print("wall_median overall: n=%d median=%.1fs (%.2f min)" % (len(wall), statistics.median(wall), statistics.median(wall)/60))

print("non-complete cells:", len(bad))
for b in bad[:30]:
    print("   ", b)

# rate: use file mtimes of newest/oldest complete cells
mts = [os.path.getmtime(f) for f in files]
mts.sort()
print("oldest cell mtime:", datetime.datetime.fromtimestamp(mts[0]).isoformat(timespec="seconds"))
print("newest cell mtime:", datetime.datetime.fromtimestamp(mts[-1]).isoformat(timespec="seconds"))
# per engine wall median
print("per-engine wall median (min):")
for e in sorted(engine_ct):
    ws = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if d.get("engine") == e and d.get("wall_median") is not None:
            ws.append(float(d["wall_median"]))
    if ws:
        print("   %s n=%d median=%.1f min" % (e, len(ws), statistics.median(ws)/60))
