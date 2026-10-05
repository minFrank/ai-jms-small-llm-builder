"""色彩鲜艳度量化:per 方案计算 HSV 饱和度(S)与色相多样性。

你的观察「diffusers 色彩更鲜艳」→ 客观口径:
  鲜艳度 = 非灰像素的平均饱和度 S∈[0,1](越接近 1 越艳)
  色相跨度 = 有效色相 H 的四分位距(颜色是否单一)
只统计 p{p}_s{seed} 新批图(每方案 6 张 = 2 prompt × 3 seed)。
"""
import colorsys
import json
import os
import re
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image  # noqa: E402

OUT4 = r"D:/models/txt2img/out4"
SCHEMES = ["sdcpp-cpu", "sdcpp-vulkan", "diffusers"]


def metrics(path, step=7):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    sats, hues = [], []
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = [v / 255 for v in px[x, y]]
            hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
            if vv < 0.06:          # 近黑不算
                continue
            if ss > 0.05:          # 近灰不算
                sats.append(ss)
                hues.append(hh)
    if not sats:
        return None
    return {
        "sat_mean": statistics.mean(sats),
        "sat_median": statistics.median(sats),
        "sat_std": statistics.pstdev(sats) if len(sats) > 1 else 0,
        "hue_iqr": (statistics.quantiles(hues, n=4)[2]
                    - statistics.quantiles(hues, n=4)[0]) if len(hues) >= 8 else 0,
        "n": len(sats),
    }


print(f"{'方案':<16} {'样本':>4} {'鲜艳度(平均S)':>14} {'中位S':>8} {'色相IQR':>9}")
print("-" * 60)
allm = {}
for sc in SCHEMES:
    files = sorted(f for f in os.listdir(OUT4)
                   if f.startswith(sc + "_p") and "_s" in f and f.endswith(".png"))
    vals = []
    for f in files:
        m = metrics(os.path.join(OUT4, f))
        if m:
            vals.append(m)
    if not vals:
        print(f"{sc:<16} (新批图还没有)")
        continue
    sm = statistics.mean(v["sat_mean"] for v in vals)
    md = statistics.mean(v["sat_median"] for v in vals)
    iq = statistics.mean(v["hue_iqr"] for v in vals)
    allm[sc] = {"n": len(vals), "sat_mean": round(sm, 4),
                "sat_median": round(md, 4), "hue_iqr": round(iq, 4),
                "per_file": {f: None for f in files}}
    print(f"{sc:<16} {len(vals):>4} {sm:>14.3f} {md:>8.3f} {iq:>9.3f}")

if len(allm) == 3:
    best = max(allm, key=lambda k: allm[k]["sat_mean"])
    worst = min(allm, key=lambda k: allm[k]["sat_mean"])
    print(f"\n鲜艳度排序: {best} 最艳({allm[best]['sat_mean']:.3f}) > "
          + " > ".join(k for k in sorted(allm, key=lambda k: -allm[k]['sat_mean'])
                       if k not in (best, worst))
          + f" > {worst}({allm[worst]['sat_mean']:.3f})")
    out = os.path.join(r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs",
                       "color_metrics.json")
    json.dump(allm, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved ->", out)
