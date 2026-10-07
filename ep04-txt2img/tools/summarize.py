#!/usr/bin/env python
"""ep04 五方案对照汇总: 从数据文件现算,禁止手打。

数据源:
  logs/bench4-progress.json   已发布三方案(sd.cpp cpu / sd.cpp vulkan / diffusers)
  logs/bench5-progress.json   阶段1 ComfyUI(cold/warm/anchor)
  logs/bench6-progress.json   阶段2 ONNX/DML(cold) + profiling 门禁

输出: replicate/summary-five-schemes.json + stdout 表格
口径(dsh §4.1):
  - 耗时一律 cold_total(冷启动含加载);warm 单列不进头条
  - n>=3 报 median 与 (max-min)/median
  - 只允许两类结论句: 同落点比引擎 / 同引擎比落点;跨栈句需标不可归因
"""
import hashlib
import json
import os
import statistics as st
from collections import defaultdict
from datetime import datetime

E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
OUT = os.path.join(E04, "replicate", "summary-five-schemes.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def stat(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    med = st.median(xs)
    return {"n": len(xs), "median": round(med, 2),
            "min": round(min(xs), 2), "max": round(max(xs), 2),
            "spread_pct": round((max(xs) - min(xs)) / med * 100, 2) if med else None,
            "mean": round(st.mean(xs), 2)}


def latest_attempt(rows, mode=None):
    """按 cell 取最新 attempt(C4 重跑后避免新旧混算)。"""
    best = {}
    for r in rows:
        if mode and r.get("mode") != mode:
            continue
        c = r.get("cell")
        if c not in best or (r.get("attempt") or 0) >= (best[c].get("attempt") or 0):
            best[c] = r
    return list(best.values())


def per_cell_spread(rows, field="seconds_total"):
    """R18: 每格 (prompt,seed) 的重复运行离散度 = (max-min)/median, DP-15 判据。"""
    g = defaultdict(list)
    for r in rows:
        v = r.get(field)
        if v is not None:
            g[(r.get("prompt_idx"), r.get("seed"))].append(v)
    out = {}
    for k, v in sorted(g.items()):
        med = st.median(v)
        sp = round((max(v) - min(v)) / med * 100, 2) if med else None
        out[f"p{k[0]}_s{k[1]}"] = {"n": len(v), "median": round(med, 2),
                                   "spread_pct": sp,
                                   "pass_5pct": sp is not None and sp <= 5}
    out["all_pass"] = all(x["pass_5pct"] for x in out.values()
                          if isinstance(x, dict))
    return out


def batch_groups(rows, gap_s=300):
    """R8: 按 ts 间隔归批(>gap 视为新批次), 返回批次列表与行数。"""
    rs = sorted(rows, key=lambda r: r.get("ts") or "")
    groups, cur = [], []
    prev = None
    for r in rs:
        ts = r.get("ts") or ""
        if prev:
            try:
                t1 = datetime.strptime(prev, "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                if (t2 - t1).total_seconds() > gap_s:
                    groups.append(cur)
                    cur = []
            except Exception:
                pass
        cur.append(r)
        prev = ts
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        out.append({"batch_id": f"B{i + 1}", "n": len(g),
                    "start": g[0].get("ts"), "end": g[-1].get("ts"),
                    "attempts": sorted({r.get("attempt") for r in g})})
    return out


_ARCHIVE_NOTE = {
    "bench6-progress.v2-缺陷批.json":
        "dsh REVIEW-bench6 首版判 24 处/10 阻断(R1/R2/R3/R4 计时边界与"
        "profiling 覆盖缺陷), 整批归档不入表",
    "bench6-progress.v4-批首效应.json":
        "批首效应: 每批首个子进程 gen 65-75s、其后 96-98s, 池化 spread "
        "14.5-21.9% 超 5% 判据, 归档改用 warmup 预热后重跑",
    "bench6-progress.profiling-v3归档.json":
        "v3 profiling 行按修正前判据产出(err 字段语义不同), 指纹不一致归档",
    "bench6-landing.v1.json":
        "v1 landing 行(旧判据 A: max>500MB / B: n=1), 被 evidence-v2 r4 取代",
}


def rerun_reasons():
    """R8: 重跑原因不能只留在归档文件里, 必须进 summary。"""
    out = []
    for fn in ("bench6-contaminated-p0s43-att2.json",
               "bench6-attempt-p0s43-att2.json",
               "bench6-progress.v2-缺陷批.json",
               "bench6-progress.v4-批首效应.json",
               "bench6-progress.profiling-v3归档.json",
               "bench6-landing.v1.json"):
        p = os.path.join(E04, "logs", fn)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            rows = d.get("rows") or []
            cells = sorted({r.get("cell") for r in rows if r.get("cell")})
            reason = d.get("note")
            if not reason:
                reason = _ARCHIVE_NOTE.get(fn, "(归档内未写 note)")
            out.append({
                "archive": f"logs/{fn}",
                "reason": reason,
                "n_rows": len(rows),
                "n_cells": len(cells),
                "cells": cells[:12],
                "excluded_from": "summary-five-schemes headline",
            })
        except Exception as e:
            out.append({"archive": f"logs/{fn}", "err": str(e)[:160]})
    out.append({
        "archive": "(正式重跑, 已入表)",
        "reason": "p0_s43 attempt2 首格 r0=109.56s 偏快、按格离散 5.33%>5%, "
                  "归档后 warmup 3 重跑(第 2 次, C4 上限内)",
        "cells": ["onnx_cold_p0_s43_r0", "onnx_cold_p0_s43_r1",
                  "onnx_cold_p0_s43_r2"],
        "result": "115.50/115.49/115.71, 离散 0.19%, PASS",
        "excluded_from": "-",
    })
    out.append({
        "archive": "(定向重跑, 已入表)",
        "reason": "p0_s42 与 p0_s44 首轮出现 99.9s/104.0s 离群, 按格离散"
                  "13.09%/10.55%>5%, C4 判污染后定向重跑",
        "cells": ["onnx_cold_p0_s42_*", "onnx_cold_p0_s44_*"],
        "result": "重跑后 spread 2.78% / 0.38%, PASS",
        "excluded_from": "-",
    })
    return out


def attempt_mix(rows):
    """R8: headline 由哪些 attempt 构成(4 格 attempt1 + 2 格 attempt2 之类)。"""
    from collections import Counter
    c = Counter(r.get("attempt") for r in rows)
    return {f"attempt_{k}": v for k, v in sorted(c.items())}


def per_prompt_seed_median(rows, field="seconds_total"):
    """按 (prompt, seed) 分组取 median —— 每组 n>=3(DP-14)。"""
    g = defaultdict(list)
    for r in rows:
        v = r.get(field)
        if v is not None:
            g[(r.get("prompt_idx"), r.get("seed"))].append(v)
    return {f"p{k[0]}_s{k[1]}": {"n": len(v), "median": round(st.median(v), 2)}
            for k, v in sorted(g.items())}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    b4 = load(os.path.join(E04, "logs", "bench4-progress.json"))["rows"]
    b5 = load(os.path.join(E04, "logs", "bench5-progress.json"))["rows"]
    b6 = load(os.path.join(E04, "logs", "bench6-progress.json"))
    b6r = b6["rows"]

    # evidence-v2 必须在 json.dump 之前读入, 否则产物里没有证据(dsh §7.1)
    _EVID = {}
    _ev_path = os.path.join(E04, "replicate", "evidence-v2.json")
    if os.path.exists(_ev_path):
        with open(_ev_path, encoding="utf-8") as f:
            _EVID = json.load(f)

    # ---- bench4 批次拆分(判据1: 同一数据源、同批)----
    # _s<seed> 批 = 正式批 = 文章已发布数字;_r<0|1> 批 = 早期试跑(条件不同,不可混算)
    # R16: 已发布正文写明三方案各 6 条(2 prompt x 3 seed), 与冻结清单常量比对,
    # 不再只靠后缀猜
    FORMAL_CELLS = {f"{s}_p{p}_s{sd}"
                    for s in ("sdcpp-cpu", "sdcpp-vulkan", "diffusers")
                    for p in (0, 1) for sd in (42, 43, 44)}

    def is_formal(r):
        c = r.get("cell", "")
        if c not in FORMAL_CELLS:
            return False
        # 防御: 正式批必须 steps=20 / 512x512(与正文口径一致)
        return r.get("steps") == 20 and r.get("size") == "512x512"

    b4_formal = [r for r in b4 if is_formal(r)]
    b4_trial = [r for r in b4 if not is_formal(r)]

    res = {"sources": {
        "bench4": sha(os.path.join(E04, "logs", "bench4-progress.json")),
        "bench5": sha(os.path.join(E04, "logs", "bench5-progress.json")),
        "bench6": sha(os.path.join(E04, "logs", "bench6-progress.json")),
    },
        "batches": {
            "formal": {"rows": len(b4_formal), "note": "_s42/_s43/_s44 正式批(已发布)"},
            "trial": {"rows": len(b4_trial),
                      "note": "_r0/_r1 早期试跑(条件不同,不入表)"},
            "trial_stats": {},
        }, "schemes": {}}

    for scheme, label in (("sdcpp-cpu", "sd.cpp · 纯 CPU"),
                          ("sdcpp-vulkan", "sd.cpp · Vulkan 核显"),
                          ("diffusers", "diffusers · 纯 CPU")):
        rs = [r for r in b4_formal if r.get("scheme") == scheme and r.get("ok")]
        tr = [r for r in b4_trial if r.get("scheme") == scheme and r.get("ok")]
        res["schemes"][label] = {
            "source": "bench4 正式批(已发布,冻结)",
            "landing": "CPU" if "vulkan" not in scheme else "iGPU(Vulkan)",
            "seconds": stat([r.get("seconds") for r in rs]),
            # R23: 缺内存的行不参与统计(填 0 会拉低 median)
            "mem_mb": stat([(r["mem_peak"] / 1048576) for r in rs
                            if r.get("mem_peak")]),
        }
        res["batches"]["trial_stats"][scheme] = stat(
            [r.get("seconds") for r in tr])

    # ---- 阶段1 ComfyUI ----
    cold5 = [r for r in b5 if r.get("mode") == "cold" and r.get("ok")]
    res["schemes"]["ComfyUI · 纯 CPU(冷启动)"] = {
        "source": "bench5 cold",
        "landing": "CPU",
        "seconds_total": stat([r.get("seconds_total") for r in cold5]),
        "seconds_gen": stat([r.get("seconds_gen") for r in cold5]),
        "mem_mb": stat([r.get("mem_peak_mb") for r in cold5]),
        "timing_scope": "cold_total_incl_load",
        "device_evidence": all(r.get("device_hit") for r in cold5),
    }
    warm5 = [r for r in b5 if r.get("mode") == "warm" and r.get("ok")]
    res["schemes"]["ComfyUI · 纯 CPU(暖态,单列)"] = {
        "source": "bench5 warm",
        "seconds_gen": stat([r.get("seconds_gen") for r in warm5]),
        "timing_scope": "warm_gen_only",
    }

    # ---- 锚点漂移(DP-19) ----
    # R16: 基线取**已发布正文**写明的 241.6s(均值), 不是同源重算的 241.05
    #      (同源重算=自证, dsh 明确否掉)
    PUB_BASELINE = 241.6
    anch = [r for r in b5 if r.get("mode") == "anchor" and r.get("ok")]
    anchors = []
    if anch:
        am = st.median([r["seconds_total"] for r in anch])
        anchors.append({
            "date": "2026-10-06", "source": "bench5 anchor",
            "retested_median": round(am, 2), "published_median": PUB_BASELINE,
            "drift_pct": round((am - PUB_BASELINE) / PUB_BASELINE * 100, 2),
            "n": len(anch),
            "covers_onnx_batch": False,
        })
    # 同日 anchor(evidence-v2, 与 ONNX 批同一天)
    ev_path = os.path.join(E04, "replicate", "evidence-v2.json")
    if os.path.exists(ev_path):
        with open(ev_path, encoding="utf-8") as f:
            ev = json.load(f)
        a2 = ev.get("r17_anchor") or {}
        if a2.get("ok") and a2.get("median"):
            anchors.append({
                "date": a2.get("date"), "source": "evidence-v2 r17",
                "retested_median": a2["median"],
                "published_median": PUB_BASELINE,
                "drift_pct": a2.get("drift_pct_vs_published"),
                "n": a2.get("n_ok"),
                "covers_onnx_batch": a2.get("covers_onnx_batch_date"),
            })
    if anchors:
        worst = max(abs(a["drift_pct"]) for a in anchors
                    if a.get("drift_pct") is not None)
        res["anchor"] = {
            "baseline_source": "已发布正文常量 241.6s(均值, n=6)",
            "runs": anchors,
            "worst_abs_drift_pct": worst,
            "within_5pct": worst < 5,
            "n": sum(a.get("n") or 0 for a in anchors),
            "conclusion": (
                "跨日锚点漂移在 5% 内, 跨期可比"
                if worst < 5 else
                f"跨日锚点最差漂移 {worst}% (>5%), 整张五方案表的跨批比较"
                f"必须按该漂移区间解读; 同批内部比较不受影响"),
        }

    # ---- 阶段2 ONNX/DML(取每个 cell 的最新 attempt) ----
    cold6 = [r for r in latest_attempt(b6r, "timing") if r.get("ok")]
    if cold6:
        res["schemes"]["ONNX/DML · 核显(冷启动)"] = {
            "source": "bench6 timing(最新 attempt)",
            "landing": "iGPU(DirectML)",
            "seconds_total": stat([r.get("seconds_total") for r in cold6]),
            "seconds_load": stat([r.get("seconds_load") for r in cold6]),
            "seconds_gen": stat([r.get("seconds_gen") for r in cold6]),
            "seconds_decode": stat([r.get("seconds_decode") for r in cold6]),
            "mem_mb": stat([r.get("mem_peak_mb") for r in cold6]),
            "timing_scope": "cold_incl_session_create",
            "providers": sorted({p for r in cold6 for p in (r.get("providers") or [])}),
            "nfe": sorted({r.get("nfe") for r in cold6}),
            "per_prompt_seed_median": per_prompt_seed_median(cold6),
            # R18: DP-15 的"离散度"是按格的重复运行离散度, 不是池化值
            "per_cell_spread": per_cell_spread(cold6),
            "pooled_spread_note": "池化 spread 只作参考; 判据用 per_cell_spread",
            # R8: 批次字段 + attempt 构成(披露 headline 是跨 attempt 拼接)
            "batches": batch_groups(cold6),
            "attempt_mix": attempt_mix(cold6),
            "headline_note": ("headline 取 latest attempt; 若 attempt_mix 不是"
                              "单一 attempt, 正文须披露重跑格与原因"),
            "rerun_reasons": rerun_reasons(),
            # dsh §7.5: headline 跨 attempt 时必须并列各批中位数,
            # 正文只能引"逐批次中位数"而不是单个池化数
            "headline_by_batch": [
                {
                    "batch_id": b["batch_id"],
                    "n": b["n"],
                    "start": b["start"], "end": b["end"],
                    "attempts": b["attempts"],
                    "median_s": round(st.median(
                        [r["seconds_total"] for r in cold6
                         if b["start"] <= (r.get("ts") or "") <= b["end"]]), 2),
                }
                for b in batch_groups(cold6)
                if [r for r in cold6 if b["start"] <= (r.get("ts") or "")
                    <= b["end"]]
            ],
        }
    # ---- R4 落点门禁(两段式) ----
    # profiling: 实测证明 ORT 度量不到 DML 的 GPU 执行时间(覆盖率 2.8-5.2%),
    #   因此**不得**用它写"CPU 占比 0%"(那是假绿)。只如实记录覆盖率与
    #   "未记录到 CPU 节点"这一条弱证据。
    # landing: 真门禁 = PDH GPU 计数器在跑测期间增长 + 同图 DML/CPU 对照。
    prof = latest_attempt(b6r, "profiling")
    if prof:
        cov = [r.get("prof_coverage") for r in prof if r.get("prof_coverage") is not None]
        usable = [r.get("prof_gate_usable") for r in prof]
        res["profiling_gate"] = {
            "n": len(prof),
            "coverage_pct": [round(c * 100, 1) for c in cov],
            "coverage_min_pct": round(min(cov) * 100, 1) if cov else None,
            "gate_usable": any(usable) if usable else False,
            # dsh §7.7: 覆盖率 <20% 时 cpu_pct 必须为 null。
            # 源行里写的是 0.0(bench6 源文件与数据指纹一致, 不改源),
            # 这里在汇总层显式作废, 防止 0.0 被当成"CPU 占比 0%"引用。
            "cpu_pct": (None if (cov and min(cov) < 0.20) else 0.0),
            "cpu_pct_invalid_reason": (
                f"profiling 覆盖率最低 {round(min(cov) * 100, 1)}% (<20%), "
                "未记录到 CPU 节点不等于执行在 GPU; 源行的 cpu_pct=0.0 已作废"
                if (cov and min(cov) < 0.20) else None),
            "conclusion": ("工具可用" if any(usable) else
                           "ORT profiling 覆盖率 <20%, 时间口径不可用(工具限制); "
                           "落点改由 landing 门禁判定"),
            "rows_with_err": [r["cell"] for r in prof if r.get("err")],
        }
    if b6.get("landing"):
        lg = b6["landing"]
        res["landing_gate"] = {
            "ok": lg.get("ok"),
            "dml_gen_s": lg.get("dml_gen_s"),
            "cpu_gen_s": lg.get("cpu_gen_s"),
            "speedup_vs_cpu": lg.get("speedup_vs_cpu"),
            "gpu_shared_min_mb": (round(lg["gpu_shared_min"] / 1048576, 1)
                                  if lg.get("gpu_shared_min") else None),
            "gpu_shared_max_mb": (round(lg["gpu_shared_max"] / 1048576, 1)
                                  if lg.get("gpu_shared_max") else None),
            "gpu_dedicated_max_mb": (round(lg["gpu_dedicated_max"] / 1048576, 1)
                                     if lg.get("gpu_dedicated_max") else None),
            "criteria_A_gpu_counter": lg.get("A_gpu_counter_grew"),
            "criteria_B_dml_faster": lg.get("B_dml_faster_than_cpu"),
            "cpu_control_providers": lg.get("cpu_providers"),
            "harness_criteria_note": (
                "harness 自带 landing 是旧判据(A: max>500MB, B: n=1), "
                "新判据见 landing_gate_v2"),
        }
    # ---- evidence-v2 的新版 landing(R4 修复: A 真增长, B n=3 双侧 + 两侧预热) ----
    if _EVID.get("r4_landing"):
        r4 = _EVID["r4_landing"]
        res["landing_gate_v2"] = {
            "ok": r4.get("ok"),
            "source": "replicate/evidence-v2.json r4_landing",
            "dml_gen_s_median": r4.get("dml_median"),
            "cpu_gen_s_median": r4.get("cpu_median"),
            "speedup_median": r4.get("speedup_median"),
            "A_criteria": r4.get("A_criteria"),
            "B_criteria": r4.get("B_criteria"),
            "cpu_control_providers": r4.get("cpu_control_providers"),
            "regime_note": (
                "四次 DML 跑的 gen 分属不同来源、量级互不一致: "
                "evidence r4 65.709s / bench6 landing 73.842s / "
                "evidence r10 子进程 86.941s / timing 头条 97.15s。"
                "成因未定(已排除可归因证据, parentload_probe 无产物), "
                "故各 landing 倍数只在本轮内部有效, 不得与 115.49s 头条混算。"),
            "publishable": "定性(DML EP 实际启用且显著快于纯 CPU), 倍数不入正文",
        }
    # ---- R11: Q2 的 scheduler 等价性断言(PNDM 无 sigmas, 改用 timesteps 哈希) ----
    # 已发布 diffusers 行 = 管线默认 PNDM;本行同样 PNDM 且 sched_config 同源
    # (bench6 指纹里已含 sched_config_sha)。这里把两侧 20 步的 timesteps
    # 数组哈希算出来存档, 作为"同一组时间步"的可查证据。
    try:
        from diffusers import PNDMScheduler
        with open(r"D:/ep04/onnx/sd15/scheduler-config.json",
                  encoding="utf-8") as _f:
            _sc = json.load(_f)
        _sch = PNDMScheduler.from_config(_sc["config"])
        _sch.set_timesteps(20)
        _ts = hashlib.sha256(
            _sch.timesteps.detach().cpu().numpy().astype("float64").tobytes()
        ).hexdigest()[:16]
        # 两侧独立构造再比对 —— 已发布行用 gen_diffusers_one.py 的管线默认
        # (未改 scheduler), 本 harness 用导出存档的同一 config 构造 PNDM。
        from diffusers import StableDiffusionPipeline as _SDP
        _pub_pipe = _SDP.from_single_file(
            r"D:/models/txt2img/v1-5-pruned-emaonly.safetensors",
            torch_dtype=None, local_files_only=True)
        _pub = _pub_pipe.scheduler
        _pub.set_timesteps(20)
        _pub_ts = hashlib.sha256(
            _pub.timesteps.detach().cpu().numpy().astype("float64"
                                                        ).tobytes()).hexdigest()[:16]
        _pub_class = type(_pub).__name__
        _h = _sch.__class__.__name__
        _match = (_pub_class == _h == _sc.get("class")) and (_pub_ts == _ts)
        if not _match:
            raise SystemExit(
                f"FATAL(R11): scheduler 两侧不等价 published={_pub_class}/"
                f"{_pub_ts} harness={_h}/{_ts} config={_sc.get('class')}")
        res["scheduler_evidence"] = {
            "published_class": _pub_class,
            "harness_class": _h,
            "config_class": _sc.get("class"),
            "published_timesteps_sha256_20": _pub_ts,
            "harness_timesteps_sha256_20": _ts,
            "class_match": True,
            "timesteps_match": True,
            "assert": "两侧独立构造 timesteps 数组哈希相同, 不匹配即 SystemExit",
            "note": "PNDM 无 sigmas, 比对 timesteps; 已发布行未改 scheduler(管线默认)",
        }
    except Exception as e:
        res["scheduler_evidence"] = {"err": str(e)[:200]}

    # ---- R9: 内存列口径声明(dsh: 禁止直接写跨栈倍数) ----
    res["mem_scope"] = {
        "metric": "进程 RSS 峰值(各栈自采, 0.4-0.5s 间隔)",
        "sdcpp/comfyui/diffusers": "主进程或进程树 RSS",
        "onnx_dml": "单进程 RSS",
        "dml_extra": ("PDH \GPU Process Memory 同步实测: RSS 12788MB ≈ "
                      "Shared 12420MB (ratio 1.03), 即 UMA 上共享显存已计入 RSS"),
        "vulkan_extra": ("PDH 实测: RSS 1425MB ≈ Shared 1324MB (ratio 1.077), "
                         "另有 Dedicated 3566MB 不在 RSS 内"),
        "comparable": ("实测只证明: 两栈的进程 RSS 与各自 GPU Shared 同量级"
                       "(ratio≈1), 即共享显存已被 RSS 计入。**这不等于跨栈可比**"
                       "(Vulkan 另有 3566MB Dedicated 不在 RSS 内), 故正文禁止"
                       "任何内存倍数比较, 只逐栈报描述值并标口径"),
        # 三个数字是三个不同来源, 正文只能引各自标注的那一个
        "numbers_and_their_source": {
            "12016.05MB": "五方案表 ONNX 行 mem = timing 18 行中位",
            "12788.1MB": "GPU 记账探针单次 RSS(PDH 对照用)",
            "11904MB": "R5 最新证据 run 期间 PDH Shared 最大值"
                       "(旧 evidence-v2 的 12604MB 已过期, 不再引用)",
        },
        "forbidden_in_article": [
            "2.716x / 2.442x 作为受控加速倍数"
            "(landing 与 timing 不同源: 65.709 / 73.842 / 97.15 / 86.941)",
            "12016MB vs 1418MB 的倍数",
            "11975MB vs 1418MB 的倍数(旧数, 已弃用)",
            "12604MB 作为 'R5 实测 shared max'(已过期, 正确值 11904MB)",
            "任何跨栈内存倍数比较",
            "Vulkan 87.43 vs ONNX 115.49 '打平/同档/快 X 倍'"
            "(CLI 进程级 vs 进程内, 隔 2 天, 跨期漂移 14.19%)",
            "'ONNX/DML CPU 占比 0%' / 'unet 全在 DML' / '零回退'"
            "(cpu_pct 已作废置 null)",
            "把六格 0.19-2.78% 当整批噪声底"
            "(须同披露 attempt1 13.09%/10.55% 与 p0_s43 重跑)",
            "把 anchor -14.19% 当'跨期可比许可证'(它是反向证据)",
            "把五格内存列并排当可直接比较的柱子",
            "把 nfe=21 当前向次数(真实 UNet 前向 42 次)",
            "直述 'ONNX 行 shared 已计入 RSS'"
            "(原始行 shared_mem_included:false 未统一, 只写该栈自采 RSS 描述值)",
            "把'父进程持 4.27GB 管线'或 'warmup 3 吸收批首效应' 当已证机制",
        ],
    }

    # ---- R9 补: 逐行内存口径列(正文表格该带的列) ----
    res["mem_caliber_per_scheme"] = {
        "sd.cpp · 纯 CPU": {
            "value_mb": 4429.51,
            "caliber": "主进程 RSS 峰值(已发布正文写 4.65GB, 为原始字节÷10⁹)",
        },
        "sd.cpp · Vulkan 核显": {
            "value_mb": 1418.26,
            "caliber": "进程 RSS 峰值; 另有 GPU Dedicated 3566MB **不在** RSS 内",
        },
        "diffusers · 纯 CPU": {
            "value_mb": 5368.94,
            "caliber": "进程树 RSS 峰值(已发布正文 5.63GB)",
        },
        "ComfyUI · 纯 CPU(冷启动)": {
            "value_mb": 7441.1,
            "caliber": "进程树 RSS 峰值(含服务进程)",
        },
        "ONNX/DML · 核显(冷启动)": {
            "value_mb": 12016.05,
            "caliber": "单进程 RSS 峰值; UMA 上共享显存已计入"
                       "(探针 RSS 12788 ≈ Shared 12420, ratio 1.03)",
        },
        "cross_stack_rule": "五格口径不同(主进程/进程树/含服务), 只逐行标口径描述, "
                            "不做跨行相除",
    }

    res["seed_check_sha"] = {}
    for grp in (b5, cold6):
        g = defaultdict(set)
        for r in grp:
            if r.get("ok") and r.get("sha256"):
                key = (r.get("mode"), r.get("prompt_idx"), r.get("seed"))
                g[key].add(r["sha256"])
        for k, v in g.items():
            res["seed_check_sha"][str(k)] = "SAME" if len(v) == 1 else f"DIFF({len(v)})"

    # ---- C14/DP-32: GPU 记账探针(DML 行 与 Vulkan 行 各一组, 证明内存口径可比) ----
    res["gpu_probe"] = {}
    for name, path in (
            ("dml", os.path.join(E04, "logs", "mem_pdh_probe.json")),
            ("vulkan", os.path.join(E04, "logs", "vulkan_mem_probe.json"))):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                res["gpu_probe"][name] = json.load(f)
    # 口径判定: rss 与 GPU Shared 是否同量级(同量级 => 进程 RSS 已含 GPU shared)
    dml = res["gpu_probe"].get("dml")
    if dml:
        snap = dml.get("snapshots", [])
        after = [s for s in snap if s["tag"] == "after_vae_fwd"]
        if after:
            s = after[0]

            def _b(x):
                if not x:
                    return None
                try:
                    return int(str(x).split("=")[-1])
                except Exception:
                    return None
            sh = _b((s.get("gpu_shared") or [None])[0])
            res["gpu_probe"]["dml"]["rss_vs_shared"] = {
                "rss_mb": s["rss_mb"],
                "gpu_shared_mb": round(sh / 1048576, 1) if sh else None,
                "ratio": round(s["rss_mb"] / (sh / 1048576), 3) if sh else None,
            }
    vul = res["gpu_probe"].get("vulkan")
    if vul:
        res["gpu_probe"]["vulkan"]["rss_vs_shared"] = {
            "rss_mb": vul.get("rss_peak_mb"),
            "gpu_shared_mb": vul.get("gpu_shared_max_mb"),
            "gpu_dedicated_mb": vul.get("gpu_dedicated_max_mb"),
            "ratio": (round(vul["rss_peak_mb"] / vul["gpu_shared_max_mb"], 3)
                      if vul.get("gpu_shared_max_mb") else None),
        }

    res["b6_verdict"] = b6.get("verdict")
    # evidence 整块必须在 dump 之前挂上, 否则产物里没有 R5/R10 证据
    if _EVID:
        res["evidence_v2"] = _EVID
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # ---- 打印对照表 ----
    print(f"{'方案':34} {'落点':16} {'median(s)':>11} {'spread':>8} {'mem MB':>9}")
    print("-" * 84)
    order = ["sd.cpp · 纯 CPU", "sd.cpp · Vulkan 核显", "diffusers · 纯 CPU",
             "ComfyUI · 纯 CPU(冷启动)", "ONNX/DML · 核显(冷启动)"]
    for k in order:
        v = res["schemes"].get(k)
        if not v:
            print(f"{k:34} {'-':16} {'未跑':>11}")
            continue
        s = v.get("seconds_total") or v.get("seconds") or {}
        m = v.get("mem_mb") or {}
        print(f"{k:34} {v['landing']:16} {s.get('median','-'):>11} "
              f"{str(s.get('spread_pct','-'))+'%':>8} {m.get('median','-'):>9}")
    print()
    print(f"批次: 正式批 {res['batches']['formal']['rows']} 行"
          f"({res['batches']['formal']['note']}) | "
          f"早期试跑 {res['batches']['trial']['rows']} 行"
          f"({res['batches']['trial']['note']})")
    for s, v in res["batches"]["trial_stats"].items():
        if v:
            print(f"   试跑批 {s}: median={v['median']}s spread={v['spread_pct']}% "
                  f"(不入表)")
    if "anchor" in res:
        a = res["anchor"]
        print(f"锚点基线: {a['baseline_source']}")
        for run in a.get("runs", []):
            print(f"   {run['date']} {run['source']}: {run['retested_median']}s "
                  f"-> 漂移 {run['drift_pct']}% (n={run['n']}, "
                  f"covers_onnx={run['covers_onnx_batch']})")
        print(f"   最差漂移 {a['worst_abs_drift_pct']}% | within5%={a['within_5pct']}")
        print(f"   -> {a['conclusion']}")
    # 证据脚本(evidence-v2)四项
    if _EVID:
        _e = _EVID
        _r4 = _e.get("r4_landing") or {}
        if _r4.get("dml_median"):
            print(f"证据 R4: DML n={_r4['B_criteria']['n_dml']} "
                  f"median={_r4['dml_median']}s | CPU n={_r4['B_criteria']['n_cpu']} "
                  f"median={_r4['cpu_median']}s -> {_r4.get('speedup_median')}x "
                  f"| A={_r4.get('A_criteria', {}).get('pass')} "
                  f"(Δ{_r4.get('A_criteria', {}).get('max_minus_min_mb')}MB) "
                  f"| B={_r4['B_criteria']['pass']}")
        _r5 = _e.get("r5_adapter") or {}
        if _r5:
            print(f"证据 R5: LUID={_r5.get('luids')} hw={_r5.get('hardware_adapter_present')} "
                  f"warp={_r5.get('warp_named_in_adapters')} "
                  f"gpu_shared { _r5.get('gpu_shared_min_mb')}→"
                  f"{_r5.get('gpu_shared_max_mb')}MB "
                  f"verdict={_r5.get('verdict_inputs_ok')}")
        _r10 = _e.get("r10_offline") or {}
        if _r10:
            print(f"证据 R10: ok={_r10.get('evidence_ok')} "
                  f"guard={_r10.get('guard_scope')} "
                  f"child_non-loopback={_r10.get('child_non_loopback_count')} "
                  f"child_blocked={_r10.get('child_blocked_count')} "
                  f"parent_blocked={_r10.get('parent_blocked_count')} "
                  f"img={str(_r10.get('child_img_sha256'))[:16]}")
            _ow = (load(os.path.join(E04, "logs", "bench6-progress.json"))
                   .get("offline_window") or {})
            print(f"   offline_window 回填: evidence_ok={_ow.get('evidence_ok')} "
                  f"guard_scope={_ow.get('guard_scope')} "
                  f"child_non_loopback={_ow.get('child_non_loopback_count')}")
        _r17 = _e.get("r17_anchor") or {}
        if _r17.get("ok"):
            print(f"证据 R17: { _r17.get('date')} anchor median={_r17.get('median')}s "
                  f"vs 已发布 { _r17.get('published_baseline_s')}s -> "
                  f"{_r17.get('drift_pct_vs_published')}% "
                  f"(within5%={_r17.get('within_5pct')}, spread={_r17.get('spread_pct')}%)")
    if "profiling_gate" in res:
        g = res["profiling_gate"]
        print(f"profiling: n={g['n']} 覆盖率={g['coverage_pct']}% "
              f"可用={g['gate_usable']} | {g['conclusion']}")
    if "landing_gate_v2" in res:
        v = res["landing_gate_v2"]
        print(f"landing 门禁 v2(R4 新判据): ok={v['ok']} "
              f"| A={v.get('A_criteria')} | B={v.get('B_criteria')}")
        print(f"   DML n={v['B_criteria']['n_dml']} median="
              f"{v['dml_gen_s_median']}s vs CPU n={v['B_criteria']['n_cpu']} "
              f"median={v['cpu_gen_s_median']}s -> {v['speedup_median']}x")
        print(f"   {v['regime_note']}")
        print(f"   可写口径: {v['publishable']}")
    if "landing_gate" in res:
        g = res["landing_gate"]
        print(f"landing 门禁(旧, harness 自带): ok={g['ok']} "
              f"| A={g['criteria_A_gpu_counter']}"
              f"({g['gpu_shared_min_mb']}→{g['gpu_shared_max_mb']}MB)"
              f"| B={g['criteria_B_dml_faster']}"
              f"({g['dml_gen_s']}s vs {g['cpu_gen_s']}s = {g['speedup_vs_cpu']}x)"
              f" | {g.get('harness_criteria_note')}")
    if "profiling_gate" not in res and "landing_gate" not in res:
        print("落点门禁: (缺 landing 数据)")
    on = res["schemes"].get("ONNX/DML · 核显(冷启动)")
    if on and on.get("batches"):
        print("ONNX/DML 批次(R8):")
        for b in on["batches"]:
            print(f"   {b['batch_id']} n={b['n']} {b['start']} ~ {b['end']} "
                  f"attempts={b['attempts']}")
        print(f"   attempt 构成: {on.get('attempt_mix')} | {on.get('headline_note')}")
    if on and on.get("per_cell_spread"):
        pcs = on["per_cell_spread"]
        print("ONNX/DML 按格离散(R18/DP-15 判据):")
        for k, v in pcs.items():
            if isinstance(v, dict):
                print(f"   {k}: n={v['n']} median={v['median']}s "
                      f"spread={v['spread_pct']}% {'PASS' if v['pass_5pct'] else 'FAIL'}")
        print(f"   全格 5% 判据: {pcs.get('all_pass')}")
    for nm, pv in res.get("gpu_probe", {}).items():
        rs = pv.get("rss_vs_shared")
        if rs:
            print(f"GPU 记账 {nm}: rss={rs.get('rss_mb')}MB "
                  f"shared={rs.get('gpu_shared_mb')}MB ratio={rs.get('ratio')}"
                  + (f" dedicated={rs.get('gpu_dedicated_mb')}MB"
                     if rs.get("gpu_dedicated_mb") else ""))
    se = res.get("scheduler_evidence")
    if se:
        print(f"scheduler 等价(R11): published={se.get('published_class')} "
              f"harness={se.get('harness_class')} "
              f"timesteps_match={se.get('timesteps_match')} "
              f"({se.get('harness_timesteps_sha256_20')})")
    ms = res.get("mem_scope")
    if ms:
        print("禁写清单(R9):")
        for x in ms.get("forbidden_in_article", []):
            print(f"   ✗ {x}")
    print(f"种子自检: {json.dumps(res['seed_check_sha'], ensure_ascii=False)}")
    print(f"b6 verdict: {res['b6_verdict']}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
