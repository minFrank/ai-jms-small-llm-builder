# -*- coding: utf-8 -*-
"""垂直板块重构 · 第一步：新增 vertical 字段并给 102 期打标签
用户 2026-10-27 决策：1 按建议（六板块，串场景并入小模型）2 库结构 A（vertical 字段）
                       4 按建议（55 占位重分配）5 文生视频不处理 6 优先补 L3
"""
import sqlite3, shutil, pathlib, time, json

DB = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db")
BAK = pathlib.Path(str(DB) + ".bak-vertical")
if not BAK.exists():
    shutil.copy2(DB, BAK)
    print("备份: %s (%.1f MB)" % (BAK.name, BAK.stat().st_size / 1048576))

# ---- 板块归属（人工核定；ep24 串场景并入 llm）----
LIVE = {
    "ocr":         [11, 12, 30],
    "asr":         [3, 9, 10, 28],
    "voice-clone": [2, 25, 41],
    "txt2img":     [4, 5, 6, 7, 8],
    "llm":         [1, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27,
                    29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47],
}
assign = {}
layer = {}
for v, eps in LIVE.items():
    for e in eps:
        assign[e] = v
        layer[e] = "live"

# ---- 占位段重分配 ----
for e in range(48, 52):                       # ep48-51 有具体选题，本就是小模型场景
    assign[e], layer[e] = "llm", "scenario"

order5 = ["ocr", "asr", "voice-clone", "txt2img", "llm"]
# ep52-67（16 期生活场景）→ L5 串场景层，均分到 5 个在营板块
for i, e in enumerate(range(52, 68)):
    assign[e], layer[e] = order5[i % 5], "L5"
# ep68-87（20 期档位）→ 小模型档位层
for e in range(68, 88):
    assign[e], layer[e] = "llm", "L2-tier"
# ep88-102（15 期失败边界）→ L3 边界层，均分 5 板块（每板块 3 期）
for i, e in enumerate(range(88, 103)):
    assign[e], layer[e] = order5[i % 5], "L3"

missing = sorted(set(range(1, 103)) - set(assign))
dup = len(assign)
print("归属: %d 行 | 缺 %s" % (dup, missing or "无"))

from collections import Counter
print("\n板块分布:", dict(Counter(assign.values())))
print("层分布  :", dict(Counter(layer.values())))

con = sqlite3.connect(str(DB), timeout=30)
try:
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(series_plans)")]
    if "vertical" not in cols:
        cur.execute("ALTER TABLE series_plans ADD COLUMN vertical TEXT")
        print("\n已新增列 vertical")
    else:
        print("\n列 vertical 已存在")

    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    # 打标签
    n = 0
    for e, v in assign.items():
        cur.execute("UPDATE series_plans SET vertical=?, updated_at=? "
                    "WHERE brand='local-ai' AND episode=?", (v, ts, e))
        n += cur.rowcount
    print("打标 %d 行" % n)

    # 占位段 notes 留痕（只追加一次）
    NOTE = ("2026-10-27 垂直板块重构：本行按用户决策归入 <{v}> 板块，层=<{l}>。"
            "占位选题动笔前定；板块归属已定，不再运行时决定。")
    for e, v in assign.items():
        if layer[e] == "live":
            continue
        row = cur.execute("SELECT notes FROM series_plans "
                          "WHERE brand='local-ai' AND episode=?", (e,)).fetchone()
        old = (row[0] if row else "") or ""
        if "垂直板块重构" in old:
            continue
        add = NOTE.format(v=v, l=layer[e])
        cur.execute("UPDATE series_plans SET notes=?, updated_at=? "
                    "WHERE brand='local-ai' AND episode=?",
                    ((old + " | " + add).strip(" |"), ts, e))
    con.commit()
    print("占位段 notes 留痕完成")

    # ---- 复校验 ----
    print("\n=== 复校验 ===")
    rows = cur.execute("""SELECT episode, vertical, title, publish_date, notes
                          FROM series_plans WHERE brand='local-ai' ORDER BY episode""").fetchall()
    print("  总行 %d | 有 vertical %d" % (len(rows), sum(1 for r in rows if r[1])))
    print("  板块分布:", dict(Counter(r[1] for r in rows)))
    no_v = [r[0] for r in rows if not r[1]]
    print("  无标签:", no_v or "无")
    # 号位/日期未被破坏
    print("  号位唯一:", len(set(r[0] for r in rows)) == len(rows))
    dated = [(r[0], r[3]) for r in rows if r[3]]
    bad, prev = [], None
    for ep, d in dated:
        if prev and d < prev[1]: bad.append((prev[0], prev[1], ep, d))
        prev = (ep, d)
    print("  有日期 %d | 倒挂 %d 处（应仍为 2，均为已知）" % (len(dated), len(bad)))
    for x in bad: print("     ep%s %s -> ep%s %s" % x)
finally:
    con.close()
