# -*- coding: utf-8 -*-
"""给 ep4 / ep8 写号序倒挂说明（用户回「2」= 加备注，不重编号）"""
import sqlite3, time

DB = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
con = sqlite3.connect(DB, timeout=20)
try:
    cur = con.cursor()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    full = ("2026-10-27 号序说明:本线期号 4-8 早于已发布的 9-12,但排期落在 2026-12"
            "(前期跳过未做),与 ep9 构成号序倒挂。号位保留、不重编号(重编号会打断文内"
            "「第X节」引用);发布一律以日期为准,号位仅作选题编号。")
    mark = "2026-10-27 号序倒挂点:ep8(2026-12-29) 晚于 ep9(2026-10-05),说明见 ep4 notes。"

    n = 0
    for ep, add in [(4, full), (8, mark)]:
        row = cur.execute(
            "SELECT notes FROM series_plans WHERE brand='local-ai' AND episode=?", (ep,)).fetchone()
        old = (row[0] if row else "") or ""
        if "号序说明" in old or "号序倒挂点" in old:
            print("  ep%d 已有说明,跳过" % ep)
            continue
        cur.execute(
            "UPDATE series_plans SET notes=?, updated_at=? WHERE brand='local-ai' AND episode=?",
            ((old + " | " + add).strip(" |"), ts, ep))
        n += 1
        print("  ep%d 已追加" % ep)
    con.commit()
    print("写入 %d 条" % n)

    print()
    for r in cur.execute("""SELECT episode,notes FROM series_plans
                            WHERE brand='local-ai' AND episode IN (4,8) ORDER BY episode"""):
        print("ep%d notes:\n  %s\n" % (r[0], r[1]))
finally:
    con.close()
