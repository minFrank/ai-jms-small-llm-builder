# -*- coding: utf-8 -*-
import json, os, glob, datetime
EP = r"D:/study/ai-jms/ep13-docparse"
CELLS = os.path.join(EP, "cells", "ep13-full-001")
man = json.load(open(os.path.join(EP, "samples", "manifest.json"), encoding="utf-8"))
u2i = {s["sample_uuid"]: s["sample_id"] for s in man["samples"]}
now = datetime.datetime.now()
rows = []
for f in glob.glob(os.path.join(CELLS, "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    b = os.path.basename(f)
    mt = os.path.getmtime(os.path.join(CELLS, b))
    rows.append((d.get("cer_median"), d.get("engine"), u2i.get(b.split("__")[0], "?"),
                 datetime.datetime.fromtimestamp(mt), b))
out = sorted([r for r in rows if isinstance(r[0], float) and r[0] > 0.5], key=lambda r: r[3], reverse=True)
print("OUTLIERS_BY_MTIME(newest first):")
for cer, eng, smp, mt, b in out:
    print("  %s %-13s %-9s cer=%.4f age_min=%.0f" % (
        mt.strftime("%m-%d %H:%M"), eng, smp, cer, (now - mt).total_seconds() / 60))
recent = [r for r in rows if (now - r[3]).total_seconds() < 120]
print("CELLS_FINISHED_LAST_2MIN:", len(recent))
# heartbeat
for p in ["control/heartbeat.json", "control/task.json"]:
    fp = os.path.join(EP, p)
    if os.path.exists(fp):
        try:
            print(p, "=>", json.dumps(json.load(open(fp, encoding="utf-8")), ensure_ascii=False)[:600])
        except Exception as e:
            print(p, "ERR", e)
