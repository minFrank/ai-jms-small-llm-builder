
# -*- coding: utf-8 -*-
"""用 ep11 同一套 CER 口径算 rapidocrlite-small，并与 medium 对比。
口径：cer.py norm v1（NFKC + 去标点 + 小写 + 去空白）；
      vert_01/02 走字符层面判读（用户批复 A），其余走顺序 CER；
      剔除 book_02/skew_02（用户批复 A）。"""
import json, glob, sys, collections
from collections import Counter

sys.path.insert(0, r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr")
import cer as cermod

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
GT_DIRS = [r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/gt",
           r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"]
EXCL = {"book_02", "skew_02"}
VERT = {"vert_01", "vert_02"}

def load_gt(img):
    for d in GT_DIRS:
        p = d + "/" + img + ".txt"
        try:
            return open(p, encoding="utf-8").read()
        except Exception:
            continue
    return None

def char_metric(gt, hyp):
    """字符层面判读：归一化后比较字符多重集。返回 (cer_used, miss, extra, gt_len, hyp_len)"""
    r = cermod.normalize(gt, True)
    h = cermod.normalize(hyp, True)
    cr, ch = Counter(r), Counter(h)
    miss = sum((cr - ch).values())
    extra = sum((ch - cr).values())
    used = (miss + extra) / float(len(r)) if r else None
    return used, miss, extra, len(r), len(h)

out = {}
for eng in ["rapidocrlite-medium", "rapidocrlite-small", "lightonocr"]:
    rows = []
    for f in sorted(glob.glob(BASE + "/cells/%s__*.json" % eng)):
        c = json.load(open(f, encoding="utf-8"))
        img = c["img"].replace(".png", "")
        if img in EXCL:
            continue
        gt = load_gt(img)
        if gt is None:
            print("MISSING GT: %s" % img); continue
        if c.get("err") or not c.get("median"):
            continue
        hyp = c.get("text") or ""
        if img in VERT:
            used, miss, extra, gl, hl = char_metric(gt, hyp)
            metric = "char"
            order = cermod.cer(gt, hyp, True)
        else:
            used = cermod.cer(gt, hyp, True)
            order = used
            metric = "order"
            r = cermod.normalize(gt, True); h = cermod.normalize(hyp, True)
            cr, ch = Counter(r), Counter(h)
            miss = sum((cr - ch).values()); extra = sum((ch - cr).values())
            gl, hl = len(r), len(h)
        rows.append({"img": img, "cer_used": used, "cer_order": order, "metric": metric,
                     "miss": miss, "extra": extra, "gt_len": gl, "hyp_len": hl,
                     "median": c["median"], "spread": c.get("spread_pct"),
                     "peak": c.get("peak_rss_mb"), "err": False})
    out[eng] = rows

# 汇总
print("=" * 92)
print("RapidOCRLite 两档实测（24 图，剔除 book_02/skew_02；vert 走字符层面）")
print("=" * 92)
print("%-20s %-4s %-9s %-9s %-9s %-9s" % ("配置","n","CER中位","CER均值","耗时中位","峰值中位"))
agg = {}
for eng, rows in out.items():
    cer = sorted(r["cer_used"] for r in rows if r["cer_used"] is not None)
    t = sorted(r["median"] for r in rows)
    pk = sorted(r["peak"] for r in rows if r["peak"])
    agg[eng] = {"n": len(rows), "cer_med": cer[len(cer)//2], "cer_mean": sum(cer)/len(cer),
                "t_med": t[len(t)//2], "rss_med": pk[len(pk)//2], "rows": rows}
    print("%-20s %-4d %-9.4f %-9.4f %-9.2f %-9.1f" % (
        eng.split("-")[-1], len(rows), cer[len(cer)//2], sum(cer)/len(cer),
        t[len(t)//2], pk[len(pk)//2]))

m, s = agg["rapidocrlite-medium"], agg["rapidocrlite-small"]
print("\n  small 相对 medium:")
print("    CER 中位  %.4f -> %.4f   %+.1f%%" % (m["cer_med"], s["cer_med"],
      (s["cer_med"]-m["cer_med"])/m["cer_med"]*100))
print("    CER 均值  %.4f -> %.4f   %+.1f%%" % (m["cer_mean"], s["cer_mean"],
      (s["cer_mean"]-m["cer_mean"])/m["cer_mean"]*100))
print("    耗时中位  %.2f -> %.2f s  快 %.2f 倍" % (m["t_med"], s["t_med"], m["t_med"]/s["t_med"]))
print("    峰值中位  %.0f -> %.0f MB 省 %.0f%%" % (m["rss_med"], s["rss_med"],
      (1-s["rss_med"]/m["rss_med"])*100))

print("\n--- vert 字符层面判定 ---")
for eng in ["rapidocrlite-medium", "rapidocrlite-small", "lightonocr"]:
    for r in agg[eng]["rows"]:
        if r["img"] in VERT:
            print("  %-20s %-8s cer_used=%.4f  miss=%-3d extra=%-3d gt=%-3d hyp=%-3d" % (
                eng.split("-")[-1], r["img"], r["cer_used"], r["miss"], r["extra"],
                r["gt_len"], r["hyp_len"]))

print("\n--- 两档 CER 差最大的 6 张图 ---")
mi = {r["img"]: r for r in m["rows"]}
si = {r["img"]: r for r in s["rows"]}
diffs = [(si[k]["cer_used"]-mi[k]["cer_used"], k) for k in mi if k in si]
diffs.sort(reverse=True)
print("%-12s %-12s %-12s %s" % ("图","medium","small","差"))
for d, k in diffs[:6]:
    print("%-12s %-12.4f %-12.4f %+.4f" % (k, mi[k]["cer_used"], si[k]["cer_used"], d))

json.dump(agg, open(BASE + "/_agg_3eng.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n已存 %s/_small_agg.json" % BASE)
