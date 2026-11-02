# -*- coding: utf-8 -*-
"""ep12 成稿配图重绘 · 统一 1080 画布（公众号 2x，手机显示约 540，字号按 1x 可读设计）。
浅色留白、精细规则线、等宽数字、禁 emoji。"""
import os, json, pathlib
from PIL import Image, ImageDraw, ImageFont

A = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets"
os.makedirs(A, exist_ok=True)
FZH, FZHB, FNUM = "C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/msyhbd.ttc","C:/Windows/Fonts/consola.ttf"
def zh(s,b=False): return ImageFont.truetype(FZHB if b else FZH, s)
def nu(s): return ImageFont.truetype(FNUM, s)
INK,INK2,INK3 = (28,32,38),(100,108,120),(150,158,170)
RULE,RULE2,BG,PANEL = (230,234,240),(206,212,222),(255,255,255),(247,249,252)
BLUE,ORANGE,TEAL,GREEN = (34,96,182),(198,92,48),(40,128,102),(60,140,90)
W = 1080

def new(h):
    im=Image.new("RGB",(W,h),BG); return im, ImageDraw.Draw(im)
def txt(d,xy,s,f,fill=INK,anchor="la"): d.text(xy,s,font=f,fill=fill,anchor=anchor)

ROWS = [  # 名, CER, 耗时s, 内存MB, 满分, 组
 ("RapidOCRLite small",  0.0242,  0.65,  323,"10/24","det"),
 ("RapidOCRLite medium", 0.0250,  2.67,  686,"10/24","det"),
 ("SimdPaddleOCR 默认",  0.0250,  2.77,  745, "9/24","det"),
 ("SimdPaddleOCR 受控",  0.0246,  2.93,  754,"10/24","det"),
 ("EasyOCR",             0.0656,  4.74, 1529, "1/24","det"),
 ("PaddleOCR 官方",      0.0137, 22.19, 1928,"11/24","det"),
 ("LightOnOCR-3 剥标记", 0.0263, 26.77, 1562, "9/24","e2e"),
 ("LightOnOCR-3 原始输出",0.5167,26.77, 1562, "2/24","e2e"),
 ("GLM-OCR 0.9B",        0.0000, 52.68, 3361,"13/24","e2e"),
]

# ============================================================ 1 总榜三联条形
def board():
    h = 1240
    im,d = new(h)
    txt(d,(56,54),"总榜 · 三项指标",zh(36,True))
    txt(d,(56,106),"24 张样本中位 · 纯 CPU · 每张 3 次取中位 · x/24 = 全对张数",zh(19),fill=INK3)
    top, rowh, name_w = 210, 96, 300
    metrics=[("字错率中位",[r[1] for r in ROWS],"%.4f",BLUE),
             ("单页耗时（秒）",[r[2] for r in ROWS],"%.2f",ORANGE),
             ("内存峰值（MB）",[r[3] for r in ROWS],"%d",TEAL)]
    colw=(W-112-name_w-2*36)//3
    for mi,(mt,vals,fmt,col) in enumerate(metrics):
        x0=56+name_w+mi*(colw+36)
        txt(d,(x0,top-46),mt,zh(20,True),fill=INK2)
        d.line([x0,top-14,x0+colw,top-14], fill=RULE2,width=2)
        mx=max(vals)
        for i,r in enumerate(ROWS):
            y=top+i*rowh
            v=vals[i]; bl=max(3,(colw-104)*v/mx)
            c = ORANGE if r[5]=="e2e" else col
            d.rectangle([x0,y+10,x0+bl,y+28], fill=c)
            txt(d,(x0+bl+10,y+9),fmt%v,nu(17),fill=INK)
    for i,r in enumerate(ROWS):
        y=top+i*rowh
        txt(d,(56,y+6),r[0],zh(20),fill=INK)
        txt(d,(56,y+38),r[4],nu(16),fill=INK3)
        d.line([56,y+68,W-56,y+68],fill=RULE,width=1)
    d.line([56,h-96,W-56,h-96],fill=RULE2,width=2)
    txt(d,(56,h-70),"蓝/橙区分检测式与端到端。LightOnOCR-3 两行是同一批输出的两种算法。",zh(18),fill=INK2)
    im.save(A+"/local-ai-ep12-fig1-总榜.png"); return "fig1 总榜"

# ============================================================ 2 速度内存双栏
def speedmem():
    h=1000
    im,d=new(h)
    txt(d,(56,54),"单页耗时与内存峰值",zh(36,True))
    txt(d,(56,106),"24 张样本中位 · 纯 CPU · 每张图 3 次取中位",zh(19),fill=INK3)
    top,rowh=220,80
    name_w=300
    panels=[("单页耗时中位（秒）",[r[2] for r in ROWS],"%.2f",ORANGE),
            ("内存峰值中位（MB）",[r[3] for r in ROWS],"%d",TEAL)]
    colw=(W-112-name_w-40)//2
    for pi_,(mt,vals,fmt,col) in enumerate(panels):
        x0=56+name_w+pi_*(colw+40)
        txt(d,(x0,top-44),mt,zh(20,True),fill=INK2)
        d.line([x0,top-14,x0+colw,top-14],fill=RULE2,width=2)
        mx=max(vals)
        for i,r in enumerate(ROWS):
            y=top+i*rowh
            v=vals[i]; bl=max(3,(colw-100)*v/mx)
            d.rectangle([x0,y+8,x0+bl,y+26],fill=col)
            txt(d,(x0+bl+10,y+7),fmt%v,nu(16),fill=INK)
    for i,r in enumerate(ROWS):
        y=top+i*rowh
        txt(d,(56,y+4),r[0],zh(19),fill=INK)
        d.line([56,y+56,W-56,y+56],fill=RULE,width=1)
    d.line([56,h-88,W-56,h-88],fill=RULE2,width=2)
    txt(d,(56,h-62),"前五名与最后一名两项一致；中间两名对调——PaddleOCR 更慢但更省内存。",zh(18),fill=INK2)
    im.save(A+"/local-ai-ep12-fig2-速度内存.png"); return "fig2 速度内存"

# ============================================================ 3 同权重三栈
def stacks():
    h=580
    im,d=new(h)
    txt(d,(56,54),"同一套模型权重，只换推理栈",zh(36,True))
    txt(d,(56,106),"三个引擎读的是同一个模型文件，档位相同、字典 18708 条逐条比对完全一致",zh(18),fill=INK3)
    data=[("PaddleOCR 官方（Python 栈）",22.19,ORANGE,False),
          ("SimdPaddleOCR 受控（纯 C#）",2.93,BLUE,False),
          ("RapidOCRLite medium（C++）",2.67,BLUE,True)]
    top,rowh,bx0=220,96,470
    bw=W-bx0-210; mx=22.19
    for i,(lbl,v,col,best) in enumerate(data):
        y=top+i*rowh
        txt(d,(56,y+10),lbl,zh(22,True if best else False),fill=INK if best else INK2)
        bl=bw*v/mx
        d.rectangle([bx0,y,bx0+bl,y+32],fill=col)
        txt(d,(bx0+bl+16,y+6),"%.2f s"%v,nu(23),fill=INK)
        if best: txt(d,(bx0+bl+118,y+12),"最快",zh(17),fill=GREEN)
        d.line([56,y+64,W-56,y+64],fill=RULE,width=1)
    d.line([56,h-84,W-56,h-84],fill=RULE2,width=2)
    txt(d,(56,h-58),"8.3 倍有前提：oneDNN 在本机报错，PaddleOCR 只能关加速裸跑。",zh(18),fill=INK2)
    im.save(A+"/local-ai-ep12-fig3-三栈.png"); return "fig3 三栈"

# ============================================================ 4 降档位哑铃图
def downgrade():
    h=820
    im,d=new(h)
    txt(d,(56,54),"RapidOCRLite 降一档位",zh(36,True))
    txt(d,(56,106),"同管线、同检测参数、只换权重 · 右端为更好那一档",zh(19),fill=INK3)
    # 指标, medium, small, 越低越好?, 格式, 变化文字
    M=[("单页耗时（秒）",2.67,0.65,True,"%.2f","快 4.13 倍"),
       ("内存峰值（MB）",686,323,True,"%d","省 53%"),
       ("字错率中位",0.0250,0.0242,True,"%.4f","基本持平"),
       ("字错率 p90",0.9790,0.7377,True,"%.4f","降 24.6%"),
       ("满分张数",10,10,False,"%d/24","持平")]
    x0=340; xmax=W-250; top,rowh=230,104
    txt(d,(x0,top-46),"medium 档",zh(19,True),fill=ORANGE,anchor="ma")
    txt(d,(xmax,top-46),"small 档",zh(19,True),fill=BLUE,anchor="ma")
    d.line([56,top-18,W-56,top-18],fill=RULE2,width=2)
    for i,(nm,a,b,lowbetter,fmt,chg) in enumerate(M):
        y=top+i*rowh+30
        # 归一：让"更好"永远靠右
        mx=max(a,b) or 1
        pa = a/mx; pb = b/mx
        if lowbetter: pa, pb = 1-pa, 1-pb
        xa = x0+(xmax-x0)*pa; xb = x0+(xmax-x0)*pb
        txt(d,(56,y-14),nm,zh(21),fill=INK)
        txt(d,(56,y+14),chg,zh(16),fill=INK3)
        better_b = (b<a) if lowbetter else (b>a)
        d.line([min(xa,xb),y,max(xa,xb),y],fill=RULE2,width=4)
        # 画箭头指向更好的那端
        ax = xb if better_b else xa
        dirn = 1 if xb>xa else -1
        if a!=b:
            d.polygon([(ax,y),(ax-14*dirn,y-11),(ax-14*dirn,y+11)],fill=GREEN)
        d.ellipse([xa-12,y-12,xa+12,y+12],fill=ORANGE)
        d.ellipse([xb-12,y-12,xb+12,y+12],fill=BLUE)
        txt(d,(xa,y-30),fmt%a,nu(18),fill=ORANGE,anchor="ma")
        txt(d,(xb,y+26),fmt%b,nu(18),fill=BLUE,anchor="ma")
        d.line([56,y+52,W-56,y+52],fill=RULE,width=1)
    d.line([56,h-88,W-56,h-88],fill=RULE2,width=2)
    txt(d,(56,h-62),"字错率中位几乎不变是假象——红章压字那张从 0.05 崩到 0.37，中位数反映不出这件事。",zh(18),fill=INK2)
    im.save(A+"/local-ai-ep12-fig4-降档位.png"); return "fig4 降档位"

# ============================================================ 5 GLM vs LightOn 哑铃图
def glmvslighton():
    h=1000
    im,d=new(h)
    txt(d,(56,54),"GLM-OCR 与 LightOnOCR-3",zh(36,True))
    txt(d,(56,106),"两个 1B 以内端到端模型 · 都走 Ollama · 颜色认模型，位置认数值大小",zh(19),fill=INK3)
    M=[("单页耗时（秒）",52.68,26.77,"%.2f","LightOn 快 1.97 倍"),
       ("内存峰值（MB）",3361,1562,"%d","LightOn 省 54%"),
       ("字错率均值",0.2102,0.1896,"%.4f","LightOn 更低"),
       ("字错率中位",0.0000,0.0263,"%.4f","GLM 更低"),
       ("满分张数",13,9,"%d/24","GLM 更多")]
    x0=330; xmax=W-330
    top,rowh=220,116
    for i,(nm,a,b,fmt,note) in enumerate(M):
        y=top+i*rowh
        mx=max(a,b); a_=x0+(xmax-x0)*a/mx; b_=x0+(xmax-x0)*b/mx
        txt(d,(56,y-12),nm,zh(21),fill=INK)
        txt(d,(56,y+16),note,zh(16),fill=INK3)
        d.line([min(a_,b_),y,max(a_,b_),y],fill=RULE2,width=3)
        d.ellipse([a_-12,y-12,a_+12,y+12],fill=ORANGE)   # 恒为 GLM
        d.ellipse([b_-12,y-12,b_+12,y+12],fill=GREEN)    # 恒为 LightOn
        txt(d,(a_,y-26),fmt%a,nu(17),fill=INK2,anchor="ma")
        txt(d,(b_,y+18),fmt%b,nu(17),fill=INK,anchor="ma")
        d.line([56,y+52,W-56,y+52],fill=RULE,width=1)
    # 图例按颜色认，不按位置认（点是按数值定位的，位置会随指标变）
    txt(d,(56,top-56),"●",zh(24),fill=ORANGE,anchor="lm")
    txt(d,(84,top-56),"GLM-OCR 0.9B",zh(19,True),fill=ORANGE,anchor="lm")
    txt(d,(286,top-56),"●",zh(24),fill=GREEN,anchor="lm")
    txt(d,(314,top-56),"LightOnOCR-3 0.8B",zh(19,True),fill=GREEN,anchor="lm")
    d.line([56,h-88,W-56,h-88],fill=RULE2,width=2)
    txt(d,(56,h-62),"量化不同（F16 vs Q8_0），体积差有一部分是量化的账；输出格式各有用途。",zh(18),fill=INK2)
    im.save(A+"/local-ai-ep12-fig5-同类对照.png"); return "fig5 同类对照"

out=[board(),speedmem(),stacks(),downgrade(),glmvslighton()]
print("生成:",out)
for f in sorted(os.listdir(A)):
    if f.startswith("local-ai-ep12-fig"):
        print("  %-40s %5d KB"%(f, os.path.getsize(A+"/"+f)//1024))
