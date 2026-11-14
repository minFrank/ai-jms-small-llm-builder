# -*- coding: utf-8 -*-
"""离群格诊断：gt_v/gt_hash/字段结构 + 与已知离群对照。只读。"""
import json, os, glob, collections, datetime

EP = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(EP, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}

cells = []
for p in sorted(glob.glob(os.path.join(EP, "cells", "ep13-full-001", "*.json"))):
    try:
        c = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    if c.get("input", {}).get("sha256") not in sha2img:
        continue
    c["_p"] = p
    c["_mt"] = os.path.getmtime(p)
    cells.append(c)

latest = {}
for c in cells:
    k = (sha2img[c["input"]["sha256"]], c.get("engine"))
    if k not in latest or c["_mt"] > latest[k]["_mt"]:
        latest[k] = c

print("n latest:", len(latest))
print("gt_v:", collections.Counter(c.get("gt_v") for c in latest.values()))
print("gt_hash:", collections.Counter(str(c.get("gt_hash"))[:20] for c in latest.values()))
print("status:", collections.Counter(c.get("status") for c in latest.values()))
print("fingerprint keys:", sorted(latest[list(latest)[0]].keys()))

# 一个正常格的指标字段结构
sample = latest[("book_01.png", "xiaomi_vl")] if ("book_01.png", "xiaomi_vl") in latest else latest[list(latest)[0]]
print("== metric-ish fields of", sample.get("engine"), sha2img.get(sample["input"]["sha256"]))
for k, v in sample.items():
    if k in ("text", "pages", "pred", "paras"):
        print("  %s: <len %s>" % (k, len(v) if hasattr(v, "__len__") else "?"))
    else:
        s = json.dumps(v, ensure_ascii=False)
        print("  %s: %s" % (k, s[:300]))

# 离群明细（含 gt_v、wall、样本 mtime）
print("== OUTLIERS >=0.5")
rows = []
for (img, eng), c in latest.items():
    cer = c.get("cer_median")
    if isinstance(cer, (int, float)) and cer >= 0.5:
        rows.append((cer, eng, img, c.get("gt_v"), str(c.get("gt_hash"))[:16],
                     c.get("wall_median"), datetime.datetime.fromtimestamp(c["_mt"]).strftime("%m-%d %H:%M")))
for r in sorted(rows, reverse=True):
    print("  cer=%.3f %s %s gt_v=%s gt_hash=%s wall=%s mtime=%s" % r)

# 每引擎 CER 中位（正常格）+ 每引擎 wall 中位
import statistics
print("== per-engine (normal <0.5)")
byeng = collections.defaultdict(list)
wbyeng = collections.defaultdict(list)
for (img, eng), c in latest.items():
    cer = c.get("cer_median")
    if isinstance(cer, (int, float)) and cer < 0.5:
        byeng[eng].append(cer)
    w = c.get("wall_median")
    if isinstance(w, (int, float)):
        wbyeng[eng].append(w)
for eng in sorted(set(list(byeng) + list(wbyeng))):
    n = len(byeng[eng])
    med = statistics.median(byeng[eng]) if n else None
    wmed = statistics.median(wbyeng[eng]) if wbyeng[eng] else None
    print("  %-14s normal_n=%-3d cer_med=%s wall_med=%s" % (eng, n, round(med, 4) if med else "-", wmed))
