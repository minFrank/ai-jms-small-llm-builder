
# -*- coding: utf-8 -*-
"""ep12 终版汇总 v2：8 配置统一口径，与已发布报告严格对齐。

口径（已逐位复现验证，见 _repro_check）：
  normalize = NFKC → 只删 PUNCT 集合 → 小写 → 去空白
  ⚠️ 不做 Unicode P/S 类别过滤（这是与 ep11 cer.py 的唯一区别）。
     ep11 cer.py 会额外删掉 S* 类符号，如 U+2217 ∗（GT 中 3 个），
     导致 gt_len 差 3、CER 偏差。本脚本口径与已发布报告逐位一致。
  CER = 编辑距离 / len(归一化 GT)

口径决策（用户批复 A）：
  - 剔除 book_02 / skew_02（GT 不完整）
  - vert_01/02 走字符层面判读（顺序 CER 对竖排误判）
  - LightOnOCR 报两个口径：raw（默认输出含坐标+HTML 标签）/ stripped（剥标记后）
"""
import json, glob, os, re, unicodedata

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
GTD = [r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/gt",
       r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]
PUNCT = set("，。、；：？！“”‘’（）《》【】—…·　,.;:?!\"'()<>[]{}-_~/\\|@#$%^&*+=`~")

def normalize(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(ch for ch in s if ch not in PUNCT)
    s = s.lower()
    return "".join(ch for ch in s if not ch.isspace())

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
    if not r: return None
    return lev(r, h) / float(len(r))

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
    r_, h_ = normalize(g), normalize(h)
    from collections import Counter
    cr, ch = Counter(r_), Counter(h_)
    miss, extra = sum((cr - ch).values()), sum((ch - cr).values())
    return ((miss + extra) / float(len(r_)) if r_ else None), miss, extra

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
            used, miss, extra = char_metric(g, hyp)
            metric = "char"
        else:
            used = cer(g, hyp); metric = "order"
            r_, h_ = normalize(g), normalize(hyp)
            from collections import Counter
            cr, ch = Counter(r_), Counter(h_)
            miss, extra = sum((cr - ch).values()), sum((ch - cr).values())
        rows.append({"img": img, "cer": used, "metric": metric,
                     "miss": miss, "extra": extra,
                     "gt_len": len(normalize(g)), "hyp_len": len(normalize(hyp)),
                     "median": c["median"], "spread": c.get("spread_pct"),
                     "peak": c.get("peak_rss_mb"), "n_lines": c.get("n_lines")})
    cer_ = sorted(r["cer"] for r in rows if r["cer"] is not None)
    t = sorted(r["median"] for r in rows)
    pk = sorted(r["peak"] for r in rows if r["peak"])
    def pctl(xs, q):
        if not xs: return None
        return sorted(xs)[int(round(q * (len(xs) - 1)))]
    return {"n": len(rows), "cer_med": cer_[len(cer_)//2], "cer_mean": sum(cer_)/len(cer_),
            "cer_p90": pctl(cer_, 0.9),
            "perfect": sum(1 for x in cer_ if x < 0.005),
            "t_med": t[len(t)//2], "rss_med": pk[len(pk)//2] if pk else None,
            "max_spread": max((r["spread"] or 0 for r in rows), default=0),
            "rows": rows}

ENGS = ["rapidocrlite-medium", "rapidocrlite-small", "simdpaddleocr",
        "simdpaddleocr-default", "paddleocr", "easyocr", "glmocr"]
out = {e: evaluate(e) for e in ENGS}
out["lightonocr"] = evaluate("lightonocr")
out["lightonocr-stripped"] = evaluate("lightonocr", strip_markup)

json.dump(out, open(BASE + "/_agg_v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("="*100)
print("ep12 终版汇总 v2（24 图，剔除 book_02/skew_02；vert 走字符层面）")
print("="*100)
print("%-26s %-4s %-8s %-8s %-8s %-5s %-8s %-9s" % ("配置","n","CER中位","CER均值","CER p90","满分","耗时中位","峰值中位MB"))
for k in ENGS + ["lightonocr", "lightonocr-stripped"]:
    d = out[k]
    print("%-26s %-4d %-8.4f %-8.4f %-8.4f %-5d %-8.2f %-9.0f" % (
        k, d["n"], d["cer_med"], d["cer_mean"], d["cer_p90"],
        d["perfect"], d["t_med"], d["rss_med"]))
