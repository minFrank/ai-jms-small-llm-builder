import json, os, glob, statistics, datetime, subprocess
from collections import Counter, defaultdict

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
sha2sid = {s["sha256"]: s["sample_id"] for s in man["samples"]}

files = sorted(glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json")))
rows = []
for f in files:
    c = json.load(open(f, encoding="utf-8"))
    sha = (c.get("input") or {}).get("sha256")
    rows.append(dict(status=c["status"], engine=c["engine"],
                     cer=c.get("cer_median"), wall=c.get("wall_median"),
                     img=sha2img.get(sha, "?"), sid=sha2sid.get(sha, "?"),
                     mtime=os.path.getmtime(f), key=c["cell_key"]))

print("total_cells", len(rows), "expected 156")
out = [r for r in rows if r["cer"] is not None and r["cer"] >= 0.5]
out.sort(key=lambda r: -r["cer"])
print("outliers", len(out))
for r in out:
    print("  %.3f %s %s" % (r["cer"], r["engine"], r["img"]))

normal = [r["cer"] for r in rows if r["cer"] is not None and r["cer"] < 0.5]
print("normal_n", len(normal), "median", round(statistics.median(normal), 4))
walls = [r["wall"] for r in rows if r["wall"]]
print("wall_median", round(statistics.median(walls), 2), "min", round(min(walls),1), "max", round(max(walls),1))

# per engine status
eng = defaultdict(Counter)
for r in rows:
    eng[r["engine"]][r["status"]] += 1
for k in sorted(eng):
    print("ENG", k, dict(eng[k]))

# oldest/newest cell mtimes
mts = sorted(r["mtime"] for r in rows)
f = lambda t: datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S")
print("oldest_cell", f(mts[0]), "newest_cell", f(mts[-1]))

# pid check
for pid in (32504, 28156, 16776):
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "(Get-Process -Id %d -ErrorAction SilentlyContinue) -ne $null" % pid],
        capture_output=True, text=True)
    print("pid", pid, r.stdout.strip(), r.stderr.strip()[:80])

now = datetime.datetime.now()
print("now", now.strftime("%H:%M:%S"))
