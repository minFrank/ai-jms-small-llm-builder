
# -*- coding: utf-8 -*-
"""核对 v3：§12 两张表 / §10 第③组 / §05 逐样本表 / 正文推导倍数。"""
import json, re, pathlib
BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
V = json.load(open(BASE + "/_verify1.json", encoding="utf-8"))
t = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html").read_text(encoding="utf-8")
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
    print("  %s %-22s %s%s" % ("✅" if ok else "❌", tag, got, "" if ok else ("  应为 " + str(exp))))

G, L = V["glmocr"], V["lightonocr-stripped"]
LR = V["lightonocr"]
gp = sum(1 for x in G["rows"] if x["cer"]==0)
lp = sum(1 for x in L["rows"] if x["cer"]==0)
lrp = sum(1 for x in LR["rows"] if x["cer"]==0)

# ── §12 表② 剥标记后与 GLM-OCR 正面比 ──
print("="*74); print("§12 表② GLM-OCR vs LightOnOCR-3"); print("="*74)
tbls12 = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("12"), re.S)
for r in rows_of(tbls12[1])[1:]:
    k, a, b = r[0], r[1], r[2]
    exp = {"CER 中位":("%.4f"%G["med"], "%.4f"%L["med"]),
           "CER 均值":("%.4f"%G["mean"], "%.4f"%L["mean"]),
           "CER p90":("%.4f"%G["p90"], "%.4f"%L["p90"]),
           "满分张数":("%d/24"%gp, "%d/24"%lp),
           "单页耗时中位":("%.2f s"%G["t"], "%.2f s"%L["t"]),
           "内存峰值中位":("%.0f MB"%G["rss"], "%.0f MB"%L["rss"])}.get(k)
    if exp: chk("§12 "+k, (a, b), exp)

# ── §10 第③组 ──
print("\n"+"="*74); print("§10 第③组 GLM-OCR vs LightOnOCR-3"); print("="*74)
tbls10 = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("10"), re.S)
for r in rows_of(tbls10[-1])[1:]:
    k, a, b = r[0], r[1], r[2]
    exp = {"CER 中位":("%.4f"%G["med"], "%.4f"%L["med"]),
           "CER 均值":("%.4f"%G["mean"], "%.4f"%L["mean"]),
           "满分张数":("%d/24"%gp, "%d/24"%lp),
           "单页耗时中位":("%.2f s"%G["t"], "%.2f s"%L["t"]),
           "内存峰值中位":("%.0f MB"%G["rss"], "%.0f MB"%L["rss"])}.get(k)
    if exp: chk("§10③ "+k, (a, b), exp)

# ── §05 逐样本表 8 列 × 24 行 ──
print("\n"+"="*74); print("§05 逐样本表（8 配置 × 24 样本）"); print("="*74)
KM = {"Simd受控":"simdpaddleocr","Simd默认":"simdpaddleocr-default",
      "Rcl-med":"rapidocrlite-medium","Rcl-small":"rapidocrlite-small",
      "Paddle官方":"paddleocr","EasyOCR":"easyocr",
      "LightOn":"lightonocr-stripped","GLM-OCR":"glmocr"}
idx = {k: {x["img"]: x for x in V[k]["rows"]} for k in KM.values()}
tbl05 = re.search(r'<div class="tw"><table>.*?</table></div>', sec("05"), re.S).group(0)
nd = tot = 0
for r in rows_of(tbl05)[1:]:
    img = r[0]
    if img not in idx["glmocr"]: continue
    for j, name in enumerate(KM):
        got = r[j+1]; k = KM[name]
        if img not in idx[k]: exp = "—"
        else:
            c = idx[k][img]["cer"]
            exp = "%.4f" % c
            if c == 0: exp = "%.4f" % c          # 报告里满分加粗但数值不变
        tot += 1
        if got != exp:
            nd += 1
            if nd <= 12: print("  ❌ %-11s %-12s 报告=%-9s 应为=%s" % (img, name, got, exp))
print("  逐样本表: %d 格核对，不符 %d %s" % (tot, nd, "✅" if nd==0 else "❌"))
if nd: fails.append(("§05 逐样本表", "%d 格不符" % nd, "0"))

# ── 正文推导倍数 ──
print("\n"+"="*74); print("正文推导倍数"); print("="*74)
Rm, Rs = V["rapidocrlite-medium"], V["rapidocrlite-small"]
Pd, Gm = V["paddleocr"], V["glmocr"]
derived = [
 ("8.3 倍 (22.19/2.67)", round(Pd["t"]/Rm["t"], 1), 8.3),
 ("4.13 倍 (2.67/0.65)", round(Rm["t"]/Rs["t"], 2), 4.13),
 ("省 53% (1-323/686)", round((1-Rs["rss"]/Rm["rss"])*100), 53),
 ("LightOn 快 1.97 倍 (52.68/26.77)", round(Gm["t"]/L["t"], 2), 1.97),
 ("LightOn 省 54% (1-1562/3361)", round((1-L["rss"]/Gm["rss"])*100), 54),
 ("small CER 中位 −3.2%", round((Rs["med"]-Rm["med"])/Rm["med"]*100, 1), -3.2),
 ("small CER p90 −24.6%", round((Rs["p90"]-Rm["p90"])/Rm["p90"]*100, 1), -24.6),
 ("LightOn 均值好 9.8%", round((Gm["mean"]-L["mean"])/Gm["mean"]*100, 1), 9.8),
 ("GLM 满分多 4 张", gp-lp, 4),
]
for name, got, exp in derived:
    chk(name, got, exp)

print("\n"+"="*74); print("失败项: %d" % len(fails)); print("="*74)
for f in fails: print("  ", f)
