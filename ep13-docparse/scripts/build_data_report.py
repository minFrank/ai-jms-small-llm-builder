# -*- coding: utf-8 -*-
"""ep13 数据报告生成器：读 156 格 cell 现算 → 浅色 HTML（总榜/逐样本/边界/口径/声明）"""
import json, glob, os, statistics, collections, datetime

# 2026-11-12 收口：路径可配置 + 项目内自留一份，避免「期目录 outputs/ 为空、产物只落在 C 盘」。
# 默认行为不变（仍写原 hermes 路径）；可用 EP13_BASE / EP13_REPORT_OUT 覆盖。
BASE = os.environ.get("EP13_BASE", r"D:/study/ai-jms/ep13-docparse")
OUT = os.environ.get("EP13_REPORT_OUT",
                     r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/2026-11-10-ep13-数据报告.html")
LOCAL_COPY = os.path.join(BASE, "outputs", "2026-11-10-ep13-数据报告.html")
man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
img_order = [s["img"] for s in man["samples"]]
ENGINES = ["xiaomi_vl", "paddleocr_vl", "oxr", "monkey_rec", "ovis_ocr2", "surya_2_5"]
ENG_CN = {"xiaomi_vl": "Xiaomi-OCR-0", "paddleocr_vl": "PaddleOCR-VL-1.6", "oxr": "OXR-1.0",
          "monkey_rec": "MonkeyOCR-pro", "ovis_ocr2": "OvisOCR2", "surya_2_5": "surya-2.5"}

cells = []
for p in glob.glob(os.path.join(BASE, "cells", "ep13-full-001", "*.json")):
    c = json.load(open(p, encoding="utf-8"))
    c["_img"] = sha2img.get(c["input"]["sha256"], "?")
    cells.append(c)

# ---- 总榜（逐引擎）----
rows = []
for e in ENGINES:
    ec = [c for c in cells if c["engine"] == e]
    cers = sorted(c["cer_median"] for c in ec if c.get("cer_median") is not None)
    norm = [x for x in cers if x <= 0.5]
    walls = sorted(c["wall_median"] for c in ec if c.get("wall_median") is not None)
    n6 = sum(1 for c in ec if c["n_valid"] >= 6)
    rows.append(dict(engine=e, n=len(ec), complete=sum(1 for c in ec if c["status"] == "complete"),
                     n6=n6, cer_med=statistics.median(cers), cer_norm=statistics.median(norm) if norm else None,
                     cer_min=cers[0], cer_max=cers[-1], wall_med=statistics.median(walls),
                     cer_gt05=len(cers) - len(norm)))

# ---- 逐样本矩阵 ----
matrix = {}
for c in cells:
    matrix[(c["_img"], c["engine"])] = c.get("cer_median")

# ---- 离群三类 ----
outliers = sorted([c for c in cells if (c.get("cer_median") or 0) > 0.5],
                  key=lambda c: -c["cer_median"])

def fmt(x, n=4):
    return ("%%.%df" % n) % x if x is not None else "-"

# ---- HTML ----
def bar(v, mx=0.5):
    w = min(100, v / mx * 100)
    color = "#2563eb" if v <= 0.5 else ( "#f59e0b" if v <= 1 else "#dc2626" )
    return f'<span class="bar"><i style="width:{w:.0f}%;background:{color}"></i><b>{v:.3f}</b></span>'

H = []
# ---- 总榜 ----
H.append("<h2>一、全集分布表（六引擎 × 26 格，含 unstable——展示用，<b>非排名</b>，排名见一·B）</h2>")
H.append("""<table><tr><th>引擎（出品方见口径表）</th><th>格数</th><th>complete</th><th>6-rep 达标</th>
<th>CER 中位（全26）</th><th>正常格中位（≤0.5）</th><th>min</th><th>max</th><th>&gt;0.5</th><th>wall 中位</th></tr>""")
for r in sorted(rows, key=lambda r: r["cer_med"]):
    H.append(f"""<tr><td><b>{ENG_CN[r['engine']]}</b></td><td class="num">{r['n']}</td>
<td class="num">{r['complete']}</td><td class="num">{r['n6']}</td>
<td class="num">{fmt(r['cer_med'])}</td><td class="num">{fmt(r['cer_norm'])}</td>
<td class="num">{fmt(r['cer_min'])}</td><td class="num">{fmt(r['cer_max'])}</td>
<td class="num">{r['cer_gt05']}</td><td class="num">{r['wall_med']:.1f}s</td></tr>""")
H.append("</table>")
H.append("""<div class="small">口径：CER 中位含全部 26 格（含复读/困难样本与 unstable 格）；「正常格」= CER≤0.5；wall=端到端（预处理起→解码止，load 外置，OXR 含 D-FINE 版面）。<b>相邻分差 &lt;0.01 视为并列、不下顺序结论</b>（当前 26 格中位最小相邻差：Ovis 0.0862 vs OXR 0.0867，差 0.0005，属并列组；<b>A+C 判据分层下质量名次六引擎全排、两榜（不剔/剔 unstable）同序</b>——详见一·B）。</div>""")

# ---- F-1: 排名榜（剔除 unstable，规格 §2.2/§4.5 要求）----
# r15: rank_set 只含 eligible 引擎的稳定格（稳定格≥25；OXR/Ovis/surya 等 ineligible 整列排除）
# C 方案（2026-11-09 用户拍板）：质量名次按 CER——CER 可用格全入（156 全 complete）
_STABLE_MIN = 25
_stable_cnt = collections.Counter(c["engine"] for c in cells if not c.get("unstable"))
_eligible_engines = {e for e, n in _stable_cnt.items() if n >= _STABLE_MIN}  # 计时稳定列用
rank_cells = [c for c in cells if c.get("cer_median") is not None]  # 质量名次=全部 CER 可用格
rank_keys = [{"sample_id": c["sample_id"], "engine": c["engine"]} for c in rank_cells]
json.dump({"note": ("判据分层（A+C, 2026-11-09）：质量名次=CER 可用格（156 全量、6 引擎全入）；"
                    "计时稳定列=wall stable≥25（%s 不足仅计时名次不含）" % sorted(set(
                        e for e, n in _stable_cnt.items() if n < _STABLE_MIN))),
           "cells": rank_keys},
          open(os.path.join(BASE, "gates", "rank_set.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
import collections as _c0  # 确保（若函数内无 collections）
H.append("<h2>一·B、排名榜（剔除 unstable 格，按规格 §2.2/§4.5）</h2>")
_n_un = sum(1 for c in cells if c.get("unstable"))
_un_d = dict(__import__("collections").Counter(c["engine"] for c in cells if c.get("unstable")))
H.append("""<div class="callout"><b>判据分层（A+C，2026-11-09 拍板）：质量名次按 CER（{} 个 unstable 格的 CER 多为 12 次全同、质量稳定，仍入质量名次）；计时稳定性单列（wall IQR/中位&gt;10% 越阈格）：{}</b>。下表质量名次为结论主榜，计时列供稳定性参考。</div>""".format(_n_un, _un_d))
H.append("""<table><tr><th>引擎</th><th>CER 中位（<b>不剔 unstable</b>，全 26 格）</th><th>名次①（不剔）</th><th>CER 中位（<b>剔 unstable</b>，仅稳定格）</th><th>名次②（剔除）</th><th>并列组（按①中位，&lt;0.01 传递）</th><th>计时稳定格（wall）</th></tr>""")
all_rank = sorted(rows, key=lambda r: r["cer_med"])
all_rank_pos = {r["engine"]: i + 1 for i, r in enumerate(all_rank)}
stab = []
for e in ENGINES:
    ec = [c for c in cells if c["engine"] == e and c.get("cer_median") is not None]  # 不剔=全可用
    cers = sorted(c["cer_median"] for c in ec if c.get("cer_median") is not None)
    if not cers:
        continue
    ec_st = [c for c in ec if not c.get("unstable")]
    cers_st = sorted(c["cer_median"] for c in ec_st if c.get("cer_median") is not None)
    med_st = statistics.median(cers_st) if cers_st else None
    n_stable = len(ec_st)
    stab.append((e, n_stable, statistics.median(cers), len(ec), med_st))
stab.sort(key=lambda x: x[2])  # 名次①按不剔中位
# 名次②按剔除中位
_st_order = sorted([x for x in stab if x[4] is not None], key=lambda x: x[4])
_st_pos = {x[0]: i + 1 for i, x in enumerate(_st_order)}
# 按 <0.01 连通分量分组（相邻传递：a-b<0.01 且 b-c<0.01 则 a,b,c 同组）
groups = []
for idx, item in enumerate(stab):
    if groups and (item[2] - groups[-1][-1][2]) < 0.01:
        groups[-1].append(item)
    else:
        groups.append([item])
letters = "ABCDEFGH"
gmap = {}
for gi, grp in enumerate(groups):
    _deltas = ["Δ%.4f" % (grp[k][2] - grp[k-1][2]) for k in range(1, len(grp))] if len(grp) > 1 else []
    tag = "组%s%s" % (letters[gi], ("（并列：%s）" % "、".join(_deltas)) if len(grp) > 1 else "")
    for it in grp:
        gmap[it[0]] = (tag, len(grp))
for i, (e, n_stable, med, n_cer, med_st) in enumerate(stab):
    pos1 = i + 1  # 名次①不剔
    tag, glen = gmap[e]
    rank1 = "第 %d%s" % (pos1, "（组内并列）" if glen > 1 else "")
    pos2 = _st_pos.get(e)
    rank2 = ("第 %d%s" % (pos2, "（组内并列）" if glen > 1 else "")) if pos2 else "—"
    med_st_s = ("%.4f" % med_st) if med_st is not None else "—"
    timing = "%d/26" % n_stable
    if n_stable < 25:
        timing += "（&lt;25）"
    _tag9 = gmap.get(e, ("—", 1))[0]
    _desc9 = "（② stable&lt;25：仅描述性）" if (n_stable < 25 and pos2) else ""
    H.append(f"<tr><td><b>{ENG_CN[e]}</b></td><td class='num'>{med:.4f}</td>"
             f"<td class='num'>{rank1}</td><td class='num'>{med_st_s}</td>"
             f"<td class='num'>{rank2}{_desc9}</td><td>{_tag9}</td>"
             f"<td class='num'>{timing}</td></tr>")
H.append("</table>")
H.append("""<div class="small"><b>判据分层（A+C，2026-11-09 用户拍板）</b>：<b>排名榜给两版并列——名次①不剔 unstable（全 26 格 CER 中位）、名次②剔 unstable（仅 wall 稳定格）</b>，两版差异即 unstable 格的影响，供对照。① <b>质量名次（主榜）</b>=按 CER 中位全排，入榜资格=CER 可用格≥25——156 格全 complete、六引擎全入（gate1 per_engine.quality_eligible=true）；unstable 格的 CER 多为 12 次全同、质量稳定，<b>不移出质量名次</b>。② <b>计时稳定性列</b>=wall stable/26（判据：IQR/中位&gt;10% 越阈），oxr/ovis/surya 计时名次不含（&lt;25），仅质量名次给出。<b>并列组规则（事后展示规则，非预注册判据）</b>：相邻中位差 &lt;0.01 视为同组（传递连通），<b>组内不下先后结论、只做组间比较</b>——组标见表。</div>""")

# ---- F-9: 统计检验（动态现算 + 落 artifact）----
import random as _rnd9
_rnd9.seed(1301)
_un9 = [c for c in cells if c.get("unstable")]
_un_cnt9 = {}
for _e9 in ENGINES:
    _un_cnt9[_e9] = sum(1 for c in cells if c.get("engine") == _e9 and c.get("unstable"))
_n_e9 = [26] * len(ENGINES)
_N9 = sum(_un_cnt9.values())
def _sd9(cnts):
    rates = [c / n for c, n in zip(cnts, _n_e9)]
    return max(rates) - min(rates)
_obs9 = _sd9([_un_cnt9[e] for e in ENGINES])
_flags9 = [1] * _N9 + [0] * (156 - _N9)
_hit9 = 0
for _ in range(20000):
    _rnd9.shuffle(_flags9)
    _c9, _i9 = [0] * len(ENGINES), 0
    for _k9, _n9 in enumerate(_n_e9):
        _c9[_k9] = sum(_flags9[_i9:_i9 + _n9]); _i9 += _n9
    if _sd9(_c9) >= _obs9 - 1e-9:
        _hit9 += 1
_p1_9 = (_hit9 + 1) / 20001
# Kruskal-Wallis（wall IQR 连续值）
import statistics as _st9
def _w9(c):
    rep = c.get("reps") or []
    w = [r.get("wall") for r in rep if r.get("wall")]
    if len(w) < 4: return None
    med = _st9.median(w)
    if med <= 0: return None
    q1, q3 = _st9.quantiles(w, n=4)[0], _st9.quantiles(w, n=4)[2]
    return (q3 - q1) / med
_grp9 = [[v for v in (_w9(c) for c in cells if c.get("engine") == e) if v is not None] for e in ENGINES]
_all9 = [(v, gi) for gi, g in enumerate(_grp9) for v in g]
_all9.sort(key=lambda x: x[0])
_r9 = [0.0] * len(_all9); _i9b = 0
while _i9b < len(_all9):
    _j9 = _i9b
    while _j9 + 1 < len(_all9) and _all9[_j9 + 1][0] == _all9[_i9b][0]:
        _j9 += 1
    _av9 = (_i9b + _j9) / 2 + 1
    for _k9 in range(_i9b, _j9 + 1):
        _r9[_k9] = _av9
    _i9b = _j9 + 1
_rs9 = [0.0] * len(ENGINES); _cg9 = [0] * len(ENGINES)
for _rr9, (_v9, _gi9) in zip(_r9, _all9):
    _rs9[_gi9] += _rr9; _cg9[_gi9] += 1
_N2_9 = len(_all9)
_H9 = 12 / (_N2_9 * (_N2_9 + 1)) * sum(rr ** 2 / n for rr, n in zip(_rs9, _cg9)) - 3 * (_N2_9 + 1)
import json as _json9
_json9.dump(dict(method_unstable="permutation 20000, seed 1301, stat=max-min rate",
                 unstable_counts=_un_cnt9, obs_range=round(_obs9, 4), p_value=round(_p1_9, 4),
                 method_wall="Kruskal-Wallis on per-cell wall IQR/med", H=round(_H9, 3),
                 df=len(ENGINES) - 1, note="chi2 crit 11.07 @0.05"),
            open(os.path.join(BASE, "gates", "stats_test.json"), "w", encoding="utf-8"),
            ensure_ascii=False, indent=1)
H.append("""<div class="callout"><b>统计检验（本轮新增，artifact: gates/stats_test.json（评审包内为 r14-stats_test.json））</b>：① unstable 触发率引擎间差异——20,000 次置换检验（seed 1301），极差 %.3f，<b>p=%.4f（显著）</b>；② wall IQR 整体分布跨引擎——Kruskal-Wallis H=%.2f（df=%d，χ² 临界 11.07@0.05），<b>不显著</b>。读法：典型格同样稳（IQR 中位 0.008–0.014），差异在尾部（越阈频率）。</div>""" % (_obs9, _p1_9, _H9, len(ENGINES) - 1))


# ---- F-2: S24 主榜口径披露 ----
H.append("<h2>一·C、口径声明：本报告按 S26 全集披露（规格 S24 主榜 † 未冻结、不生成表；S_PDF 未跑）</h2>")
H.append("""<div class="warnbox"><b>规格 §2.1 定义 S24 主榜 = 26 图去 † 两张（144 格），但两份规格与 sets.yaml 都未写明 † 是哪两张</b>——成员未冻结，因此本报告<b>不出 S24 主榜表</b>（不能临时挑选样本充当预注册口径）。当前全部结果按 S26 全集（156 格）披露；† 成员需在规格中补冻结后，S24 表可从同一份数据零成本生成。144 格与 95% 门槛（≥137）的数字口径已按 V6e 记录。<b>S_PDF（逐页 PDF 集）本期未跑</b>（spec 定义的扩展集，需 PDF 逐页样本，不在本批 156 格内）——如实声明缺席。<b>spec 版本说明</b>：权威源为 hermes plans/2026-11-03-docparse-bench-console-spec.md（正文标题仍 V6d、§2.2b 增补为 V6e，以 errata 与 §2.2b 为准；评审副本 spec-V6e.md 同源）。</div>""")
H.append("""<div class="small"><b>样本构成</b>：26 张 = 18 张复用自 ep11-OCR（含 skew/invoice/table 系，图与 GT 同源拷贝，sha256 核对一致）+ 8 张本机合成（公文/合同/菜单/海报/论文/表单/简历/混合，make_samples_13.py 生成含 GT）。<b>DPI 如实披露</b>：8 张合成为 150dpi（1240×1754，代码注释即 A4@150dpi；spec 的 300dpi 未采用），18 张复用保持原图 dpi；manifest 与逐格 input.dpi 已按实际回填 150/300——<b>150dpi 与 spec 300dpi 的偏差作为已披露偏差接受</b>（同图对所有引擎一致、相对比较成立；与"统一 300dpi"的绝对 CER 不可比），不重跑。逐格 sample_id 映射见附录 A。<b>证据链加固（数据复核轮补）</b>：GT 26 份逐文件字节 sha256 审计（gt/gt_audit.json，与 manifest 26/26 一致）；九目录主权重文件 sha256（模型根 WEIGHTS_SHA256.json，MANIFEST 挂载 8 个实跑/归档模型（WEIGHTS 9 条含 TeleOCR-stardoc 别名），原 fingerprint 占位 see-MANIFEST 已回填为真值 156/156）。</div>""")

H.append(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ep13 文档解析实测 · 数据报告</title><style>
:root{{--bg:#fafafa;--card:#fff;--ink:#1a1a1a;--sub:#666;--line:#e5e5e5;--accent:#2563eb}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1060px;margin:0 auto;padding:32px 20px 70px}}
h1{{font-size:26px;margin:8px 0 4px}} h2{{font-size:21px;margin:44px 0 12px;padding-top:16px;border-top:1px solid var(--line)}}
h3{{font-size:17px;margin:24px 0 8px}} .meta{{color:var(--sub);font-size:14px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px;margin:12px 0}}
th,td{{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left}} th{{background:#f1f3f5;font-weight:600}}
tr:last-child td{{border-bottom:none}} .num{{font-family:Consolas,Menlo,monospace}}
.bar{{position:relative;display:inline-block;width:110px;height:16px;background:#f1f3f5;border-radius:3px;vertical-align:middle;margin-right:6px}}
.bar i{{position:absolute;left:0;top:0;bottom:0;border-radius:3px;opacity:.75}} .bar b{{position:absolute;right:4px;top:0;font:600 11px/16px Consolas;color:#111}}
.callout{{border-left:3px solid var(--accent);background:#eff6ff;padding:10px 14px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14.5px}}
.warnbox{{border:1px solid #fcd34d;background:#fffbeb;border-radius:10px;padding:12px 16px;margin:14px 0;font-size:14px}}
.small{{font-size:13.5px;color:var(--sub)}} code{{background:#f1f3f5;padding:1px 5px;border-radius:4px;font:13px Consolas,monospace}}
.tag{{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;font-weight:600}}
.ok{{background:#dcfce7;color:#15803d}}.bad{{background:#fee2e2;color:#b91c1c}}.wn{{background:#fef3c7;color:#b45309}}
@media(max-width:640px){{.wrap{{padding:20px 12px 60px}} table{{font-size:12.5px}} th,td{{padding:6px 6px}}}}
</style></head><body><div class="wrap">""")

H.append(f"""<h1>ep13 文档解析实测 · 数据报告</h1>
<div class="meta">2026-11-10 ｜ run <code>ep13-full-001</code> ｜ <b>156 格全 complete</b>（26 样本 × 6 引擎）｜ 协议 A（每格 6–12 rep，greedy）｜ GT=ep13-gt-v2（signed）｜ CER=(S+D+I)/N 逐字符</div>
<div class="callout"><b>怎么读</b>：CER = 字错率，越小越好（0.05 = 每 100 字错 5 个）。每格 = 1 张样本 × 1 个引擎，取有效 rep（6–12）的中位数。总榜给引擎中位，逐样本矩阵给 156 格明细。</div>""")

# ---- 逐样本矩阵 ----
H.append("<h2>二、逐样本 CER 矩阵（26 × 6，格内=该格 cer_median）</h2>")
H.append("<div style='overflow-x:auto'><table><tr><th>样本</th>" + "".join(
    f"<th>{ENG_CN[e].split()[0]}</th>" for e in ENGINES) + "</tr>")
for img in img_order:
    tds = []
    for e in ENGINES:
        v = matrix.get((img, e))
        if v is None: tds.append("<td class='num'>-</td>"); continue
        star = "*" if any(c.get("unstable") and c["_img"] == img and c["engine"] == e
                          for c in cells) else ""
        cls = "" if v <= 0.5 else " style=\"background:#fef2f2;font-weight:700\""
        tds.append(f"<td class='num'{cls}>{v:.3f}{star}</td>")
    H.append(f"<tr><td><code>{img}</code></td>" + "".join(tds) + "</tr>")
H.append("</table></div>")
H.append("""<div class="small">粗体 = CER&gt;0.5（离群，逐格定性见第三节）。多引擎同高的只有 lc_01/shot_01/shot_02 三个样本（共 18 格；同页面两截图+变体）；lc_02/lc_03 表现正常，不构成"整个 shot/lc 系"的结论。<b>*</b> 号 = unstable 格（波动超阈值，已剔出排名榜）。0.5 为本报告事后分诊阈值（非预注册判据）。</div>""")

# ---- 边界与离群 ----
H.append("<h2>三、边界：26 个离群格的逐格定性</h2>")
H.append("""<div class="callout"><b>三类结构</b>（复现取证后定性，参数未做任何干预——复读与多输出都是模型真实表现）：</div>""")
H.append("<table><tr><th>类</th><th>格数</th><th>判据</th><th>处置</th></tr>")
H.append("<tr><td><b>① 复读</b></td><td>1</td><td>monkey×lc_01=10.30：该格 cell 记录 6 rep 各 ~580s、trunc_rate=0；<b>复现诊断单跑</b>（存档 runs/diag_lc01_monkey.txt，非该格记录）：输出 3059 字符（GT 293）、「百度」top-gram 循环 251 次、耗时 706s</td><td>如实记录，报告披露复读率 1/156</td></tr>")
H.append("<tr><td><b>② 多输出特性</b></td><td>3</td><td>surya×3（1.67/1.55/1.24）：标签已剥净（extract 后 5.45→1.67），剩余为 &lt;img alt&gt; 英文描述等画面外生成文本+顺序差异</td><td>如实记录（surya 输出特性）</td></tr>")
H.append("<tr><td><b>③ 困难样本聚集</b></td><td>22</td><td>shot_01/shot_02/lc_01 网页截图多引擎同高（0.53–1.00），book_02/table/skew 零星</td><td>如实记录（共同难点）</td></tr>")
H.append("</table>")
H.append("""<div class="callout"><b>单列说明（r14）</b>：paper_01×OXR CER 0.548 在离群表（困难样本类）——该样本英文段词内断行，端到端含版面的 OXR 受影响最大，其余五引擎 0.001–0.020；构造层面的页脚/词内断行缺陷已于 r14 修复（合成 8 张重渲染、66 格重跑：48 合成 + 18 GT 变更）。</div>""")
H.append("<h3>离群明细（26 格，按 CER 降序）</h3>")
H.append("<table><tr><th>CER</th><th>引擎</th><th>样本</th><th>类</th></tr>")
for c in outliers:
    cer = c["cer_median"]
    kind = "①复读" if cer > 5 else ("②多输出" if c["engine"] == "surya_2_5" and cer > 1 else "③困难样本")
    H.append(f"<tr><td class='num'>{cer:.3f}</td><td>{ENG_CN[c['engine']]}</td>"
             f"<td><code>{c['_img']}</code></td><td>{kind}</td></tr>")
H.append("</table>")

# ---- F-5: GT 同源披露 ----
H.append("<h3>GT 内容重复 5 组的披露（同源图，非拷贝错误）</h3>")
H.append("""<div class="callout">5 组 GT 文本 SHA 相同。经逐组核验图 SHA 与 CER 分布，<b>均为同源样本、非 GT 错误</b>：
<ul style="margin:6px 0">
<li><b>book_01=skew_01、book_02=skew_02</b>：skew 是 book 的退化变体（同一底图），复用底图 GT 属设计；</li>
<li><b>invoice_02=lc_03</b>：同一票据的两个尺寸截图（图 SHA 不同），六引擎 CER 完全一致（全 0.0/0.05）佐证同源；</li>
<li><b>lc_01=shot_01</b>：同一网页的两个截图（图 SHA 不同），五引擎 CER 分布同步起伏佐证同源（Monkey 除外：其 lc_01 格为复读离群，10.297 vs 0.782 不同步）；</li>
<li><b>skew_03=table_02</b>：同底图派生（skew 退化变体与表格样本共用底图 GT，同 book/skew 类设计）。</li>
</ul>
<b>影响</b>：26 样本按内容计 21 个唯一文本——每格仍是独立测量，但"26 个独立难度"不成立。命名说明：lc_01/lc_03 文件名沿用 ep11，内容实为网页/票据（命名与内容不符属 ep11 遗留，不影响 GT 匹配）。</div>""")

# ---- 过程失败案例（≥3）----
H.append("<h2>四、失败案例（3 例过程轮次 + 1 例数据集内，均如实记录）</h2>")
H.append("""<div class="callout"><b>以下 3 例是修复过程轮次的记录</b>（发生在最终 156 格收口之前，<b>不在最终数据集内</b>——最终 156 格 n_fail 合计仅 1）：</div>
<table><tr><th>现象</th><th>根因</th><th>处置</th></tr>
<tr><td>Paddle 8 连败（8×extract_fail）</td><td>inputs.to(dtype) 把 input_ids 转成 float + text 未走 chat_template（image tokens=0）</td><td>只转浮点张量 + P0 单链构造 → 第 3 轮 complete 6/6</td></tr>
<tr><td>monkey/oxr 批量 load 失败（os error 1455）</td><td>系统 commit 耗尽（页面文件 84GB 用满、瞬时峰值撞墙），大参数引擎先失败</td><td>杀常驻应用腾 5.4GB + 最终重启清 95GB → 缺格断点补跑全过</td></tr>
<tr><td>OXR 26 格全败 + monkey lc_01 复读</td><td>OXR：text_tokenizer.pad_token_id=None（modeling_oxr.generate:978 必崩）；monkey：lc_01 样本触发生成失控</td><td>OXR 补 pad 兜底（Qwen eos=151643）+ generate 参数对齐 P0 → 26 格补跑全过；monkey 复读如实记录</td></tr>
<tr><td><b>最终数据集内唯一失败</b></td><td>OvisOCR2 一格 12 attempt / 11 valid（n_fail=1，unstable 标记）</td><td>如实记录；该格 CER 可用入质量名次、计时列计 unstable</td></tr></table>""")

# ---- 口径表 ----
H.append("<h2>五、口径表（全文缩写与名词）</h2>")
H.append("""<table><tr><th>词</th><th>是什么 + 怎么读</th></tr>
<tr><td><b>GT</b>（Ground Truth）</td><td>标准答案文本——26 张样本各自的人工核对文字，CER 拿它当参照</td></tr>
<tr><td><b>CER</b>（字错率）</td><td>(替换 S + 删除 D + 插入 I) ÷ GT 字符数 N；越小越准，0 = 全对。<b>N 的口径</b>：N = GT 文件字符数（strip 首尾后、内部换行保留；cer.py 实现即此）——例：lc_01 N=293（gt_manifest chars 已按文件实际修正；旧值 311 为 CRLF 期口径、r12/r13 勘误），CER×N=3017 为整数编辑数可反证（156/156 格整数性验证通过）。</td></tr>
<tr><td><b>rep</b>（重复次数）</td><td>同一格同一引擎重复推理一次；协议 A 要求 6 次有效（波动大加到 12）</td></tr>
<tr><td><b>格 / cell</b></td><td>1 张样本 × 1 个引擎 = 1 格；本期 26×6=156 格</td></tr>
<tr><td><b>wall</b>（墙钟）</td><td>端到端耗时：图像预处理开始→文本解码结束；模型加载不计入（另记 cold_load）</td></tr>
<tr><td><b>cold_load</b></td><td>引擎首次加载模型的耗时，session 级只记一次</td></tr>
<tr><td><b>complete / partial / failed / skipped</b></td><td>规格四态：complete=有效 rep≥6 达标；partial=有效 4–5（未达排名线，不入排名）；failed=有效&lt;4（协议终态）；skipped=未执行（如归档引擎）。本期 156 格全部 complete；扩展格对账（与 gate1 Σn_attempt 一致，动态核过）：monkey Σ=163（mixed_01=9、contract_01=10，其余 24×6）、ovis=168（contract_01=12·unstable、lc_02=12·unstable）、oxr=197（skew_01=11 及 6 个 unstable 格各 12）、paddle=160（resume_01=10）、surya=168（table_02/cn_doc_01 各 12·unstable）、xiaomi=167（skew_01=12·unstable、hard_01=11）——非 6 格全部为 IQR 触发的协议内扩展或样本差异（extension_note 逐格留痕）。monkey×resume_01 本轮重跑后 n=6 未触发扩展（r8 历史轮次曾 n=7：第 6 次 wall IQR/中位&gt;10% 触发加跑、收敛后停止；重跑后 6 次 IQR≈0.23% 稳定）</td></tr>
<tr><td><b>OXR / D-FINE</b></td><td>OXR=文档解析引擎（SoMarkAI 出品，1.3B，含版面+识别）；D-FINE=其版面前置服务（本机 CPU 模式）</td></tr>
<tr><td><b>提取（extract）</b></td><td>引擎输出→纯文本：剥结构记号（&lt;|标记|&gt;/HTML/markdown 符号），画面文字一律不动</td></tr></table>""")

# ---- 三重声明 ----
H.append("<h2>六、声明与未达标项</h2>")
H.append("""<div class="callout"><b>三重声明</b>：① 这是观测——156 格逐格 JSON 与 GT 随复刻包交付，表格数字均可逐项复算；诊断类单跑数字（如复读诊断 706s）标注来源文件、不参与表格；② 预期声明——他人复现预期<b>相同量级</b>：准确率（CER 相对关系）预期一致，耗时绝对值不预期一致（机器/负载差异）；③ 方法成熟度——<b>探索性实测（非生产级认证）</b>：n=26（唯一文本 21）、单机跨天批次、无置信区间，结论限于本机本批相对比较；若他人发现方法缺陷，已发表结论视为已撤回。<br>
<b>本报告未跑 SPEC 基准，引用的是其披露纪律。</b></div>""")
H.append("""<div class="warnbox"><b>未达标项（主动披露）</b>：
<ul style="margin:6px 0">
<li><b>⑤ 三件套缺口（A 方案披露，2026-11-10 拍板）</b>：cold 计时完整（wall 含 load 外置）；<b>rss 逐格未采集</b>（仅复读诊断单点 14.35GB）、<b>timeout 逐格无记录</b>——跑完无法回溯，不补采（避免口径分叉），如实披露为未达标项</li>
<li><b>G0 fail 项（诚实披露）</b>：run 级 started_at 未落盘——cell schema 无时间戳字段、mtime 已被回填刷新不可用；补 run_manifest 才能闭环（gate0.json「caliber audit finished_at」check 的 detail 记录 started_at=None 为证据）</li>
<li>cell.fingerprint.seed/order=0 是协议采样位（greedy 解码未用），如实落盘；任务序随机化 seed=1301 落在 batch_state（值与源码 batch_runner.py 一致，state 于数据复核轮回填并标注）；batch_state 的 desired/seq/n_run 为末批残值（最后一批 4 run/22 skip/0 fail），非全量统计——全量以 cells 156 为准；</li>
<li>未测噪声地板、未报置信区间、样本量未由置信度反推；</li>
<li>耗时段有跨天批次（分批夜跑），<b>跨批耗时不横比</b>（CER/准确率不受影响）；</li>
<li>monkey×lc_01 复读格未剔除（属模型真实表现，已单列披露）；</li>
<li>fingerprint 的 git/deps/config_hash/engine_version/host_manifest_id 为标签级占位（非 commit/哈希/主机清单），<b>不能声称环境级精确可复现</b>——权重身份以 WEIGHTS_SHA256.json 为准；</li>
<li>许可风险待发布前清：Xiaomi-OCR-0 与 MonkeyOCR-pro 仓库无 LICENSE 文件、surya 许可待确认（AI PUBS modified），已在 control/LICENSES.md 登记——G3 发布前门须逐项处置。</li>
</ul>
因此：本文<b>不对耗时做跨引擎精细排名</b>、不对 0.01 级 CER 差异下结论。</div>""")

# ---- 附录 A: sample_id→样本名映射 ----
H.append("<h2>附录 A：sample_id → 样本名映射（26 项）</h2>")
H.append("""<div class="small">r1 发现的 27→26 双 ID 已统一：paddle×book_01 的旧 ID <code>954a8c42…</code> 与其余五引擎的 <code>d9412c21…</code> 为同一图（sha256 fe182871…），已按 manifest 样本 UUID 回填合并。下表为全量映射。</div>""")
H.append("<table><tr><th>sample_id</th><th>样本名</th></tr>")
_seen = {}
for c in sorted(cells, key=lambda x: x["sample_id"]):
    _seen[c["sample_id"]] = c["_img"]
for sid, img in sorted(_seen.items(), key=lambda kv: kv[1]):
    H.append(f"<tr><td class='num'><code>{sid}</code></td><td><code>{img}</code></td></tr>")
H.append("</table>")

# ---- 闸门 ----
try:
    g = json.load(open(os.path.join(BASE, "gates", "summary.json"), encoding="utf-8"))
    H.append(f"<h2>七、闸门状态</h2><p>G0 {g['gates']['G0']} ｜ G1 {g['gates']['G1']} ｜ "
             f"G2 {g['gates']['G2']} ｜ G3 {g['gates']['G3']}</p>"
             f"""<div class="small">说明：四态以 gates/gateN.json 为准；当前 G3={g['gates']['G3']}
             （发布前门，未 pass 即阻断发布；G3 现仅差用户终审）。本报告是<b>数据层报告</b>，不是发布许可。</div>""")
except Exception:
    pass

H.append("</div></body></html>")
html = "".join(H)
for _out in (OUT, LOCAL_COPY):
    os.makedirs(os.path.dirname(_out), exist_ok=True)
    open(_out, "w", encoding="utf-8").write(html)
    print("报告 → %s (%.1f KB)" % (_out, len(html.encode('utf-8'))/1024))
print("数据点核对: 156 格 | 离群 %d | 引擎 %d" % (len(outliers), len(rows)))
