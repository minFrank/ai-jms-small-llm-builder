
# -*- coding: utf-8 -*-
"""按 v3 口径重画 §04 两张条形图（8 配置）。"""
import json, pathlib
V3 = json.loads(pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_agg_v3.json").read_text(encoding="utf-8"))

# (显示名, key) —— LightOnOCR 只画剥标记行，raw 在 §12 说明
ENGS = [("Rcl-med",  "rapidocrlite-medium"),
        ("Rcl-small","rapidocrlite-small"),
        ("Simd受控",  "simdpaddleocr"),
        ("Simd默认",  "simdpaddleocr-default"),
        ("EasyOCR",  "easyocr"),
        ("Paddle官方","paddleocr"),
        ("LightOn",  "lightonocr-stripped"),
        ("GLM-OCR",  "glmocr")]

def bar_chart(items, unit, fmt, title):
    W, LEFT, BAR_H, GAP = 720, 178, 22, 24
    H = 18 + len(items) * (BAR_H + GAP)
    mx = max(v for _, v in items)
    span = W - LEFT - 120
    out = ['<svg viewBox="0 0 %d %d" class="chart" role="img"><title>%s</title>' % (W, H, title)]
    out.append('<line x1="%d" y1="6" x2="%d" y2="%d" stroke="#e3e6ea" stroke-width="1"/>' % (LEFT, LEFT, H-12))
    for i, (name, v) in enumerate(items):
        y = 12 + i * (BAR_H + GAP)
        w = max(1.0, span * v / mx)
        fill = "#b9544e" if v == mx else "#2f6fb2"
        out.append('<text x="%d" y="%d" class="bl">%s</text>' % (LEFT-10, y+16, name))
        out.append('<rect x="%d" y="%d" width="%.1f" height="%d" fill="%s" rx="1"/>'
                   % (LEFT, y, w, BAR_H, fill))
        out.append('<text x="%.1f" y="%d" class="bv">%s</text>' % (LEFT+w+8, y+16, fmt(v)))
    out.append('</svg>')
    return "".join(out)

t_item = [(n, V3[k]["t_med"]) for n, k in ENGS]
m_item = [(n, V3[k]["rss_med"]) for n, k in ENGS]

svg_t = bar_chart(t_item, "s", lambda v: "%.2f s" % v, "单页耗时中位（秒）")
svg_m = bar_chart(m_item, "MB", lambda v: "%.0f MB" % v, "内存峰值中位（MB）")

print("=== 耗时图（升序）===")
for n, v in sorted(t_item, key=lambda x: x[1]):
    print("  %-12s %8.2f s" % (n, v))
print("\n=== 内存图（升序）===")
for n, v in sorted(m_item, key=lambda x: x[1]):
    print("  %-12s %8.0f MB" % (n, v))

pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_charts.json").write_text(
    json.dumps({"time": svg_t, "mem": svg_m}, ensure_ascii=False), encoding="utf-8")
print("\n已存 _charts.json")
