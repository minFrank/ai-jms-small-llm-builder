# -*- coding: utf-8 -*-
"""总榜图表化 · 第二批四个形式：热力图 / 分布箱线 / 棒棒糖 / 排名变化。
箱线用 raw_agg.json 的逐张真实数据（不是中位数）。"""
import os, json, math, pathlib
from PIL import Image, ImageDraw, ImageFont

A = r"C:/Users/Frank/AppData/Local/hermes/workspace/_themes"
FZH, FZHB, FNUM = "C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/msyhbd.ttc","C:/Windows/Fonts/consola.ttf"
def zh(s,b=False): return ImageFont.truetype(FZHB if b else FZH, s)
def nu(s): return ImageFont.truetype(FNUM, s)
INK,INK2,INK3 = (30,34,40),(104,112,124),(152,160,172)
RULE,RULE2,BG,PANEL = (232,236,242),(210,216,224),(255,255,255),(248,250,253)
BLUE,ORANGE,TEAL = (36,101,190),(200,96,52),(44,134,108)

ROWS = [
 ("RCL small",  0.0242,  0.65,  323, 10, "det"),
 ("RCL medium", 0.0250,  2.67,  686, 10, "det"),
 ("Simd 默认",  0.0250,  2.77,  745,  9, "det"),
 ("Simd 受控",  0.0246,  2.93,  754, 10, "det"),
 ("EasyOCR",    0.0656,  4.74,1529,  1, "det"),
 ("Paddle官方", 0.0137, 22.19,1928, 11, "det"),
 ("LightOn剥标",0.0263, 26.77,1562,  9, "e2e"),
 ("LightOn原始",0.5167, 26.77,1562,  2, "e2e"),
 ("GLM-OCR",    0.0000, 52.68,3361, 13, "e2e"),
]
def new(w,h):
    im=Image.new("RGB",(w,h),BG); return im, ImageDraw.Draw(im)
def txt(d,xy,s,f,fill=INK,anchor="la"): d.text(xy,s,font=f,fill=fill,anchor=anchor)

# ---------------------------------------------------------------- D 热力图
def candD():
    W,H=900,1010
    im,d=new(W,H)
    txt(d,(48,44),"总榜 · 热力图",zh(30,True))
    txt(d,(48,88),"每列独立归一化 · 颜色越深数值越大",zh(16),fill=INK3)
    cols=[("字错率中位",1),("单页耗时",2),("内存峰值",3),("满分率",4)]
    x0,y0=300,190; cw,ch=140,74
    for ci,(cn,_) in enumerate(cols):
        txt(d,(x0+ci*cw+cw//2, y0-30), cn, zh(16,True), fill=INK2, anchor="ma")
    d.line([x0,y0-12,x0+4*cw,y0-12], fill=RULE2, width=2)
    maxv={k:max(r[k] for r in ROWS) for k in (1,2,3,4)}
    for ri,r in enumerate(ROWS):
        y=y0+ri*ch
        txt(d,(48,y+ch//2-16), r[0], zh(17), fill=INK, anchor="lm")
        txt(d,(48,y+ch//2+8), r[5] and ("检测式" if r[5]=="det" else "端到端"), zh(13), fill=INK3, anchor="lm")
        for ci,(cn,k) in enumerate(cols):
            v=r[k]; f=v/maxv[k]
            base = BLUE if k in (1,2,3) else TEAL
            if k==1: base=BLUE
            shade=tuple(int(255-(255-c)*f) for c in base)
            x=x0+ci*cw
            d.rectangle([x+3,y+3,x+cw-3,y+ch-3], fill=shade)
            lum=0.299*shade[0]+0.587*shade[1]+0.114*shade[2]
            tc=(255,255,255) if lum<140 else INK
            lab={1:"%.4f"%v,2:"%.2f"%v,3:"%d"%v,4:"%d/24"%v}[k]
            txt(d,(x+cw//2,y+ch//2), lab, nu(16), fill=tc, anchor="mm")
        d.line([48,y+ch,W-48,y+ch], fill=RULE, width=1)
    d.line([48,H-76,W-48,H-76], fill=RULE2, width=1)
    txt(d,(48,H-54),"同一列内比颜色深浅才有意义，跨列不能比。LightOnOCR-3 两行是同一批输出的两种算法。",zh(14),fill=INK2)
    im.save(A+"/candD-热力图.png"); return "D"

# ---------------------------------------------------------------- E 分布箱线
def candE():
    raw=json.loads(pathlib.Path(r"D:/study/deepseek-harness/ep12_review/raw_agg.json").read_text(encoding="utf-8"))
    pi=raw["per_image"]
    order=[("rapidocrlite-small","RCL small","det"),("rapidocrlite-medium","RCL medium","det"),
           ("simdpaddleocr-default","Simd 默认","det"),("simdpaddleocr","Simd 受控","det"),
           ("easyocr","EasyOCR","det"),("paddleocr","Paddle官方","det"),
           ("lightonocr","LightOn剥标","e2e"),("glmocr","GLM-OCR","e2e")]
    W,H=900,980
    im,d=new(W,H)
    txt(d,(48,44),"总榜 · 逐张分布",zh(30,True))
    txt(d,(48,88),"每个点是一张图的字错率 · 箱体是四分位 · 竖线是中位",zh(16),fill=INK3)
    L,R_,T,B=190,W-60,190,H-130
    d.rectangle([L,T,R_,B], fill=PANEL); d.rectangle([L,T,R_,B], outline=RULE2,width=1)
    def py(v): return B-(B-T)*min(v,1.0)/1.0
    for gv in [0,0.2,0.4,0.6,0.8,1.0]:
        y=py(gv); d.line([L,y,R_,y], fill=RULE,width=1)
        txt(d,(L-10,y),"%.1f"%gv, nu(13), fill=INK3, anchor="rm")
    txt(d,(64,(T+B)//2),"字错率（>1 截到顶轴）", zh(15), fill=INK2, anchor="mm")
    rowh=(B-T)/len(order)
    for i,(key,nm,g) in enumerate(order):
        vals=sorted(v["cer"] for v in pi[key] if v.get("img") not in ("book_02","skew_02"))
        n=len(vals); q1=vals[n//4]; med=vals[n//2]; q3=vals[(3*n)//4]
        cy=T+rowh*(i+0.5); cx=L+(R_-L)*0.55
        col=BLUE if g=="det" else ORANGE
        # 箱体
        d.rectangle([cx-52, py(q3), cx+52, py(q1)], outline=col, width=2, fill=(255,255,255))
        d.line([cx-52, py(med), cx+52, py(med)], fill=col, width=4)
        # 逐点
        for k,v in enumerate(pi[key]):
            if v.get("img") in ("book_02","skew_02"): continue
            px_=cx-40+80*((k*37)%97)/97
            yy=py(v["cer"])
            d.ellipse([px_-3,yy-3,px_+3,yy+3], outline=col, width=1)
        txt(d,(48,cy-8), nm, zh(16), fill=INK, anchor="lm")
        txt(d,(48,cy+12), "中位 %.4f"%med, nu(13), fill=INK3, anchor="lm")
    d.line([48,H-86,W-48,H-86], fill=RULE2,width=1)
    txt(d,(48,H-64),"GLM-OCR 中位是 0（箱体压在底轴），但上须拖到顶——多数题满分、少数题崩，中位数看不出这件事。",zh(14),fill=INK2)
    im.save(A+"/candE-分布箱线.png"); return "E"

# ---------------------------------------------------------------- F 棒棒糖
def candF():
    W,H=900,1010
    im,d=new(W,H)
    txt(d,(48,44),"总榜 · 棒棒糖图",zh(30,True))
    txt(d,(48,88),"单页耗时中位 · 点为精确值",zh(16),fill=INK3)
    x0=300; xmax=W-140; mx=52.68
    top=190; rowh=80
    for gv in [0,10,20,30,40,50]:
        x=x0+(xmax-x0)*gv/mx
        d.line([x,top-24,x,H-110], fill=RULE,width=1)
        txt(d,(x,top-38),str(gv), nu(13), fill=INK3, anchor="ma")
    txt(d,((x0+xmax)//2, H-92), "单页耗时中位（秒）", zh(15), fill=INK2, anchor="ma")
    for i,(nm,c,t,m,p,g) in enumerate([(r[0],r[1],r[2],r[3],r[4],r[5]) for r in ROWS]):
        y=top+i*rowh
        x=x0+(xmax-x0)*t/mx
        col=BLUE if p=="det" else ORANGE
        txt(d,(48,y-9), nm, zh(17), fill=INK, anchor="lm")
        txt(d,(48,y+13), "内存 %d MB"%m, nu(13), fill=INK3, anchor="lm")
        d.line([x0,y,x,y], fill=col, width=3)
        d.ellipse([x-9,y-9,x+9,y+9], fill=col)
        txt(d,(x+16,y-9), "%.2f s"%t, nu(16), fill=INK, anchor="lm")
        txt(d,(x+16,y+11), "CER %.4f"%c, nu(12), fill=INK3, anchor="lm")
        d.line([48,y+34,W-48,y+34], fill=RULE,width=1)
    d.line([48,H-72,W-48,H-72], fill=RULE2,width=1)
    txt(d,(48,H-50),"一个指标一张图，读起来最干净；但四张才说得完，占版面。",zh(14),fill=INK2)
    im.save(A+"/candF-棒棒糖.png"); return "F"

# ---------------------------------------------------------------- G 排名变化
def candG():
    W,H=900,1000
    im,d=new(W,H)
    txt(d,(48,44),"总榜 · 排名变化",zh(30,True))
    txt(d,(48,88),"四项指标各自的名次 · 线越平说明越全面",zh(16),fill=INK3)
    axes=[("字错率",lambda r:-r[1]),("单页耗时",lambda r:r[2]),("内存峰值",lambda r:r[3]),("满分张数",lambda r:-r[4])]
    xs=[220,420,620,820]; T,B=180,830
    ranks={}
    for ai,(an,f) in enumerate(axes):
        s=sorted(range(len(ROWS)), key=lambda i: f(ROWS[i]))
        for pos,i in enumerate(s): ranks.setdefault(i,{})[ai]=pos
        txt(d,(xs[ai],T-34), an, zh(16,True), fill=INK2, anchor="ma")
        d.line([xs[ai],T-12,xs[ai],B+12], fill=RULE2, width=1)
        for pos in range(len(ROWS)):
            y=T+pos*(B-T)/(len(ROWS)-1)
            txt(d,(xs[ai]-14,y), str(pos+1), nu(12), fill=INK3, anchor="rm")
    for i,r in enumerate(ROWS):
        col=BLUE if r[5]=="det" else ORANGE
        pts=[(xs[a], T+ranks[i][a]*(B-T)/(len(ROWS)-1)) for a in range(4)]
        for k in range(3):
            d.line([pts[k],pts[k+1]], fill=col, width=2)
        for x,y in pts: d.ellipse([x-5,y-5,x+5,y+5], fill=col)
        txt(d,(48,pts[0][1]-8), r[0], zh(15), fill=INK, anchor="lm")
        txt(d,(W-30,pts[3][1]-8), "#%d"%(ranks[i][3]+1), nu(14), fill=col, anchor="rm")
    d.line([48,H-106,W-48,H-106], fill=RULE2,width=1)
    txt(d,(48,H-84),"越靠上名次越好。PaddleOCR 与 LightOnOCR-3 的线在耗时与内存之间交叉——一个更慢但更省内存。",zh(14),fill=INK2)
    txt(d,(48,H-62),"GLM-OCR 字错率第 1、满分第 1，但耗时与内存都垫底，线一路下滑。",zh(14),fill=INK2)
    im.save(A+"/candG-排名变化.png"); return "G"

out=[candD(),candE(),candF(),candG()]
print("生成:",out)
for f in sorted(os.listdir(A)):
    if f.startswith("cand"): print("  %-30s %5d KB"%(f, os.path.getsize(A+"/"+f)//1024))
