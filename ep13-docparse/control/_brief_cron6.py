import json, glob, os, collections, statistics, datetime, time

BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
u2img = {s["sample_uuid"]: s["img"] for s in man["samples"]}

fs = glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json"))
rows = []
for f in fs:
    d = json.load(open(f, encoding="utf-8"))
    uid = os.path.basename(f).split("__")[0]
    d["_img"] = u2img.get(uid, uid[:8])
    d["_mt"] = os.path.getmtime(f)
    rows.append(d)

st = json.load(open(os.path.join(BASE, "control/batch_state.json"), encoding="utf-8"))
hb = json.load(open(os.path.join(BASE, "control/heartbeat.json"), encoding="utf-8"))
tk = json.load(open(os.path.join(BASE, "control/task.json"), encoding="utf-8"))

cnt = collections.Counter(r["status"] for r in rows)
eng = collections.defaultdict(collections.Counter)
for r in rows:
    eng[r["engine"]][r["status"]] += 1

cer_ok = [r["cer_median"] for r in rows
          if r["status"] == "complete" and isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] < 0.5]
wall = [r["wall_median"] for r in rows if r["status"] == "complete" and isinstance(r.get("wall_median"), (int, float))]
outs = sorted([r for r in rows
               if r["status"] == "complete" and isinstance(r.get("cer_median"), (int, float)) and r["cer_median"] >= 0.5],
              key=lambda r: -r["cer_median"])
known = {("xiaomi_vl", "shot_01.png"), ("xiaomi_vl", "table_01.png")}

now = time.time()
last_mt = max(r["_mt"] for r in rows)
mts = sorted(r["_mt"] for r in rows)
gap20 = (mts[-1] - mts[-20]) / 60 / 19

print("NOW", datetime.datetime.fromtimestamp(now).strftime("%H:%M"))
print("STATE", json.dumps(st, ensure_ascii=False))
print("HB", json.dumps(hb, ensure_ascii=False))
print("TASK", json.dumps(tk, ensure_ascii=False))
print("NCELLS", len(rows), dict(cnt))
for e in sorted(eng):
    print("ENG", e, dict(eng[e]), "n=", sum(eng[e].values()))
print("CER_OK n=%d median=%.4f" % (len(cer_ok), statistics.median(cer_ok)))
print("WALL n=%d median=%.1f" % (len(wall), statistics.median(wall)))
print("OUTLIERS n=%d" % len(outs))
for r in outs:
    tag = "KNOWN" if (r["engine"], r["_img"]) in known else "-"
    print("   %.3f %s %s %s %s" % (r["cer_median"], r["engine"], r["_img"], tag,
                                   datetime.datetime.fromtimestamp(r["_mt"]).strftime("%m-%d %H:%M")))
print("LAST_CELL", datetime.datetime.fromtimestamp(last_mt).strftime("%m-%d %H:%M"),
      "age_min=%.0f" % ((now - last_mt) / 60))
print("RATE_last20_min_per_cell=%.2f" % gap20)
print("WRITTEN_last6h", sum(1 for t in mts if now - t < 6 * 3600))

fails = [r for r in rows if r["status"] != "complete"]
print("FAILED n=%d" % len(fails))
for r in sorted(fails, key=lambda x: x["_img"]):
    print("   ", r["engine"], r["_img"], r.get("err"), "attempt=", r.get("n_attempt"))

# batch_state seq meaning
print("SEQ", st.get("seq"), "n_run", st.get("n_run"), "n_skip", st.get("n_skip"), "n_fail", st.get("n_fail"),
      "current", st.get("current"), "desired", st.get("desired"), "finished_at", st.get("finished_at"))
print("last_progress_age_min=%.0f" % ((now - time.mktime(time.strptime(st["last_progress"], "%Y-%m-%dT%H:%M:%S"))) / 60))
