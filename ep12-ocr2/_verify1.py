
# -*- coding: utf-8 -*-
"""独立核对：从原始 cell JSON 重算全部配置，输出可与 HTML 比对的干净结果。
不复用 _agg_v3.json —— 那是我自己生成的，要用它核对就成了循环论证。"""
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
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1]

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

def run(eng, transform=None):
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
            r_, h_ = normalize(g), normalize(h)
            cr, ch = Counter(r_), Counter(h_)
            cer = (sum((cr-ch).values()) + sum((ch-cr).values())) / float(len(r_))
        else:
            cer = lev(normalize(g), normalize(h)) / float(len(normalize(g)))
        rows.append({"img": img, "cer": cer, "t": c["median"], "rss": c.get("peak_rss_mb")})
    cs = sorted(r["cer"] for r in rows)
    ts = sorted(r["t"] for r in rows)
    rs = sorted(r["rss"] for r in rows if r["rss"])
    p90 = sorted(cs)[int(round(0.9*(len(cs)-1)))]
    return {"n": len(rows), "med": cs[len(cs)//2], "mean": sum(cs)/len(cs),
            "p90": p90, "perfect": sum(1 for x in cs if x < 0.005),
            "t": ts[len(ts)//2], "rss": rs[len(rs)//2], "rows": rows}

OUT = {}
for e in ["rapidocrlite-medium","rapidocrlite-small","simdpaddleocr",
          "simdpaddleocr-default","paddleocr","easyocr","glmocr"]:
    OUT[e] = run(e)
OUT["lightonocr"] = run("lightonocr")
OUT["lightonocr-stripped"] = run("lightonocr", strip_markup)
json.dump(OUT, open(BASE + "/_verify1.json", "w", encoding="utf-8"), ensure_ascii=False)

print("="*92)
print("独立重算（不复用 _agg_v3.json）")
print("="*92)
print("%-24s %-4s %-8s %-8s %-8s %-5s %-8s %-8s" % ("配置","n","CERmed","CERmean","p90","满分","耗时","峰值MB"))
for k, d in OUT.items():
    print("%-24s %-4d %-8.4f %-8.4f %-8.4f %-5d %-8.2f %-8.0f" % (
        k, d["n"], d["med"], d["mean"], d["p90"], d["perfect"], d["t"], d["rss"]))
