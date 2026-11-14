# -*- coding: utf-8 -*-
import json, os, glob, datetime, collections, statistics

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2id = {s["sha256"]: s["sample_id"] for s in man["samples"]}
st = json.load(open(os.path.join(base, "control", "batch_state.json"), encoding="utf-8"))
hb = json.load(open(os.path.join(base, "control", "heartbeat.json"), encoding="utf-8"))
tk = json.load(open(os.path.join(base, "control", "task.json"), encoding="utf-8"))
now = datetime.datetime.now()
lp = datetime.datetime.fromisoformat(st["last_progress"])
print("NOW:", now.strftime("%H:%M:%S"))
print("STATE:", json.dumps(st, ensure_ascii=False))
print("HB:", json.dumps(hb, ensure_ascii=False), "| TASK:", json.dumps(tk, ensure_ascii=False))
print("last_progress age min: %.1f" % ((now - lp).total_seconds() / 60))

files = glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json"))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_mt"] = os.path.getmtime(f)
    rows.append(d)
print("cells=%d complete=%d failed=%d" % (
    len(rows), sum(1 for r in rows if r["status"] == "complete"),
    sum(1 for r in rows if r["status"] == "failed")))
print("state counters: run+skip+fail=%d ; seq=%s" % (
    st["n_run"] + st["n_skip"] + st["n_fail"], st["seq"]))
print("engine:", {e: dict(c) for e, c in
      ((e, collections.Counter(r["status"] for r in rows if r["engine"] == e))
       for e in sorted({r["engine"] for r in rows}))})

cerc = [r["cer_median"] for r in rows if isinstance(r.get("cer_median"), (int, float))]
norm = [c for c in cerc if c < 0.5]
print("CER normal n=%d median %.4f | all n=%d median %.4f" % (
    len(norm), statistics.median(norm), len(cerc), statistics.median(cerc)))
walls = [r["wall_median"] for r in rows if isinstance(r.get("wall_median"), (int, float))]
print("wall median %.1fs (n=%d)" % (statistics.median(walls), len(walls)))

outl = []
for r in rows:
    c = r.get("cer_median")
    if isinstance(c, (int, float)) and c >= 0.5:
        outl.append((c, r["engine"], sha2id.get(r["input"]["sha256"], "?"),
                     datetime.datetime.fromtimestamp(r["_mt"])))
cut = datetime.datetime.fromisoformat("2026-11-06T22:21:00")
new = [o for o in outl if o[3] >= cut]
print("outliers total=%d | since22:21=%d" % (len(outl), len(new)))
for c, e, s, t in sorted(outl, key=lambda x: -x[0]):
    tag = "NEW" if t >= cut else ("EXEMPT" if (e, s) in (("xiaomi_vl", "shot_01"), ("xiaomi_vl", "table_01")) else "old")
    print("   %.3f | %-13s | %-11s | %s | %s" % (c, e, s, t.strftime("%m-%d %H:%M"), tag))

# rates
started = datetime.datetime.fromisoformat(st["started_at"])
res = int(st["seq"].split("/")[1]) - int(st["seq"].split("/")[0])
print("remaining seq units:", res)
# batch rate since 22:21 process start
b0 = datetime.datetime.fromisoformat("2026-11-06T22:21:10")
nb = sum(1 for r in rows if datetime.datetime.fromtimestamp(r["_mt"]) >= b0)
nb_real = sum(1 for r in rows if datetime.datetime.fromtimestamp(r["_mt"]) >= b0 and r["status"] == "complete")
mins = (now - b0).total_seconds() / 60
print("since 22:21: cells=%d (complete=%d) over %.1f min -> all %.1f min/cell, real %.1f min/cell" % (
    nb, nb_real, mins, mins / nb, mins / nb_real))
# gaps among monkey cells in batch
mon = sorted(r["_mt"] for r in rows if r["engine"] == "monkey_rec" and datetime.datetime.fromtimestamp(r["_mt"]) >= b0)
if len(mon) > 1:
    g = [(mon[i] - mon[i - 1]) / 60 for i in range(1, len(mon))]
    print("monkey batch gaps:", [round(x, 1) for x in g], "median %.1f" % statistics.median(g))
# ETA
print("ETA @batch-all rate: %.1f h | @monkey-real rate: %.1f h" % (
    res * (mins / nb) / 60, res * (mins / nb_real) / 60))
