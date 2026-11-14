# -*- coding: utf-8 -*-
"""查 batch_runner / runner 子进程存活（经 powershell 子进程，只读）。"""
import subprocess

q = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "
     "'batch_runner|scripts.runner.py' } | ForEach-Object "
     "{ '{0}|{1}|{2}' -f $_.ProcessId, $_.CreationDate, $_.Name }")
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", q],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=90)
    print("STDOUT:")
    print(out.stdout.strip() or "(empty)")
    print("STDERR:", out.stderr.strip()[:300])
except Exception as e:
    print("ERR:", e)
