#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ep25 数据汇总：三轮跑测 + v3 字准率 + 18 个失败案例 → JSON + HTML"""
import os, sys, json, time, statistics, html
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = r"D:/study/ai-jms/voice_samples/ep25_run"
OUTD = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench"
SLOT = os.path.join(BASE, "slot_0015")

def load_slot(name):
    tj = os.path.join(BASE, name, "timing.jsonl")
    if not os.path.exists(tj): return [], None
    rows = [json.loads(l) for l in open(tj, encoding="utf-8") if l.strip()]
    cells = [r for r in rows if r.get("kind") == "cell"]
    ld = None
    lp = os.path.join(BASE, name, "load.json")
    if os.path.exists(lp): ld = json.load(open(lp, encoding="utf-8"))
    return cells, ld

# ---------- 1. 三轮跑测 ----------
runs = {}
for s in ("slot_1400", "slot_2100", "slot_0015"):
    c, l = load_slot(s)
    runs[s] = {"cells": c, "load": l}

# ---------- 2. v3 字准率 ----------
cer = {}
p = os.path.join(SLOT, "asr_cer_v3.json")
if os.path.exists(p):
    cer = {r["engine"]: [] for r in json.load(open(p, encoding="utf-8"))["results"] if r.get("asr_ok")}
    for r in json.load(open(p, encoding="utf-8"))["results"]:
        if r.get("asr_ok"): cer.setdefault(r["engine"], []).append(r)

# ---------- 3. 汇总（主轮 slot_0015）----------
main_cells = runs["slot_0015"]["cells"]
ok_cells   = [c for c in main_cells if c.get("ok")]

by_eng = {}
for c in main_cells: by_eng.setdefault(c["engine"], []).append(c)

eng_rows = []
for e, cs in sorted(by_eng.items(), key=lambda kv: statistics.median(
        [x["wall_s"] for x in kv[1] if x.get("ok")] or [1e9])):
    o = [x for x in cs if x.get("ok")]
    w = sorted(x["wall_s"] for x in o)
    r = sorted(x["rtf"] for x in o if x.get("rtf"))
    cc = cer.get(e, [])
    cers = [x["cer_v3_pct"] for x in cc]
    eng_rows.append({
        "engine": e, "n_total": len(cs), "n_ok": len(o), "n_fail": len(cs)-len(o),
        "wall_min": round(w[0],1) if w else None,
        "wall_med": round(statistics.median(w),1) if w else None,
        "wall_max": round(w[-1],1) if w else None,
        "rtf_med": round(statistics.median(r),2) if r else None,
        "cer_med": round(statistics.median(cers),2) if cers else None,
        "cer_mean": round(sum(cers)/len(cers),2) if cers else None,
        "cer_max": round(max(cers),2) if cers else None,
        "cer_perfect": sum(1 for v in cers if v == 0.0),
        "cer_n": len(cers),
        "dur_med": round(statistics.median([x["audio_s"] for x in o]),2) if o else None,
    })

# 题组维度
grp = {}
for c in ok_cells: grp.setdefault(c.get("group") or "?", []).append(c)
grp_rows = []
for g in sorted(grp):
    cs = grp[g]
    cers = []
    for c in cs:
        for r in cer.get(c["engine"], []):
            if r["qid"] == c["qid"]: cers.append(r["cer_v3_pct"])
    grp_rows.append({
        "group": g, "n": len(cs),
        "wall_med": round(statistics.median([x["wall_s"] for x in cs]),1),
        "dur_med": round(statistics.median([x["audio_s"] for x in cs]),2),
        "cer_med": round(statistics.median(cers),2) if cers else None,
        "cer_n": len(cers),
    })

# ---------- 4. 失败案例（18 个）----------
fails = []
for slot, d in runs.items():
    for c in d["cells"]:
        if not c.get("ok"):
            note = str(c.get("note") or "")
            kind = "HTTP 503 超 600 秒被服务放弃" if "503" in note else \
                   "HTTP 500 子进程模式中止" if "500" in note else "其它"
            fails.append({"src": slot, "engine": c["engine"], "qid": c["qid"],
                          "group": c.get("group") or "", "kind": kind,
                          "wall_s": round(c["wall_s"],1)})
# 预飞/专项失败
preflight_fails = [
    {"engine":"VoxCPM2","kind":"预飞专项","reason":"冷启 66.04s 成功，合成跑到 23%（142 步扩散）被 info.bytes AttributeError 中断，无最终 wav",
     "note":"正式跑测 slot_0015 里 voxcpm2 25/25 全过 —— 该失败来自预飞脚本自身，非模型不可用"},
    {"engine":"Qwen3-TTS-0.6B","kind":"预飞专项","reason":"ValueError: model type 'qwen3_tts' 不被 transformers 5.21 识别",
     "note":"权重完整 2.34 GB；独立 venv 已建、dry-run 无降级；需升 transformers 才能验证"},
    {"engine":"GPT-SoVITS","kind":"预飞专项","reason":"9880 端口监听成功，但 /tts 请求 UnicodeEncodeError（URL 含中文），从未完成一次合成",
     "note":"端口起来不等于能跑；本引擎在本次数据中无任何成功样本"},
    {"engine":"MOSS-TTS-Nano","kind":"安装事故","reason":"pip 降级 torch 2.8.0→2.7.0、transformers 5.15.1→4.57.1，弄坏 VoiceStudio 主 venv",
     "note":"已回滚并复验 17 个关键包全部恢复；该引擎已移出阵容"},
    {"engine":"MegaTTS3","kind":"未测","reason":"权重在下载，未验证完整性与 CPU 可行性，零数据点",
     "note":"不能写入任何『它如何』的结论"},
]

# ---------- 5. 环境快照 ----------
snaps = {s: runs[s]["load"] for s in runs if runs[s]["load"]}

# ---------- 6. 落 JSON ----------
summary = {
    "generated": time.strftime("%Y-%m-%d %H:%M"),
    "main_slot": "slot_0015",
    "total_cells": sum(len(runs[s]["cells"]) for s in runs),
    "total_ok": sum(1 for s in runs for c in runs[s]["cells"] if c.get("ok")),
    "engines": eng_rows, "groups": grp_rows,
    "fail_cells": fails, "preflight_fails": preflight_fails,
    "snaps": snaps,
}
jp = os.path.join(OUTD, "ep25-数据汇总.json")
json.dump(summary, open(jp + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
os.replace(jp + ".tmp", jp)
print("JSON: %s" % jp)
print("总格 %d / 成功 %d / 失败格 %d / 预飞失败 %d"
      % (summary["total_cells"], summary["total_ok"], len(fails), len(preflight_fails)))
for r in eng_rows:
    print("  %-22s %d/%d  med %.1fs  RTF %s  CER %s"
          % (r["engine"], r["n_ok"], r["n_total"], r["wall_med"] or -1,
             r["rtf_med"], r["cer_med"]))
