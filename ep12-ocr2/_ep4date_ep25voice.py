# -*- coding: utf-8 -*-
"""按用户 2026-10-27 回复执行：
2) ep4 publish_date = 2026-10-21
5) 声音克隆一期占 ep25 号位（A 方案：替换原「会议场景」选题）
"""
import sqlite3, time

DB = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
ts = time.strftime("%Y-%m-%dT%H:%M:%S")

TITLE = "声音克隆续测：Qwen3-TTS、CosyVoice3、GPT-SoVITS 同机对照"
TESTPLAN = ("见 articles/bench/ep13-16-小模型场景实测-跑测方案.html 同类骨架 + "
            "articles/bench/声音克隆-模型能力验证.md（已完成的选型与真跑实测）")
SAMPLE = ("25 条中文提示词（同骨架 §B2 反推，±19.6pp）；同段参考音频、同参考文本跨引擎；"
          "耗时每配置 3 次取中位；噪声地板同种子连跑 5 次比哈希")
CAND = ("入选：Qwen3-TTS-0.6B-Base（RTF≈7.1，已真跑，中文同音混淆「积木师→金牧师」）、"
        "CosyVoice3（RTF 7-8，中文清晰，Apache-2.0）、GPT-SoVITS（MIT，快线 RTF≈2）；"
        "出局：Kokoro-82M（不能克隆，54 固定说话人）、Qwen3 CustomVoice（非克隆，9 固定音色）、"
        "omnivoice（CC-BY-NC 非商用）、F5-TTS / ChatTTS / fish-speech（均 CC-BY-NC 非商用）")
NOTES = ("2026-10-27 用户选 A 方案：占 ep25 号位，原选题「会议场景:说话人分离+自动字幕」移出"
         "（与横评段 ep28「同一段会议录音，6 个本地模型谁转得准」主题重复）。"
         "选型与真跑实测已完成，报告 articles/bench/声音克隆-模型能力验证.md"
         "（含三轮：文档级 / 实测级 / 真跑；第一轮曾被覆盖写丢失已重建）。"
         "工作标题待动笔前定稿。")

con = sqlite3.connect(DB, timeout=20)
try:
    cur = con.cursor()

    # --- 2) ep4 群发日期 ---
    b = cur.execute("SELECT publish_date, title FROM series_plans "
                    "WHERE brand='local-ai' AND episode=4").fetchone()
    print("ep4 改前 date=%r" % b[0])
    cur.execute("UPDATE series_plans SET publish_date=?, updated_at=? "
                "WHERE brand='local-ai' AND episode=4", ("2026-10-21", ts))
    a = cur.execute("SELECT publish_date, status FROM series_plans "
                    "WHERE brand='local-ai' AND episode=4").fetchone()
    print("ep4 改后 date=%r status=%r  ✅" % (a[0], a[1]))

    # --- 5) ep25 -> 声音克隆 ---
    old = cur.execute("SELECT title, status, publish_date, notes FROM series_plans "
                      "WHERE brand='local-ai' AND episode=25").fetchone()
    print("\nep25 改前: title=%r status=%r date=%r" % (old[0], old[1], old[2]))
    keep_date = old[2]  # 日期不动
    cur.execute("""UPDATE series_plans SET title=?, status=?, sample_plan=?, candidate_models=?,
                   test_plan=?, notes=?, updated_at=?
                   WHERE brand='local-ai' AND episode=25""",
                (TITLE, "planned", SAMPLE, CAND, TESTPLAN, NOTES, ts))
    con.commit()

    # --- 复校验 ---
    print("\n=== 复校验 ===")
    rows = cur.execute("""SELECT episode,title,status,publish_date FROM series_plans
                          WHERE brand='local-ai' ORDER BY episode""").fetchall()
    print("  总行 %d | 有日期 %d" % (len(rows), sum(1 for r in rows if r[3])))
    for e in (4, 24, 25, 26):
        r = [x for x in rows if x[0] == e][0]
        print("  ep%-4d %-11s %-9s %s" % (r[0], r[3] or "(空)", r[2], (r[1] or "")[:50]))
    # 日期倒挂
    dated = [(r[0], r[3]) for r in rows if r[3]]
    bad, prev = [], None
    for ep, d in dated:
        if prev and d < prev[1]: bad.append((prev[0], prev[1], ep, d))
        prev = (ep, d)
    print("\n  日期倒挂 %d 处:" % len(bad))
    for x in bad: print("    ep%s %s -> ep%s %s" % x)
    # 号位唯一
    eps = [r[0] for r in rows]
    print("  号位唯一:", len(set(eps)) == len(eps), "| 号序 1..102 连续:",
          sorted(eps) == list(range(1, 103)))
finally:
    con.close()
