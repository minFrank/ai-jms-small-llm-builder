# -*- coding: utf-8 -*-
"""最后一步：把报告正文里出现的每个数字都抽出来，与"已核对清单"比对，
找出任何未被覆盖的数字。"""
import re, pathlib, json

RPT = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html"
BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"

t = re.sub(r'src="data:image/png;base64,[^"]+"', ' ', pathlib.Path(RPT).read_text(encoding="utf-8"))
txt = re.sub(r'<[^>]+>', ' ', t)
txt = re.sub(r'\s+', ' ', txt)

# 已核对的数字（穷举三部分覆盖的）
COVERED = set()
V = json.loads(pathlib.Path(BASE+"/_verify1.json").read_text(encoding="utf-8"))
for k, d in V.items():
    for v in [d["med"], d["mean"], d["p90"], d["t"], d["rss"]]:
        COVERED.update({"%.4f"%v, "%.2f"%v, "%.0f"%v, "%.3f"%v, "%.1f"%v})
    COVERED.add("%d/24" % d["perfect"])
# 推导值
for v in ["8.3","7.6","8.0","4.13","53","3.2","24.6","1.97","2.0","54","9.8","4",
          "19.8","81.6","2.56","2.81","3.6","31","39","40","10.4","20.3","12.5",
          "11.1","0.0","13.44","10.52","10.69","8.77","4.63","4.64","7.18",
          "0.0137","0.1922","27.85","2204","0.4286","189.97","4858","1.91","0.0383",
          "1.02","2.66","156","26","24","9","6","7","8","5","3","2","1","10","12","13"]:
    COVERED.add(v)
# 常量
for v in ["4096","4100","4089","3790","18708","0.6","1.5","0.3","0.9905","0.033",
          "66.7","30.3","2.0","131","256","0.51","135.45","23","2461","2480","19",
          "0.9923","0.9650","3.3497","0.5167","0.0263","0.0242","0.0250","0.0246",
          "0.0125","0.0656","0.2102","0.2136","0.2221","0.2222","0.1896","0.2171",
          "0.2123","0.3488","97","120","6","20","104","110","0.648","1.03","0.024",
          "0.014","0.646","2.67","52.68","26.77","1562","3361","686","323","754",
          "745","1928","1529","0.65","22.19","4.74","2.93","2.77","0.12","2411",
          "2428","2423","91","2640","234","1.10","1.04","1.57","1.07","1.09"]:
    COVERED.add(v)

# 抽取所有数字 token
nums = re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])', txt)
from collections import Counter
cnt = Counter(nums)

uncovered = []
for n, c in sorted(cnt.items(), key=lambda x: -x[1]):
    if n in COVERED: continue
    # 上下文
    for m in re.finditer(r'(?<![\w.])' + re.escape(n) + r'(?![\w.])', txt):
        ctx = txt[max(0, m.start()-70):m.start()+70]
        uncovered.append((n, c, ctx.strip()))
        break

print("=" * 88)
print("报告正文数字穷举扫描")
print("=" * 88)
print("  正文数字 token 总数(去重): %d" % len(cnt))
print("  已核对清单覆盖: %d" % len([n for n in cnt if n in COVERED]))
print("  未覆盖: %d" % len([n for n in cnt if n not in COVERED]))
print()
for n, c, ctx in uncovered[:40]:
    print("  %-10s ×%d  …%s…" % (n, c, ctx[:96]))
