# -*- coding: utf-8 -*-
"""ep11 造样本 v2：真实来源优先 + 合成版面补充，逐张记来源与变换参数。

样本来源分三类（报告里逐张标注）：
  real_pdf   真实 PDF 原页渲染（arXiv 论文，公开可复刻）
  real_web   真实网页 headless Chrome 截图（GT 取自 DOM 文本层）
  synthetic  按真实票据/表格/说明书版式合成的版面（GT 精确）
退化类（倾斜/低对比）只作用在**真实底图**上，保留原图与参数。
"""
import hashlib
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output", "samples")
SRC = os.path.join(BASE, "output", "src")
GT = os.path.join(BASE, "gt")
for d in (OUT, SRC, GT):
    os.makedirs(d, exist_ok=True)

F_SONG = "C:/Windows/Fonts/simsun.ttc"
F_KAI = "C:/Windows/Fonts/simkai.ttf"
F_HEI = "C:/Windows/Fonts/simhei.ttf"
F_YAHEI = "C:/Windows/Fonts/msyh.ttc"
F_FANG = "C:/Windows/Fonts/simfang.ttf"
CHROME = "C:/Users/Frank/AppData/Local/Google/Chrome/Application/chrome.exe"
PROXY = "http://127.0.0.1:7897"


def font(p, s):
    return ImageFont.truetype(p, s)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def para(d, xy, text, f, fill, maxw, lh):
    x, y = xy
    line = ""
    for ch in text:
        if d.textlength(line + ch, font=f) > maxw or ch == "\n":
            d.text((x, y), line, font=f, fill=fill)
            y += lh
            line = "" if ch == "\n" else ch
        else:
            line += ch
    if line:
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


# ---------- 真实来源 1：arXiv PDF 原页 ----------
def fetch_pdf(url, name):
    import requests
    dst = os.path.join(SRC, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 100000:
        return dst
    proxies = {"http": PROXY, "https": PROXY}
    last = None
    for px in (proxies, None):
        try:
            r = requests.get(url, timeout=120, proxies=px)
            if r.status_code == 200 and len(r.content) > 100000:
                open(dst, "wb").write(r.content)
                return dst
            last = "status %s len %d" % (r.status_code, len(r.content))
        except Exception as e:  # noqa
            last = str(e)
    raise SystemExit("pdf download failed: %s" % last)


def pdf_pages(pdf_path, pages):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_path)
    out = []
    for pno in pages:
        page = doc[pno]
        bmp = page.render(scale=2.2)
        pil = bmp.to_pil().convert("RGB")
        ip = os.path.join(SRC, "pdf_p%d.png" % (pno + 1))
        pil.save(ip)
        tp = os.path.join(SRC, "pdf_p%d.txt" % (pno + 1))
        if not os.path.exists(tp):
            txt = page.get_textpage().get_text_range()
            open(tp, "w", encoding="utf-8").write(txt)
        out.append((pno + 1, ip, open(tp, encoding="utf-8").read()))
    return out


# ---------- 真实来源 2：真实网页截图 ----------
def shot(url, name, width=1280, height=2400):
    """真实网页 -> 打印成 PDF -> 渲染成 PNG；GT 取 PDF 文本层（与画面逐字对应）。

    早期版本用 --screenshot + DOM 文本层当 GT：DOM 是整页文本（20 万字符），
    而截图只含视口那一块，CER 会变成 ~0.999 的无意义值，故改为 PDF 文本层。
    """
    import pypdfium2 as pdfium
    pdfp = os.path.join(SRC, name + ".pdf")
    for p in (pdfp,):
        if os.path.exists(p):
            os.remove(p)
    cmd = [CHROME, "--headless=new", "--disable-gpu",
           "--user-data-dir=" + os.path.abspath(os.path.join(SRC, "chrome-" + name)),
           "--virtual-time-budget=12000", "--no-pdf-header-footer",
           "--print-to-pdf=" + pdfp, url]
    subprocess.run(cmd, capture_output=True, timeout=240)
    if not os.path.exists(pdfp) or os.path.getsize(pdfp) < 20000:
        raise SystemExit("print-to-pdf failed: " + url)
    doc = pdfium.PdfDocument(pdfp)
    page = doc[0]
    pil = page.render(scale=2.0).to_pil().convert("RGB")
    png = os.path.join(SRC, name + ".png")
    pil.save(png)
    txt = page.get_textpage().get_text_range()
    if len(txt.strip()) < 80:
        raise SystemExit("pdf text layer too short: " + url)
    return png, txt


def dom_text(dom_path):
    """从 DOM 提取可见文本（document order），作为截图 GT。"""
    import re
    html = open(dom_path, encoding="utf-8", errors="replace").read()
    html = re.sub(r"(?is)<script.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?</noscript>", " ", html)
    html = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h[1-6]|/td)[^>]*>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    import html as htmllib
    txt = htmllib.unescape(html)
    lines = [re.sub(r"\s+", " ", l).strip() for l in txt.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines)


# ---------- 合成版面 ----------
INV1 = """【实测样例 非真实票据】
增值税电子普通发票
发票代码 044032200111
发票号码 25893417
开票日期 2026年03月12日
购买方 南京星桥信息有限公司
纳税人识别号 91320100MA1MPQX23K
项目名称 规格 数量 单价 金额 税率 税额
信息技术服务费 次 1 8000.00 8000.00 6% 480.00
数据存储服务 GB月 12 150.00 1800.00 6% 108.00
价税合计 人民币 壹万零叁佰捌拾捌元整 10388.00
销售方 杭州云禾科技有限公司
收款人 李明 复核 王芳 开票人 张伟"""

INV2 = """【实测样例 非真实票据】
电子发票 普通发票
发票号码 31905672
开票日期 2026年06月28日
购买方 陈静
购买方身份证号 320102199003152418
货物或应税劳务名称 数量 单价 金额 税额
办公用品 文件夹 20 12.50 250.00 3.25
办公用品 中性笔 60 2.80 168.00 2.18
打印纸 A4 5kg 32.00 160.00 2.08
合计 578.00 7.51
开票人 赵敏
备注栏 本发票为实测样例 不作报销凭证"""

TBL1 = """初二3班期中成绩表
姓名 语文 数学 英语 物理 总分
陈思远 92 108 96 88 384
李雨桐 87 115 91 93 386
王浩然 78 96 82 75 331
周子涵 95 102 98 90 385
孙一诺 83 89 88 71 331
班级平均分 87.0 102.0 91.0 83.4 363.4"""

TBL2 = """家庭月度开支明细 2026年9月
类别 项目 金额 占比 备注
居住 房贷 6800.00 46.3% 每月15日扣款
居住 物业费 420.00 2.9% 按季预缴
食品 菜场 1860.00 12.6% 现金为主
食品 超市 930.00 6.3% 周末采购
交通 地铁 268.00 1.8% 月票
交通 加油 600.00 4.1% 92号汽油
教育 课外书 356.00 2.4% 网购
教育 文具 88.00 0.6% 学校门口
医疗 门诊 240.00 1.6% 社区医院
合计 14562.00 100.0% 记账人 林岚"""

HARD2 = """产品说明书 智能空气检测仪 型号 KJ-2000
一 产品参数
额定电压 DC 5V 2A  额定功率 8W  颗粒物CADR 200立方米每小时
甲醛CADR 80立方米每小时  噪声 32至66分贝  适用面积 23至40平方米
二 指示灯说明
绿色 常亮 空气质量优良  黄色 常亮 轻度污染  红色 常亮 中重度污染
蓝色 常亮 正在联网配网  白色 闪烁 固件升级中 请勿断电
三 故障处理
E01 传感器无响应 请断电重启  E02 风机堵转 请清理进风口
E03 网络超时 请检查路由器 2.4G 频段  E04 存储异常 请恢复出厂设置
四 售后 保修期一年 全国联保 客服电话 400-820-1234 服务时间 周一至周日 九点至二十一点"""


def render_doc(text, w, fnt, lh, pad=48, title_font=None):
    # 画布先给足高度再裁：直接在 200px 高的画布上画会被裁掉（踩过，只渲染出前 4 行）
    img = Image.new("RGB", (w, 6000), "white")
    d = ImageDraw.Draw(img)
    y = pad
    for i, ln in enumerate(text.split("\n")):
        f = title_font if (i == 0 and title_font) else fnt
        y = para(d, (pad, y), ln, f, "black", w - 2 * pad, lh)
        y += 6
    return img.crop((0, 0, w, y + pad))


def render_table(text, colw, fnt, lh, pad=44):
    rows = [r.split(" ") for r in text.split("\n")]
    ncol = len(rows[1])
    img = Image.new("RGB", (sum(colw) + 2 * pad, 3000), "white")
    d = ImageDraw.Draw(img)
    d.text((pad, pad), rows[0][0], font=font(F_HEI, 30), fill="black")
    top = pad + 60
    y = top
    heights = []
    for r in rows[1:]:
        h = 0
        x = pad
        for ci, cell in enumerate(r[:ncol]):
            yy = para(d, (x + 10, y + 10), cell, fnt, "black", colw[ci] - 20, lh)
            h = max(h, yy - y - 10)
        heights.append(h + 20)
        y += h + 20
    total_h = y - top
    for ri in range(len(rows[1:]) + 1):
        yy = top + sum(heights[:ri])
        d.line([(pad, yy), (pad + sum(colw), yy)], fill="black", width=2)
    x = pad
    d.line([(pad, top), (pad, top + total_h)], fill="black", width=2)
    for ci in range(ncol + 1):
        d.line([(x, top), (x, top + total_h)], fill="black", width=2)
        if ci < ncol:
            x += colw[ci]
    return img.crop((0, 0, sum(colw) + 2 * pad, top + total_h + pad))


def degrade_lowcontrast(img):
    g = ImageEnhance.Contrast(img.convert("L")).enhance(0.28)
    g = ImageEnhance.Brightness(g).enhance(1.12)
    out = g.convert("RGB")
    d = ImageDraw.Draw(out)
    W, H = out.size
    for i in range(60):
        a = int(200 * (1 - i / 60) ** 2)
        d.pieslice([W - 520 + i * 2, -460 + i * 2, W + 420 - i * 2, 520 - i * 2], 0, 360,
                   fill=(255, 255, 255, a))
    return out


def skew(img, angle):
    g = img.convert("L").rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=255)
    W, H = g.size
    canvas = Image.new("L", (W + 120, H + 120), 255)
    canvas.paste(g, (60, 60))
    return canvas.convert("RGB")


meta = []


def save(img, name, gt_text, category, source, note="", gt_extra=None):
    p = os.path.join(OUT, name + ".png")
    img.save(p)
    gp = os.path.join(GT, name + ".txt")
    with open(gp, "w", encoding="utf-8") as f:
        f.write(gt_text)
    m = {"name": name, "img": p, "gt": gp, "category": category,
         "source": source, "note": note,
         "sha256_16": sha(p), "gt_sha256_16": sha(gp)}
    m["w"], m["h"] = Image.open(p).size
    m["bytes"] = os.path.getsize(p)
    if gt_extra:
        with open(os.path.join(GT, name + ".table.json"), "w", encoding="utf-8") as f:
            json.dump(gt_extra, f, ensure_ascii=False, indent=1)
        m["table_gt"] = name + ".table.json"
    meta.append(m)
    return m


def table_gt(text):
    rows = [r.split(" ") for r in text.split("\n")]
    return {"rows": len(rows[1:]), "cols": len(rows[1]),
            "header": rows[1], "title": rows[0][0],
            "cells": rows[1:], "join": "space"}


def main():
    # 1) 真实 PDF 页（GOT-OCR2.0 论文，公开 arXiv 2409.01704）
    pdf = fetch_pdf("https://arxiv.org/pdf/2409.01704", "got-ocr-paper.pdf")
    pages = pdf_pages(pdf, [0, 1, 2, 3])
    # GT 用 PDF 内嵌文本层；报告里标注「GT 来自 PDF 文本层」
    save(Image.open(pages[0][1]), "book_01", pages[0][2], "书页",
         "real_pdf", "arXiv 2409.01704 第 %d 页，PDF 文本层作 GT" % pages[0][0])
    save(Image.open(pages[1][1]), "book_02", pages[1][2], "书页",
         "real_pdf", "arXiv 2409.01704 第 %d 页，PDF 文本层作 GT" % pages[1][0])

    # 2) 真实网页（打印成 PDF 后渲染，GT = PDF 文本层）
    png1, txt1 = shot("https://www.baidu.com", "baidu")
    save(Image.open(png1), "shot_01", txt1, "截图",
         "real_web_pdf", "baidu.com 首页打印为 PDF 后渲染，GT=PDF 文本层")
    png2, txt2 = shot("https://www.gov.cn/", "govcn")
    save(Image.open(png2), "shot_02", txt2, "截图",
         "real_web_pdf", "gov.cn 首页打印为 PDF 后渲染，GT=PDF 文本层")

    # 3) 合成版面（真实票据/表格/说明书版式）
    inv1 = render_doc(INV1, 1100, font(F_SONG, 24), 40, title_font=font(F_HEI, 34))
    inv2 = render_doc(INV2, 1050, font(F_SONG, 25), 42, title_font=font(F_HEI, 32))
    tbl1 = render_table(TBL1, [230, 150, 150, 150, 150, 170], font(F_SONG, 26), 36)
    tbl2 = render_table(TBL2, [170, 250, 180, 150, 300], font(F_SONG, 24), 34)
    hard2 = render_doc(HARD2, 1020, font(F_FANG, 19), 29, pad=30)
    save(inv1, "invoice_01", INV1, "电子发票", "synthetic", "按真实票样版式合成")
    save(inv2, "invoice_02", INV2, "电子发票", "synthetic", "按真实票样版式合成")
    save(tbl1, "table_01", TBL1, "表格", "synthetic", "按真实成绩表版式合成",
         table_gt(TBL1))
    save(tbl2, "table_02", TBL2, "表格", "synthetic", "按真实记账表版式合成",
         table_gt(TBL2))
    save(hard2, "hard_02", HARD2, "混合难例", "synthetic", "19pt 仿宋 密集混排")

    # 4) 退化只作用在真实底图上
    p3 = pages[2]
    save(Image.open(p3[1]), "hard_01", p3[2], "混合难例",
         "real_pdf", "arXiv 2409.01704 第 %d 页 双栏小字" % p3[0])
    save(skew(Image.open(pages[0][1]), 7), "skew_01", pages[0][2], "倾斜拍照",
         "real_pdf+degrade", "底图 = book_01 同页，整体旋转 7 度（合成退化，非真实拍照）")
    save(skew(Image.open(pages[1][1]), 13), "skew_02", pages[1][2], "倾斜拍照",
         "real_pdf+degrade", "底图 = book_02 同页，整体旋转 13 度（合成退化，非真实拍照）")
    save(degrade_lowcontrast(Image.open(png1)), "lc_01", txt1, "低对比反光",
         "real_web+degrade", "底图 = shot_01 同页，对比度 0.28 + 右上反光（合成退化）")
    save(degrade_lowcontrast(Image.open(pages[3][1])), "lc_02", pages[3][2], "低对比反光",
         "real_pdf+degrade", "底图 = arXiv 第 %d 页，对比度 0.28 + 右上反光（合成退化）" % pages[3][0])

    with open(os.path.join(GT, "samples_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("样本 %d 张" % len(meta))
    for m in meta:
        print("  %-11s %-7s %-18s %dx%d %7dB %s" %
              (m["name"], m["category"], m["source"], m["w"], m["h"],
               m["bytes"], m["sha256_16"]))


if __name__ == "__main__":
    main()
