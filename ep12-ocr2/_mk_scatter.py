
# -*- coding: utf-8 -*-
"""重画 §04 准确率-速度散点图：8 配置（含 Rcl-small 与 LightOnOCR）。"""
import json, pathlib
V3 = json.loads(pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_agg_v3.json").read_text(encoding="utf-8"))

# LightOnOCR 用剥标记口径（raw 在 §12 说明）
ITEMS = [("Rcl-small", "rapidocrlite-small"),
         ("Rcl-med",   "rapidocrlite-medium"),
         ("Simd受控",   "simdpaddleocr"),
         ("Simd默认",   "simdpaddleocr-default"),
         ("EasyOCR",   "easyocr"),
         ("Paddle官方", "paddleocr"),
         ("LightOn",   "lightonocr-stripped"),
         ("GLM-OCR",   "glmocr")]

pts = [(n, V3[k]["t_med"], V3[k]["cer_med"]) for n, k in ITEMS]
xs = [p[1] for p in pts]; ys = [p[2] for p in pts]

W, H = 700, 320
L, R, T, B = 62, 26, 26, 48           # 边距
xmin, xmax = 0, max(xs) * 1.12
ymin, ymax = 0, max(ys) * 1.18

def sx(v): return L + (W - L - R) * (v - xmin) / (xmax - xmin)
def sy(v): return (H - B) - (H - B - T) * (v - ymin) / (ymax - ymin)

out = ['<svg viewBox="0 0 %d %d" class="chart" role="img"><title>准确率-速度散点图</title>' % (W, H)]
out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#d6dae0"/>' % (L, H-B, W-R, H-B))
out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#d6dae0"/>' % (L, T, L, H-B))
out.append('<text x="%d" y="%d" class="ax">单页耗时中位（秒）→</text>' % (W-R-160, H-14))
out.append('<text x="%d" y="%d" class="ax">CER 中位 ↑</text>' % (6, T+4))

# 标签避让：按 x 排序，纵向推开
placed = []
order = sorted(range(len(pts)), key=lambda i: pts[i][1])
for i in order:
    n, x, y = pts[i]
    px, py = sx(x), sy(y)
    ly = py + 4
    for _ in range(12):
        if all(abs(ly - qy) > 15 or abs(px - qx) > 78 for qx, qy in placed):
            break
        ly += 15
    placed.append((px, ly))
    if abs(ly - py) > 6:   # 有位移才画引线
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#b9bfc6" stroke-width="0.8"/>'
                   % (px, py, px + 6, ly - 4))
    out.append('<circle cx="%.1f" cy="%.1f" r="5.5" fill="#2f6fb2" opacity="0.88"/>' % (px, py))
    out.append('<text x="%.1f" y="%.1f" class="dl">%s</text>' % (px + 8, ly, n))
out.append('</svg>')
svg = "".join(out)

pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_scatter.json").write_text(
    json.dumps({"svg": svg}, ensure_ascii=False), encoding="utf-8")

print("=== 散点坐标 ===")
print("%-12s %-10s %-10s %s" % ("名","耗时s","CER中位","位置"))
for n, x, y in sorted(pts, key=lambda p: p[1]):
    print("%-12s %-10.2f %-10.4f x=%.0f y=%.0f" % (n, x, y, sx(x), sy(y)))
print("\nsvg %d 字节" % len(svg))
