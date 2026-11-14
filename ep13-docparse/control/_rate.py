# -*- coding: utf-8 -*-
"""Rate + leftover checks. ASCII output only."""
import json, os, glob, datetime, time, statistics

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
mts = sorted(os.path.getmtime(p) for p in files)
now = time.time()

def fmt(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")

# session boundaries: cells written this run day
cut = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
sess = [m for m in mts if m >= cut]
print("all cells %d span %s -> %s" % (len(files), fmt(mts[0]), fmt(mts[-1])))
if len(sess) >= 2:
    print("session(>=11-05 06:50) n=%d span=%.1f min => %.2f min/cell" % (
        len(sess), (sess[-1] - sess[0]) / 60.0, (sess[-1] - sess[0]) / 60.0 / (len(sess) - 1)))
for k in (5, 8, 12):
    if len(mts) > k:
        print("last%d: %.2f min/cell (%s -> %s)" % (
            k, (mts[-1] - mts[-1 - k]) / 60.0 / k, fmt(mts[-1 - k]), fmt(mts[-1])))

# cells written in final hour before finish
fin = datetime.datetime(2026, 11, 6, 1, 6, 6).timestamp()
last_hour = [m for m in mts if fin - m <= 3600]
print("cells in last hour before finish: %d" % len(last_hour))

# mtime histogram by hour (today)
from collections import Counter
c = Counter(datetime.datetime.fromtimestamp(m).strftime("%m-%d %H") for m in mts)
print("by hour:", dict(sorted(c.items())))

# outlier sample grouping
man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
out = []
for p in files:
    d = json.load(open(p, encoding="utf-8"))
    v = d.get("cer_median")
    if isinstance(v, (int, float)) and v >= 0.5:
        out.append((v, d.get("engine"), sha2img.get((d.get("input") or {}).get("sha256"), "?")))
out.sort(reverse=True)
byimg = Counter(i for _, _, i in out)
print("outlier by sample:", dict(byimg))
byeng = Counter(e for _, e, _ in out)
print("outlier by engine:", dict(byeng))

# process re-check
import subprocess
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' -and "
      "$_.Name -like 'python*' } | Measure-Object | Select-Object -ExpandProperty Count")
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("BATCH_PY_COUNT", (r.stdout or "").strip())
