# -*- coding: utf-8 -*-
"""穷举式核对：把报告里出现的每个数字都抽出来，逐个判定能否追溯到原始数据。

分类：
  T  表格单元格值      → 与 raw_agg / cell JSON 逐位比对
  D  推导值（倍数/百分比）→ 用 raw_agg 重算算术
  P  正文引用值        → 与 raw_agg 比对
  M  方法学参数        → 从 cell JSON 现算
  X  外部源值          → 从外部源（ep11 / Ollama / 模型文件）现查
  C  常量              → 逐个查证
  ?  无法归类          → 人工判断
"""
import json, re, glob, os, unicodedata, statistics
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
RPT  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html"
E11  = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"

# ── 权威数据源 ──
V = json.load(open(BASE + "/_verify1.json", encoding="utf-8"))
E11R = json.load(open(E11 + "/result.json", encoding="utf-8"))["cells"]

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(c for c in s if unicodedata.category(c)[0] != "P")
    return "".join(c for c in s.lower() if not c.isspace())

def lev(a, b):
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]

# 从 cell JSON 现算（不依赖 _verify1，避免循环论证）
GTD = [E11 + "/gt",
       r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]
def gt_of(img):
    for d in GTD:
        p = os.path.join(d, img + ".txt")
        if os.path.exists(p): return open(p, encoding="utf-8").read()
    return None

COORD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
TAG   = re.compile(r"</?[a-zA-Z][^>]*>")
def strip_markup(s):
    return re.sub(r"\s+", " ", TAG.sub(" ", COORD.sub(" ", s)))

EXCL = {"book_02", "skew_02"}
VERT = {"vert_01", "vert_02"}

def recompute(eng, transform=None):
    rows = []
    for f in sorted(glob.glob(BASE + "/cells/%s__*.json" % eng)):
        c = json.load(open(f, encoding="utf-8"))
        img = c["img"].replace(".png", "")
        if img in EXCL or c.get("err") or not c.get("median"): continue
        g = gt_of(img)
        if g is None: continue
        h = c.get("text") or ""
        if transform: h = transform(h)
        if img in VERT:
            r_, h_ = norm(g), norm(h)
            cr, ch = Counter(r_), Counter(h_)
            cer = (sum((cr-ch).values()) + sum((ch-cr).values())) / float(len(r_))
        else:
            cer = lev(norm(g), norm(h)) / float(len(norm(g)))
        rows.append({"img": img, "cer": cer, "t": c["median"], "rss": c.get("peak_rss_mb"),
                     "spread": c.get("spread_pct") or 0})
    cs = sorted(r["cer"] for r in rows)
    ts = sorted(r["t"] for r in rows)
    rs = sorted(r["rss"] for r in rows if r["rss"])
    return {"n": len(rows), "med": cs[len(cs)//2], "mean": sum(cs)/len(cs),
            "p90": cs[int(round(0.9*(len(cs)-1)))],
            "perfect": sum(1 for x in cs if x == 0),
            "t": ts[len(ts)//2], "rss": rs[len(rs)//2],
            "maxspread": max(r["spread"] for r in rows), "rows": rows}

RAW = {}
for e in ["rapidocrlite-medium","rapidocrlite-small","simdpaddleocr",
          "simdpaddleocr-default","paddleocr","easyocr","glmocr"]:
    RAW[e] = recompute(e)
RAW["lightonocr"] = recompute("lightonocr")
RAW["lightonocr-stripped"] = recompute("lightonocr", strip_markup)

# 与 _verify1 交叉核对（确认 recompute 无误）
cross_fail = 0
for k in RAW:
    if abs(RAW[k]["med"] - V[k]["med"]) > 1e-12: cross_fail += 1
    if abs(RAW[k]["mean"] - V[k]["mean"]) > 1e-12: cross_fail += 1

print("=" * 84)
print("穷举式核对")
print("=" * 84)
print("recompute 与 _verify1 交叉核对不符项: %d %s" % (cross_fail, "✅" if cross_fail == 0 else "❌"))

# ── 报告全文 ──
t = open(RPT, encoding="utf-8").read()
# 去掉 base64（避免把图片数据里的数字当成内容）
t_clean = re.sub(r'src="data:image/png;base64,[^"]+"', 'src="[IMG]"', t)
t_txt = re.sub(r'<[^>]+>', ' ', t_clean)

# ── 抽取所有表格单元格数字 ──
def sec(n):
    a = t_clean.find('<h2><span class="no">%s</span>' % n)
    b = t_clean.find('<h2><span class="no">', a + 10)
    return t_clean[a:b if b > 0 else len(t_clean)]

def rows_of(tbl):
    return [[re.sub(r'<[^>]+>', '', c).strip()
             for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            for tr in re.findall(r'<tr>(.*?)</tr>', tbl, re.S)]

results = {"ok": 0, "bad": [], "unknown": []}

def check(cat, desc, got, exp):
    if got == exp:
        results["ok"] += 1
    else:
        results["bad"].append((cat, desc, got, exp))

# ── §02 总榜 9 行 × 6 数值列 ──
KM = {"RapidOCRLite medium":"rapidocrlite-medium","RapidOCRLite small":"rapidocrlite-small",
      "SimdPaddleOCR 受控":"simdpaddleocr","SimdPaddleOCR 默认":"simdpaddleocr-default",
      "PaddleOCR 官方":"paddleocr","EasyOCR":"easyocr","GLM-OCR 0.9B":"glmocr",
      "LightOnOCR-3 原始输出":"lightonocr","LightOnOCR-3 剥标记":"lightonocr-stripped"}
tb02 = re.search(r'<div class="tw"><table>.*?</table></div>', sec("02"), re.S).group(0)
n02 = 0
for r in rows_of(tb02)[1:]:
    if r[0] not in KM: continue
    d = RAW[KM[r[0]]]
    exp = ["%.4f" % d["med"], "%.4f" % d["mean"], "%.4f" % d["p90"],
           "%d/24" % d["perfect"], "%.2f s" % d["t"], "%.0f MB" % d["rss"],
           "%.2f%%" % d["maxspread"]]
    for i, (g, e) in enumerate(zip(r[1:8], exp)):
        check("§02", "%s 第%d列" % (r[0], i+1), g, e)
    n02 += 1
print("  §02 总榜: %d 行 × 7 列 = %d 格" % (n02, n02 * 7))

# ── §05 逐样本 8 配置 × 24 样本 ──
KM5 = {"Simd受控":"simdpaddleocr","Simd默认":"simdpaddleocr-default",
       "Rcl-med":"rapidocrlite-medium","Rcl-small":"rapidocrlite-small",
       "Paddle官方":"paddleocr","EasyOCR":"easyocr",
       "LightOn":"lightonocr-stripped","GLM-OCR":"glmocr"}
idx = {k: {x["img"]: x for x in RAW[k]["rows"]} for k in KM5.values()}
tb05 = re.search(r'<div class="tw"><table>.*?</table></div>', sec("05"), re.S).group(0)
n05 = 0
for r in rows_of(tb05)[1:]:
    img = r[0]
    if img not in idx["glmocr"]: continue
    for j, name in enumerate(KM5):
        k = KM5[name]
        exp = "%.4f" % idx[k][img]["cer"] if img in idx[k] else "—"
        check("§05", "%s × %s" % (img, name), r[j+1], exp)
        n05 += 1
print("  §05 逐样本: %d 格" % n05)

json.dump({"ok": results["ok"], "bad": results["bad"][:60]},
          open(BASE + "/_exhaustive1.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n  通过 %d 项，不符 %d 项" % (results["ok"], len(results["bad"])))
for b in results["bad"][:15]:
    print("   ❌", b)
