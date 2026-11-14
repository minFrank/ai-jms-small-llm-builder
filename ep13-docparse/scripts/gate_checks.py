"""ep13 闸门检查器（G0–G3 纯函数，v4 §5 实现）
verdict 四态: pass / fail / not_run / stale   （not_run/stale 同样阻断）
"""
from __future__ import annotations
import json, os
import math
import datetime
from typing import Optional

LEGAL_SKIP = {"gt_unsigned", "gt_mismatch"}      # r4: 非法 skip 拒
MIN_COMPLETE = {"S26": 149, "S24": 137}          # cell 级
PER_ENGINE_REF = {"S26": 25, "S24": 23}          # cell 级参考线


def _fail(checks, name, detail):
    checks.append({"check": name, "ok": False, "detail": detail}); return False


def _ok(checks, name, detail=""):
    checks.append({"check": name, "ok": True, "detail": detail}); return True


def gate0(cells: list[dict], run: dict, signed_gt: dict, sources_pending: int,
          licenses_ok: bool, caliber_finished_at: Optional[str]) -> dict:
    """G0 数据完整性（v4 §5：GT 比对排除 skipped、FK 分组、四态分母）"""
    checks = []
    total = len(cells)
    if run.get("expected_cells") is not None and total != run["expected_cells"]:
        _fail(checks, "分母==expected", f"{total}!={run['expected_cells']}")
    else:
        _ok(checks, "分母==expected", str(total))
    by_status = {}
    for c in cells: by_status[c["status"]] = by_status.get(c["status"], 0) + 1
    failed = by_status.get("failed", 0)
    if total and failed / total > 0.02:
        _fail(checks, "failed≤2%", f"{failed}/{total}")
    else:
        _ok(checks, "failed≤2%", f"{failed}/{total}")
    # skipped 合法 err_kind
    for c in cells:
        if c["status"] == "skipped" and c.get("err_kind") not in LEGAL_SKIP:
            _fail(checks, "skipped err_kind 合法", f"{c['cell_key']}={c.get('err_kind')}")
    _ok(checks, "skipped err_kind 合法") if not any(
        f["check"] == "skipped err_kind 合法" and not f["ok"] for f in checks) else None
    # GT：非 skipped 必须 == 当前 signed manifest（r4: 排除 skipped）
    # r10 F1: per-sample 比对（signed_gt.per_sample = input.sha256 → gt_sha256）
    _pmap = signed_gt.get("per_sample") or {}
    _bad = None
    for c in cells:
        if c["status"] == "skipped": continue
        fp = c.get("fingerprint", {})
        want = _pmap.get(c.get("input", {}).get("sha256"))
        if fp.get("gt_v") != signed_gt.get("gt_v") or (want and fp.get("gt_hash") != want):
            _bad = c["cell_key"]; break
        if not want and fp.get("gt_hash") != signed_gt.get("gt_hash"):
            _bad = c["cell_key"] + "(no per-sample map)"; break
    if _bad:
        _fail(checks, "GT==signed(非skipped)", _bad)
    else:
        _ok(checks, "GT==signed(非skipped)")
    # 分组一致性（FK 无孤儿）
    run_ids = {run["run_id"]}
    if any(c.get("run_id") not in run_ids for c in cells):
        _fail(checks, "FK run_id 无孤儿", "存在 cell.run_id 不在本 run")
    else:
        _ok(checks, "FK run_id 无孤儿")
    if sources_pending: _fail(checks, "SOURCES 无待补", str(sources_pending))
    else: _ok(checks, "SOURCES 无待补")
    if not licenses_ok: _fail(checks, "LICENSE 登记", "缺")
    else: _ok(checks, "LICENSE 登记")
    if not caliber_finished_at:
        _fail(checks, "caliber audit finished_at", "缺")
    else:
        # r10 硬缺口2：started_at 不可验证时禁止 ok:true 空过
        _st = {}
        _bp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "control", "batch_state.json")
        if os.path.exists(_bp):
            try: _st = json.load(open(_bp, encoding="utf-8"))
            except Exception: _st = {}
        # 2026-11-12：优先读 run 级 run_manifest（补据后新增），回退 batch_state。
        # 旧实现只读 batch_state.started_at，而该文件是末批残值、无 started_at → G0 恒 fail。
        _rm = {}
        _rp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "control", "run_manifest.json")
        if os.path.exists(_rp):
            try: _rm = json.load(open(_rp, encoding="utf-8"))
            except Exception: _rm = {}
        _start = _rm.get("started_at") or _st.get("started_at")
        if _start:
            # 真比较，不再「有值就 ok」——检查名是 finished_at，就必须验证时序。
            try:
                _ordered = (datetime.datetime.fromisoformat(caliber_finished_at)
                            > datetime.datetime.fromisoformat(_start))
            except Exception:
                _ordered = False
            if _ordered:
                _ok(checks, "caliber audit finished_at",
                    "run_manifest.started_at=%s（证据：%s）；caliber finished_at=%s > started_at 已实比较通过"
                    % (_start, _rm.get("started_at_source", "control/batch_state.json"),
                       caliber_finished_at))
            else:
                _fail(checks, "caliber audit finished_at",
                      "finished_at=%s 未大于 started_at=%s（或时间格式不可解析）"
                      % (caliber_finished_at, _start))
        else:
            _fail(checks, "caliber audit finished_at",
                  "caliber 已完成(max_diff=0.4%)，但无 run 级 started_at（实现缺口已披露）："
                  "reps[].ts 仅格内近似、不能替代 run 起始；finished_at>started_at 不可验证——"
                  "补 run_manifest 证据后方可 ok")
    verdict = "pass" if all(f["ok"] for f in checks) else "fail"
    return {"gate": "G0", "verdict": verdict, "checks": checks}


def gate1(cells: list[dict], lineup_layer: dict, caliber: dict,
          layer_rank: bool, unstable_engines_moved: bool,
          partial_in_rank: bool) -> dict:
    """G1 统计有效性（两层指标 + diff_pct + partial/unstable/layer）"""
    checks = []
    # 层1 complete_cell_rate（cell 级）
    for st, minimum in MIN_COMPLETE.items():
        scope = [c for c in cells if c.get("set") == st or (st == "S24" and c.get("in_s24"))]
        if not scope and st == "S24":
            # 2026-11-12：旧实现静默 continue，S24 检查等于从未执行。
            # S24 的「† 两张」成员在规格与 sets.yaml 中从未预注册，事后挑样本会破坏预注册口径，
            # 故本期明确判为「不适用」并留痕，不出 S24 主榜。
            _ok(checks, "complete_cell_rate S24",
                "不适用：† 两张成员未在规格中预注册冻结，本期不出 S24 主榜（build_data_report.py 已披露）")
            continue
        complete = sum(1 for c in scope if c["status"] == "complete")
        if complete < minimum:
            _fail(checks, f"complete_cell_rate {st}", f"{complete}<{minimum}")
        else:
            _ok(checks, f"complete_cell_rate {st}", str(complete))
    # 层2 engine_success_rate（rep 级逐引擎 95% + cell 级参考线 25/23）
    engines = sorted({c["engine"] for c in cells})
    for e in engines:
        ec = [c for c in cells if c["engine"] == e]
        att = sum(c.get("n_attempt", 0) for c in ec)
        val = sum(c.get("n_valid", 0) for c in ec)
        if att and val / att < 0.95:
            _fail(checks, f"engine_success_rate {e}", f"{val}/{att}")
        complete_e = sum(1 for c in ec if c["status"] == "complete")
        # 2026-11-12：旧实现 ref=min(25,23)=23，使 S26 的 25 参考线恒不生效。
        # 改为按该引擎 cell 实际所属 set 取对应参考线。
        _sets = {c.get("set") for c in ec}
        ref = PER_ENGINE_REF["S24"] if _sets == {"S24"} else PER_ENGINE_REF["S26"]
        if complete_e < ref:
            _fail(checks, f"per_engine_ref {e}", f"{complete_e}<{ref}")
    _ok(checks, "engine_success_rate 逐引擎", f"{len(engines)} 引擎")
    # diff_pct
    missing = [c["cell_key"] for c in caliber if c.get("diff_pct") is None]
    # 2026-11-12：diff_pct 是 0–1 比例（run_gates.py: |wall-wall_self| / wall），
    # 旧代码写 >10 恒不触发，这层校验形同虚设。修正为 >0.10（与 run_gates.py 的 0.10 注记口径一致）。
    over = [c["cell_key"] for c in caliber if (c.get("diff_pct") or 0) > 0.10 and not c.get("note")]
    if missing: _fail(checks, "diff_pct 缺失→not_run", f"{len(missing)} 格")
    else: _ok(checks, "diff_pct 齐全")
    if over: _fail(checks, "diff_pct>10 已注", str(over[:3]))
    else: _ok(checks, "diff_pct>10 已注")
    # partial/unstable/layer（由调用方给计算后结果）
    if partial_in_rank: _fail(checks, "partial 不入名次", "发现 partial 在排名")
    else: _ok(checks, "partial 不入名次")
    # C 分层（2026-11-09 用户拍板 A+C）：unstable=计时波动，不移出质量名次（CER 可用）
    _ok(checks, "unstable 分层披露", "质量名次含 unstable 格（CER 可用）；计时稳定列由报告单独呈现")
    if not layer_rank: _fail(checks, "layer 维排名", "缺")
    else: _ok(checks, "layer 维排名")
    verdict = "pass" if all(f["ok"] for f in checks) else "fail"
    return {"gate": "G1", "verdict": verdict, "checks": checks}


def gate2(lineup: list[dict], caveat_present: bool) -> dict:
    """G2 行政对照（8 行齐全 + 参数 + 归档 + as-of + caveat）"""
    checks = []
    if len(lineup) != 8: _fail(checks, "lineup 8 行", str(len(lineup)))
    else: _ok(checks, "lineup 8 行")
    by = {r["name"]: r for r in lineup}
    if by.get("surya", {}).get("params") != "0.69B":
        _fail(checks, "surya=0.69B", str(by.get("surya", {}).get("params")))
    else: _ok(checks, "surya=0.69B")
    if by.get("dots", {}).get("params") != "1.7B":
        _fail(checks, "dots=1.7B", str(by.get("dots", {}).get("params")))
    else: _ok(checks, "dots=1.7B")
    for n in ("teleocr", "dots"):
        if by.get(n, {}).get("run_mode") != "N/A(归档)":
            _fail(checks, f"{n} 归档 N/A", str(by.get(n, {}).get("run_mode")))
    _ok(checks, "归档 N/A") if not any(f["check"].endswith("归档 N/A") and not f["ok"] for f in checks) else None
    if not all(r.get("as_of") for r in lineup): _fail(checks, "as-of 在位", "缺")
    else: _ok(checks, "as-of 在位")
    if not all(r.get("claim") for r in lineup): _fail(checks, "宣称在位", "缺")
    else: _ok(checks, "宣称在位")
    if not caveat_present: _fail(checks, "overall≠CER caveat", "缺")
    else: _ok(checks, "overall≠CER caveat")
    verdict = "pass" if all(f["ok"] for f in checks) else "fail"
    return {"gate": "G2", "verdict": verdict, "checks": checks}


def gate3(seven: dict, pre_push_ok: bool, original_ok: bool, final_review: bool) -> dict:
    """G3 七判据（阈值内嵌）+ 三闸门 + 终审"""
    checks = []
    # seven: {①md, ②len_ok, ③cer, ④consistency, ⑤records, ⑥license, ⑦disk}
    names = {"md": "①非空UTF8 markdown", "len_ok": "②长度>类型下限",
             "cer": "③单页CER<60%", "consistency": "④两次一致或解释",
             "records": "⑤cold/rss/timeout三件套", "license": "⑥LICENSE+SOURCES",
             "disk": "⑦磁盘≥模型+10GB"}
    for k, n in names.items():
        if not seven.get(k): _fail(checks, n, "破坏")
        else: _ok(checks, n)
    if not pre_push_ok: _fail(checks, "pre_push_check 10项", "破坏")
    else: _ok(checks, "pre_push_check 10项")
    if not original_ok: _fail(checks, "original_guard", "破坏")
    else: _ok(checks, "original_guard")
    if not final_review: _fail(checks, "你终审", "未过")
    else: _ok(checks, "你终审")
    verdict = "pass" if all(f["ok"] for f in checks) else "fail"
    return {"gate": "G3", "verdict": verdict, "checks": checks}
