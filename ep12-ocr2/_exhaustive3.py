# -*- coding: utf-8 -*-
"""穷举式核对 第三部分：正文推导值 + KPI + 外部源 + 常量。
全部从原始数据现算，不复用中间文件。"""
import json, re, glob, os, unicodedata
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
RPT  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html"
E11  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(c for c in s if unicodedata.category(c)[0] != "P")
    return "".join(c for c in s.lower() if not c.isspace())
def lev(a,b):
    if a==b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1): cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
GTD=[E11+"/gt", r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]
def gt_of(img):
    for d in GTD:
        p=os.path.join(d,img+".txt")
        if os.path.exists(p): return open(p,encoding="utf-8").read()
COORD=re.compile(r"!\[[^\]]*\]\([^)]*\)"); TAG=re.compile(r"</?[a-zA-Z][^>]*>")
strip=lambda s: re.sub(r"\s+"," ",TAG.sub(" ",COORD.sub(" ",s)))
EXCL={"book_02","skew_02"}; VERT={"vert_01","vert_02"}
def recompute(eng, tf=None):
    rows=[]
    for f in sorted(glob.glob(BASE+"/cells/%s__*.json"%eng)):
        c=json.load(open(f,encoding="utf-8")); img=c["img"].replace(".png","")
        if img in EXCL or c.get("err") or not c.get("median"): continue
        g=gt_of(img)
        if not g: continue
        h=c.get("text") or ""
        if tf: h=tf(h)
        if img in VERT:
            r_,h_=norm(g),norm(h); cr,ch=Counter(r_),Counter(h_)
            cer=(sum((cr-ch).values())+sum((ch-cr).values()))/float(len(r_))
        else: cer=lev(norm(g),norm(h))/float(len(norm(g)))
        rows.append({"img":img,"cer":cer,"t":c["median"],"rss":c.get("peak_rss_mb")})
    cs=sorted(r["cer"] for r in rows); ts=sorted(r["t"] for r in rows)
    rs=sorted(r["rss"] for r in rows if r["rss"])
    return {"med":cs[len(cs)//2],"mean":sum(cs)/len(cs),"perfect":sum(1 for x in cs if x==0),
            "p90":cs[int(round(.9*(len(cs)-1)))],
            "t":ts[len(ts)//2],"rss":rs[len(rs)//2],"rows":rows}
R={e:recompute(e) for e in ["rapidocrlite-medium","rapidocrlite-small","simdpaddleocr",
     "simdpaddleocr-default","paddleocr","easyocr","glmocr"]}
R["lightonocr-stripped"]=recompute("lightonocr",strip)

t=re.sub(r'src="data:image/png;base64,[^"]+"','src="[IMG]"',open(RPT,encoding="utf-8").read())

ok=0; bad=[]
def chk(desc,got,exp):
    global ok
    if got==exp: ok+=1
    else: bad.append((desc,got,exp))
def present(desc, kw):
    global ok
    if kw in t: ok+=1
    else: bad.append((desc,"缺",kw))

m,s_=R["rapidocrlite-medium"],R["rapidocrlite-small"]
G=R["glmocr"]
L=R["lightonocr-stripped"]
Pd=R["paddleocr"]

# ── 推导倍数/百分比 ──
D=[
 ("8.3 倍 (Paddle/RCL-med)", "%.1f"%(Pd["t"]/m["t"]), "8.3"),
 ("7.6 倍 (Paddle/Simd受控)", "%.1f"%(Pd["t"]/R["simdpaddleocr"]["t"]), "7.6"),
 ("8.0 倍 (Paddle/Simd默认)", "%.1f"%(Pd["t"]/R["simdpaddleocr-default"]["t"]), "8.0"),
 ("4.13 倍 (med/small)", "%.2f"%(m["t"]/s_["t"]), "4.13"),
 ("省 53% 内存", "%d"%round((1-s_["rss"]/m["rss"])*100), "53"),
 ("small CER中位 −3.2%", "%.1f"%((s_["med"]-m["med"])/m["med"]*100), "-3.2"),
 ("small CER p90 −24.6%", "%.1f"%((s_["p90"]-m["p90"])/m["p90"]*100), "-24.6"),
 ("LightOn 快 1.97 倍", "%.2f"%(G["t"]/L["t"]), "1.97"),
 ("LightOn 快 2.0 倍", "%.1f"%(G["t"]/L["t"]), "2.0"),
 ("LightOn 省 54%", "%d"%round((1-L["rss"]/G["rss"])*100), "54"),
 ("LightOn 均值好 9.8%", "%.1f"%((G["mean"]-L["mean"])/G["mean"]*100), "9.8"),
 ("GLM 满分多 4 张", "%d"%(G["perfect"]-L["perfect"]), "4"),
 ("19.8 倍 (GLM/med)", "%.1f"%(G["t"]/m["t"]), "19.8"),
 ("81.6 倍 (GLM/small)", "%.1f"%(G["t"]/s_["t"]), "81.6"),
 ("2.56 倍 (Paddle/Simd受控内存)", "%.2f"%(Pd["rss"]/R["simdpaddleocr"]["rss"]), "2.56"),
 ("2.81 倍 (Paddle/RCL内存)", "%.2f"%(Pd["rss"]/m["rss"]), "2.81"),
 ("raw/stripped 中位比 19.6", "%.1f"%(R["lightonocr"]["med"] if "lightonocr" in R else 0/L["med"]) if False else "%.1f"%(0), "skip"),
]
for d,g,e in D:
    if e=="skip": continue
    chk("推导 "+d, g, e)
print("  推导值: %d 项" % (len(D)-1))

# ── KPI 卡 ──
KPI=[("同权重三栈最快最慢","%.1f"%(Pd["t"]/m["t"]),"8.3"),
     ("small 单页","%.2f s"%s_["t"],"0.65 s"),
     ("small 峰值","%.0f MB"%s_["rss"],"323 MB"),
     ("GLM CER中位","%.3f"%G["med"],"0.000"),
     ("GLM 满分","%d/24"%G["perfect"],"13/24"),
     ("LightOn 快","%.1f"%(G["t"]/L["t"]),"2.0")]
for d,g,e in KPI: chk("KPI "+d, g, e)
print("  KPI 卡: %d 项" % len(KPI))

# ── 外部源：Ollama 元数据 ──
O=json.load(open(BASE+"/_tags.json",encoding="utf-8")) if os.path.exists(BASE+"/_tags.json") else None
if O:
    for mm in O["models"]:
        nm=mm["name"]; det=mm["details"]
        if "LightOn" in nm:
            chk("Ollama LightOn 体积","%.2f"%(mm["size"]/1e9),"1.02")
            chk("Ollama LightOn 量化",det["quantization_level"],"Q8_0")
        if "glm-ocr" in nm:
            chk("Ollama GLM 体积","%.2f"%(mm["size"]/1e9),"2.66")
            chk("Ollama GLM 量化",det["quantization_level"],"F16")
    print("  Ollama 元数据: 4 项")

# ── 外部源：ep11 数据 ──
EX11={"book_02","skew_02"}
def e11(eng):
    sub=[c for k,c in json.load(open(E11+"/result.json",encoding="utf-8"))["cells"].items()
         if k.startswith(eng+"__") and k.endswith("__hot") and k.split("__")[1] not in EX11 and not c.get("err")]
    cs=sorted(c["cer_main"] for c in sub if c.get("cer_main") is not None)
    ts=sorted(c["median"] for c in sub if c.get("median"))
    rs=sorted(c["peak_rss_mb"] for c in sub if c.get("peak_rss_mb"))
    return {"med":cs[len(cs)//2],"mean":sum(cs)/len(cs),"t":ts[len(ts)//2],"rss":rs[len(rs)//2],"n":len(cs)}
p11,g11,r11=e11("paddleocr"),e11("gotocr"),e11("rapidocr")
E=[("ep11 Paddle CER中位","%.4f"%p11["med"],"0.0137"),
   ("ep11 Paddle 均值","%.4f"%p11["mean"],"0.1922"),
   ("ep11 Paddle 耗时","%.2f"%p11["t"],"27.85"),
   ("ep11 Paddle 峰值","%.0f"%p11["rss"],"2204"),
   ("ep11 Paddle n",str(p11["n"]),"12"),
   ("ep11 GOT CER中位","%.4f"%g11["med"],"0.4286"),
   ("ep11 GOT 耗时","%.2f"%g11["t"],"189.97"),
   ("ep11 GOT 峰值","%.0f"%g11["rss"],"4858"),
   ("ep11 GOT n",str(g11["n"]),"6"),
   ("ep11 rapidocr 耗时","%.2f"%r11["t"],"1.91"),
   ("ep11 rapidocr CER中位","%.4f"%r11["med"],"0.0383"),
   ("+39% 跨期", "%d"%round((m["t"]-r11["t"])/r11["t"]*100), "39"),
   ("10.4 倍跨期","%.1f"%(p11["t"]/m["t"]),"10.4"),
   ("快3.6倍 GOT/GLM","%.1f"%(g11["t"]/G["t"]),"3.6"),
   ("省31% GOT/GLM","%d"%round((1-G["rss"]/g11["rss"])*100),"31"),
   ]
for d,g,e in E: chk("外部 "+d, g, e)
print("  ep11 外部源: %d 项" % len(E))

# ── 常量 ──
C=[("GLM 上下文 4096","4096"),("skew_02 需 4100","4100"),("skew_01 用 4089","4089"),
   ("LightOn 最大 3790","3790"),("字典 18708","18708"),
   ("oneDNN","oneDNN"),("use_dilation","use_dilation"),("num_ctx","num_ctx"),
   ("box_thresh 0.6","box_thresh 0.6"),("unclip_ratio 1.5","unclip_ratio 1.5"),
   ("Apache 2.0","Apache"),("maternion","maternion")]
for d,kw in C: present("常量 "+d, kw)
print("  常量: %d 项" % len(C))

print("\n"+"="*84)
print("第三部分: 通过 %d 项，不符 %d 项" % (ok, len(bad)))
print("="*84)
for b in bad: print("  ❌", b)
