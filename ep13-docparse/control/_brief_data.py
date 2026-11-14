# -*- coding: utf-8 -*-
"""One-shot data pull for the ep13 progress brief. ASCII output only."""
import json, os, glob, random, statistics, hashlib, datetime, time, subprocess
from collections import Counter, defaultdict

ROOT = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(ROOT, "cells", "ep13-full-001")
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]
KNOWN_OUT = {"xiaomi_vl": {"shot_01", "table_01"}}   # already-diagnosed

man = json.load(open(os.path.join(ROOT, "samples", "manifest.json"), encoding="utf-8"))
img2sha = {s["img"]: s["sha256"] for s in man["samples"]}
sha2img = {v: k for k, v in img2sha.items()}
tasks = [(s["img"], e) for s in man["samples"] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != "oxr"]

st = json.load(open(os.path.join(ROOT, "control", "batch_state.json"), encoding="utf-8"))
seq_done = int(st["seq"].split("/")[0]); total = int(st["seq"].split("/")[1])
consumed = seq_done - 1

rows, files = [], sorted(glob.glob(os.path.join(CELLS, "*.json")))
for p in files:
    rows.append(json.load(open(p, encoding="utf-8")))

print("NOW", datetime.datetime.now().strftime("%H:%M:%S"))
print("STATE seq=%s current=%s n_run=%d n_skip=%d n_fail=%d last_progress=%s started_at=%s desired=%s" % (
    st["seq"], st["current"], st["n_run"], st["n_skip"], st["n_fail"],
    st["last_progress"], st["started_at"], st.get("desired")))
print("COUNT state_sum=%d consumed=%d files=%d" % (st["n_run"] + st["n_skip"] + st["n_fail"], consumed, len(rows)))

have = {}
for d in rows:
    have[((d.get("input") or {}).get("sha256"), d.get("engine"))] = d
gap = [(i, img, eng) for i, (img, eng) in enumerate(tasks[:consumed], 1)
       if (img2sha[img], eng) not in have]
print("GAP", gap)

eng_status = defaultdict(Counter)
for d in rows:
    eng_status[d.get("engine")][d.get("status")] += 1
print("STATUS_BY_ENGINE", {k: dict(v) for k, v in sorted(eng_status.items())})
print("TOTAL_STATUS", dict(Counter(d.get("status") for d in rows)))

cer = [(d["cer_median"], d.get("engine"), sha2img.get((d.get("input") or {}).get("sha256"), "?"))
       for d in rows if isinstance(d.get("cer_median"), (int, float))]
normal = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print("CER normal n=%d median=%.4f | outliers n=%d" % (
    len(normal), statistics.median([c[0] for c in normal]), len(out)))
for cer_v, e, img in out:
    tag = "KNOWN" if (e in KNOWN_OUT and img[:-4] in KNOWN_OUT[e]) else "NEW"
    print("   %s cer=%.4f %s x %s" % (tag, cer_v, e, img))

wall = [d["wall_median"] for d in rows if isinstance(d.get("wall_median"), (int, float))]
print("WALL n=%d median=%.1fs min=%.1f max=%.1f" % (
    len(wall), statistics.median(wall), min(wall), max(wall)))

# rates
mts = sorted(os.path.getmtime(f) for f in files)
now = time.time()
sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
sess_n = sum(1 for m in mts if m >= sess0)
sess_rate = (mts[-1] - sess0) / 60.0 / max(sess_n, 1)
all_rate = (mts[-1] - mts[0]) / 60.0 / (len(mts) - 1)
k = min(8, len(mts) - 1)
recent_rate = (mts[-1] - mts[-1 - k]) / 60.0 / k
rem = total - seq_done + 1
print("RATE session=%.2f all=%.2f recent%d=%.2f min/cell | remaining=%d" % (
    sess_rate, all_rate, k, recent_rate, rem))
print("ETA session=%.1fh recent=%.1fh all=%.1fh" % (
    sess_rate * rem / 60, recent_rate * rem / 60, all_rate * rem / 60))
print("LAST_FILE %s age=%.1f min | last_progress age=%.1f min" % (
    datetime.datetime.fromtimestamp(mts[-1]).strftime("%H:%M:%S"),
    (now - mts[-1]) / 60.0,
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st["last_progress"])).total_seconds() / 60.0))

# process
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner.py*' -and "
      "$_.Name -eq 'python.exe' } | ForEach-Object { $_.ProcessId.ToString() + '|' + "
      "$_.CreationDate.ToString('yyyy-MM-dd HH:mm:ss') }")
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
print("BATCH_PYTHON_PROCS", len(lines), lines)

# heartbeat freshness
hb = json.load(open(os.path.join(ROOT, "control", "heartbeat.json"), encoding="utf-8"))
print("HEARTBEAT", hb, "age_min=%.1f" % ((now - datetime.datetime.fromisoformat(hb["hb_at"]).timestamp()) / 60.0))
