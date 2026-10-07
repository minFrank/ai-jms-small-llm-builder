# -*- coding: utf-8 -*-
"""fig10: 两条补测路线(ComfyUI / ONNX·DirectML)同题同参并排。

风格约束(用户 2026-09-25/26 两次强调):简约大气高级科技 —— 浅色留白、
精细规则线、等宽数字、禁 emoji。
所有耗时数字从 summary-five-schemes.json 现算,禁止手打。
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
SUM = os.path.join(E04, "replicate", "summary-five-schemes.json")
OUTDIR = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai-ep04"
OUT = os.path.join(OUTDIR, "fig10-补测两路线同题同参.png")

# ---- 数据:全部现算 ----
with open(SUM, encoding="utf-8") as f:
    S = json.load(f)

cf = S["schemes"]["ComfyUI · 纯 CPU(冷启动)"]["seconds_total"]
on = S["schemes"]["ONNX/DML · 核显(冷启动)"]["seconds_total"]
LANES = [
    {
        "name": "ComfyUI",
        "sub": "纯 CPU",
        "median": cf["median"],
        "n": cf["n"],
        "spread": cf["spread_pct"],
        "date": "10-06",
        "imgs": [
            r"D:/models/txt2img/out5/cold_p0_s42_r0.png",
            r"D:/models/txt2img/out5/cold_p1_s42_r0.png",
        ],
    },
    {
        "name": "ONNX / DirectML",
        "sub": "核显",
        "median": on["median"],
        "n": on["n"],
        "spread": on["spread_pct"],
        "date": "10-07",
        "imgs": [
            r"D:/models/txt2img/out6/onnx_cold_p0_s42_r0.png",
            r"D:/models/txt2img/out6/onnx_cold_p1_s42_r0.png",
        ],
    },
]

# ---- 画布:浅色留白 ----
BG = (250, 251, 252)
INK = (17, 24, 39)          # 近黑主文字
SUB = (107, 114, 128)       # 次级灰
RULE = (229, 231, 235)      # 细规则线
ACCENT = (15, 76, 129)      # #0F4C81 与正文主色一致

W = 1400
MARGIN = 72
IMG = 560
LANE_GAP = 120
LANE_W = IMG                      # 泳道内两张图纵向排, 宽 = 单图宽
TOP = 178
HEADER_H = 116
FOOT_H = 108
CAP_GAP = 64                      # 最后一张图注与底部规则线之间的留白
IMG_END = TOP + HEADER_H + IMG + 56 + IMG
H = IMG_END + CAP_GAP + FOOT_H

canvas = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(canvas)


def font(size, mono=False, bold=False):
    cands = (
        ["C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consola.ttf"]
        if mono else
        ["C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/segoeuib.ttf",
         "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
    )
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


F_TITLE = font(40, bold=True)
F_LANE = font(31, bold=True)
F_SUB = font(23)
F_NUM = font(34, mono=True)
F_META = font(21, mono=True)
F_CAP = font(21)
F_FOOT = font(20)

# ---- 标题 ----
d.text((MARGIN, 52), "两条补测路线：同题、同参、同种子", font=F_TITLE, fill=INK)
d.text((MARGIN, 106),
       "两句提示词 · 种子 42 · 512×512 · 20 步 · 每方案 18 次取中位",
       font=F_SUB, fill=SUB)
# 标题下精细规则线
d.line([(MARGIN, 152), (W - MARGIN, 152)], fill=RULE, width=2)

# ---- 两条泳道 ----
lane_x = [MARGIN, MARGIN + LANE_W + LANE_GAP]
assert lane_x[1] + LANE_W <= W - MARGIN, "版面溢出"

for li, lane in enumerate(LANES):
    x0 = lane_x[li]
    x1 = x0 + LANE_W
    # 泳道标题
    d.text((x0, TOP - 104), lane["name"], font=F_LANE, fill=INK)
    d.text((x0, TOP - 64), lane["sub"], font=F_SUB, fill=SUB)
    # 关键数字(等宽)
    num = f'{lane["median"]:.2f} s'
    d.text((x1 - 210, TOP - 106), num, font=F_NUM, fill=ACCENT)
    meta = f'n={lane["n"]}  spread={lane["spread"]:.2f}%  {lane["date"]}'
    d.text((x1 - 370, TOP - 58), meta, font=F_META, fill=SUB)
    # 泳道标题下规则线(只画该泳道宽)
    d.line([(x0, TOP - 24), (x1, TOP - 24)], fill=RULE, width=2)

    for gi, p in enumerate(lane["imgs"]):
        y = TOP + HEADER_H + gi * (IMG + 56)
        if not os.path.exists(p):
            d.rectangle([x0, y, x0 + IMG, y + IMG], outline=RULE, width=2)
            d.text((x0 + 16, y + 16), "MISSING", font=F_META, fill=(220, 38, 38))
            continue
        im = Image.open(p).convert("RGB").resize((IMG, IMG), Image.LANCZOS)
        canvas.paste(im, (x0, y))
        # 图外细框
        d.rectangle([x0, y, x0 + IMG, y + IMG], outline=RULE, width=2)
        # 图注
        tag = "提示词 1" if gi == 0 else "提示词 2"
        seed = "seed 42"
        d.text((x0, y + IMG + 14), f"{tag} · {seed}", font=F_CAP, fill=SUB)

# ---- 底部规则线 + 注 ----
d.line([(MARGIN, IMG_END + CAP_GAP), (W - MARGIN, IMG_END + CAP_GAP)],
       fill=RULE, width=2)
foot = ("两列分别取自 10-06 与 10-07 两批，采集日不同，不与前三方案横比；"
        "耗时为冷启动中位，口径见正文表注。")
d.text((MARGIN, IMG_END + CAP_GAP + 34), foot, font=F_FOOT, fill=SUB)

os.makedirs(OUTDIR, exist_ok=True)
canvas.save(OUT, optimize=True)
print("saved ->", OUT, canvas.size, os.path.getsize(OUT), "bytes")
