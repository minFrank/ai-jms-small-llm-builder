# -*- coding: utf-8 -*-
"""从 admin.db.bak-del-shells 精确还原被删的 31 期（只插缺失行，不动现有 51 行）"""
import sqlite3, time
from collections import Counter

CUR = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
BAK = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db.bak-del-shells"

c = sqlite3.connect(CUR, timeout=30)
b = sqlite3.connect(BAK, timeout=30)
try:
    cols = [r[1] for r in c.execute("PRAGMA table_info(series_plans)")]
    ei = cols.index("episode")
    cur_rows = {r[ei]: r for r in c.execute(
        "SELECT * FROM series_plans WHERE brand='local-ai'").fetchall()}
    bak_rows = {r[ei]: r for r in b.execute(
        "SELECT * FROM series_plans WHERE brand='local-ai'").fetchall()}
    missing = sorted(set(bak_rows) - set(cur_rows))
    print("当前 %d 行 | 备份 %d 行 | 待还原 %d 行" % (len(cur_rows), len(bak_rows), len(missing)))

    ph = ",".join("?" * len(cols))
    n = 0
    for e in missing:
        c.execute("INSERT INTO series_plans (%s) VALUES (%s)" % (",".join(cols), ph), bak_rows[e])
        n += 1
    c.commit()
    print("已插回 %d 行\n" % n)

    rows = c.execute("""SELECT episode, title, publish_date, vertical, status
                        FROM series_plans WHERE brand='local-ai' ORDER BY episode""").fetchall()
    print("=== 复校验 ===")
    print("  总行 %d（应 82）" % len(rows))
    eps = [r[0] for r in rows]
    print("  号位唯一:", len(set(eps)) == len(eps))
    print("  号序连续 1..82:", sorted(eps) == list(range(1, 83)))
    print("  空壳数:", sum(1 for r in rows if "选题运行时确定" in (r[1] or "")))
    print("  板块分布:", dict(Counter(r[3] for r in rows)))
    print("  status  :", dict(Counter(r[4] for r in rows)))
    dated = [(r[0], r[2]) for r in rows if r[2]]
    bad, prev = [], None
    for ep, d in dated:
        if prev and d < prev[1]: bad.append((prev[0], prev[1], ep, d))
        prev = (ep, d)
    print("  有日期 %d | 倒挂 %d 处（应 2）" % (len(dated), len(bad)))
    for x in bad: print("     ep%s %s -> ep%s %s" % x)
    print("\n  与备份逐字段比对（排除 updated_at）:")
    b2 = sqlite3.connect(BAK, timeout=20)
    try:
        bak2 = {r[ei]: r for r in b2.execute("SELECT * FROM series_plans WHERE brand='local-ai'").fetchall()}
    finally:
        b2.close()
    cur2 = {r[ei]: r for r in c.execute("SELECT * FROM series_plans WHERE brand='local-ai'").fetchall()}
    skip = {"updated_at"}
    idx = [i for i, nm in enumerate(cols) if nm not in skip]
    diff = [e for e in sorted(set(cur2) & set(bak2))
            if tuple(cur2[e][i] for i in idx) != tuple(bak2[e][i] for i in idx)]
    print("     不一致行:", diff or "0 行 ✅ 完全还原")
    print("\n  还原回来的 31 期:")
    for e in missing:
        r = cur2[e]
        print("     ep%-4d %-11s %-12s %s" % (r[ei], r[cols.index("publish_date")] or "—",
              r[cols.index("vertical")], (r[cols.index("title")] or "")[:40]))
finally:
    c.close(); b.close()
