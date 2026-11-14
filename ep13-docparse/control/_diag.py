import subprocess, datetime, json, os, glob

print("NOW", datetime.datetime.now().isoformat(timespec="seconds"))

# 1) owner pid alive?
tid = json.load(open(r"D:/study/ai-jms/ep13-docparse/control/task.json", encoding="utf-8")).get("owner_pid")
out = subprocess.run(["tasklist", "/FI", "PID eq %s" % tid], capture_output=True, timeout=60)
txt = out.stdout.decode("gbk", errors="replace")
print("PID %s ->" % tid, "ALIVE" if (" %s " % tid) in txt else "DEAD")
print("   ", txt.strip().splitlines()[-1] if txt.strip().strip() else "(empty)")

# 2) any ep13 runner process
ps = ('Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "ep13|batch" } '
      '| ForEach-Object { "$($_.ProcessId) | $($_.Name) | $($_.CreationDate) | $($_.CommandLine)" }')
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=90)
    t = out.stdout.decode("utf-8", errors="replace").strip()
    print("EPI3/BATCH PROCS:\n" + (t or "(none)"))
except Exception as e:
    print("ps err", e)

# 3) layout service 8081
import urllib.request
for url in ("http://127.0.0.1:8081/health", "http://127.0.0.1:8081/"):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        print("8081", url, "->", r.status, r.read()[:200])
        break
    except Exception as e:
        print("8081", url, "-> ERR", type(e).__name__, str(e)[:120])

# 4) model dirs
for d in (r"D:/models/models/ocr/ep13-docparse/OXR-Doc",
          r"D:/models/models/ocr/ep13-docparse"):
    print(d, "exists:", os.path.isdir(d))
    if os.path.isdir(d):
        print("   ", sorted(os.listdir(d))[:12])

# 5) recent run logs
for pat in (r"D:/study/ai-jms/ep13-docparse/runs/*", r"D:/study/ai-jms/ep13-docparse/sessions/*"):
    items = sorted(glob.glob(pat), key=os.path.getmtime, reverse=True)[:8]
    print("LOGS", pat, [os.path.basename(i) for i in items])
