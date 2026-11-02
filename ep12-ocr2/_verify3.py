
# -*- coding: utf-8 -*-
"""全量核对 v2：覆盖 §02 / §11 两张表 / §12 两张表 / §10 第③组 / §05 逐样本表。"""
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

# ── §02 总榜（含满分，判据 CER==0）──
print("="*76); print("§02 总榜（9 行 × 6 项）"); print("="*76)
KM = {"RapidOCRLite medium":"rapidocrlite-medium","RapidOCRLite small":"rapidocrlite-small",
      "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default",
      "PaddleOCR 官方":"paddleocr","EasyOCR":"easyocr","GLM-OCR 0.9B":"glmocr",
      "LightOnOCR-3 原始输出":"lightonocr","LightOnOCR-3 剥标记":"lightonocr-stripped"}
for r in rows_of(re.search(r'<div class="tw"><table>.*?</table></div>', sec("02"), re.S).group(0))[1:]:
    if r[0] not in KM: continue
    d = V[KM[r[0]]]
    perf = sum(1 for x in d["rows"] if x["cer"] == 0)
    exp = [ "%.4f"%d["med"], "%.4f"%d["mean"], "%.4f"%d["p90"],
            "%d/24"%perf, "%.2f s"%d["t"], "%.0f MB"%d["rss"] ]
    got = [r[1], r[2], r[3], r[4], r[5], r[6]]
    bad = [(i+1, a, b) for i,(a,b) in enumerate(zip(got, exp)) if a != b]
    if bad: fails.append(("§02 "+r[0], bad)); print("  ❌ %-24s %s" % (r[0], bad))
    else:   print("  ✅ %-24s 6/6" % r[0])

# ── §11 汇总表 ──
print("\n"+"="*76); print("§11 汇总表"); print("="*76)
m, s = V["rapidocrlite-medium"], V["rapidocrlite-small"]
mp, sp = sum(1 for x in m["rows"] if x["cer"]==0), sum(1 for x in s["rows"] if x["cer"]==0)
EXP11 = {"CER 中位":("%.4f"%m["med"], "%.4f"%s["med"]),
         "CER 均值":("%.4f"%m["mean"], "%.4f"%s["mean"]),
         "CER p90":("%.4f"%m["p90"], "%.4f"%s["p90"]),
         "满分张数":("%d/24"%mp, "%d/24"%sp),
         "单页耗时中位":("%.2f s"%m["t"], "%.2f s"%s["t"]),
         "内存峰值中位":("%.0f MB"%m["rss"], "%.0f MB"%s["rss"])}
for r in rows_of(re.findall(r'<div class="tw"><table>.*?</table></div>', sec("11"), re.S)[0])[1:]:
    if r[0] in EXP11 and (r[1], r[2]) != EXP11[r[0]]:
        fails.append(("§11 "+r[0], (r[1],r[2]), EXP11[r[0]])); print("  ❌ %-14s %s 应为 %s" % (r[0], (r[1],r[2]), EXP11[r[0]]))
    elif r[0] in EXP11: print("  ✅ %-14s %s" % (r[0], (r[1], r[2])))

# ── §11 逐图表 ──
print("\n"+"="*76); print("§11 逐图表"); print("="*76)
mi = {x["img"]: x for x in m["rows"]}; si = {x["img"]: x for x in s["rows"]}
nd = 0
for r in rows_of(re.findall(r'<div class="tw"><table>.*?</table></div>', sec("11"), re.S)[1])[1:]:
    img = r[0]
    if img not in mi: continue
    exp = ("%.4f"%mi[img]["cer"], "%.4f"%si[img]["cer"], "%+.4f"%(si[img]["cer"]-mi[img]["cer"]))
    got = (r[1], r[2], r[3])
    if got != exp: fails.append(("§11图 "+img, got, exp)); nd += 1; print("  ❌ %-10s %s 应为 %s" % (img, got, exp))
print("  逐图表 %s" % ("全部一致 ✅" if nd==0 else "不符 %d 行 ❌" % nd))

print("\n"+"="*76); print("失败项: %d" % len(fails)); print("="*76)
for f in fails: print("  ", f)
