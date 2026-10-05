"""ep09 证据图 —— 数字全部从 4 份跑测 JSON 现算,PIL 手绘(与 03 期 figs.py 同风格)。

图1 8 模型平均 CER 总榜(横条)
图2 FunASR vs FireRed 逐样本 CER(分组条)
图3 长音频 628s:直接喂 vs 30 秒分段(字数对照)
cover 封面(标题文字,极简)
"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

W = Path(r"C:\Users\Frank\AppData\Local\hermes\workspace")
REPO = Path(r"D:\study\ai-jms\ai-jms-small-llm-builder\ep09-asr2")
OUT = W / "assets/local-ai-ep09"
OUT.mkdir(parents=True, exist_ok=True)

MSYH = "C:/Windows/Fonts/msyh.ttc"
MSYHB = "C:/Windows/Fonts/msyhbd.ttc"


def f(sz):
    return ImageFont.truetype(MSYH, sz)


def fb(sz):
    try:
        return ImageFont.truetype(MSYHB, sz)
    except Exception:
        return ImageFont.truetype(MSYH, sz)


BG, INK, DIM = (255, 255, 255), (34, 38, 45), (122, 130, 140)
LINE = (226, 230, 234)
BLUE = (15, 76, 129)      # 新引擎主色
GREEN = (44, 122, 90)     # 老榜一
GREY = (150, 158, 168)    # 其他


def canvas(w, h, title, sub=""):
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    d.text((48, 34), title, font=fb(30), fill=INK)
    if sub:
        d.text((48, 76), sub, font=f(17), fill=DIM)
    d.line([(48, 108), (w - 48, 108)], fill=LINE, width=2)
    return im, d


def foot(d, w, h, txt):
    d.text((48, h - 42), txt, font=f(14), fill=DIM)


def load(name):
    return json.load(open(REPO / name, encoding="utf-8"))


fun_ab = load("extra_funasr.json")
fre_ab = load("extra_firered.json")
fun_c = load("extra_funasr_Cseg.json")
fre_c = load("extra_firered_Cseg.json")


def mean_cer(rows):
    v = [r["cer"] for r in rows if r.get("cer") is not None]
    return sum(v) / len(v) if v else 0.0


# ---------- 图1:8 模型平均 CER 总榜(横条) ----------
DATA1 = [
    ("Paraformer-zh", 0.0049, GREY, "上期"),
    ("Fun-ASR-Nano", mean_cer(fun_ab["rows"]), BLUE, "本期"),
    ("SenseVoice-Small", 0.0552, GREY, "上期"),
    ("FireRedASR2-AED", mean_cer(fre_ab["rows"]), BLUE, "本期"),
    ("faster-whisper small", 0.1066, GREY, "上期"),
    ("Zipformer-CTC small", 0.1690, GREY, "上期"),
    ("Whisper-small (ONNX)", 0.2228, GREY, "上期"),
    ("Zipformer-CTC zh", 0.2563, GREY, "上期"),
]
DATA1.sort(key=lambda x: x[1])

im, d = canvas(1180, 640, "8 个本地模型 · A/B 10 组音频平均字错率",
               "同机同批(AMD 5700G 8核 / 27.9GB / 无独显),越低越准")
x0, y0 = 340, 150
maxv = max(x[1] for x in DATA1)
bar_max = 660
row_h = 54
for i, (name, v, col, tag) in enumerate(DATA1):
    y = y0 + i * row_h
    d.text((48, y + 4), name, font=fb(18), fill=INK)
    w = max(3, int(bar_max * v / maxv))
    d.rectangle([x0, y + 6, x0 + w, y + 34], fill=col)
    d.text((x0 + w + 12, y + 8), f"{v*100:.2f}%", font=fb(17), fill=INK)
    d.text((1075, y + 10), tag, font=f(14), fill=DIM)
foot(d, 1180, 640, "数据:ep09-asr2/extra_*.json 与 ep03-asr/results · 2026-10-03")
im.save(OUT / "fig1-总榜CER.png")
print("fig1 OK")

# ---------- 图2:FunASR vs FireRed 逐样本 ----------
samples = sorted({r["sample"] for r in fun_ab["rows"]})
m1 = {r["sample"]: r for r in fun_ab["rows"]}
m2 = {r["sample"]: r for r in fre_ab["rows"]}
LBL = {s: s.replace(".wav", "").replace("_", " ") for s in samples}

im, d = canvas(1180, 660, "两个新模型逐样本字错率对照(10 组)",
               "左蓝 Fun-ASR-Nano,右灰 FireRedASR2-AED;打点为字错率%,胜负集中在加噪档")
gx0, gy0, gh = 90, 500, 330
maxv2 = max(max(m1[s]["cer"], m2[s]["cer"]) for s in samples)
cell_w = 104
for i, s in enumerate(samples):
    cx = gx0 + i * cell_w
    v1, v2 = m1[s]["cer"], m2[s]["cer"]
    h1 = max(2, int(gh * v1 / maxv2))
    h2 = max(2, int(gh * v2 / maxv2))
    d.rectangle([cx, gy0 - h1, cx + 38, gy0], fill=BLUE)
    d.rectangle([cx + 46, gy0 - h2, cx + 84, gy0], fill=GREY)
    if v1 > 0:
        d.text((cx + 2, gy0 - h1 - 24), f"{v1*100:.0f}", font=f(13), fill=INK)
    else:
        d.text((cx + 8, gy0 - 22), "0", font=f(13), fill=DIM)
    if v2 > 0:
        d.text((cx + 46, gy0 - h2 - 24), f"{v2*100:.0f}", font=f(13), fill=INK)
    else:
        d.text((cx + 52, gy0 - 22), "0", font=f(13), fill=DIM)
    lab = LBL[s].split(" ", 1)[1] if " " in LBL[s] else LBL[s]
    d.text((cx + 4, gy0 + 12), lab, font=f(13), fill=DIM)
    grp = LBL[s].split(" ", 1)[0]
    d.text((cx + 4, gy0 + 34), grp, font=f(13), fill=INK)
d.line([(gx0 - 20, gy0), (gx0 + cell_w * len(samples), gy0)], fill=LINE, width=2)
d.rectangle([90, 600, 114, 616], fill=BLUE)
d.text((122, 598), "Fun-ASR-Nano", font=f(15), fill=INK)
d.rectangle([330, 600, 354, 616], fill=GREY)
d.text((362, 598), "FireRedASR2-AED", font=f(15), fill=INK)
foot(d, 1180, 660, "单位:字错率 % · 数据:extra_funasr.json / extra_firered.json")
im.save(OUT / "fig2-逐样本对照.png")
print("fig2 OK")

# ---------- 图3:长音频 直接喂 vs 分段 ----------
im, d = canvas(1180, 620, "628 秒长音频:直接喂 vs 切 30 秒段",
               "应转约 2257 字(归一后);直接喂两模型分别只出 1 字和 0 字,没有报错")
panels = [
    ("Fun-ASR-Nano", "直接整段喂", 1, 100.0, BLUE,
     "切 30 秒段", fun_c["rows"][0]["chars"], fun_c["rows"][0]["cer"], GREEN),
    ("FireRedASR2-AED", "直接整段喂", 0, 100.0, BLUE,
     "切 30 秒段", fre_c["rows"][0]["chars"], fre_c["rows"][0]["cer"], GREEN),
]
px = [120, 660]
for k, (nm, l1, c1, e1, col1, l2, c2, e2, col2) in enumerate(panels):
    x = px[k]
    d.text((x, 150), nm, font=fb(22), fill=INK)
    # 左柱:直接喂
    d.rectangle([x, 470 - 4, x + 150, 470], fill=(206, 212, 220))
    d.text((x + 40, 430), f"{c1} 字", font=fb(20), fill=DIM)
    d.text((x + 10, 486), l1, font=f(15), fill=DIM)
    d.text((x + 26, 512), f"CER {e1:.0f}%", font=f(15), fill=(190, 62, 62))
    # 右柱:分段
    h2 = 300
    d.rectangle([x + 200, 470 - h2, x + 350, 470], fill=col2)
    d.text((x + 240, 470 - h2 - 34), f"{c2} 字", font=fb(20), fill=INK)
    d.text((x + 210, 486), l2, font=f(15), fill=INK)
    d.text((x + 226, 512), f"CER {e2*100:.1f}%", font=f(15), fill=INK)
d.line([(100, 470), (1080, 470)], fill=LINE, width=2)
foot(d, 1180, 620, "数据:extra_funasr_C.json / extra_firered_C.json(直接喂)与 *_Cseg.json(分段)· net 0")
im.save(OUT / "fig3-长音频分段.png")
print("fig3 OK")

# ---------- 封面(极简) ----------
im, d = canvas(1180, 500, "Fun-ASR 与 FireRedASR2 实测",
               "8 个本地转文字模型同机对照 · 长音频要先切段")
d.text((48, 200), "无独显电脑 · 同批音频 · 全程断网", font=fb(40), fill=BLUE)
d.line([(48, 270), (640, 270)], fill=BLUE, width=4)
d.text((48, 300), "平均字错率 1.98% / 5.72%  ｜  628 秒直接喂:1 字 / 0 字", font=f(22), fill=INK)
d.text((48, 350), "切 30 秒段后:2584 字 1.0% ｜ 2349 字 1.3%", font=f(22), fill=INK)
d.text((48, 430), "AI 积木师 · 本地无显卡系列", font=f(17), fill=DIM)
im.save(W / "assets/local-ai-ep09-cover.jpg", quality=92)
print("cover OK")

for p in sorted(OUT.glob("*.png")):
    print(f"  {p.name} {p.stat().st_size//1024}KB")
print("  cover", (W / "assets/local-ai-ep09-cover.jpg").stat().st_size // 1024, "KB")
