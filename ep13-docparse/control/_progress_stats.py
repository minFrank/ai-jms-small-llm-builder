import json, glob, os, statistics, collections

base = r"D:/study/ai-jms/ep13-docparse"
files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
rows, bad = [], []
for p in files:
    try:
        with open(p, encoding="utf-8") as f:
            rows.append(json.load(f))
    except Exception as e:
        bad.append((os.path.basename(p), str(e)))

print("cell_files:", len(files), "parse_fail:", len(bad), bad[:5])

status = collections.Counter()
eng_status = collections.defaultdict(collections.Counter)
cer_ok = []
outliers = []
walls = []
eng_wall = collections.defaultdict(list)
noncomplete = []
no_cer, no_wall = [], []

for d in rows:
    st, eng = d.get("status"), d.get("engine")
    cell = d.get("cell_key")
    status[st] += 1
    eng_status[eng][st] += 1
    if st != "complete":
        noncomplete.append((cell, st, d.get("err_kind")))
    cer, wall = d.get("cer_median"), d.get("wall_median")
    if cer is None:
        no_cer.append((cell, eng, st))
    elif cer < 0.5:
        cer_ok.append(cer)
    else:
        outliers.append((cer, eng, cell, d.get("input", {}).get("sha256", ""), d.get("sample_id")))
    if wall is None:
        no_wall.append((cell, eng, st))
    else:
        walls.append(wall)
        eng_wall[eng].append(wall)

print("status:", dict(status))
for eng in sorted(eng_status):
    print("   eng=%s -> %s" % (eng, dict(eng_status[eng])))
print("noncomplete n=%d:" % len(noncomplete))
for x in noncomplete[:40]:
    print("   ", x)
print("no_cer n=%d:" % len(no_cer), no_cer[:10])
print("no_wall n=%d:" % len(no_wall), no_wall[:10])

if cer_ok:
    s = sorted(cer_ok)
    print("CER normal(<0.5) n=%d median=%.4f p25=%.4f p75=%.4f min=%.4f max=%.4f"
          % (len(s), statistics.median(s), s[len(s)//4], s[3*len(s)//4], s[0], s[-1]))
print("outliers n=%d:" % len(outliers))
for o in sorted(outliers, key=lambda x: -x[0]):
    print("   CER=%.3f eng=%s cell=%s sha=%s sample=%s" % (o[0], o[1], o[2], o[3][:12], o[4]))

if walls:
    s = sorted(walls)
    print("wall all n=%d median=%.1fs (%.2f min) p25=%.1fs p75=%.1fs"
          % (len(s), statistics.median(s), statistics.median(s)/60, s[len(s)//4], s[3*len(s)//4]))
for eng in sorted(eng_wall):
    v = sorted(eng_wall[eng])
    print("   wall eng=%s n=%d median=%.1fs" % (eng, len(v), statistics.median(v)))

# manifest for outlier sample naming
mp = os.path.join(base, "samples/manifest.json")
sha2img = {}
if os.path.exists(mp):
    m = json.load(open(mp, encoding="utf-8"))
    print("manifest type=%s len=%s" % (type(m).__name__, len(m)))
    if isinstance(m, dict):
        for k, v in list(m.items())[:2]:
            print("   dict sample:", k, "->", json.dumps(v, ensure_ascii=False)[:200])
    elif isinstance(m, list):
        for v in m[:2]:
            print("   list sample:", json.dumps(v, ensure_ascii=False)[:200])
