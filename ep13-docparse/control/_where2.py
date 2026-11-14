# -*- coding: utf-8 -*-
"""Locate the 1 missing cell + check stray pids. ASCII output only."""
import json, os, glob, random, subprocess

ROOT = r"D:/study/ai-jms/ep13-docparse"
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]
man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
img2sha = {s["img"]: s["sha256"] for s in man["samples"]}
tasks = [(s["img"], e) for s in man["samples"] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != "oxr"]

# index every cell json anywhere under cells/
idx = {}
for p in glob.glob(os.path.join(ROOT, "cells", "*", "*.json")):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    sha = (d.get("input") or {}).get("sha256")
    if sha:
        idx.setdefault((sha, d.get("engine")), []).append(os.path.relpath(p, ROOT))

have_full = {(s, e) for (s, e), v in idx.items()
             if any(x.startswith(os.path.join("cells", "ep13-full-001")) for x in v)}
missing = [(img, eng) for img, eng in tasks if (img2sha[img], eng) not in have_full]
print("missing in full-001:", len(missing))
elsewhere = [(img, eng, idx.get((img2sha[img], eng))) for img, eng in missing
             if idx.get((img2sha[img], eng))]
print("found in OTHER dirs:", elsewhere)

# count in full-001 vs state
st = json.load(open(os.path.join(ROOT, "control", "batch_state.json"), encoding="utf-8"))
nfiles = len(glob.glob(os.path.join(ROOT, "cells", "ep13-full-001", "*.json")))
print("state run+skip=%d fail=%d | files=%d | gap(run+skip-files)=%d | missing=%d" % (
    st["n_run"] + st["n_skip"], st["n_fail"], nfiles,
    st["n_run"] + st["n_skip"] - nfiles, len(missing)))

# any live runner/worker python?
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and "
      "($_.CommandLine -like '*batch_runner*' -or $_.CommandLine -like '*runner.py*' "
      "-or $_.CommandLine -like '*cell_runner*') } | ForEach-Object { "
      "$_.ProcessId.ToString() + '|' + $_.CommandLine.Substring(0,[Math]::Min(160,$_.CommandLine.Length)) }")
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
print("LIVE_RUNNERS:")
for l in (r.stdout or "").splitlines():
    if l.strip():
        print("   ", l.strip())

# pid 7256 alive?
ps2 = ("Get-Process -Id 7256 -ErrorAction SilentlyContinue | ForEach-Object { "
       "$_.Id.ToString() + '|' + $_.ProcessName }")
r2 = subprocess.run(["powershell", "-NoProfile", "-Command", ps2],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("PID7256:", (r2.stdout or "").strip() or "dead")
