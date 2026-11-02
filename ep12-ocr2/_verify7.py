
# -*- coding: utf-8 -*-
"""核 §10① PaddleOCR 跨期复现 / §10② GLM-OCR vs GOT-OCR2.0。
上期数值从 ep11 result.json 现算，不抄报告。"""
import json, pathlib
E11 = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr")
R = json.loads((E11/"result.json").read_text(encoding="utf-8"))["cells"]
EXCL = {"book_02", "skew_02"}

def agg(eng):
    sub = [c for k, c in R.items()
           if k.startswith(eng+"__") and k.endswith("__hot")
           and k.split("__")[1] not in EXCL and not c.get("err")]
    cs = sorted(c["cer_main"] for c in sub if c.get("cer_main") is not None)
    ts = sorted(c["median"] for c in sub if c.get("median"))
    rs = sorted(c["peak_rss_mb"] for c in sub if c.get("peak_rss_mb"))
    return {"n": len(cs), "med": cs[len(cs)//2], "mean": sum(cs)/len(cs),
            "t": ts[len(ts)//2], "rss": rs[len(rs)//2]}

out = {e: agg(e) for e in ["paddleocr", "gotocr", "rapidocr"]}
print("=== ep11 上期数值（现算，24 图口径剔除同两张）===")
for k, d in out.items():
    print("  %-10s n=%-3d CER中位=%.4f 均值=%.4f 耗时=%.2f 峰值=%.0f" % (
        k, d["n"], d["med"], d["mean"], d["t"], d["rss"]))
json.dump(out, open(r"D:/study/ai-jms/ep12-ocr2-venvs/_ep11agg.json","w",encoding="utf-8"))

# 本期 paddleocr / glmocr
V = json.loads(pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_verify1.json").read_text(encoding="utf-8"))
P, G = V["paddleocr"], V["glmocr"]
print("\n=== 本期 ===")
print("  paddleocr CER中位=%.4f 均值=%.4f 耗时=%.2f 峰值=%.0f" % (P["med"], P["mean"], P["t"], P["rss"]))
print("  glmocr    CER中位=%.4f 均值=%.4f 耗时=%.2f 峰值=%.0f" % (G["med"], G["mean"], G["t"], G["rss"]))

print("\n=== §10① PaddleOCR 跨期表（报告应写的值）===")
p11 = out["paddleocr"]
print("  CER 中位  %.4f -> %.4f   %+.1f%%" % (p11["med"], P["med"], (P["med"]-p11["med"])/p11["med"]*100))
print("  CER 均值  %.4f -> %.4f   %+.1f%%" % (p11["mean"], P["mean"], (P["mean"]-p11["mean"])/p11["mean"]*100))
print("  耗时中位  %.2f -> %.2f   %+.1f%%" % (p11["t"], P["t"], (P["t"]-p11["t"])/p11["t"]*100))
print("  峰值中位  %.0f -> %.0f   %+.1f%%" % (p11["rss"], P["rss"], (P["rss"]-p11["rss"])/p11["rss"]*100))

print("\n=== §10② GLM-OCR vs GOT-OCR2.0（报告应写的值）===")
g11 = out["gotocr"]
print("  CER 中位  %.4f -> %.4f" % (g11["med"], G["med"]))
print("  耗时中位  %.2f -> %.2f   快 %.1f 倍" % (g11["t"], G["t"], g11["t"]/G["t"]))
print("  峰值中位  %.0f -> %.0f   省 %.0f%%" % (g11["rss"], G["rss"], (1-G["rss"]/g11["rss"])*100))
print("  耗时比值 %.2f/%.2f = %.2f" % (g11["t"], G["t"], g11["t"]/G["t"]))

print("\n=== §10 陷阱：ep11 rapidocr vs 本期 rapidocrlite ===")
r11 = out["rapidocr"]
rm = V["rapidocrlite-medium"]
print("  ep11 rapidocr   模型=PP-OCRv4  耗时=%.2f CER中位=%.4f" % (r11["t"], r11["med"]))
print("  本期 RCL medium 模型=PP-OCRv6  耗时=%.2f CER中位=%.4f" % (rm["t"], rm["med"]))
print("  耗时差 %+.1f%%   CER %.4f -> %.4f" % ((rm["t"]-r11["t"])/r11["t"]*100, r11["med"], rm["med"]))
