# -*- coding: utf-8 -*-
"""把 26 张样本原样拷到 assets（1:1，不缩放不重采样）。"""
import os, shutil
E11 = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples"
E12 = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/output/samples"
DST = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/local-ai-ep12-samples"
os.makedirs(DST, exist_ok=True)

# 清掉旧的缩略版
for f in os.listdir(DST):
    os.remove(os.path.join(DST, f))

names = sorted(f for f in os.listdir(E11) if f.endswith(".png")) + \
        sorted(f for f in os.listdir(E12) if f.endswith(".png"))
tot = 0
for fn in names:
    src = os.path.join(E12, fn) if os.path.exists(os.path.join(E12, fn)) else os.path.join(E11, fn)
    dst = os.path.join(DST, "ep12-sample-" + fn)
    shutil.copy2(src, dst)          # 原样拷贝，字节级相同
    tot += os.path.getsize(dst)

# 校验：字节是否与源一致
bad = []
for fn in names:
    src = os.path.join(E12, fn) if os.path.exists(os.path.join(E12, fn)) else os.path.join(E11, fn)
    a = open(src, "rb").read(); b = open(os.path.join(DST, "ep12-sample-" + fn), "rb").read()
    if a != b: bad.append(fn)

print("拷贝 %d 张，合计 %.2f MB" % (len(names), tot/1e6))
print("字节级比对不一致:", bad if bad else "0 张（全部与源相同）")
