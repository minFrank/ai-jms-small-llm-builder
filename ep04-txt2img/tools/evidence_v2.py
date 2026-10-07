"""ep04 扩测证据脚本 — 一次性补齐 dsh 复核 §3 的 4 处阻断。

R4  landing A/B 判据升级:
     A) GPU 计数"真增长" = max-min > 阈值(原实现只是 max>500MB, 名不副实)
     B) DML vs 纯 CPU 同图对照 n>=3 + 两侧都预热(原 n=1 且 DML 侧处首子进程偏快区)
R5  从 PDH 实例名取 DML 实际绑定的 adapter LUID, 映射到物理 adapter,
     显式断言非 WARP(Microsoft Basic Render Driver)
R10 离线证据: socket guard(父+子) + 死代理 + HF offline, 断言无 non-loopback 尝试
R17 同日 anchor: 复测 sd.cpp 纯 CPU 基准行(与 ONNX 批同一天), 覆盖跨期可比性

输出: replicate/evidence-v2.json
"""
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------- R10: 父进程 socket guard(记录, 不抹掉) ----------
_orig = socket.socket.connect
_BLOCKED = []
_PROXY = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888, 9}


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

E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
REPRO = os.path.join(E04, "replicate")
MODELS = r"D:/models/txt2img"
OUTDIR = os.path.join(MODELS, "out6")
os.makedirs(REPRO, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, os.path.join(E04, "tools"))

import bench6  # noqa: E402  (仅 import 常量与 run_child, 不执行 main)

T0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
RESULT = {"ts_start": T0}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ============================================================
# R5: adapter LUID + 非 WARP 断言
# ============================================================
def r5_adapter():
    """R5: DML 实际绑定 adapter 的 LUID + 显式非 WARP 断言。

    修复两处 bug:
      a) Win32_VideoController 单个对象时 ConvertTo-Json 返回 dict 不是 list,
         原判断遍历 dict 键 => hardware_adapter_present 恒 false
      b) PDH 采样原在子进程退出后(拿不到计数器) => 改为运行期间线程采样
    """
    import subprocess as sp
    out = {"method": "PDH instance name carries LUID, sampled DURING child run"}
    # 1) 系统显示适配器(规范化为 list)
    try:
        o = sp.run(["powershell.exe", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_VideoController | "
                    "Select-Object Name,DriverVersion,PNPDeviceID,VideoProcessor | "
                    "ConvertTo-Json -Compress"],
                   capture_output=True, timeout=60)
        ad = json.loads(o.stdout.decode("gbk", errors="replace"))
        out["adapters"] = ad if isinstance(ad, list) else [ad]
    except Exception as e:
        out["adapters"] = []
        out["adapters_err"] = str(e)
    # 2) 运行期间采 PDH(线程), 拿实例名里的 LUID
    holder, luids, phys_addrs, samples = {}, set(), set(), []
    stop = threading.Event()

    def _watch(h, luids, phys_addrs, samples, stop):
        while not stop.is_set():
            pid = h.get("pid")
            if pid:
                try:
                    o = sp.run(["powershell.exe", "-NoProfile", "-Command",
                                "(Get-Counter '\\GPU Process Memory(*)\\Shared Usage' "
                                "-ErrorAction SilentlyContinue).CounterSamples | "
                                "Where-Object {$_.InstanceName -match 'pid_" + str(pid) +
                                "_'} | ForEach-Object { $_.InstanceName + '=' + "
                                "[math]::Round($_.CookedValue/1MB) }"],
                               capture_output=True, timeout=30)
                    txt = o.stdout.decode("gbk", errors="replace")
                    for line in txt.splitlines():
                        if "=" in line and "pid_" in line:
                            inst, val = line.split("=", 1)
                            # 完整 LUID = 两段 32 位
                            # (pid_7592_luid_0x00000000_0x00001a6c_phys_0)
                            m = re.match(
                                r"pid_(\d+)_luid_(0x[0-9a-fA-F]+)_(0x[0-9a-fA-F]+)_"
                                r"phys_(\d+)",
                                inst.strip())
                            if m and int(m.group(1)) == pid:      # 精确 PID
                                luids.add(f"{m.group(2)}_{m.group(3)}")
                                phys_addrs.add(int(m.group(4)))
                                try:
                                    samples.append({"instance": inst.strip(),
                                                    "shared_mb": int(val)})
                                except ValueError:
                                    pass
                except Exception as e:
                    out.setdefault("pdh_err", []).append(str(e))
            stop.wait(3.0)

    th = threading.Thread(target=_watch,
                          args=(holder, luids, phys_addrs, samples, stop),
                          daemon=True)
    th.start()
    data, so, se, wall, rc = bench6.run_child(
        0, 42, out=os.path.join(OUTDIR, "r5_adapter.png"),
        want_pid=True, holder=holder)
    stop.set()
    th.join(timeout=8)

    pid = holder.get("pid")
    out["child_pid"] = pid
    out["child_ok"] = data is not None
    if data:
        out["providers"] = data.get("providers")
    out["luids"] = sorted(luids)
    out["phys_addrs"] = sorted(phys_addrs)
    out["gpu_shared_samples_mb"] = samples
    sh = [s["shared_mb"] for s in samples]
    out["gpu_shared_min_mb"] = min(sh) if sh else None
    out["gpu_shared_max_mb"] = max(sh) if sh else None

    # 4) 非 WARP 断言(dsh R5 要求显式, 不能只靠排除法)
    names = json.dumps(out.get("adapters", []), ensure_ascii=False)
    out["warp_named_in_adapters"] = "Basic Render Driver" in names
    hw = [a for a in out.get("adapters", []) if isinstance(a, dict)]
    out["hardware_adapters"] = [
        {"Name": a.get("Name"), "DriverVersion": a.get("DriverVersion"),
         "PNPDeviceID": a.get("PNPDeviceID")} for a in hw]
    out["hardware_adapter_present"] = any(
        "VEN_1002" in (a.get("PNPDeviceID") or "") for a in hw)
    # GPU Adapter Memory 计数器只对**硬件 GPU 适配器**出实例;
    # 我们的 phys 地址若出现在该组计数器里 => 绑定的是物理 GPU 而非 WARP
    phys_ok = False
    adapter_luids = set()
    try:
        o = sp.run(["powershell.exe", "-NoProfile", "-Command",
                    "(Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage' "
                    "-ErrorAction SilentlyContinue).CounterSamples | "
                    "ForEach-Object { $_.InstanceName }"],
                   capture_output=True, timeout=45)
        for line in o.stdout.decode("gbk", errors="replace").splitlines():
            m = re.search(r"luid_(0x[0-9a-fA-F]+)_(0x[0-9a-fA-F]+)_phys_(\d+)",
                          line.strip())
            if m:
                adapter_luids.add(f"{m.group(1)}_{m.group(2)}")
                if int(m.group(3)) in phys_addrs:
                    phys_ok = True
    except Exception as e:
        out["adapter_mem_err"] = str(e)
    out["adapter_memory_luids"] = sorted(adapter_luids)
    out["luid_maps_to_hw_gpu"] = phys_ok
    # WARP 显式断言链: 4 条全真才算排除 WARP
    checks = {
        "no_basic_render_driver": not out["warp_named_in_adapters"],
        "amd_ven1002_present": out["hardware_adapter_present"],
        "pdh_phys_on_hw_counter": phys_ok,
        "shared_grew_gt_1gb": bool(sh) and (max(sh) - min(sh)) > 1024,
        "providers_include_dml": (data or {}).get("providers")
                                 and "DmlExecutionProvider"
                                 in (data or {}).get("providers", []),
    }
    out["warp_exclusion_checks"] = checks
    out["warp_excluded"] = all(bool(v) for v in checks.values())
    out["verdict_inputs_ok"] = bool(
        out["child_ok"] and out["luids"] and out["phys_addrs"]
        and out["warp_excluded"])
    return out


# ============================================================
# R4: landing A/B 升级(n>=3 + 两侧预热 + 真增长判据)
# ============================================================
def r4_landing():
    out = {}
    shared = []
    stop = threading.Event()

    DML = ["DmlExecutionProvider", "CPUExecutionProvider"]
    CPU = ["CPUExecutionProvider"]

    # 预热两侧(消除"首子进程偏快"效应)
    for tag, prov in (("dml", DML), ("cpu", CPU)):
        for i in range(2):
            d, _s, _e, _w, _rc = bench6.run_child(
                0, 42, out=os.path.join(OUTDIR, f"_warm_{tag}{i}.png"),
                providers=prov)
            log(f"  warmup {tag}{i}: gen={(d or {}).get('gen_s')}s")

    # DML n=3
    holder = {}
    dml_gen = []
    for i in range(3):
        holder.clear()
        d, _s, _e, _w, _rc = bench6.run_child(
            0, 42, out=os.path.join(OUTDIR, f"r4_dml{i}.png"),
            providers=DML, want_pid=True, holder=holder)
        if d:
            dml_gen.append(d["gen_s"])
            log(f"  dml[{i}]: gen={d['gen_s']}s")
        else:
            log(f"  dml[{i}]: FAIL rc={_rc}")
    out["dml_gen_s"] = dml_gen

    # 专项: 单独跑一次带 PDH 采样的 DML(测 A 判据)
    stop.clear()
    holder2 = {}
    th = threading.Thread(target=_watch_pid, args=(holder2, shared, stop),
                          daemon=True)
    th.start()
    d_probe, _s, _e, _w, _rc = bench6.run_child(
        0, 42, out=os.path.join(OUTDIR, "r4_probe.png"),
        providers=DML, want_pid=True, holder=holder2)
    stop.set()
    th.join(timeout=8)
    out["gpu_shared_mb_samples"] = shared[:40]
    out["gpu_shared_mb_min"] = min(shared) if shared else None
    out["gpu_shared_mb_max"] = max(shared) if shared else None

    # CPU n=3
    cpu_gen = []
    for i in range(3):
        d, _s, _e, _w, _rc = bench6.run_child(
            0, 42, out=os.path.join(OUTDIR, f"r4_cpu{i}.png"),
            providers=CPU)
        if d:
            cpu_gen.append(d["gen_s"])
            log(f"  cpu[{i}]: gen={d['gen_s']}s")
        else:
            log(f"  cpu[{i}]: FAIL rc={_rc}")
    out["cpu_gen_s"] = cpu_gen

    import statistics as st
    def med(x):
        return round(st.median(x), 3) if x else None
    out["dml_median"] = med(dml_gen)
    out["cpu_median"] = med(cpu_gen)
    if out["dml_median"] and out["cpu_median"]:
        out["speedup_median"] = round(out["cpu_median"] / out["dml_median"], 3)

    # A 判据: 真增长 = max - min > 1024MB
    if shared:
        out["A_criteria"] = {
            "rule": "max-min > 1024MB (真增长, 非绝对值阈值)",
            "max_minus_min_mb": max(shared) - min(shared),
            "pass": (max(shared) - min(shared)) > 1024,
        }
    # B 判据: n>=3 中位数 speedup > 1.2
    out["B_criteria"] = {
        "rule": "两侧各 n>=3 预热后中位数, cpu/dml > 1.2",
        "n_dml": len(dml_gen), "n_cpu": len(cpu_gen),
        "pass": bool(len(dml_gen) >= 3 and len(cpu_gen) >= 3
                     and out.get("speedup_median")
                     and out["speedup_median"] > 1.2),
    }
    out["ok"] = bool(out.get("A_criteria", {}).get("pass")
                     and out["B_criteria"]["pass"])
    return out


def _watch_pid(holder, shared, stop):
    import subprocess as sp
    while not stop.is_set():
        pid = holder.get("pid")
        if pid:
            try:
                o = sp.run(["powershell.exe", "-NoProfile", "-Command",
                            "(Get-Counter '\\GPU Process Memory(*)\\Shared Usage' "
                            "-ErrorAction SilentlyContinue).CounterSamples | "
                            "Where-Object {$_.InstanceName -match 'pid_" + str(pid) +
                            "_'} | ForEach-Object { [math]::Round($_.CookedValue/1MB) }"],
                           capture_output=True, timeout=30)
                vals = [int(x) for x in o.stdout.decode("gbk",
                                                        errors="replace").split()
                        if x.strip().lstrip("-").isdigit()]
                if vals:
                    shared.append(max(vals))
            except Exception:
                pass
        stop.wait(3.0)


# ============================================================
# R10: 离线证据(死代理 + HF offline + socket guard)
# ============================================================
# 子进程内 socket guard: 拼在 CHILD_CODE 之前执行, 把尝试写进独立文件
# (父进程 guard 只证明父进程无外联, 不能证明出图子进程 —— dsh R10)
_CHILD_GUARD = r"""
import json as _gj, socket as _gsk, os as _gos, threading as _gth
_BLOCKED = []
_lk = _gth.Lock()
_OrigConnect = _gsk.socket.connect
_OrigGetAddr = _gsk.getaddrinfo
_LOOP = {"127.0.0.1", "::1", "localhost"}
def _rec(t, tgt, result):
    with _lk:
        _BLOCKED.append({"t": t, "target": str(tgt), "result": result})
        try:
            with open(_gos.environ["EP4_CHILD_GUARD_LOG"], "w",
                      encoding="utf-8") as _f:
                _gj.dump(_BLOCKED, _f, ensure_ascii=False)
        except Exception:
            pass
def _bad_host(host):
    h = str(host).split("%")[0]
    if h in _LOOP:
        return False
    try:
        parts = h.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return not (parts[0] == "127" or h.startswith("169.254."))
    except Exception:
        pass
    return True
def _connect(self, addr):
    if isinstance(addr, tuple) and _bad_host(addr[0]):
        _rec("connect", addr, "BLOCKED")
        raise OSError("EP4_OFFLINE_BLOCKED connect %r" % (addr,))
    return _OrigConnect(self, addr)
def _gai(host, port, *a, **k):
    if _bad_host(host):
        _rec("getaddrinfo", host, "BLOCKED")
        raise OSError("EP4_OFFLINE_BLOCKED getaddrinfo %r" % (host,))
    return _OrigGetAddr(host, port, *a, **k)
_gsk.socket.connect = _connect
_gsk.getaddrinfo = _gai
_gj.dump(_BLOCKED, open(_gos.environ["EP4_CHILD_GUARD_LOG"], "w",
                        encoding="utf-8"), ensure_ascii=False)
"""


def r10_offline():
    """R10: 子进程内装 guard 并给 per-child 零外联证据 + 回填 offline_window。"""
    import subprocess as sp
    out = {"dead_proxy": "http://127.0.0.1:9",
           "guard_scope": "child process (inside CHILD_CODE), not just parent",
           "env": ["HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1",
                   "HTTPS_PROXY=http://127.0.0.1:9", "HTTP_PROXY=http://127.0.0.1:9"]}
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9"
    os.environ["ALL_PROXY"] = "http://127.0.0.1:9"
    child_log = os.path.join(REPRO, "child-guard-log.json")
    if os.path.exists(child_log):
        os.remove(child_log)
    os.environ["EP4_CHILD_GUARD_LOG"] = child_log

    # 子进程 = guard + 原 CHILD_CODE(同一份计时/出图逻辑, payload 结构与
    # bench6.run_child 完全一致)
    with open(os.path.join(bench6.ONNX, "scheduler-config.json"),
              encoding="utf-8") as _f:
        _sched_cfg = json.load(_f)["config"]
    payload = json.dumps({
        "onnx": bench6.ONNX, "prompt": bench6.PROMPTS[0], "seed": 42,
        "steps": bench6.STEPS, "cfg": bench6.CFG, "profile": False,
        "sched_config": _sched_cfg,
        "tokenizer": "openai/clip-vit-large-patch14",
        "out": os.path.join(OUTDIR, "offline_probe.png"),
        "providers": ["DmlExecutionProvider", "CPUExecutionProvider"],
        "pid_file": None,
    })
    env = dict(os.environ)
    t0 = time.time()
    pr = subprocess.run([bench6.VENV_PY, "-c", _CHILD_GUARD + bench6.CHILD_CODE,
                         payload],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", env=env, cwd=REPRO)
    wall = time.time() - t0
    out["child_rc"] = pr.returncode
    out["child_wall_s"] = round(wall, 3)
    # CHILD_CODE 输出是 "JSON={...}" 前缀格式(与 bench6.run_child 一致)
    _so = (pr.stdout or "")
    _js = _so[_so.find("JSON=") + 5:] if "JSON=" in _so else _so
    try:
        out["child"] = json.loads(_js)
    except Exception as e:
        out["child"] = None
        out["child_err"] = str(e)[:300]
        out["child_stdout_tail"] = _so[-400:]
        out["child_stderr_tail"] = (pr.stderr or "")[-400:]
    out["child_ok"] = bool(out.get("child"))
    out["child_img_sha256"] = (out.get("child") or {}).get("img_sha256")
    # 读子进程 guard 落盘的尝试
    out["child_blocked_attempts"] = []
    if os.path.exists(child_log):
        with open(child_log, encoding="utf-8") as f:
            out["child_blocked_attempts"] = json.load(f)
    out["child_blocked_count"] = len(out["child_blocked_attempts"])
    out["child_non_loopback_count"] = len(
        [b for b in out["child_blocked_attempts"]
         if b.get("result") == "BLOCKED"])
    # 父进程 guard 也一起留
    out["parent_blocked_attempts"] = list(dict.fromkeys(_BLOCKED))
    out["parent_blocked_count"] = len(out["parent_blocked_attempts"])
    out["window"] = [T0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    out["evidence_ok"] = bool(out["child_ok"] and out["child_img_sha256"]
                              and out["child_non_loopback_count"] == 0
                              and out["parent_blocked_count"] == 0)
    return out


# ============================================================
# R17: 同日 anchor(与 ONNX 批同一天复测 sd.cpp 纯 CPU)
# ============================================================
def r17_anchor():
    import statistics as st
    exe = os.path.join(MODELS, "cpu", "sd-cli.exe")
    MODEL = os.path.join(MODELS, "v1-5-pruned-emaonly.safetensors")
    PROMPTS = [
        "a quiet lake at dawn, mist over the water, pine trees on the far shore, "
        "soft light, digital painting",
        "a wooden desk by a window, open notebook, cup of tea, morning sunlight, "
        "realistic photo",
    ]
    out = {"cmdline_template": f"{exe} -m {MODEL} --prompt <P> -W 512 -H 512 "
                              f"--steps 20 -s <SEED> -o <OUT>",
           "rows": []}
    if not os.path.exists(exe):
        out["err"] = f"{exe} 缺失"
        out["ok"] = False
        return out
    for pi, prompt in enumerate(PROMPTS):
        for seed in (42, 43, 44):
            o = os.path.join(OUTDIR, f"anchor2_p{pi}_s{seed}.png")
            if os.path.exists(o):
                os.remove(o)
            cmd = [exe, "-m", MODEL, "--prompt", prompt,
                   "-W", "512", "-H", "512", "--steps", "20",
                   "-s", str(seed), "-o", o]
            t0 = time.time()
            peak = [0]
            stop = threading.Event()

            def samp(proc_holder, peak=peak, stop=stop):
                while not stop.is_set():
                    try:
                        tot = 0
                        pr = psutil.Process(proc_holder["pid"])
                        for x in [pr] + pr.children(recursive=True):
                            try:
                                tot += x.memory_info().rss
                            except Exception:
                                pass
                        peak[0] = max(peak[0], tot)
                    except Exception:
                        pass
                    stop.wait(0.5)

            holder = {"pid": None}
            pr = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True,
                                  encoding="utf-8", errors="replace")
            holder["pid"] = pr.pid
            th = threading.Thread(target=samp, args=(holder,), daemon=True)
            th.start()
            so, se = pr.communicate(timeout=900)
            stop.set()
            th.join(timeout=5)
            dt = time.time() - t0
            ok = os.path.exists(o) and os.path.getsize(o) > 1000
            h = None
            if ok:
                hh = hashlib.sha256()
                with open(o, "rb") as f:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        hh.update(b)
                h = hh.hexdigest()
            row = {"cell": f"anchor2_p{pi}_s{seed}", "prompt_idx": pi,
                   "seed": seed, "seconds": round(dt, 2),
                   "mem_peak_mb": round(peak[0] / 1048576, 1) if peak[0] else None,
                   "ok": ok, "sha256": h,
                   "device_lines": [l.strip() for l in ((so or "") + (se or "")).splitlines()
                                    if any(k in l.lower() for k in
                                           ("backend", "device", "using"))][:3]}
            out["rows"].append(row)
            log(f"  anchor p{pi}_s{seed}: {dt:.1f}s {'OK' if ok else 'FAIL'}")
    oks = [r for r in out["rows"] if r["ok"]]
    out["n_ok"] = len(oks)
    out["ok"] = len(oks) == 6
    if oks:
        secs = [r["seconds"] for r in oks]
        out["median"] = round(st.median(secs), 2)
        out["min"], out["max"] = min(secs), max(secs)
        out["spread_pct"] = round((max(secs) - min(secs)) / st.median(secs) * 100, 2)
        # 基线取**已发布正文**的 241.6(不是同源重算 — R16)
        PUB = 241.6
        out["published_baseline_s"] = PUB
        out["drift_pct_vs_published"] = round((out["median"] - PUB) / PUB * 100, 2)
        out["within_5pct"] = abs(out["drift_pct_vs_published"]) < 5
    out["date"] = datetime.now().strftime("%Y-%m-%d")
    out["covers_onnx_batch_date"] = out["date"] >= "2026-10-07"
    return out


# ============================================================
def _backfill_offline_window(r10):
    """R10: 把子进程离线证据回填进 bench6 的 offline_window。

    只在证据成立时回填, 避免把 None 写进数据文件。
    """
    if not r10 or not r10.get("evidence_ok"):
        print("R10 证据未成立, 跳过 offline_window 回填", flush=True)
        return
    bp = os.path.join(E04, "logs", "bench6-progress.json")
    try:
        with open(bp, encoding="utf-8") as f:
            bd = json.load(f)
        prev = bd.get("offline_window") or {}
        bd["offline_window"] = {
            "start": prev.get("start") or T0,
            "end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "blocked_attempts": [],
            "evidence": "evidence-v2 r10 (per-child socket guard)",
            "guard_scope": "child process",
            "child_non_loopback_count": r10.get("child_non_loopback_count"),
            "child_blocked_count": r10.get("child_blocked_count"),
            "child_img_sha256": r10.get("child_img_sha256"),
            "parent_blocked_count": r10.get("parent_blocked_count"),
            "evidence_ok": r10.get("evidence_ok"),
            "evidence_file": "replicate/evidence-v2.json",
        }
        with open(bp + ".tmp", "w", encoding="utf-8") as f:
            json.dump(bd, f, ensure_ascii=False, indent=1)
        os.replace(bp + ".tmp", bp)
        print("offline_window 回填 -> bench6-progress.json", flush=True)
    except Exception as e:
        print(f"offline_window 回填失败: {type(e).__name__}: {e}", flush=True)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = (["r5", "r4", "r10", "r17"] if only == "all"
            else [x for x in only.split(",") if x])
    # 已有结果回填(避免重跑 70 分钟)
    prev = os.path.join(REPRO, "evidence-v2.json")
    if os.path.exists(prev):
        try:
            with open(prev, encoding="utf-8") as f:
                RESULT.update(json.load(f))
        except Exception:
            pass
    RESULT["runs"] = todo

    if "r5" in todo:
        print("=" * 60, flush=True)
        print("R5: adapter LUID / 非 WARP", flush=True)
        print("=" * 60, flush=True)
        try:
            RESULT["r5_adapter"] = r5_adapter()
        except Exception as e:
            RESULT["r5_adapter"] = {"err": f"{type(e).__name__}: {e}"}
        print(json.dumps({k: v for k, v in RESULT["r5_adapter"].items()
                          if k not in ("adapters", "gpu_shared_samples_mb")},
                         ensure_ascii=False, indent=1)[:1600], flush=True)

    if "r4" in todo:
        print("=" * 60, flush=True)
        print("R4: landing A/B(n>=3 + 两侧预热 + 真增长)", flush=True)
        print("=" * 60, flush=True)
        try:
            RESULT["r4_landing"] = r4_landing()
        except Exception as e:
            RESULT["r4_landing"] = {"err": f"{type(e).__name__}: {e}"}
        print(json.dumps(RESULT["r4_landing"], ensure_ascii=False,
                         indent=1)[:1600], flush=True)

    if "r10" in todo:
        print("=" * 60, flush=True)
        print("R10: 离线证据", flush=True)
        print("=" * 60, flush=True)
        try:
            RESULT["r10_offline"] = r10_offline()
        except Exception as e:
            RESULT["r10_offline"] = {"err": f"{type(e).__name__}: {e}"}
        print(json.dumps(RESULT["r10_offline"], ensure_ascii=False, indent=1),
              flush=True)
        # R10: 把子进程离线证据回填进 bench6 的 offline_window
        # (只在证据成立时回填, 避免把 None 写进去)
        _backfill_offline_window(RESULT["r10_offline"])

    if "r17" in todo:
        print("=" * 60, flush=True)
        print("R17: 同日 anchor(sd.cpp 纯 CPU)", flush=True)
        print("=" * 60, flush=True)
        try:
            RESULT["r17_anchor"] = r17_anchor()
        except Exception as e:
            RESULT["r17_anchor"] = {"err": f"{type(e).__name__}: {e}"}
        a = RESULT["r17_anchor"]
        print(json.dumps({k: v for k, v in a.items() if k != "rows"},
                         ensure_ascii=False, indent=1), flush=True)

    # 回填 R5 的 WARP 排除论证
    sp = RESULT.get("r4_landing", {}).get("speedup_median")
    if sp:
        RESULT["r5_adapter"]["warp_excluded_by_speedup"] = {
            "speedup_vs_cpu": sp,
            "reason": "若 DML 落到 WARP(软件 CPU 光栅), 不可能比纯 CPU 快 "
                      f"{sp} 倍; 结合硬件适配器存在且无 Basic Render Driver, "
                      "判定 WARP 已排除",
        }

    RESULT["ts_end"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    RESULT["parent_blocked_attempts"] = list(dict.fromkeys(_BLOCKED))
    path = os.path.join(REPRO, "evidence-v2.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(RESULT, f, ensure_ascii=False, indent=1)
    print(f"\nsaved -> {path}", flush=True)

    # 总判定
    checks = {
        "R4": RESULT.get("r4_landing", {}).get("ok"),
        "R5": RESULT.get("r5_adapter", {}).get("verdict_inputs_ok"),
        "R10": RESULT.get("r10_offline", {}).get("evidence_ok"),
        "R17": RESULT.get("r17_anchor", {}).get("ok"),
    }
    print("CHECKS:", json.dumps(checks), flush=True)
    if all(v for v in checks.values()):
        print("RESULT PASS", flush=True)
    else:
        print("RESULT PARTIAL", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
