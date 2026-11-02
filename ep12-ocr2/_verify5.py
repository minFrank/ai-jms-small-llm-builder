
# -*- coding: utf-8 -*-
"""补核：§12 表0（对比表）+ §12 表1（逐图表）+ §03 + §11 逐图表带说明列"""
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
    print("  %s %-26s %s%s" % ("✅" if ok else "❌", tag, got, "" if ok else ("  应为 "+str(exp))))

G, L, LR = V["glmocr"], V["lightonocr-stripped"], V["lightonocr"]
gp = sum(1 for x in G["rows"] if x["cer"]==0)
lp = sum(1 for x in L["rows"] if x["cer"]==0)

# ── §12 表0 ──
print("="*74); print("§12 表0  GLM-OCR vs LightOnOCR-3"); print("="*74)
tb = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("12"), re.S)[0]
EXP = {"CER 中位":("%.4f"%G["med"], "%.4f"%L["med"]),
       "CER 均值":("%.4f"%G["mean"], "%.4f"%L["mean"]),
       "CER p90":("%.4f"%G["p90"], "%.4f"%L["p90"]),
       "满分张数":("%d/24"%gp, "%d/24"%lp),
       "单页耗时中位":("%.2f s"%G["t"], "%.2f s"%L["t"]),
       "内存峰值中位":("%.0f MB"%G["rss"], "%.0f MB"%L["rss"]),
       "权重体积 / 量化":("2.66 GB / F16", "1.02 GB / Q8_0")}
seen = 0
for r in rows_of(tb)[1:]:
    if r[0] in EXP:
        seen += 1
        chk("§12表0 "+r[0], (r[1], r[2]), EXP[r[0]])
print("  匹配到 %d 行（应 7）" % seen)

# ── §12 表1 逐图 ──
print("\n"+"="*74); print("§12 表1 逐图表"); print("="*74)
tb2 = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("12"), re.S)[1]
li = {x["img"]: x for x in L["rows"]}; gi = {x["img"]: x for x in G["rows"]}
for r in rows_of(tb2)[1:]:
    img = r[0]
    if img in li and img in gi:
        chk("§12图 "+img, (r[1], r[2]), ("%.4f"%li[img]["cer"], "%.4f"%gi[img]["cer"]))

# ── §11 逐图表（带说明列）──
print("\n"+"="*74); print("§11 逐图表（4 行）"); print("="*74)
mi = {x["img"]: x for x in V["rapidocrlite-medium"]["rows"]}
si = {x["img"]: x for x in V["rapidocrlite-small"]["rows"]}
tb3 = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("11"), re.S)[1]
for r in rows_of(tb3)[1:]:
    img = r[0]
    if img in mi:
        exp = ("%.4f"%mi[img]["cer"], "%.4f"%si[img]["cer"],
               ("%+.4f"%(si[img]["cer"]-mi[img]["cer"])).replace("-", "−"))
        chk("§11图 "+img, (r[1], r[2], r[3]), exp)

# ── §03 核心命题表 ──
print("\n"+"="*74); print("§03 核心命题（同权重三栈）"); print("="*74)
tb4 = re.search(r'<div class="tw"><table>.*?</table></div>', sec("03"), re.S).group(0)
KM3 = {"PaddleOCR 官方":"paddleocr","RapidOCRLite medium":"rapidocrlite-medium",
       "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default"}
for r in rows_of(tb4)[1:]:
    if r[0] not in KM3: continue
    d = V[KM3[r[0]]]
    chk("§03 "+r[0], (r[1], r[3], r[4]), ("%.2f s"%d["t"], "%.4f"%d["med"], "%.0f MB"%d["rss"]))

print("\n"+"="*74); print("失败项: %d" % len(fails)); print("="*74)
for f in fails: print("  ", f)
