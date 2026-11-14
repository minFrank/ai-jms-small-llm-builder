# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:/study/ai-jms/ep13-docparse"
run = "ep13-full-001"
CELLD = f"{BASE}/cells/{run}"

st = json.load(open(f"{BASE}/control/batch_state.json", encoding="utf-8"))
print("BATCH_STATE:", json.dumps(st, ensure_ascii=False))

hb_path = f"{BASE}/control/heartbeat.json"
if os.path.exists(hb_path):
    print("HEARTBEAT:", json.dumps(json.load(open(hb_path, encoding="utf-8")), ensure_ascii=False))

# manifest sha->img
man = json.load(open(f"{BASE}/samples/manifest.json", encoding="utf-8"))
sha2img = {}
if isinstance(man, dict):
    items = man.items()
else:
    items = [(x.get("sha256"), x) for x in man]
for k, v in items:
    if isinstance(v, dict):
        sha2img[k] = v.get("img") or v.get("name") or v.get("file") or str(v)[:60]
    else:
        sha2img[k] = str(v)
print("manifest entries:", len(sha2img))

files = sorted(glob.glob(f"{CELLD}/*.json"))
print("cell files:", len(files))

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    rows.append({
        "file": os.path.basename(f),
        "status": d.get("status"),
        "engine": d.get("engine"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": d.get("input", {}).get("sha256") if isinstance(d.get("input"), dict) else d.get("input_sha256"),
        "sample": (d.get("input") or {}).get("img") if isinstance(d.get("input"), dict) else d.get("sample"),
        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)),
    })

from collections import Counter, defaultdict
print("\nSTATUS_DIST:", dict(Counter(r["status"] for r in rows)))
eng_status = defaultdict(Counter)
for r in rows:
    eng_status[r["engine"]][r["status"]] += 1
for e in sorted(eng_status, key=lambda x: str(x)):
    print("  engine", e, dict(eng_status[e]))

# non-complete
nc = [r for r in rows if r["status"] != "complete"]
print("\nNON_COMPLETE:", len(nc))
for r in nc[:40]:
    print("   ", r["file"], r["status"], r["engine"], r["cer"], r.get("err", ""))

# CER
ok = [r for r in rows if isinstance(r.get("cer"), (int, float))]
cers = sorted(r["cer"] for r in ok)
print("\ncer count:", len(cers))
if cers:
    print("cer median all:", round(statistics.median(cers), 4))
normal = [r for r in ok if r["cer"] < 0.5]
if normal:
    print("normal(<0.5) n=", len(normal), "median:", round(statistics.median([r["cer"] for r in normal]), 4))
out = [r for r in ok if r["cer"] >= 0.5]
out.sort(key=lambda r: -r["cer"])
print("OUTLIERS(>=0.5):", len(out))
for r in out:
    sha = r["sha"]
    img = r["sample"] or sha2img.get(sha) or "?"
    print("   cer=%.4f engine=%s sample=%s file=%s" % (r["cer"], r["engine"], img, r["file"]))

# wall
walls = [r["wall"] for r in rows if isinstance(r.get("wall"), (int, float))]
print("\nwall n=", len(walls), "median:", round(statistics.median(walls), 1) if walls else None)
for e in sorted(eng_status, key=lambda x: str(x)):
    w = [r["wall"] for r in rows if r["engine"] == e and isinstance(r.get("wall"), (int, float))]
    if w:
        print("   wall", e, "n=", len(w), "median=", round(statistics.median(w), 1))

# rate: mtimes of cells updated today (recent batch)
mts = sorted(r["mtime"] for r in rows)
print("\nmtime range:", mts[0], "->", mts[-1])
# last_progress based rate
lp = st.get("last_progress") or st.get("finished_at")
print("last_progress:", lp)
# cells modified in last 24h -> this batch
now = datetime.datetime.now()
recent = [m for m in mts if (now - m).total_seconds() <= 24 * 3600]
print("cells modified in last 24h:", len(recent))
if len(recent) >= 2:
    span = (max(recent) - min(recent)).total_seconds() / 60.0
    print("span min:", round(span, 1), "rate min/cell:", round(span / len(recent), 2))

# started_at? maybe in task.json
for name in ("task.json", "sets.yaml", "smoke_throughput.json"):
    p = f"{BASE}/control/{name}"
    if os.path.exists(p):
        print("\n---", name, "---")
        try:
            print(open(p, encoding="utf-8").read()[:1500])
        except Exception as e:
            print("err", e)
