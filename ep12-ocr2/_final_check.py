
# -*- coding: utf-8 -*-
"""终检：在当前交付件上重跑全部核对项。"""
import json, re, pathlib, statistics, glob
BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
V = json.load(open(BASE + "/_verify1.json", encoding="utf-8"))
T = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html")
t = T.read_text(encoding="utf-8")
fails = []

def sec(n):
    a = t.find('<h2><span class="no">%s</span>' % n)
    b = t.find('<h2><span class="no">', a+10)
    return t[a:b if b > 0 else len(t)]
def rows_of(tbl):
    return [[re.sub(r'<[^>]+>', '', c).strip()
             for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            for tr in re.findall(r'<tr>(.*?)</tr>', tbl, re.S)]
def chk(tag, got, exp):
    ok = got == exp
    if not ok: fails.append((tag, got, exp))
    return ok

# §02 总榜（满分判据 CER==0）
KM = {"RapidOCRLite medium":"rapidocrlite-medium","RapidOCRLite small":"rapidocrlite-small",
      "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default",
      "PaddleOCR 官方":"paddleocr","EasyOCR":"easyocr","GLM-OCR 0.9B":"glmocr",
      "LightOnOCR-3 原始输出":"lightonocr","LightOnOCR-3 剥标记":"lightonocr-stripped"}
# §02 现为 9 行（R2 补回 GLM-OCR）
n02 = ok02 = 0
for r in rows_of(re.search(r'<div class="tw"><table>.*?</table></div>', sec("02"), re.S).group(0))[1:]:
    if r[0] not in KM: continue
    d = V[KM[r[0]]]
    perf = sum(1 for x in d["rows"] if x["cer"] == 0)
    exp = ["%.4f"%d["med"], "%.4f"%d["mean"], "%.4f"%d["p90"], "%d/24"%perf,
           "%.2f s"%d["t"], "%.0f MB"%d["rss"]]
    got = r[1:7]
    n02 += 1
    if got == exp: ok02 += 1
    else: fails.append(("§02 "+r[0], got, exp))

# §05 逐样本
KM5 = {"Simd受控":"simdpaddleocr","Simd默认":"simdpaddleocr-default",
       "Rcl-med":"rapidocrlite-medium","Rcl-small":"rapidocrlite-small",
       "Paddle官方":"paddleocr","EasyOCR":"easyocr",
       "LightOn":"lightonocr-stripped","GLM-OCR":"glmocr"}
idx = {k: {x["img"]: x for x in V[k]["rows"]} for k in KM5.values()}
tot05 = ok05 = 0
for r in rows_of(re.search(r'<div class="tw"><table>.*?</table></div>', sec("05"), re.S).group(0))[1:]:
    img = r[0]
    if img not in idx["glmocr"]: continue
    for j, name in enumerate(KM5):
        k = KM5[name]
        exp = "%.4f" % idx[k][img]["cer"] if img in idx[k] else "—"
        tot05 += 1
        if r[j+1] == exp: ok05 += 1
        else: fails.append(("§05 "+img+" "+name, r[j+1], exp))

# §10①② + §12表0
G, L = V["glmocr"], V["lightonocr-stripped"]
gp = sum(1 for x in G["rows"] if x["cer"]==0); lp = sum(1 for x in L["rows"] if x["cer"]==0)
n10 = ok10 = 0
for r in rows_of(re.findall(r'<div class="tw"><table>.*?</table></div>', sec("10"), re.S)[-1])[1:]:
    exp = {"CER 中位":("%.4f"%G["med"], "%.4f"%L["med"]),
           "CER 均值":("%.4f"%G["mean"], "%.4f"%L["mean"]),
           "满分张数":("%d/24"%gp, "%d/24"%lp),
           "单页耗时中位":("%.2f s"%G["t"], "%.2f s"%L["t"]),
           "内存峰值中位":("%.0f MB"%G["rss"], "%.0f MB"%L["rss"])}.get(r[0])
    if exp:
        n10 += 1
        if (r[1], r[2]) == exp: ok10 += 1
        else: fails.append(("§10③ "+r[0], (r[1],r[2]), exp))

# §12 表0
n12 = ok12 = 0
for r in rows_of(re.findall(r'<div class="tw"><table>.*?</table></div>', sec("12"), re.S)[0])[1:]:
    exp = {"CER 中位":("%.4f"%G["med"], "%.4f"%L["med"]),
           "CER 均值":("%.4f"%G["mean"], "%.4f"%L["mean"]),
           "CER p90":("%.4f"%G["p90"], "%.4f"%L["p90"]),
           "满分张数":("%d/24"%gp, "%d/24"%lp),
           "单页耗时中位":("%.2f s"%G["t"], "%.2f s"%L["t"]),
           "内存峰值中位":("%.0f MB"%G["rss"], "%.0f MB"%L["rss"]),
           "权重体积 / 量化":("2.66 GB / F16", "1.02 GB / Q8_0")}.get(r[0])
    if exp:
        n12 += 1
        if (r[1], r[2]) == exp: ok12 += 1
        else: fails.append(("§12表0 "+r[0], (r[1],r[2]), exp))

# §04 图
i4 = t.find('<h2><span class="no">04</span>'); i5 = t.find('<h2><span class="no">05</span>')
svgs = list(re.finditer(r'<svg viewBox.*?</svg>', t[i4:i5], re.S))
KMC = {"Rcl-med":"rapidocrlite-medium","Rcl-small":"rapidocrlite-small",
       "Simd受控":"simdpaddleocr","Simd默认":"simdpaddleocr-default",
       "EasyOCR":"easyocr","Paddle官方":"paddleocr","GLM-OCR":"glmocr"}
ok04 = n04 = 0
for k, s in enumerate(svgs[:2]):
    for lb, vl in zip(re.findall(r'class="bl">([^<]+)</text>', s.group(0)),
                      re.findall(r'class="bv">([^<]+)</text>', s.group(0))):
        d = V["lightonocr-stripped"] if lb == "LightOn" else V[KMC[lb]]
        exp = ("%.2f s"%d["t"] if k==0 else "%.0f MB"%d["rss"])
        n04 += 1
        if vl == exp: ok04 += 1
        else: fails.append(("§04图%d %s"%(k+1,lb), vl, exp))

# 正文关键数字
KEY = ["8.3 倍","4.13 倍","省 53%","快 1.97 倍","省 54%","+39%","0.0242","0.0263",
       "0.1896","0.5167","0.65 s","323 MB","26.77 s","1562 MB","66.7%","0.9905",
       "0.033","135.45","0.51 s","+11.1%","−20.3%","−12.5%","快 3.6 倍","省 31%",
       "10/24","9/24","2/24","use_dilation"]
miss = [k for k in KEY if k not in t]

print("="*76); print("终检结果"); print("="*76)
print("  §02 总榜        %d/%d  %s" % (ok02, n02, "✅" if ok02==n02 else "❌"))
print("  §05 逐样本      %d/%d  %s" % (ok05, tot05, "✅" if ok05==tot05 else "❌"))
print("  §10③ 对照       %d/%d  %s" % (ok10, n10, "✅" if ok10==n10 else "❌"))
print("  §12表0 对照     %d/%d  %s" % (ok12, n12, "✅" if ok12==n12 else "❌"))
print("  §04 图表数值    %d/%d  %s" % (ok04, n04, "✅" if ok04==n04 else "❌"))
print("  关键数字在场    %d/%d  %s" % (len(KEY)-len(miss), len(KEY), "✅" if not miss else "❌ 缺 "+str(miss)))
print("\n  失败项总数: %d" % len(fails))
for f in fails[:20]: print("   ", f)
print("\n  文件 %.2f MB   章节 %d" % (T.stat().st_size/1e6, len(re.findall(r'<h2><span class="no">', t))))
