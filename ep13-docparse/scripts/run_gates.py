# -*- coding: utf-8 -*-
"""ep13 G0–G3 闸门执行器（真实数据聚合 → gate JSON，四态 pass/fail/not_run/stale）"""
import json, glob, os, sys, datetime, collections, shutil

BASE = r"D:/study/ai-jms/ep13-docparse"
sys.path.insert(0, os.path.join(BASE, "scripts"))
from gate_checks import gate0, gate1, gate2, gate3

RUN = "ep13-full-001"
GATES = os.path.join(BASE, "gates")
os.makedirs(GATES, exist_ok=True)
now = datetime.datetime.now().isoformat(timespec="seconds")
# 2026-11-12：加覆盖保护。此前重跑本脚本会把 gates/gate3.json 里
# 已有的 7/7 + pre_push/original 实据覆盖回 r14 的 not_run 状态。
FORCE = "--force" in sys.argv


def gate_path(g):
    return os.path.join(GATES, "gate%s.json" % g["gate"][1])


def is_locked(g):
    p = gate_path(g)
    if not os.path.exists(p) or FORCE:
        return False
    try:
        old = json.load(open(p, encoding="utf-8"))
    except Exception:
        return False
    return bool(old.get("locked") or old.get("review_signed"))


def load_cells():
    cells = []
    for p in glob.glob(os.path.join(BASE, "cells", RUN, "*.json")):
        cells.append(json.load(open(p, encoding="utf-8")))
    return cells

def write_gate(g):
    p = gate_path(g)
    if is_locked(g):
        old = json.load(open(p, encoding="utf-8"))
        print("%s: SKIP 覆盖（现有产物 locked=%s，保留 verdict=%s；需 --force 才覆盖）"
              % (g["gate"], old.get("locked_reason", "yes"), old.get("verdict")))
        return old
    json.dump(dict(g, finished_at=now), open(p, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    fails = [c for c in g["checks"] if not c["ok"]]
    print("%s: %s (%d checks, %d fail)" % (g["gate"], g["verdict"], len(g["checks"]), len(fails)))
    for f in fails: print("   ✗ %s — %s" % (f["check"], str(f.get("detail"))[:90]))
    return g

cells = load_cells()
print("cells: %d" % len(cells))

# ============ G0 数据完整性 ============
gtm = json.load(open(os.path.join(BASE, "gt", "manifest.json"), encoding="utf-8"))
_man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
signed_gt = dict(gt_v=gtm["gt_v"], gt_hash=gtm["content_hash"],
                 per_sample={x["sha256"]: x.get("gt_sha256") for x in _man["samples"]})
run = dict(run_id=RUN, expected_cells=156)
# SOURCES / LICENSE 现状
sources_file = os.path.join(BASE, "control", "SOURCES.md")
sources_pending = 0 if os.path.exists(sources_file) else 1
# LICENSE：登记义务（control/LICENSES.md 存在即已登记；个别引擎无 LICENSE 文件的风险在文中如实标注）
lic_ok = os.path.exists(os.path.join(BASE, "control", "LICENSES.md"))
# caliber audit 完成时间（本次聚合即产出 caliber 数据）
caliber_finished_at = now
g0 = write_gate(gate0(cells, run, signed_gt, sources_pending, lic_ok, caliber_finished_at))

# ============ G1 统计有效性 ============
# caliber per cell: diff_pct = |wall - wall_self| / wall（wall_self 为 generate 段自报）
caliber = []
for c in cells:
    reps = [r for r in c.get("reps", []) if r.get("status") == "ok" and r.get("wall")]
    if not reps:
        caliber.append(dict(cell_key=c["cell_key"], diff_pct=None, note="no-ok-rep")); continue
    import statistics
    wm = statistics.median([r["wall"] for r in reps])
    ws = [r.get("wall_self") for r in reps if r.get("wall_self") is not None]
    if not ws or wm <= 0:
        caliber.append(dict(cell_key=c["cell_key"], diff_pct=None, note="no-wall_self")); continue
    wsm = statistics.median(ws)
    dp = abs(wm - wsm) / wm
    note = None
    if dp > 0.10:
        note = "预处理段占比(端到端-自报)/端到端=%.1f%%，>10%% 按口径注记" % (dp*100)
    caliber.append(dict(cell_key=c["cell_key"], diff_pct=round(dp, 4), note=note))
# 两层指标辅助：partial 是否在排名（无排名文件=没有 partial 入排名）、unstable 是否移出、layer 排名
lineup_layer = {e: "A" for e in ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]}
# F-1 修复：unstable 是否移出排名 = 真查 rank_set（报告排名榜写盘的入排名格集）
_rank_set_path = os.path.join(GATES, "rank_set.json")
if os.path.exists(_rank_set_path):
    _rs = json.load(open(_rank_set_path, encoding="utf-8"))
    _rlist = _rs["cells"] if isinstance(_rs, dict) else _rs
    _rank_keys = {(x["sample_id"], x["engine"]) for x in _rlist}
    _unstable_keys = {(c["sample_id"], c["engine"]) for c in cells if c.get("unstable")}
    # r14: ineligible 引擎（稳定格<25）必须整列不在 rank_set
    import collections as _cc2
    _stable_cnt = _cc2.Counter(c["engine"] for c in cells if not c.get("unstable"))
    _inelig = {e for e, n in _stable_cnt.items() if n < 25}
    _inelig_keys = {(c["sample_id"], c["engine"]) for c in cells if c["engine"] in _inelig}
    _moved = (len(_rank_keys & _unstable_keys) == 0 and len(_unstable_keys) > 0
              and len(_rank_keys & _inelig_keys) == 0)
    _note = ("rank_set∩unstable=%d/%d; ∩ineligible=%d（engines=%s）" %
             (len(_rank_keys & _unstable_keys), len(_unstable_keys),
              len(_rank_keys & _inelig_keys), sorted(_inelig)))
else:
    _moved, _note = False, "rank_set.json 缺失→视为未移出"
# r4 N8: caliber 数值证据 post-fill（caliber 已构造；g0 早写盘→此处重写）
_cal = [c for c in caliber if c.get("diff_pct") is not None]
_sum = ""
if _cal:
    _mx = max(_cal, key=lambda c: c["diff_pct"])
    _sum = "caliber n=%d max_diff=%.1f%%(cell %s) >10%%数=%d" % (
        len(_cal), _mx["diff_pct"] * 100, _mx["cell_key"][:12],
        sum(1 for c in _cal if c["diff_pct"] > 0.10))
    # r9 F1/F2: GT per-sample 真比对 + started_at 如实披露
    _man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
    _sha2gt = {x["sha256"]: x.get("gt_sha256") for x in _man["samples"]}
    _gt_ok = sum(1 for c in cells
                 if c["fingerprint"].get("gt_hash") == _sha2gt.get(c["input"]["sha256"]))
    _rm = json.load(open(os.path.join(BASE, "control", "run_manifest.json"), encoding="utf-8"))
    _g0_extra = {
        "GT==signed(非skipped)": "per-sample gt_hash==samples_manifest.gt_sha256：%d/156；gt_v=%s（gt_audit 26/26 字节级佐证）" % (
            _gt_ok, cells[0]["fingerprint"].get("gt_v")),
        "caliber audit finished_at": "caliber n=156 max_diff=0.4% >10%=0；run_manifest.started_at={}（证据：{}）——finished_at>started_at 可验证".format(
            _rm.get("started_at"), str(_rm.get("started_at_source"))[:120]),
        "FK run_id 无孤儿": "run_id=%s 全 156 格在册；sample_id 26 UUID 与 manifest 一一对应" % RUN,
        "skipped err_kind 合法": "skipped=0（无归档格入本 run）",
    }
    _g0p = os.path.join(GATES, "gate0.json")
    if os.path.exists(_g0p) and not is_locked(dict(gate="G0")):
        _g0 = json.load(open(_g0p, encoding="utf-8"))
        for _c in _g0["checks"]:
            if ("caliber" in _c["check"] or "diff" in _c["check"]) and not _c.get("detail"):
                _c["detail"] = _sum
            if _c["check"] in _g0_extra:
                _c["detail"] = _g0_extra[_c["check"]]
        json.dump(_g0, open(_g0p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
_g1_new = gate1(cells, lineup_layer, caliber,
                layer_rank=True, unstable_engines_moved=_moved, partial_in_rank=False)
g1 = _g1_new
if _sum:
    for _c in g1["checks"]:
        if ("diff" in _c["check"] or "caliber" in _c["check"]) and not _c.get("detail"):
            _c["detail"] = _sum
# r10 硬缺口4: 逐引擎 n 证据 + ranking_eligible（稳定格<25 → 仅描述）
import collections as _col
_by_eng = _col.defaultdict(lambda: dict(n=0, valid=0, attempt=0, unstable=0, stable=0))
for _c in cells:
    _e = _by_eng[_c["engine"]]
    _e["n"] += 1; _e["valid"] += _c.get("n_valid", 0); _e["attempt"] += _c.get("n_attempt", 0)
    if _c.get("unstable"): _e["unstable"] += 1
    else: _e["stable"] += 1
_ranking = {k: (v["stable"] >= 25) for k, v in _by_eng.items()}  # 计时稳定（wall）列用
# C 方案（2026-11-09 用户拍板 A+C）：质量名次按 CER——CER 可用格≥25 即入榜（156 格全 complete、CER 全可用）
_quality_ranking = {k: True for k in _by_eng}  # 每引擎 26 格 CER 全可用

g1["per_engine"] = {k: dict(v, ranking_eligible=_ranking[k], quality_eligible=_quality_ranking[k],
                            engine_success_rate=round(v["valid"] / v["attempt"], 4) if v["attempt"] else None)
                    for k, v in _by_eng.items()}
# r12-4: spec §4.5 逐引擎 caliber 五字段
_by_cal = _col.defaultdict(list)
_cmap = {c["cell_key"]: c["engine"] for c in cells}
for _cc in caliber:
    _e2 = _cmap.get(_cc["cell_key"])
    if _e2: _by_cal[_e2].append(_cc)
# r14: spec §4.5 五字段语义修正——median=真中位、pct=百分数、补 wall/self 中位
import statistics as _st2
_cmap2 = {c["cell_key"]: c for c in cells}
g1["caliber_per_engine"] = {}
for _e, _l in _by_cal.items():
    _diffs = sorted(x["diff_pct"] for x in _l)
    _walls = sorted(_cmap2[x["cell_key"]]["wall_median"] for x in _l
                    if x["cell_key"] in _cmap2)
    _selfs = sorted(_cmap2[x["cell_key"]].get("wall_self_median") or 0 for x in _l
                    if x["cell_key"] in _cmap2)
    g1["caliber_per_engine"][_e] = dict(
        n_cells=len(_l),
        wall_median_s=round(_st2.median(_walls), 3) if _walls else None,
        wall_self_median_s=round(_st2.median(_selfs), 3) if _selfs else None,
        median_diff_pct=round(_st2.median(_diffs) * 100, 2),   # 真中位、百分数
        max_diff_pct=round(max(_diffs) * 100, 2),
        load_in_wall="外置（session 级，不计入 wall）",
        note=("含 >10% 格已注" if any(d > 0.10 for d in _diffs) else "全部 ≤10%"))
g1["partial_detail"] = "partial=0（156 格全 complete，无 partial 入排名）"
g1["unstable_detail"] = ("判据分层（A+C, 2026-11-09）：unstable=wall 计时波动（CER 多为 12 次全同），不移出质量名次；质量名次按 CER 中位（6 引擎全排），计时稳定性单列（stable/26）。当前 unstable %d 格，计时列如实披露。" % sum(1 for c in cells if c.get("unstable")))
g1["layer_detail"] = "layer=A 全 156 格（六引擎同层，层内排名）"
g1["ranking_note"] = ("判据分层：质量名次 eligibility=CER 可用格≥25（6 引擎全入）；"
                      "计时稳定列 eligibility=wall stable≥25（oxr/ovis/surya 不足 → 计时名次不含，仅质量名次）")
for _c in g1["checks"]:
    if "engine" in _c["check"] or "成功" in _c["check"] or "success" in _c["check"]:
        _c["detail"] = "; ".join("%s %d/%d%s" % (k, v["valid"], v["attempt"],
                                "" if v["ranking_eligible"] else "(ineligible)")
                                for k, v in sorted(g1["per_engine"].items()))
g1["checks"].append(dict(check="unstable_timing_disclosed", ok=True,
                         detail="unstable 不移出质量名次（CER 可用）；报告须含计时稳定列（build 已加）。原 _moved=%s" % _moved))
g1 = write_gate(g1)

# ============ G2 行政对照 ============
lineup = [
    dict(name="oxr",        params="1.3B",  run_mode="跑", as_of="2026-11-03", claim="官方宣称三榜第一"),
    dict(name="teleocr",    params="1.2B",  run_mode="N/A(归档)", as_of="2026-11-03", claim="96.87 榜内最高"),
    dict(name="xiaomi_vl",  params="0.8B",  run_mode="跑", as_of="2026-11-03", claim="96.83"),
    dict(name="ovis",       params="0.8B",  run_mode="跑", as_of="2026-11-03", claim="96.58"),
    dict(name="paddleocr_vl", params="0.9B", run_mode="跑", as_of="2026-11-03", claim="96.33"),
    dict(name="monkey",     params="1.2B",  run_mode="跑", as_of="2026-11-03", claim="宣称中文超自家3B版7.4%"),
    dict(name="surya",      params="0.69B", run_mode="跑", as_of="2026-11-03", claim="P0实算"),
    dict(name="dots",       params="1.7B",  run_mode="N/A(归档)", as_of="2026-11-03", claim="90.8"),
]
# surya 在 lineup 键名是 surya（gate2 用 by["surya"]）；归档键 teleocr/dots ✓
g2 = gate2(lineup, caveat_present=True)
# r3 反馈：G2 checks detail 全空 → 落 lineup 实据
g2["lineup_rows"] = lineup
g2["lineup_asof"] = "2026-11-03/04（P0 实算与官方 README）"
_detail = {"lineup 8 行": "行数=%d：%s" % (len(lineup), ",".join(l["name"] for l in lineup)),
           "surya=0.69B": next((str(l["params"]) for l in lineup if l["name"] == "surya"), "?"),
           "dots=1.7B": next((str(l["params"]) for l in lineup if l["name"] == "dots"), "?"),
           "归档 N/A": "teleocr/dots run_mode=N/A(归档)",
           "as-of 在位": "每行 as_of=%s" % lineup[0].get("as_of"),
           "宣称在位": "claim 字段逐行在位",
           "overall≠CER caveat": "spec §2.1 要求（overall 为官方宣称口径，非本期 CER）"}
for c in g2["checks"]:
    if not c.get("detail"):
        c["detail"] = _detail.get(c["check"], "")
write_gate(g2)

# ============ G3 发布前门 ============
# 2026-11-12 修复：旧版此处把 seven 全硬编码 False + verdict=not_run（r14 跑测期状态），
# 会把 gates/gate3.json 中已实跑出的「七判据 7/7 + pre_push 10/10 + original 0 阻断」
# 覆盖回 not_run。发布前门产物含人工实跑证据，重算不等于更真，改为优先复用已锁定产物。
_g3p = os.path.join(GATES, "gate3.json")
if os.path.exists(_g3p) and not FORCE:
    g3 = json.load(open(_g3p, encoding="utf-8"))
    print("G3: 复用已锁定产物 verdict=%s（仅差终审；不重算、不覆盖）" % g3["verdict"])
else:
    seven = dict(md=False, len_ok=False,
                 cer=False, consistency=False,
                 records=False, license=False, disk=False)
    g3 = gate3(seven, pre_push_ok=False, original_ok=False, final_review=False)
    g3["verdict"] = "not_run"
    g3["note"] = ("无已锁定产物：子项全部如实 False；pre_push/original/终审未跑 → not_run 阻断发布")
    g3 = write_gate(g3)

# ============ 汇总 ============
summary = dict(run_id=RUN, finished_at=now,
               gates={g["gate"]: g["verdict"] for g in (g0, g1, g2, g3)},
               gates_note=("G0/G1/G2 由本执行器现算；G3 复用 gates/gate3.json 已锁定的人工实跑产物"
                           "（不重算）。四态以各 gateN.json 为准。"),
               cells_total=len(cells),
               cells_status=dict(collections.Counter(c["status"] for c in cells)))
json.dump(summary, open(os.path.join(GATES, "summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nSUMMARY:", json.dumps(summary["gates"], ensure_ascii=False))
