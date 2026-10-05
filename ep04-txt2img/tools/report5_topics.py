#!/usr/bin/env python
"""ep04 题材扩样报告:4 题材 × 3 方案 → 浅色自适应 HTML(图内嵌 base64,可离线打开)。"""
import base64
import json
import os
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
PROG = os.path.join(E, "logs", "bench5-topics.json")
OUTDIR = r"D:/models/txt2img/out4"
DST = r"C:/Users/Frank/AppData/Local/hermes/workspace/reports/ep04-topics.html"

TOPIC_CN = {"dogcat": "狗与猫", "car": "汽车", "clothes": "衣服", "bicycle": "自行车"}
SCHEMES = ["sdcpp-cpu", "sdcpp-vulkan", "diffusers"]
SCHEME_CN = {
    "sdcpp-cpu": "sd.cpp · 纯 CPU",
    "sdcpp-vulkan": "sd.cpp · 核显",
    "diffusers": "diffusers · 纯 CPU",
}
ORDER_TOPIC = ["dogcat", "car", "clothes", "bicycle"]

rows = json.load(open(PROG, encoding="utf-8"))["rows"]
ok_rows = [r for r in rows if r.get("ok")]
print(f"rows={len(rows)} ok={len(ok_rows)}")


def b64(cell):
    p = os.path.join(OUTDIR, cell + ".png")
    if not os.path.exists(p):
        return None
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()


# ---- 汇总 ----
agg = {}
for r in ok_rows:
    a = agg.setdefault(r["scheme"], {"t": [], "m": [], "n": 0})
    a["n"] += 1
    a["t"].append(r["seconds"])
    if r.get("mem_peak"):
        a["m"].append(r["mem_peak"])

by = {(r["scheme"], r["topic"]): r for r in rows}

table_rows = []
for s in SCHEMES:
    a = agg.get(s)
    if not a:
        continue
    table_rows.append(
        f"<tr><td>{SCHEME_CN[s]}</td>"
        f"<td class='num'>{min(a['t']):.1f}–{max(a['t']):.1f}</td>"
        f"<td class='num'>{statistics.mean(a['t']):.1f}</td>"
        f"<td class='num'>{max(a['m']) / 1048576:.0f} MB</td>"
        f"<td class='num'>{a['n']}/4</td></tr>")

grid = []
for t in ORDER_TOPIC:
    cells = []
    for s in SCHEMES:
        r = by.get((s, t))
        if r and r.get("ok"):
            img = b64(r["cell"])
            cells.append(
                f"<figure><img src='{img}' alt='{TOPIC_CN[t]} · {SCHEME_CN[s]}' loading='lazy'>"
                f"<figcaption>{SCHEME_CN[s]} · {r['seconds']:.1f} 秒 · "
                f"{r['mem_peak'] // 1048576 if r.get('mem_peak') else '?'} MB</figcaption></figure>")
        else:
            cells.append(f"<figure class='miss'><div class='box'>未出图</div>"
                         f"<figcaption>{SCHEME_CN[s]} · "
                         f"{(r or {}).get('err', '缺记录')[:60]}</figcaption></figure>")
    grid.append(f"<section class='topic'><h2>{TOPIC_CN[t]}</h2>"
                f"<div class='row'>{''.join(cells)}</div></section>")

fails = [r for r in rows if not r.get("ok")]
fail_html = ""
if fails:
    items = "".join(f"<li><code>{r['cell']}</code> — {r.get('err','')[:120]}</li>" for r in fails)
    fail_html = f"<h2>未出图</h2><ul class='fail'>{items}</ul>"

mean_cpu = statistics.mean([r["seconds"] for r in ok_rows if r["scheme"] == "sdcpp-cpu"])
mean_vk = statistics.mean([r["seconds"] for r in ok_rows if r["scheme"] == "sdcpp-vulkan"])
mean_df = statistics.mean([r["seconds"] for r in ok_rows if r["scheme"] == "diffusers"])

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>题材扩样实测 · 4 题材 × 3 方案</title>
<style>
:root{{--ink:#22262d;--dim:#7a828c;--line:#e3e7ec;--bg:#f7f8fa;--blue:#0f4c81;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.65;
 -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:40px 20px 72px}}
header{{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:26px}}
h1{{font-size:25px;margin:0 0 8px;letter-spacing:.2px}}
.meta{{color:var(--dim);font-size:13.5px}}
.meta b{{color:var(--ink);font-weight:600}}
h2{{font-size:17px;margin:34px 0 14px;padding-left:10px;border-left:3px solid var(--blue)}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:14.5px;
 border:1px solid var(--line)}}
th,td{{padding:11px 13px;border-bottom:1px solid var(--line);text-align:left}}
th{{background:#fbfcfd;font-weight:600;font-size:13.5px;color:var(--dim);
 border-bottom:2px solid var(--line)}}
td.num,.num{{font-variant-numeric:tabular-nums;font-family:Consolas,monospace}}
tr:last-child td{{border-bottom:none}}
.topic{{margin-bottom:30px}}
.topic h2{{margin-top:0}}
.row{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
figure{{margin:0;background:#fff;border:1px solid var(--line);padding:8px}}
figure img{{width:100%;display:block;aspect-ratio:1/1;object-fit:cover;background:#eef0f3}}
figcaption{{font-size:12.5px;color:var(--dim);padding-top:7px;
 font-variant-numeric:tabular-nums}}
.miss .box{{aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
 background:#eef0f3;color:var(--dim);font-size:14px}}
ul.fail{{background:#fff;border:1px solid var(--line);padding:14px 14px 14px 32px;
 font-size:13.5px;color:#8a3b3b}}
.note{{background:#fff;border:1px solid var(--line);padding:16px 18px;font-size:14px;
 color:var(--dim);margin-top:10px}}
.note b{{color:var(--ink)}}
code{{font-family:Consolas,monospace;font-size:12.5px}}
@media(max-width:720px){{.row{{grid-template-columns:1fr}}h1{{font-size:21px}}
 .wrap{{padding:26px 14px 56px}}}}
</style></head><body><div class="wrap">
<header>
<h1>题材扩样：狗猫 · 汽车 · 衣服 · 自行车</h1>
<div class="meta"><b>口径</b> 512×512 · 20 步 · seed 42 · 串行 · 出网 0 ｜
<b>方案</b> sd.cpp 核显 / sd.cpp 纯 CPU / diffusers 纯 CPU ｜
<b>出图</b> {len(ok_rows)}/{len(rows)}</div>
</header>

<h2>耗时与内存（4 题材各自 1 跑）</h2>
<table><thead><tr><th>方案</th><th>单张耗时（秒）</th><th>均值（秒）</th>
<th>峰值内存</th><th>出图</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table>
<div class="note">三方案均值：核显 <b>{mean_vk:.1f} 秒</b>、diffusers <b>{mean_df:.1f} 秒</b>、
纯 CPU <b>{mean_cpu:.1f} 秒</b> —— 核显 / 纯 CPU = <b>{mean_cpu / mean_vk:.2f}×</b>。
内存按进程名（sd-cli）求和、diffusers 取子进程 RSS 峰值；核显走统一内存，
进程 RSS 未必含显存侧占用，两列并列时须带此口径注。</div>

{''.join(grid)}
{fail_html}
<div class="note">每格固定 seed 42、同参数，图上时间即该次真实耗时；
原始日志在 <code>logs/raw-T_*.txt</code>，逐格记录在 <code>logs/bench5-topics.json</code>。</div>
</div></body></html>"""

os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, "w", encoding="utf-8").write(html)
print(f"saved -> {DST} {os.path.getsize(DST) // 1024} KB")
print(f"均值: vk {mean_vk:.1f} | diffusers {mean_df:.1f} | cpu {mean_cpu:.1f} | "
      f"cpu/vk {mean_cpu / mean_vk:.2f}x")
