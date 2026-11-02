# -*- coding: utf-8 -*-
"""穷举式核对 第二部分：§03/§04/§09/§10/§11/§12 表格 + 图表 + 方法学 + 外部源 + 常量。
从 cell JSON 现算（不复用任何中间聚合文件）。"""
import json, re, glob, os, unicodedata, statistics
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
RPT  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html"
E11  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(c for c in s if unicodedata.category(c)[0] != "P")
    return "".join(c for c in s.lower() if not c.isspace())
def lev(a, b):
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]
GTD = [E11 + "/gt", r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]
def gt_of(img):
    for d in GTD:
        p = os.path.join(d, img + ".txt")
        if os.path.exists(p): return open(p, encoding="utf-8").read()
COORD = re.compile(r"!\[[^\]]*\]\([^)]*\)"); TAG = re.compile(r"</?[a-zA-Z][^>]*>")
strip = lambda s: re.sub(r"\s+", " ", TAG.sub(" ", COORD.sub(" ", s)))
EXCL = {"book_02","skew_02"}; VERT = {"vert_01","vert_02"}

def recompute(eng, tf=None):
    rows = []
    for f in sorted(glob.glob(BASE + "/cells/%s__*.json" % eng)):
        c = json.load(open(f, encoding="utf-8"))
        img = c["img"].replace(".png","")
        if img in EXCL or c.get("err") or not c.get("median"): continue
        g = gt_of(img)
        if not g: continue
        h = c.get("text") or ""
        if tf: h = tf(h)
        if img in VERT:
            r_, h_ = norm(g), norm(h); cr, ch = Counter(r_), Counter(h_)
            cer = (sum((cr-ch).values())+sum((ch-cr).values()))/float(len(r_))
        else:
            cer = lev(norm(g), norm(h))/float(len(norm(g)))
        rows.append({"img":img,"cer":cer,"t":c["median"],"rss":c.get("peak_rss_mb"),
                     "spread":c.get("spread_pct") or 0})
    cs=sorted(r["cer"] for r in rows); ts=sorted(r["t"] for r in rows)
    rs=sorted(r["rss"] for r in rows if r["rss"])
    return {"n":len(rows),"med":cs[len(cs)//2],"mean":sum(cs)/len(cs),
            "p90":cs[int(round(.9*(len(cs)-1)))],"perfect":sum(1 for x in cs if x==0),
            "t":ts[len(ts)//2],"rss":rs[len(rs)//2],
            "maxspread":max(r["spread"] for r in rows),"rows":rows}

R = {e: recompute(e) for e in ["rapidocrlite-medium","rapidocrlite-small","simdpaddleocr",
     "simdpaddleocr-default","paddleocr","easyocr","glmocr"]}
R["lightonocr"]=recompute("lightonocr"); R["lightonocr-stripped"]=recompute("lightonocr", strip)

t = re.sub(r'src="data:image/png;base64,[^"]+"','src="[IMG]"', open(RPT,encoding="utf-8").read())
def sec(n):
    a=t.find('<h2><span class="no">%s</span>'%n); b=t.find('<h2><span class="no">',a+10)
    return t[a:b if b>0 else len(t)]
def rows_of(tb):
    return [[re.sub(r'<[^>]+>','',c).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tr,re.S)]
            for tr in re.findall(r'<tr>(.*?)</tr>',tb,re.S)]

ok=0; bad=[]
def _norm_sign(x):
    """统一减号：真减号 U+2212 与 ASCII 连字符视为同一个字符。"""
    if isinstance(x, str): return x.replace("\u2212", "-")
    if isinstance(x, tuple): return tuple(_norm_sign(i) for i in x)
    return x

def chk(desc,got,exp):
    global ok
    if _norm_sign(got)==_norm_sign(exp): ok+=1
    else: bad.append((desc,got,exp))

# ── §03 核心命题 ──
KM3={"PaddleOCR 官方":"paddleocr","RapidOCRLite medium":"rapidocrlite-medium",
     "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default"}
tb=re.search(r'<div class="tw"><table>.*?</table></div>',sec("03"),re.S).group(0)
for r in rows_of(tb)[1:]:
    if r[0] not in KM3: continue
    d=R[KM3[r[0]]]
    chk("§03 %s 耗时"%r[0], r[1], "%.2f s"%d["t"])
    chk("§03 %s CER"%r[0], r[3], "%.4f"%d["med"])
    chk("§03 %s 峰值"%r[0], r[4], "%.0f MB"%d["rss"])
print("  §03 核心命题: %d 项" % (len(KM3)*3))

# ── §04 图表 ──
i4=t.find('<h2><span class="no">04</span>'); i5=t.find('<h2><span class="no">05</span>')
svgs=list(re.finditer(r'<svg viewBox.*?</svg>',t[i4:i5],re.S))
KMC={"Rcl-med":"rapidocrlite-medium","Rcl-small":"rapidocrlite-small","Simd受控":"simdpaddleocr",
     "Simd默认":"simdpaddleocr-default","EasyOCR":"easyocr","Paddle官方":"paddleocr","GLM-OCR":"glmocr"}
nb=0
for k,s in enumerate(svgs[:2]):
    for lb,vl in zip(re.findall(r'class="bl">([^<]+)</text>',s.group(0)),
                     re.findall(r'class="bv">([^<]+)</text>',s.group(0))):
        d = R["lightonocr-stripped"] if lb=="LightOn" else R[KMC[lb]]
        chk("§04图%d %s"%(k+1,lb), vl, ("%.2f s"%d["t"] if k==0 else "%.0f MB"%d["rss"])); nb+=1
pts=re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)"',svgs[2].group(0))
chk("§04散点 点数", len(pts), 8)
print("  §04 图表: %d 条 + 散点 8 点" % nb)

# ── §09 GLM 三段耗时 ──
tot={"pe":0.,"ev":0.,"ld":0.}
for f in sorted(glob.glob(BASE+"/cells/glmocr__*.json")):
    c=json.load(open(f,encoding="utf-8"))
    if not c.get("median"): continue
    ex=c.get("extra") or {}
    tot["pe"]+=ex.get("prompt_eval_duration_s") or 0
    tot["ev"]+=ex.get("eval_duration_s") or 0
    tot["ld"]+=ex.get("load_duration_s") or 0
s=sum(tot.values())
chk("§09 prefill占比","%.1f%%"%(tot["pe"]/s*100),"66.7%")
chk("§09 生成占比","%.1f%%"%(tot["ev"]/s*100),"30.3%")
chk("§09 装载占比","%.1f%%"%(tot["ld"]/s*100),"3.0%")
pts2=[]
for f in sorted(glob.glob(BASE+"/cells/glmocr__*.json")):
    c=json.load(open(f,encoding="utf-8")); ex=c.get("extra") or {}
    if ex.get("prompt_eval_count") and ex.get("prompt_eval_duration_s"):
        pts2.append((ex["prompt_eval_count"],ex["prompt_eval_duration_s"]))
xs=[a for a,_ in pts2]; ys=[b for _,b in pts2]
mx,my=statistics.mean(xs),statistics.mean(ys)
r_=sum((a-mx)*(b-my) for a,b in pts2)/((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5)
slope=sum((a-mx)*(b-my) for a,b in pts2)/sum((a-mx)**2 for a in xs)
chk("§09 相关系数 r","%.4f"%r_,"0.9905")
chk("§09 斜率","%.3f"%slope,"0.033")
tb9=re.findall(r'<div class="tw"><table>.*?</table></div>',sec("09"),re.S)
for r in rows_of(tb9[1])[1:]:
    c=json.load(open(BASE+"/cells/glmocr__%s.json"%r[0],encoding="utf-8")); ex=c["extra"]
    chk("§09 %s token"%r[0], r[1], str(ex["prompt_eval_count"]))
    chk("§09 %s prefill"%r[0], r[2], "%.2f s"%ex["prompt_eval_duration_s"])
    chk("§09 %s eval"%r[0], r[3], "%.2f s"%ex["eval_duration_s"])
print("  §09 方法学: 3 占比 + r + 斜率 + 4 行 × 3")

# ── §10 三组 ──
EXCL11={"book_02","skew_02"}
def e11(eng):
    sub=[c for k,c in json.load(open(E11+"/result.json",encoding="utf-8"))["cells"].items()
         if k.startswith(eng+"__") and k.endswith("__hot") and k.split("__")[1] not in EXCL11 and not c.get("err")]
    cs=sorted(c["cer_main"] for c in sub if c.get("cer_main") is not None)
    ts=sorted(c["median"] for c in sub if c.get("median"))
    rs=sorted(c["peak_rss_mb"] for c in sub if c.get("peak_rss_mb"))
    return {"med":cs[len(cs)//2],"mean":sum(cs)/len(cs),"t":ts[len(ts)//2],"rss":rs[len(rs)//2]}
p11=g11=r11=e11("paddleocr"),e11("gotocr"),e11("rapidocr")
p11,g11,r11=e11("paddleocr"),e11("gotocr"),e11("rapidocr")
tb10=re.findall(r'<div class="tw"><table>.*?</table></div>',sec("10"),re.S)
EXP={"CER 中位":("%.4f"%p11["med"],"%.4f"%R["paddleocr"]["med"],
      "%.1f%%"%((R["paddleocr"]["med"]-p11["med"])/p11["med"]*100)),
     "CER 均值":("%.4f"%p11["mean"],"%.4f"%R["paddleocr"]["mean"],
      "+%.1f%%"%((R["paddleocr"]["mean"]-p11["mean"])/p11["mean"]*100)),
     "耗时中位":("%.2f s"%p11["t"],"%.2f s"%R["paddleocr"]["t"],
      "−%.1f%%"%abs((R["paddleocr"]["t"]-p11["t"])/p11["t"]*100)),
     "峰值中位":("%.0f MB"%p11["rss"],"%.0f MB"%R["paddleocr"]["rss"],
      "−%.1f%%"%abs((R["paddleocr"]["rss"]-p11["rss"])/p11["rss"]*100))}
for r in rows_of(tb10[0])[1:]:
    if r[0] in EXP: chk("§10① %s"%r[0], (r[1],r[2],r[3]), EXP[r[0]])
GP=R["glmocr"]["perfect"]
EXP2={"CER 中位":("0.4286","0.0000","中位为 0（%d/24 满分）"%GP),
      "耗时中位":("%.2f s"%g11["t"],"%.2f s"%R["glmocr"]["t"],"快 %.1f 倍"%(g11["t"]/R["glmocr"]["t"])),
      "峰值中位":("%.0f MB"%g11["rss"],"%.0f MB"%R["glmocr"]["rss"],
        "省 %d%%"%round((1-R["glmocr"]["rss"]/g11["rss"])*100))}
for r in rows_of(tb10[1])[1:]:
    if r[0] in EXP2: chk("§10② %s"%r[0], (r[1],r[2],r[3]), EXP2[r[0]])
L=R["lightonocr-stripped"]
EXP3={"CER 中位":("0.0000","%.4f"%L["med"]),"CER 均值":("%.4f"%R["glmocr"]["mean"],"%.4f"%L["mean"]),
      "满分张数":("%d/24"%GP,"%d/24"%L["perfect"]),
      "单页耗时中位":("%.2f s"%R["glmocr"]["t"],"%.2f s"%L["t"]),
      "内存峰值中位":("%.0f MB"%R["glmocr"]["rss"],"%.0f MB"%L["rss"])}
for r in rows_of(tb10[2])[1:]:
    if r[0] in EXP3: chk("§10③ %s"%r[0], (r[1],r[2]), EXP3[r[0]])
print("  §10 三组: %d 项" % 13)

# ── §11 / §12 ──
m,s_=R["rapidocrlite-medium"],R["rapidocrlite-small"]
tb11=re.findall(r'<div class="tw"><table>.*?</table></div>',sec("11"),re.S)
E11x={"CER 中位":("%.4f"%m["med"],"%.4f"%s_["med"]),"CER 均值":("%.4f"%m["mean"],"%.4f"%s_["mean"]),
      "CER p90":("%.4f"%m["p90"],"%.4f"%s_["p90"]),"满分张数":("%d/24"%m["perfect"],"%d/24"%s_["perfect"]),
      "单页耗时中位":("%.2f s"%m["t"],"%.2f s"%s_["t"]),"内存峰值中位":("%.0f MB"%m["rss"],"%.0f MB"%s_["rss"])}
for r in rows_of(tb11[0])[1:]:
    if r[0] in E11x: chk("§11 %s"%r[0], (r[1],r[2]), E11x[r[0]])
mi={x["img"]:x for x in m["rows"]}; si={x["img"]:x for x in s_["rows"]}
for r in rows_of(tb11[1])[1:]:
    if r[0] in mi: chk("§11图 %s"%r[0], (r[1],r[2]),
        ("%.4f"%mi[r[0]]["cer"], "%.4f"%si[r[0]]["cer"]))
tb12=re.findall(r'<div class="tw"><table>.*?</table></div>',sec("12"),re.S)
E12={"CER 中位":("%.4f"%R["glmocr"]["med"],"%.4f"%L["med"]),
     "CER 均值":("%.4f"%R["glmocr"]["mean"],"%.4f"%L["mean"]),
     "CER p90":("%.4f"%R["glmocr"]["p90"],"%.4f"%L["p90"]),
     "满分张数":("%d/24"%GP,"%d/24"%L["perfect"]),
     "单页耗时中位":("%.2f s"%R["glmocr"]["t"],"%.2f s"%L["t"]),
     "内存峰值中位":("%.0f MB"%R["glmocr"]["rss"],"%.0f MB"%L["rss"])}
for r in rows_of(tb12[0])[1:]:
    if r[0] in E12: chk("§12 %s"%r[0], (r[1],r[2]), E12[r[0]])
li={x["img"]:x for x in L["rows"]}; gi={x["img"]:x for x in R["glmocr"]["rows"]}
for r in rows_of(tb12[1])[1:]:
    if r[0] in li: chk("§12图 %s"%r[0], (r[1],r[2]),
        ("%.4f"%li[r[0]]["cer"], "%.4f"%gi[r[0]]["cer"]))
print("  §11 + §12: 24 项")

# ── §09 skew_01 极端例 ──
c=json.load(open(BASE+"/cells/glmocr__skew_01.json",encoding="utf-8")); ex=c["extra"]
chk("§09 skew_01 prefill","%.2f s"%ex["prompt_eval_duration_s"],"135.45 s")
chk("§09 skew_01 eval","%.2f s"%ex["eval_duration_s"],"0.51 s")
chk("skew_01 识别字数", str(c["text_len"]), "23")

print("\n" + "="*84)
print("第二部分: 通过 %d 项，不符 %d 项" % (ok, len(bad)))
print("="*84)
for b in bad: print("  ❌", b)
