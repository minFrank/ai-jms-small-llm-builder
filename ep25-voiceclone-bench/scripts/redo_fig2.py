#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重做 ep12 fig2「单页耗时与内存峰值」。

原图把 lightonocr 与 lightonocr-stripped 拆成两行，但两者耗时/内存完全相同
（26.7745 / 1561.8，差 0.0），只有字错率不同 —— 在这张速度/内存图上就是两行
一模一样的重复条形。合并为一行，字错率差异交给总榜图说明。

配色沿用方案 B（暖砂）；水印画在底部追加带，绝不压内容。
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont

FDIR = r"C:/Windows/Fonts"
OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/ep12-refined/ep12-refined-fig2-速度内存.png"
DATA = r"D:/study/ai-jms/ep12-ocr2-venvs/_agg_v3.json"

BG     = (250, 247, 242)
FG     = (29, 26, 21)
GOLD   = (168, 118, 62)
OLIVE  = (110, 122, 74)
LINE   = (236, 229, 218)
GREY   = (122, 112, 100)
LBL    = (74, 68, 58)

def f(sz, bold=False):
    for n in (["msyhbd.ttc", "msyh.ttc"] if bold else ["msyh.ttc", "msyhbd.ttc"]):
        try: return ImageFont.truetype(os.path.join(FDIR, n), sz)
        except Exception: pass
    return ImageFont.load_default()

W, PAD = 1080, 96

H = 118 + 52 + 10 * 62 + 120   # 先给足高度，画完按实际内容裁

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)

d.text((60, 46), "单页耗时与内存峰值", font=f(32, True), fill=FG)
d.text((60, 92), "24 张样本中位 · 纯 CPU · 每张图 3 次取中位", font=f(19), fill=GREY)

# 图例
lx = 620
d.rounded_rectangle([lx, 52, lx + 26, 70], radius=5, fill=GOLD)
d.text((lx + 36, 48), "单页耗时中位（秒）", font=f(19), fill=LBL)
d.rounded_rectangle([lx, 86, lx + 26, 104], radius=5, fill=OLIVE)
d.text((lx + 36, 82), "内存峰值中位（MB）", font=f(19), fill=LBL)

src = json.load(open(DATA, encoding="utf-8"))
raw = [(k, v["t_med"], v["rss_med"], v["cer_med"])
       for k, v in src.items() if v.get("t_med") is not None]
# 合并两行：lightonocr / lightonocr-stripped 耗时内存完全相同
merged = {}
for k, t, r, c in raw:
    key = "lightonocr" if k.startswith("lightonocr") else k
    if key not in merged:
        merged[key] = [k, t, r, c]
    else:
        merged[key][1] = max(merged[key][1], t)
        merged[key][2] = max(merged[key][2], r)
LBLNAME = {
    "rapidocrlite-small": "RapidOCRLite small",
    "rapidocrlite-medium": "RapidOCRLite medium",
    "simdpaddleocr-default": "SimdPaddleOCR 默认",
    "simdpaddleocr": "SimdPaddleOCR 受控",
    "easyocr": "EasyOCR",
    "paddleocr": "PaddleOCR 官方",
    "lightonocr": "LightOnOCR-3",
    "glmocr": "GLM-OCR 0.8B",
}
rows = sorted(merged.values(), key=lambda x: x[1])
mt = max(r[1] for r in rows)
mr = max(r[2] for r in rows)

X0, LABW = 60, 232          # 标签区 60..292
BX0 = X0 + LABW             # 条形起点 292
BXW = 272                   # 条形最大宽
LBLW = 52                   # 数值标签宽
GAPX = 34                   # 两组之间留白
X2 = BX0 + BXW + LBLW + GAPX          # 第二组条形起点 = 292+272+52+34 = 650
top, bh, gap = 170, 30, 32
print("版面: 标签 %d-%d | 组1 %d-%d 标签到 %d | 组2 %d-%d 标签到 %d | 右边距 %d"
      % (X0, X0 + LABW, BX0, BX0 + BXW, BX0 + BXW + LBLW,
         X2, X2 + BXW, X2 + BXW + LBLW, W - (X2 + BXW + LBLW)))

for i, (k, t, r, c) in enumerate(rows):
    y = top + i * (bh + gap)
    d.text((X0, y + 1), LBLNAME.get(k, k), font=f(20), fill=FG)
    # 耗时条
    d.rounded_rectangle([BX0, y, BX0 + max(10, int(BXW * t / mt)), y + bh], radius=7, fill=GOLD)
    d.text((BX0 + BXW + 10, y + 2), "%.2f" % t, font=f(19, True), fill=FG)
    # 内存条
    d.rounded_rectangle([X2, y, X2 + max(10, int(BXW * r / mr)), y + bh], radius=7, fill=OLIVE)
    d.text((X2 + BXW + 10, y + 2), "%.0f" % r, font=f(19, True), fill=FG)
    if i:
        d.line([X0, y - gap // 2, W - 60, y - gap // 2], fill=LINE, width=2)

fy = top + len(rows) * (bh + gap) + 16
d.line([60, fy, W - 60, fy], fill=LINE, width=2)
d.text((60, fy + 18), "前五名与最后一名两项一致；中间两名对调——PaddleOCR 更慢但更省内存。",
       font=f(19), fill=GREY)
d.text((60, fy + 50), "LightOnOCR-3 两行输出耗时与内存相同，本图合并为一行，字错率差异见总榜。",
       font=f(19), fill=GREY)

im.save(OUT, optimize=True)
# 按实际内容裁到底，再加水印带，避免中间留大片空白
import numpy as np
_L = np.array(im.convert("L")).astype(int)
_bg = np.median(_L)
_last = int(np.max(np.where((_np := np.abs(_L - _bg) > 25).any(axis=1))[0]))
im = im.crop((0, 0, W, _last + 22))
w, h = im.size
canvas = Image.new("RGB", (w, h + PAD), BG)
canvas.paste(im, (0, 0))
d2 = ImageDraw.Draw(canvas)
d2.text((w - 46, h + 24), "ep12 · 续测开源 OCR 六套同机实测",
        font=f(20), fill=GREY, anchor="ra")
d2.text((w - 46, h + 52), "公众号：AI 积木师", font=f(15), fill=GREY, anchor="ra")
canvas.save(OUT, optimize=True)

print("fig2 重做完成 %dx%d" % canvas.size)
print("行数 %d（原 9，合并掉 lightonocr-stripped）" % len(rows))
for k, t, r, c in rows:
    print("   %-24s %7.2f s  %6.0f MB" % (LBLNAME.get(k, k), t, r))
