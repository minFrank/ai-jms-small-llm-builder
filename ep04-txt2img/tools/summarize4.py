"""三方案汇总:sd.cpp-CPU / sd.cpp-Vulkan / diffusers → 表 + 并排图。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
LOG = os.path.join(E, "logs", "bench4-progress.json")
OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai-ep09"

d = json.load(open(LOG, encoding="utf-8"))
rows = [r for r in d["rows"] if "_s" in r.get("cell", "")]  # 只用空载干净批
print(f"总 {len(rows)} 格,方案:", sorted({r['scheme'] for r in rows}))

# ---- 按方案聚合 ----
agg = {}
for r in rows:
    a = agg.setdefault(r["scheme"], {"t": [], "m": [], "ok": 0, "n": 0, "err": []})
    a["n"] += 1
    a["t"].append(r["seconds"])
    if r.get("mem_peak"):
        a["m"].append(r["mem_peak"])
    if r["ok"]:
        a["ok"] += 1
    else:
        a["err"].append(r.get("err", "")[:120])

print("\n=== 汇总表 ===")
print(f"{'方案':<14} {'出图':>5} {'单图耗时(秒)':>18} {'峰值内存':>10} {'净出网':>6}")
order = ["sdcpp-cpu", "sdcpp-vulkan", "diffusers"]
for s in order:
    a = agg.get(s)
    if not a:
        continue
    tmin, tmax = min(a["t"]), max(a["t"])
    mem = max(a["m"]) / 1048576 if a["m"] else 0
    print(f"{s:<16} {a['ok']}/{a['n']:<3} {f'{tmin:.0f}–{tmax:.0f}':>18} "
          f"{f'{mem:.0f} MB':>10} {'0':>6}")

# ---- 关键对比 ----
import statistics
cpu = statistics.mean([r["seconds"] for r in rows if r["scheme"] == "sdcpp-cpu"])
vk = statistics.mean([r["seconds"] for r in rows if r["scheme"] == "sdcpp-vulkan"])
df = statistics.mean([r["seconds"] for r in rows if r["scheme"] == "diffusers"])
print(f"\n均值: CPU {cpu:.0f}s | Vulkan {vk:.0f}s | diffusers {df:.0f}s")
print(f"核显 vs CPU: {cpu/vk:.2f}× 快")
print(f"sd.cpp-CPU vs diffusers: {df/cpu:.2f}× (diffusers 相对倍数)")

# ---- 每方案的 4 张图 ----
schemes = [s for s in order if s in agg]
groups = {}
for r in rows:
    if r["ok"]:
        groups.setdefault((r["prompt_idx"], r["run_idx"]), {})[r["scheme"]] = \
            os.path.join(r"D:/models/txt2img/out4", r["cell"] + ".png")

# ---- 并排对比图(PIL)----
from PIL import Image, ImageDraw, ImageFont
MSYH, MSYHB = "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"
f = lambda sz: ImageFont.truetype(MSYH, sz)  # noqa: E731


def fb(sz):
    try:
        return ImageFont.truetype(MSYYB := MSYHB, sz)
    except Exception:
        return ImageFont.truetype(MSYH, sz)


PROMPT_TAG = {0: "湖畔清晨", 1: "窗边木桌"}
BG, INK, DIM = (255, 255, 255), (34, 38, 45), (122, 130, 140)
BLUE = (15, 76, 129)
CELL = 512
pad, gap, top = 30, 12, 110
W = pad * 2 + CELL * 3 + gap * 2
H = top + 56 + (CELL + 40) * 2 + pad
im = Image.new("RGB", (W, H), BG)
dr = ImageDraw.Draw(im)
dr.text((pad, 26), "三方案同题同种子并排（seed 42 · 512×512 · 20 步）",
        font=fb(30), fill=INK)
dr.text((pad, 68), "左 sd.cpp CPU ｜ 中 sd.cpp Vulkan 核显 ｜ 右 diffusers（PyTorch CPU）",
        font=f(18), fill=DIM)
dr.line([(pad, 100), (W - pad, 100)], fill=(226, 230, 234), width=2)

titles = ["sd.cpp-CPU", "sd.cpp-Vulkan(核显)", "diffusers-CPU"]
stats = {s: (statistics.mean([r["seconds"] for r in rows if r["scheme"] == s]),
             max([(r.get("mem_peak") or 0) for r in rows if r["scheme"] == s]) / 1048576)
          for s in order if s in agg}

y = top
for (pidx, ridx), files in sorted(groups.items()):
    dr.text((pad, y), f"{PROMPT_TAG.get(pidx, pidx)} · seed {ridx}",
            font=fb(20), fill=INK)
    y += 36
    x = pad
    for s, name in zip(order, titles):
        p = files.get(s)
        if p and os.path.exists(p):
            img = Image.open(p).convert("RGB").resize((CELL, CELL))
            im.paste(img, (x, y))
            t, m = stats.get(s, (0, 0))
            dr.rectangle([x, y + CELL - 34, x + CELL, y + CELL],
                         fill=(0, 0, 0))
            dr.text((x + 8, y + CELL - 30),
                    f"{name} {t:.0f}s {m/1024:.1f}G", font=f(15), fill=(235, 238, 242))
        else:
            dr.rectangle([x, y, x + CELL, y + CELL], fill=(240, 242, 245))
            dr.text((x + 150, y + 240), "缺图", font=f(20), fill=DIM)
        x += CELL + gap
    y += CELL + 40

dst = os.path.join(OUT, "fig5-三方案并排.png")
im.save(dst, optimize=True)
print(f"\nsaved -> {dst} {os.path.getsize(dst)//1024}KB {im.size}")

# 汇总 json
summary = {
    "cells": len(rows),
    "schemes": {},
}
for s in order:
    a = agg.get(s)
    if not a:
        continue
    summary["schemes"][s] = {
        "ok": f"{a['ok']}/{a['n']}",
        "sec_min": round(min(a["t"]), 1), "sec_max": round(max(a["t"]), 1),
        "sec_mean": round(sum(a["t"]) / len(a["t"]), 1),
        "mem_peak_mb": round(max(a["m"]) / 1048576) if a["m"] else None,
    }
json.dump(summary, open(os.path.join(E, "logs", "bench4_summary.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
print("summary -> logs/bench4_summary.json")
print(json.dumps(summary["schemes"], ensure_ascii=False, indent=1))
