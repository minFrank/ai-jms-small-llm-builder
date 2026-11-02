# -*- coding: utf-8 -*-
"""ep25 方案：加「公平性与可比性声明」+ 跑量改为 5 引擎 + 补出局与国际系行"""
import pathlib, re

p = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep25-声音克隆-选题与方案.html")
t = p.read_text(encoding="utf-8", errors="replace")
n = 0

def rep(t, old, new, tag):
    global n
    c = t.count(old)
    assert c == 1, "[%s] 命中 %d" % (tag, c)
    n += 1
    return t.replace(old, new)

SEC = """<h3>§A0 公平性与可比性声明 <span class="tag t-info">2026-10-27 加</span></h3>

<div class="callout bad"><strong>先说结论：五个引擎一起比，<u>不能给总排名</u>。</strong>
原因很直白 —— <strong>它们不是在同一条起跑线上</strong>。下面三条是硬规则，跑之前就写死，跑完不许改。</div>

<h4>三个不公平点（有据）</h4>
<table><thead><tr><th>不公平在哪</th><th>大白话</th><th>证据</th></tr></thead><tbody>
<tr><td><strong>比快慢不公平</strong></td>
<td>小 20 倍的模型当然快。放一起比谁快，等于<strong>让小学生跟大学生赛跑</strong>。</td>
<td>MOSS-Nano <strong>1 亿</strong>参数；VoxCPM2 约 <strong>20 亿</strong>；Qwen3 0.6B；CosyVoice3 0.5B；MetaVoice 1.2B</td></tr>
<tr><td><strong>要交的东西不一样</strong></td>
<td>Qwen3 除了要参考音频，<strong>还要你把那段音频念的字打给它</strong>（逐字稿）。别的引擎只要一段录音。你多给一样东西它表现好，能算它赢吗？</td>
<td>Qwen3 README：需 <code>ref_audio</code> + <code>ref_text</code>；其余 README 未见此要求</td></tr>
<tr><td><strong>上手难度不一样</strong></td>
<td>有的插上就用，<strong>有的要先训练</strong>。不是一回事。</td>
<td>VoxCPM2 与 MetaVoice 的 README 出现微调/训练相关内容；其余未见</td></tr>
</tbody></table>

<h4>三条规则（跑之前定死）</h4>
<table><thead><tr><th>#</th><th>规则</th><th>为什么</th></tr></thead><tbody>
<tr><td class="num">1</td>
<td><strong>不评总分，只分维度各排一榜</strong></td>
<td>速度榜、中文字准榜、听感榜、上手难度榜、许可榜 —— <strong>五个榜分开</strong>。<strong>谁都不是第一，谁都有擅长的</strong>，读者按自己要什么挑</td></tr>
<tr><td class="num">2</td>
<td><strong>同样大小的才互相比</strong></td>
<td><strong>轻量组</strong>（≤0.5B）：MOSS-Nano、CosyVoice3<br><strong>主力组</strong>（0.5–0.7B）：Qwen3<br><strong>大块头组</strong>（≥1B）：VoxCPM2<br>
<strong>跨档只给对照，不排名</strong></td></tr>
<tr><td class="num">3</td>
<td><strong>不对等的地方，每张表下面都标出来</strong></td>
<td>要交几个输入、要不要先训练、有没有 CPU 优化、参数多少 —— <strong>不藏</strong>，读者自己判断「它赢是不是占了便宜」</td></tr>
</tbody></table>

<h4>我的检测方法有局限，必须先说</h4>
<div class="callout warn">
上面「它要什么、它多大」这些<strong>是靠搜 README 关键词扒出来的，不完全靠谱</strong>。<br><br>
<strong>具体反例：CosyVoice3 我标成「不用逐字稿」，其实它要</strong> —— 只是它的参数名叫 <code>prompt_audio</code> / <code>prompt_text</code>，不叫 <code>ref_audio</code>，我搜错了词没命中。<br><br>
<strong>所以这一列只能当线索，最终以实跑为准。</strong>不许拿这张搜出来的表直接写进文章 —— 真跑时逐个引擎核对它到底要什么输入，核对结果才是正文数据。
</div>

<h4>顺带加一个指标：上手难度</h4>
<p>既然要交的东西不一样，<strong>「要准备什么」本身就是读者最关心的</strong>。加一列 <strong>上手难度</strong>：</p>
<ul>
<li>给一段录音就行</li>
<li>录音 + 逐字稿</li>
<li>还得先训练</li>
</ul>
<p class="small">这个角度 <strong>ep2 已经验证过</strong>（ep2 的卖点就是「20–30 秒录音、不训练、不联网」），本期接着做，能跟上期连上。</p>

<h3>§A 等价性（测前固定，跑之前写死）</h3>"""

t = rep(t, '<h3>§A 等价性（测前固定，跑之前写死）</h3>', SEC, "fairness")

t = rep(t, '<tr><td>三引擎 × 25 题 × 3 次（合成）</td><td class="num">225</td>',
        '<tr><td>五引擎 × 25 题 × 3 次（合成）</td><td class="num">375</td>', "run5")
t = rep(t, '<tr><td>噪声地板（三引擎 × 5 次）</td><td class="num">15</td>',
        '<tr><td>噪声地板（五引擎 × 5 次）</td><td class="num">25</td>', "floor5")
t = rep(t, '<tr><td><strong>ASR 回验转写</strong>（225 段 × 3 次取多数）</td><td class="num">675 段</td>',
        '<tr><td><strong>ASR 回验转写</strong>（375 段 × 3 次取多数）</td><td class="num">1125 段</td>', "asr5")
t = rep(t, '<tr><td><strong>合计</strong></td><td class="num"><strong>约 900 次调用</strong></td>',
        '<tr><td><strong>合计</strong></td><td class="num"><strong>约 1500 次调用</strong></td>', "tot5")
t = rep(t, '<td class="num"><strong>约 1–3.5 小时</strong></td>', '<td class="num"><strong>约 1.5–5 小时</strong></td>', "time5")

t = rep(t, '<tr><td>F5-TTS / ChatTTS / fish-speech</td><td><strong>CC-BY-NC*</strong></td><td>—</td><td><span class="tag t-bad">出局</span> 三个最热门的都非商用</td></tr>',
        '<tr><td>F5-TTS / ChatTTS / fish-speech</td><td><strong>CC-BY-NC*</strong></td><td>—</td><td><span class="tag t-bad">出局</span> 三个最热门的都非商用</td></tr>\n'
        '<tr><td><strong>Spark-TTS-0.5B</strong>（747 赞）/ <strong>MaskGCT</strong>（309 赞）</td><td><strong>cc-by-nc</strong></td><td>—</td>'
        '<td><span class="tag t-bad">出局</span> <strong>国际系里赞最高的两个，也都是非商用</strong></td></tr>\n'
        '<tr><td>MetaVoice / OpenVoiceV2 / Zonos / MOSS-Nano</td><td>apache-2.0 / MIT</td><td>—</td>'
        '<td><span class="tag t-info">移下期</span> <strong>国际系单独一期</strong>（ep41，英文题），本期只做中系</td></tr>',
        "cand")

t = t.replace("方案 v1 · 待你选", "方案 v2 · 选题已定，含公平性声明")

p.write_text(t, encoding="utf-8")
v = p.read_text(encoding="utf-8", errors="replace")
print("修改 %d 处 | %.1f KB" % (n, len(v.encode())/1024))
for k in ["§A0 公平性与可比性声明", "不评总分", "同样大小的才互相比", "prompt_audio",
          "让小学生跟大学生赛跑", "约 1500 次调用", "国际系单独一期", "上手难度",
          "方案 v2"]:
    print("  %-26s %s" % (k, "OK" if k in v else "MISSING"))
bad = 0
for a, b in [("<table", "</table>"), ("<tr", "</tr>"), ("<td", "</td>"), ("<div", "</div>"),
             ("<h3", "</h3>"), ("<h4", "</h4>"), ("<ul", "</ul>"), ("<li", "</li>")]:
    n1 = len(re.findall(re.escape(a) + r"[ >]", v)) if a in ("<tr", "<td", "<li") else v.count(a)
    if n1 != v.count(b):
        print("  MISMATCH %-9s %d vs %d" % (a, n1, v.count(b)))
        bad += 1
print("结构:", "ALL BALANCED" if bad == 0 else "%d mismatch" % bad)
print("收尾:", repr(v.rstrip()[-22:]))