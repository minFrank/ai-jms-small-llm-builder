# -*- coding: utf-8 -*-
"""删除全部 31 个空壳期（用户回「A」，后果已告知：四个板块 L3 归零、排期缩到 2027-09-07）"""
import sqlite3, pathlib, shutil, time
from collections import Counter

DB = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db")
BAK = pathlib.Path(str(DB) + ".bak-del-shells")
if not BAK.exists():
    shutil.copy2(DB, BAK)
    print("备份: %s (%.1f MB)" % (BAK.name, BAK.stat().st_size / 1048576))

con = sqlite3.connect(str(DB), timeout=30)
try:
    cur = con.cursor()

    # ---- 0) 安全核查 ----
    shells = cur.execute("""SELECT episode FROM series_plans WHERE brand='local-ai'
                            AND title LIKE '%选题运行时确定%' ORDER BY episode""").fetchall()
    eps = [r[0] for r in shells]
    print("\n待删 %d 期: ep%d–ep%d" % (len(eps), eps[0], eps[-1]))
    print("  非连续？", "无" if eps == list(range(eps[0], eps[-1] + 1)) else "有缺口 %s" % eps)

    st = cur.execute("""SELECT status, COUNT(*) FROM series_plans WHERE brand='local-ai'
                        AND title LIKE '%选题运行时确定%' GROUP BY status""").fetchall()
    print("  状态分布:", dict(st))
    assert all(s == "planned" for s, _ in st), "存在非 planned 行，停止"

    art = cur.execute("""SELECT episode FROM articles WHERE series='local-ai'
                         AND episode IN (%s)""" % ",".join(map(str, eps))).fetchall()
    print("  articles 表命中:", art or "无 ✅")
    assert not art, "articles 有记录，停止"

    md_dir = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai")
    import re
    md_eps = []
    for f in md_dir.glob("*.md"):
        m = re.search(r"local-ai-(\d+)-", f.name)
        if m and int(m.group(1)) in eps:
            md_eps.append(f.name)
    print("  本地成稿命中:", md_eps or "无 ✅")
    assert not md_eps, "有成稿，停止"

    before_n = cur.execute("SELECT COUNT(*) FROM series_plans WHERE brand='local-ai'").fetchone()[0]

    # ---- 1) 删除 ----
    cur.execute("""DELETE FROM series_plans WHERE brand='local-ai'
                   AND title LIKE '%选题运行时确定%'""")
    print("\n删除 %d 行" % cur.rowcount)
    con.commit()

    # ---- 2) 复校验 ----
    rows = cur.execute("""SELECT episode, title, publish_date, vertical, status
                          FROM series_plans WHERE brand='local-ai' ORDER BY episode""").fetchall()
    print("\n=== 复校验 ===")
    print("  总行 %d → %d" % (before_n, len(rows)))
    eps2 = [r[0] for r in rows]
    print("  号位唯一:", len(set(eps2)) == len(eps2))
    print("  号序连续 1..%d:" % len(eps2), sorted(eps2) == list(range(1, len(eps2) + 1)))
    print("  残留空壳:", sum(1 for r in rows if "选题运行时确定" in (r[1] or "")))
    print("  板块分布:", dict(Counter(r[3] for r in rows)))
    print("  status  :", dict(Counter(r[4] for r in rows)))
    dated = [(r[0], r[2]) for r in rows if r[2]]
    bad, prev = [], None
    for ep, d in dated:
        if prev and d < prev[1]:
            bad.append((prev[0], prev[1], ep, d))
        prev = (ep, d)
    print("  有日期 %d | 倒挂 %d 处（应仍 2）" % (len(dated), len(bad)))
    for x in bad:
        print("     ep%s %s -> ep%s %s" % x)
    print("\n  各板块剩什么:")
    g = Counter()
    for e, t, d, v, s in rows:
        g[v] += 1
    for v in ["ocr", "asr", "voice-clone", "txt2img", "llm"]:
        eps_v = [(e, d) for e, t, d, vv, s in rows if vv == v]
        print("    %-12s %2d 期  %s ~ %s" % (v, len(eps_v),
              min(d for _, d in eps_v if d) if any(d for _, d in eps_v) else "—",
              max(d for _, d in eps_v if d) if any(d for _, d in eps_v) else "—"))
    print("\n  末尾 5 期:")
    for r in rows[-5:]:
        print("     ep%-4d %-11s %-12s %s" % (r[0], r[2] or "—", r[3], (r[1] or "")[:46]))
finally:
    con.close()
