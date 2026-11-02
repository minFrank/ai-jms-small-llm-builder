# -*- coding: utf-8 -*-
"""doocs_classic 主题本地预览：md -> 微信 HTML -> 图片改绝对路径 -> 手机宽截图。
正文不改动。"""
import os, sys, re, subprocess
from PIL import Image

REPO = r"D:/study/ai-jms/ai-radar-trend"
MD   = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/local-ai-12-local-ocr2.md"
OUT  = r"C:/Users/Frank/AppData/Local/hermes/workspace/_themes"
ROOT = r"C:/Users/Frank/AppData/Local/hermes/workspace/"
EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, REPO + "/content-admin")
from app.services.render import md_to_html, to_wechat

text = open(MD, encoding="utf-8").read()
parts = text.split("---", 2)
body = parts[2]

html = to_wechat(md_to_html(body), theme="doocs_classic")

# 相对 assets/ 路径 -> 绝对 file:///
def to_abs(m):
    rel = m.group(1).replace("\\", "/")
    return 'src="file:///' + ROOT.replace("\\", "/") + rel + '"'

html2 = re.sub(r'src="(?!file:///)(?!https?)(?!data:)([^"]+)"', to_abs, html)

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>doocs_classic 预览</title>
<style>
body{margin:0;background:#f0f1f3;font-family:"Microsoft YaHei",sans-serif}
.bar{position:sticky;top:0;background:#fff;border-bottom:1px solid #e3e5e8;
     padding:14px 18px;font-size:15px;font-weight:700;color:#1a1d21;z-index:9}
.bar span{font-weight:400;color:#8a919b;font-size:12px;margin-left:10px}
.wrap{max-width:480px;margin:0 auto;background:#fff;min-height:100vh}
</style></head><body>
<div class="bar">主题：doocs_classic <span>正文未改动 · 图片已指向本地文件</span></div>
<div class="wrap">""" + html2 + "</div></body></html>"

page = os.path.join(OUT, "preview-doocs_classic.html")
open(page, "w", encoding="utf-8").write(PAGE)

shot = os.path.join(OUT, "preview-doocs_classic.png")
subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--window-size=520,3000",
                "--screenshot=" + shot, "file:///" + page.replace("\\", "/")],
               capture_output=True)

n_img = len(re.findall(r"<img", html2))
n_abs = len(re.findall(r'src="file:///', html2))
print("img %d 个，绝对路径 %d 个，残留相对路径 %d" % (n_img, n_abs, len(re.findall(r'src="(?!file:///)(?!https?)(?!data:)[^"]+"', html2))))
print("preview:", page)
if os.path.exists(shot):
    im = Image.open(shot); print("shot:", im.size, os.path.getsize(shot)//1024, "KB")
