"""ep13 CellRunner —— 协议 A 状态机（v4 §2 · r4 终验通过的实现契约）
设计权威源: docs/reviews/2026-11-04-...-v4.html §2/§3 + 规格 V6d-errata
r4 盯点落实: ①WorkerFatal 超预算置 fatal ②timeout kill+丢迟到 ③validate 失败重存
            ④A⑤/A⑥ 夹具语义 ⑤schema if/then ⑥failed 全 null 口径 ⑦FK 校验
"""
from __future__ import annotations
import time, statistics, json, os
from dataclasses import dataclass, field
from typing import Optional

TARGET_VALID = 6
INITIAL_MAX = 8
EXTENSION_MAX = 12
IQR_LIMIT = 0.10          # IQR/median > 10% 超阈
RESPAWN_BUDGET = 1        # 次/引擎/小时（r4 盯点1 关联）


class CellFatal(Exception):
    """不可恢复的格级错误（r4: err_kind=cell_fatal）"""


class WorkerFatal(Exception):
    """worker 进程级错误（可 respawn 一次/小时预算）"""


@dataclass
class Rep:
    n: int
    attempt: int
    status: str                 # ok|fail|timeout|skipped
    wall: Optional[float] = None
    wall_self: Optional[float] = None
    cer: Optional[float] = None
    truncated: Optional[bool] = None
    err_kind: Optional[str] = None
    ts: Optional[str] = None

    def to_dict(self):
        return dict(n=self.n, attempt=self.attempt, status=self.status,
                    wall=self.wall, wall_self=self.wall_self, cer=self.cer,
                    truncated=self.truncated, err_kind=self.err_kind, ts=self.ts)


class Cell:
    """schema 生产者（r4 阻断2：实例化、单点计数）"""
    def __init__(self, **kw):
        self.reps: list[Rep] = []
        self.walls: list[float] = []
        self.cers: list[float] = []
        self.n_attempt = 0            # ★ 只在 absorb +1（单点计数）
        self.n_valid = 0
        self.fatal: Optional[str] = None
        self.max_attempts = INITIAL_MAX
        self.unstable = False
        self.status = None
        for k, v in kw.items():
            setattr(self, k, v)

    # ---------- 单点计数 ----------
    def absorb(self, rep: Rep) -> None:
        self.reps.append(rep)
        self.n_attempt += 1
        if rep.status == "ok" and rep.wall is not None:
            self.n_valid += 1
            self.walls.append(rep.wall)
            if rep.cer is not None:
                self.cers.append(rep.cer)

    # ---------- 扩展门（r4 A②）----------
    def extension_gate(self) -> bool:
        if self.n_attempt >= INITIAL_MAX and self.max_attempts == INITIAL_MAX \
           and self.n_valid >= TARGET_VALID and self._iqr_over():
            self.max_attempts = EXTENSION_MAX
            return True
        return False

    def done_ok(self) -> bool:
        return self.n_valid >= TARGET_VALID and not self._iqr_over()

    def _iqr_over(self) -> bool:
        if len(self.walls) < 4:
            return False
        med = statistics.median(self.walls)
        if med <= 0:
            return False
        q1, q3 = statistics.quantiles(self.walls, n=4)[0], statistics.quantiles(self.walls, n=4)[2]
        return (q3 - q1) / med > IQR_LIMIT

    # ---------- 四收尾（r4 阻断3 冻结顺序：median≤0 最先）----------
    def finish(self) -> dict:
        # ① median≤0 → 报错留痕（在分级之前）
        if self.walls and statistics.median(self.walls) <= 0:
            status, err, err_kind = "failed", "median_le_0", "median_le_0"
        elif self.fatal:
            status, err, err_kind = "failed", self.fatal, (self.fatal if self.fatal in
                ("cell_fatal", "worker_fatal", "gt_unsigned", "gt_mismatch") else "cell_fatal")
        elif self.n_valid < 4:
            status, err, err_kind = "failed", f"n_valid={self.n_valid}<4", None
        elif self.n_valid < TARGET_VALID:
            status, err, err_kind = "partial", None, None
        else:
            # n_valid >= 6
            if self.n_attempt >= EXTENSION_MAX and self._iqr_over():
                status, err, err_kind = "complete", None, None
                self.unstable = True          # r4 冻结口径：attempt=12 且仍超阈
            else:
                status, err, err_kind = "complete", None, None
        # 聚合（failed 全 null 口径 r4⑥）
        ok = status in ("complete", "partial")
        wall_median = statistics.median(self.walls) if (ok and self.walls) else None
        wall_iqr = None
        if ok and len(self.walls) >= 4:
            q1, q3 = statistics.quantiles(self.walls, n=4)[0], statistics.quantiles(self.walls, n=4)[2]
            wall_iqr = q3 - q1
        cer_median = statistics.median(self.cers) if (ok and self.cers) else None
        csr = (self.n_valid / self.n_attempt) if (ok and self.n_attempt) else None
        truncs = [r.truncated for r in self.reps if r.status == "ok" and r.truncated is not None]
        trunc_rate = (sum(1 for t in truncs if t) / len(truncs)) if (ok and truncs) else None
        self.status = status
        return dict(status=status, err=err, err_kind=err_kind,
                    n_attempt=self.n_attempt, n_valid=self.n_valid,
                    n_fail=self.n_attempt - self.n_valid,
                    wall_median=wall_median, wall_iqr=wall_iqr,
                    cer_median=cer_median, cell_success_rate=csr,
                    trunc_rate=trunc_rate, unstable=self.unstable,
                    reps=[r.to_dict() for r in self.reps])

    def to_schema(self, base: dict) -> dict:
        """base: run_id/cell_key/engine/layer/sample_id/set/input/fingerprint/... 静态字段"""
        out = dict(base)
        out.update(schema=6, target_valid=TARGET_VALID,
                   max_attempts=self.max_attempts)
        out.update(self.finish())
        # skipped 语义（外部调用方用 mark_skipped）
        return out

    def mark_skipped(self, err_kind: str) -> dict:
        """GT 未签/revoke → skipped cell（r4 C 组：仅允许 gt_unsigned/gt_mismatch）"""
        assert err_kind in ("gt_unsigned", "gt_mismatch"), "非法 skip err_kind"
        self.status = "skipped"
        return dict(schema=6, status="skipped", target_valid=TARGET_VALID,
                    max_attempts=INITIAL_MAX, err=err_kind, err_kind=err_kind,
                    n_attempt=0, n_valid=0, n_fail=0, reps=[],
                    wall_median=None, wall_iqr=None, cer_median=None,
                    cell_success_rate=None, trunc_rate=None, unstable=False)


def run(cell: Cell, worker, save_raw, validate_soft=None, now=time.time, hard_cap=None) -> Cell:
    """主循环（v4 §2.1：timeout rep / WorkerFatal respawn / return cell）
    worker.infer(timeout) -> Rep-dict | raise TimeoutError | CellFatal | WorkerFatal
    """
    respawn_budget = RESPAWN_BUDGET
    try:
        while True:
            if cell.fatal:
                break                                  # fatal 置位也走 finally
            cap = min(cell.max_attempts, hard_cap) if hard_cap else cell.max_attempts
            if cell.n_attempt >= cap:
                break
            try:
                rep_d = worker.infer(timeout=1800)     # D2=30min（父进程 kill 在 worker 内）
            except TimeoutError:
                rep_d = dict(status="timeout", wall=None, wall_self=None, cer=None,
                             truncated=None, err_kind="timeout", ts=None)
            except CellFatal as e:
                cell.fatal = "cell_fatal"              # 不 absorb，走 finally
                break
            except WorkerFatal:
                # r4 盯点1: 超预算必须置 fatal（防死循环）
                if respawn_budget <= 0:
                    cell.fatal = "worker_fatal"
                    break
                respawn_budget -= 1
                if hasattr(worker, "respawn"):
                    worker.respawn()                   # r4 盯点2: kill+新进程（迟到响应丢弃）
                continue                               # 不 absorb，重试
            rep = Rep(n=cell.n_attempt + 1, attempt=cell.n_attempt + 1, **rep_d)
            cell.absorb(rep)
            cell.extension_gate()
            if cell.done_ok():
                break
    finally:
        cell.finish()                       # 幂等：设置 cell.status（可重复调）
        payload = cell.to_schema(cell.base) if hasattr(cell, "base") else None
        if payload is not None:
            save_raw(payload)                          # F-05 先行
            if validate_soft:
                validate_soft(payload)                 # 失败重存 schema_err（r4 盯点3）
    return cell
