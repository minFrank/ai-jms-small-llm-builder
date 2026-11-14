"""ep13 runner —— 单进程主控（v4 §7：独占 task.json、spawn venv worker、格边界控制）
用法: python scripts/runner.py --engine paddleocr_vl --img <path> [--out <cells_dir>]
r4 盯点: timeout→kill+丢迟到 / respawn 预算 / 心跳分文件 / save_raw 先行
"""
from __future__ import annotations
import sys, os, json, time, subprocess, argparse, uuid, hashlib

# r15: GT 指纹真值（原写死 none-smoke 导致重跑格 G0 失败）
import json as _j0
_W0 = _j0.load(open(r"D:/models/models/ocr/ep13-docparse/WEIGHTS_SHA256.json", encoding="utf-8"))
_E0 = {"oxr": "OXR-1.0", "paddleocr_vl": "PaddleOCR-VL-1.6", "xiaomi_vl": "Xiaomi-OCR-0",
       "ovis_ocr2": "OvisOCR2", "monkey_rec": "MonkeyOCR-pro-1.2B", "surya_2_5": "surya-ocr-2.5"}
_WSHA = {}
for _e, _k in _E0.items():
    _d0 = _W0.get("engines", _W0)
    _ent = _d0.get(_k) or next((v for kk, v in _d0.items() if _k.split("-")[0] in kk and isinstance(v, dict)), None)
    if isinstance(_ent, dict) and _ent.get("sha256"):
        _WSHA[_e] = _ent["sha256"]
_GTM = json.load(open(os.path.join(BASE, "gt", "manifest.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(BASE, "gt", "manifest.json")) else {}
_S2GT = {}
_sm = os.path.join(BASE, "samples", "manifest.json")
if os.path.exists(_sm):
    _S2GT = {x["sha256"]: x.get("gt_sha256") for x in
             json.load(open(_sm, encoding="utf-8"))["samples"]}

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cell_runner import Cell, Rep, run as run_cell, CellFatal, WorkerFatal

VENV_PY = {   # 每引擎独立 venv（P0 实证 5.0/5.1/5.22 互不兼容）
    "paddleocr_vl": EP + "/venvs/paddle/Scripts/python.exe",
    "xiaomi_vl":    EP + "/venvs/ovis/Scripts/python.exe",
    "ovis_ocr2":    EP + "/venvs/ovis/Scripts/python.exe",
    "monkey_rec":   EP + "/venvs/dots/Scripts/python.exe",
    "surya_2_5":    EP + "/venvs/dots/Scripts/python.exe",
    "oxr":          EP + "/venvs/oxr/Scripts/python.exe",
}

class NdvWorker:
    """NDJSON 子进程封装（单飞、超时 kill、迟到丢弃）"""
    def __init__(self, engine: str):
        self.engine = engine
        py = VENV_PY[engine]
        if not os.path.exists(py):
            raise WorkerFatal(f"venv python 缺: {py}")
        self.proc = subprocess.Popen(
            [py, os.path.join(HERE, "worker.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            cwd=EP)
        self._id = 0
        # boot 事件
        print(f"[worker] spawn pid={self.proc.pid}，等 boot…")
        boot = self._read(timeout=30)
        print(f"[worker] boot: {boot}")

    def _read(self, timeout: float) -> dict:
        """轮询进程存活（Windows pipe 杀后不 EOF——join 会卡死，必须 poll 兜底）"""
        import threading, queue
        q = queue.Queue()
        def rd():
            try:
                line = self.proc.stdout.readline()
                q.put(json.loads(line) if line.strip() else {"ok": False, "err": "read:EOF"})
            except Exception as e:
                q.put({"ok": False, "err": f"read:{e}"})
        threading.Thread(target=rd, daemon=True).start()
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:          # ★ 进程已死 → 立即 WorkerFatal
                raise WorkerFatal(f"worker exited code={self.proc.returncode}")
            try:
                return q.get(timeout=1.0)
            except queue.Empty:
                continue
        self.kill()                                   # 超时 kill（r4 盯点2）
        raise TimeoutError("worker read timeout")

    def call(self, cmd: str, timeout: float, **kw) -> dict:
        self._id += 1
        msg = dict(cmd=cmd, id=self._id, **kw)
        try:
            self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except Exception:
            raise WorkerFatal("stdin 写失败（worker 已死）")
        resp = self._read(timeout)
        if resp.get("id") not in (None, self._id):
            raise WorkerFatal(f"迟到响应丢弃 id={resp.get('id')}")   # r4 盯点2
        return resp

    def respawn(self) -> None:
        """r4 盯点1: runner 侧 respawn（预算由 cell_runner 计）"""
        self.kill()
        py = VENV_PY[self.engine]
        self.proc = subprocess.Popen(
            [py, os.path.join(HERE, "worker.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1, cwd=EP)
        self._read(timeout=30)
        self.call("load", timeout=600, engine=self.engine)

    def kill(self) -> None:
        try:
            self.proc.kill(); self.proc.wait(timeout=5)
        except Exception: pass

    def alive(self) -> bool:
        return self.proc.poll() is None


class CellAdapter:
    """cell_runner.run() 需要的 worker 接口"""
    def __init__(self, ndv: NdvWorker):
        self.ndv = ndv
    def infer(self, timeout: float) -> dict:
        r = self.ndv.call("infer", timeout=timeout, path=self.path,
                          max_new=2048)
        if not r.get("ok"):
            err = str(r.get("err", ""))
            # WorkerFatal（触发 respawn 预算）：进程死/读失败/not_loaded/协议错
            if ("not_loaded" in err or "read:" in err or "stdin" in err
                    or not self.ndv.alive()):
                raise WorkerFatal(err or "worker died")
            # infer 内部错误 → fail rep（占 attempt，不重生）
            return dict(status="fail", wall=None, wall_self=None, cer=None,
                        truncated=None, err_kind="extract_fail", ts=None)
        # EXTRACTION_CONTRACT v1：strip 后逐字符 CER（GT 与 img 同名同目录）
        c = None
        gt_path = self.gt_path
        if gt_path and os.path.exists(gt_path):
            from cer import cer as _cer
            from extract_text import extract as _ex
            ref = open(gt_path, encoding="utf-8").read()
            c = round(_cer(ref, _ex(r.get("text") or "")), 6)   # v2: 先格式解析
        return dict(status="ok", wall=r["wall"], wall_self=r["wall_self"],
                    cer=c,
                    truncated=r.get("truncated"), err_kind=None, ts=r["ts"])
    def respawn(self):
        self.ndv.respawn()
    path = ""
    gt_path = None


def heartbeat_loop(stop_flag, run_id, path):
    """独立 5s 心跳（r4: 与 task 分文件——runner 不碰 heartbeat.json 由本线程独占）"""
    while not stop_flag[0]:
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(hb_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                               owner_pid=os.getpid(), run_id=run_id), f)
            os.replace(tmp, path)
        except Exception: pass
        time.sleep(5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--img", required=True)
    ap.add_argument("--run-id", default="ep13-smoke-" + time.strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--out", default=os.path.join(EP, "cells"))
    ap.add_argument("--max-attempts", type=int, default=8, help="冒烟用 1（不入分母）")
    args = ap.parse_args()

    run_id = args.run_id
    os.makedirs(os.path.join(args.out, run_id), exist_ok=True)
    # 心跳（分文件）
    stop = [False]
    import threading
    hb_path = os.path.join(EP, "control", "heartbeat.json")
    threading.Thread(target=heartbeat_loop, args=(stop, run_id, hb_path), daemon=True).start()
    # task.json（runner 独占）
    task_path = os.path.join(EP, "control", "task.json")
    def write_task(state, seq):
        tmp = task_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dict(run_id=run_id, state=state, state_seq=seq, owner_pid=os.getpid(),
                           updated_by="runner", last_progress=time.strftime("%Y-%m-%dT%H:%M:%S"),
                           finished_at=None if state == "running" else time.strftime("%Y-%m-%dT%H:%M:%S")), f)
        os.replace(tmp, task_path)
    write_task("running", 1)

    ndv = None; cell_payload = None; exit_code = 0
    try:
        ndv = NdvWorker(args.engine)
        hello = ndv.call("hello", timeout=90, engine=args.engine)
        print(f"[runner] hello: {hello}")
        load = ndv.call("load", timeout=600, engine=args.engine)
        print(f"[runner] load: {load}")
        if not load.get("ok"):
            raise WorkerFatal(load.get("err", "load 失败"))

        sha = hashlib.sha256(open(args.img, "rb").read()).hexdigest()
        # ★ sample_uuid 取自 manifest（G0 FK / 断点关联——禁随机 uuid）
        _man = json.load(open(os.path.join(EP, "samples", "manifest.json"), encoding="utf-8"))
        _img_name = os.path.basename(args.img)
        _entry = next((s for s in _man["samples"] if s["img"] == _img_name), None)
        if _entry is None:
            raise WorkerFatal(f"样本不在 manifest: {_img_name}")
        sample_uuid = _entry["sample_uuid"]
        cell = Cell()
        cell.base = dict(schema=6, run_id=run_id,
                         cell_key=f"{sample_uuid}__{args.engine}__p1",
                         engine=args.engine, layer="A", sample_id=sample_uuid,
                         set="S26", input=dict(kind="image", sha256=sha, page_no=1, dpi=300),
                         fingerprint=dict(git="ep13", weights_sha=_WSHA.get(args.engine, "see-MANIFEST"), deps="see-venv",
                                          config_hash="engines-ep13-v1", extract_v="contract-v1",
                                          gt_v=_GTM.get("gt_v", "unsigned"), gt_hash=_S2GT.get(sha, _GTM.get("content_hash", "")), sample_sha=sha,
                                          engine_version="p0-validated", host_manifest_id="host-1",
                                          seed=0, order=0))
        adapter = CellAdapter(ndv); adapter.path = args.img
        sample = os.path.splitext(os.path.basename(args.img))[0]
        adapter.gt_path = os.path.join(EP, "gt", sample + ".txt")

        def save_raw(payload):
            p = os.path.join(args.out, run_id, payload["cell_key"] + ".json")
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            os.replace(tmp, p)
            print(f"[runner] save_raw → {p}")

        def validate_soft(payload):
            try:
                import jsonschema
                schema = json.load(open(os.path.join(EP, "schema", "cell.schema.json"),
                                        encoding="utf-8"))
                jsonschema.validate(payload, schema)
                print("[runner] validate: OK")
            except ImportError:
                print("[runner] validate: jsonschema 未装，跳过（冒烟）")
            except Exception as e:
                # r4 盯点3: 校验失败仍已 save_raw，重存 schema_err
                payload["err"] = f"schema_err:{e}"[:200]
                save_raw(payload)

        cell = run_cell(cell, adapter, save_raw=save_raw, validate_soft=validate_soft,
                        hard_cap=(args.max_attempts if args.max_attempts != 8 else None))
        payload = cell.to_schema(cell.base)
        cell_payload = payload
        print(f"[runner] DONE status={payload['status']} n_attempt={payload['n_attempt']} "
              f"wall_median={payload['wall_median']}")
        if payload["status"] not in ("complete", "partial"):
            exit_code = 2
    except (CellFatal, WorkerFatal, TimeoutError) as e:
        print(f"[runner] FATAL: {type(e).__name__}: {e}")
        exit_code = 3
    finally:
        stop[0] = True
        if ndv:
            try: ndv.call("teardown", timeout=60)
            except Exception: pass
            ndv.kill()
        write_task("done" if exit_code == 0 else "failed", 2)
        print(f"[runner] exit={exit_code} heartbeat→stale(停止)")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
