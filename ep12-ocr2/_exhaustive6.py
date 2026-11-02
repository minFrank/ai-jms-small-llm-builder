# -*- coding: utf-8 -*-
"""核对正文里所有具体字数/尺寸声明。"""
import json, glob, os, unicodedata, re, pathlib
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
E11  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"
E12G = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(c for c in s if unicodedata.category(c)[0] != "P")
    return "".join(c for c in s.lower() if not c.isspace())
COORD=re.compile(r"!\[[^\]]*\]\([^)]*\)"); TAG=re.compile(r"</?[a-zA-Z][^>]*>")
strip=lambda s: re.sub(r"\s+"," ",TAG.sub(" ",COORD.sub(" ",s)))
EXCL={"book_02","skew_02"}; VERT={"vert_01","vert_02"}

def gt_of(img):
    for d in [E11+"/gt", E12G]:
        p=os.path.join(d,img+".txt")
        if os.path.exists(p): return open(p,encoding="utf-8").read()

def stats(eng, img, tf=None):
    f = BASE+"/cells/%s__%s.json"%(eng,img)
    if not os.path.exists(f): return None
    c=json.load(open(f,encoding="utf-8"))
    h=c.get("text") or ""
    if tf: h=tf(h)
    g=gt_of(img)
    r_,h_=norm(g),norm(h)
    cr,ch=Counter(r_),Counter(h_)
    miss=sum((cr-ch).values()); extra=sum((ch-cr).values())
    cer=lev=None
    return {"miss":miss,"extra":extra,"gt":len(r_),"hyp":len(h_),"raw_len":len(c.get("text") or "")}

def levenshtein(a,b):
    if a==b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1): cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]

ok=0; bad=[]
def chk(desc,got,exp):
    global ok
    if got==exp: ok+=1
    else: bad.append((desc,got,exp))

print("="*84); print("正文具体声明核对"); print("="*84)

# lowres_01: "GT 2640 字。A组4+EasyOCR 读出 2400+ 字乱码（Simd受控多2411、RCL多2428、PaddleOCR多2423），GLM只多91字、CER 0.12"
g = norm(gt_of("lowres_01"))
chk("lowres_01 GT 归一化字数", len(g), 2640)
for eng, exp in [("simdpaddleocr",2411),("rapidocrlite-medium",2428),("paddleocr",2423),("glmocr",91)]:
    s = stats(eng, "lowres_01")
    chk("lowres_01 %s 多读字数"%eng, s["extra"], exp)
s = stats("easyocr","lowres_01"); chk("lowres_01 EasyOCR 多读", s["extra"] > 2400, True)
s = stats("simdpaddleocr-default","lowres_01"); chk("lowres_01 Simd默认 多读", s["extra"] > 2400, True)
s = stats("rapidocrlite-small","lowres_01"); chk("lowres_01 RCL small 多读", s["extra"] > 2400, True)
# GLM CER
g_ = gt_of("lowres_01"); c = json.load(open(BASE+"/cells/glmocr__lowres_01.json",encoding="utf-8"))
cer = levenshtein(norm(g_), norm(c["text"]))/float(len(norm(g_)))
chk("lowres_01 GLM CER", "%.2f"%cer, "0.12")

# lowres_02: "GT 234 字。全员 CER 0.91–0.99。RCL多225，Simd多194"
g2 = norm(gt_of("lowres_02"))
chk("lowres_02 GT 字数", len(g2), 234)
s = stats("rapidocrlite-medium","lowres_02"); chk("lowres_02 RCL多读", s["extra"], 225)
s = stats("simdpaddleocr","lowres_02"); chk("lowres_02 Simd多读", s["extra"], 194)
cers=[]
for eng in ["simdpaddleocr","simdpaddleocr-default","rapidocrlite-medium","rapidocrlite-small",
            "paddleocr","easyocr","glmocr","lightonocr"]:
    c=json.load(open(BASE+"/cells/%s__lowres_02.json"%eng,encoding="utf-8"))
    h=c["text"] or ""
    if eng=="lightonocr": h=strip(h)
    cers.append(levenshtein(norm(g2),norm(h))/float(len(norm(g2))))
chk("lowres_02 CER 下界", "%.2f"%min(cers), "0.91")
chk("lowres_02 CER 上界", "%.2f"%max(cers), "0.99")

# seal_01: "PaddleOCR 多读2字（单位→草位），RCL 缺 16 字"
g3 = norm(gt_of("seal_01"))
s = stats("paddleocr","seal_01"); chk("seal_01 PaddleOCR 多读", s["extra"], 2)
s = stats("rapidocrlite-medium","seal_01"); chk("seal_01 RCL 缺字", s["miss"], 16)
# 草位
c=json.load(open(BASE+"/cells/paddleocr__seal_01.json",encoding="utf-8"))
chk("seal_01 PaddleOCR 含'草位'", "草位" in c["text"], True)
chk("seal_01 GT 含'单位'", "单位" in norm(g3), True)

# skew_02 图片尺寸 1825×2123
from PIL import Image
p = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples/skew_02.png"
if os.path.exists(p):
    im = Image.open(p)
    chk("skew_02 图片宽", im.size[0], 1825)
    chk("skew_02 图片高", im.size[1], 2123)

# vert 顺序 CER 0.77/0.83
V=json.load(open(BASE+"/_verify1.json",encoding="utf-8"))
for eng, e1, e2 in [("rapidocrlite-medium",0.77,0.83)]:
    pass
# 顺序 CER 需现算
for img, exp in [("vert_01",0.77),("vert_02",0.83)]:
    g_=norm(gt_of(img))
    c=json.load(open(BASE+"/cells/rapidocrlite-medium__%s.json"%img,encoding="utf-8"))
    cer=levenshtein(g_,norm(c["text"]))/float(len(g_))
    chk("vert %s 顺序CER"%img, "%.2f"%cer, "%.2f"%exp)

# hard_01 RCL small CER 0.000518
g_=gt_of("hard_01")
c=json.load(open(BASE+"/cells/rapidocrlite-small__hard_01.json",encoding="utf-8"))
cer=levenshtein(norm(g_),norm(c["text"]))/float(len(norm(g_)))
chk("hard_01 RCL small CER", "%.6f"%cer, "0.000518")

# skew_01 检测式区间 0.014–0.025
for img in ["skew_01"]:
    vals={}
    for eng in ["paddleocr","rapidocrlite-medium","simdpaddleocr","simdpaddleocr-default"]:
        c=json.load(open(BASE+"/cells/%s__%s.json"%(eng,img),encoding="utf-8"))
        vals[eng]=levenshtein(norm(gt_of(img)),norm(c["text"]))/float(len(norm(gt_of(img))))
    chk("skew_01 A组最小", "%.3f"%min(vals.values()), "0.014")
    chk("skew_01 A组最大", "%.3f"%max(vals.values()), "0.025")

print("  核对项: %d" % (ok+len(bad)))
print("  通过 %d，不符 %d" % (ok, len(bad)))
for b in bad: print("  ❌", b)
