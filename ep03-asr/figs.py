"""03 期 ASR 实测证据图 —— 数字全部从 result.json 现算，红字按 difflib 现标，不用 matplotlib。"""
import json, difflib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W = Path(r"C:\Users\Frank\AppData\Local\hermes\workspace")
E = W / "articles/series/local-ai/ep03"
OUT = W / "assets/local-ai-ep03"
OUT.mkdir(parents=True, exist_ok=True)
rows = [r for r in json.loads((E / "result.json").read_text(encoding="utf-8")) if not r.get("error")]

MSYH = "C:/Windows/Fonts/msyh.ttc"
MSYHB = "C:/Windows/Fonts/msyhbd.ttc"
def f(sz):
    return ImageFont.truetype(MSYH, sz)
def fb(sz):
    try:
        return ImageFont.truetype(MSYHB, sz)
    except Exception:
        return ImageFont.truetype(MSYH, sz)

BG, INK, DIM, RED = (255, 255, 255), (34, 38, 45), (122, 130, 140), (190, 62, 62)
ACC = {"paraformer": (44, 122, 90), "sensevoice": (58, 110, 176), "fw": (176, 122, 48), "whisper": (168, 74, 74)}
NAME = {"paraformer": "Paraformer-zh", "sensevoice": "SenseVoice-Small",
        "fw": "faster-whisper small", "whisper": "Whisper-small (ONNX)"}
ORDER = ["paraformer", "sensevoice", "fw", "whisper"]

def grp(s):
    return "A 档 8 秒" if s.startswith("A_") else "B 档 17 秒" if s.startswith("B_") else "C 档 10.5 分钟"

def canvas(w, h, title, sub=""):
    im = Image.new("RGB", (w, h), BG); d = ImageDraw.Draw(im)
    d.text((48, 34), title, font=fb(30), fill=INK)
    if sub:
        d.text((48, 76), sub, font=f(17), fill=DIM)
    d.line([(48, 108), (w - 48, 108)], fill=(226, 230, 234), width=2)
    return im, d

def foot(d, w, h, txt):
    d.text((48, h - 42), txt, font=f(14), fill=DIM)

def centered(d, cx, y, txt, font, fill):
    d.text((cx - d.textlength(txt, font=font) / 2, y), txt, font=font, fill=fill)

# ---------- 图1 CER / 图2 倍速 ----------
groups = ["A 档 8 秒", "B 档 17 秒", "C 档 10.5 分钟"]
by = {}
for r in rows:
    by.setdefault(("cer", grp(r["sample"]), r["model"]), []).append(r["cer"] * 100)
    by.setdefault(("rtf", grp(r["sample"]), r["model"]), []).append(r["rtf_x"])

def bar_fig(fname, key, title, sub, fmt):
    im, d = canvas(1180, 640, title, sub)
    x0, y0, plot_h = 60, 500, 330
    cells = []
    cx = x0
    for g in groups:
        for m in ORDER:
            v = by.get((key, g, m))
            cells.append((cx, g, m, sum(v) / len(v) if v else None)); cx += 72
        cx += 40
    mx = max(c[3] for c in cells if c[3])
    for cx, g, m, v in cells:
        if v is None:
            continue
        h = max(2, int(plot_h * v / mx))
        d.rectangle([cx, y0 - h, cx + 52, y0], fill=ACC[m])
        centered(d, cx + 26, y0 - h - 25, fmt.format(v=v), fb(15), INK)
    d.line([(x0 - 12, y0), (cx - 30, y0)], fill=(200, 206, 212), width=2)
    for i, g in enumerate(groups):
        centered(d, x0 + i * (72 * 4 + 40) + 144 - 20, y0 + 34, g, fb(17), INK)
    ly = 150
    for m in ORDER:
        d.rectangle([x0 + 4, ly, x0 + 20, ly + 13], fill=ACC[m])
        d.text((x0 + 28, ly - 3), NAME[m], font=f(16), fill=INK)
        ly += 24
    foot(d, 1180, 640, "数据来源：本机实测 result.json（4 模型 × 15 组）· 纯 CPU：AMD Ryzen 7 5700G / 27.9GB · 模型体积与下载地址见正文")
    im.save(OUT / fname); print("  ", fname, im.size)

bar_fig("fig1-CER对比.png", "cer", "字错率（CER）：越低越准", "三档音频的平均值（每档 5 个样本）", "{v:.1f}%")
bar_fig("fig2-实时倍速.png", "rtf", "处理速度：纯 CPU 上的实时倍速", "1× = 刚好跟上录音速度，越高越快", "{v:.0f}×")

# ---------- 图3 横向对比 ----------
im, d = canvas(1180, 600, "四款模型横向对比：体积 · 速度 · 精度", "同机同批样本实测（60 条明细）")
hdrs = [("模型", 40), ("部署体积", 330), ("平均倍速", 500), ("CER 中位", 660), ("CER 最差", 830), ("结论", 1000)]
for t, x in hdrs:
    d.text((x, 152), t, font=fb(17), fill=DIM)
y = 200
for m in ORDER:
    g = [x for x in rows if x["model"] == m]
    cs = sorted(x["cer"] for x in g); rts = [x["rtf_x"] for x in g]
    d.text((40, y), NAME[m], font=fb(18), fill=ACC[m])
    d.text((330, y), f"{g[0]['size_mb']:.0f} MB", font=f(17), fill=INK)
    d.text((500, y), f"{sum(rts)/len(rts):.1f}×", font=f(17), fill=INK)
    d.text((660, y), f"{cs[len(cs)//2]*100:.2f}%", font=f(17), fill=INK)
    d.text((830, y), f"{cs[-1]*100:.1f}%", font=f(17), fill=INK)
    d.text((1000, y), {"paraformer": "推荐", "sensevoice": "可用", "fw": "偏慢",
                       "whisper": "不推荐"}[m], font=f(17), fill=INK)
    d.line([(40, y + 32), (1130, y + 32)], fill=(238, 241, 244), width=1)
    y += 56
foot(d, 1180, 600, "体积 = 模型部署文件（int8）大小；整包解压后另含其余文件，见正文「下载体积」一节")
im.save(OUT / "fig3-横向对比.png"); print("   fig3-横向对比.png", im.size)

# ---------- 图4 同一句话四个模型听成什么（红字 = 与原文不符，difflib 现算）----------
REF = "大家好，这里是AI积木师。今天用3分钟把1个AI工具拆成，看得懂，用得上装得起的积木块。从今天起，我每天帮你塞一个真正有价值的东西出来。"
smp = "B_1_clean.wav"
im, d = canvas(1180, 760, "同一段话，四个模型各自听成了什么", "样本：B 档 17 秒真人录音（干净）· 红字 = 与原文不符处（含数字/标点转写差异）")
y = 152
for m in ORDER:
    r = next((x for x in rows if x["model"] == m and x["sample"] == smp), None)
    if not r:
        continue
    d.text((40, y + 2), NAME[m], font=fb(18), fill=ACC[m])
    d.text((40, y + 30), f"CER {r['cer']*100:.2f}% · {r['wall_s']:.2f} 秒", font=f(15), fill=DIM)
    sm = difflib.SequenceMatcher(None, REF, r["text"] or "")
    spans, x, line = [], 310, 0
    FONT18 = f(18)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        seg = (r["text"] or "")[j1:j2]
        for ch in seg:
            w = d.textlength(ch, font=FONT18)
            if x + w > 1128:              # 折到第二行
                line, x = 1, 310
            spans.append((x, line, ch, INK if tag == "equal" else RED))
            x += w
        if line >= 1 and x >= 1128:
            break
    for sx, sline, ch, col in spans:
        d.text((sx, y + sline * 26), ch, font=FONT18, fill=col)
    y += 160
    d.line([(40, y - 40), (1130, y - 40)], fill=(238, 241, 244), width=1)
foot(d, 1180, 760, "口径说明：数字/标点转写差异（如「三→3」「AI→a i」）也计入 CER，属保守口径，正文逐条说明")
im.save(OUT / "fig4-失败案例.png"); print("   fig4-失败案例.png", im.size)
print("\n输出:", OUT)
