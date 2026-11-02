# -*- coding: utf-8 -*-
"""词级指标（ICDAR / NIST 协议）+ 交叉验证。
口径与总榜一致：逐图计算 → 取上中位 v[n//2]；聚合 24 张（剔 book_02/skew_02）。
归一化（与报告一致）：NFKC -> 滤 Unicode P 类留 S 类 -> 小写 -> 去空白。
"""
import json, os, re, pathlib, unicodedata

CELLS = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/cells")
GTDIRS = [pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/gt"),
          pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/gt")]
EXCLUDE = {"book_02", "skew_02"}
ENGS = [("RCL small","rapidocrlite-small"), ("RCL medium","rapidocrlite-medium"),
        ("Simd 默认","simdpaddleocr-default"), ("Simd 受控","simdpaddleocr"),
        ("EasyOCR","easyocr"), ("Paddle官方","paddleocr"),
        ("LightOn剥标","lightonocr"), ("GLM-OCR","glmocr")]
KNOWN = {"RCL small":0.0242, "RCL medium":0.0250, "Simd 默认":0.0250,
         "Simd 受控":0.0246, "EasyOCR":0.0656, "Paddle官方":0.0137,
         "LightOn剥标":0.0263, "GLM-OCR":0.0000}

def find_gt(img):
    for d in GTDIRS:
        p = d / (img + ".txt")
        if p.exists(): return p
    return None

def upper_median(v):
    v = sorted(v)
    return v[len(v)//2]          # 与报告一致：偶数取上中位

def norm_cer(s):                 # 报告口径
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "P")
    return re.sub(r"\s+", "", s.lower())

def lev(a, b):
    n, m = len(a), len(b); prev = list(range(m+1))
    for i in range(1, n+1):
        cur = [i] + [0]*m
        for j in range(1, m+1):
            cur[j] = min(prev[j]+1, cur[j-1]+1, prev[j-1] + (0 if a[i-1]==b[j-1] else 1))
        prev = cur
    return prev[m]

def multiset_diff(a, b):
    """报告对竖排两图的特例口径：字符多重集差，顺序无关（ICDAR 协议无此规则）。"""
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    return sum(abs(ca[k] - cb[k]) for k in set(ca) | set(cb))

VERT = {"vert_01", "vert_02"}
COORD_M = re.compile(r"!\[[^\]]*\]\([^)]*\)")
TAG_M   = re.compile(r"</?[a-zA-Z][^>]*>")
def strip_markup(s):
    """与 _exhaustive.py 完全一致：剥坐标（markdown 图片语法）与 HTML 标签。"""
    return re.sub(r"\s+", " ", TAG_M.sub(" ", COORD_M.sub(" ", s)))

def word_align(gt_words, hyp_words):
    """词级对齐，返回 (距离, 完全匹配数)"""
    n, m = len(gt_words), len(hyp_words)
    dp = [[0]*(m+1) for _ in range(n+1)]
    bk = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0] = i
    for j in range(m+1): dp[0][j] = j
    for i in range(1, n+1):
        for j in range(1, m+1):
            c = 0 if gt_words[i-1] == hyp_words[j-1] else 1
            opts = [(dp[i-1][j]+1,1), (dp[i-1][j-1]+c,2), (dp[i][j-1]+1,3)]
            dp[i][j], bk[i][j] = min(opts, key=lambda x:x[0])
    i, j, match = n, m, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and bk[i][j] == 2:
            if gt_words[i-1] == hyp_words[j-1]: match += 1
            i, j = i-1, j-1
        elif i > 0 and (j == 0 or bk[i][j] == 1):
            i -= 1
        else:
            j -= 1
    return dp[n][m], match

def collect(pref):
    cer, line_er, line_acc = [], [], []
    for f in sorted(CELLS.glob(pref + "__*.json")):
        img = f.stem.split("__", 1)[1]
        if img in EXCLUDE: continue
        gt_p = find_gt(img)
        if gt_p is None: continue
        try: d = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        gt, hyp = gt_p.read_text(encoding="utf-8"), (d.get("text") or "")
        if pref == "lightonocr":
            hyp = strip_markup(hyp)     # 总榜口径用剥标记后的文本
        a, b = norm_cer(gt), norm_cer(hyp)
        if a:
            # 竖排两图走报告的多重集特例，其余走编辑距离
            cer.append((multiset_diff(a, b) if img in VERT else lev(a, b)) / len(a))
        # 行级：中文无空格，ICDAR 的"词级"退化为行级，故按换行切分
        ga = [x.strip() for x in unicodedata.normalize("NFKC", gt).split("\n") if x.strip()]
        hb = [x.strip() for x in unicodedata.normalize("NFKC", hyp).split("\n") if x.strip()]
        if ga:
            if img in VERT:      # 同一特例，词序列顺序无关
                from collections import Counter as _C
                ca, cb = _C(ga), _C(hb)
                dist = sum(abs(ca[k]-cb[k]) for k in set(ca)|set(cb))
                mt = sum(min(ca[k], cb[k]) for k in set(ca)|set(cb))
            else:
                dist, mt = word_align(ga, hb)
            line_er.append(dist / len(ga))
            line_acc.append(mt / len(ga))
    return cer, line_er, line_acc

print("=== 交叉验证：逐图 CER 的上中位 vs 总榜 ===")
print("%-14s %6s %10s %10s %6s" % ("配置", "图数", "重算中位", "总榜", "判定"))
ok_all = True
res = {}
for name, pref in ENGS:
    cer, ler, lacc = collect(pref)
    if not cer: print("%-14s   0  (无数据)" % name); continue
    med = upper_median(cer); kn = KNOWN[name]
    ok = abs(med - kn) < 0.0015
    ok_all &= ok
    res[name] = (len(cer), upper_median(ler), upper_median(lacc))
    print("%-14s %6d %10.4f %10.4f %6s" % (name, len(cer), med, kn, "对上" if ok else "不符"))
print("\n交叉验证:", "全部对上 ✅" if ok_all else "有不符 ❌（不可引用）")

if ok_all:
    print("\n=== 词级指标（逐图上中位，24 张）===")
    print("%-14s %6s %12s %12s" % ("配置", "图数", "行级错误率", "行完全正确率"))
    print("-"*50)
    out = []
    for name, pref in ENGS:
        if name not in res: continue
        n, w, a = res[name]
        print("%-14s %6d %11.1f%% %11.1f%%" % (name, n, w*100, a*100))
        out.append({"name": name, "n_img": n,
                    "line_er_upper_median": round(w, 6),
                    "line_acc_upper_median": round(a, 6)})
    p = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/word_metrics.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n已写:", p)
