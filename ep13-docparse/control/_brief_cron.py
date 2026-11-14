import json, glob, os, statistics, hashlib, collections, datetime

BASE = r"D:/study/ai-jms/ep13-docparse"
st = json.load(open(os.path.join(BASE, "control/batch_state.json"), encoding="utf-8"))
hb = json.load(open(os.path.join(BASE, "control/heartbeat.json"), encoding="utf-8"))
tk = json.load(open(os.path.join(BASE, "control/task.json"), encoding="utf-8"))
print("STATE", json.dumps(st, ensure_ascii=False))
print("HB", json.dumps(hb, ensure_ascii=False))
print("TASK", json.dumps(tk, ensure_ascii=False))

files = sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json")))
print("NCELLS", len(files))

# manifest sha256 -> img
man = {}
try:
    m = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
    if isinstance(m, dict):
        items = m
    else:
        items = {}
        for e in m:
            items[e.get("sha256")] = e
    for k, v in (m.items() if isinstance(m, dict) else []):
        pass
    print("MAN_TYPE", type(m).__name__, "MAN_LEN", len(m))
except Exception as e:
    print("MAN_ERR", e)

def walk_manifest(m):
    out = {}
    def rec(o):
        if isinstance(o, dict):
            sha = o.get("sha256") or o.get("sha")
            img = o.get("img") or o.get("image") or o.get("path") or o.get("file")
            if sha and img:
                out[sha] = img
            for v in o.values():
                rec(v)
        elif isinstance(m, list):
            for v in o:
                rec(v)
    if isinstance(m, dict) and "sha256" not in m:
        # maybe sha->entry mapping
        for k, v in m.items():
            if isinstance(v, dict):
                img = v.get("img") or v.get("image") or v.get("path") or v.get("file") or v.get("name")
                if img:
                    out[k] = img
                rec(v)
            else:
                rec(v)
    else:
        rec(m)
    return out

try:
    man_map = walk_manifest(m)
except Exception as e:
    man_map = {}
    print("MANMAP_ERR", e)
print("MANMAP", len(man_map))
if man_map:
    k = list(man_map)[:3]
    print("MAN_SAMPLE", [(x, man_map[x]) for x in k])

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    d["_file"] = os.path.basename(f)
    rows.append(d)

print("KEYS", sorted({k for r in rows for k in r if k != "_file"}))

stat = collections.Counter()
by_engine = collections.defaultdict(collections.Counter)
for r in rows:
    s = r.get("status")
    stat[s] += 1
    by_engine[r.get("engine")][s] += 1
print("STATUS_DIST", dict(stat))
for e, c in sorted(by_engine.items(), key=lambda x: str(x[0])):
    print("ENGINE", e, dict(c))

def num(r, k):
    v = r.get(k)
    try:
        return float(v)
    except Exception:
        return None

# CER
cer_ok = []
outliers = []
noncomplete = []
for r in rows:
    if r.get("status") != "complete":
        noncomplete.append((r.get("_file"), r.get("status"), r.get("engine"), r.get("error") or r.get("err") or ""))
        continue
    c = num(r, "cer_median")
    if c is None:
        continue
    if c < 0.5:
        cer_ok.append(c)
    else:
        outliers.append((c, r.get("engine"), r.get("_file"), r.get("input_sha256") or r.get("input.sha256")))

print("N_COMPLETE_CER_OK", len(cer_ok))
if cer_ok:
    print("CER_MEDIAN_OK", round(statistics.median(cer_ok), 4))
print("OUTLIERS", len(outliers))
for o in sorted(outliers, reverse=True):
    sha = o[3]
    img = man_map.get(sha, "?") if sha else "?"
    print("  OUT", round(o[0], 3), o[1], o[2], "img=", img, "sha=", str(sha)[:12])

walls = [num(r, "wall_median") for r in rows if r.get("status") == "complete"]
walls = [w for w in walls if w is not None]
print("WALL_N", len(walls))
if walls:
    print("WALL_MEDIAN_S", round(statistics.median(walls), 1), "MIN", round(min(walls),1), "MAX", round(max(walls),1))

# mtimes for rate
mt = []
for f in files:
    try:
        mt.append((os.path.getmtime(f), os.path.basename(f)))
    except Exception:
        pass
mt.sort()
print("OLDEST", datetime.datetime.fromtimestamp(mt[0][0]).strftime("%m-%d %H:%M:%S"), mt[0][1])
print("NEWEST", datetime.datetime.fromtimestamp(mt[-1][0]).strftime("%m-%d %H:%M:%S"), mt[-1][1])

# per-engine complete counts & mtimes to estimate batch rate (recent)
import time
now = time.time()
recent = [m for m in mt if now - m[0] < 6*3600]
print("RECENT_6H", len(recent))
if len(recent) >= 2:
    span = (recent[-1][0] - recent[0][0]) / 60.0
    print("RECENT_SPAN_MIN", round(span, 1), "PER_CELL_MIN", round(span / (len(recent)-1), 2) if len(recent) > 1 else None)

# non-complete detail
print("NONCOMPLETE", len(noncomplete))
for x in noncomplete[:40]:
    print("  NC", x)

# sample of a complete cell to see fields
for r in rows:
    if r.get("status") == "complete":
        print("SAMPLE_COMPLETE", json.dumps({k: v for k, v in r.items() if k != "_file"}, ensure_ascii=False)[:1200])
        break
for r in rows:
    if r.get("status") not in ("complete",):
        print("SAMPLE_OTHER", json.dumps({k: v for k, v in r.items() if k != "_file"}, ensure_ascii=False)[:800])
        break
