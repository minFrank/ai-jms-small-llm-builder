import json, glob, os, statistics, datetime, collections

ROOT = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(ROOT, "samples/manifest.json"), encoding="utf-8"))
uuid2img = {s["sample_uuid"]: s["img"] for s in man["samples"]}
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}

cells = sorted(glob.glob(os.path.join(ROOT, "cells/ep13-full-001/*.json")))
rows = []
for f in cells:
    d = json.load(open(f, encoding="utf-8"))
    base = os.path.basename(f)
    uuid, eng = base.split("__")[0], base.split("__")[1]
    sha = (d.get("input") or {}).get("sha256")
    rows.append(dict(
        f=base, uuid=uuid, img=uuid2img.get(uuid) or sha2img.get(sha, "?"),
        eng=eng, status=d.get("status"), cer=d.get("cer_median"),
        wall=d.get("wall_median"), sha=sha, reps=d.get("n_rep") or d.get("reps"),
        err=str(d.get("err") or "")[:160], mt=os.path.getmtime(f),
        keys=sorted(d.keys()),
    ))

print("KEYS_SAMPLE", rows[0]["keys"])
print("status:", collections.Counter(r["status"] for r in rows))
print("eng:", collections.Counter(r["eng"] for r in rows))

# outliers >=0.5
outs = sorted([r for r in rows if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5],
              key=lambda r: -r["cer"])
print("\nOUTLIERS n=%d" % len(outs))
for r in outs:
    print("  %.3f  %-12s %-16s %-8s reps=%s mtime=%s" % (
        r["cer"], r["eng"], r["img"], r["status"], r["reps"],
        datetime.datetime.fromtimestamp(r["mt"]).strftime("%m-%d %H:%M")))

# known
known = {("xiaomi_vl", "shot_01"), ("xiaomi_vl", "table_01")}
print("\nKNOWN present:", [ (round(r['cer'],3), r['eng'], r['img']) for r in outs if (r['eng'], r['img']) in known ])

# median per engine on complete cells with cer<0.5
print("\nPER ENGINE (complete): n, median cer (<0.5), median wall s")
by = collections.defaultdict(list)
for r in rows:
    if r["status"] == "complete":
        by[r["eng"]].append(r)
for e, rs in sorted(by.items()):
    ok = [r["cer"] for r in rs if isinstance(r["cer"], (int, float)) and r["cer"] < 0.5]
    w = [r["wall"] for r in rs if isinstance(r["wall"], (int, float))]
    o = sum(1 for r in rs if isinstance(r["cer"], (int, float)) and r["cer"] >= 0.5)
    print("  %-12s n=%2d ok=%2d out=%2d med_cer=%s med_wall=%.1fs" % (
        e, len(rs), len(ok), o,
        ("%.4f" % statistics.median(ok)) if ok else "-",
        statistics.median(w) if w else -1))

all_ok = [r["cer"] for r in rows if r["status"] == "complete" and isinstance(r["cer"], (int, float)) and r["cer"] < 0.5]
all_w = [r["wall"] for r in rows if isinstance(r["wall"], (int, float))]
print("\nALL med_cer(<0.5)=%.4f n=%d ; med_wall=%.1fs (%.2f min) n=%d" % (
    statistics.median(all_ok), len(all_ok), statistics.median(all_w),
    statistics.median(all_w)/60, len(all_w)))

# failed cells detail
print("\nFAILED cells:")
for r in rows:
    if r["status"] != "complete":
        print("  %-12s %-16s %s | err=%s" % (r["eng"], r["img"], r["status"], r["err"]))

# rate from mtime of last N cells
mts = sorted(r["mt"] for r in rows)
now = datetime.datetime.now().timestamp()
print("\nnewest cell mtime:", datetime.datetime.fromtimestamp(mts[-1]).isoformat(),
      " age_min=%.1f" % ((now - mts[-1]) / 60))
for n in (10, 20, 50):
    if len(mts) > n:
        span = (mts[-1] - mts[-n]) / 60
        print("last %d cells: %.1f min total = %.2f min/cell" % (n, span, span/(n-1)))
