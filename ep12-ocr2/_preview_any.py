# -*- coding: utf-8 -*-
"""参数化微信预览：python _preview_any.py <md路径> <theme>
输出 _themes/preview-<theme>.html + 手机宽截图。正文不改动。"""
import os, sys, re, subprocess, time
from PIL import Image

REPO = r"D:/study/ai-jms/ai-radar-trend"
OUT = r"C:/Users/Frank/AppData/Local/hermes/workspace/_themes"
ROOT = r"C:/Users/Frank/AppData/Local/hermes/workspace/"
EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
os.makedirs(OUT, exist_ok=True)

MD = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/local-ai-04-txt2img.md"
THEME = sys.argv[2] if len(sys.argv) > 2 else "doocs_simple"

sys.path.insert(0, REPO + "/content-admin")
from app.services.render import md_to_html, to_wechat

text = open(MD, encoding="utf-8").read()
parts = text.split("---", 2)
body = parts[2] if len(parts) >= 3 else text

html = to_wechat(md_to_html(body), theme=THEME)


def to_abs(m):
    rel = m.group(1).replace("\\", "/")
    return 'src="file:///' + ROOT.replace("\\", "/") + rel + '"'


html2 = re.sub(r'src="(?!file:///)(?!https?)(?!data:)([^"]+)"', to_abs, html)

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s 预览</title>
<style>
body{margin:0;background:#f0f1f3;font-family:"Microsoft YaHei",sans-serif}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #e3e5e8;
     padding:14px 18px;font-size:15px;font-weight:700;color:#1a1d21;z-index:9}
.bar span{font-weight:400;font-size:12px;color:#8a919b;margin-left:10px}
.wrap{max-width:480px;margin:0 auto;background:#fff;min-height:100vh}
</style></head><body>
<div class="bar">主题：%s <span>正文未改动 · 图片已指向本地文件 · %s</span></div>
<div class="wrap">%s</div></body></html>""" % (THEME, THEME, time.strftime("%H:%M:%S"), html2)

page = os.path.join(OUT, "preview-%s.html" % THEME)
open(page, "w", encoding="utf-8").write(PAGE)

shot = os.path.join(OUT, "shot-%s.png" % THEME)
subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars",
                "--window-size=480,3000", "--screenshot=" + shot,
                "--virtual-time-budget=8000", "file:///" + page],
               capture_output=True, timeout=180)
if os.path.exists(shot):
    im = Image.open(shot)
    im.thumbnail((480, 3000))
    im.save(shot)

print("img %d 个" % len(re.findall(r"<img", html2)))
print("preview: %s (%.1f KB)" % (page, os.path.getsize(page) / 1024))
if os.path.exists(shot):
    print("shot: %s %s %.0f KB" % (shot, Image.open(shot).size, os.path.getsize(shot) / 1024))
