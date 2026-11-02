# -*- coding: utf-8 -*-
"""同一份 md 用 6 套主题各渲染一遍，出手机宽度预览页 + 截图。正文不改动。"""
import os, sys, re, subprocess, pathlib
from PIL import Image

REPO = r"D:/study/ai-jms/ai-radar-trend"
MD   = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/local-ai-12-local-ocr2.md"
OUT  = r"C:/Users/Frank/AppData/Local/hermes/workspace/_themes"
os.makedirs(OUT, exist_ok=True)
EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

THEMES = ["light", "warm", "mono", "doocs_classic", "doocs_grace", "doocs_simple"]

src = open(REPO + "/content-admin/app/services/render.py", encoding="utf-8", errors="replace").read()
print("render.py 存在，主题定义里出现的键：")
for m in re.finditer(r'"(\w+)":\s*\{', src):
    pass
th = re.findall(r'^\s{4}(\w+):\s*\{', src, re.M)
print("  ", sorted(set(th)) or "(未按此模式匹配，实际可用主题以 publish --help 为准)")

text = open(MD, encoding="utf-8").read()
parts = text.split("---", 2)
fm, body = parts[1], parts[2]
title = re.search(r"^title:\s*(.+)$", fm, re.M).group(1).strip()

sys.path.insert(0, REPO + "/content-admin")
from app.services.render import md_to_html, to_wechat  # noqa

WIDGET = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<style>
body{margin:0;background:#f0f1f3;font-family:"Microsoft YaHei",sans-serif}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #e3e5e8;
     padding:14px 18px;font-size:15px;font-weight:700;color:#1a1d21;z-index:9}
.bar span{font-weight:400;color:#8a919b;font-size:12px;margin-left:10px}
.wrap{max-width:480px;margin:0 auto;background:#fff;min-height:100vh;padding:0 0 40px}
</style></head><body>
<div class="bar">主题：%s <span>local-ai 第 12 期 · 正文未改动</span></div>
<div class="wrap">%s</div>
</body></html>"""

made = []
for th in THEMES:
    html = to_wechat(md_to_html(body), theme=th)
    page = WIDGET % (th, th, html)
    p = os.path.join(OUT, "theme-%s.html" % th)
    open(p, "w", encoding="utf-8").write(page)
    shot = os.path.join(OUT, "theme-%s.png" % th)
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--window-size=520,2400",
                    "--screenshot=" + shot, "file:///" + p.replace("\\", "/")],
                   capture_output=True)
    if os.path.exists(shot):
        im = Image.open(shot)
        made.append((th, os.path.getsize(shot)//1024, im.size))
        print("  ✓ %-14s %6d KB  %s" % (th, os.path.getsize(shot)//1024, im.size))
    else:
        print("  ✗ %-14s 截图失败" % th)

print("\n预览页目录:", OUT)
print("标题:", title[:70])
