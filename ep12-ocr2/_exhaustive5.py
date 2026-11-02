# -*- coding: utf-8 -*-
"""把 part4 报出的"未覆盖"数字分类：CSS / §05已核 / 样本图内容 / 真未核。"""
import re, pathlib, json, unicodedata, glob, os
from collections import Counter

RPT = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html"
BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
E11  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"

raw = pathlib.Path(RPT).read_text(encoding="utf-8")
# 1) 剥掉 <style> 与 <script>（CSS 数值不算数据）
body = re.sub(r'<style.*?</style>', ' ', raw, flags=re.S)
body = re.sub(r'<script.*?</script>', ' ', body, flags=re.S)
# 2) 剥掉 base64
body = re.sub(r'src="data:image/png;base64,[^"]+"', ' ', body)
# 3) 剥掉 <pre> 代码块（那是示例输出，不是测量数据）
pre_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', body, flags=re.S)
body_nopre = re.sub(r'<pre[^>]*>.*?</pre>', ' [PRE] ', body, flags=re.S)
txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body_nopre))

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

# 建立"合法值全集"：所有配置 × 所有 24 样本的 CER 值（4 位小数）
legal = set()
for eng, tf in [("rapidocrlite-medium",None),("rapidocrlite-small",None),
                ("simdpaddleocr",None),("simdpaddleocr-default",None),
                ("paddleocr",None),("easyocr",None),("glmocr",None),
                ("lightonocr",strip)]:
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
        legal.add("%.4f"%cer)

# 抽取数字
nums = Counter(re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])', txt))
# 合法值扩展：耗时、内存、百分比等
for eng in ["rapidocrlite-medium","rapidocrlite-small","simdpaddleocr",
            "simdpaddleocr-default","paddleocr","easyocr","glmocr","lightonocr"]:
    for f in glob.glob(BASE+"/cells/%s__*.json"%eng):
        c=json.load(open(f,encoding="utf-8"))
        if c.get("median"): legal.add("%.2f"%c["median"])
        if c.get("peak_rss_mb"): legal.add("%.0f"%c["peak_rss_mb"])
        ex=c.get("extra") or {}
        for k in ("prompt_eval_count","prompt_eval_duration_s","eval_duration_s",
                  "load_duration_s","eval_count"):
            v=ex.get(k)
            if isinstance(v,(int,float)): legal.add("%.2f"%v); legal.add(str(int(v)))
# 常量与推导
for v in ["4096","4100","4089","3790","18708","0.9905","0.033","66.7","30.3","3.0",
          "2461","2480","19","23","0.9923","2.67","52.68","26.77","1562","3361",
          "686","323","754","745","1928","1529","0.65","22.19","4.74","2.93","2.77",
          "8.3","7.6","8.0","4.13","53","19.8","81.6","2.56","2.81","1.97","2.0",
          "54","9.8","3.6","31","39","40","10.4","20.3","12.5","11.1","0.0",
          "13.44","10.52","10.69","8.77","4.63","4.64","7.18","9.19",
          "1.02","2.66","156","26","24","9","6","7","8","5","3","2","1","10","12","13",
          "0.77","0.83","2400","2411","2428","2423","91","2640","234","0.648","1.03",
          "0.014","0.025","1.04","1.10","1.57","1.07","1.09","0.51","135.45","4089",
          "4100","16","120","97","110","0.12","200","0.1896","0.2102","0.0263","0.0242",
          "0.0250","0.0246","0.0137","0.0656","0.5167","0.0000","0.4286","189.97",
          "4858","1.91","0.0383","27.85","2204","0.1922","2.0","0.646","1.6",
          "131","256","4","0.005","1","2","3","4","5","6","7","8","9","10","11","12",
          "13","14","15","16","24","26"]:
    legal.add(v)

uncovered = []
for n, c in sorted(nums.items(), key=lambda x:-x[1]):
    if n in legal: continue
    m = re.search(r'(?<![\w.])'+re.escape(n)+r'(?![\w.])', txt)
    ctx = txt[max(0,m.start()-70):m.start()+70] if m else ""
    uncovered.append((n,c,ctx.strip()))

print("="*88)
print("剥掉 CSS / 脚本 / 代码块后的数字扫描")
print("="*88)
print("  正文数字 token(去重): %d" % len(nums))
print("  合法值全集覆盖: %d" % len([n for n in nums if n in legal]))
print("  未覆盖: %d" % len(uncovered))
print()
for n,c,ctx in uncovered[:35]:
    print("  %-10s ×%d  …%s…" % (n,c,ctx[:92]))
