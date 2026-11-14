"""四组定向测试 · A（协议A九例）+ B（schema 正反例）—— dsh r4 定义的可执行判据
跑法: python scripts/test_design.py   （在 ep13-docparse/ 根，venv 任意 python≥3.10）
"""
import sys, os, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell_runner import Cell, Rep, run, CellFatal, WorkerFatal, TARGET_VALID

PASS, FAIL = 0, []
def check(name, cond, detail=""):
    global PASS
    if cond: PASS += 1
    else: FAIL.append(f"{name}: {detail}")

# ---------------- mock worker ----------------
class MockWorker:
    """script: 元素 = 'ok'(wall=100+i), 'fail', 'timeout' 或 Exception 实例"""
    def __init__(self, script):
        self.script = list(script); self.i = 0; self.respawned = 0
    def infer(self, timeout):
        if self.i >= len(self.script):
            raise AssertionError("script 耗尽——attempt 超出预期")
        item = self.script[self.i]; self.i += 1
        if isinstance(item, Exception): raise item
        if isinstance(item, tuple) and item[0] == "ok":
            return dict(status="ok", wall=float(item[1]), wall_self=float(item[1]) - 1,
                        cer=0.05, truncated=False, err_kind=None, ts="t")
        if item == "ok":
            wall = 100.0 + self.i
            if isinstance(item, tuple): wall = item[1]
            return dict(status="ok", wall=wall, wall_self=wall - 1,
                        cer=0.05, truncated=False, err_kind=None, ts="t")
        if isinstance(item, tuple) and item[0] == "ok":
            return dict(status="ok", wall=float(item[1]), wall_self=float(item[1]) - 1,
                        cer=0.05, truncated=False, err_kind=None, ts="t")
        if item == "fail":
            return dict(status="fail", wall=None, wall_self=None, cer=None,
                        truncated=None, err_kind="extract_fail", ts="t")
        if item == "timeout":
            return dict(status="timeout", wall=None, wall_self=None, cer=None,
                        truncated=None, err_kind="timeout", ts="t")
        raise AssertionError(item)
    def respawn(self): self.respawned += 1

def new_cell(**kw):
    c = Cell()
    c.base = dict(schema=6, run_id="ep13-test", cell_key="00000000-0000-0000-0000-000000000000__oxr__p1",
                  engine="oxr", layer="A", sample_id="s", set="S26",
                  input=dict(kind="image", sha256="0"*64, page_no=1, dpi=300),
                  fingerprint=dict(git="g", weights_sha="w", deps="d", config_hash="c",
                                   extract_v="e", gt_v="v", gt_hash="h", sample_sha="s",
                                   engine_version="ev", host_manifest_id="hm", seed=1, order=1))
    return c

def exec_cell(script):
    c = new_cell(); w = MockWorker(script)
    saved = []
    run(c, w, save_raw=lambda p: saved.append(p), validate_soft=lambda p: None)
    return c, w, saved

# ---------------- A 组九例 ----------------
# ① 6 次 ok → complete, n_attempt=6
c, w, _ = exec_cell(["ok"]*6)
r = c.finish()
check("A①", r["status"]=="complete" and r["n_attempt"]==6 and r["n_valid"]==6,
      f"{r['status']} n={r['n_attempt']}")
# ② 6ok 超阈 + 7/8 fail → 扩展至 12 → 仍超 → unstable
walls = [100, 101, 102, 300, 301, 302]   # IQR 大
c = new_cell(); w = MockWorker([("ok",100),("ok",101),("ok",102),("ok",300),("ok",301),("ok",302)] + ["fail","fail"] + [("ok",400)]*4)
run(c, w, save_raw=lambda p: None)
r = c.finish()
check("A②", r["n_attempt"]==12 and r["status"]=="complete" and r["unstable"] is True,
      f"n={r['n_attempt']} {r['status']} un={r['unstable']}")
# ③ 5valid/3fail → 第8次停 → partial
c = new_cell(); w = MockWorker(["ok"]*5 + ["fail"]*3)
run(c, w, save_raw=lambda p: None)
r = c.finish()
check("A③", r["status"]=="partial" and r["n_attempt"]==8 and r["n_valid"]==5,
      f"{r['status']} n={r['n_attempt']} v={r['n_valid']}")
# ④ 0valid/8fail → failed, reps 恰 8 条
c = new_cell(); w = MockWorker(["fail"]*8)
run(c, w, save_raw=lambda p: None)
r = c.finish()
check("A④", r["status"]=="failed" and r["n_attempt"]==8 and len(r["reps"])==8,
      f"{r['status']} n={r['n_attempt']} reps={len(r['reps'])}")
# ⑤ 6valid/6fail 且 IQR 超 → expected=unstable（r4 冻结语义）
c = new_cell(); w = MockWorker([("ok",100),("ok",101),("ok",102),("ok",300),("ok",301),("ok",302)] + ["fail"]*6)
run(c, w, save_raw=lambda p: None)
r = c.finish()
check("A⑤", r["status"]=="complete" and r["unstable"] is True and r["n_attempt"]==12,
      f"{r['status']} un={r['unstable']} n={r['n_attempt']}")
# ⑥ CellFatal → failed 且落盘（save_raw 必被调）
c = new_cell(); w = MockWorker(["ok", CellFatal("boom")])
saved = []
run(c, w, save_raw=lambda p: saved.append(p))
r = c.finish()
check("A⑥", r["status"]=="failed" and r["err_kind"]=="cell_fatal" and len(saved)>=1,
      f"{r['status']} ek={r['err_kind']} saved={len(saved)}")
# ⑦ 超时 → TimeoutError → timeout rep 占 attempt（不 script消耗）
class TOWorker(MockWorker):
    def infer(self, timeout): raise TimeoutError()
c = new_cell(); w = TOWorker([])
saved = []
run(c, w, save_raw=lambda p: saved.append(p))
r = c.finish()
check("A⑦", r["n_attempt"]==8 and all(x["status"]=="timeout" for x in r["reps"]),
      f"n={r['n_attempt']} statuses={[x['status'] for x in r['reps']]}")
# ⑧ 12 全 ok 超阈 → unstable（walls 分裂大）
c = new_cell(); w = MockWorker(["ok"]*6 + ["fail"]*0 + ["ok"]*6)  # n=12 但第6后需超阈……用分段 walls
# 手工构造：直接 absorb 分裂 walls
c2 = new_cell()
for i in range(6): c2.absorb(Rep(n=i+1, attempt=i+1, status="ok", wall=100.0+i, cer=0.05))
for i in range(6): c2.absorb(Rep(n=7+i, attempt=7+i, status="ok", wall=500.0+i, cer=0.05))
c2.max_attempts = 12
r = c2.finish()
check("A⑧", r["n_attempt"]==12 and r["n_valid"]==12 and r["unstable"] is True and r["status"]=="complete",
      f"n={r['n_attempt']} v={r['n_valid']} un={r['unstable']}")
# ⑨ 4valid 且 median≤0 → 报错非 partial
c = new_cell()
for i in range(4): c.absorb(Rep(n=i+1, attempt=i+1, status="ok", wall=0.0, cer=0.05))
c.max_attempts = 4
r = c.finish()
check("A⑨", r["status"]=="failed" and r["err"]=="median_le_0",
      f"{r['status']} err={r['err']}")

# ---------------- B 组 schema 正反例 ----------------
try:
    import jsonschema
    SCHEMA = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "schema", "cell.schema.json"), encoding="utf-8"))
    def valid(payload):
        try:
            jsonschema.validate(payload, SCHEMA); return True, ""
        except jsonschema.ValidationError as e:
            return False, e.message[:80]
    def mkcell(status="complete", **over):
        c = new_cell()
        if status == "skipped":
            base = dict(c.base); base.update(c.mark_skipped("gt_unsigned"))
        else:
            for i in range(6 if status=="complete" else 4):
                c.absorb(Rep(n=i+1, attempt=i+1, status="ok", wall=100.0+i, cer=0.05))
            if status == "partial":
                for i in range(2): c.absorb(Rep(n=7+i, attempt=7+i, status="fail", err_kind="extract_fail"))
            if status == "failed":
                c.fatal = None
                c.n_valid = 2
            base = c.to_schema(c.base)
        base.update(over)
        return base
    # 正例四态
    for st in ("complete", "partial", "failed", "skipped"):
        ok, msg = valid(mkcell(st))
        check(f"B-正-{st}", ok, msg)
    # 负例
    negs = {}
    p = mkcell(); p["input"]["sha256"] = "deadbeef"; negs["page_sha型短hash"] = p  # pattern 拒
    p = mkcell(); del p["cer_median"]; negs["缺cer_median"] = p
    p = mkcell(); p["status"] = "done"; negs["status枚举越界"] = p
    p = mkcell(); del p["wall_iqr"]; negs["required缺失"] = p
    p = mkcell(); p["input"]["extra"] = 1; negs["嵌套多余键"] = p
    p = mkcell("failed"); p["wall_median"] = 0; negs["failed wall=0"] = p
    p = mkcell("skipped"); p["n_attempt"] = 1; negs["skipped带reps"] = p
    p = mkcell(); p["hacker"] = 1; negs["顶层多余键"] = p
    for name, payload in negs.items():
        ok, msg = valid(payload)
        check(f"B-负-{name}", (not ok), f"应拒未拒: {msg}")
except ImportError:
    for n in ("正-complete","正-partial","正-failed","正-skipped"): check("B-"+n, False, "jsonschema 未装")
    FAIL.append("B: jsonschema 库缺失")

# ---------------- 汇总 ----------------
print(f"A+B 组: PASS={PASS}  FAIL={len(FAIL)}")
for f in FAIL: print("  ✗", f)
sys.exit(1 if FAIL else 0)
