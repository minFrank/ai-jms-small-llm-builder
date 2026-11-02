# -*- coding: utf-8 -*-
"""ep6 方案补 4 项（用户回「补」）：① LCM ② 中文文字渲染专项 ③ 题材分层 ④ ep5 分工 + 排期表 test_plan"""
import pathlib, re, sqlite3, time

# ================= A) ep6 跑测方案 =================
p = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep6-一步出图-跑测方案.html")
t = p.read_text(encoding="utf-8", errors="replace")
n = 0
def rep(t, old, new, tag):
    global n
    c = t.count(old)
    assert c == 1, "[%s] 命中 %d" % (tag, c)
    n += 1
    return t.replace(old, new)

# --- 1) 模型选型表加 LCM 行 ---
old = """<tr><td><strong>基线</strong></td><td><strong>SD 1.5</strong>（ep4 已有，4.27 GB）</td><td class="num">已下载</td><td class="num">20</td><td><span class="tag t-ok">已核</span></td></tr>"""
new = """<tr><td><strong>基线</strong></td><td><strong>SD 1.5</strong>（ep4 已有，4.27 GB）</td><td class="num">已下载</td><td class="num">20</td><td><span class="tag t-ok">已核</span></td></tr>
<tr><td><strong>主测 4</strong> <span class="tag t-info">2026-10-27 补</span></td>
<td><strong>LCM-LoRA</strong>（<strong>加在上面那个 SD 1.5 上</strong>）<br><span class="small">latent-consistency/lcm-lora-sdv1-5</span></td>
<td class="num"><strong>128.4 MB</strong></td><td class="num">4</td><td><span class="tag t-ok">openrail++</span></td></tr>"""
t = rep(t, old, new, "model-lcm-row")

# --- 2) 模型选型后补 LCM 说明 ---
old = """<h3>为什么用 OpenVINO 版</h3>"""
new = """<div class="callout"><strong>LCM 为什么这么加（控制变量最干净的一档）：</strong><br>
① 它是 <strong>LoRA 不是新模型</strong> —— <strong>加在 ep4 已经跑过的那个 SD 1.5 上</strong>，基座、字典、VAE 全不变，<strong>唯一变量是「加不加 LCM-LoRA」</strong>；<br>
② <strong>128.4 MB、openrail++ 可商用、12.9 万下载</strong> —— 成本几乎为零，但补上了排期表标题承诺的 <code>SD-Turbo/LCM</code> 里那个 <strong>LCM</strong>（v1 方案漏了，本次补齐）；<br>
③ 有 <strong>同作者 OpenVINO 版</strong>（<code>rupeshs/sd15-lcm-square-openvino-int8</code>，与 FastSD 同一作者），可与 SDXS 同路线对照；<br>
④ 与 SD-Turbo / SDXL-Turbo 形成 <strong>两条加速路线的对照</strong>：蒸馏（ADD，改权重）vs 一致性（LCM，加 LoRA）。</div>

<h3>为什么用 OpenVINO 版</h3>"""
t = rep(t, old, new, "lcm-rationale")

# --- 3) §五 加题材分层 + 中文专项（插在 §B2 之前）---
old = """<h3>§B2 样本量（按骨架反推，不拍脑袋）</h3>"""
new = """<h3>§B0 题库设计：五类题材分层 + 中文专项 <span class="tag t-info">2026-10-27 补</span></h3>

<p><strong>25 题按五类题材分层，每类 5 题</strong> —— 沿用 <strong>ep4 的五类与提示词原文</strong>（跨期可比），另加中文专项：</p>

<table><thead><tr><th>#</th><th>题材</th><th>ep4 提示词原文（照抄，不改）</th><th>ep4 当时的判定</th><th>ep6 要看什么</th></tr></thead><tbody>
<tr><td>1</td><td>老人肖像</td><td><code>portrait of an elderly fisherman with wrinkled face</code></td><td>✅ 干净</td><td>1 步下皱纹/皮肤质感还剩多少</td></tr>
<tr><td>2</td><td>人群街市</td><td><code>a busy street market with many people</code></td><td>✅ 干净（无人肢体错乱）</td><td>人多时 1 步是否肢体错乱</td></tr>
<tr><td>3</td><td>动漫人物</td><td><code>anime girl with blue hair</code></td><td>✅ 五官比例正常</td><td>五官是否崩</td></tr>
<tr><td>4</td><td>微距水珠</td><td><code>macro photo of a dew drop on a green leaf</code></td><td>可用但偏糊</td><td>1 步是否更糊</td></tr>
<tr><td>5</td><td><strong>图表</strong></td><td><code>a simple bar chart on white background, three blue bars</code></td><td><span class="tag t-warn">柱子对、字乱码</span></td><td><strong>1 步会不会更糟</strong></td></tr>
<tr><td>6–10</td><td><strong>中文写字专项</strong></td><td>白牌子 / 横幅 / 招牌三类场景，含 <code>「你好世界」</code>、<code>「AI 积木师」</code>等中文短语</td><td><span class="tag t-warn">ep4：20 步出的是假汉字</span></td><td><strong>1 步 vs 4 步(LCM) vs 20 步，中文能不能写真</strong></td></tr>
</tbody></table>

<p class="small"><strong>判定沿用 ep4 的三样，不另立标准</strong>：肢体有没有错乱、五官比例正不正常、<strong>字是不是假的</strong>。题材提示词<strong>逐字沿用 ep4</strong>，这样两期数字可直接对表。</p>

<div class="callout"><strong>中文专项为什么必须有：</strong>ep4 的「三个做不到」第一条就是<strong>图里写中文出来是假汉字</strong>（白牌子与图表两处）。<strong>步数从 20 降到 1，细节只会更少，几乎必然更差</strong> —— 这是本测最可能出结论的地方，也是<strong>第三方只报速度、不报画质</strong>留下的空档。</div>

<h3>§B2 样本量（按骨架反推，不拍脑袋）</h3>"""
t = rep(t, old, new, "topic-layering")

# --- 4) §B1 口径补题材/中文 ---
old = """<li><strong>范围</strong>：本机 5700G + 上述三模型，<strong>不外推到其它 CPU 或有显卡机器</strong></li>"""
new = """<li><strong>范围</strong>：本机 5700G + 上述四模型（含 LCM），<strong>不外推到其它 CPU 或有显卡机器</strong></li>
<li><strong>题材与中文专项</strong>：五类题材 + 中文写字专项<strong>各配置都跑</strong>，不只跑通用题；判定沿用 ep4 三样</li>"""
t = rep(t, old, new, "scope-lcm")

# --- 5) 跑量表加 LCM 档 ---
old = """<tr><td>sd.cpp / diffusers 对照档（1 步模型）</td><td class="num">150</td><td class="num">约 5–30 s</td><td class="num">约 13–75 分</td></tr>"""
new = """<tr><td><strong>LCM-LoRA 4 步 · SD1.5 · 512² · 25 题 × 3 次</strong></td><td class="num">75</td><td class="num">约 40–90 s<br><span class="small">同基座 20 步是 94–265 s</span></td><td class="num"><strong>约 0.8–1.9 小时</strong></td></tr>
<tr><td><strong>中文专项（1/4/20 步三档 × 10 题 × 3 次）</strong></td><td class="num">90</td><td class="num">—</td><td class="num">并入上表</td></tr>
<tr><td>sd.cpp / diffusers 对照档（1 步模型）</td><td class="num">150</td><td class="num">约 5–30 s</td><td class="num">约 13–75 分</td></tr>"""
t = rep(t, old, new, "run-lcm")

t = t.replace("<strong>约 540 次出图</strong>", "<strong>约 705 次出图</strong>")
t = t.replace("<td class=\"num\"><strong>约 3–8 小时</strong></td>", "<td class=\"num\"><strong>约 4–10 小时</strong></td>")

# --- 6) 排除项表补 ep5 分工 ---
old = """<tr><td><strong>OpenVINO 之外的加速库</strong></td>"""
new = """<tr><td><strong>量化位数</strong>（Q8 / Q6 / Q4…）</td><td><strong>归 ep5「同模型量到 4 位」</strong>（2026-12-08）。<strong>两期分工</strong>：ep5 只动<strong>位宽</strong>、步数固定；ep6 只动<strong>步数</strong>、位宽固定 —— <strong>同一期不同时动两个变量</strong></td></tr>
<tr><td><strong>OpenVINO 之外的加速库</strong></td>"""
t = rep(t, old, new, "ep5-split")

# --- 7) 新增一节讲分工（放在第七节后）---
old = """<h2>八、文章重设计（吸收 ep4 阅读量的四条教训）</h2>"""
new = """<h2>七之二、与 ep5 的分工（避免测重）<span class="tag t-info">2026-10-27 补</span></h2>

<table><thead><tr><th></th><th>ep5 量化档（2026-12-08）</th><th>ep6 一步出图（2026-12-15）</th></tr></thead><tbody>
<tr><td><strong>动什么</strong></td><td><strong>位宽</strong>（8 / 6 / 4 位）</td><td><strong>步数</strong>（1 / 4 / 20 步）</td></tr>
<tr><td><strong>固定什么</strong></td><td>步数固定、模型固定</td><td>位宽固定、模型固定</td></tr>
<tr><td><strong>回答什么</strong></td><td>量化掉多少画质、省多少内存</td><td>少走几步快多少、画质掉多少</td></tr>
<tr><td><strong>共同点</strong></td><td colspan="2">同一个 SD 1.5 基座、同一批提示词、同种子、同一台 5700G —— <strong>两期数字可互相引用但不可混表</strong></td></tr>
</tbody></table>

<p class="small"><strong>原则：同一期不同时动两个变量。</strong>若两期都动，读者分不清是位宽还是步数导致的差异 —— 这是 ep4 没踩但容易踩的坑。</p>

<h2>八、文章重设计（吸收 ep4 阅读量的四条教训）</h2>"""
t = rep(t, old, new, "sec-ep5-split")

# --- 8) 待拍板补一行 ---
old = """<tr><td>5</td><td><strong>画质盲评</strong>由你打分（25 题 × 3 模型并排）</td>"""
new = """<tr><td>6</td><td><strong>中文专项 10 题</strong>（1/4/20 三档）要不要单独给你看图打分？</td><td><strong>要</strong> —— 这是最可能出结论的地方；约 10 分钟</td></tr>
<tr><td>5</td><td><strong>画质盲评</strong>由你打分（25 题 × 4 模型并排）</td>"""
t = rep(t, old, new, "pending-6")

# 25 题 x 3 模型 -> 4 模型（加了 LCM）
t = t.replace("25 题 × 3 模型并排", "25 题 × 4 模型并排")
t = t.replace("25 题 × 3 模型", "25 题 × 4 模型")

# 版本号
t = t.replace("方案 v1 · 待你 review", "方案 v2 · 待你 review（v1→v2 补 4 项）")
t = t.replace("ep6 跑测方案：一步出图", "ep6 跑测方案 v2：一步出图")

p.write_text(t, encoding="utf-8")
v = p.read_text(encoding="utf-8", errors="replace")
print("=== ep6 方案 v2 ===")
print("修改 %d 处 | %.1f KB" % (n, len(v.encode())/1024))
for k in ["lcm-lora-sdv1-5", "128.4 MB", "openrail++", "五类题材分层", "中文写字专项",
          "与 ep5 的分工", "705 次", "方案 v2", "portrait of an elderly fisherman"]:
    print("  %-32s %s" % (k, "✅" if k in v else "❌"))
bad = 0
for a, b in [("<table","</table>"),("<tr","</tr>"),("<td","</td>"),("<div","</div>"),("<strong","</strong>"),("<h2","</h2>")]:
    n1 = len(re.findall(re.escape(a)+r"[ >]", v)) if a in ("<tr","<td") else v.count(a)
    if n1 != v.count(b): print("  ✗", a, n1, v.count(b)); bad += 1
print("  结构:", "✅ 平" if bad == 0 else "✗ %d" % bad)
print("  h2 章节:")
for m in re.finditer(r"<h2>(.*?)</h2>", v, re.S):
    print("    ", re.sub(r"<[^>]+>", "", m.group(1))[:60])

# ================= B) 排期表 ep6 补 test_plan =================
DB = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
TESTPLAN = ("见 articles/bench/ep6-一步出图-跑测方案.html（v2）：四模型（SDXS/SD-Turbo/SDXL-Turbo/SD1.5+LCM-LoRA）"
            "× 1/4/20 步；题库 25 题按 ep4 五类题材分层 + 中文写字专项 10 题；"
            "口径含噪声地板（同种子连跑 5 次比哈希）、冷启与推理分开计时、每配置 3 次取中位；"
            "与 ep5 分工=ep5 只动位宽、ep6 只动步数；许可三款全部放行（SDXL 初版误判已纠正）")
con = sqlite3.connect(DB, timeout=20)
try:
    cur = con.cursor()
    old_tp = cur.execute("SELECT test_plan FROM series_plans WHERE brand='local-ai' AND episode=6").fetchone()[0]
    print("\n=== 排期表 ep6 test_plan ===")
    print("  改前:", repr(old_tp)[:80])
    cur.execute("UPDATE series_plans SET test_plan=?, updated_at=? WHERE brand='local-ai' AND episode=6",
                (TESTPLAN, time.strftime("%Y-%m-%dT%H:%M:%S")))
    con.commit()
    new_tp = cur.execute("SELECT test_plan FROM series_plans WHERE brand='local-ai' AND episode=6").fetchone()[0]
    print("  改后: %d 字 ✅" % len(new_tp))
finally:
    con.close()
