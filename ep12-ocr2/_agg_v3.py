
# -*- coding: utf-8 -*-
"""ep12 终版汇总 v3 —— 精确复现已发布报告的口径。

归一化（已全量核验：6 配置 × 24 格 = 144 格与报告逐位一致，0 处不符）：
  NFKC → 只滤 Unicode 类别 P（标点）→ 小写 → 去所有空白
  ⚠️ 保留 S 类符号（| ^ + = ~ < > ∗ 等）。这是与 ep11 cer.py 的关键差别：
     cer.py 用固定 PUNCT 集合 + 同时滤 P/S 两类，会多删掉 S 类符号，
     导致 gt_len 偏差（book_01 差 3、shot_02 差 10、hard_01 差 3）。
  CER = 编辑距离 / len(归一化 GT)

口径决策（用户批复 A）：
  - 剔除 book_02 / skew_02（GT 不完整）
  - vert_01/02 走字符层面判读（顺序 CER 对竖排误判）
  - LightOnOCR 报两个口径：raw / stripped（用户批复 A：两口径都报）
"""
import json, glob, os, re, unicodedata
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
GTD = [r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/gt",
       r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]

def normalize(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(c for c in s if unicodedata.category(c)[0] != "P")
    s = s.lower()
    return "".join(c for c in s if not c.isspace())

def lev(a, b):
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def cer(ref, hyp):
    r, h = normalize(ref), normalize(hyp)
    return lev(r, h) / float(len(r)) if r else None

def gt(img):
    for d in GTD:
        p = os.path.join(d, img + ".txt")
        if os.path.exists(p): return open(p, encoding="utf-8").read()
    return None

COORD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
TAG   = re.compile(r"</?[a-zA-Z][^>]*>")
def strip_markup(s):
    s = COORD.sub(" ", s); s = TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s)

EXCL = {"book_02", "skew_02"}
VERT = {"vert_01", "vert_02"}

def char_metric(g, h):
    r_, h_ = normalize(g), normalize(h)
    cr, ch = Counter(r_), Counter(h_)
    miss, extra = sum((cr-ch).values()), sum((ch-cr).values())
    return ((miss+extra)/float(len(r_)) if r_ else None), miss, extra

def evaluate(eng, transform=None):
    rows = []
    for f in sorted(glob.glob(BASE + "/cells/%s__*.json" % eng)):
        c = json.load(open(f, encoding="utf-8"))
        img = c["img"].replace(".png", "")
        if img in EXCL or c.get("err") or not c.get("median"): continue
        g = gt(img)
        if g is None: continue
        hyp = c.get("text") or ""
        if transform: hyp = transform(hyp)
        if img in VERT:
            used, miss, extra = char_metric(g, hyp); metric = "char"
        else:
            used = cer(g, hyp); metric = "order"
            r_, h_ = normalize(g), normalize(hyp)
            cr, ch = Counter(r_), Counter(h_)
            miss, extra = sum((cr-ch).values()), sum((ch-cr).values())
        rows.append({"img": img, "cer": used, "metric": metric,
                     "miss": miss, "extra": extra,
                     "gt_len": len(normalize(g)), "hyp_len": len(normalize(hyp)),
                     "median": c["median"], "spread": c.get("spread_pct"),
                     "peak": c.get("peak_rss_mb"), "n_lines": c.get("n_lines")})
    cs = sorted(r["cer"] for r in rows if r["cer"] is not None)
    t  = sorted(r["median"] for r in rows)
    pk = sorted(r["peak"] for r in rows if r["peak"])
    p90 = cs[int(round(0.9*(len(cs)-1)))] if cs else None
    return {"n": len(rows), "cer_med": cs[len(cs)//2] if cs else None,
            "cer_mean": sum(cs)/len(cs) if cs else None, "cer_p90": p90,
            "perfect": sum(1 for x in cs if x < 0.005),
            "t_med": t[len(t)//2] if t else None,
            "rss_med": pk[len(pk)//2] if pk else None,
            "max_spread": max((r["spread"] or 0 for r in rows), default=0),
            "rows": rows}

ENGS = ["rapidocrlite-medium", "rapidocrlite-small", "simdpaddleocr",
        "simdpaddleocr-default", "paddleocr", "easyocr", "glmocr"]
out = {e: evaluate(e) for e in ENGS}
out["lightonocr"] = evaluate("lightonocr")
out["lightonocr-stripped"] = evaluate("lightonocr", strip_markup)
json.dump(out, open(BASE + "/_agg_v3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 与已发布报告逐位核验
RD = json.load(open(BASE + "/report_data.json", encoding="utf-8"))
print("=== 与已发布报告逐格核验 ===")
for eng in ENGS:
    rep = {r["img"]: r for r in RD["rows"] if r["engine"] == eng}
    nd = sum(1 for r in out[eng]["rows"]
             if r["img"] in rep and abs(r["cer"] - rep[r["img"]]["cer_used"]) > 1e-9)
    print("  %-24s 不符 %d / %d  %s" % (eng, nd, len(out[eng]["rows"]), "✅" if nd == 0 else "❌"))

print("\n" + "="*104)
print("ep12 终版汇总 v3（24 图，剔除 book_02/skew_02；vert 走字符层面）")
print("="*104)
print("%-26s %-4s %-8s %-8s %-8s %-5s %-8s %-9s %-8s" % (
    "配置","n","CER中位","CER均值","CER p90","满分","耗时中位","峰值中位MB","离散度最大"))
for k in ENGS + ["lightonocr", "lightonocr-stripped"]:
    d = out[k]
    print("%-26s %-4d %-8.4f %-8.4f %-8.4f %-5d %-8.2f %-9.0f %-7.2f%%" % (
        k, d["n"], d["cer_med"], d["cer_mean"], d["cer_p90"],
        d["perfect"], d["t_med"], d["rss_med"], d["max_spread"]))
