
# -*- coding: utf-8 -*-
"""ep12 终版汇总：8 个配置统一口径。

口径（与已发布报告完全一致）：
  - 剔除 book_02 / skew_02（GT 不全，用户批复 A）
  - vert_01/02 走字符层面判读（用户批复 A）
  - LightOnOCR 报两个口径：raw（默认输出含坐标+HTML标签）/ stripped（剥标记后）
"""
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
    return ((miss+extra)/float(len(r_)) if r_ else None), miss, extra

def evaluate(eng, transform=None):
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
            used, miss, extra = char_metric(g, hyp)
            metric = "char"
        else:
            used = cermod.cer(g, hyp, True)
            metric = "order"
        rows.append({"img": img, "cer": used, "metric": metric,
                     "median": c["median"], "spread": c.get("spread_pct"),
                     "peak": c.get("peak_rss_mb"),
                     "n_lines": c.get("n_lines"),
                     "text_len": c.get("text_len")})
    cer = sorted(r["cer"] for r in rows if r["cer"] is not None)
    t = sorted(r["median"] for r in rows)
    pk = sorted(r["peak"] for r in rows if r["peak"])
    return {"n": len(rows),
            "cer_med": cer[len(cer)//2] if cer else None,
            "cer_mean": sum(cer)/len(cer) if cer else None,
            "t_med": t[len(t)//2] if t else None,
            "rss_med": pk[len(pk)//2] if pk else None,
            "rows": rows}

ENGS = ["rapidocrlite-medium", "rapidocrlite-small", "simdpaddleocr",
        "simdpaddleocr-default", "paddleocr", "easyocr", "glmocr"]

out = {}
for e in ENGS:
    out[e] = evaluate(e)
out["lightonocr"] = evaluate("lightonocr")                 # raw
out["lightonocr-stripped"] = evaluate("lightonocr", strip_markup)  # 剥标记

json.dump(out, open(BASE + "/_agg_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print("="*96)
print("ep12 终版汇总（24 图，剔除 book_02/skew_02；vert 走字符层面）")
print("="*96)
print("%-26s %-4s %-9s %-9s %-9s %-10s" % ("配置","n","CER中位","CER均值","耗时中位","峰值中位MB"))
for k in ENGS + ["lightonocr", "lightonocr-stripped"]:
    d = out[k]
    print("%-26s %-4d %-9.4f %-9.4f %-9.2f %-10.0f" % (
        k, d["n"], d["cer_med"], d["cer_mean"], d["t_med"], d["rss_med"]))
