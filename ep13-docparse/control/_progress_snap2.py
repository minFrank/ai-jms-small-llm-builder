# -*- coding: utf-8 -*-
"""Progress brief data pull for ep13 full run. ASCII output only."""
import json, os, glob, statistics, datetime, time, subprocess
from collections import Counter, defaultdict

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
KNOWN_OUT = {"xiaomi_vl": {"shot_01", "table_01"}}

man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
print("NOW", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

st = json.load(open(os.path.join(ROOT, "control", "batch_state.json"), encoding="utf-8"))
print("STATE", json.dumps(st, ensure_ascii=False))

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
rows = []
bad = []
for p in files:
    try:
        rows.append(json.load(open(p, encoding="utf-8")))
    except Exception as e:
        bad.append(os.path.basename(p) + " " + str(e))
print("FILES", len(files), "PARSE_ERR", len(bad), bad[:5])

# counts
n_run = st.get("n_run", 0); n_skip = st.get("n_skip", 0); n_fail = st.get("n_fail", 0)
print("COUNTS state_sum=%d (run=%d skip=%d fail=%d) cellfiles=%d" % (
    n_run + n_skip + n_fail, n_run, n_skip, n_fail, len(files)))

# seq
seq = str(st.get("seq"))
print("SEQ", seq)

eng_status = defaultdict(Counter)
for d in rows:
    eng_status[d.get("engine")][d.get("status")] += 1
print("STATUS_BY_ENGINE")
for e in sorted(eng_status, key=str):
    print("   ", e, dict(eng_status[e]))
print("TOTAL_STATUS", dict(Counter(d.get("status") for d in rows)))

nc = [(os.path.basename(p), d) for p, d in zip(files, rows) if d.get("status") != "complete"]
print("NON_COMPLETE", len(nc))
for fn, d in nc[:40]:
    print("   ", fn, d.get("engine"), d.get("status"), "cer=", d.get("cer_median"),
          "err=", (d.get("error") or d.get("err") or "")[:200])

cer = []
for p, d in zip(files, rows):
    v = d.get("cer_median")
    if isinstance(v, (int, float)):
        img = sha2img.get((d.get("input") or {}).get("sha256"), "?")
        cer.append((v, d.get("engine"), img))
normal = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print("CER normal n=%d median=%.4f | outliers n=%d" % (
    len(normal), statistics.median([c[0] for c in normal]) if normal else -1, len(out)))
for v, e, img in out:
    tag = "KNOWN" if (e in KNOWN_OUT and str(img)[:-4] in KNOWN_OUT[e]) else "NEW"
    print("   %s cer=%.4f %s x %s" % (tag, v, e, img))

wall = [d["wall_median"] for d in rows if isinstance(d.get("wall_median"), (int, float))]
if wall:
    print("WALL n=%d median=%.1fs min=%.1f max=%.1f" % (
        len(wall), statistics.median(wall), min(wall), max(wall)))

mts = sorted(os.path.getmtime(p) for p in files)
now = time.time()
if len(mts) >= 2:
    k = min(8, len(mts) - 1)
    print("RATE recent%d=%.2f min/cell | ALLSPAN %.1f min / %d cells = %.2f min/cell" % (
        k, (mts[-1] - mts[-1 - k]) / 60.0 / k,
        (mts[-1] - mts[0]) / 60.0, len(mts), (mts[-1] - mts[0]) / 60.0 / (len(mts) - 1)))
    print("FIRST_MTIME %s LAST_MTIME %s age=%.1f min" % (
        datetime.datetime.fromtimestamp(mts[0]).strftime("%Y-%m-%d %H:%M"),
        datetime.datetime.fromtimestamp(mts[-1]).strftime("%Y-%m-%d %H:%M"),
        (now - mts[-1]) / 60.0))

lp = st.get("last_progress")
if lp:
    age = (datetime.datetime.now() - datetime.datetime.fromisoformat(lp)).total_seconds() / 60.0
    print("last_progress=%s age=%.1f min" % (lp, age))
if st.get("started_at"):
    age0 = (datetime.datetime.now() - datetime.datetime.fromisoformat(st["started_at"])).total_seconds() / 3600.0
    print("started_at=%s elapsed=%.2f h" % (st["started_at"], age0))
if st.get("finished_at"):
    print("finished_at=%s" % st["finished_at"])

# process: real batch_runner python
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' -and "
      "$_.Name -like 'python*' } | ForEach-Object { $_.ProcessId.ToString() + '|' + "
      "$_.Name + '|' + $_.CreationDate.ToString('yyyy-MM-dd HH:mm:ss') }")
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
print("BATCH_PYTHON_PROCS", len(lines), lines)

hb_path = os.path.join(ROOT, "control", "heartbeat.json")
if os.path.exists(hb_path):
    hb = json.load(open(hb_path, encoding="utf-8"))
    print("HEARTBEAT", json.dumps(hb, ensure_ascii=False),
          "age_min=%.1f" % ((now - datetime.datetime.fromisoformat(hb.get("hb_at")).timestamp()) / 60.0))
else:
    print("HEARTBEAT missing")
