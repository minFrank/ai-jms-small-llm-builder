# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(BASE, "cells", "ep13-full-001")
MAN = os.path.join(BASE, "samples", "manifest.json")
ST = os.path.join(BASE, "control", "batch_state.json")

now = datetime.datetime.now()
st = json.load(open(ST, encoding="utf-8"))

man = json.load(open(MAN, encoding="utf-8"))
sha2img = {}
for s in man.get("samples", []):
    sha2img[s.get("sha256")] = s.get("img")

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
rows = []
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        rows.append({"file": os.path.basename(f), "status": "PARSE_ERR", "err": str(e)})
        continue
    rows.append({
        "file": os.path.basename(f),
        "cell_key": d.get("cell_key"),
        "engine": d.get("engine"),
        "sample_id": d.get("sample_id"),
        "status": d.get("status"),
        "cer": d.get("cer_median"),
        "wall": d.get("wall_median"),
        "sha": (d.get("input") or {}).get("sha256"),
        "n_attempt": d.get("n_attempt"),
        "n_valid": d.get("n_valid"),
        "n_fail": d.get("n_fail"),
        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)),
    })

n_total = len(rows)
from collections import Counter, defaultdict
status_c = Counter(r.get("status") for r in rows)
engine_status = defaultdict(Counter)
for r in rows:
    engine_status[r.get("engine")][r.get("status")] += 1

# CER
complete = [r for r in rows if r.get("status") == "complete" and isinstance(r.get("cer"), (int, float))]
normal = [r for r in complete if r["cer"] < 0.5]
outl = [r for r in complete if r["cer"] >= 0.5]
cer_med = statistics.median([r["cer"] for r in normal]) if normal else None
wall_med = statistics.median([r["wall"] for r in complete if isinstance(r.get("wall"), (int, float))]) if complete else None

def sample_name(r):
    return sha2img.get(r.get("sha")) or r.get("sample_id")

outl_sorted = sorted(outl, key=lambda r: -r["cer"])
outl_lines = ["  - CER %.3f · %s · %s (attempt=%s)" % (r["cer"], r.get("engine"), sample_name(r), r.get("n_attempt")) for r in outl_sorted]

# mtime-based progress: cells finished in this batch window
mtimes = sorted(r["mtime"] for r in rows if "mtime" in r)
recent = [m for m in mtimes if m >= datetime.datetime.fromisoformat(st.get("started_at"))]
per_engine_recent = Counter()
for r in rows:
    if "mtime" in r and r["mtime"] >= datetime.datetime.fromisoformat(st.get("started_at")):
        per_engine_recent[r.get("engine")] += 1

# rate: cells completed in last N minutes
def count_since(dt):
    return sum(1 for r in rows if "mtime" in r and r["mtime"] >= dt)

for win in (60, 120, 180):
    print("cells_mtime_last_%dmin=%d" % (win, count_since(now - datetime.timedelta(minutes=win))))

# last 10 mtime gaps
last10 = mtimes[-12:]
gaps = [(last10[i+1]-last10[i]).total_seconds()/60 for i in range(len(last10)-1)]
print("last10_gaps_min=", [round(g,2) for g in gaps])
if len(mtimes) >= 2:
    span_h = (mtimes[-1]-mtimes[0]).total_seconds()/3600
    print("full_span_hours=%.2f" % span_h)

# batch window rate
if recent:
    span = (max(recent)-min(recent)).total_seconds()/60
    print("batch_started_cells=%d span_min=%.1f rate=%.2f min/cell" % (len(recent), span, span/max(1,len(recent)-1) if len(recent)>1 else 0))

print()
print("NOW=", now.isoformat(timespec="seconds"))
print("STATE=", json.dumps(st, ensure_ascii=False))
lp = datetime.datetime.fromisoformat(st.get("last_progress"))
print("last_progress_age_min=%.1f" % ((now-lp).total_seconds()/60))
print()
print("TOTAL_CELLS=", n_total, " expected=", man.get("count"), "*5 =", (man.get("count") or 0)*5)
print("STATUS=", dict(status_c))
print()
print("ENGINE_STATUS:")
for e in sorted(engine_status, key=lambda x: str(x)):
    print("  ", e, dict(engine_status[e]))
print()
print("CER_MED(normal<0.5, n=%d)=%.4f" % (len(normal), cer_med) if normal else "CER none")
print("WALL_MED(complete n=%d)=%s" % (len(complete), round(wall_med,2) if wall_med else None))
print("OUTLIERS n=%d:" % len(outl_sorted))
for l in outl_lines:
    print(l)
print()
non_complete = [r for r in rows if r.get("status") != "complete"]
print("NON_COMPLETE n=%d:" % len(non_complete))
for r in non_complete:
    print("  -", r.get("file"), "status=", r.get("status"), "engine=", r.get("engine"), "n_attempt=", r.get("n_attempt"), "n_fail=", r.get("n_fail"), "mtime=", r.get("mtime"))
print()
# newest cells
print("NEWEST_8:")
for r in sorted([x for x in rows if "mtime" in x], key=lambda x: -x["mtime"].timestamp())[:8]:
    print("  ", r["mtime"].isoformat(timespec="seconds"), r.get("status"), r.get("engine"), sample_name(r))
