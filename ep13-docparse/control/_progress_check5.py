# -*- coding: utf-8 -*-
import json, os, glob, sys, io, datetime, statistics, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = r"D:/study/ai-jms/ep13-docparse"
st = json.load(open(B + "/control/batch_state.json", encoding="utf-8"))
files = glob.glob(B + "/cells/ep13-full-001/*.json")
now = datetime.datetime.now()
print("NOW", now.strftime("%H:%M:%S"))
print("seq=%s run=%d skip=%d fail=%d sum=%d" % (st["seq"], st["n_run"], st["n_skip"], st["n_fail"], st["n_run"]+st["n_skip"]+st["n_fail"]))
print("last_progress", st["last_progress"], "age_min=%.1f" % ((now - datetime.datetime.fromisoformat(st["last_progress"])).total_seconds()/60))
print("finished_at", st.get("finished_at"), "desired", st.get("desired"), "current", st.get("current", "<absent>"))
print("files", len(files), "run+skip", st["n_run"]+st["n_skip"], "diff", st["n_run"]+st["n_skip"]-len(files))
mts = sorted(os.path.getmtime(f) for f in files)
print("last cell mtime", datetime.datetime.fromtimestamp(mts[-1]).strftime("%H:%M:%S"))
k = 30
print("rate last%d = %.2f min/cell" % (k, (mts[-1]-mts[-1-k])/60/k))
rem = 130 - len(files)
print("remaining %d cells -> %.1f h at last30 rate" % (rem, rem*(mts[-1]-mts[-1-k])/60/k/60))
hb = json.load(open(B + "/control/heartbeat.json", encoding="utf-8"))
print("heartbeat", hb, "age_s=%.0f" % (time.time()-datetime.datetime.fromisoformat(hb["hb_at"]).timestamp()))
tj = json.load(open(B + "/control/task.json", encoding="utf-8"))
print("task.json", tj)
