import json, os, glob, statistics, datetime, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")

st = json.load(open(os.path.join(BASE, "control", "batch_state.json"), encoding="utf-8"))
man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
# manifest: sha256 -> img mapping (may be list or dict)
sha2img = {}
if isinstance(man, dict):
    for k, v in man.items():
        if isinstance(v, str):
            sha2img[k] = v
        elif isinstance(v, dict):
            s = v.get("sha256") or v.get("sha")
            img = v.get("img") or v.get("path") or v.get("file")
            if s:
                sha2img[s] = img
            else:
                # maybe key is sha
                sha2img[k] = v.get("img") or v.get("path") or k
elif isinstance(man, list):
    for v in man:
        s = v.get("sha256") or v.get("sha")
        img = v.get("img") or v.get("path") or v.get("file")
        if s:
            sha2img[s] = img

rows = []
for p in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(p), "status": "PARSE_ERR:" + str(e)})
        continue
    inp = d.get("input") or {}
    sha = inp.get("sha256") if isinstance(inp, dict) else None
    rows.append({
        "file": os.path.basename(p),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": sha,
        "sample": d.get("sample") or d.get("sample_id"),
        "keys": sorted(d.keys()),
    })

print("== batch_state ==")
print(json.dumps(st, ensure_ascii=False, indent=1))
print("n_cells_files:", len(rows))
print("manifest entries:", len(sha2img))

stc = collections.Counter(r["status"] for r in rows)
print("status dist:", dict(stc))

eng = collections.Counter((r["engine"], r["status"]) for r in rows)
print("engine x status:")
for k in sorted(eng, key=lambda x: (str(x[0]), str(x[1]))):
    print("   ", k, eng[k])

cers = [r["cer"] for r in rows if r["cer"] is not None]
normal = [c for c in cers if c < 0.5]
print("cer present:", len(cers), "normal(<0.5):", len(normal))
if normal:
    print("cer median normal:", round(statistics.median(normal), 4))
if cers:
    print("cer median all:", round(statistics.median(cers), 4))

# outliers
def sample_name(r):
    if r.get("sample"):
        return r["sample"]
    if r["sha"] and r["sha"] in sha2img:
        return sha2img[r["sha"]]
    # try file name lookup
    return None

outs = sorted([r for r in rows if r["cer"] is not None and r["cer"] >= 0.5],
              key=lambda r: -r["cer"])
print("outliers (CER>=0.5):", len(outs))
for r in outs:
    print("   %.3f | %s | %s | sha=%s" % (r["cer"], r["engine"], sample_name(r), (r["sha"] or "")[:12]))

# also show how sample names map for a couple cells
print("sample cell keys:", rows[0]["keys"])

walls = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
if walls:
    print("wall median (all):", round(statistics.median(walls), 2), "n=", len(walls))
    wnorm = [w for w in walls if w < 10000]
    print("wall median (<10000):", round(statistics.median(wnorm), 2), "n=", len(wnorm))

# non-complete statuses with file names
nc = [r for r in rows if r["status"] != "complete"]
print("non-complete count:", len(nc))
for r in nc[:40]:
    print("   ", r["status"], r["engine"], r["file"], r["cer"])

# wall by mtime ordering: progress rate
files = [(os.path.getmtime(os.path.join(CELLS, f)), f) for f in os.listdir(CELLS)]
files.sort()
print("first mtime:", datetime.datetime.fromtimestamp(files[0][0]))
print("last  mtime:", datetime.datetime.fromtimestamp(files[-1][0]))
