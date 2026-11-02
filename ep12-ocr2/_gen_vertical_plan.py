# -*- coding: utf-8 -*-
"""垂直板块重构方案（HTML）—— 数字全部从 _schedule_dump.json 现算"""
import json, pathlib, datetime as dt
from collections import Counter

SRC = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/_schedule_dump.json")
OUT = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/垂直板块重构方案.html")
rows = {r["ep"]: r for r in json.loads(SRC.read_text(encoding="utf-8"))}

# 订正后的板块归属（人工核定，非关键词）
V = {
 "OCR":       [11, 12, 30],
 "ASR":       [3, 9, 10, 28],
 "声音克隆":   [2, 25, 41],
 "小模型":    [1, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26, 27,
             29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47],
 "文生图":    [4, 5, 6, 7, 8],
 "串场景":    [24],
 "跨场景":    list(range(48, 68)),
 "档位":      list(range(68, 88)),
 "失败边界":   list(range(88, 103)),
}
LAYER = {  # 五层深度路径：单点 / 横评 / 边界 / 换代 / 串场景
 "OCR":    ["ep11 三引擎对照", "ep12 续测六引擎", "—", "—", "ep30 票据场景"],
 "ASR":    ["ep3 六模型", "ep9 八模型 / ep10 双档", "—", "—", "ep28 会议录音"],
 "声音克隆": ["ep2 零样本人门", "ep25 三引擎 / ep41 四音色", "—", "—", "—"],
 "小模型":  ["ep13 中系 / ep14 英系", "ep15 中英对决 / ep29-47 任务横评", "ep16 思考 / ep23 边界清单", "—", "ep24 语音对话"],
 "文生图":  ["ep4 四引擎", "ep7 换引擎 / ep5 量化 / ep6 步数", "ep8 大模型的墙", "ep6 续测 ep4", "—"],
 "文生视频": ["⚠ 空白", "⚠ 空白", "⚠ 空白", "⚠ 空白", "⚠ 空白"],
}
def esc(s): return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def stat(eps):
    e = sorted(set(eps))
    pub = [x for x in e if rows[x]["st"] in ("published", "drafted")]
    d = [rows[x]["date"] for x in e if rows[x]["date"]]
    return len(e), len(pub), (min(d) if d else "—"), (max(d) if d else "—")

CSS = """
:root{--ink:#16191d;--sub:#667085;--line:#e6e8eb;--bg:#fff;--soft:#f6f7f9;--acc:#1f5eff;--ok:#0a7d4f;--warn:#b45309;--bad:#c0392b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14.8px;line-height:1.72}
.wrap{max-width:1000px;margin:0 auto;padding:46px 22px 80px}
h1{font-size:26px;margin:0 0 6px}h2{font-size:19.5px;margin:42px 0 12px;padding-top:17px;border-top:1px solid var(--line)}
h3{font-size:16px;margin:24px 0 8px;color:#2b3038}p{margin:10px 0}
.lede{color:var(--sub);margin:0 0 24px}
.meta{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 26px}
.pill{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:3px 11px;font-size:12.5px;color:#4b5563}
table{width:100%;border-collapse:collapse;margin:13px 0;font-size:13.9px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);font-weight:600;font-size:13px;color:#3b4149}td.num,th.num{text-align:right}
.tag{display:inline-block;padding:1px 7px;border-radius:4px;font-size:12px;font-weight:600;white-space:nowrap}
.t-ok{background:#e7f6ef;color:var(--ok)}.t-warn{background:#fdf3e3;color:var(--warn)}
.t-bad{background:#fdeceb;color:var(--bad)}.t-info{background:#eaf0ff;color:var(--acc)}
.t-mut{background:#eef0f3;color:#667085}
.callout{background:var(--soft);border-left:3px solid var(--acc);padding:13px 16px;margin:16px 0;border-radius:0 6px 6px 0;font-size:14.1px}
.callout.warn{border-left-color:var(--warn);background:#fffaf2}
.callout.bad{border-left-color:var(--bad);background:#fdf6f5}
.gap{color:var(--bad);font-weight:600}.ok{color:var(--ok);font-weight:600}
code{background:var(--soft);padding:0 4px;border-radius:3px;font-family:Consolas,monospace;font-size:12.7px}
.small{font-size:12.9px;color:var(--sub)}
.foot{margin-top:44px;padding-top:15px;border-top:1px solid var(--line);color:#98a2b3;font-size:12.3px}
ol li,ul li{margin:6px 0}
"""
H = ["<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
     "<meta name='viewport' content='width=device-width,initial-scale=1'>",
     "<title>垂直板块重构方案</title><style>%s</style></head><body><div class='wrap'>" % CSS,
     "<h1>垂直板块重构方案</h1>",
     "<p class='lede'>把单一长线拆成 <strong>OCR / ASR / 声音克隆 / 小模型 / 文生图 / 文生视频</strong> 六个垂直板块，<strong>加强深度而非铺量</strong>。</p>",
     "<div class='meta'><span class='pill'>方案 v1 · 待你 review</span>"
     "<span class='pill'>不重编号</span><span class='pill'>数字现算自 102 行排期</span>"
     "<span class='pill'>本轮未执行</span></div>"]

# 一、现状
H.append("<h2>一、现状盘点（订正后）</h2>")
H.append("<p class='small'>关键词自动归类有误（ep4 含「画图」被误归小模型、ep24 语音对话被误归 OCR、ep2 含「录音」被误归 ASR），<strong>下表为人工核定</strong>，覆盖 102/102 无重复无遗漏。</p>")
H.append("<table><thead><tr><th>板块</th><th class='num'>期数</th><th class='num'>已发/待发</th><th>跨度</th><th>现有深度</th></tr></thead><tbody>")
ORDER = ["OCR", "ASR", "声音克隆", "小模型", "文生图", "串场景", "跨场景", "档位", "失败边界"]
for v in ORDER:
    n, pub, d0, d1 = stat(V[v])
    tag = ("<span class='tag t-ok'>已成线</span>" if pub >= 2 else
           "<span class='tag t-warn'>起步</span>" if pub >= 1 else
           "<span class='tag t-mut'>纯规划</span>" if n > 0 else "<span class='tag t-bad'>空白</span>")
    H.append("<tr><td><strong>%s</strong></td><td class='num'>%d</td><td class='num'>%d</td><td class='small'>%s ~ %s</td><td>%s</td></tr>"
             % (v, n, pub, d0, d1, tag))
H.append("<tr><td><strong>文生视频</strong></td><td class='num'>0</td><td class='num'>0</td><td class='small'>—</td><td><span class='tag t-bad'>完全空白</span></td></tr>")
H.append("</tbody></table>")
H.append("<div class='callout'><strong>三个事实：</strong>"
         "① <strong>小模型独大 31 期</strong>，其中 ep29–47 是 19 期「同一个任务 N 个模型」任务横评 —— 这本身就是一条独立垂线；"
         "② <strong>55 期是占位</strong>（ep48–102），大量「选题运行时确定」，是可再分配的空位；"
         "③ <strong>ASR 与 OCR 是读者已验证的兴趣点</strong>（已发布 7 期里占 5 期）。</div>")

# 二、板块设计
H.append("<h2>二、六个板块的定位与深度路径</h2>")
H.append("<p>每板块统一走 <strong>五层深度路径</strong>，层与层之间不是并列而是<strong>递进</strong> —— "
         "上一层的结论是下一层的前提：</p>")
H.append("<table><thead><tr><th>层</th><th>回答什么</th><th>典型形式</th></tr></thead><tbody>")
for a, b, c in [
 ("L1 单点实测", "这个东西能不能在我机器上跑", "一个引擎 / 一个模型 / 一个任务，给耗时与内存实数"),
 ("L2 横评对照", "同任务下谁更好", "N 个引擎/模型同机同参，同口径直比"),
 ("L3 边界与失败", "哪里会崩、崩成什么样", "极限档位、噪声地板、失败模式清单"),
 ("L4 换代续测", "新版本出来还值不值得重跑", "同口径复测 + 与上一代跨期直比"),
 ("L5 串场景", "它跟别的板块怎么接成工作流", "ASR→小模型→TTS 之类的链路实测"),
]:
    H.append("<tr><td><strong>%s</strong></td><td>%s</td><td class='small'>%s</td></tr>" % (a, b, c))
H.append("</tbody></table>")

H.append("<h3>各板块现在的层与缺口</h3>")
H.append("<table><thead><tr><th>板块</th><th>L1 单点</th><th>L2 横评</th><th>L3 边界</th><th>L4 换代</th><th>L5 串场景</th></tr></thead><tbody>")
for v in ["OCR", "ASR", "声音克隆", "小模型", "文生图", "文生视频"]:
    cells = LAYER[v]
    H.append("<tr><td><strong>%s</strong></td>" % v)
    for c in cells:
        if c.startswith("—"):
            H.append("<td class='gap'>缺</td>")
        elif c.startswith("⚠"):
            H.append("<td class='gap'>空白</td>")
        else:
            H.append("<td class='small'>%s</td>" % esc(c))
    H.append("</tr>")
H.append("</tbody></table>")
H.append("<div class='callout warn'><strong>缺口最集中的两层</strong>："
         "<strong>L3 边界</strong>（除小模型外全缺）与 <strong>L4 换代续测</strong>（只有文生图 ep6 算）—— "
         "这两层恰是「深度」的来源：<strong>L2 只能说谁快，L3/L4 才能说什么时候不能用、值不值得换</strong>。</div>")

# 三、文生视频可行性
H.append("<h2>三、文生视频：可行性红线（先看清再决定要不要立板块）</h2>")
H.append("<table><thead><tr><th>场景</th><th>耗时</th><th>出处</th><th>性质</th></tr></thead><tbody>")
for a, b, c, d in [
 ("M3 Ultra（比本机快得多）· CogVideoX-Fun q4 · 672×384",
  "<strong>338 秒 / 1 秒视频</strong>", "rapidmlx 文档", "<span class='tag t-info'>第三方</span>"),
 ("A100 80GB 单卡 · Wan2.1-1.3B · 480p 5 秒（最轻档）",
  "<strong>3 分钟</strong>", "Clore.ai 基准", "<span class='tag t-info'>第三方</span>"),
 ("A100 80GB · CogVideoX-5B · 480p 5 秒", "10 分钟", "Clore.ai", "<span class='tag t-info'>第三方</span>"),
 ("A100 80GB · Hunyuan Video · 720p 5 秒", "<strong>约 3 小时</strong>", "Clore.ai", "<span class='tag t-info'>第三方</span>"),
 ("任何模型 · 1080p", "显存溢出", "Clore.ai", "<span class='tag t-bad'>跑不了</span>"),
 ("最低显存 Wan2.1-1.3B", "8 GB VRAM", "多处交叉", "<span class='tag t-warn'>本机无显卡</span>"),
]:
    H.append("<tr><td>%s</td><td>%s</td><td class='small'>%s</td><td>%s</td></tr>" % (a, b, c, d))
H.append("</tbody></table>")
H.append("<div class='callout bad'><strong>推论（本机估算，非实测）：</strong>"
         "M3 Ultra 出 1 秒视频要 338 秒；本机 Ryzen 7 5700G <strong>慢一个数量级是合理预期</strong>，"
         "则 <strong>5 秒视频约需几十分钟到数小时</strong>。最低档 Wan2.1-1.3B 下载 &lt;5 GB，<strong>技术上可能跑得动</strong>，"
         "但一轮完整跑测（多题 × 多模型）<strong>可能是数十小时量级</strong>。</div>")
H.append("<div class='callout'><strong>但这恰恰是最稀缺的一格：</strong>正因为慢，<strong>没显卡跑视频没人测过</strong> —— "
         "「无显卡机器出 5 秒视频要多久、画质掉在哪」这个题<strong>几乎零竞争</strong>。"
         "<br><br><strong>我的建议：不立板块，先做一次可行性探测</strong> —— 用 Wan2.1-1.3B 出 1 段最短视频，"
         "<strong>只回答「跑不跑得动、多久、多大内存」三个问题</strong>，拿到真实数再决定要不要立板块。"
         "<strong>避免先立板块后发现跑不动</strong>。</div>")

# 四、库结构
H.append("<h2>四、库结构怎么改（零风险方案）</h2>")
H.append("<table><thead><tr><th>做法</th><th>改动</th><th>风险</th></tr></thead><tbody>")
for a, b, c in [
 ("<strong>A（推荐）：新增 <code>vertical</code> 字段</strong>",
  "给 102 行各打一个板块标签（ocr / asr / voice-clone / llm / txt2img / cross…）",
  "<span class='tag t-ok'>零</span> —— 不动 episode、不动日期、不动标题；文内「第X节」引用不受影响"),
 ("B：拆成多个 series（新表或改 brand）",
  "每板块一个 brand/series 值",
  "<span class='tag t-warn'>中</span> —— articles 表、成稿路径、脚本里的 brand='local-ai' 全要跟着改", ),
 ("C：重编号（每板块独立 ep1 起）",
  "彻底重排",
  "<span class='tag t-bad'>高</span> —— 会打断已发布 7 期的引用与历史链接，<strong>不建议</strong>", ),
]:
    H.append("<tr><td>%s</td><td class='small'>%s</td><td class='small'>%s</td></tr>" % (a, b, c))
H.append("</tbody></table>")

# 五、节奏
H.append("<h2>五、发布节奏怎么排</h2>")
H.append("<table><thead><tr><th>方案</th><th>做法</th><th>利</th><th>弊</th></tr></thead><tbody>")
for a, b, c, d in [
 ("<strong>A（推荐）</strong>", "<strong>板块内连续 3–4 期</strong>，再换板块",
  "读者能连着看完整条深度路径；<strong>搜一搜同主题命中叠加</strong>", "换板块时读者需重新认识"),
 ("B", "每周轮流不同板块", "内容多样", "<strong>深度路径被打断</strong>，读者记不住上期"),
 ("C", "每月一个板块主题（4 期/月）", "节奏稳定", "换月才换主题，跨度偏长"),
]:
    H.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (a, b, c, d))
H.append("</tbody></table>")
H.append("<p class='small'><strong>按 A 排的话</strong>：11 月 ep13–16 是小模型四期（已排，正好是一个连续块）；"
         "12 月 ep5–8 是文生图四期（已排）—— <strong>现有节奏其实已经接近 A</strong>，只需把换板块处加过渡说明。</p>")

# 六、重分配
H.append("<h2>六、55 期占位怎么再分配</h2>")
H.append("<table><thead><tr><th>占位段</th><th>期数</th><th>现状</th><th>建议去向</th></tr></thead><tbody>")
for a, b, c, d in [
 ("ep48–51", "4", "有具体选题（知识库问答 / 长文摘要 / 离线翻译 / 写代码）", "<strong>归小模型板块</strong>（本就是小模型场景）"),
 ("ep52–67", "16", "「装进具体生活场景」占位", "<strong>按内容分配到各板块的 L5 串场景层</strong>"),
 ("ep68–87", "20", "「不同机器档位实测」占位", "<strong>归小模型板块的档位层</strong>，或<strong>收缩</strong>（20 期偏多）"),
 ("ep88–102", "15", "「失败与边界实录」占位", "<strong>正好对应 L3 边界层</strong> —— 按板块拆分而非单列"),
]:
    H.append("<tr><td><strong>%s</strong></td><td class='num'>%s</td><td class='small'>%s</td><td class='small'>%s</td></tr>" % (a, b, c, d))
H.append("</tbody></table>")
H.append("<div class='callout warn'><strong>一个诚实的提醒：</strong>ep88–102 共 15 期全叫「失败与边界实录·选题运行时确定」，"
         "<strong>等于 15 个空壳排到了 2028-09</strong>。按板块重构正是清理它们的时机 —— "
         "把「边界」拆到各板块的 L3 层，<strong>而不是留 15 期同名占位</strong>。</div>")

# 七、待拍板
H.append("<h2>七、待你拍板</h2>")
H.append("<table><thead><tr><th>#</th><th>问题</th><th>我的建议</th></tr></thead><tbody>")
for i, (q, s) in enumerate([
 ("六板块是否照此划分？（OCR / ASR / 声音克隆 / 小模型 / 文生图 / 文生视频）",
  "<strong>是</strong>；但「串场景」（ep24）建议并入小模型 L5，不单列"),
 ("库结构怎么改？", "<strong>A：新增 <code>vertical</code> 字段</strong>，102 行各打标签，不重编号"),
 ("发布节奏？", "<strong>A：板块内连续 3–4 期</strong>（现有节奏已接近，只需加板块过渡说明）"),
 ("55 期占位怎么处理？",
  "<strong>按第六节重分配</strong>：ep52–67 拆到各板块 L5、ep68–87 归档位层、<strong>ep88–102 拆到各板块 L3</strong>"),
 ("文生视频立不立板块？",
  "<strong>先不立</strong> —— 用 Wan2.1-1.3B 做<strong>一次可行性探测</strong>（1 段最短视频），"
  "拿到真实耗时/内存再决定；<strong>避免先立板块后发现跑不动</strong>"),
 ("优先补哪层？", "<strong>L3 边界层</strong> —— 六板块里五个缺，且它是「深度」的核心来源"),
], 1):
    H.append("<tr><td class='num'>%d</td><td>%s</td><td class='small'>%s</td></tr>" % (i, q, s))
H.append("</tbody></table>")
H.append("<p class='small'>回序号 + 处置词即可（如「1 是、2 A、3 A、4 照做、5 探测、6 L3」）。</p>")

H.append("<div class='foot'>方案 v1 · 生成于 2026-10-27 · <strong>本轮未写库、未改任何一行排期</strong><br>"
         "板块归属为<strong>人工核定</strong>（关键词自动归类有误，已订正），覆盖 102/102 无重复无遗漏。<br>"
         "文生视频数据均为<strong>第三方</strong>（rapidmlx / Clore.ai），<strong>本机未实测</strong>；推论已标注为估算。</div>")
H.append("</div></body></html>")

OUT.write_text("".join(H), encoding="utf-8")
v = OUT.read_text(encoding="utf-8", errors="replace")
import re
print("生成: %s | %.1f KB" % (OUT.name, len(v.encode())/1024))
bad = 0
for a, b in [("<table","</table>"),("<tr","</tr>"),("<td","</td>"),("<div","</div>"),("<h2","</h2>"),("<h3","</h3>")]:
    n1 = len(re.findall(re.escape(a)+r"[ >]", v)) if a in ("<tr","<td") else v.count(a)
    if n1 != v.count(b): print("  ✗", a, n1, v.count(b)); bad += 1
print("  结构:", "✅ 平" if bad == 0 else "✗ %d" % bad)
print("  h2:", [re.sub(r"<[^>]+>","",m.group(1)) for m in re.finditer(r"<h2>(.*?)</h2>", v, re.S)])
# 板块期数校验
tot = sum(len(set(V[k])) for k in V)
print("  板块合计期数:", tot, "(应 102)" if tot == 102 else "✗")
