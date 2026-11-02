# -*- coding: utf-8 -*-
"""按用户「其他按建议来」更新两份方案文档（只改文档，不执行）
ep6 方案: SDXL-Turbo 由出局改为进名单（许可已澄清）+ 资源账 +2
排期方案: 第七节 2/3/4/5 标已定 + 资源账 + 声音克隆号位已定
"""
import pathlib, re

# ============ 1) ep6 跑测方案 ============
p6 = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep6-一步出图-跑测方案.html")
t = p6.read_text(encoding="utf-8", errors="replace")
n = 0

def rep(t, old, new, tag):
    global n
    c = t.count(old)
    assert c == 1, "[%s] 命中 %d 次" % (tag, c)
    n += 1
    return t.replace(old, new)

# 1a. SDXL-Turbo 许可行
old_sdxl_lic = """<tr><td><strong>SDXL-Turbo</strong><br><span class="small">stabilityai/sdxl-turbo</span></td>
<td><code>license: other</code> · <code>license_name: <strong>sai-nc-community</strong></code><br>LICENSE.md 同为 Stability AI Community License<br>README：<em>"For commercial use, please refer to stability.ai/license."</em></td>
<td><span class="tag t-bad">非商用</span></td>
<td><strong>出局</strong> —— <code>nc</code> 即 non-commercial。第三方那张 2.5 秒的表正是它，<strong>数字诱人但不能进可商用结论</strong></td></tr>"""
new_sdxl_lic = """<tr><td><strong>SDXL-Turbo</strong><br><span class="small">stabilityai/sdxl-turbo</span></td>
<td><code>LICENSE.md</code> = STABILITY AI COMMUNITY LICENSE AGREEMENT（11733 字符，<strong>与 sd-turbo 逐字相同</strong>）<br>原文：<em>"allow research, non-commercial, and <strong>limited commercial uses</strong> … free of charge"</em> · <em>"free access … annual revenue of <strong>less than US $1,000,000</strong>"</em><br><span class="small">HF 元数据 <code>license_name: sai-nc-community</code> 与正文冲突，<strong>以 LICENSE.md 正文为准</strong></span></td>
<td><span class="tag t-ok">已澄清：可商用</span></td>
<td><strong>进名单</strong> —— <strong>本方案初版误判为非商用，2026-10-27 读 LICENSE.md 正文后纠正</strong>。年收入低于 100 万美元免费商用</td></tr>"""
t = rep(t, old_sdxl_lic, new_sdxl_lic, "sdxl-license-row")

# 1b. callout bad -> 已澄清
old_call = """<div class="callout bad"><strong>这是本方案第一个硬结论：</strong>FastSD README 里最快的三个数（0.82 / 1.7 / 2.5 秒），<strong>其中 2.5 秒那个（SDXL-Turbo）是非商用许可</strong>。文章若引用必须标注，否则读者照做会踩授权风险 —— 违反「对外内容无授权风险」这条底线。</div>"""
new_call = """<div class="callout warn"><strong>许可闸门的教训（写进流程）：</strong>初版据 HF 元数据 <code>license_name: sai-nc-community</code> 判 SDXL-Turbo 为非商用，<strong>读 LICENSE.md 正文后发现是误判</strong> —— 两份 LICENSE.md 逐字相同，都允许年收入 &lt; US$1M 的商用。<br><br><strong>规则：HF 的 license 字段只作线索，判定必须读仓库内 LICENSE 正文 + 官方许可页</strong>（<code>stability.ai/license</code> 的 FAQ 原文亦确认 Community 覆盖 SDXL Turbo）。</div>"""
t = rep(t, old_call, new_call, "callout-bad")

# 1c. 模型选型表 SDXL 行
old_sel = """<tr><td><strong>对照位</strong></td><td>SDXL-Turbo</td><td class="num">6.62 GB<br><span class="small">（fp16）</span></td><td class="num">1</td><td><span class="tag t-bad">非商用</span></td></tr>"""
if t.count(old_sel) != 1:
    old_sel = """<tr><td><strong>对照位</strong></td><td>SDXL-Turbo</td><td class="num">6.62 GB (fp16)</td><td class="num">1</td><td><span class="tag t-bad">非商用</span></td></tr>"""
new_sel = """<tr><td><strong>主测 3</strong></td><td><strong>SDXL-Turbo</strong><br><span class="small">stabilityai/sdxl-turbo（fp16 6616.7 MB）</span></td><td class="num">6.62 GB<br><span class="small">（OpenVINO int8 版 4.43 GB）</span></td><td class="num">1</td><td><span class="tag t-ok">已澄清可商用</span></td></tr>"""
t = rep(t, old_sel, new_sel, "sdxl-select-row")

# 1d. 「SDXL-Turbo 的处置」段
i = t.find("<p class=\"small\"><strong>SDXL-Turbo 的处置</strong>")
if i > 0:
    j = t.find("</p>", i) + 4
    t = t[:i] + ("<p class=\"small\"><strong>SDXL-Turbo 的处置（2026-10-27 更新）</strong>：许可已澄清为可商用，"
                 "<strong>纳入主测</strong>。它是行业最快的参照点，第三方 2.5 秒必须有本机一手数才站得住。"
                 "<strong>体积 6.62 GB（fp16）或 OpenVINO int8 版 4.43 GB</strong> —— 建议走 int8 版，与 SDXS 同路线可比。</p>") + t[j:]
    n += 1

# 1e. 排除项表：SDXL 那行
old_ex = """<tr><td><strong>SDXL-Turbo 实测</strong></td><td><span class="tag t-bad">非商用</span>（<code>sai-nc-community</code>）；只引用第三方数字</td></tr>"""
new_ex = """<tr><td><strong>SDXL fp16 完整版</strong></td><td>13.2 GB 单文件，CPU 路线用不上；<strong>改用 OpenVINO int8 版（4.43 GB）</strong>，与 SDXS 同路线</td></tr>"""
t = rep(t, old_ex, new_ex, "exclude-sdxl")

# 1f. 跑量表加 SDXL 档
old_run = """<tr><td>sd.cpp / diffusers 对照档（1 步模型）</td><td class="num">150</td><td class="num">约 5–30 s</td><td class="num">约 13–75 分</td></tr>"""
new_run = """<tr><td><strong>SDXL-Turbo 1 步 · OpenVINO int8 · 512² · 25 题 × 3 次</strong></td><td class="num">75</td><td class="num">约 3–12 s<br><span class="small">第三方 2.5 s / i7-12700</span></td><td class="num">约 4–15 分</td></tr>
<tr><td>sd.cpp / diffusers 对照档（1 步模型）</td><td class="num">150</td><td class="num">约 5–30 s</td><td class="num">约 13–75 分</td></tr>"""
t = rep(t, old_run, new_run, "run-sdxl")

t = t.replace("<tr><td><strong>合计</strong></td><td class=\"num\"><strong>约 465 次出图</strong></td>",
              "<tr><td><strong>合计</strong></td><td class=\"num\"><strong>约 540 次出图</strong></td>")
t = t.replace("<td class=\"num\"><strong>约 3–7.5 小时</strong></td>", "<td class=\"num\"><strong>约 3–8 小时</strong></td>")

# 1g. 待拍板 2/3 标已定
old_p2 = """<tr><td>2</td><td><strong>SDXL-Turbo</strong> 要不要实测？</td><td><strong>不跑</strong>（非商用，省 6.6 GB），只引第三方数字并标注</td></tr>"""
new_p2 = """<tr><td>2</td><td><strong>SDXL-Turbo</strong> 要不要实测？</td><td><span class="tag t-ok">已定：跑</span> 许可已澄清可商用（初版误判已纠正），走 OpenVINO int8 版 4.43 GB</td></tr>"""
t = rep(t, old_p2, new_p2, "pending-2")

old_p3 = """<tr><td>3</td><td><strong>模型下载</strong>：SDXS OpenVINO 2.81 GB + SD-Turbo 1.65 GB ≈ <strong>4.5 GB</strong></td><td>批准后我才下（按规矩先问）</td></tr>"""
new_p3 = """<tr><td>3</td><td><strong>模型下载</strong>：SDXS OpenVINO 2.81 + SD-Turbo 1.65 + <strong>SDXL-Turbo int8 4.43</strong> ≈ <strong>8.9 GB</strong></td><td><span class="tag t-warn">已批准，待执行</span> 首次下到 61% 已按你「不要执行」停掉，<strong>可续传</strong>；ep6 跑测窗口 12-08~12-14</td></tr>"""
t = rep(t, old_p3, new_p3, "pending-3")

# 1h. 跑量风险句里的 465
t = t.replace("跑量与耗时估算", "跑量与耗时估算")
p6.write_text(t, encoding="utf-8")
v6 = p6.read_text(encoding="utf-8", errors="replace")
print("ep6 方案: %d 处修改 | %.1f KB" % (n, len(v6.encode())/1024))
for k in ["已澄清：可商用", "主测 3", "约 540 次", "已定：跑", "8.9 GB", "误判"]:
    print("   %-16s %s" % (k, "✅" if k in v6 else "❌"))
print("   残留「非商用」:", v6.count("非商用"), "（应只剩解释误判的上下文）")

# ============ 2) 排期方案 ============
pr = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/排期方案-未来90天.html")
r = pr.read_text(encoding="utf-8", errors="replace")
m = 0
def rp(r, old, new, tag):
    global m
    c = r.count(old)
    assert c == 1, "[%s] 命中 %d" % (tag, c)
    m += 1
    return r.replace(old, new)

# 2a. 声音克隆行
old_v = """<td><strong>声音克隆</strong><br>号位未定</td>
<td><span class="tag t-ok">实测已完成</span><br><span class="small">Qwen3-0.6B-Base RTF≈7.1 · 中文清晰度输给 CosyVoice3</span></td>
<td>定号位（A 替换 ep24/25 · B 进 ep48+）</td>
<td><span class="tag t-warn">你</span> 定号位</td></tr>"""
new_v = """<td><strong>声音克隆</strong><br>ep25 号位</td>
<td><span class="tag t-ok">实测已完成 + 号位已定</span><br><span class="small">Qwen3-0.6B-Base RTF≈7.1 · 中文清晰度输给 CosyVoice3</span></td>
<td>出跑测方案 → 跑测 → 写稿（2027-03-02 发布）</td>
<td><span class="tag t-info">我</span></td></tr>"""
r = rp(r, old_v, new_v, "voice-line")

# 2b. 资源账
old_res = """<tr><td><strong>模型下载</strong></td><td class="num">约 14 GB</td><td class="num">ep6 约 4.5 GB<br><span class="small">（+6.6 GB 若跑 SDXL，待你定）</span></td><td class="num">0（已完成）</td><td class="num"><strong>约 18.5 GB</strong></td></tr>"""
new_res = """<tr><td><strong>模型下载</strong></td><td class="num">约 14 GB</td><td class="num">ep6 约 <strong>8.9 GB</strong><br><span class="small">SDXS 2.81 + SD-Turbo 1.65 + SDXL int8 4.43</span></td><td class="num">0（已完成）</td><td class="num"><strong>约 22.9 GB</strong></td></tr>"""
r = rp(r, old_res, new_res, "resource-dl")

old_rt = """<tr><td><strong>跑测时长</strong></td><td class="num">约 35 小时</td><td class="num">ep6 约 3–7.5 小时<br><span class="small">（ep5/7/8 未估）</span></td>"""
new_rt = """<tr><td><strong>跑测时长</strong></td><td class="num">约 35 小时</td><td class="num">ep6 约 3–8 小时<br><span class="small">（ep5/7/8 未估）</span></td>"""
r = rp(r, old_rt, new_rt, "resource-time")

# 2c. 第七节全改
old_pend = r[r.find("<tr><td>1</td><td><strong>ep4 档期冲突</strong>"):]
old_pend = old_pend[:old_pend.find("</tbody>")]
new_pend = """<tr><td>1</td><td><strong>ep4 档期冲突</strong>（第四节）</td><td><span class="tag t-ok">已执行 B</span> ep4 → published + 清日期（<strong>1 行</strong>）；ep5–8 未动</td></tr>
<tr><td>2</td><td><strong>ep4 实际群发日期</strong></td><td><span class="tag t-ok">已补</span> <strong>2026-10-21</strong></td></tr>
<tr><td>3</td><td><strong>ep6 要不要跑 SDXL-Turbo</strong></td><td><span class="tag t-ok">已定：跑</span> 许可读 LICENSE.md 正文后澄清为可商用（初版据 HF 元数据误判），走 int8 版 4.43 GB</td></tr>
<tr><td>4</td><td><strong>小模型 9 个 GGUF（14 GB）什么时候下</strong></td><td><span class="tag t-ok">已定：10-31 前</span> 给 ep13 留出 11-01 跑测窗口（ep13 排 11-03）</td></tr>
<tr><td>5</td><td><strong>声音克隆号位</strong></td><td><span class="tag t-ok">已定：A，占 ep25</span> 2027-03-02；原「会议场景」移出（与横评段 ep28 主题重复）</td></tr>
"""
r = r.replace(old_pend, new_pend, 1); m += 1

# 2d. 第四节标完成 + 不执行声明更新
r = r.replace("<li><strong>不下载</strong> —— ep6 那两个模型下到 61% 已停（HF 缓存可续传，不记为已下）；小模型 9 个 GGUF 未动</li>",
              "<li><strong>不下载</strong> —— ep6 模型下到 61% 已停（HF 缓存可续传，不记为已下）；小模型 9 个 GGUF 未动。<strong>已批准待执行：ep6 8.9 GB、小模型 14 GB（10-31 前）</strong></li>")

pr.write_text(r, encoding="utf-8")
vr = pr.read_text(encoding="utf-8", errors="replace")
print("\n排期方案: %d 处修改 | %.1f KB" % (m, len(vr.encode())/1024))
for k in ["ep25 号位", "22.9 GB", "已补</span> <strong>2026-10-21", "已定：跑", "10-31 前", "已定：A，占 ep25"]:
    print("   %-24s %s" % (k, "✅" if k in vr else "❌"))

# 结构复核
for name, doc in [("ep6", v6), ("排期", vr)]:
    bad = 0
    for a, b in [("<table","</table>"),("<tr","</tr>"),("<div","</div>"),("<strong","</strong>")]:
        n1 = len(re.findall(re.escape(a)+r"[ >]", doc)) if a == "<tr" else doc.count(a)
        if n1 != doc.count(b): print("   ✗ %s %s %d/%d" % (name, a, n1, doc.count(b))); bad += 1
    print("   %s 结构: %s" % (name, "✅ 平" if bad == 0 else "✗ %d" % bad))
