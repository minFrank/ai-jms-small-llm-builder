# -*- coding: utf-8 -*-
import json, os, glob, datetime, collections, statistics

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples", "manifest.json"), encoding="utf-8"))
sha2id = {s["sha256"]: s["sample_id"] for s in man["samples"]}
st = json.load(open(os.path.join(base, "control", "batch_state.json"), encoding="utf-8"))
started = datetime.datetime.fromisoformat(st["started_at"])

files = glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json"))
rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    d["_mt"] = os.path.getmtime(f)
    rows.append(d)
rows.sort(key=lambda r: r["_mt"])

thisrun = [r for r in rows if datetime.datetime.fromtimestamp(r["_mt"]) >= started]
print("THIS RUN cells (%d):" % len(thisrun))
for r in thisrun:
    print("  %s | %-13s | %-11s | %s" % (
        datetime.datetime.fromtimestamp(r["_mt"]).strftime("%m-%d %H:%M"),
        r["engine"], sha2id.get(r["input"]["sha256"], "?"), r["status"]))

# lc_01 monkey cell detail
for r in rows:
    if r["engine"] == "monkey_rec" and sha2id.get(r["input"]["sha256"]) == "lc_01":
        print("LC01 MONKEY:", json.dumps({k: r[k] for k in
              ("status", "cer_median", "n_attempt", "n_valid", "n_fail", "trunc_rate",
               "cell_success_rate", "unstable", "err", "err_kind", "wall_median")},
              ensure_ascii=False))
        print("  reps:", [(x["n"], x["status"], round(x.get("cer") or -1, 3), x.get("truncated")) for x in r["reps"]])

# all lc_01 cells
print("LC_01 all engines:")
for r in sorted([x for x in rows if sha2id.get(x["input"]["sha256"]) == "lc_01"], key=lambda x: x["cer_median"] or 0):
    print("   %-13s cer=%.3f trunc=%.2f valid=%s status=%s" % (
        r["engine"], r.get("cer_median") or -1, r.get("trunc_rate") or 0, r.get("n_valid"), r["status"]))

# oxr fail times
oxr = [r for r in rows if r["engine"] == "oxr"]
print("OXR cells: %d, time range: %s -> %s" % (
    len(oxr),
    datetime.datetime.fromtimestamp(min(r["_mt"] for r in oxr)).strftime("%m-%d %H:%M"),
    datetime.datetime.fromtimestamp(max(r["_mt"] for r in oxr)).strftime("%m-%d %H:%M")))
print("oxr sample ids:", sorted(sha2id.get(r["input"]["sha256"], "?") for r in oxr))
e = oxr[0].get("err")
print("oxr first err:", str(e)[:300], "| err_kind:", oxr[0].get("err_kind"), "| n_attempt:", oxr[0].get("n_attempt"), "n_valid:", oxr[0].get("n_valid"))

# monkey this-run cells rate
mon = [r for r in thisrun if r["engine"] == "monkey_rec"]
if mon:
    t0 = started.timestamp()
    t1 = mon[-1]["_mt"]
    print("monkey thisrun: %d cells over %.2f h -> %.1f min/cell" % (
        len(mon), (t1 - t0) / 3600, (t1 - t0) / 60 / len(mon)))
    for r in mon:
        print("   ", datetime.datetime.fromtimestamp(r["_mt"]).strftime("%m-%d %H:%M"),
              sha2id.get(r["input"]["sha256"], "?"), round(r["cer_median"], 3))
