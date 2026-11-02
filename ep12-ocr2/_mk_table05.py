
# -*- coding: utf-8 -*-
"""重做 §05 逐样本 CER 表：8 配置 × 26 样本。"""
import json, pathlib
V3 = json.loads(pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_agg_v3.json").read_text(encoding="utf-8"))

COLS = [("Simd受控","simdpaddleocr"), ("Simd默认","simdpaddleocr-default"),
        ("Rcl-med","rapidocrlite-medium"), ("Rcl-small","rapidocrlite-small"),
        ("Paddle官方","paddleocr"), ("EasyOCR","easyocr"),
        ("LightOn","lightonocr-stripped"), ("GLM-OCR","glmocr")]

idx = {k: {r["img"]: r for r in V3[k]["rows"]} for _, k in COLS}
imgs = sorted(V3["glmocr"]["rows"], key=lambda r: r["img"])
EXCL_NOTE = {"book_02": "GT 不全", "skew_02": "GT 不全"}

def cell(img, key):
    r = idx[key].get(img)
    if r is None:
        return "<td class='num'>—</td>"
    c = r["cer"]
    if c is None:
        return "<td class='num'>—</td>"
    cls = "num"
    if c < 0.005: cls = "num b"          # 满分加粗
    elif c > 0.9: cls = "num dim"        # 接近全错淡显
    return "<td class='%s'>%.4f</td>" % (cls, c)

out = ['<div class="tw"><table><thead><tr><th>样本</th>']
for name, _ in COLS:
    out.append('<th class="num">%s</th>' % name)
out.append('</tr></thead><tbody>')

for r in imgs:
    img = r["img"]
    if img in EXCL_NOTE:
        out.append("<tr><td class='nm'>%s</td>" % img)
        out.append("<td class='num dim' colspan='%d'>已剔除 —— %s</td></tr>" % (len(COLS), EXCL_NOTE[img]))
        continue
    out.append("<tr><td class='nm'>%s</td>" % img)
    for _, key in COLS:
        out.append(cell(img, key))
    out.append("</tr>")

out.append("</tbody></table></div>")
html = "".join(out)
pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/_table05.json").write_text(
    json.dumps({"html": html}, ensure_ascii=False), encoding="utf-8")

print("行数 %d（含 2 行剔除说明）  列数 %d" % (len(imgs), len(COLS)))
print("html %d 字节" % len(html))
print("\n样例（book_01 行）:")
i = html.find("book_01")
print(" ", html[i:i+430])
