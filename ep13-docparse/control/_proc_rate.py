import subprocess, glob, os, datetime

q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and "
     "$_.CommandLine -like '*batch_runner*' } | ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }")
r = subprocess.run(["powershell", "-NoProfile", "-Command", q],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
print("BATCH_RUNNER_PYTHON_PROCS:", len(lines))
for l in lines:
    print("  ", l[:220])
if r.stderr:
    print("stderr:", r.stderr[:300])

fs = glob.glob(r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001/*.json")
mts = sorted(os.path.getmtime(p) for p in fs)
cut = datetime.datetime(2026, 11, 6, 8, 0).timestamp()
sel = [m for m in mts if m >= cut]
span = (sel[-1] - sel[0]) / 60
print("since0800 n=%d span=%.1fmin rate=%.2f min/cell  window=%s->%s" % (
    len(sel), span, span / max(1, len(sel) - 1),
    datetime.datetime.fromtimestamp(sel[0]).strftime("%H:%M"),
    datetime.datetime.fromtimestamp(sel[-1]).strftime("%H:%M")))
k = min(8, len(mts) - 1)
print("recent8=%.2f min/cell" % ((mts[-1] - mts[-1 - k]) / 60 / k))
print("NOW", datetime.datetime.now().strftime("%H:%M:%S"))
