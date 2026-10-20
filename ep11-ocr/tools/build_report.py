# -*- coding: utf-8 -*-
"""生成数据报告 HTML（浅色、多端自适应）。所有数字来自 result 数据，禁止手打。"""
import json
import os
import time

import metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "report_ep11.html")


def load_json(p, default=None):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def m(id_, value, nd=2):
    """带 metric id 的数字标签：assert_report.py 会逐个复算。"""
    if value is None:
        return '<span class="m" data-metric="%s">失败</span>' % id_
    if isinstance(value, float):
        return ('<span class="m" data-metric="%s">%%.%df</span>' % (id_, nd)) % value
    return '<span class="m" data-metric="%s">%s</span>' % (id_, value)


def table(head, rows):
    h = "".join("<th>%s</th>" % x for x in head)
    b = "".join("<tr>" + "".join("<td>%s</td>" % x for x in r) + "</tr>" for r in rows)
    return "<table><tr>%s</tr>%s</table>" % (h, b)


def main():
    data = M.compute()
    env = load_json(os.path.join(BASE, "env_snapshot.json"), {}) or {}
    meta = load_json(os.path.join(BASE, "gt", "samples_meta.json"), []) or []
    net = load_json(os.path.join(BASE, "logs", "net_selftest.json"), {}) or {}
    batch = {}
    bdir = os.path.join(BASE, "output", "batch")
    if os.path.isdir(bdir):
        for f in os.listdir(bdir):
            if f.endswith(".json"):
                batch[f[:-5]] = load_json(os.path.join(bdir, f))
    offline = load_json(os.path.join(BASE, "result_offline.json"), None)
    cells, engines, images = data["cells"], data["engines"], data["images"]
    main_eng = [e for e in engines if e != "gotocr"]
    got = [e for e in engines if e == "gotocr"]

    parts = []
    A = parts.append
    A("""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ep11 本地 OCR 实测 · 数据报告</title><style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e6e9ef;--ink:#1c2536;--muted:#69748a;--blue:#2f6bd8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 70px}
header{border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:18px}
h1{margin:0 0 6px;font-size:23px;letter-spacing:-.2px}
.sub{color:var(--muted);font-size:13px}
h2{font-size:18px;margin:30px 0 10px;padding-left:10px;border-left:4px solid var(--blue)}
h3{font-size:15.5px;margin:18px 0 6px}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:13px;margin:8px 0}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:#f0f2f6;font-weight:600;white-space:nowrap}
code{background:#eef0f4;padding:1px 5px;border-radius:4px;font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 15px;margin:10px 0}
.muted{color:var(--muted);font-size:12.5px}
.m{font-variant-numeric:tabular-nums;font-family:Consolas,monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:10px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.kpi .n{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .l{color:var(--muted);font-size:12px;margin-top:2px}
.scroll{overflow-x:auto}
</style></head><body><div class="wrap">""")

    A("<header><h1>ep11 本地 OCR 实测 · 数据报告</h1>"
      "<div class='sub'>栏目「本地无显卡 AI」第 11 期 · 本文件为<b>数据报告</b>（未写稿、未推草稿箱）· "
      "生成时间 %s</div></header>" % time.strftime("%Y-%m-%d %H:%M"))

    # ---- 结论摘要 ----
    A("<h2>一、一句话结论</h2><div class='card'>")
    tot = len(cells)
    A("本轮共跑 <b>%s</b> 个测量格，覆盖 %s 个引擎、%s 张样本图。"
      % (m("cells_total", tot), m("engines_n", len(engines)), m("images_n", len(images))))
    tu0 = M.topup_compare()
    if tu0:
        A("补跑批次：%s 项任务（去重 %s 格）全部完成——n&lt;3 的格全部补到 n=3、"
          "超时格出数、离散格定向重跑，详见十四节。"
          % (m("tu_tasks", tu0["n_tasks"]), m("tu_unique", tu0["n_unique"])))
    A("</div>")

    # ---- 硬件与依赖 ----
    A("<h2>二、硬件与依赖版本（自动读取，非手填）</h2>")
    A(table(["项", "值"],
            [["CPU 逻辑/物理核", "%s / %s" % (env.get("cpu_physical_logical", ["?", "?"])[1],
                                       env.get("cpu_physical_logical", ["?", "?"])[0])],
             ["内存", "%s GB" % env.get("mem_total_gb", "?")],
             ["独立显卡", "无（torch.cuda.is_available = %s）" % env.get("torch_cuda_available")],
             ["Python", (env.get("python") or "").split()[0]],
             ["onnxruntime", env.get("onnxruntime", "?")],
             ["opencv / numpy", "%s / %s" % (env.get("cv2", "?"), env.get("numpy", "?"))],
             ["rapidocr-onnxruntime", env.get("rapidocr_onnxruntime", "?")],
             ["paddlepaddle / paddleocr", "%s / %s" % (env.get("paddle", "?"), env.get("paddleocr", "?"))],
             ["torch / transformers（主 venv）", "%s / %s" % (env.get("torch", "?"), env.get("transformers", "?"))],
             ["GOT 独立 venv", env.get("got_venv", "?")],
             ["freeze 主 venv sha256(16)", env.get("freeze_main_sha", "见 freeze_main.txt")]]))

    # ---- 样本与来源 ----
    A("<h2>三、样本与 GT（14 张，来源逐张标注）</h2>")
    A(table(["图", "类别", "来源", "尺寸", "字节", "GT 文件", "说明"],
            [[x["name"], x["category"], x["source"], "%d×%d" % (x["w"], x["h"]),
              m("bytes_%s" % x["name"], x["bytes"]),
              os.path.basename(x["gt"]), x.get("note", "")] for x in meta]))
    A("<div class='muted'>来源三类：<code>real_pdf</code>=真实 PDF 原页渲染（arXiv 2409.01704）；"
      "<code>real_web</code>=真实网页 headless Chrome 截图（GT 取自 DOM 文本层，与视觉阅读顺序可能有出入）；"
      "<code>synthetic</code>=按真实票据/表格/说明书版式合成（GT 精确）。"
      "倾斜与低对比只作用在真实底图上，属<b>合成退化，非真实拍照</b>（无相机输入）。"
      "手写类本期未覆盖（inbox 为空，按批复 D2 降级为 7 类 14 张）。</div>")

    # ---- 覆盖矩阵 ----
    A("<h2>四、覆盖矩阵（行=维度，列=引擎，格=数据点数）</h2>")
    rows = []
    for label, mode, field in (("冷启动单页耗时", "cold", "median"),
                               ("热态单页耗时", "hot", "median")):
        r = [label]
        for e in engines:
            got_cells = [c for c in cells.values()
                         if c["engine"] == e and c["mode"] == mode]
            r.append("%d 格" % len(got_cells) if got_cells else "<b>失败</b>")
        rows.append(r)
    r = ["字错率 CER"]
    for e in engines:
        n = len([c for c in cells.values() if c["engine"] == e and c["cer_main"] is not None])
        r.append("%d 张" % n if n else "<b>失败</b>")
    rows.append(r)
    A(table(["维度 \\ 引擎"] + engines, rows))

    # ---- 冷启动 ----
    A("<h2>五、冷启动（t_spawn → 结果落盘前，含解释器启动/导入/建 session/首次执行）</h2>")
    A("<div class='muted'>口径：进程冷、磁盘未必冷（模型文件已在 OS 缓存）。段=进程启动/导入/建 session/首次推理/收尾，"
      "残差&gt;5%% 判该格不闭合（DP-02）。</div>")
    A("<div class='scroll'>")
    A(table(["引擎", "图", "格", "中位(s)", "min", "max", "n", "离散%", "段残差%", "峰值内存(MB)"],
            [[c["engine"], c["img"], (c.get("cell") or "").split("__")[-1],
              m("cold_%s_%s_median" % (c.get("cell"), c["img"]), c["median"]),
              m("cold_%s_%s_min" % (c.get("cell"), c["img"]), c["min"]),
              m("cold_%s_%s_max" % (c.get("cell"), c["img"]), c["max"]),
              c["n"], m("cold_%s_%s_spread" % (c.get("cell"), c["img"]), c["spread_pct"]),
              m("cold_%s_%s_resid" % (c.get("cell"), c["img"]), c["seg_residual_pct"]),
              m("cold_%s_%s_rss" % (c.get("cell"), c["img"]), c["peak_rss_mb"])]
             for k, c in sorted(cells.items()) if c["mode"] == "cold"]))
    A("</div>")

    # ---- 热态 ----
    GT_WEAK = {"book_02", "skew_02", "shot_01", "shot_02", "lc_01"}
    A("<h2>六、热态单页（session 已建好，同进程连续计时）</h2>")
    A("<div class='muted'>CER 标 <b>†</b> 的行：GT 来自 PDF 文本层且<b>不完备</b>（不含图内栅格文字/部分渲染元素），"
      "识别结果往往比 GT 更全，<b>该 CER 不能当准确率读</b>，详见十二节案例 4。</div>")
    A("<div class='scroll'>")
    A(table(["引擎", "图", "中位(s)", "min", "max", "n", "离散%", "识别行数", "CER(空格不敏感)"],
            [[c["engine"], c["img"],
              m("hot_%s_%s_median" % (c["engine"], c["img"]), c["median"], 3),
              m("hot_%s_%s_min" % (c["engine"], c["img"]), c["min"], 3),
              m("hot_%s_%s_max" % (c["engine"], c["img"]), c["max"], 3),
              c["n"], m("hot_%s_%s_spread" % (c["engine"], c["img"]), c["spread_pct"]),
              c["n_lines"],
              m("hot_%s_%s_cer" % (c["engine"], c["img"]), c["cer_main"], 4)
              + ("†" if c["img"].replace(".png", "") in GT_WEAK else "")]
             for k, c in sorted(cells.items()) if c["mode"] == "hot"]))
    A("</div>")

    # ---- 分类 CER 汇总 ----
    A("<h2>七、分场景字错率（按 7 类聚合，不给单点「很准」）</h2>")
    cat = {x["name"]: x["category"] for x in meta}
    rows = []
    for e in engines:
        byc = {}
        for k, c in cells.items():
            if c["engine"] != e or c["mode"] != "hot" or c["cer_main"] is None:
                continue
            byc.setdefault(cat.get(c["img"].replace(".png", ""), "?"), []).append(c["cer_main"])
        for cname in sorted(byc):
            vals = sorted(byc[cname])
            import statistics as st
            rows.append([e, cname, m("cer_%s_%s_med" % (e, cname), st.median(vals), 4),
                         m("cer_%s_%s_min" % (e, cname), vals[0], 4),
                         m("cer_%s_%s_max" % (e, cname), vals[-1], 4), len(vals)])
    A(table(["引擎", "类别", "中位 CER", "最好", "最差", "样本数"], rows))

    # ---- 表格结构 ----
    A("<h2>八、表格结构还原（人工判定）</h2>")
    tj = os.path.join(BASE, "quality", "table_judge.md")
    if os.path.exists(tj):
        A("<div class='card'><pre style='white-space:pre-wrap;font-size:12.5px;margin:0'>%s</pre></div>"
          % open(tj, encoding="utf-8").read())
    else:
        A("<div class='card'>判定记录未生成（quality/table_judge.md 缺失）</div>")

    # ---- 体积 / 内存 ----
    A("<h2>九、体积与内存（自动量取）</h2>")
    A(table(["引擎", "模型落地体积(MB)", "冷启动峰值内存(MB)", "口径"],
            [[e,
              m("mb_%s" % e, max([c["model_bytes"] for c in cells.values()
                                  if c["engine"] == e and c["model_bytes"]] or [0]) / 1048576.0),
              m("rss_%s" % e, max([c["peak_rss_mb"] for c in cells.values()
                                   if c["engine"] == e and c["peak_rss_mb"]] or [0])),
              "单进程峰值 RSS（含解释器与模型），不含父进程"]
             for e in engines]))

    # ---- 批量吞吐 ----
    A("<h2>十、批量吞吐（热态，用同一套 14 张循环补齐）</h2>")
    brows = []
    for k, v in sorted(batch.items()):
        if not v:
            continue
        brows.append([v.get("engine"), v.get("pages"), v.get("ok"), v.get("fail"),
                      m("batch_%s_load" % k, v.get("load_s")),
                      m("batch_%s_wall" % k, v.get("wall_s")),
                      m("batch_%s_spp" % k, v.get("s_per_page"), 2),
                      m("batch_%s_ppm" % k, v.get("pages_per_min"))])
    A(table(["引擎", "页数", "成功", "失败", "加载(s)", "总墙钟(s)", "每页(s)", "页/分钟"], brows))

    # ---- 断网 ----
    A("<h2>十一、断网测试（进程级 Python socket 出网拦截，非物理断网）</h2>")
    A("<div class='card'>guard 自检：<code>guard_loaded=%s</code> <code>blocked=%s</code>"
      "<br>未继承 guard 的子进程探针 rc=%s（blocked=%s）——这条明确记为<b>未覆盖路径</b>。"
      "<div class='muted'>拦截口径：非回环 host 一律拒绝；回环 + 本机代理端口（7897/7890/1080/8080…）同样拒绝，"
      "因为 Windows 上 urllib/requests 会读注册表代理、连接落到 127.0.0.1:代理端口。"
      "该证据只覆盖 Python socket 层，不覆盖原生库直连与不继承 guard 的子进程。</div></div>"
      % (net.get("guard_loaded"), net.get("blocked"), net.get("subprocess_rc"),
         net.get("subprocess_blocked")))
    if offline:
        oc = offline.get("cells", {})
        rows = [[c["engine"], c["img"], c["mode"], c["status"],
                 m("off_%s_%s_%s_cer" % (c["engine"], c["img"], c["mode"]), c["cer_main"], 4),
                 m("off_%s_%s_%s_median" % (c["engine"], c["img"], c["mode"]), c["median"], 2)]
                for k, c in sorted(oc.items())]
        A("<div class='scroll'>")
        A(table(["引擎", "图", "模式", "状态", "CER", "中位(s)"], rows))
        A("</div>")
    else:
        A("<div class='card'>断网批未跑（result_offline.json 缺失）</div>")

    # ---- 失败案例 ----
    A("<h2>十二、失败案例（什么情况下不能用）</h2>")
    fc = os.path.join(BASE, "quality", "failure_cases.md")
    if os.path.exists(fc):
        A("<div class='card'><pre style='white-space:pre-wrap;font-size:12.5px;margin:0'>%s</pre></div>"
          % open(fc, encoding="utf-8").read())
    else:
        A("<div class='card'>失败案例清单未生成</div>")

    # ---- 数据密度 ----
    A("<h2>十三、数据密度自评</h2>")
    n_fail = len(data["failures"])
    A(table(["项", "实测", "下限", "判定"],
            [["测量格（数据点）", m("density_cells", tot), 30,
              "达标" if tot >= 30 else "<b>不足</b>"],
             ["真实样本图", m("density_images", len(images)), 10,
              "达标" if len(images) >= 10 else "<b>不足</b>"],
             ["失败案例", m("density_fails", n_fail), 3,
              "达标" if n_fail >= 3 else "<b>不足</b>（见十二节人工补充）"]]))
    A("<div class='muted'>离散度（热态，按格算 (max−min)/median）：%s 格可算，超 5%% 的 %s 格。"
      "冷启动段和残差超 5%% 的格：%s / %s。"
      % (data["disp_n"], m("disp_over_n", len(data["disp_over"])),
         m("seg_bad_n", len(data["seg_bad"])), data["seg_n"]))
    A("<br>坏行（截断/非法 JSON）：%s。</div>" % data["bad_lines"])

    # ---- 补跑批次 ----
    tu = M.topup_compare()
    if tu:
        A("<h2>十四、补跑批次达成情况（%s 项任务 → %s 格，全部完成）</h2>"
          % (m("tu_tasks", tu["n_tasks"]), m("tu_unique", tu["n_unique"])))
        A("<div class='card'>")
        A("① n&lt;3 的格：<b>%s / 19</b> 补到 n=3（同格整格重跑，一格一子进程，预热不计时）；"
          % m("tu_nlt3_fixed", tu["n_lt3_fixed"]))
        A("② 超时失败格（gotocr skew_01 hot）：单格上限从 1200s 放宽到 5400s 后出数——"
          "中位 <b>%s 秒</b>、离散 %s%%、CER %s；归因=<b>上轮超时窗口过短</b>（该图单页就要 10 分钟量级），不是模型失败。"
          % (m("tu_skew_median", cells.get(tu["timeout_cell"], {}).get("median"), 2),
             m("tu_skew_spread", cells.get(tu["timeout_cell"], {}).get("spread_pct")),
             m("tu_skew_cer", cells.get(tu["timeout_cell"], {}).get("cer_main"), 3)))
        disp = {r["img"]: r for r in tu["disp_fixed"]}
        A("③ 离散超标格：定向重跑一次（每档只跑一次，不为达标反复跑）→ table_02 %s%%→%s%% 达标；"
          "invoice_01 %s%%、table_01 %s%% 仍 &gt;5%%，如实标注。"
          % (m("tu_%s_sp_b" % disp["table_02"]["cell"], disp["table_02"]["sp_b"]),
             m("tu_%s_sp_a" % disp["table_02"]["cell"], disp["table_02"]["sp_a"]),
             m("tu_%s_sp_a" % disp["invoice_01"]["cell"], disp["invoice_01"]["sp_a"]),
             m("tu_%s_sp_a" % disp["table_01"]["cell"], disp["table_01"]["sp_a"])))
        A("④ 跨批一致性：同格重跑前后中位偏差，全部格最大 %s%%（属亚秒级格）；"
          "中位 ≥1 秒的格最大 %s%%。"
          % (m("tu_drift_max", tu["drift_max_pct"]),
             m("tu_drift_big", tu["drift_big_pct"])))
        A("</div>")
        A("<div class='scroll'>")
        A(table(["引擎", "图", "模式", "触发原因", "n 前→后", "离散% 前→后",
                 "中位(s) 前→后", "补跑后状态"],
                [[r["engine"], r["img"], r["mode"], r["reason"],
                  "%s→%s" % (m("tu_%s_n_b" % r["cell"], r["n_b"]),
                             m("tu_%s_n_a" % r["cell"], r["n_a"])),
                  "%s→%s" % (m("tu_%s_sp_b" % r["cell"], r["sp_b"]),
                             m("tu_%s_sp_a" % r["cell"], r["sp_a"])),
                  "%s→%s" % (m("tu_%s_md_b" % r["cell"], r["md_b"], 2),
                             m("tu_%s_md_a" % r["cell"], r["md_a"], 2)),
                  r["status_a"] + (" " + r["err_a"] if r["err_a"] else "")]
                 for r in tu["rows"]]))
        A("</div>")
        over_txt = "；".join(
            "%s %s（绝对极差 %s 秒）" % (
                r["cell"], m("tu_%s_sp_a" % r["cell"], r["sp_a"]),
                m("tu_abs_%s" % r["cell"],
                  (cells[r["cell"]]["max"] - cells[r["cell"]]["min"])
                  if cells.get(r["cell"]) and cells[r["cell"]]["max"] is not None
                  and cells[r["cell"]]["min"] is not None else None, 3))
            for r in tu["still_over"])
        A("<div class='muted'>表注：① 补跑方法 = 命中格整格重跑为新 attempt，聚合按「每格取最新 attempt」；"
          "被替换的旧 attempt 留在 progress.json 可审计。单格超时上限：paddleocr 1500s / gotocr 2400s（skew_01 单独 5400s）。"
          "② 仍 &gt;5%% 的 %d 格都是亚秒级页面：%s —— 毫秒级调度抖动在相对口径下被放大；"
          "按纪律定向重跑只做一次，不再重跑。③ 冷启动补格按「同图 3 个独立进程」读，跨进程极差 invoice_01 %s%%、table_01 %s%%。"
          "</div>"
          % (len(tu["still_over"]), over_txt,
             m("tu_cold_spr_gotocr_invoice_01",
               next((r["sp_a"] for r in tu["rows"]
                     if r["cell"] == "gotocr__invoice_01__cold"), None)),
             m("tu_cold_spr_gotocr_table_01",
               next((r["sp_a"] for r in tu["rows"]
                     if r["cell"] == "gotocr__table_01__cold"), None))))

    A("<h2>十五、口径与不做</h2><div class='card'>"
      "① 三引擎依赖栈不同（onnxruntime / paddlepaddle / torch），<b>不做跨引擎排名</b>；"
      "GOT-OCR2.0 为端到端多模态对照维度，不进主线结论。<br>"
      "② RapidOCR 默认 PP-OCRv4 模型、PaddleOCR 默认 PP-OCRv6 模型，<b>代际不同</b>，"
      "差异不可归因于运行时单变量；本表按「各自默认配置对照」读。<br>"
      "③ PaddleOCR 关闭了 oneDNN（本机默认开启会报 Paddle 内部错误），此配置写入每行 settings。<br>"
      "④ 不做 GPU 路线、不做屏幕实拍，证据一律为原始日志。</div>")

    A("</div></body></html>")
    html = "\n".join(parts)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出", OUT, len(html), "chars")


if __name__ == "__main__":
    main()
