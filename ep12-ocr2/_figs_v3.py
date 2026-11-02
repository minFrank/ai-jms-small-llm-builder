# -*- coding: utf-8 -*-
"""§六/§七 精简配套图：
 - fig4 补印 20/3/1 分布
 - fig6 GLM 耗时拆解（替掉表格）
 - fig7 跨期对比（PaddleOCR 复现 + GLM vs GOT）
"""
import os
from PIL import Image, ImageDraw, ImageFont

A = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets"
FZH,FZHB,FNUM = "C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/msyhbd.ttc","C:/Windows/Fonts/consola.ttf"
def zh(s,b=False): return ImageFont.truetype(FZHB if b else FZH, s)
def nu(s): return ImageFont.truetype(FNUM, s)
INK,INK2,INK3 = (28,32,38),(100,108,120),(150,158,170)
RULE,RULE2,BG,PANEL = (230,234,240),(206,212,222),(255,255,255),(247,249,252)
BLUE,ORANGE,TEAL,GREEN,GREY = (34,96,182),(198,92,48),(40,128,102),(60,140,90),(158,166,178)
W = 1080
def new(h):
    im=Image.new("RGB",(W,h),BG); return im, ImageDraw.Draw(im)
def txt(d,xy,s,f,fill=INK,anchor="la"): d.text(xy,s,font=f,fill=fill,anchor=anchor)

# ==================================================== fig4 补印分布
def fig4():
    h=860
    im,d=new(h)
    txt(d,(56,54),"RapidOCRLite 降一档位",zh(36,True))
    txt(d,(56,106),"同管线、同检测参数、只换权重 · 右端为更好那一档",zh(19),fill=INK3)
    M=[("单页耗时（秒）",2.67,0.65,True,"%.2f","快 4.13 倍"),
       ("内存峰值（MB）",686,323,True,"%d","省 53%"),
       ("字错率中位",0.0250,0.0242,True,"%.4f","基本持平"),
       ("字错率 p90",0.9790,0.7377,True,"%.4f","降 24.6%"),
       ("满分张数",10,10,False,"%d/24","持平")]
    x0=340; xmax=W-250; top,rowh=226,96
    txt(d,(x0,top-46),"medium 档",zh(19,True),fill=ORANGE,anchor="ma")
    txt(d,(xmax,top-46),"small 档",zh(19,True),fill=BLUE,anchor="ma")
    d.line([56,top-18,W-56,top-18],fill=RULE2,width=2)
    for i,(nm,a,b,lowbetter,fmt,chg) in enumerate(M):
        y=top+i*rowh+28
        mx=max(a,b) or 1
        pa,pb = a/mx, b/mx
        if lowbetter: pa,pb = 1-pa, 1-pb
        xa,xb = x0+(xmax-x0)*pa, x0+(xmax-x0)*pb
        txt(d,(56,y-14),nm,zh(21),fill=INK)
        txt(d,(56,y+14),chg,zh(16),fill=INK3)
        better_b = (b<a) if lowbetter else (b>a)
        d.line([min(xa,xb),y,max(xa,xb),y],fill=RULE2,width=4)
        ax = xb if better_b else xa
        dirn = 1 if xb>xa else -1
        if a!=b:
            d.polygon([(ax,y),(ax-14*dirn,y-11),(ax-14*dirn,y+11)],fill=GREEN)
        d.ellipse([xa-12,y-12,xa+12,y+12],fill=ORANGE)
        d.ellipse([xb-12,y-12,xb+12,y+12],fill=BLUE)
        txt(d,(xa,y-30),fmt%a,nu(18),fill=ORANGE,anchor="ma")
        txt(d,(xb,y+30),fmt%b,nu(18),fill=BLUE,anchor="ma")
        d.line([56,y+50,W-56,y+50],fill=RULE,width=1)
    # 底部：分布拆解（新印上去的）
    y0=h-176
    d.line([56,y0-16,W-56,y0-16],fill=RULE2,width=2)
    txt(d,(56,y0),"24 张逐张看",zh(20,True),fill=INK)
    chips=[("20 张 无差",GREEN),("3 张 变差",ORANGE),("1 张 变好",BLUE)]
    cx=300
    for lab,col in chips:
        d.ellipse([cx,y0+6,cx+16,y0+22],fill=col)
        txt(d,(cx+24,y0+2),lab,zh(19),fill=INK)
        cx+=230
    txt(d,(56,y0+46),"变差集中在印章和密集英文页；变好的是低分辨率那张（中权重几乎框不出字，小权重捞回 1358 字）。",zh(17),fill=INK2)
    txt(d,(56,y0+80),"中位数几乎不变是假象——红章压字那张从 0.05 崩到 0.37。",zh(17),fill=INK2)
    im.save(A+"/local-ai-ep12-fig4-降档位.png"); return "fig4"

# ==================================================== fig6 GLM 耗时拆解
def fig6():
    h=840
    im,d=new(h)
    txt(d,(56,54),"GLM-OCR 单页耗时去哪了",zh(36,True))
    txt(d,(56,106),"52.68 秒 · 24 张中位 · 纯 CPU",zh(19),fill=INK3)
    # 堆叠条
    top=230; barh=86; x0=56; bw=W-112
    segs=[("读图 prefill",66.7,BLUE),("写文字 生成",30.3,ORANGE),("装载模型",3.0,GREY)]
    x=x0
    for nm,pct,col in segs:
        w=bw*pct/100
        d.rectangle([x,top,x+w,top+barh],fill=col)
        if pct>10:
            txt(d,(x+w/2,top+barh/2),"%.1f%%"%pct,nu(28),fill=(255,255,255),anchor="mm")
            txt(d,(x+w/2,top+barh/2+26),nm,zh(17),fill=(255,255,255),anchor="mm")
        x+=w
    # 小段引线标注
    xt=x0+bw*97/100
    d.line([xt,top+barh,xt,top+barh+40],fill=GREY,width=2)
    txt(d,(W-56,top+barh+44),"装载模型 3.0%",zh(16),fill=INK2,anchor="ra")
    # 说明
    y=top+barh+120
    d.line([56,y-30,W-56,y-30],fill=RULE2,width=2)
    txt(d,(56,y),"为什么慢：图上每个角落都要过一遍模型",zh(22,True),fill=INK)
    pts=["检测式只对框出的文字块跑识别模型，空白和图形不进。",
         "GLM-OCR 把整张图全部转成视觉 token，不管那里有没有字。",
         "token 越多越慢：每多 1 个约多花 0.033 秒。"]
    for i,p in enumerate(pts):
        txt(d,(56,y+48+i*42),"·  "+p,zh(18),fill=INK2)
    # 极端例
    y2=h-150
    d.line([56,y2-24,W-56,y2-24],fill=RULE2,width=2)
    txt(d,(56,y2),"最极端的一张：倾斜 7 度那张",zh(21,True),fill=INK)
    txt(d,(56,y2+42),"读图 135.45 秒",zh(23,True),fill=BLUE)
    txt(d,(360,y2+42),"生成 0.51 秒",zh(23,True),fill=ORANGE)
    txt(d,(620,y2+42),"4089 个视觉 token",zh(23,True),fill=INK2)
    txt(d,(56,y2+82),"几乎没读出内容，但 4089 个 token 一个不少全过了一遍——与有没有字无关。",zh(17),fill=INK2)
    im.save(A+"/local-ai-ep12-fig6-耗时拆解.png"); return "fig6"

# ==================================================== fig7 跨期对比
def fig7():
    h=1300
    im,d=new(h)
    txt(d,(56,54),"跨期对比",zh(36,True))
    txt(d,(56,106),"同机同口径 · 灰点上期、蓝点本期",zh(19),fill=INK3)
    x0=350; xmax=W-250
    def block(y0, title, sub, M):
        # 表头已删：点位按数值排，固定表头会误导（副标题已写明灰=上期、蓝=本期）
        txt(d,(56,y0),title,zh(23,True),fill=INK)
        txt(d,(56,y0+36),sub,zh(16),fill=INK3)
        d.line([56,y0+64,W-56,y0+64],fill=RULE2,width=2)
        for i,(nm,a,b,fmt,note) in enumerate(M):
            y=y0+116+i*98
            mx=max(a,b) or 1
            pa,pb=a/mx,b/mx
            xa,xb=x0+(xmax-x0)*pa, x0+(xmax-x0)*pb
            txt(d,(56,y-12),nm,zh(20),fill=INK)
            txt(d,(56,y+16),note,zh(15),fill=INK3)
            d.line([min(xa,xb),y,max(xa,xb),y],fill=RULE2,width=4)
            d.ellipse([xa-11,y-11,xa+11,y+11],fill=GREY)
            d.ellipse([xb-11,y-11,xb+11,y+11],fill=BLUE)
            txt(d,(xa,y-30),fmt%a,nu(18),fill=INK2,anchor="ma")
            txt(d,(xb,y+30),fmt%b,nu(18),fill=INK,anchor="ma")
            d.line([56,y+50,W-56,y+50],fill=RULE,width=1)
        return y0+116+len(M)*98
    y=block(230,"PaddleOCR 官方 · 字错率跨期复现","同引擎、同口径，字错率几乎完全复现",
            [("字错率中位",0.0137,0.0137,"%.4f","差 −0.1%"),
             ("单页耗时（秒）",27.85,22.19,"%.2f","采集条件不同，非引擎变快"),
             ("内存峰值（MB）",2204,1928,"%d","同上")])
    y=block(y+96,"GOT-OCR2.0 换成 GLM-OCR","端到端换代：580 M → 891 M，transformers → Ollama + llama.cpp",
            [("字错率中位",0.4286,0.0000,"%.4f","中位降到 0，13/24 满分"),
             ("单页耗时（秒）",189.97,52.68,"%.2f","快 3.6 倍"),
             ("内存峰值（MB）",4858,3361,"%d","省 31%")])
    d.line([56,h-90,W-56,h-90],fill=RULE2,width=2)
    txt(d,(56,h-62),"均值差 11.1% 是因为两期样本集不同（14 张 vs 24 张），不能直接比。",zh(17),fill=INK2)
    im.save(A+"/local-ai-ep12-fig7-跨期对比.png"); return "fig7"

out=[fig4(),fig6(),fig7()]
print("生成:",out)
for f in sorted(os.listdir(A)):
    if f.startswith("local-ai-ep12-fig"):
        print("  %-40s %5d KB"%(f,os.path.getsize(A+"/"+f)//1024))
