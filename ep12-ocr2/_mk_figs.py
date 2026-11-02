# -*- coding: utf-8 -*-
"""ep12 成稿配图：速度内存双栏 / 准确率-速度散点 / 同权重三栈 / 新样本构成 / 封面。
风格：浅色留白、精细规则线、等宽数字。中文走雅黑，数字走 Consolas。"""
import os
from PIL import Image, ImageDraw, ImageFont

A = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets"
os.makedirs(A, exist_ok=True)
os.makedirs(A + "/local-ai-ep12-samples", exist_ok=True)

FZH   = "C:/Windows/Fonts/msyh.ttc"
FZHB  = "C:/Windows/Fonts/msyhbd.ttc"
FNUM  = "C:/Windows/Fonts/consola.ttf"

INK    = (32, 36, 42)
INK2   = (96, 104, 116)
INK3   = (150, 158, 170)
RULE   = (224, 228, 234)
RULE2  = (206, 212, 220)
BG     = (255, 255, 255)
PANEL  = (249, 250, 252)
ACC    = (28, 92, 176)
ACC2   = (196, 74, 60)
ACC3   = (46, 132, 106)

def f(path, size): return ImageFont.truetype(path, size)
def zh(s, sz, b=False): return f(FZHB if b else FZH, sz)
def num(s): return f(FNUM, s)

W = 1400  # 统一画布宽

def new(w, h):
    im = Image.new("RGB", (w, h), BG)
    return im, ImageDraw.Draw(im)

def txt(d, xy, s, font, fill=INK, anchor="la"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)

def wof(d, s, font):
    return d.textbbox((0,0), s, font=font)[2]

# ---------------------------------------------------------------- 数据
ROWS = [  # (标签, 耗时中位 秒, 内存中位 MB, CER 中位, 组别)
    ("RapidOCRLite small", 0.65,  323,  0.0242, "det"),
    ("RapidOCRLite medium",2.67,  686,  0.0250, "det"),
    ("SimdPaddleOCR 默认", 2.77,  745,  0.0250, "det"),
    ("SimdPaddleOCR 受控", 2.93,  754,  0.0246, "det"),
    ("EasyOCR",            4.74, 1529,  0.0656, "det"),
    ("PaddleOCR 官方",    22.19, 1928,  0.0137, "det"),
    ("LightOnOCR-3 剥标记",26.77,1562,  0.0263, "e2e"),
    ("GLM-OCR 0.9B",      52.68, 3361,  0.0000, "e2e"),
]
SHORT = {"RapidOCRLite small":"Rcl-small", "RapidOCRLite medium":"Rcl-med",
         "SimdPaddleOCR 默认":"Simd默认", "SimdPaddleOCR 受控":"Simd受控",
         "EasyOCR":"EasyOCR", "PaddleOCR 官方":"Paddle官方",
         "LightOnOCR-3 剥标记":"LightOn", "GLM-OCR 0.9B":"GLM-OCR"}

# ================================================================ fig1 速度内存双栏
def fig1():
    H = 720
    im, d = new(W, H)
    txt(d, (60, 46), "单页耗时与内存峰值（24 张样本中位）", zh(0, 27, True))
    txt(d, (60, 88), "同机 · 纯 CPU · 每张图 3 次取中位", zh(0, 15), fill=INK3)

    pad_l, gap = 300, 96
    colw = (W - 120 - gap) // 2 - pad_l//2
    top, rowh = 168, 58
    panels = [("单页耗时中位（秒）", [r[1] for r in ROWS], "%.2f", ACC),
              ("内存峰值中位（MB）", [r[2] for r in ROWS], "%d", ACC3)]

    for pi, (title, vals, fmt, col) in enumerate(panels):
        x0 = 60 + pi*(colw + pad_l//2 + gap)
        w  = W - 60 - x0 if pi == 1 else colw
        txt(d, (x0, top-30), title, zh(0, 17, True), fill=INK)
        mx = max(vals)
        for i, r in enumerate(ROWS):
            y = top + i*rowh
            # 标签
            txt(d, (x0, y+4), SHORT[r[0]], zh(0, 15), fill=INK2)
            bx0 = x0 + 150
            bw  = w - 150 - 96
            v   = vals[i]
            bl  = max(3, bw * v / mx)
            fill = col if r[4] == "det" else ACC2
            d.rectangle([bx0, y+6, bx0+bl, y+25], fill=fill)
            txt(d, (bx0+bl+10, y+4), fmt % v, num(15), fill=INK)
            d.line([x0, y+40, x0+w, y+40], fill=RULE, width=1)

    d.line([60, H-92, W-60, H-92], fill=RULE2, width=1)
    txt(d, (60, H-70), "蓝色为检测式（先定位再识别），红色为端到端（整页进、全文出）。LightOnOCR-3 按剥标记口径计。",
        zh(0, 14), fill=INK2)
    im.save(A + "/local-ai-ep12-fig1-速度内存.png")
    return "fig1"

# ================================================================ fig2 散点
def fig2():
    H = 800
    im, d = new(W, H)
    txt(d, (60, 46), "准确率与速度的关系", zh(0, 27, True))
    txt(d, (60, 88), "横轴向左更快，纵轴向下更准 —— 左下角是理想位置", zh(0, 15), fill=INK3)

    L, R_, T, B = 170, W-260, 176, H-156
    d.rectangle([L, T, R_, B], fill=PANEL)
    d.rectangle([L, T, R_, B], outline=RULE2, width=1)

    xs = [r[1] for r in ROWS]; ys = [r[3] for r in ROWS]
    xmax = max(xs)*1.10; ymax = max(ys)*1.14
    def px(v): return L + (R_-L)*v/xmax
    def py(v): return B - (B-T)*v/ymax

    for gv in [0, 0.02, 0.04, 0.06]:
        y = py(gv)
        d.line([L, y, R_, y], fill=RULE, width=1)
        txt(d, (L-12, y), "%.2f" % gv, num(14), fill=INK3, anchor="rm")
    for gv in [0, 10, 20, 30, 40, 50]:
        x = px(gv)
        d.line([x, T, x, B], fill=RULE, width=1)
        txt(d, (x, B+14), str(gv), num(14), fill=INK3, anchor="ma")
    txt(d, ((L+R_)//2, B+48), "单页耗时中位（秒）", zh(0, 15), fill=INK2, anchor="ma")
    txt(d, (66, (T+B)//2), "CER 中位", zh(0, 15), fill=INK2, anchor="mm")

    CLUSTER = [r for r in ROWS if r[4] == "det"]
    ALONE   = [r for r in ROWS if r[4] == "e2e" or r[0].startswith("EasyOCR")]

    # --- 左下角整簇：四个检测式配置画一个圈 + 引线，不逐个叠标签
    cxs = [px(r[1]) for r in CLUSTER]; cys = [py(r[3]) for r in CLUSTER]
    cx, cy = sum(cxs)/len(cxs), sum(cys)/len(cys)
    rad = max(max(cxs)-min(cxs), max(cys)-min(cys))/2 + 34
    d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=ACC, width=1)
    for r in CLUSTER:
        x, y = px(r[1]), py(r[3])
        d.ellipse([x-7, y-7, x+7, y+7], fill=ACC)
    # 引线斜向右下出簇（左上方向空间不够，会跑出画布）
    lx, ly = cx+rad+30, cy+rad+56
    d.line([cx+rad*0.62, cy+rad*0.62, lx-8, ly-26], fill=ACC, width=1)
    d.ellipse([lx-3, ly-29, lx+3, ly-23], fill=ACC)
    txt(d, (lx, ly-52), "四个检测式配置", zh(0, 16, True), fill=ACC, anchor="la")
    txt(d, (lx, ly-26), "耗时 0.65–2.93 秒", num(14), fill=INK2, anchor="la")
    txt(d, (lx, ly-6),  "CER 中位 0.0242–0.0250", num(14), fill=INK2, anchor="la")

    # --- 其余逐个标
    for name, t_, m, cer, grp in ALONE:
        x, y = px(t_), py(cer)
        col = ACC if grp == "det" else ACC2
        d.ellipse([x-9, y-9, x+9, y+9], fill=col)
        d.ellipse([x-15, y-15, x+15, y+15], outline=col, width=1)
        lbl = SHORT[name]
        ax, anc = x + 24, "lm"
        d.line([x+15, y, ax-3, y], fill=RULE2, width=1)
        txt(d, (ax, y-9), lbl, zh(0, 15), fill=INK, anchor=anc)
        txt(d, (ax, y+10), "%.4f" % cer, num(13), fill=INK3, anchor=anc)

    d.line([60, H-92, W-60, H-92], fill=RULE2, width=1)
    txt(d, (60, H-68), "GLM-OCR 的 CER 中位为 0.0000，贴在底轴上；它的均值 0.2102 并不低，是「多数题满分、少数题崩」的分布。",
        zh(0, 14), fill=INK2)
    im.save(A + "/local-ai-ep12-fig2-散点.png")
    return "fig2"

# ================================================================ fig3 三栈
def fig3():
    H = 470
    im, d = new(W, H)
    txt(d, (60, 46), "同一套模型权重，只换推理栈", zh(0, 27, True))
    txt(d, (60, 88), "三者权重经逐字节核验为同一套，识别模型输出差为 0", zh(0, 15), fill=INK3)

    data = [("PaddleOCR 官方（Python 栈）", 22.19, ACC2, False),
            ("SimdPaddleOCR 受控（纯 C#）", 2.93,  ACC,  False),
            ("RapidOCRLite medium（C++）", 2.67,  ACC,  True)]
    top, rowh, bx0 = 176, 78, 400
    bw = W - bx0 - 190
    mx = 22.19
    for i, (lbl, v, col, best) in enumerate(data):
        y = top + i*rowh
        txt(d, (60, y+8), lbl, zh(0, 17, True if best else False), fill=INK if best else INK2)
        bl = bw * v / mx
        d.rectangle([bx0, y, bx0+bl, y+34], fill=col)
        txt(d, (bx0+bl+14, y+6), "%.2f s" % v, num(19), fill=INK)
        if best:
            txt(d, (bx0+bl+96, y+10), "最快", zh(0, 14), fill=ACC3)
        d.line([60, y+54, W-60, y+54], fill=RULE, width=1)

    d.line([60, H-84, W-60, H-84], fill=RULE2, width=1)
    txt(d, (60, H-60), "8.3 倍有前提：本机必须关掉 PaddleOCR 的 oneDNN 加速才能跑，参照方是被迫裸跑的。",
        zh(0, 14), fill=INK2)
    im.save(A + "/local-ai-ep12-fig3-三栈.png")
    return "fig3"

# ================================================================ fig 新样本构成
def figsamples():
    H = 460
    im, d = new(W, H)
    txt(d, (60, 46), "本期新造的 8 张样本", zh(0, 27, True))
    txt(d, (60, 88), "四类各两张，补的是上一期没有代表的场景", zh(0, 15), fill=INK3)

    cats = [("低分辨率", ["lowres_01", "lowres_02"], "真实底图降采样派生，试检测式引擎的下限"),
            ("竖排文字", ["vert_01", "vert_02"],     "竖排四列，试行分组与阅读顺序"),
            ("红章压字", ["seal_01", "seal_02"],     "印章盖在正文上，试端到端模型"),
            ("海报",     ["poster_01", "poster_02"], "字少排版怪，试版面理解")]
    cw = (W - 120 - 3*36) // 4
    top = 172
    for i, (nm, files, desc) in enumerate(cats):
        x0 = 60 + i*(cw+36)
        d.rectangle([x0, top, x0+cw, H-108], outline=RULE2, width=1)
        txt(d, (x0+18, top+16), nm, zh(0, 19, True))
        txt(d, (x0+cw-18, top+20), "2 张", num(14), fill=INK3, anchor="ra")
        d.line([x0+18, top+50, x0+cw-18, top+50], fill=RULE, width=1)
        # 描述按宽度自动换行
        words, line, lines = list(desc), "", []
        for ch in words:
            if wof(d, line+ch, zh(0, 14)) > cw-36:
                lines.append(line); line = ch
            else:
                line += ch
        if line: lines.append(line)
        for j, ln in enumerate(lines[:4]):
            txt(d, (x0+18, top+64+j*24), ln, zh(0, 14), fill=INK2)
        txt(d, (x0+18, H-140), "  ".join(f.replace("_", " ") for f in files),
            zh(0, 13), fill=INK3)

    d.line([60, H-84, W-60, H-84], fill=RULE2, width=1)
    txt(d, (60, H-60), "加上上一期沿用的 14 张与本期补跑的 12 张（含这 8 张），共 26 张。", zh(0, 14), fill=INK2)
    im.save(A + "/local-ai-ep12-fig-新样本构成.png")
    return "fig-新样本构成"

# ================================================================ 封面
def cover():
    w, h = 900, 383
    im, d = new(w, h)
    d.rectangle([0, 0, w, 6], fill=ACC)
    txt(d, (56, 76), "本地无显卡 AI · 第 12 期", zh(0, 16), fill=INK3)
    txt(d, (56, 128), "六套开源 OCR", zh(0, 40, True))
    txt(d, (56, 186), "同机实测", zh(0, 40, True))
    d.line([56, 254, 480, 254], fill=RULE2, width=1)
    txt(d, (56, 280), "26 张图 · 208 条测量 · 0.65 秒到 52.68 秒", zh(0, 17), fill=INK2)
    # 右侧竖线组装饰
    for i in range(9):
        x = 620 + i*28
        d.line([x, 96, x, 286], fill=RULE if i % 2 else RULE2, width=1)
    d.line([620, 286, 620+8*28, 286], fill=ACC, width=2)
    im.convert("RGB").save(A + "/local-ai-ep12-cover.jpg", quality=92)
    return "cover"

if __name__ == "__main__":
    out = [fig1(), fig2(), fig3(), figsamples(), cover()]
    # 样本图拷贝
    src = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/output/samples"
    n = 0
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".png"):
            im = Image.open(os.path.join(src, fn)).convert("RGB")
            im.thumbnail((760, 760), Image.LANCZOS)
            im.save(A + "/local-ai-ep12-samples/ep12-sample-" + fn, optimize=True)
            n += 1
    print("图表:", out, "| 样本拷贝:", n)
    for fn in sorted(os.listdir(A)):
        if "ep12" in fn and os.path.isfile(os.path.join(A, fn)):
            print("  %-46s %7.1f KB" % (fn, os.path.getsize(os.path.join(A, fn))/1024))
