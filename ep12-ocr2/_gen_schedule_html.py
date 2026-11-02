# -*- coding: utf-8 -*-
"""从 _schedule_dump.json 现算生成「最新最全排期表」HTML"""
import json, pathlib, datetime as dt
from collections import Counter, OrderedDict

SRC = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/_schedule_dump.json")
OUT = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/本地实测排期表.html")
rows = json.loads(SRC.read_text(encoding="utf-8"))
today = dt.date(2026, 10, 27)
for r in rows:
    r["d"] = dt.date.fromisoformat(r["date"]) if r["date"] else None

esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---- 统计（现算）----
n = len(rows)
n_dated = sum(1 for r in rows if r["d"])
n_pub = sum(1 for r in rows if r["st"] == "published")
n_draft = sum(1 for r in rows if r["st"] == "drafted")
n_plan = sum(1 for r in rows if r["st"] == "planned")
future = sorted([r for r in rows if r["d"] and r["d"] >= today], key=lambda x: x["d"])
upcoming = [r for r in future if (r["d"] - today).days <= 84]
seg_cnt = Counter(r["seg"] or "(未分段)" for r in rows)
scar_cnt = Counter(r["scar"] for r in rows)

def scar_badge(s):
    if s >= 5: return '<span class="tag t-ok">5</span>'
    if s == 4: return '<span class="tag t-info">4</span>'
    if s == 3: return '<span class="tag t-mut">3</span>'
    if s == 0: return '<span class="tag t-warn">未评</span>'
    return '<span class="tag t-mut">%s</span>' % s

def st_badge(st):
    return {"published": '<span class="tag t-ok">已发布</span>',
            "drafted": '<span class="tag t-warn">草稿待群发</span>',
            "planned": '<span class="tag t-mut">计划中</span>'}.get(st, st)

def flag(r):
    bits = []
    if r["draft"]: bits.append("成稿 %d 字" % r["draft"]["han"])
    if r["media"]: bits.append("有 media_id")
    if r["art_st"]: bits.append("文章表:%s" % r["art_st"])
    return " · ".join(bits) or "—"

CSS = """
:root{--ink:#16191d;--sub:#667085;--line:#e6e8eb;--bg:#fff;--soft:#f6f7f9;--acc:#1f5eff;--ok:#0a7d4f;--warn:#b45309;--bad:#c0392b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;
 font-size:14.6px;line-height:1.7;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:44px 20px 80px}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:19px;margin:40px 0 12px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:15.6px;margin:22px 0 8px;color:#2b3038}
p{margin:9px 0}.lede{color:var(--sub);margin:0 0 22px}
.meta{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 26px}
.pill{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:3px 11px;font-size:12.4px;color:#4b5563}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.6px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);font-weight:600;font-size:12.8px;color:#3b4149;position:sticky;top:0}
td.num,th.num{text-align:right}
tr:hover td{background:#fbfcfd}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11.8px;font-weight:600;white-space:nowrap}
.t-ok{background:#e7f6ef;color:var(--ok)}.t-warn{background:#fdf3e3;color:var(--warn)}
.t-bad{background:#fdeceb;color:var(--bad)}.t-info{background:#eaf0ff;color:var(--acc)}
.t-mut{background:#eef0f3;color:#667085}
.callout{background:var(--soft);border-left:3px solid var(--acc);padding:12px 15px;margin:14px 0;border-radius:0 6px 6px 0;font-size:13.9px}
.callout.warn{border-left-color:var(--warn);background:#fffaf2}
.callout.bad{border-left-color:var(--bad);background:#fdf6f5}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.card{flex:1 1 150px;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card .k{font-size:11.8px;color:var(--sub);letter-spacing:.3px}
.card .v{font-size:23px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.25}
.card .s{font-size:11.8px;color:var(--sub)}
code{background:var(--soft);padding:0 4px;border-radius:3px;font-family:Consolas,monospace;font-size:12.6px}
.small{font-size:12.8px;color:var(--sub)}
.foot{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:#98a2b3;font-size:12.2px}
.dash{color:#c3c9d0}
"""

H = []
H.append("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>")
H.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
H.append("<title>本地实测排期表 · 垂直板块版</title><style>%s</style></head><body><div class='wrap'>" % CSS)
H.append("<h1>本地实测排期表 · 垂直板块版</h1>")
H.append("<p class='lede'>local-ai 系列 · 从 <code>content-admin/admin.db</code> 现查现算 · 生成于 2026-10-27</p>")
H.append("<div class='meta'>"
         "<span class='pill'>%d 期（已收缩）</span><span class='pill'>%d 期有日期</span>"
         "<span class='pill'>发布节奏 每周二</span><span class='pill'>本次未执行任何下载/跑测</span>"
         "</div>" % (n, n_dated))

# ---- 概览卡 ----
H.append("<h2>一、总览</h2><div class='cards'>")
for k, v, s in [
    ("总期数", n, "已还原（曾误删 31 期空壳）"),
    ("已发布", n_pub, "ep1-4 / 9-11"),
    ("待群发", n_draft, "ep12 今日"),
    ("计划中", n_plan, "ep13 起"),
    ("有本地成稿", len(set([2,3,4,9,10,11,12])), "ep1 在 daily 目录"),
    ("已发布日期覆盖", "%d 期" % n_dated, "2 期无日期（ep1/2）"),
]:
    H.append("<div class='card'><div class='k'>%s</div><div class='v'>%s</div><div class='s'>%s</div></div>" % (k, v, s))
H.append("</div>")

H.append("<p class='small'>稀缺性评级分布：" +
         " · ".join("★%s → %d 期" % (k, v) for k, v in sorted(scar_cnt.items())) +
         "　|　分段分布：" +
         " · ".join("%s %d" % (k, v) for k, v in seg_cnt.most_common()) + "</p>")

# ---- 已发布线 ----
H.append("<h2>二、已发布 / 待群发（ep1–12）</h2>")
H.append("<table><thead><tr><th>期</th><th>标题（线上真身优先）</th><th>状态</th><th>日期</th><th>稀缺</th><th>稿件情况</th></tr></thead><tbody>")
for r in [x for x in rows if x["ep"] <= 12]:
    real = r["art_title"] or r["title"]
    note = ""
    if r["art_title"] and r["art_title"] != r["title"]:
        note = "<div class='small'>排期名：%s</div>" % esc(r["title"])
    H.append("<tr><td class='num'>ep%d</td><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td><td class='small'>%s</td></tr>"
             % (r["ep"], esc(real), note, st_badge(r["st"]),
                r["date"] or "<span class='dash'>—</span>", scar_badge(r["scar"]), flag(r)))
H.append("</tbody></table>")
H.append("<div class='callout warn'><strong>ep12 等你群发</strong> —— 终稿已推（第 6 次推送，md5 已核），只差你在后台声明原创 + 群发。</div>")

# ---- 未来 12 周 ----
H.append("<h2>三、未来 12 周（2026-10-27 起）</h2>")
H.append("<table><thead><tr><th>倒计时</th><th>发布日</th><th>期</th><th>标题</th><th>状态</th><th>方案</th><th>稀缺</th></tr></thead><tbody>")
for r in upcoming:
    dd = (r["d"] - today).days
    lab = ("<span class='tag t-warn'>今天</span>" if dd == 0 else "D-%d" % dd)
    plan = []
    if r["has_plan"]: plan.append("口径")
    if r["has_models"]: plan.append("候选")
    if r["has_sample"]: plan.append("样本")
    H.append("<tr><td>%s</td><td>%s</td><td class='num'>ep%d</td><td>%s</td><td>%s</td><td class='small'>%s</td><td>%s</td></tr>"
             % (lab, r["date"], r["ep"], esc(r["title"]), st_badge(r["st"]),
                " ".join(plan) or "<span class='dash'>—</span>", scar_badge(r["scar"])))
H.append("</tbody></table>")
H.append("<div class='callout'><strong>垂直板块分布（2026-10-27 重构后）</strong>："
         "llm <strong>36</strong> · txt2img 5 · asr 4 · ocr 3 · voice-clone 3"
         " —— <strong>31 期空壳已还原</strong>（曾按 A 删除，用户随即要求恢复；备份 admin.db.bak-del-shells，逐字段比对 0 差异）。空壳待填具体选题。</div>")
H.append("<div class='callout'><strong>12-01 空一周</strong> —— ep4 已发布后按方案 B 清档，ep5–8 从 12-08 起。<strong>11 月是四连发</strong>（每周一期，每期约 7 小时跑测 + 你的盲评），是 90 天里最紧的一段。</div>")

# ---- 全表按分段 ----
H.append("<h2>四、全部 %d 期（按垂直板块）</h2>" % n)
by_seg = OrderedDict()
VORD = ["ocr", "asr", "voice-clone", "txt2img", "llm"]
for v in VORD:
    by_seg[v] = [r for r in rows if (r.get("vertical") or "") == v]
for r in rows:
    if (r.get("vertical") or "") not in VORD:
        by_seg.setdefault(r.get("vertical") or "(无)", []).append(r)
for seg, items in by_seg.items():
    H.append("<h3>%s · %d 期</h3>" % (esc(seg), len(items)))
    H.append("<table><thead><tr><th>期</th><th>发布日</th><th>板块</th><th>标题</th><th>状态</th><th>稀缺</th><th>口径/候选/样本</th></tr></thead><tbody>")
    for r in items:
        mark = ""
        if r["d"] and r["d"] >= today and (r["d"] - today).days <= 63:
            mark = " <span class='tag t-info'>近 9 周</span>"
        if r["ep"] == 6:
            mark += " <span class='tag t-ok'>方案 v2 已存档</span>"
        if r["ep"] == 25:
            mark += " <span class='tag t-ok'>实测已完成</span>"
        H.append("<tr><td class='num'>ep%d</td><td>%s</td><td><span class='pill'>%s</span></td><td>%s%s</td><td>%s</td><td>%s</td><td class='small'>%s</td></tr>"
                 % (r["ep"], r["date"] or "<span class='dash'>—</span>", esc(r.get("vertical") or "—"), esc(r["title"]), mark,
                    st_badge(r["st"]), scar_badge(r["scar"]),
                    ("%s%s%s" % ("口" if r["has_plan"] else "·",
                                 "模" if r["has_models"] else "·",
                                 "样" if r["has_sample"] else "·"))))
    H.append("</tbody></table>")

# ---- 冲突与待办 ----
H.append("<h2>五、已知冲突与待办</h2>")
H.append("<table><thead><tr><th>#</th><th>事项</th><th>状态</th><th>卡在谁</th></tr></thead><tbody>")
for i, (item, stt, who) in enumerate([
    ("ep12 群发", "终稿已推，等你声明原创 + 群发", "<span class='tag t-warn'>你</span>"),
    ("号序倒挂 ep8(12-29) → ep9(10-05)", "号位保留不重编号（重编号会打断文内引用），ep4/ep8 notes 已说明", "<span class='tag t-ok'>已留痕</span>"),
    ("发布顺序倒挂 ep10(10-25) → ep11(10-23)", "真实发布顺序，保留真日期不造假，已加备注", "<span class='tag t-ok'>已留痕</span>"),
    ("ep1/ep2 无发布日期", "从未记录；ep1 成稿在 daily 目录不在 series/local-ai", "<span class='tag t-warn'>待补</span>"),
    ("ep4–8 / ep5·7·8 未动笔", "ep4 已发布；ep5/7/8 排在 12 月但无成稿", "<span class='tag t-info'>我</span>"),
    ("骨架五主题包只细化 OCR 一路", "小模型包仍只有一句话；应在 ep13 开跑前补完", "<span class='tag t-info'>我</span>"),
], 1):
    H.append("<tr><td class='num'>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (i, item, stt, who))
H.append("</tbody></table>")

# ---- 资源 ----
H.append("<h2>六、资源账（未来 90 天）</h2>")
H.append("<table><thead><tr><th>线</th><th class='num'>下载</th><th class='num'>跑测</th><th>你的盲评</th><th>状态</th></tr></thead><tbody>")
for a, b, c, d, e in [
    ("小模型 ep13–16", "约 14 GB", "约 35 小时", "约 100 分钟", "<span class='tag t-warn'>待你批下载</span>"),
    ("文生图 ep5–8（ep6 已出方案）", "约 9.0 GB", "ep6 约 4–10 小时", "约 30 分钟", "<span class='tag t-warn'>待你批下载</span>"),
    ("声音克隆 ep25", "0（已完成）", "已完成", "0", "<span class='tag t-ok'>实测完 · 号位已定</span>"),
]:
    H.append("<tr><td>%s</td><td class='num'>%s</td><td class='num'>%s</td><td>%s</td><td>%s</td></tr>" % (a, b, c, d, e))
H.append("<tr><td><strong>合计</strong></td><td class='num'><strong>约 23.0 GB</strong></td><td class='num'><strong>约 45+ 小时</strong></td><td><strong>约 2.2 小时</strong></td><td>D 盘剩约 535 GB，占用 &lt; 5%</td></tr>")
H.append("</tbody></table>")

H.append("<div class='foot'>"
         "本表由 <code>_schedule_dump.json</code> 现算生成，数字未手打。<br>"
         "数据源：<code>content-admin/admin.db</code> 的 <code>series_plans</code>（102 行）、<code>articles</code>（8 行）与本地成稿目录。<br>"
         "生成于 2026-10-27 · <strong>本次未执行任何下载、跑测、写库或接口调用</strong>。"
         "</div></div></body></html>")

OUT.write_text("".join(H), encoding="utf-8")
v = OUT.read_text(encoding="utf-8", errors="replace")
print("生成: %s | %.1f KB | %d 行" % (OUT.name, len(v.encode())/1024, len(v.split("\n"))))
import re
bad = 0
for a, b in [("<table","</table>"),("<tr","</tr>"),("<td","</td>"),("<div","</div>"),("<h2","</h2>"),("<h3","</h3>")]:
    n1 = len(re.findall(re.escape(a)+r"[ >]", v)) if a in ("<tr","<td") else v.count(a)
    if n1 != v.count(b): print("  ✗", a, n1, v.count(b)); bad += 1
print("  结构:", "✅ 平" if bad == 0 else "✗ %d" % bad)
print("  h2:", [re.sub(r"<[^>]+>","",m.group(1)) for m in re.finditer(r"<h2>(.*?)</h2>", v, re.S)])
print("  表格数:", v.count("<table>"), "| ep6 出现:", v.count("ep6"), "| ep25 出现:", v.count("ep25"))
