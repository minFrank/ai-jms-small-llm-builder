import subprocess, datetime

print("NOW", datetime.datetime.now().isoformat(timespec="seconds"))

# owner pid from task.json
try:
    import json
    tid = json.load(open(r"D:/study/ai-jms/ep13-docparse/control/task.json", encoding="utf-8")).get("owner_pid")
except Exception as e:
    tid = None
    print("task read err", e)
print("owner_pid:", tid)

try:
    out = subprocess.run(["tasklist", "/FI", "PID eq %s" % tid], capture_output=True, text=True, timeout=60)
    print("tasklist pid:", (out.stdout or "").strip()[-300:], (out.stderr or "").strip()[:200])
except Exception as e:
    print("tasklist err", e)

ps = ('Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "batch_runner|runner.py|worker.py" } '
      '| ForEach-Object { "$($_.ProcessId) | $($_.Name) | $($_.CreationDate) | $($_.CommandLine)" }')
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=90)
    print("RUNNER_PROCS:\n" + (out.stdout.strip() or "(none)"))
    if out.stderr.strip():
        print("stderr:", out.stderr.strip()[:300])
except Exception as e:
    print("ps err", e)

# count python processes overall
try:
    out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=60)
    lines = [l for l in out.stdout.splitlines() if "python" in l.lower()]
    print("python procs:", len(lines))
    for l in lines:
        print("   ", l.strip())
except Exception as e:
    print("tasklist all err", e)
