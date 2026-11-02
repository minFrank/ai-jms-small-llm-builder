# -*- coding: utf-8 -*-
"""收缩：删除 ep68-87（20 期档位占位）+ ep88-102 重编号为 ep68-82 + 日期前移 147 天
安全前提已核：articles 表无 ep68+ 记录、本地成稿无 ep68+、全部 planned 占位
备份：admin.db.bak-vertical
"""
import sqlite3, pathlib, time, datetime as dt
from collections import Counter

DB = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db")
SHIFT = 147   # 21 周
ts = time.strftime("%Y-%m-%dT%H:%M:%S")

con = sqlite3.connect(str(DB), timeout=30)
try:
    cur = con.cursor()
    before_n = cur.execute("SELECT COUNT(*) FROM series_plans WHERE brand='local-ai'").fetchone()[0]
    del_titles = cur.execute("""SELECT episode,title FROM series_plans
                                WHERE brand='local-ai' AND episode BETWEEN 68 AND 87
                                ORDER BY episode""").fetchall()
    print("删前总行 %d | 待删 %d 行" % (before_n, len(del_titles)))
    print("待删标题（全部占位）:")
    uniq = Counter(t for _, t in del_titles)
    for t, c in uniq.items():
        print("   %s ×%d" % (t, c))

    # ---- 1) 删除 ----
    cur.execute("DELETE FROM series_plans WHERE brand='local-ai' AND episode BETWEEN 68 AND 87")
    print("\n删除 %d 行" % cur.rowcount)

    # ---- 2) 重编号 88-102 -> 68-82 ----
    rows = cur.execute("""SELECT id, episode, publish_date FROM series_plans
                          WHERE brand='local-ai' AND episode BETWEEN 88 AND 102
                          ORDER BY episode""").fetchall()
    print("待重编号 %d 行" % len(rows))
    for rid, ep, d in rows:
        new_ep = ep - 20
        new_id = "sp_ep%02d" % new_ep if rid.startswith("sp_ep") else rid
        nd = ""
        if d:
            nd = (dt.date.fromisoformat(d) - dt.timedelta(days=SHIFT)).isoformat()
        cur.execute("""UPDATE series_plans SET episode=?, id=?, publish_date=?, updated_at=?
                       WHERE brand='local-ai' AND episode=?""",
                    (new_ep, new_id, nd, ts, ep))

    # ---- 3) notes 留痕 ----
    for rid, ep, d in rows:
        new_ep = ep - 20
        row = cur.execute("SELECT notes FROM series_plans "
                          "WHERE brand='local-ai' AND episode=?", (new_ep,)).fetchone()
        old = (row[0] if row else "") or ""
        add = ("2026-10-27 收缩：原 ep%d（档位占位段 ep68-87 已删除 20 期）"
               "重编号为 ep%d，日期前移 %d 天（%.0f 周）以保持每周二节奏。" % (ep, new_ep, SHIFT, SHIFT/7))
        if "收缩：原 ep" in old:
            continue
        cur.execute("UPDATE series_plans SET notes=?, updated_at=? "
                    "WHERE brand='local-ai' AND episode=?",
                    ((old + " | " + add).strip(" |"), ts, new_ep))
    con.commit()
    print("已提交")

    # ---- 复校验 ----
    rows2 = cur.execute("""SELECT episode, id, title, publish_date, vertical, status
                           FROM series_plans WHERE brand='local-ai' ORDER BY episode""").fetchall()
    print("\n=== 复校验 ===")
    print("  总行 %d（删前 %d，应 -20）" % (len(rows2), before_n))
    eps = [r[0] for r in rows2]
    print("  号位唯一:", len(set(eps)) == len(eps))
    print("  号序连续 1..%d:" % len(eps), sorted(eps) == list(range(1, len(eps) + 1)))
    print("  板块分布:", dict(Counter(r[4] for r in rows2)))
    print("  status  :", dict(Counter(r[5] for r in rows2)))
    dated = [(r[0], r[3]) for r in rows2 if r[3]]
    bad, prev = [], None
    for ep, d in dated:
        if prev and d < prev[1]: bad.append((prev[0], prev[1], ep, d))
        prev = (ep, d)
    print("  有日期 %d | 倒挂 %d 处（应 2，均为已知）" % (len(dated), len(bad)))
    for x in bad: print("     ep%s %s -> ep%s %s" % x)
    print("\n  末尾 6 期:")
    for r in rows2[-6:]:
        print("     ep%-4d %-11s %-10s %-9s %s" % (r[0], r[3] or "—", r[4], r[5], (r[2] or "")[:44]))
    print("\n  衔接处 ep66/67/68/69:")
    for r in rows2:
        if r[0] in (66, 67, 68, 69):
            print("     ep%-4d %-11s %-10s %s" % (r[0], r[3] or "—", r[4], (r[2] or "")[:44]))
finally:
    con.close()
