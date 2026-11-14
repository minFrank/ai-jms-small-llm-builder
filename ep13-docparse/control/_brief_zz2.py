# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r"D:/study/ai-jms/ep13-docparse"
CELLD = f"{BASE}/cells/ep13-full-001"
man = json.load(open(f"{BASE}/samples/manifest.json", encoding="utf-8"))
u2name = {}
for s in man["samples"]:
    u2name[s["sample_uuid"]] = (s["sample_id"], s["img"])

rows = []
for f in sorted(glob.glob(f"{CELLD}/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(f))
    sid = d.get("sample_id")
    name, img = u2name.get(sid, (sid, "?"))
    rows.append(dict(file=os.path.basename(f), st=d.get("status"), eng=d.get("engine"),
                     cer=d.get("cer_median"), wall=d.get("wall_median"),
                     sid=sid, name=name, img=img, mt=mt, err=d.get("err"),
                     n_attempt=d.get("n_attempt"), n_valid=d.get("n_valid")))

rows.sort(key=lambda r: -r["mt"].timestamp())
print("== 最近 30 格 (mtime desc) ==")
for r in rows[:30]:
    print("  %s %s %s cer=%s wall=%s err=%s" % (r["mt"].strftime("%m-%d %H:%M"), r["eng"], r["name"], r["cer"], r["wall"], r["err"]))

# batch window: last contiguous tail where gap > 3h marks session? just show distribution by hour
from collections import Counter
print("\n== 按小时分布(今日) ==")
c = Counter(r["mt"].strftime("%m-%d %H") for r in rows)
for k in sorted(c):
    if k.startswith("11-06") or k.startswith("11-05"):
        print("  ", k, c[k])

# this batch = cells finished in final session: define session start = last time before gap>6h
gaps = [(rows[i]["mt"] - rows[i+1]["mt"]).total_seconds() for i in range(len(rows)-1)]
big = [(i, g) for i, g in enumerate(gaps) if g > 6*3600]
print("\ngaps>6h at idx (desc order):", [(i, round(g/3600,1), rows[i]["mt"].strftime("%m-%d %H:%M"), rows[i+1]["mt"].strftime("%m-%d %H:%M")) for i, g in big])

# failed cells detail
fails = [r for r in rows if r["st"] != "complete"]
print("\n== FAILED %d ==" % len(fails))
for r in sorted(fails, key=lambda x: x["name"]):
    print("  %s | %s | err=%s n_attempt=%s n_valid=%s mtime=%s" % (r["name"], r["eng"], r["err"], r["n_attempt"], r["n_valid"], r["mt"].strftime("%m-%d %H:%M")))

# outliers with names
out = [r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5]
out.sort(key=lambda r: -r["cer"])
print("\n== OUTLIERS CER>=0.5 : %d ==" % len(out))
for r in out:
    print("  %.4f | %s | %s (%s) | mtime=%s" % (r["cer"], r["eng"], r["name"], r["img"], r["mt"].strftime("%m-%d %H:%M")))

ok = [r for r in rows if isinstance(r["cer"], (int, float))]
normal = [r["cer"] for r in ok if r["cer"] < 0.5]
print("\nnormal n=%d median=%.4f" % (len(normal), statistics.median(normal)))
print("wall median all=%.1f" % statistics.median([r["wall"] for r in ok]))
# outlier count per engine
print("outlier per engine:", dict(Counter(r["eng"] for r in out)))
print("complete per engine:", dict(Counter(r["eng"] for r in rows if r["st"]=="complete")))
# normal median per engine
for e in sorted(set(r["eng"] for r in rows)):
    v = [r["cer"] for r in ok if r["eng"]==e and r["cer"]<0.5]
    if v:
        print("  normal median %s n=%d %.4f" % (e, len(v), statistics.median(v)))
