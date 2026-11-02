
# -*- coding: utf-8 -*-
"""把 HTML 报告里每个表格的数字提出来，与独立重算结果逐格比对。"""
import json, re, pathlib

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
V = json.load(open(BASE + "/_verify1.json", encoding="utf-8"))
t = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html").read_text(encoding="utf-8")

def sec(n):
    a = t.find('<h2><span class="no">%s</span>' % n)
    b = t.find('<h2><span class="no">', a+10)
    return t[a:b if b > 0 else len(t)]

def cells(tbl_html):
    """返回 [(行文本列表)]"""
    out = []
    for tr in re.findall(r'<tr>(.*?)</tr>', tbl_html, re.S):
        out.append([re.sub(r'<[^>]+>', '', c).strip()
                    for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)])
    return out

fails = []

# ── §02 总榜 ──
print("="*80); print("§02 总榜"); print("="*80)
tbl = re.search(r'<div class="tw"><table>.*?</table></div>', sec("02"), re.S).group(0)
rows = cells(tbl)
KEYMAP = {"RapidOCRLite medium":"rapidocrlite-medium","RapidOCRLite small":"rapidocrlite-small",
          "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default",
          "PaddleOCR 官方":"paddleocr","EasyOCR":"easyocr","GLM-OCR 0.9B":"glmocr",
          "LightOnOCR-3 原始输出":"lightonocr","LightOnOCR-3 剥标记":"lightonocr-stripped"}
for r in rows[1:]:
    if len(r) < 7: continue
    nm = r[0]
    if nm not in KEYMAP: 
        print("  ? 未识别行:", nm); continue
    d = V[KEYMAP[nm]]
    chk = [("CER中位", r[1], "%.4f"%d["med"]), ("CER均值", r[2], "%.4f"%d["mean"]),
           ("p90", r[3], "%.4f"%d["p90"]), ("满分", r[4], "%d/24"%d["perfect"]),
           ("耗时", r[5].replace(" s",""), "%.2f"%d["t"]), ("峰值", r[6].replace(" MB",""), "%.0f"%d["rss"])]
    bad = [(k, a, b) for k, a, b in chk if a != b]
    if bad:
        fails.append(("§02 "+nm, bad))
        print("  ❌ %-24s %s" % (nm, bad))
    else:
        print("  ✅ %-24s 6 项全对" % nm)

# ── §11 small vs medium ──
print("\n"+"="*80); print("§11 降档位汇总表"); print("="*80)
s11 = sec("11")
m, s = V["rapidocrlite-medium"], V["rapidocrlite-small"]
tbl11 = re.findall(r'<div class="tw"><table>.*?</table></div>', s11, re.S)
for r in cells(tbl11[0])[1:]:
    k, a, b, ch = r[0], r[1], r[2], r[3]
    exp = {"CER 中位":("%.4f"%m["med"], "%.4f"%s["med"], "−3.2%"),
           "CER 均值":("%.4f"%m["mean"], "%.4f"%s["mean"], "+0.0%"),
           "CER p90":("%.4f"%m["p90"], "%.4f"%s["p90"], "−24.6%"),
           "满分张数":("%d/24"%m["perfect"], "%d/24"%s["perfect"], "持平"),
           "单页耗时中位":("%.2f s"%m["t"], "%.2f s"%s["t"], "快 4.13 倍"),
           "内存峰值中位":("%.0f MB"%m["rss"], "%.0f MB"%s["rss"], "省 53%")}.get(k)
    if not exp: print("  ? 未识别:", k); continue
    ok = (a, b, ch) == exp
    if not ok: fails.append(("§11 "+k, (a,b,ch), exp))
    print("  %s %-14s 报告[%s|%s|%s]  应为[%s|%s|%s]" % ("✅" if ok else "❌", k, a, b, ch, *exp))

print("\n"+"="*80)
print("失败项: %d" % len(fails))
for f in fails: print("  ", f)
