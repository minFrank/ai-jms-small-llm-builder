# -*- coding: utf-8 -*-
import json, glob, os, sys, io, statistics, datetime, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = r"D:/study/ai-jms/ep13-docparse"
files = glob.glob(B + "/cells/ep13-full-001/*.json")
mts = sorted(os.path.getmtime(f) for f in files)
gaps = [(mts[i+1]-mts[i])/60 for i in range(len(mts)-1)]
g30 = gaps[-30:]
print("last30 gap: median=%.2f mean=%.2f max=%.2f" % (statistics.median(g30), statistics.mean(g30), max(g30)))
print("last10 gaps:", [round(g,1) for g in gaps[-10:]])
print("last cell:", datetime.datetime.fromtimestamp(mts[-1]).strftime("%m-%d %H:%M:%S"))
sess0 = datetime.datetime(2026, 11, 5, 6, 50, 31).timestamp()
before = sum(1 for m in mts if m < sess0)
print("files before session(11-05 06:50:31):", before, "| since:", len(mts)-before)
# errors
errs = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    if d.get("err") or d.get("err_kind"):
        errs.append((d.get("engine"), str(d.get("err"))[:60], d.get("err_kind")))
print("cells with err:", len(errs), errs[:5])
uns = [json.load(open(f, encoding='utf-8')) for f in files if json.load(open(f, encoding='utf-8')).get('unstable')]
print("unstable:", [(d.get('engine'), d.get('cell_success_rate')) for d in uns])
# outlier concentration
man = json.load(open(B + "/samples/manifest.json", encoding="utf-8"))
uuid2img = {s["sample_uuid"]: s["img"] for s in man["samples"]}
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
from collections import Counter
out_by_sample = Counter()
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    cer = d.get("cer_median")
    if isinstance(cer, (int, float)) and cer >= 0.5:
        img = uuid2img.get(d.get("sample_id")) or sha2img.get((d.get("input") or {}).get("sha256"), "?")
        out_by_sample[img] += 1
print("outlier by sample:", dict(out_by_sample.most_common()))
# per engine done vs 26
eng = Counter(json.load(open(f, encoding='utf-8')).get('engine') for f in files)
print("per-engine files (expect 26 each):", dict(eng))
