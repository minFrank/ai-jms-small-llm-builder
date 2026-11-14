import json, os, glob, statistics, datetime

BASE = r"D:/study/ai-jms/ep13-docparse"
state = json.load(open(BASE + "/control/batch_state.json", encoding="utf-8"))
cells_dir = BASE + "/cells/ep13-full-001"
manifest = json.load(open(BASE + "/samples/manifest.json", encoding="utf-8"))

sha2img = {}
if isinstance(manifest, dict):
    for k, v in manifest.items():
        if isinstance(v, str):
            sha2img[k] = v
        elif isinstance(v, dict):
            sha2img[k] = v.get("img") or v.get("path") or v.get("file") or str(v)
            if "sha256" in v:
                sha2img[v["sha256"]] = v.get("img") or v.get("path") or str(v)
elif isinstance(manifest, list):
    for v in manifest:
        sha2img[v.get("sha256")] = v.get("img") or v.get("path") or str(v)

files = sorted(glob.glob(cells_dir + "/*.json"))
recs = []
bad = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        bad.append((os.path.basename(f), str(e)))
        continue
    d["_file"] = os.path.basename(f)
    recs.append(d)

def g(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

from collections import Counter, defaultdict
status_c = Counter()
eng_c = Counter()
eng_status = defaultdict(Counter)
cer_by_eng = defaultdict(list)
wall_all = []
outliers = []
noncomplete = []
for d in recs:
    st = g(d, "status", default="<none>")
    en = g(d, "engine", default="<none>")
    status_c[st] += 1
    eng_c[en] += 1
    eng_status[en][st] += 1
    cer = g(d, "cer_median", "cer")
    wall = g(d, "wall_median", "wall")
    if isinstance(wall, (int, float)):
        wall_all.append(wall)
    if isinstance(cer, (int, float)):
        cer_by_eng[en].append((cer, d))
        if cer >= 0.5:
            sha = g(d, "input_sha256", "input", "sha256")
            if isinstance(sha, dict):
                sha = sha.get("sha256")
            img = sha2img.get(sha, (str(sha)[:12] if sha else "?"))
            outliers.append((cer, en, img, d["_file"]))
    if st != "complete":
        noncomplete.append((st, en, d["_file"], cer))

normal = sorted([c for c, d in [(g(d, "cer_median", "cer"), d) for d in recs]
                 if isinstance(c, (int, float)) and c < 0.5])
med_normal = statistics.median(normal) if normal else None
med_wall = statistics.median(wall_all) if wall_all else None

now = datetime.datetime.now()
lp = state.get("last_progress")
lp_age = None
if lp:
    try:
        lp_age = (now - datetime.datetime.fromisoformat(lp)).total_seconds() / 60.0
    except Exception:
        pass

print("NOW", now.isoformat(timespec="seconds"))
print("STATE", json.dumps(state, ensure_ascii=False))
print("NFILES", len(files), "NRECS", len(recs), "BAD", bad)
print("STATUS", dict(status_c))
print("ENGINE", dict(eng_c))
print("ENG_STATUS", {k: dict(v) for k, v in eng_status.items()})
print("CER_MED_NORMAL", med_normal, "n=", len(normal))
print("WALL_MED", med_wall, "n=", len(wall_all))
print("OUTLIERS", len(outliers))
for o in sorted(outliers, reverse=True):
    print("  OUT", round(o[0], 4), o[1], o[2], o[3])
print("NONCOMPLETE", len(noncomplete))
for nc in noncomplete[:40]:
    print("  NC", nc)
print("LP_AGE_MIN", lp_age)
