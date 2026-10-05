# ep04 · 补测配图：fig7 分辨率曲线 / fig8 题材鲁棒性
import json, os
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai-ep04"
PNG = r"D:/models/txt2img/out"
LOG = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs"
BG, INK, SUB, LINE, ACC, BAD = "#fbfcfe", "#16202c", "#6b7686", "#e6e9ee", "#1f5fd0", "#b91c1c"
FONT = "C:/Windows/Fonts/msyhbd.ttc"
FONT_R = "C:/Windows/Fonts/msyh.ttc"
MONO = "C:/Windows/Fonts/consola.ttf"

def F(p, s):
    try:
        return ImageFont.truetype(p, s)
    except Exception:
        return ImageFont.load_default()

def pick(ascii_f, cn_f, txt):
    return cn_f if any("一" <= c <= "鿿" for c in txt) else ascii_f

def save(im, name):
    p = os.path.join(OUT, name)
    im.save(p, quality=94)
    print("→", p, os.path.getsize(p), "B")

# ---------- fig7 分辨率曲线 ----------
def fig7():
    rows = [
        ("512 × 512", "243–265 秒", "94–96 秒", "两个后端都能画", INK),
        ("768 × 768", "770–771 秒", "507–507 秒", "两个后端都能画，核显优势收窄到约 1.5 倍", INK),
        ("1024 × 1024", "1951–1973 秒", "失败", "纯 CPU 能画但要 33 分钟；核显画到解码那步崩", BAD),
    ]
    W, H = 1500, 860
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t, f_h, f_c, f_n, f_s = F(FONT, 42), F(FONT, 30), F(FONT, 30), F(MONO, 28), F(FONT_R, 26)
    d.text((80, 55), "画多大：三个分辨率档的实测（各 2 次，20 步）", font=f_t, fill=INK)
    d.line([(80, 124), (1420, 124)], fill=LINE, width=2)
    cols = [(80, "尺寸", f_h), (470, "纯 CPU", f_h), (810, "核显", f_h), (1130, "备注", f_h)]
    for x, t, f in cols:
        d.text((x, 155), t, font=f, fill=SUB)
    y = 215
    for size, cpu, vul, note, color in rows:
        d.line([(80, y - 16), (1420, y - 16)], fill=LINE, width=1)
        d.text((80, y), size, font=f_c, fill=INK)
        d.text((470, y), cpu, font=pick(f_n, f_c, cpu), fill=INK)
        d.text((810, y), vul, font=pick(f_n, f_c, vul), fill=color)
        # 备注折行
        ty = y
        for seg in [note[i:i+16] for i in range(0, len(note), 16)]:
            d.text((1130, ty), seg, font=f_s, fill=SUB)
            ty += 36
        y += 130
    d.line([(80, y - 16), (1420, y - 16)], fill=LINE, width=2)
    notes = [
        "分辨率每翻一档，等待时间大约翻两到三倍 —— 像素量是按边长平方涨的。",
        "核显在 512 档领先 2.7 倍，768 档缩到约 1.5 倍：图越大，核显越吃力。",
        "核显 1024 失败的原始报错：vk::Queue::submit: ErrorOutOfDeviceMemory",
        "（采样 1392 秒已跑完，最后解码那步显存不够）—— 日志见 raw-B_vulkan_1024_r0.txt。",
    ]
    for i, n in enumerate(notes):
        d.text((80, y + 14 + i * 40), n, font=f_s, fill=INK if i == 0 else SUB)
    save(im, "fig7-分辨率曲线.png")

# ---------- fig8 题材鲁棒性 ----------
def fig8():
    topics = [("portrait", "老人肖像"), ("crowd", "人群街市"),
              ("chart", "图表"), ("anime", "动漫"), ("macro", "微距")]
    cell, pad, top = 260, 60, 175
    W = pad * 2 + cell * 5 + 40 * 4
    H = top + cell + 300
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t, f_l, f_s = F(FONT, 42), F(FONT, 28), F(FONT_R, 25)
    d.text((pad, 45), "五类题材各画一次：4 类干净可用，图表类文字会变乱码", font=f_t, fill=INK)
    d.line([(pad, 118), (W - pad, 118)], fill=LINE, width=2)
    for i, (key, label) in enumerate(topics):
        p = os.path.join(PNG, f"C_cpu_{key}.png")
        if not os.path.exists(p):
            continue
        x = pad + i * (cell + 40)
        img = Image.open(p).convert("RGB").resize((cell, cell), Image.LANCZOS)
        im.paste(img, (x, top))
        d.rectangle([x, top, x + cell, top + cell], outline=LINE, width=2)
        d.text((x, top + cell + 16), label, font=f_l, fill=INK)
        st = "干净可用" if key != "chart" else "文字乱码"
        d.text((x, top + cell + 58), st, font=f_s, fill=ACC if key != "chart" else "#b45309")
    lines = [
        "实测口径：5 类题材 × 双后端 × 20 步，共 10 次全部出图成功，无崩溃。",
        "图表类能画出柱子和布局，但上面的字是乱码 —— 图表要自己做，别让它画；",
        "这与第三节「图里写中文必乱」是同一条限制的两个面。",
    ]
    for i, l in enumerate(lines):
        d.text((pad, top + cell + 106 + i * 40), l, font=f_s, fill=SUB if i else INK)
    save(im, "fig8-题材鲁棒性.png")

for fn in (fig7, fig8):
    try:
        fn()
    except Exception as e:
        print(f"{fn.__name__} 失败: {type(e).__name__}: {e}")
