#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ep25 补三张图：fig3 题组双指标、fig4 失败分布、fig5 摊薄效应。同一套浅色规范。"""
import os, sys, json, statistics
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets"
FONT = r"C:/Windows/Fonts/msyh.ttc"; MONO = r"C:/Windows/Fonts/consola.ttf"
def f(sz, mono=False): return ImageFont.truetype(MONO if mono else FONT, sz)
BG, FG, MUT, LINE = "#ffffff", "#1a1d21", "#8a919c", "#e5e7eb"
BAR, BAR2, BAD = "#2f6feb", "#b9c4d4", "#c2413b"
W = 1080

def base(h):
    im = Image.new("RGB", (W, h), BG); return im, ImageDraw.Draw(im)
def rules(d, y0, y1, step=34):
    for y in range(y0, y1, step): d.line([(60, y), (W-60, y)], fill="#f4f6f8", width=1)

ROWS = [g for g in json.load(open(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep25-数据汇总.json", encoding="utf-8"))["groups"]]

# ---------- fig3 题组：音频时长 vs 每秒音频耗时 ----------
def fig3():
    # 每秒音频耗时 = 每条各算 wall/audio 再取中位（与稿中 RTF 定义一致）
    # 不用「中位耗时 ÷ 中位音频」——两种算法最大差 20.7%，口径必须统一
    import json as _J
    _rows = [_J.loads(l) for l in open(r"D:/study/ai-jms/voice_samples/ep25_run/slot_0015/timing.jsonl", encoding="utf-8")
             if l.strip() and _J.loads(l).get("kind") == "cell"]
    _ok = [r for r in _rows if r.get("ok")]
    _g = {}
    for c in _ok: _g.setdefault(c.get("group"), []).append(c)
    eff = {k: statistics.median([x["wall_s"]/x["audio_s"] for x in v]) for k, v in _g.items()}

    im, d = base(620)
    d.text((60, 44), "五个题组：音频有多长，每秒音频要等多久", font=f(33), fill=FG)
    d.text((60, 90), "四引擎合并统计 · 每秒音频耗时 = 各条耗时÷音频时长的中位数", font=f(20), fill=MUT)
    x0, x1 = 250, W-170
    top, bh, gap = 140, 44, 30
    mx = max(r["dur_med"] for r in ROWS)
    m2 = max(eff.values())
    for i, r in enumerate(ROWS):
        y = top + i*(bh+gap)
        nm = r["group"].split(" ", 1)[1]
        d.text((60, y+bh//2-15), nm, font=f(23), fill=FG)
        w1 = int((x1-x0) * r["dur_med"]/mx)
        d.rectangle([x0, y, x0+w1, y+bh//2-4], fill=BAR)
        d.text((x0+w1+10, y-14), "%.1f s" % r["dur_med"], font=f(21, True), fill=FG)
        e = eff[r["group"]]
        w2 = int((x1-x0) * e/m2)
        d.rectangle([x0, y+bh//2+2, x0+w2, y+bh], fill=BAR2)
        d.text((x0+w2+10, y+bh//2-2), "%.1f s" % e, font=f(21, True), fill=MUT)
    d.line([(60, 540), (W-60, 540)], fill=LINE, width=2)
    d.rectangle([60, 562, 84, 578], fill=BAR);   d.text((94, 556), "音频中位时长", font=f(21), fill=FG)
    d.rectangle([280, 562, 304, 578], fill=BAR2); d.text((314, 556), "每秒音频耗时", font=f(21), fill=MUT)
    d.text((470, 556), "长句音频最长，但每秒反而最快 —— 固定开销被摊薄", font=f(21), fill=MUT)
    im.save(os.path.join(OUT, "localai-ep25-fig3-groups.png")); print("  fig3 ok")

# ---------- fig4 失败分布 ----------
def fig4():
    import json as J
    rows = [J.loads(l) for l in open(r"D:/study/ai-jms/voice_samples/ep25_run/slot_0015/timing.jsonl", encoding="utf-8")
            if l.strip() and J.loads(l).get("kind")=="cell"]
    engs = ["cosyvoice","voxcpm2","omnivoice","omnivoice-subprocess"]
    nm = {"cosyvoice":"CosyVoice3","voxcpm2":"VoxCPM2","omnivoice":"VoiceStudio 内建","omnivoice-subprocess":"VoiceStudio 子进程"}
    gs = ["1 基准短句","2 多音字","3 长句与停顿","4 数字与英文夹杂","5 语气与情感"]
    fail = {}
    for r in rows:
        if not r.get("ok"): fail[(r["engine"], r.get("group"))] = fail.get((r["engine"], r.get("group")), 0)+1
    im, d = base(560)
    d.text((60, 44), "12 格失败全部集中在两种跑法上", font=f(33), fill=FG)
    d.text((60, 90), "格数 · 越短越好 · 100 格里失败 12 格", font=f(20), fill=MUT)
    x0, x1 = 300, W-120
    _tot = {}
    for (_e, _g), _n in fail.items(): _tot[_e] = _tot.get(_e, 0) + _n
    mx = max([1] + list(_tot.values()))          # 按单引擎总失败数(11)定格宽
    top, bh, gap = 140, 40, 26
    for i, e in enumerate(engs):
        y = top + i*(bh+gap)
        d.text((60, y+bh//2-14), nm[e], font=f(23), fill=FG)
        cx = x0; unit = (x1-x0)//mx
        for g in gs:
            n = fail.get((e,g), 0)
            for _ in range(n):
                d.rectangle([cx, y, cx+unit-6, y+bh], fill=BAD)
                cx += unit
        tot = sum(fail.get((e,g),0) for g in gs)
        lx = min(max(cx + 10, x0), W - 110)   # 标签不越过画布右缘
        d.text((lx if tot else x0, y+bh//2-13), ("%d 格" % tot) if tot else "0 格", font=f(21, True), fill=BAD if tot else MUT)
    d.line([(60, 470), (W-60, 470)], fill=LINE, width=2)
    d.text((60, 492), "每格代表 1 格失败；格子颜色不分题组 —— 崩在哪一组见正文第五节", font=f(21), fill=MUT)
    im.save(os.path.join(OUT, "localai-ep25-fig4-fails.png")); print("  fig4 ok")

# ---------- fig5 摊薄效应 ----------
def fig5():
    # 与 fig3 同口径：逐条算 wall/audio 再取中位，不用中位相除
    import json as _J
    _rows = [_J.loads(l) for l in open(r"D:/study/ai-jms/voice_samples/ep25_run/slot_0015/timing.jsonl", encoding="utf-8")
             if l.strip() and _J.loads(l).get("kind") == "cell"]
    _ok = [r for r in _rows if r.get("ok")]
    _g = {}
    for c in _ok: _g.setdefault(c.get("group"), []).append(c)
    dur_med = {k: statistics.median([x["audio_s"] for x in v]) for k, v in _g.items()}
    eff_med = {k: statistics.median([x["wall_s"]/x["audio_s"] for x in v]) for k, v in _g.items()}
    tot_med = {k: statistics.median([x["wall_s"] for x in v]) for k, v in _g.items()}
    k0 = next(k for k in _g if k.startswith("1"))
    k3 = next(k for k in _g if k.startswith("3"))
    d1 = dur_med[k3]/dur_med[k0]        # 音频时长倍数
    e1 = eff_med[k3]/eff_med[k0]        # 每秒音频耗时倍数
    t1 = tot_med[k3]/tot_med[k0]        # 总耗时倍数

    im, d = base(470)
    d.text((60, 44), "长句为什么反而更划算", font=f(33), fill=FG)
    d.text((60, 90), "以基准短句为 1.0 倍基准", font=f(20), fill=MUT)
    x0, x1 = 300, W-200
    top, bh, gap = 150, 56, 40
    mx = 2.6
    for i, (nm_, v) in enumerate([("音频时长", d1), ("每秒音频耗时", e1)]):
        y = top + i*(bh+gap)
        d.text((60, y+bh//2-16), nm_, font=f(25), fill=FG)
        w = max(4, int((x1-x0)*v/mx))
        d.rectangle([x0, y, x0+w, y+bh], fill=BAR if i == 0 else BAR2)
        d.text((x0+w+14, y+bh//2-17), "%.2f 倍" % v, font=f(26, True), fill=FG)
    d.line([(60, 400), (W-60, 400)], fill=LINE, width=2)
    d.text((60, 418), "音频时长 ×%.2f，每秒音频耗时 ×%.2f —— 固定开销被摊薄"
           % (d1, e1), font=f(22), fill=MUT)
    d.text((60, 444), "每次调用的固定开销被长文本摊薄了", font=f(22), fill=MUT)
    im.save(os.path.join(OUT, "localai-ep25-fig5-amortize.png")); print("  fig5 ok")

print("生成:"); fig3(); fig4(); fig5()
for n in ["localai-ep25-fig3-groups.png","localai-ep25-fig4-fails.png","localai-ep25-fig5-amortize.png"]:
    p = os.path.join(OUT, n); print("  %-34s %.0f KB %s" % (n, os.path.getsize(p)/1024, Image.open(p).size))
