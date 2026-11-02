
# -*- coding: utf-8 -*-
"""总榜表补充统计：p90 / 满分张数 / 离散度最大值。"""
import json, glob, os, sys, re
sys.path.insert(0, r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr")
import cer as cermod
from collections import Counter

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
GTD = [r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/gt",
       r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]

def gt(img):
    for d in GTD:
        p = os.path.join(d, img + ".txt")
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return None

COORD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
TAG   = re.compile(r"</?[a-zA-Z][^>]*>")
def strip_markup(s):
    s = COORD.sub(" ", s)
    s = TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s)

EXCL = {"book_02", "skew_02"}
VERT = {"vert_01", "vert_02"}

def char_metric(g, h):
    r_, h_ = cermod.normalize(g, True), cermod.normalize(h, True)
    cr, ch = Counter(r_), Counter(h_)
    miss, extra = sum((cr-ch).values()), sum((ch-cr).values())
    return ((miss+extra)/float(len(r_)) if r_ else None)

def pctl(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = int(round(q * (len(xs) - 1)))
    return xs[i]

def stats(eng, transform=None):
    rows = []
    for f in sorted(glob.glob(BASE + "/cells/%s__*.json" % eng)):
        c = json.load(open(f, encoding="utf-8"))
        img = c["img"].replace(".png", "")
        if img in EXCL or c.get("err") or not c.get("median"):
            continue
        g = gt(img)
        if g is None:
            continue
        hyp = c.get("text") or ""
        if transform:
            hyp = transform(hyp)
        if img in VERT:
            used = char_metric(g, hyp)
        else:
            used = cermod.cer(g, hyp, True)
        rows.append({"img": img, "cer": used,
                     "median": c["median"], "spread": c.get("spread_pct") or 0})
    cer = [r["cer"] for r in rows if r["cer"] is not None]
    perfect = sum(1 for x in cer if x < 0.005)
    return {"n": len(rows), "p90": pctl(cer, 0.9), "perfect": perfect,
            "max_spread": max((r["spread"] for r in rows), default=0)}

ENGS = [("rapidocrlite-medium","RapidOCRLite medium"),
        ("rapidocrlite-small","RapidOCRLite small"),
        ("simdpaddleocr","SimdPaddleOCR 受控"),
        ("simdpaddleocr-default","SimdPaddleOCR 默认"),
        ("paddleocr","PaddleOCR 官方"),
        ("easyocr","EasyOCR"),
        ("glmocr","GLM-OCR 0.9B"),
        ("lightonocr","LightOnOCR-3 raw"),
        ("lightonocr","LightOnOCR-3 剥标记")]

print("%-24s %-4s %-9s %-8s %-10s" % ("配置","n","CER p90","满分","离散度最大"))
out = {}
for eng, label in ENGS:
    tr = strip_markup if label.endswith("剥标记") else None
    s = stats(eng, tr)
    out[label] = s
    print("%-24s %-4d %-9.4f %-8d %-10.2f%%" % (label, s["n"], s["p90"], s["perfect"], s["max_spread"]))
json.dump(out, open(BASE + "/_agg_stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
