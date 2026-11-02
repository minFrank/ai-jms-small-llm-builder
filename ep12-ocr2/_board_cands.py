# -*- coding: utf-8 -*-
"""总榜图表化：三个候选样式，同一份数据。手机宽度 900px 画布（2x 供 480 显示）。"""
import os
from PIL import Image, ImageDraw, ImageFont

A = r"C:/Users/Frank/AppData/Local/hermes/workspace/_themes"
os.makedirs(A, exist_ok=True)
FZH, FZHB, FNUM = "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/consola.ttf"
def zh(s,b=False): return ImageFont.truetype(FZHB if b else FZH, s)
def nu(s): return ImageFont.truetype(FNUM, s)

INK, INK2, INK3 = (30,34,40), (104,112,124), (152,160,172)
RULE, RULE2, BG, PANEL = (232,236,242), (210,216,224), (255,255,255), (248,250,253)
BLUE, ORANGE, TEAL, GREY = (36,101,190), (200,96,52), (44,134,108), (150,158,170)

# 配置, CER中位, 耗时s, 内存MB, 满分, 组
ROWS = [
 ("RapidOCRLite small",  0.0242,  0.65,  323, "10/24", "det"),
 ("RapidOCRLite medium", 0.0250,  2.67,  686, "10/24", "det"),
 ("SimdPaddleOCR 默认",  0.0250,  2.77,  745,  "9/24", "det"),
 ("SimdPaddleOCR 受控",  0.0246,  2.93,  754, "10/24", "det"),
 ("EasyOCR",             0.0656,  4.74, 1529,  "1/24", "det"),
 ("PaddleOCR 官方",      0.0137, 22.19, 1928, "11/24", "det"),
 ("LightOnOCR-3 剥标记",  0.0263, 26.77, 1562,  "9/24", "e2e"),
 ("LightOnOCR-3 原始输出",0.5167, 26.77, 1562,  "2/24", "e2e"),
 ("GLM-OCR 0.9B",        0.0000, 52.68, 3361, "13/24", "e2e"),
]

def new(w,h):
    im = Image.new("RGB",(w,h),BG); return im, ImageDraw.Draw(im)
def txt(d,xy,s,f,fill=INK,anchor="la"): d.text(xy,s,font=f,fill=fill,anchor=anchor)
def wd(d,s,f): return d.textbbox((0,0),s,font=f)[2]

# ============================================================ A 三联小图
def candA():
    W,H = 900, 1080
    im,d = new(W,H)
    txt(d,(48,44),"总榜 · 三项指标",zh(30,True))
    txt(d,(48,88),"24 张样本中位 · 同机纯 CPU",zh(16),fill=INK3)
    top, rowh = 158, 74
    name_w = 250
    metrics = [("字错率中位", [r[1] for r in ROWS], "%.4f", BLUE),
               ("单页耗时（秒）", [r[2] for r in ROWS], "%.2f", ORANGE),
               ("内存峰值（MB）",[r[3] for r in ROWS], "%d", TEAL)]
    colw = (W - 96 - name_w - 2*28) // 3
    for mi,(mt, vals, fmt, col) in enumerate(metrics):
        x0 = 48 + name_w + mi*(colw+28)
        txt(d,(x0, top-40), mt, zh(17,True), fill=INK2)
        d.line([x0, top-14, x0+colw, top-14], fill=RULE2, width=1)
        mx = max(vals)
        for i,r in enumerate(ROWS):
            y = top + i*rowh
            v = vals[i]; bl = max(2, (colw-92)*v/mx)
            c = col if r[5]=="det" else ORANGE
            if mi==1: c = ORANGE if r[5]=="det" else ORANGE
            d.rectangle([x0, y+8, x0+bl, y+28], fill=c)
            txt(d,(x0+bl+8, y+7), fmt % v, nu(14), fill=INK)
    # 左侧配置名 + 满分
    for i,r in enumerate(ROWS):
        y = top + i*rowh
        txt(d,(48, y+6), r[0], zh(16), fill=INK)
        txt(d,(48, y+30), r[4]+" 满分", nu(13), fill=INK3)
        d.line([48, y+54, W-48, y+54], fill=RULE, width=1)
    d.line([48,H-72,W-48,H-72], fill=RULE2, width=1)
    txt(d,(48,H-50),"蓝色为检测式，橙色为端到端。LightOnOCR-3 两行是同一批输出的两种算法。",zh(14),fill=INK2)
    im.save(A+"/candA-三联小图.png"); return "A"

# ============================================================ B 气泡散点
def candB():
    W,H = 900, 1000
    im,d = new(W,H)
    txt(d,(48,44),"总榜 · 气泡散点",zh(30,True))
    txt(d,(48,88),"横轴耗时 · 纵轴字错率 · 气泡大小为内存",zh(16),fill=INK3)
    L,R_,T,B = 110, W-60, 160, H-150
    d.rectangle([L,T,R_,B], fill=PANEL); d.rectangle([L,T,R_,B], outline=RULE2, width=1)
    import math
    xs=[r[2] for r in ROWS]; ys=[r[1] for r in ROWS]; ms=[r[3] for r in ROWS]
    def px(v): return L + (R_-L)*(math.log10(v+0.5)-math.log10(0.5))/(math.log10(53.5)-math.log10(0.5))
    def py(v): return B - (B-T)*v/0.56
    def pr(v): return 12 + 46*(v-300)/3061
    for gv in [0,0.1,0.2,0.3,0.4,0.5]:
        y=py(gv); d.line([L,y,R_,y], fill=RULE, width=1)
        txt(d,(L-10,y),"%.1f"%gv, nu(13), fill=INK3, anchor="rm")
    for gv in [1,2,5,10,20,50]:
        x=px(gv); d.line([x,T,x,B], fill=RULE, width=1)
        txt(d,(x,B+12),str(gv), nu(13), fill=INK3, anchor="ma")
    txt(d,((L+R_)//2,B+42),"单页耗时中位（秒，对数刻度）", zh(15), fill=INK2, anchor="ma")
    txt(d,(36,(T+B)//2),"字错率中位", zh(15), fill=INK2, anchor="mm")
    # 左下角整簇（CER 与耗时都接近的四个检测式配置）：画圈 + 引线，不逐个叠标签
    near = [r for r in ROWS if r[2] < 6]
    cxs = [px(r[2]) for r in near]; cys = [py(r[1]) for r in near]
    cx, cy = sum(cxs)/len(cxs), sum(cys)/len(cys)
    rad = max(max(cxs)-min(cxs), max(cys)-min(cys))/2 + 30
    d.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=BLUE, width=1)
    for r in near:
        x, y = px(r[2]), py(r[1])
        d.ellipse([x-6, y-6, x+6, y+6], fill=BLUE)
    lx, ly = cx-rad-14, cy-rad-30
    d.line([cx-rad*0.72, cy-rad*0.72, lx, ly], fill=BLUE, width=1)
    txt(d,(lx-12, ly-42), "四个检测式配置", zh(15,True), fill=BLUE, anchor="ra")
    txt(d,(lx-12, ly-20), "耗时 0.65–2.93 秒", nu(13), fill=INK2, anchor="ra")
    txt(d,(lx-12, ly-2),  "CER 0.0242–0.0250", nu(13), fill=INK2, anchor="ra")
    # 其余逐个标
    for name,c,t_,m,pct,g in ROWS:
        if t_ < 6: continue
        x, y = px(t_), py(c)
        col = BLUE if g=="det" else ORANGE
        d.ellipse([x-9, y-9, x+9, y+9], fill=col, outline=(255,255,255), width=2)
        lbl = name.replace("RapidOCRLite","Rcl").replace("SimdPaddleOCR","Simd").replace("LightOnOCR-3","LightOn").replace(" 原始输出"," 原始").replace(" 剥标记"," 剥标")
        # 右半区标签朝左，避免跑出画布
        if x > (L+R_)*0.56:
            d.line([x-15, y, x-30, y], fill=RULE2, width=1)
            txt(d,(x-36, y-9), lbl, zh(14), fill=INK, anchor="rm")
            txt(d,(x-36, y+9), "%d MB"%m, nu(12), fill=INK3, anchor="rm")
        else:
            d.line([x+15, y, x+30, y], fill=RULE2, width=1)
            txt(d,(x+36, y-9), lbl, zh(14), fill=INK, anchor="lm")
            txt(d,(x+36, y+9), "%d MB"%m, nu(12), fill=INK3, anchor="lm")
    d.line([48,H-92,W-48,H-92], fill=RULE2, width=1)
    txt(d,(48,H-70),"左下角是理想位置。GLM-OCR 字错率最低但最慢最重；Rcl-small 最快最轻但字错率不是最低。",zh(14),fill=INK2)
    im.save(A+"/candB-气泡散点.png"); return "B"

# ============================================================ C 排行卡片
def candC():
    W,H = 900, 1180
    im,d = new(W,H)
    txt(d,(48,44),"总榜 · 排行卡片",zh(30,True))
    txt(d,(48,88),"四项指标横向对比 · 越长越好/越差看方向",zh(16),fill=INK3)
    # 表头
    top=176
    cols = [("字错率中位",300),("单页耗时",470),("内存峰值",640),("满分张数",830)]
    for name,x in cols:
        txt(d,(x, top-34), name, zh(15,True), fill=INK2, anchor="ra")
    d.line([48,top-12,W-48,top-12], fill=RULE2, width=2)
    rowh=100
    maxc=max(r[1] for r in ROWS); maxt=max(r[2] for r in ROWS); maxm=max(r[3] for r in ROWS)
    for i,r in enumerate(ROWS):
        y=top+i*rowh
        col = BLUE if r[5]=="det" else ORANGE
        # 排名
        d.rectangle([48,y+16,60,y+34], fill=col)
        txt(d,(54,y+16),str(i+1), nu(13), fill=(255,255,255), anchor="ma")
        txt(d,(72,y+10), r[0], zh(17,True), fill=INK)
        # 三条迷你条
        for bi,(val, mx, x, wmax, fmt) in enumerate([
            (r[1],maxc,300,150,"%.4f"), (r[2],maxt,470,150,"%.2f"), (r[3],maxm,640,150,"%d")]):
            bl = max(2, wmax*val/mx)
            yy = y+14+bi*20
            d.rectangle([x-bl+wmax*0 if False else x, yy, x+bl, yy+12], fill=col)
            txt(d,(x+wmax+8, yy-3), fmt % val, nu(13), fill=INK)
        txt(d,(830,y+20), r[4], nu(17), fill=INK)
        txt(d,(830,y+42), "满分", zh(12), fill=INK3)
        d.line([48,y+76,W-48,y+76], fill=RULE, width=1)
    d.line([48,H-72,W-48,H-72], fill=RULE2, width=1)
    txt(d,(48,H-50),"三条迷你条同向，越长表示越大：字错率越大越差、耗时越长越差、内存越大越差。",zh(14),fill=INK2)
    im.save(A+"/candC-排行卡片.png"); return "C"

out=[candA(),candB(),candC()]
print("生成:", out)
for f in sorted(os.listdir(A)):
    if f.startswith("cand"): print("  %-28s %5d KB" % (f, os.path.getsize(A+"/"+f)//1024))
