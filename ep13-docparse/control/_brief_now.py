# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, time, subprocess
from collections import Counter, defaultdict

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
KNOWN_OUT = {"xiaomi_vl": {"shot_01", "table_01"}}

man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
st = json.load(open(os.path.join(ROOT, "control", "batch_state.json"), encoding="utf-8"))
print("NOW", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("STATE", json.dumps(st, ensure_ascii=False))

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
rows, mt = [], {}
for p in files:
    rows.append(json.load(open(p, encoding="utf-8")))
    mt[p] = os.path.getmtime(p)
print("FILES", len(files), "TOTAL_STATUS", dict(Counter(d.get("status") for d in rows)))

started = datetime.datetime.fromisoformat(st["started_at"]).timestamp()
n_this_run = sum(1 for p in files if mt[p] >= started)
print("cells_mtimed_since_started:", n_this_run, "of", len(files))

# rate by mtime
mts = sorted(mt.values())
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
overall = (mts[-1] - mts[0]) / 60.0 / (len(mts) - 1)
print("RATE recent%d=%.2f min/cell | overall_span=%.2f min/cell" % (k, recent, overall))
print("LAST_MTIME", datetime.datetime.fromtimestamp(mts[-1]).strftime("%H:%M:%S"),
      "age_min=%.1f" % ((time.time() - mts[-1]) / 60.0))

# engines
es = defaultdict(Counter)
for d in rows:
    es[d.get("engine")][d.get("status")] += 1
for e in sorted(es):
    print("  ENG", e, dict(es[e]))

# CER
cer = []
for p, d in zip(files, rows):
    v = d.get("cer_median")
    if isinstance(v, (int, float)):
        cer.append((v, d.get("engine"), sha2img.get((d.get("input") or {}).get("sha256"), "?"), p, mt[p]))
normal = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print("CER normal n=%d median=%.4f | all_complete_median=%.4f | outliers n=%d" % (
    len(normal), statistics.median([c[0] for c in normal]),
    statistics.median([c[0] for c in cer]), len(out)))
new_this_run, preexist = [], []
for v, e, img, p, m in out:
    tag = "KNOWN" if (e in KNOWN_OUT and str(img)[:-4] in KNOWN_OUT[e]) else "OTHER"
    bucket = new_this_run if m >= started else preexist
    bucket.append((tag, v, e, str(img)[:-4]))
print("OUTLIERS landed_this_run=%d preexisting=%d" % (len(new_this_run), len(preexist)))
for t, v, e, s in new_this_run:
    print("   THISRUN %s %.4f %s x %s" % (t, v, e, s))
print("-- preexisting (count by engine/sample) --")
pe = Counter((t, e, s) for t, v, e, s in preexist)
for kk, vv in sorted(pe.items(), key=lambda x: str(x[0])):
    print("   PRE tag=%s engine=%s sample=%s n=%d" % (kk[0], kk[1], kk[2], vv))
# sample clustering among all outliers
print("OUT_SAMPLE_CLUSTER", dict(Counter(s for t, v, e, s in new_this_run + preexist)))

wall = [d["wall_median"] for d in rows if isinstance(d.get("wall_median"), (int, float))]
print("WALL n=%d median=%.1fs p25=%.1f p75=%.1f" % (
    len(wall), statistics.median(wall),
    statistics.quantiles(wall, n=4)[0], statistics.quantiles(wall, n=4)[2]))

lp = datetime.datetime.fromisoformat(st["last_progress"])
now = datetime.datetime.now()
print("last_progress_age_min=%.1f elapsed_h=%.2f" % ((now - lp).total_seconds() / 60.0,
      (now - datetime.datetime.fromisoformat(st["started_at"])).total_seconds() / 3600.0))
print("state_sum=%d (run+skip+fail=%d) cellfiles=%d" % (
    st["n_run"] + st["n_skip"] + st["n_fail"], st["n_run"] + st["n_skip"] + st["n_fail"], len(files)))

# heartbeat
hb = json.load(open(os.path.join(ROOT, "control", "heartbeat.json"), encoding="utf-8"))
hage = (now - datetime.datetime.fromisoformat(hb["hb_at"])).total_seconds() / 60.0
print("HEARTBEAT", json.dumps(hb, ensure_ascii=False), "age_min=%.1f" % hage)

# process
q = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' -and "
     "$_.Name -like 'python*' } | ForEach-Object { $_.ProcessId.ToString() + '|' + $_.Name }")
r = subprocess.run(["powershell", "-NoProfile", "-Command", q],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
print("BATCH_PYTHON_PROCS", len(lines), lines)

# current cell file presence
cur = st.get("current") or ""
sep = "×" if "×" in cur else ("x" if "x" in cur else "")
if sep:
    img_p, eng_p = cur.rsplit(sep, 1)
    img_p, eng_p = img_p.strip(), eng_p.strip()
    sha_by_img = {os.path.basename(str(s["img"])): s["sha256"] for s in man["samples"]}
    sha = sha_by_img.get(img_p)
    hit = [os.path.basename(p) for p, d in zip(files, rows)
           if sha and (d.get("input") or {}).get("sha256") == sha and d.get("engine") == eng_p]
    print("CURRENT_CELL_FILE", cur, "sha=%s" % (str(sha)[:12] if sha else None), "->", hit)

# per-engine normal CER median
pe2 = defaultdict(list)
for v, e, img, p, m in normal:
    pe2[e].append(v)
for e in sorted(pe2):
    print("  CER_NORMAL %s n=%d median=%.4f" % (e, len(pe2[e]), statistics.median(pe2[e])))
