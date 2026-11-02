
# -*- coding: utf-8 -*-
"""补核：§09 GLM-OCR 三段耗时 / §10①② / §01 KPI / §11§12 正文数字"""
import json, glob, os, re, pathlib, statistics
BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
V = json.load(open(BASE + "/_verify1.json", encoding="utf-8"))
t = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2/ep12-ocr-report.html").read_text(encoding="utf-8")
fails = []
def sec(n):
    a = t.find('<h2><span class="no">%s</span>' % n)
    b = t.find('<h2><span class="no">', a+10)
    return t[a:b if b > 0 else len(t)]
def rows_of(tbl):
    return [[re.sub(r'<[^>]+>', '', c).strip()
             for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            for tr in re.findall(r'<tr>(.*?)</tr>', tbl, re.S)]
def chk(tag, got, exp):
    ok = got == exp
    if not ok: fails.append((tag, got, exp))
    print("  %s %-24s %s%s" % ("✅" if ok else "❌", tag, got, "" if ok else ("  应为 "+str(exp))))

# ── §09 三段耗时（从 cell JSON 现算）──
print("="*74); print("§09 GLM-OCR 三段耗时"); print("="*74)
tot = {"pe":0.0, "ev":0.0, "ld":0.0}
for f in sorted(glob.glob(BASE + "/cells/glmocr__*.json")):
    c = json.load(open(f, encoding="utf-8"))
    if not c.get("median"): continue
    ex = c.get("extra") or {}
    tot["pe"] += ex.get("prompt_eval_duration_s") or 0
    tot["ev"] += ex.get("eval_duration_s") or 0
    tot["ld"] += ex.get("load_duration_s") or 0
s = sum(tot.values())
chk("§09 prefill 占比", "%.1f%%" % (tot["pe"]/s*100), "66.7%")
chk("§09 生成占比",   "%.1f%%" % (tot["ev"]/s*100), "30.3%")
chk("§09 装载占比",   "%.1f%%" % (tot["ld"]/s*100), "3.0%")

# 逐格表 4 行
tb = re.findall(r'<div class="tw"><table>.*?</table></div>', sec("09"), re.S)
for r in rows_of(tb[1])[1:]:
    img = r[0]
    f = BASE + "/cells/glmocr__%s.json" % img
    if not os.path.exists(f): continue
    c = json.load(open(f, encoding="utf-8")); ex = c.get("extra") or {}
    chk("§09 %s" % img, (r[1], r[2], r[3]),
        (str(ex.get("prompt_eval_count")), "%.2f s"%ex.get("prompt_eval_duration_s"),
         "%.2f s"%ex.get("eval_duration_s")))

# 线性相关 r 与斜率
pts = []
for f in sorted(glob.glob(BASE + "/cells/glmocr__*.json")):
    c = json.load(open(f, encoding="utf-8")); ex = c.get("extra") or {}
    if ex.get("prompt_eval_count") and ex.get("prompt_eval_duration_s"):
        pts.append((ex["prompt_eval_count"], ex["prompt_eval_duration_s"]))
xs=[a for a,_ in pts]; ys=[b for _,b in pts]
mx,my=statistics.mean(xs),statistics.mean(ys)
r_ = sum((a-mx)*(b-my) for a,b in pts)/((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5)
slope = sum((a-mx)*(b-my) for a,b in pts)/sum((a-mx)**2 for a in xs)
chk("§09 相关系数 r", "%.4f"%r_, "0.9905")
chk("§09 斜率 秒/token", "%.3f"%slope, "0.033")

# skew_01 极端例
c = json.load(open(BASE+"/cells/glmocr__skew_01.json", encoding="utf-8")); ex=c["extra"]
chk("§09 skew_01 prefill", "%.2f s"%ex["prompt_eval_duration_s"], "135.45 s")
chk("§09 skew_01 生成", "%.2f s"%ex["eval_duration_s"], "0.51 s")

print("\n"+"="*74); print("失败项: %d" % len(fails)); print("="*74)
for f in fails: print("  ", f)
