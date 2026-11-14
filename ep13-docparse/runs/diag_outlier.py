# -*- coding: utf-8 -*-
"""离群定性：monkey×lc_01（10.30 复读嫌疑）+ surya×shot_01（1.67 标签嫌疑）
用法: python diag_outlier.py <engine> <img_name>
输出: OUT_LEN / GT_LEN / CER / 标签计数 / head / tail / 是否复读(重复n-gram)
"""
import sys, os, json, subprocess, threading, queue, time, re, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
eng, img_name = sys.argv[1], sys.argv[2]
VENV = {"monkey_rec": "dots", "surya_2_5": "dots"}
py = os.path.join(BASE, "venvs", VENV[eng], "Scripts", "python.exe")
img = os.path.join(BASE, "samples", img_name)
gt = open(os.path.join(BASE, "gt", os.path.splitext(img_name)[0] + ".txt"), encoding="utf-8").read()

p = subprocess.Popen([py, os.path.join(BASE, "scripts", "worker.py")],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, encoding="utf-8", bufsize=1, cwd=BASE)
q, eq = queue.Queue(), queue.Queue()
threading.Thread(target=lambda: [q.put(l) for l in p.stdout], daemon=True).start()
threading.Thread(target=lambda: eq.put(p.stderr.read()), daemon=True).start()

def call(o, t):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
    return json.loads(q.get(timeout=t))

q.get(timeout=30)
call(dict(cmd="hello", id=1, engine=eng), 150)
ld = call(dict(cmd="load", id=2, engine=eng), 500)
print("load:", ld.get("ok"), str(ld.get("err", ""))[:150], flush=True)
if not ld.get("ok"):
    p.kill(); sys.exit(1)
t0 = time.time()
r = call(dict(cmd="infer", id=3, path=img, max_new=2048), 1200)
print("infer ok:", r.get("ok"), "| %.0fs" % (time.time() - t0))
if not r.get("ok"):
    print("err:", str(r.get("err"))[:400]); print("trace:", str(r.get("trace"))[-500:])
    p.kill(); sys.exit(1)
text = r.get("text") or ""
p.kill()

sys.path.insert(0, os.path.join(BASE, "scripts"))
from extract_text import extract
from cer import cer

parsed = extract(text)
# 标签统计（原输出，extract 前）
tags_pipe = len(re.findall(r"<\|[^|]*\|>", text))
tags_html = len(re.findall(r"</?[a-zA-Z][^>]*>", text))
# 复读检测：最频繁 8-gram 重复数
grams = collections.Counter("".join(text.split())[i:i+16] for i in range(0, max(0, len("".join(text.split()))-16), 8))
top = grams.most_common(3)
# 重复行
lines = [l for l in text.splitlines() if l.strip()]
dup_lines = [l for l, n in collections.Counter(lines).items() if n >= 3]

print("OUT_LEN=%d GT_LEN=%d" % (len(text), len(gt.strip())))
print("TAGS: <|..|>=%d html=%d" % (tags_pipe, tags_html))
print("CER_raw=%.4f CER_extract=%.4f" % (cer(gt, text), cer(gt, parsed)))
print("TOP16GRAM:", [(g[:16], n) for g, n in top])
print("重复≥3次行数:", len(dup_lines), "样例:", dup_lines[:3])
print("=== HEAD 300 ==="); print(text[:300])
print("=== TAIL 300 ==="); print(text[-300:])
