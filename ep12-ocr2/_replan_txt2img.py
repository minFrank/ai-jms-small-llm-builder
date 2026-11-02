# -*- coding: utf-8 -*-
"""方案A：ep4-8（文生图线）插进 2026-12-01 起，ep17+ 整体后移 5 周"""
import sqlite3, shutil, pathlib, time, datetime as dt

DB = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db")
BAK = pathlib.Path(str(DB) + ".bak-txt2img-replan")
if not BAK.exists():
    shutil.copy2(DB, BAK)
    print("备份: %s (%.1f MB)" % (BAK.name, BAK.stat().st_size / 1048576))
else:
    print("备份已存在:", BAK.name)

SHIFT = dt.timedelta(days=35)          # 5 周
NEW48 = ["2026-12-01", "2026-12-08", "2026-12-15", "2026-12-22", "2026-12-29"]

con = sqlite3.connect(str(DB), timeout=20)
try:
    cur = con.cursor()
    before = cur.execute(
        "SELECT episode, publish_date FROM series_plans WHERE brand='local-ai' ORDER BY episode"
    ).fetchall()
    bmap = dict(before)
    print("\n改前 ep4-8:", [(e, bmap.get(e)) for e in range(4, 9)])
    print("改前 ep17/27/47/102:", [(e, bmap.get(e)) for e in (17, 27, 47, 102)])

    # 1) ep17+ 整体后移 5 周
    moved = 0
    for ep, d in before:
        if ep >= 17 and d:
            nd = (dt.date.fromisoformat(d) + SHIFT).isoformat()
            cur.execute(
                "UPDATE series_plans SET publish_date=?, updated_at=? WHERE brand='local-ai' AND episode=?",
                (nd, time.strftime("%Y-%m-%dT%H:%M:%S"), ep))
            moved += 1
    print("\n后移 ep17+ : %d 行 (+35 天)" % moved)

    # 2) ep4-8 填 12 月
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    for i, ep in enumerate(range(4, 9)):
        cur.execute(
            "UPDATE series_plans SET publish_date=?, updated_at=? WHERE brand='local-ai' AND episode=?",
            (NEW48[i], ts, ep))
    print("ep4-8 排期:", NEW48)

    con.commit()
    print("已提交")

    # ---- 复校验 ----
    after = cur.execute(
        "SELECT episode, title, status, publish_date FROM series_plans "
        "WHERE brand='local-ai' ORDER BY publish_date, episode").fetchall()
    dated = [(e, d) for e, t, s, d in after if d]
    print("\n=== 复校验 ===")
    print("  已排期行: %d / 102" % len(dated))
    # 日期单调（按 episode 排）
    byep = cur.execute(
        "SELECT episode, publish_date FROM series_plans "
        "WHERE brand='local-ai' AND publish_date<>'' ORDER BY episode").fetchall()
    bad = []
    prev = None
    for ep, d in byep:
        if prev and d < prev[1]:
            bad.append((prev, (ep, d)))
        prev = (ep, d)
    print("  日期倒挂: %d 处" % len(bad))
    for a, b in bad[:8]:
        print("    ep%s %s  ->  ep%s %s" % (a[0], a[1], b[0], b[1]))
    # 关键行
    print("\n=== 改后关键行 ===")
    for e in [4, 5, 6, 7, 8, 13, 16, 17, 27, 47, 102]:
        r = cur.execute(
            "SELECT publish_date, title, status FROM series_plans "
            "WHERE brand='local-ai' AND episode=?", (e,)).fetchone()
        print("  ep%-4d %-11s %-9s %s" % (e, r[0] or "(空)", r[2], (r[1] or "")[:46]))
finally:
    con.close()
