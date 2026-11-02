# -*- coding: utf-8 -*-
"""ep4 三处修正（用户回「改」）：
1) series_plans.title  -> 成稿/线上真身标题
2) series_plans.status -> published
3) series_plans.publish_date -> 清空（12-01 是方案A留下的、前提已变）
备注注明群发日期待补。
方案 B 下只动 ep4 这 1 行；ep5-8 日期不变（12-08/12-15/12-22/12-29）。
"""
import sqlite3, time

DB = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
REAL_TITLE = "同一个 Stable Diffusion 1.5，四套引擎无显卡实测：谁能跑、谁最快"
NOTE = ("2026-10-27 用户确认本期已群发。原 2026-12-01 系方案A误置"
        "(前提为ep4-8全部未动笔,后经用户确认ep4已发布),已清空。"
        "★群发日期待用户补充(本号freepublish无权限,读不到已发表列表)。"
        "线上真身标题已由选题规划名「不买显卡,把文字画成图(本地文生图)」改为成稿标题。")

con = sqlite3.connect(DB, timeout=20)
try:
    cur = con.cursor()
    before = cur.execute(
        "SELECT title, status, publish_date, notes FROM series_plans "
        "WHERE brand='local-ai' AND episode=4").fetchone()
    print("改前: title=%r\n      status=%r\n      date=%r" % (before[0], before[1], before[2]))

    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    old_notes = before[3] or ""
    new_notes = old_notes if "群发日期待用户补充" in old_notes else (
        (old_notes + " | " + NOTE).strip(" |"))

    cur.execute(
        "UPDATE series_plans SET title=?, status=?, publish_date=?, notes=?, updated_at=? "
        "WHERE brand='local-ai' AND episode=4",
        (REAL_TITLE, "published", "", new_notes, ts))
    con.commit()

    after = cur.execute(
        "SELECT title, status, publish_date, notes FROM series_plans "
        "WHERE brand='local-ai' AND episode=4").fetchone()
    print("\n改后: title=%r\n      status=%r\n      date=%r" % (after[0], after[1], after[2]))
    print("      notes 末 90 字: …%s" % after[3][-90:])

    # ---- 复校验 ----
    print("\n=== 复校验 ===")
    print("  ep4 标题 == 成稿标题 :", after[0] == REAL_TITLE)
    print("  ep4 status=published :", after[1] == "published")
    print("  ep4 日期已清         :", after[2] == "")
    rows = cur.execute(
        "SELECT episode, publish_date FROM series_plans "
        "WHERE brand='local-ai' AND publish_date<>'' ORDER BY episode").fetchall()
    print("  有日期行: %d / 102" % len(rows))
    print("\n  文生图线 12 月:")
    for r in cur.execute(
            "SELECT episode, title, status, publish_date FROM series_plans "
            "WHERE brand='local-ai' AND episode BETWEEN 4 AND 8 ORDER BY episode"):
        print("    ep%-3d %-11s %-9s %s" % (r[0], r[3] or "(空)", r[2], (r[1] or "")[:44]))
    # 日期单调复核
    bad, prev = [], None
    for ep, d in rows:
        if prev and d < prev[1]: bad.append((prev, (ep, d)))
        prev = (ep, d)
    print("\n  日期倒挂: %d 处 %s" % (len(bad), [(a[0], a[1], b[0], b[1]) for a, b in bad]))
finally:
    con.close()
