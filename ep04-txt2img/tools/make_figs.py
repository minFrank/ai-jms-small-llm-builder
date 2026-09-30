# ep04 · 配图（5 张，全部由真实运行数据生成）
# 风格硬要求：浅色留白、精细规则线、等宽数字、无 emoji（用户 2026-09-25 逐字要求）
import json, os, sys, textwrap, datetime
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai-ep04"
os.makedirs(OUT, exist_ok=True)
LOG = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs"
KIT = r"D:/models/txt2img/kit"
PNG = r"D:/models/txt2img/out"

BG, INK, SUB, LINE, ACC = "#fbfcfe", "#16202c", "#6b7686", "#e6e9ee", "#1f5fd0"
FONT = "C:/Windows/Fonts/msyhbd.ttc"      # 微软雅黑粗
FONT_R = "C:/Windows/Fonts/msyh.ttc"
MONO = "C:/Windows/Fonts/consola.ttf"

def F(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def canvas(w, h):
    im = Image.new("RGB", (w, h), BG)
    return im, ImageDraw.Draw(im)

def text(d, xy, s, f, fill=INK, anchor=None):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)

def pick(font_ascii, font_cn, txt):
    """含中文字形就不能用 consola（会渲染成方块/问号）——2026-09-29 实测踩坑"""
    return font_cn if any('一' <= c <= '鿿' for c in txt) else font_ascii

def save(im, name):
    p = os.path.join(OUT, name)
    im.save(p, quality=94)
    # 2026-09-30 自检:排版图的底部 20 行应是纯底色。若不是,说明有内容画到画布外
    # —— fig2 曾因画布只按一行算高度,下排两格整行落在画布外(用户终审「图片显示不全」)。
    w, h = im.size
    px = list(im.crop((0, h - 20, w, h)).getdata())
    near = sum(1 for c in px if all(abs(c[k] - (251, 252, 254)[k]) <= 6 for k in range(3)))
    if near < 0.95 * len(px):
        print(f"  ⚠️ {name}: 底部 20 行非纯底色(占比 {near / len(px):.2f}) → 内容可能被画布裁掉")
    print("→", p, os.path.getsize(p), "B")


# ---------- 图1 目录结构 ----------
def fig1():
    im, d = canvas(1500, 900)
    f_t, f_b, f_n = F(FONT, 44), F(FONT_R, 30), F(MONO, 28)
    text(d, (80, 60), "一键包里就三样东西，解压后双击就行", f_t)
    d.line([(80, 130), (1420, 130)], fill=LINE, width=2)
    rows = [
        ("kit/", "文件夹", "解压后长这样"),
        ("├── 双击下载模型.bat", "约 1.4KB", "第一步：下 4.27GB 模型，下过自动跳过"),
        ("├── 双击生成.bat", "约 1.5KB", "第二步：读 prompt.txt 画出 result.png"),
        ("├── prompt.txt", "101B", "要画什么，用记事本改这一行"),
        ("├── sd-cli.exe", "656KB", "画图程序本体（引擎 MIT 许可）"),
        ("├── *.dll ×15", "约 34MB", "程序的依赖库，不用动"),
        ("└── v1-5-pruned-emaonly.safetensors", "4.27GB", "画图模型（下载 bat 放这里）"),
        ("", "", ""),
        ("跑完之后会多出来", "", ""),
        ("└── result.png", "约 480KB", "你画的第一张图"),
    ]
    y = 180
    for name, size, desc in rows:
        if not name:
            y += 26
            continue
        if not name.startswith(("├", "└", " ")):
            text(d, (80, y), name, F(FONT, 34), fill=ACC)
            y += 56
            continue
        text(d, (100, y), name, F(FONT_R, 27), fill=INK)   # 含中文文件名，禁用 consola
        text(d, (760, y), size, f_n, fill=SUB)              # 纯 ASCII 体积才用等宽
        text(d, (1000, y), desc, F(FONT_R, 27), fill=INK)
        y += 54
    text(d, (80, 830), "体积合计约 4.35GB，其中模型占 4.27GB（实测字节数见第五节）", F(FONT_R, 27), fill=SUB)
    save(im, "fig1-一键包结构.png")


# ---------- 图2 同种子对照 ----------
def fig2():
    picks = [("cpu_s20_p0_r0.png", "纯CPU · 20步", "243–265 秒"),
             ("vulkan_s20_p0_r0.png", "核显 · 20步", "94–96 秒"),
             ("cpu_s8_p0_r0.png", "纯CPU · 8步", "120–121 秒"),
             ("vulkan_s8_p0_r0.png", "核显 · 8步", "44 秒")]
    cell, pad, top = 470, 40, 150
    row_step = cell + 95                     # 两行之间的步进:图 + 标签 + 耗时
    # 2026-09-30 修:原高度 top+cell+150=770 只够第一行,第二行(y=715)整行画到
    # 画布外,下排两格只剩 34px 露出来(用户终审「图片显示不全」的根因)
    im, d = canvas(pad * 2 + cell * 2 + 30, top + row_step + cell + 150)
    f_t, f_c, f_s = F(FONT, 40), F(FONT, 29), F(FONT_R, 25)
    text(d, (pad, 40), "同一句话、同一种子：四个格子的成图与耗时", f_t)
    d.line([(pad, 112), (im.width - pad, 112)], fill=LINE, width=2)
    for i, (fn, label, t) in enumerate(picks):
        x = pad + (i % 2) * (cell + 30)
        y = top + (i // 2) * (cell + 95)
        p = os.path.join(PNG, fn)
        if not os.path.exists(p):
            continue
        img = Image.open(p).convert("RGB").resize((cell, cell), Image.LANCZOS)
        im.paste(img, (x, y))
        d.rectangle([x, y, x + cell, y + cell], outline=LINE, width=2)
        text(d, (x, y + cell + 14), label, f_c)
        text(d, (x, y + cell + 54), t, f_s, fill=ACC)
    save(im, "fig2-同种子对照.png")


# ---------- 图3 环境自检 ----------
def fig3():
    im, d = canvas(1500, 860)
    f_t, f_b, f_n = F(FONT, 42), F(FONT_R, 29), F(MONO, 27)
    text(d, (80, 55), "环境自检：两个后端都被认出来了", f_t)
    d.line([(80, 124), (1420, 124)], fill=LINE, width=2)
    lines = [
        "$ sd-cli.exe --list-devices",
        "ggml_vulkan: Found 1 Vulkan devices:",
        "ggml_vulkan: 0 = AMD Radeon(TM) Graphics (AMD proprietary driver)",
        "                | uma: 1 | fp16: 1 | warp size: 64",
        "Vulkan0    AMD Radeon(TM) Graphics",
        "CPU        AMD Ryzen 7 5700G with Radeon Graphics",
        "",
        "$ python -c \"import psutil; print(psutil.__version__)\"",
        "7.2.2",
        "",
        "# 模型体积核对（实下字节数）",
        "v1-5-pruned-emaonly.safetensors   4,265,146,304 B  = 4.27 GB",
        "# 引擎包（GitHub releases 实下）",
        "win-cpu-x64.zip      17,486,440 B",
        "win-vulkan-x64.zip   30,067,605 B",
    ]
    y = 165
    for ln in lines:
        if not ln:
            y += 18
            continue
        c = ACC if ln.startswith("$") else INK
        text(d, (80, y), ln, pick(f_n, F(FONT_R, 25), ln), fill=c)
        y += 46
    text(d, (80, 800), "意义：这一步把「跑到一半才报错」变成「一开始就知道行不行」", F(FONT_R, 27), fill=SUB)
    save(im, "fig3-环境自检.png")


# ---------- 图4 速度对比图 ----------
def fig4():
    data = [("纯CPU · 20步", 243.1, 265.3, "#9aa7bd"),
            ("核显 · 20步", 93.6, 95.7, ACC),
            ("纯CPU · 8步", 119.7, 121.1, "#9aa7bd"),
            ("核显 · 8步", 43.8, 44.3, ACC)]
    W, H = 1500, 940
    im, d = canvas(W, H)
    f_t, f_l, f_v, f_s = F(FONT, 42), F(FONT, 30), F(MONO, 30), F(FONT_R, 25)
    text(d, (80, 55), "画一张图要等多久：每个格子 4 次实测的区间", f_t)
    d.line([(80, 124), (1420, 124)], fill=LINE, width=2)
    x0, xmax, scale = 460, 900, 830 / 265.3
    y = 190
    for label, lo, hi, color in data:
        text(d, (80, y + 12), label, f_l)
        w1, w2 = (hi - lo) * scale, lo * scale
        d.rectangle([x0, y, x0 + w2 + max(w1, 6), y + 56], fill=color)
        if w1 > 4:
            d.rectangle([x0 + w2, y, x0 + w2 + w1, y + 56], fill="#c3cede")
        text(d, (x0 + w2 + max(w1, 6) + 18, y + 26),
             f"{lo:.0f}–{hi:.0f} 秒", F(FONT, 29), fill=INK, anchor="lm")  # 含中文「秒」禁用 consola
        y += 110
    # 坐标轴
    d.line([(x0, 180), (x0, y - 30)], fill=LINE, width=2)
    for v in (0, 60, 120, 180, 240):
        x = x0 + v * scale
        d.line([(x, 180), (x, y - 30)], fill=LINE, width=1)
        text(d, (x, y - 16), str(v), F(MONO, 24), fill=SUB, anchor="ma")
    text(d, (x0, y + 26), "秒", F(FONT_R, 24), fill=SUB)
    text(d, (80, y + 90), "同尺寸、同一种子、同两句话；每格 4 次取区间。20 步是默认画质，8 步是省时档。", F(FONT_R, 27), fill=SUB)
    text(d, (80, y + 134), "派生回算：核显比纯 CPU 快 2.66 倍（20步）/ 2.74 倍（8步）；8 步比 20 步省约一半时间。", F(FONT_R, 27), fill=INK)
    save(im, "fig4-速度对比.png")


# ---------- 图5 真实日志 ----------
def fig5():
    src = os.path.join(LOG, "bat-test.txt")
    if not os.path.exists(src):
        print("缺 bat-test.txt，跳过 fig5")
        return
    keep, raw = [], open(src, encoding="utf-8", errors="replace").read()
    for ln in raw.splitlines():
        s = ln.rstrip()
        if not s:
            continue
        if any(k in s for k in ("## 双击", "rc=", "跳过", "4265146304", "你要画的",
                                "正在生成", "sampling completed", "generate_image completed",
                                "save result image", "[完成]", "result.png:",
                                "loaded CPU backend", "total params memory size")):
            keep.append(s)
    keep = keep[:26]
    W = 1500
    H = 170 + len(keep) * 44 + 70
    im, d = canvas(W, H)
    f_t, f_n = F(FONT, 42), F(MONO, 26)
    text(d, (80, 50), "原始日志 · 未修改（一键包两个脚本的真实执行记录）", f_t)
    d.line([(80, 120), (W - 80, 120)], fill=LINE, width=2)
    y = 155
    for ln in keep:
        s = ln.replace("\x1b", "")
        s = re.sub(r"\[[0-9;]*[A-Za-z]", "", s) if (re := __import__("re")) else s
        s = s[:120]
        c = ACC if s.startswith(("##", "[跳过", "[完成")) else INK
        text(d, (80, y), s, pick(f_n, F(FONT_R, 24), s), fill=c)
        y += 44
    text(d, (80, H - 52), "日志随复刻包提供、可逐字核对；跑测耗时 229.9 秒与正文数字同批。", F(FONT_R, 26), fill=SUB)
    save(im, "fig5-一键包日志.png")


for fn in (fig1, fig2, fig3, fig4, fig5):
    try:
        fn()
    except Exception as e:
        print(f"{fn.__name__} 失败: {type(e).__name__}: {e}")
