#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ep25 配图：fig1 速度条形、fig2 字错率、封面。浅色留白 / 精细规则线 / 等宽数字 / 无 emoji。"""
import os, sys, json
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai"
os.makedirs(OUT, exist_ok=True)

FONT = r"C:/Windows/Fonts/msyh.ttc"
MONO = r"C:/Windows/Fonts/consola.ttf"
def f(sz, mono=False):
    return ImageFont.truetype(MONO if mono else FONT, sz)

BG      = "#ffffff"
FG      = "#1a1d21"
MUT     = "#8a919c"
LINE    = "#e5e7eb"
BAR     = "#2f6feb"
BAR2    = "#b9c4d4"
W       = 1080

def base(h):
    im = Image.new("RGB", (W, h), BG)
    return im, ImageDraw.Draw(im)

def rules(d, y0, y1, step=40):
    for y in range(y0, y1, step):
        d.line([(60, y), (W-60, y)], fill="#f4f6f8", width=1)

# ---------- fig1 速度 ----------
def fig1():
    data = [("CosyVoice3", 58.7), ("VoxCPM2", 191.2),
            ("VoiceStudio 子进程", 280.9), ("VoiceStudio 内建", 293.0)]
    im, d = base(560)
    rules(d, 130, 470, 34)
    d.text((60, 46), "四种跑法的单次合成中位耗时", font=f(34), fill=FG)
    d.text((60, 92), "秒 · 越短越好 · 25 题中位数 · 无显卡纯 CPU", font=f(20), fill=MUT)
    x0, x1, maxv = 300, W-150, 320
    top, bh, gap = 150, 52, 32
    for i, (nm, v) in enumerate(data):
        y = top + i*(bh+gap)
        d.text((60, y+bh//2-16), nm, font=f(25), fill=FG)
        w = int((x1-x0) * v/maxv)
        d.rectangle([x0, y, x0+w, y+bh], fill=BAR if i == 0 else BAR2)
        d.text((x0+w+14, y+bh//2-17), "%.1f s" % v, font=f(26, True), fill=FG)
    d.line([(60, 480), (W-60, 480)], fill=LINE, width=2)
    d.text((60, 500), "最快与最慢相差约 5 倍", font=f(22), fill=MUT)
    im.save(os.path.join(OUT, "ep25-fig1-speed.png"))
    print("  fig1 ok")

# ---------- fig2 字错率 ----------
def fig2():
    data = [("VoiceStudio 内建", 0.00, "13/24 零错"), ("VoiceStudio 子进程", 0.00, "9/14 零错"),
            ("CosyVoice3", 1.54, "12/25 零错"), ("VoxCPM2", 2.33, "11/25 零错")]
    im, d = base(560)
    rules(d, 130, 470, 34)
    d.text((60, 46), "四种跑法的字错率中位数", font=f(34), fill=FG)
    d.text((60, 92), "百分比 · 越低越好 · 差距在噪声内，不足以排名", font=f(20), fill=MUT)
    x0, x1, maxv = 340, W-190, 3.0
    top, bh, gap = 150, 52, 32
    for i, (nm, v, note) in enumerate(data):
        y = top + i*(bh+gap)
        d.text((60, y+bh//2-16), nm, font=f(25), fill=FG)
        w = max(3, int((x1-x0) * v/maxv))
        d.rectangle([x0, y, x0+w, y+bh], fill=BAR if i < 2 else BAR2)
        d.text((x0+w+14, y+bh//2-17), "%.2f %%" % v, font=f(26, True), fill=FG)
        d.text((x1+18, y+bh//2-13), note, font=f(19), fill=MUT)
    d.line([(60, 480), (W-60, 480)], fill=LINE, width=2)
    d.text((60, 500), "本次未做统计检验，0.00% 与 2.33% 的差别不足以判定优劣", font=f(22), fill=MUT)
    im.save(os.path.join(OUT, "ep25-fig2-cer.png"))
    print("  fig2 ok")

# ---------- 封面 ----------
def cover():
    im, d = base(383)
    d.rectangle([0, 0, W, 8], fill=BAR)
    d.text((72, 78), "没显卡跑声音克隆", font=f(58), fill=FG)
    d.text((72, 158), "CosyVoice3 · VoxCPM2 · VoiceStudio", font=f(30), fill=FG)
    d.line([(72, 214), (W-72, 214)], fill=LINE, width=2)
    d.text((72, 240), "四种跑法同机对照", font=f(28), fill=MUT)
    d.text((72, 300), "AI 积木师", font=f(24), fill=MUT)
    im.save(os.path.join(OUT, "ep25-cover.jpg"), quality=92)
    print("  cover ok")

print("生成配图:")
fig1(); fig2(); cover()
for n in ["ep25-fig1-speed.png", "ep25-fig2-cer.png", "ep25-cover.jpg"]:
    p = os.path.join(OUT, n)
    print("  %-26s %.0f KB  %s" % (n, os.path.getsize(p)/1024, Image.open(p).size))
