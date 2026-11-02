# -*- coding: utf-8 -*-
"""ep6 方案 v2 存入排期（用户回「先存入排期」）"""
import sqlite3, time, json, pathlib

DB = r"C:/Users/Frank/AppData/Local/hermes/workspace/content-admin/admin.db"
ts = time.strftime("%Y-%m-%dT%H:%M:%S")

SAMPLE = ("题库 25 题按 ep4 五类题材分层（每类 5 题，提示词原文逐字沿用 ep4 保证跨期可比）"
          "+ 中文写字专项 10 题（1/4/20 步三档对照）；"
          "耗时每配置 3 次取中位；噪声地板同种子连跑 5 次比哈希（扩散确定性硬判据）；"
          "样本量依骨架 §B2 反推 ±19.6pp（p=0.5 最保守 95% 置信），小于约 20 个百分点的差距一律写未证明有差异")

CAND = ("待测 4 + 基线 1："
        "SDXS-512-0.9 OpenVINO 版 2.81GB（1 步，openrail++）；"
        "SD-Turbo fp16 1.65GB（1 步，Stability AI Community License，年收入<US$1M 可商用，已读 LICENSE.md 核过）；"
        "SDXL-Turbo OpenVINO int8 4.43GB（1 步，与 SD-Turbo 同一份许可，"
        "★初版据 HF 元数据 sai-nc-community 误判为非商用，2026-10-27 读 LICENSE.md 正文纠正）；"
        "SD1.5 + LCM-LoRA 128.4MB（4 步，openrail++；LoRA 加在 ep4 已有的 SD1.5 上，唯一变量是加不加 LoRA，控制变量最干净）；"
        "基线 SD1.5 20 步（ep4 已有 94–265 秒同机数据）。"
        "排除：FLUX 全系（第三方 4 分 30 秒/512² 且需约 30GB 内存）、Qwen-Image 20B（太慢）、768² 以上")

NOTES = ("2026-10-27 用户选方案A:本就无日期,保持待重排。未动笔。 | "
         "2026-10-27 方案 v2 存档（v1→v2 补 4 项：LCM / 中文写字专项 / 五类题材分层 / 与 ep5 分工）。"
         "★ep5 分工：ep5 只动位宽、ep6 只动步数，同一期不同时动两个变量。"
         "★稀缺性 4/5（我方评级，待用户复核）：第三方只报速度不报画质；中文写字 1/4/20 步对照与 LCM·蒸馏两路线同机比均未见同类；与 ep4 同机同种子可跨期直比。"
         "★阻塞：待用户批准下载 9.0GB（SDXS 2.81+SD-Turbo 1.65+SDXL int8 4.43+LCM 0.13，首次下到 61% 已停可续传）。"
         "★工作标题「一步出图行不行:少步加速档实测(SD-Turbo/LCM)」是规划名，动笔前需定稿并涵盖 SDXS/SD-Turbo/SDXL-Turbo/LCM-LoRA。"
         "★文章结构已按 ep4 阅读量四条教训设计：开头 200 字给结果 / 原理压到 300 字内 / 术语不挡开头 / 结尾一个具体问题。")

con = sqlite3.connect(DB, timeout=20)
try:
    cur = con.cursor()
    old = cur.execute("""SELECT sample_plan, candidate_models, scarcity, notes, stage_log_json
                         FROM series_plans WHERE brand='local-ai' AND episode=6""").fetchone()
    print("改前: sample=%d 字 cand=%d 字 scarcity=%s" % (
        len(old[0] or ""), len(old[1] or ""), old[2]))

    try:
        stage = json.loads(old[4] or "[]")
    except Exception:
        stage = []
    stage.append({"ts": ts, "status": "planned",
                  "actor": "agent",
                  "note": "方案 v2 存入排期：4 待测+基线、25 题五类分层+中文专项 10 题、"
                          "噪声地板、与 ep5 分工、许可四款全放行（SDXL 误判已纠正）；阻塞=9.0GB 下载待批"})

    cur.execute("""UPDATE series_plans SET sample_plan=?, candidate_models=?, scarcity=?,
                   notes=?, stage_log_json=?, updated_at=?
                   WHERE brand='local-ai' AND episode=6""",
                (SAMPLE, CAND, 4, NOTES, json.dumps(stage, ensure_ascii=False), ts))
    con.commit()

    a = cur.execute("""SELECT sample_plan, candidate_models, scarcity, test_plan, stage_log_json
                       FROM series_plans WHERE brand='local-ai' AND episode=6""").fetchone()
    print("改后: sample=%d 字 cand=%d 字 scarcity=%s test_plan=%d 字 stage=%d 条 ✅" % (
        len(a[0]), len(a[1]), a[2], len(a[3]), len(json.loads(a[4]))))
finally:
    con.close()

# ============ 落盘状态文件（与 ep13-16 同规格）============
out = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep6-排期状态.json")
state = {
    "episode": 6, "brand": "local-ai",
    "title_planning": "一步出图行不行:少步加速档实测(SD-Turbo/LCM)",
    "publish_date": "2026-12-15", "status": "planned",
    "plan_doc": "articles/bench/ep6-一步出图-跑测方案.html",
    "plan_version": "v2", "plan_date": "2026-10-27",
    "v2_changes": ["LCM-LoRA 进方案与许可闸门", "中文写字专项 10 题 1/4/20 步",
                   "题材分层沿用 ep4 五类原提示词", "与 ep5 分工写明 + 排期表 test_plan"],
    "core_question": "没显卡的电脑 2026 年还能不能秒出图；1 步比 20 步快多少、画质掉多少、中文能不能写真",
    "models": [
        {"name": "SDXS-512-0.9 OpenVINO", "size_gb": 2.81, "steps": 1,
         "license": "openrail++", "license_status": "已核可商用", "source": "rupeshs/sdxs-512-0.9-openvino"},
        {"name": "SD-Turbo fp16", "size_gb": 1.65, "steps": 1,
         "license": "Stability AI Community License", "license_status": "已核可商用(<US$1M)",
         "source": "stabilityai/sd-turbo"},
        {"name": "SDXL-Turbo OpenVINO int8", "size_gb": 4.43, "steps": 1,
         "license": "Stability AI Community License", "license_status": "已核可商用(<US$1M)；初版误判为非商用已纠正",
         "source": "rupeshs/sdxl-turbo-openvino-int8"},
        {"name": "SD1.5 + LCM-LoRA", "size_gb": 0.13, "steps": 4,
         "license": "openrail++", "license_status": "已核可商用",
         "source": "latent-consistency/lcm-lora-sdv1-5", "note": "LoRA 加在 ep4 已有 SD1.5 上，唯一变量"},
        {"name": "SD1.5 20 步基线", "size_gb": 0, "steps": 20,
         "license": "已核", "license_status": "已核", "source": "ep4 已有，实测 94–265 秒"},
    ],
    "download_total_gb": 9.0,
    "download_status": "已批准待执行；首次下到 61% 已按用户「不要执行」停掉，HF 缓存可续传",
    "run_count": 705, "run_time_estimate": "约 4–10 小时（估算，非实测）",
    "engines": ["FastSD CPU (OpenVINO)", "stable-diffusion.cpp", "diffusers"],
    "method": {
        "noise_floor": "同种子连跑 5 次比哈希（扩散确定性硬判据）",
        "repeat": "每配置 3 次取中位", "cold_start": "冷启与推理分开计时",
        "sample_size": "25 题 ±19.6pp（骨架 §B2 反推，p=0.5 最保守 95% 置信）",
        "min_reportable_diff": "小于约 20 个百分点的差距一律写未证明有差异",
        "scoring": "同题并排盲评，打乱顺序隐去引擎名；不合成单一分数",
    },
    "division_with_ep5": "ep5 只动位宽、ep6 只动步数；同一期不同时动两个变量",
    "scarcity": {"score": 4, "note": "我方评级待用户复核：第三方只报速度不报画质；中文写字 1/4/20 步对照与 LCM·蒸馏两路线同机比未见同类；与 ep4 同机同种子可跨期直比"},
    "blocking": ["用户批准下载 9.0GB（未执行）",
                 "用户画质盲评 25 题 × 4 模型（约 20 分钟）",
                 "用户中文专项 10 题打分（约 10 分钟，待拍板 #6）"],
    "excluded": ["FLUX 全系（第三方 4 分 30 秒/512²，需约 30GB 内存）",
                 "Qwen-Image 20B（1024² 10 步约 795 秒）",
                 "768² 以上（像素线性推高耗时，ep4 已证核显 1024 崩）",
                 "量化位数（归 ep5）"],
    "article_structure": "按 ep4 阅读量四条教训：开头 200 字给结果 / 原理压到 300 字内 / 术语不挡开头 / 结尾一个具体问题",
    "updated_at": ts,
}
out.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n状态文件: %s (%.1f KB)" % (out.name, out.stat().st_size / 1024))
print("  models=%d  blocking=%d  excluded=%d" % (
    len(state["models"]), len(state["blocking"]), len(state["excluded"])))
