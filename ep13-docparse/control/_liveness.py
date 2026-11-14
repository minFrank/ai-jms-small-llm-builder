# -*- coding: utf-8 -*-
import json, os, glob, datetime, subprocess, collections

base = r"D:/study/ai-jms/ep13-docparse"
now = datetime.datetime.now()
print("NOW:", now.isoformat(timespec="seconds"))
for n in ("batch_state.json", "heartbeat.json", "task.json"):
    p = os.path.join(base, "control", n)
    print(n, "mtime:", datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%H:%M:%S"),
          "->", open(p, encoding="utf-8").read().strip())

files = glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json"))
mts = sorted((os.path.getmtime(f), f) for f in files)
print("cells:", len(files), "latest 5:")
for t, f in mts[-5:]:
    print("   ", datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M:%S"), os.path.basename(f))
print("age of newest cell (min): %.1f" % ((now.timestamp() - mts[-1][0]) / 60))

# is 19676 alive?
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          'if (Get-Process -Id 19676 -ErrorAction SilentlyContinue) { "ALIVE" } else { "DEAD" }'],
                         capture_output=True, text=True, timeout=60)
    print("pid19676:", out.stdout.strip(), out.stderr.strip()[:200])
except Exception as e:
    print("ps err", e)

# all runner/worker processes
out = subprocess.run(["powershell", "-NoProfile", "-Command",
    'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "scripts.(runner|worker|batch_runner).py" } | ForEach-Object { "$($_.ProcessId) | $($_.CreationDate) | $($_.Name)" }'],
    capture_output=True, text=True, timeout=60)
print("runner/worker/batch procs:\n" + out.stdout.strip())
