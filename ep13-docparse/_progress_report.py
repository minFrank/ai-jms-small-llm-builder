import json, glob, os, statistics, collections
d = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
files = sorted(glob.glob(os.path.join(d, "*.json")))
cells = []
for f in files:
    try:
        j = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("BADJSON", f, e); continue
    cells.append((os.path.basename(f), j))
print("files:", len(files))
# keys overview
print("sample keys:", sorted(cells[0][1].keys()) if cells else None)
status = collections.Counter()
eng = collections.Counter()
eng_status = collections.Counter()
cands = []
walls = []
noncomplete = []
for name, j in cells:
    st = j.get("status")
    status[st] += 1
    e = j.get("engine")
    eng[e] += 1
    eng_status[(e, st)] += 1
    if st != "complete":
        noncomplete.append((name, st))
    cer = j.get("cer_median")
    wm = j.get("wall_median")
    if isinstance(wm, (int, float)):
        walls.append((wm, name, e))
    sha = None
    inp = j.get("input")
    if isinstance(inp, dict):
        sha = inp.get("sha256")
    if isinstance(cer, (int, float)):
        cands.append((cer, name, e, sha))
print("status:", dict(status))
print("engine:", dict(eng))
print("eng_status:", {f"{k[0]}|{k[1]}": v for k, v in sorted(eng_status.items(), key=lambda x: str(x[0]))})
normal = sorted([c for c in cands if c[0] < 0.5])
outl = sorted([c for c in cands if c[0] >= 0.5], reverse=True)
print("cer_count:", len(cands))
if normal:
    print("cer_median_normal:", statistics.median([c[0] for c in normal]))
print("outliers:")
for c in outl:
    print("  ", c[0], c[1], c[2], c[3])
if walls:
    ws = sorted(w[0] for w in walls)
    print("wall_median_all:", statistics.median(ws), "n=", len(ws))
    print("wall_min_max:", ws[0], ws[-1])
print("noncomplete:", noncomplete)
# manifest map
mf = r"D:/study/ai-jms/ep13-docparse/samples/manifest.json"
try:
    m = json.load(open(mf, encoding="utf-8"))
    print("manifest type:", type(m).__name__, "len:", len(m))
except Exception as e:
    print("manifest err", e)
