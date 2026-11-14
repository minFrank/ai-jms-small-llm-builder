"""C 组：G0–G3 fail fixture（dsh r4 C 组名单——每个破坏项必须 fail、基线必须 pass）
跑法: python scripts/test_gate_fixtures.py
"""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_checks import gate0, gate1, gate2, gate3

PASS, FAIL = 0, []
def check(name, cond, detail=""):
    global PASS
    if cond: PASS += 1
    else: FAIL.append(f"{name}: {detail}")

def base_cell(i=0, **ov):
    c = dict(schema=6, run_id="ep13-t", cell_key=f"00000000-0000-0000-0000-00000000000{i}__oxr__p1",
             engine="oxr", layer="A", sample_id=f"s{i}", set="S26", status="complete",
             n_attempt=6, n_valid=6, err_kind=None,
             fingerprint={"gt_v": "v1", "gt_hash": "h1"})
    c.update(ov); return c

def g0_env(n_complete=149, extra=None, **kw):
    cells = [base_cell(i) for i in range(n_complete)]
    if extra: cells += extra
    run = dict(run_id="ep13-t", expected_cells=len(cells))
    signed = dict(gt_v="v1", gt_hash="h1")
    d = dict(run=run, signed_gt=signed, sources_pending=0, licenses_ok=True,
             caliber_finished_at="2026-11-04T00:00:00")
    d.update(kw); return cells, d

# ---- G0 基线 pass ----
cells, d = g0_env()
r = gate0(cells, **d); check("G0-基线", r["verdict"]=="pass", str([f for f in r["checks"] if not f["ok"]]))
# G0-f1: 1 个未签 skip（合法 err_kind → 单列不误杀，仍 pass）
cells, d = g0_env(extra=[base_cell(99, status="skipped", err_kind="gt_unsigned", n_attempt=0, n_valid=0)])
d["run"]["expected_cells"] = len(cells)
r = gate0(cells, **d); check("G0-未签skip单列", r["verdict"]=="pass", str([f for f in r["checks"] if not f["ok"]]))
# G0-f2: failed > 2%
cells, d = g0_env(extra=[base_cell(98, status="failed", err_kind="cell_fatal")]*4)
d["run"]["expected_cells"] = len(cells)
r = gate0(cells, **d); check("G0-failed超2%", r["verdict"]=="fail")
# G0-f3: 非法 skip err_kind（timeout 不在合法集）
cells, d = g0_env(extra=[base_cell(97, status="skipped", err_kind="timeout")])
d["run"]["expected_cells"] = len(cells)
r = gate0(cells, **d); check("G0-非法skip", r["verdict"]=="fail")
# G0-f4: run 级 GT mismatch（非 skipped cell 指纹≠signed）
cells, d = g0_env(extra=[base_cell(96, fingerprint={"gt_v": "v0", "gt_hash": "h0"})])
d["run"]["expected_cells"] = len(cells)
r = gate0(cells, **d); check("G0-GT不符", r["verdict"]=="fail")
# G0-f5: FK 孤儿（run_id 不符）
cells, d = g0_env(extra=[base_cell(95, run_id="ep13-other")])
d["run"]["expected_cells"] = len(cells)
r = gate0(cells, **d); check("G0-FK孤儿", r["verdict"]=="fail")
# G0-f6: SOURCES 待补 / LICENSE 缺 / caliber 缺（三项各破坏）
cells, d = g0_env(sources_pending=1); r = gate0(cells, **d)
check("G0-SOURCES待补", r["verdict"]=="fail")
cells, d = g0_env(licenses_ok=False); r = gate0(cells, **d)
check("G0-LICENSE缺", r["verdict"]=="fail")
cells, d = g0_env(caliber_finished_at=None); r = gate0(cells, **d)
check("G0-caliber缺", r["verdict"]=="fail")

# ---- G1 ----
def g1_env(**kw):
    cells = [base_cell(i) for i in range(156)]
    caliber = [{"cell_key": c["cell_key"], "diff_pct": 3.0, "note": None} for c in cells]
    d = dict(cells=cells, lineup_layer={e: "A" for e in ["oxr"]}, caliber=caliber,
             layer_rank=True, unstable_engines_moved=True, partial_in_rank=False)
    d.update(kw); return d
r = gate1(**g1_env()); check("G1-基线", r["verdict"]=="pass", str([f for f in r["checks"] if not f["ok"]]))
# G1-f1: complete 149 不达标（148）
dd = g1_env(); dd["cells"] = [base_cell(i) for i in range(148)] + \
     [base_cell(200, status="partial", n_attempt=8, n_valid=5)]
r = gate1(**dd); check("G1-149不达标", r["verdict"]=="fail")
# G1-f2: engine_success_rate <95%（一引擎 60%）
dd = g1_env()
for c in dd["cells"][:50]: c.update(n_attempt=10, n_valid=6)   # 60%
r = gate1(**dd); check("G1-成功率<95%", r["verdict"]=="fail")
# G1-f3: diff_pct>10 未注
dd = g1_env(); dd["caliber"][0]["diff_pct"] = 15.0
r = gate1(**dd); check("G1-diff>10未注", r["verdict"]=="fail")
# G1-f4: diff_pct 缺失 → not_run 阻断
dd = g1_env(); dd["caliber"][0]["diff_pct"] = None
r = gate1(**dd); check("G1-diff缺失", r["verdict"]=="fail")
# G1-f5: partial 混排名
dd = g1_env(partial_in_rank=True); r = gate1(**dd)
check("G1-partial混排名", r["verdict"]=="fail")
# G1-f6: unstable 未移出
dd = g1_env(unstable_engines_moved=False); r = gate1(**dd)
check("G1-unstable未移", r["verdict"]=="fail")
# G1-f7: layer 排名缺
dd = g1_env(layer_rank=False); r = gate1(**dd)
check("G1-layer缺", r["verdict"]=="fail")

# ---- G2 ----
def lineup():
    L = []
    for n, p in [("oxr","0.9B"),("paddleocr_vl","1.6B"),("xiaomi_vl","7B"),
                 ("ovis_ocr2","0.85B"),("monkey_rec","7B"),("surya","0.69B"),
                 ("teleocr","2.7B"),("dots","1.7B")]:
        L.append(dict(name=n, params=p, run_mode=("N/A(归档)" if n in ("teleocr","dots") else "跑"),
                      as_of="2026-11", claim="官方"))
    return L
r = gate2(lineup(), caveat_present=True); check("G2-基线", r["verdict"]=="pass", str([f for f in r["checks"] if not f["ok"]]))
L = lineup(); L[5]["params"] = "未核"; r = gate2(L, True); check("G2-surya参数错", r["verdict"]=="fail")
L = lineup()[:7]; r = gate2(L, True); check("G2-7行缺1", r["verdict"]=="fail")
L = lineup(); L[6]["run_mode"] = "跑"; r = gate2(L, True); check("G2-归档N/A缺", r["verdict"]=="fail")
L = lineup(); L[0]["as_of"] = ""; r = gate2(L, True); check("G2-as-of缺", r["verdict"]=="fail")
L = lineup(); L[0]["claim"] = ""; r = gate2(L, True); check("G2-宣称缺", r["verdict"]=="fail")
r = gate2(lineup(), caveat_present=False); check("G2-caveat缺", r["verdict"]=="fail")
L = lineup(); L[7]["params"] = "3B"; r = gate2(L, True); check("G2-dots参数错", r["verdict"]=="fail")

# ---- G3 ----
def seven(**kw):
    d = dict(md=True, len_ok=True, cer=True, consistency=True, records=True,
             license=True, disk=True); d.update(kw); return d
r = gate3(seven(), True, True, True); check("G3-基线", r["verdict"]=="pass", str([f for f in r["checks"] if not f["ok"]]))
for k, n in [("md","①md破坏"),("len_ok","②长度破坏"),("cer","③CER破坏"),
             ("consistency","④一致性破坏"),("records","⑤三件套破坏"),
             ("license","⑥LICENSE破坏"),("disk","⑦磁盘破坏")]:
    r = gate3(seven(**{k: False}), True, True, True)
    check(f"G3-{n}", r["verdict"]=="fail")
r = gate3(seven(), False, True, True); check("G3-pre_push破坏", r["verdict"]=="fail")
r = gate3(seven(), True, False, True); check("G3-original破坏", r["verdict"]=="fail")
r = gate3(seven(), True, True, False); check("G3-终审未过", r["verdict"]=="fail")

print(f"C 组: PASS={PASS}  FAIL={len(FAIL)}")
for f in FAIL: print("  ✗", f)
sys.exit(1 if FAIL else 0)
