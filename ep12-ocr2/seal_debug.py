"""渲染印章四字的无遮挡对照图，用于判定是渲染错还是视觉读错。

布局照抄 make_seal 里的写法：两列，右列 seal_text[:2]，左列 seal_text[2:4]，
列内自上而下。中文公章阅读顺序 = 自右向左、列内自上而下。
"""
import os

from PIL import Image, ImageDraw, ImageFont

F_HEI = "C:/Windows/Fonts/simhei.ttf"
OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt/_seal_debug.png"

seal_text = "单位公章"
ss = 240
img = Image.new("RGB", (ss + 40, ss + 40), "white")
d = ImageDraw.Draw(img)
f_seal = ImageFont.truetype(F_HEI, 62)

# 与 make_seal 完全相同的坐标算法（原点平移到画布内）
sx, sy = 20, 20
d.ellipse([sx, sy, sx + ss, sy + ss], outline=(200, 30, 30), width=9)
for ci, col in enumerate([seal_text[:2], seal_text[2:4]]):
    for ri, ch in enumerate(col):
        cx = sx + ss - 92 - ci * 92
        cy = sy + 60 + ri * 96
        d.text((cx, cy), ch, font=f_seal, fill=(200, 30, 30))

img.save(OUT)
print("已写:", OUT)

# 同时把每个字的落点打出来，方便对照
print("\n坐标对照（cx=字符左缘, cy=字符顶）:")
for ci, col in enumerate([seal_text[:2], seal_text[2:4]]):
    for ri, ch in enumerate(col):
        cx = sx + ss - 92 - ci * 92
        cy = sy + 60 + ri * 96
        where = "右列" if ci == 0 else "左列"
        pos = "上" if ri == 0 else "下"
        print("  %r  %s%s  cx=%d cy=%d" % (ch, where, pos, cx, cy))

print("\n阅读顺序（公章规范：自右向左，列内自上而下）:")
order = []
for ci in range(2):
    for ri in range(2):
        order.append(seal_text[ci * 2 + ri])
print("  →", "".join(order))
print("  GT 里的 seal_text =", seal_text)
print("  一致:", "".join(order) == seal_text)
