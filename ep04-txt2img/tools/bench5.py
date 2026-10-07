#!/usr/bin/env python
"""ep04 扩测阶段1:ComfyUI 冷启动基准 v2(修 REVIEW-bench5.md 的 B01-B13)。

判据来源: EXPAND-DESIGN.md + REVIEW-dsh.md(设计)+ REVIEW-bench5.md(代码)

阶段显式(B07): --only cold|warm|anchor|cold,warm|anchor,cold
  cold    冷启动主测:每轮重启 server,计时起点在 Popen 之前(含 import+加载)
  warm    暖态列(单列,不进头条):服务常驻,只提交
  anchor  锚点复测(DP-19):重跑 sd.cpp 纯 CPU 基准行,写独立 scheme

用法:
  python bench5.py --only cold --n 3
  python bench5.py --only warm
  python bench5.py --only anchor
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------- 禁联网 guard(B11: 记录,不抹掉) ----------
_orig = socket.socket.connect
_BLOCKED = []
_PROXY = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888}


def _g(self, address, *a, **k):
    host = str(address[0]) if isinstance(address, tuple) and address else str(address)
    port = int(address[1]) if isinstance(address, tuple) and len(address) > 1 else 0
    if host not in ("127.0.0.1", "::1", "localhost"):
        _BLOCKED.append(f"{host}:{port} non-loopback")
        raise OSError(f"[offline-guard] blocked {host}:{port}")
    if port in _PROXY:
        _BLOCKED.append(f"{host}:{port} proxy")
        raise OSError(f"[offline-guard] blocked proxy {port}")
    return _orig(self, address, *a, **k)


socket.socket.connect = _g

import psutil  # noqa: E402

MODELS = r"D:/models/txt2img"
E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
COMFY = r"D:/ep04/comfy/ComfyUI-src"
COMFY_PY = r"D:/ep04/comfy/venv/Scripts/python.exe"
BENCH4 = os.path.join(E04, "tools", "bench4.py")
LOG = os.path.join(E04, "logs", "bench5-progress.json")
OUTDIR = os.path.join(MODELS, "out5")
REPRO = os.path.join(E04, "replicate")
TODAY = datetime.now().strftime("%Y%m%d")
SCHEMA_VERSION = 2
PORT = 8199

# 与 bench4 完全一致的口径
PROMPTS = [
    "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
]
NEG = ""
SEEDS = [42, 43, 44]
SIZE, STEPS, CFG = (512, 512), 20, 7.0
SAMPLER, SCHEDULER = "euler", "normal"
PRECISION, CLIP_SKIP = "fp32", 1
CKPT = "v1-5-pruned-emaonly.safetensors"
MODEL = os.path.join(MODELS, CKPT)

for d in (OUTDIR, REPRO, os.path.join(E04, "logs")):
    os.makedirs(d, exist_ok=True)

WARM_KILL_FAIL = None
OUT = {
    "schema_version": SCHEMA_VERSION,
    "ts_start": time.strftime("%Y-%m-%d %H:%M:%S"),
    "stages": [],
    "requested_n": None,
    "frozen_src_sha256": None,
    "offline_window": {"start": None, "end": None, "blocked_attempts": []},
    "rows": [],
}


def sha256_file(p):
    if not p or not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- B06: 冻结旧数据(带日期 + linkage) ----------
def freeze_old():
    src = os.path.join(E04, "logs", "bench4-progress.json")
    if not os.path.exists(src):
        raise SystemExit("FATAL(C1): 找不到 bench4-progress.json")
    dated = os.path.join(E04, "logs", f"bench4-progress.frozen.{TODAY}.json")
    if not os.path.exists(dated):
        shutil.copy2(src, dated)
    h_src = sha256_file(src)
    h_frozen = sha256_file(dated)
    if h_src != h_frozen:
        raise SystemExit(f"FATAL(C1): 源与冻结副本不一致 {h_src[:16]} vs {h_frozen[:16]}")
    # 覆盖 bench4.py 自身(C11: 旧语义不得被改)
    h_script = sha256_file(BENCH4)
    if not h_script:
        raise SystemExit("FATAL(C11): bench4.py 缺失")
    return h_src, h_script


def assert_frozen(h_src, h_script, where):
    if sha256_file(os.path.join(E04, "logs", "bench4-progress.json")) != h_src:
        raise SystemExit(f"FATAL(C1)@{where}: 旧 progress 被改动")
    if sha256_file(BENCH4) != h_script:
        raise SystemExit(f"FATAL(C11)@{where}: bench4.py 被改动")


# ---------- B06: 落盘 append-only(保留失败行, attempt 序号) ----------
def load_state():
    if not os.path.exists(LOG):
        return
    try:
        with open(LOG, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        raise SystemExit(f"FATAL(B06): {LOG} 解析失败(拒绝用空历史覆盖): {e}")
    # R05: schema 与类型校验
    if d.get("schema_version") not in (None, SCHEMA_VERSION):
        raise SystemExit(f"FATAL(R05): schema_version={d.get('schema_version')} "
                         f"不兼容本脚本({SCHEMA_VERSION})")
    if not isinstance(d.get("rows", []), list):
        raise SystemExit("FATAL(R05): rows 不是 list,历史文件类型损坏")
    # R04: 顶层键从盘上恢复(保留旧段 ts_start/stages)
    for k in ("ts_start", "stages", "requested_n", "frozen_src_sha256",
              "offline_window", "verdict"):
        if k in d:
            OUT[k] = d[k]
    OUT["rows"] = d.get("rows", [])


def save():
    disk = {}
    if os.path.exists(LOG):
        try:
            with open(LOG, encoding="utf-8") as f:
                disk = json.load(f)
        except Exception as e:
            raise SystemExit(f"FATAL(B06): 盘上 JSON 已损坏,停止写入: {e}")
    # append-only: 内存行已含 load_state 灌入的全部历史,盘上独有行保留,重复 (cell,attempt) 以内存为准
    old = disk.get("rows", [])
    seen = {(r.get("cell"), r.get("attempt")) for r in OUT.get("rows", [])}
    merged = [r for r in old if (r.get("cell"), r.get("attempt")) not in seen]
    merged += OUT.get("rows", [])
    out = dict(disk)
    out.update({k: v for k, v in OUT.items() if k != "rows"})
    out["rows"] = merged
    with open(LOG + ".tmp", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(LOG + ".tmp", LOG)


def cell_key(mode, p, seed, run):
    return f"{mode}_p{p}_s{seed}_r{run}"


def attempt_of(cell):
    """该 cell 已有尝试次数(含失败)。"""
    return sum(1 for r in OUT["rows"] if r.get("cell") == cell)


def done_ok(cell, fingerprint):
    """B08: 该 cell 已有成功行且指纹一致才跳过;指纹变即要求人工确认。"""
    for r in OUT["rows"]:
        if r.get("cell") == cell and r.get("ok"):
            if r.get("fingerprint") != fingerprint:
                raise SystemExit(
                    f"FATAL(B08): {cell} 已存在但指纹不一致(输入/引擎已变),"
                    f"旧行={r.get('fingerprint')} 本轮={fingerprint} — 需人工确认")
            return True
    return False


# ---------- B01/B02/B10: 进程与端口 ----------
def port_busy():
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect(("127.0.0.1", PORT))
        return True
    except OSError:
        return False
    finally:
        s.close()


def kill_tree(pid):
    """B02: 递归终止整棵树,按 PID 复查全灭 + 端口释放。返回 (ok, msg)。"""
    try:
        root = psutil.Process(pid)
        procs = root.children(recursive=True) + [root]
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        gone, alive = psutil.wait_procs(procs, timeout=20)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
        gone2, alive2 = psutil.wait_procs(alive, timeout=10)
        if alive2:
            names = ",".join(str(getattr(p, "pid", "?")) for p in alive2[:5])
            return False, f"进程树残留 pid={names}"
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        return False, f"kill_tree: {e}"
    for _ in range(20):
        if not port_busy():
            return True, ""
        time.sleep(1)
    return False, f"port {PORT} 仍在监听"


# ---------- 进程树 RSS(C10: 0.5s,递归) ----------
class TreePeak:
    def __init__(self):
        self.peak, self._stop = 0, threading.Event()

    def sample(self, pid):
        tot = 0
        try:
            root = psutil.Process(pid)
            for p in [root] + root.children(recursive=True):
                try:
                    tot += p.memory_info().rss
                except Exception:
                    pass
        except Exception:
            pass
        self.peak = max(self.peak, tot)

    def run(self, pid):
        while not self._stop.is_set():
            self.sample(pid)
            time.sleep(0.5)

    def start(self, pid):
        self.pid = pid
        self.sample(pid)  # N07: Popen 后立即采一次
        threading.Thread(target=self.run, args=(pid,), daemon=True).start()
        return self

    def stop(self):
        self._stop.set()
        try:
            self.sample(self.pid)
        except Exception:
            pass
        return self.peak


# ---------- ComfyUI 服务 ----------
def ensure_ckpt():
    ck = os.path.join(COMFY, "models", "checkpoints")
    os.makedirs(ck, exist_ok=True)
    dst = os.path.join(ck, CKPT)
    want = sha256_file(MODEL)
    if not os.path.exists(dst):
        try:
            os.symlink(MODEL, dst)
        except OSError:
            shutil.copyfile(MODEL, dst)
    got = sha256_file(dst)
    if got != want:
        raise SystemExit(f"FATAL(N04): checkpoint 校验失败 {dst} {got} != {want}")
    return want


def start_server(logf, rundir, pk=None):
    """B01: 先断言端口空闲,Popen 后校验新进程存活。
    R12: pk 给定时在 Popen 后立刻开采样(覆盖解释器/torch import 期峰值)。"""
    if port_busy():
        raise SystemExit(f"FATAL(B01): 端口 {PORT} 已被占用(上轮残留),拒绝开跑")
    env = dict(os.environ)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    cmd = [COMFY_PY, os.path.join(COMFY, "main.py"), "--cpu",
           "--port", str(PORT), "--disable-auto-launch",
           "--output-directory", rundir,
           "--verbose", "DEBUG"]
    p = subprocess.Popen(cmd, cwd=COMFY, stdout=logf, stderr=subprocess.STDOUT, env=env)
    if pk is not None:
        pk.start(p.pid)          # R12: Popen 之后立刻起采样
    import urllib.request
    for _ in range(120):
        if p.poll() is not None:
            raise RuntimeError(f"server exited rc={p.returncode} (log={logf.name})")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/system_stats", timeout=2).read()
            return p, cmd
        except Exception:
            time.sleep(2)
    raise TimeoutError("ComfyUI 240s 未就绪")


def submit(base, prompt_text, rundir, seed, timeout=1200):
    """返回 (gen秒, 图路径, err)。B03: 只认 history 返回的 filename,按 mtime 断言本轮。"""
    import urllib.request
    wf = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": STEPS, "cfg": CFG, "sampler_name": SAMPLER,
            "scheduler": SCHEDULER, "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": SIZE[0], "height": SIZE[1], "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "b5", "images": ["9", 0]}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    }
    wpath = os.path.join(rundir, "workflow.json")
    with open(wpath, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=1)
    req = urllib.request.Request(base + "/prompt",
                                 data=json.dumps({"prompt": wf}).encode(),
                                 headers={"Content-Type": "application/json"})
    pid = json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]
    t0 = time.time()
    while True:
        h = json.loads(urllib.request.urlopen(base + f"/history/{pid}", timeout=10).read())
        if pid in h:
            item = h[pid]
            st = item.get("status", {})
            # B10: 必须明确成功
            if st.get("status_str") != "success":
                return None, None, "status=" + str(st.get("status_str")) + " " + json.dumps(st)[:300]
            gen_s = time.time() - t0
            for node in item.get("outputs", {}).values():
                for im in node.get("images", []):
                    src = os.path.join(rundir, im.get("subfolder", ""), im["filename"])
                    if not os.path.exists(src):
                        return None, None, f"history 图不存在: {src}"
                    # B03: 必须是本轮提交之后生成
                    if os.path.getmtime(src) < t0 - 1:
                        return None, None, f"B03: 图早于本轮提交 {src}"
                    return gen_s, src, ""
            return None, None, "history 无 images"
        if time.time() - t0 > timeout:
            return None, None, f"history timeout {timeout}s"
        time.sleep(2)


def device_evidence(logf):
    """DP-05/DP-07: 实测落点。B05: 每轮独立日志 + 断言命中 device 行。"""
    ev = {"log": logf, "device_lines": [], "hit": False}
    try:
        with open(logf, encoding="utf-8", errors="replace") as f:
            for line in f:
                l = line.strip()
                if any(k in l for k in ("Device:", "device:", "Using device",
                                        "pytorch version", "Device: cpu")):
                    ev["device_lines"].append(l[:200])
                    ev["hit"] = True
    except Exception as e:
        ev["err"] = str(e)
    return ev


def base_row(mode, p, seed, fingerprint):
    return {
        "cell": None, "scheme": "comfyui", "mode": mode,
        "prompt_idx": p, "prompt_text": PROMPTS[p],
        "prompt_sha256": sha256_text(PROMPTS[p]),
        "negative_prompt": NEG, "seed": seed,
        "steps": STEPS, "size": "512x512", "cfg": CFG,
        "sampler": SAMPLER, "scheduler": SCHEDULER,
        "precision": PRECISION, "clip_skip": CLIP_SKIP,
        "runtime_version": f"comfyui-0.38.0/torch-{torch_version()}",
        "ckpt_sha256": CKPT_SHA,
        "fingerprint": fingerprint,
        "requested_n": OUT.get("requested_n"),
        "attempt": 0, "ts": now_ts(),
        "timing_scope": None, "seconds_total": None, "seconds_gen": None,
        "mem_peak_bytes": None, "mem_peak_mb": None,
        "shared_mem_included": False,   # CPU 路线无显存分配(DP-10)
        "server_pid": None, "server_log": None,
        "device_hit": None, "cmdline": None,
        "sha256": None, "ok": False, "err": "",
    }


def torch_version():
    try:
        import torch
        return torch.__version__
    except Exception:
        return "unknown"


CKPT_SHA = None


def emit(row, h_src, h_script):
    row["attempt"] = attempt_of(row["cell"]) + 1
    OUT["rows"].append(row)
    save()
    assert_frozen(h_src, h_script, row["cell"])


# ---------- cold ----------
def run_cold(n, h_src, h_script, fingerprint):
    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            for run in range(n):
                cell = cell_key("cold", p, seed, run)
                if done_ok(cell, fingerprint):
                    print(f"  {cell:<30} skip", flush=True)
                    continue
                rundir = os.path.join(OUTDIR, cell)
                if os.path.isdir(rundir):
                    shutil.rmtree(rundir, ignore_errors=True)  # B03: 清残留
                os.makedirs(rundir, exist_ok=True)
                row = base_row("cold", p, seed, fingerprint)
                row.update({"cell": cell, "timing_scope": "cold_total_incl_load"})
                logf_path = os.path.join(E04, "logs", f"comfy5_{cell}.log")
                srv = None
                pk = None
                t_start = time.time()
                with open(logf_path, "w") as logf:
                    try:
                        pk = TreePeak()
                        srv, cmd = start_server(logf, rundir, pk)
                        row["server_pid"] = srv.pid
                        row["cmdline"] = " ".join(cmd)
                        row["server_log"] = logf_path
                        gen_s, src, err = submit(f"http://127.0.0.1:{PORT}",
                                                 PROMPTS[p], rundir, seed)
                        if src:
                            dst = os.path.join(OUTDIR, cell + ".png")
                            shutil.copyfile(src, dst)
                            row["sha256"] = sha256_file(dst)
                            row["ok"] = bool(row["sha256"]) and os.path.getsize(dst) > 1000
                        row["err"] = err
                        row["seconds_gen"] = round(gen_s, 2) if gen_s else None
                        row["seconds_total"] = round(time.time() - t_start, 2)
                    except SystemExit:
                        raise
                    except Exception as e:
                        row["err"] = str(e)[-1200:]
                    finally:
                        if row.get("seconds_total") is None:
                            row["seconds_total"] = round(time.time() - t_start, 2)
                        if pk:
                            pb = pk.stop()
                            row["mem_peak_bytes"] = pb or None
                            row["mem_peak_mb"] = round(pb / 1048576, 1) if pb else None
                        if srv:
                            ok_kill, msg = kill_tree(srv.pid)
                            if not ok_kill:
                                row["err"] = (row["err"] + " | " + msg).strip(" |")
                                row["ok"] = False
                                print(f"  !! B02 回收失败: {msg}", flush=True)
                row.setdefault("seconds_total",
                               round(time.time() - t_start, 2))
                ev = device_evidence(logf_path)
                row["device_hit"] = ev["hit"]
                row["device_lines"] = ev["device_lines"][:4]
                if row["ok"] and not ev["hit"]:
                    row["ok"] = False
                    row["err"] = (row["err"] + " | B05: 未命中 device 行").strip(" |")
                emit(row, h_src, h_script)
                print(f"  {cell:<30} total={row['seconds_total']:6.1f}s "
                      f"gen={row['seconds_gen'] or 0:6.1f}s "
                      f"peak={row['mem_peak_mb'] or 0:6.1f}MB "
                      f"{'OK' if row['ok'] else 'FAIL:' + str(row['err'])[:70]}",
                      flush=True)


# ---------- warm ----------
def run_warm(h_src, h_script, fingerprint):
    global WARM_KILL_FAIL
    rundir = os.path.join(OUTDIR, "warm_session")
    if os.path.isdir(rundir):
        shutil.rmtree(rundir, ignore_errors=True)
    os.makedirs(rundir, exist_ok=True)
    logf_path = os.path.join(E04, "logs", "comfy5_warm.log")
    srv = None
    with open(logf_path, "w") as logf:
        try:
            srv, cmd = start_server(logf, rundir)
        except Exception as e:
            print(f"  !! warm 启动失败: {e}", flush=True)
            if srv:
                kill_tree(srv.pid)
            return
        try:
            for p in range(len(PROMPTS)):
                for seed in SEEDS:
                    cell = cell_key("warm", p, seed, 0)
                    if done_ok(cell, fingerprint):
                        continue
                    row = base_row("warm", p, seed, fingerprint)
                    row.update({"cell": cell,
                                "timing_scope": "warm_gen_only",
                                "server_pid": srv.pid,
                                "server_log": logf_path,
                                "cmdline": " ".join(cmd)})
                    try:
                        gen_s, src, err = submit(f"http://127.0.0.1:{PORT}",
                                                 PROMPTS[p], rundir, seed)
                        if src:
                            dst = os.path.join(OUTDIR, cell + ".png")
                            shutil.copyfile(src, dst)
                            row["sha256"] = sha256_file(dst)
                            row["ok"] = bool(row["sha256"])
                        row["err"] = err
                        row["seconds_gen"] = round(gen_s, 2) if gen_s else None
                    except SystemExit:
                        raise
                    except Exception as e:
                        row["err"] = str(e)[-1200:]
                    ev = device_evidence(logf_path)
                    row["device_hit"] = ev["hit"]
                    row["device_lines"] = ev["device_lines"][:4]
                    emit(row, h_src, h_script)
                    print(f"  {cell:<30} gen={row['seconds_gen'] or 0:6.1f}s "
                          f"{'OK' if row['ok'] else 'FAIL'}", flush=True)
        finally:
            if srv:
                ok_kill, msg = kill_tree(srv.pid)
                if not ok_kill:
                    WARM_KILL_FAIL = msg
                    print(f"  !! B02 warm 回收失败(计入退出码): {msg}", flush=True)
            logf.close()


# ---------- anchor (DP-19) ----------
def run_anchor(h_src, h_script, fingerprint):
    exe = os.path.join(MODELS, "cpu", "sd-cli.exe")
    if not os.path.exists(exe):
        raise SystemExit(f"FATAL(B09): {exe} 缺失")
    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            cell = cell_key("anchor", p, seed, 0)
            if done_ok(cell, fingerprint):
                continue
            out = os.path.join(OUTDIR, cell + ".png")
            if os.path.exists(out):
                os.remove(out)
            cmd = [exe, "-m", MODEL, "--prompt", PROMPTS[p],
                   "-W", str(SIZE[0]), "-H", str(SIZE[1]),
                   "--steps", str(STEPS), "-s", str(seed), "-o", out]
            row = base_row("anchor", p, seed, fingerprint)
            row.update({"cell": cell, "scheme": "anchor-sdcpp-cpu",
                        "timing_scope": "cold_total_incl_load",
                        "cmdline": " ".join(cmd)})
            pk = None
            t0 = time.time()
            try:
                pr = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True,
                                      encoding="utf-8", errors="replace")
                pk = TreePeak().start(pr.pid)
                try:
                    so, se = pr.communicate(timeout=1800)
                except subprocess.TimeoutExpired:
                    kill_tree(pr.pid)
                    raise TimeoutError("anchor 1800s 时间盒到点(C9)")
                row["seconds_total"] = round(time.time() - t0, 2)
                row["seconds_gen"] = row["seconds_total"]
                row["sha256"] = sha256_file(out)
                row["ok"] = bool(row["sha256"]) and os.path.getsize(out) > 1000
                row["err"] = "" if row["ok"] else (se or so or "")[-800:]
                # R07: 落点证据取 sd-cli 自报的后端行(实测,非硬编码)
                blob = (so or "") + "\n" + (se or "")
                hits = [l.strip() for l in blob.splitlines()
                        if any(k in l.lower() for k in ("backend", "device", "using"))]
                row["device_lines"] = hits[:4]
                row["device_hit"] = any("cpu" in l.lower() for l in hits)
                if row["ok"] and not row["device_hit"]:
                    row["ok"] = False
                    row["err"] = (row["err"] + " | R07: 未命中 CPU 落点证据").strip(" |")
            except SystemExit:
                raise
            except Exception as e:
                row["seconds_total"] = round(time.time() - t0, 2)
                row["err"] = str(e)[-1200:]
            finally:
                if pk:
                    pb = pk.stop()
                    row["mem_peak_bytes"] = pb or None
                    row["mem_peak_mb"] = round(pb / 1048576, 1) if pb else None
            row.setdefault("device_lines", [])
            row.setdefault("device_hit", False)
            emit(row, h_src, h_script)
            print(f"  {cell:<30} {row['seconds_total']:6.1f}s "
                  f"{'OK' if row['ok'] else 'FAIL'}", flush=True)


# ---------- B04: 种子自检 ----------
def seed_check():
    print("\n=== 种子自检(C5/DP-16: 同格各 run sha256 必须全同)===", flush=True)
    groups = {}
    for r in OUT["rows"]:
        if r.get("scheme") == "comfyui" and r.get("mode") == "cold" and r.get("ok"):
            groups.setdefault((r["prompt_idx"], r["seed"]), []).append(r)
    fails, insufficient = [], []
    for k, rs in sorted(groups.items()):
        shas = {r.get("sha256") for r in rs}
        if any(s in (None, "") for s in shas) or len(rs) < 2:
            insufficient.append(k)
            print(f"  p{k[0]}_s{k[1]}: n={len(rs)} INSUFFICIENT(样本/哈希不足)", flush=True)
        elif len(shas) == 1:
            print(f"  p{k[0]}_s{k[1]}: n={len(rs)} SAME PASS", flush=True)
        else:
            fails.append(k)
            print(f"  p{k[0]}_s{k[1]}: n={len(rs)} DIFF FAIL (sha集合={len(shas)})", flush=True)
    return fails, insufficient


def main():
    global CKPT_SHA
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True,
                    help="cold|warm|anchor, 可逗号组合")
    ap.add_argument("--n", type=int, default=3, help="cold 每格轮数(DP-14: >=3)")
    a = ap.parse_args()

    stages = [s.strip() for s in a.only.split(",") if s.strip()]
    valid = {"cold", "warm", "anchor"}
    if not stages or not set(stages) <= valid:
        raise SystemExit(f"FATAL(B07): --only 非法 {a.only!r} (允许 {valid})")
    if "cold" in stages and a.n < 3:
        raise SystemExit(f"FATAL(DP-14): --n={a.n} < 3,拒绝开跑")
    OUT["stages"] = stages
    OUT["requested_n"] = a.n if "cold" in stages else None

    h_src, h_script = freeze_old()
    OUT["frozen_src_sha256"] = h_src
    print(f"冻结校验 OK progress={h_src[:16]}… bench4.py={h_script[:16]}…", flush=True)

    load_state()
    OUT["stages"] = sorted(set(OUT.get("stages", []) + stages))
    OUT["frozen_src_sha256"] = h_src
    OUT["offline_window"]["start"] = now_ts()
    print(f"已有 {len(OUT['rows'])} 行(断点续跑) stages={stages} n={a.n}", flush=True)

    CKPT_SHA = ensure_ckpt()
    fp = sha256_text(json.dumps(
        {"prompts": PROMPTS, "neg": NEG, "ckpt": CKPT, "ckpt_sha": CKPT_SHA,
         "size": SIZE, "steps": STEPS, "cfg": CFG, "sampler": SAMPLER,
         "sched": SCHEDULER, "seeds": SEEDS, "precision": PRECISION,
         "clip_skip": CLIP_SKIP, "engine": "comfyui-0.38.0",
         "torch": torch_version()}, sort_keys=True))[:16]

    bad_kill = []
    try:
        if "cold" in stages:
            run_cold(a.n, h_src, h_script, fp)
        if "warm" in stages:
            run_warm(h_src, h_script, fp)
        if "anchor" in stages:
            run_anchor(h_src, h_script, fp)
    finally:
        OUT["offline_window"]["end"] = now_ts()
        OUT["offline_window"]["blocked_attempts"] = list(dict.fromkeys(_BLOCKED))[:50]
        assert_frozen(h_src, h_script, "finally-before-save")   # R01: 先校验
        save()
        assert_frozen(h_src, h_script, "finally")               # R01: 再存后兜底
        print(f"离线窗口 {OUT['offline_window']['start']} ~ "
              f"{OUT['offline_window']['end']} 被拦尝试={len(OUT['offline_window']['blocked_attempts'])} 次",
              flush=True)

    # B11: 跑测窗口内不允许出现非回环出网尝试
    leaks = [b for b in _BLOCKED if "non-loopback" in b]
    print(f"\n离线证据: non-loopback 尝试 {len(leaks)} 次 "
          f"{'(应为 0,被 guard 拦下则为正数但已阻断)' if leaks else ''}", flush=True)
    with open(os.path.join(REPRO, "offline-evidence.json"), "w", encoding="utf-8") as f:
        json.dump({"blocked": _BLOCKED, "window": OUT["offline_window"]},
                  f, ensure_ascii=False, indent=1)

    # 复刻包要素(B13)
    rep = {
        "cmdline": " ".join(sys.argv),
        "python": sys.version,
        "comfy_freeze": sha256_file(os.path.join(E04, "env-comfy.txt")),
        "ckpt_sha256": CKPT_SHA,
        "comfy_zip_sha256": sha256_file(os.path.join(E04, "comfy.zip")),
        "frozen_src_sha256": h_src,
        "bench4_py_sha256": h_script,
        "fingerprint": fp,
    }
    with open(os.path.join(REPRO, f"bench5-repro-{TODAY}.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    fails, insuff = seed_check()
    # B10 修复: 全阶段判定 —— 按 cell 看是否存在成功 attempt(历史失败行已被成功重跑覆盖,R15)
    by_cell = {}
    for r in OUT["rows"]:
        if r.get("mode") in ("cold", "warm", "anchor"):
            by_cell.setdefault(r.get("cell"), []).append(r)
    bad_cells = {c: rs for c, rs in by_cell.items()
                 if not any(x.get("ok") for x in rs)}
    print(f"\n未通过 cell(全阶段): {len(bad_cells)} / {len(by_cell)}", flush=True)
    for c, rs in list(bad_cells.items())[:8]:
        print(f"  - {c} attempts={len(rs)} "
              f"err={str(rs[-1].get('err'))[:80]}", flush=True)
    verdict = []
    if bad_cells:
        verdict.append(f"cells_not_ok={len(bad_cells)}")
    if fails:
        verdict.append(f"seed_diff={len(fails)}")
    if insuff:
        verdict.append(f"seed_insufficient={len(insuff)}")
    if WARM_KILL_FAIL:
        verdict.append(f"warm_kill_fail={WARM_KILL_FAIL[:40]}")
    OUT["verdict"] = "pass" if not verdict else "fail: " + "; ".join(verdict)
    save()
    if verdict:
        print(f"RESULT FAIL ({OUT['verdict']})", flush=True)
        sys.exit(1)
    print("RESULT PASS", flush=True)


if __name__ == "__main__":
    main()
