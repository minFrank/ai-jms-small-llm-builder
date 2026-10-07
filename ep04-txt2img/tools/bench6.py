#!/usr/bin/env python
"""ep04 阶段2 测速 harness: ONNX/DML 核显路线冷启动基准。

判据来源: REVIEW-p2.md (B5/B7/B8/B10, DP-28~DP-37) + REVIEW-bench5.md 的教训

关键设计:
  B7  每次计时运行 = 独立子进程(DML 首次执行要编译着色器,共用 session 会污染 median;
      每格新进程则每格都吃编译,至少口径一致),编译耗时单列。
  B5  回退门禁三维: ① CPU 时间占比 <5%(按 profiling 的节点 dur 求和,不是节点数)
      ② 去噪主循环关键路径零 CPU 节点 ③ 逐子模块统计(text_encoder/unet/vae 分开)
      profiling 跑与计时跑**分开**(两个子命令),避免 profiling 开销污染头条。
  B10 断言 DML adapter 不是 Basic Render Driver(WARP),记录描述+LUID+驱动版本。
  Q2  scheduler 断言在 harness 不在导出脚本: 比对 sigma/timestep 数组哈希,不比类名。
  P-6 cfg=7 → 每步 cond+uncond 两次前向,UNet 图按 batch=2 导出。
  与阶段1/已发布口径一致: prompt 2句 × seed 42/43/44 × 512×512 × steps 20 × cfg 7.0

用法:
  python bench6.py --mode timing --n 3     # 冷启动计时(每格独立进程)
  python bench6.py --mode profiling        # 单格 profiling(回退门禁证据)
  python bench6.py --mode adapter          # B10 adapter 断言
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
VENV_PY = r"D:/ep04/onnx/venv/Scripts/python.exe"
ONNX = r"D:/ep04/onnx/sd15"
MODEL = r"D:/models/txt2img/v1-5-pruned-emaonly.safetensors"
LOG = os.path.join(E04, "logs", "bench6-progress.json")
OUTDIR = r"D:/models/txt2img/out6"
REPRO = os.path.join(E04, "replicate")
BENCH4 = os.path.join(E04, "tools", "bench4.py")
SCHEMA_VERSION = 3
TODAY = datetime.now().strftime("%Y%m%d")
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(REPRO, exist_ok=True)

PROMPTS = [
    "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
]
NEG = ""
SEEDS = [42, 43, 44]
SIZE, STEPS, CFG = (512, 512), 20, 7.0
PRECISION = {"text_encoder": "fp32", "unet": "fp16", "vae": "fp32"}

OUT = {
    "schema_version": SCHEMA_VERSION,
    "ts_start": time.strftime("%Y-%m-%d %H:%M:%S"),
    "stages": [],
    "requested_n": None,
    "frozen_src_sha256": None,
    "offline_window": {"start": None, "end": None, "blocked_attempts": []},
    "verdict": None,
    "rows": [],
}


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def onnx_group_sha(part_dir):
    """R6: model.onnx + 它引用的全部 external data 一起算(否则只 hash 0.9MB 图)。"""
    opath = os.path.join(part_dir, "model.onnx")
    files = [opath] if os.path.isfile(opath) else []
    if files:
        try:
            import onnx
            m = onnx.load(opath, load_external_data=False)
            refs = set()
            for t in m.graph.initializer:
                for kv in t.external_data:
                    if kv.key == "location":
                        refs.add(os.path.join(part_dir, kv.value))
            for n in m.graph.node:
                for a in n.attribute:
                    if a.HasField("t"):
                        for kv in a.t.external_data:
                            if kv.key == "location":
                                refs.add(os.path.join(part_dir, kv.value))
            for r in sorted(refs):
                if os.path.isfile(r):
                    files.append(r)
        except Exception:
            pass
    h = hashlib.sha256()
    for f in files:
        h.update(os.path.basename(f).encode())
        with open(f, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
    return h.hexdigest()


def runtime_versions():
    """R6: 参与出数的库版本(换版本 = 换配方)。"""
    out = {}
    try:
        import importlib.metadata as md
        for pkg in ("onnxruntime-directml", "onnx", "torch", "diffusers",
                    "transformers", "numpy", "onnxruntime"):
            try:
                out[pkg] = md.version(pkg)
            except Exception:
                out[pkg] = "(缺)"
    except Exception as e:
        out["err"] = str(e)
    return out


# ---------- C1/B8: 冻结旧数据(复用阶段1的冻结副本 + deep-equal 断言) ----------
def freeze_old():
    src = os.path.join(E04, "logs", "bench4-progress.json")
    if not os.path.exists(src):
        raise SystemExit("FATAL(C1): 缺 bench4-progress.json")
    dated = os.path.join(E04, "logs", f"bench4-progress.frozen.{TODAY}.json")
    if not os.path.exists(dated):
        shutil.copy2(src, dated)
    h_src, h_frozen = sha256_file(src), sha256_file(dated)
    if h_src != h_frozen:
        raise SystemExit(f"FATAL(C1): 源与冻结副本不一致 {h_src[:16]} vs {h_frozen[:16]}")
    # B8: 阶段1 的数据文件也纳入冻结(不得被阶段2改动)
    p5 = os.path.join(E04, "logs", "bench5-progress.json")
    h5 = sha256_file(p5)
    if not h5:
        raise SystemExit("FATAL(B8): 缺 bench5-progress.json(阶段1数据)")
    h_bench4 = sha256_file(BENCH4)
    if not h_bench4:
        raise SystemExit("FATAL: 缺 bench4.py")
    return h_src, h5, h_bench4


def assert_frozen(h_src, h5, h_bench4, where):
    if sha256_file(os.path.join(E04, "logs", "bench4-progress.json")) != h_src:
        raise SystemExit(f"FATAL(C1)@{where}: bench4-progress.json 被改动")
    if sha256_file(os.path.join(E04, "logs", "bench5-progress.json")) != h5:
        raise SystemExit(f"FATAL(B8)@{where}: bench5-progress.json 被改动")
    if sha256_file(BENCH4) != h_bench4:
        raise SystemExit(f"FATAL(C11)@{where}: bench4.py 被改动")


def load_state():
    if not os.path.exists(LOG):
        return
    try:
        with open(LOG, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        raise SystemExit(f"FATAL(B06): {LOG} 解析失败(拒绝空历史覆盖): {e}")
    if d.get("schema_version") not in (None, SCHEMA_VERSION):
        raise SystemExit(f"FATAL: schema_version={d.get('schema_version')} 不兼容")
    if not isinstance(d.get("rows", []), list):
        raise SystemExit("FATAL: rows 类型损坏")
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
            raise SystemExit(f"FATAL(B06): 盘上 JSON 损坏,停止写入: {e}")
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


def attempt_of(cell):
    return sum(1 for r in OUT["rows"] if r.get("cell") == cell)


def done_ok(cell, fp):
    for r in OUT["rows"]:
        if r.get("cell") == cell and r.get("ok"):
            if r.get("fingerprint") != fp:
                raise SystemExit(
                    f"FATAL(B08): {cell} 已存在但指纹不一致,需人工确认 "
                    f"旧行={r.get('fingerprint')} 本轮={fp}")
            return True
    return False


def emit(row, hashes):
    row["attempt"] = attempt_of(row["cell"]) + 1
    OUT["rows"].append(row)
    save()
    assert_frozen(*hashes, row["cell"])


# ---------- B10: adapter 断言 ----------
def check_adapter():
    import onnxruntime as ort
    info = {"providers_available": ort.get_available_providers(),
            "ort_version": ort.__version__}
    if "DmlExecutionProvider" not in info["providers_available"]:
        raise SystemExit("FATAL(B10): 无 DmlExecutionProvider")
    try:
        import onnxruntime_directml
        info["dml_module"] = getattr(onnxruntime_directml, "__file__", "?")
    except Exception as e:
        info["dml_module_err"] = str(e)
    # DXGI adapter 枚举(WARP 检测)
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object Name,DriverVersion,PNPDeviceID | ConvertTo-Json -Compress"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60)
        info["adapters"] = json.loads(out.stdout or "[]")
    except Exception as e:
        info["adapters_err"] = str(e)
    ids = json.dumps(info.get("adapters", ""))
    if "ROOT\\BasicRenderDriver" in ids or "Microsoft Basic Render Driver" in ids:
        info["warp_suspected"] = True
    else:
        info["warp_suspected"] = False
    return info


# ---------- Q2: scheduler 断言(sigma 数组哈希) ----------
def scheduler_check():
    """断言 ONNX harness 用的 scheduler 配置 = 已发布 diffusers 行的配置。"""
    sp = os.path.join(ONNX, "scheduler-config.json")
    if not os.path.exists(sp):
        raise SystemExit("FATAL(Q2): 缺 scheduler-config.json")
    with open(sp, encoding="utf-8") as f:
        sc = json.load(f)
    import torch
    from diffusers import EulerDiscreteScheduler, StableDiffusionPipeline

    # 已发布 diffusers 行: from_single_file 默认 PNDM(gen_diffusers_one.py 未改 scheduler)
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL, torch_dtype=torch.float32, local_files_only=True)
    pub = type(pipe.scheduler).__name__
    sig = None
    try:
        # sigma 序列: 用 20 步的 sigmas 哈希(可比性锚点)
        import numpy as np
        sch = pipe.scheduler
        sch.set_timesteps(STEPS)
        sig = hashlib.sha256(
            np.asarray(sch.sigmas, dtype=np.float64).tobytes()).hexdigest()[:16]
    except Exception as e:
        sig = f"err:{e}"
    return {"published_scheduler_class": pub,
            "exported_default_class": sc.get("class"),
            "published_sigma_sha256": sig,
            "euler_config": sc.get("euler_config"),
            "match": pub == sc.get("class")}


# ---------- 冷启动计时子进程单元 ----------
CHILD_CODE = r'''
import json, os, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# R2: 计时起点放在第一条 import 之前(含解释器启动后的全部开销)
t0 = time.time()

# landing 模式: 把本进程 PID 落盘, 供父进程做 PDH 采样(须尽早, 采样覆盖整段)
_A0 = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
if _A0.get("pid_file"):
    try:
        with open(_A0["pid_file"], "w") as _pf:
            _pf.write(str(os.getpid()))
    except Exception:
        pass

import numpy as np
import onnxruntime as ort

t_imp = time.time()
A = json.loads(sys.argv[1])

opts = ort.SessionOptions()
# R4: log_severity_level=0 才能收到 ORT 的静默回退 warning(原 3 会压掉)
opts.log_severity_level = 0
# landing 模式可指定 providers(DML 对 CPU 的同图对照)
prov = A.get("providers") or ["DmlExecutionProvider", "CPUExecutionProvider"]
if A.get("profile"):
    opts.enable_profiling = True     # R4: 三张图全开,不是只开 unet

sess = {}
for p in ("text_encoder", "unet", "vae"):
    sess[p] = ort.InferenceSession(os.path.join(A["onnx"], p, "model.onnx"),
                                   opts, providers=prov)
t_sess = time.time()

# DP-10: 自身进程 RSS 采样(0.4s)
import threading as _th
_peak = [0]
_stop = _th.Event()
import psutil as _psu
_self = _psu.Process()


def _sample():
    while not _stop.is_set():
        try:
            _peak[0] = max(_peak[0], _self.memory_info().rss)
        except Exception:
            pass
        _stop.wait(0.4)


_th.Thread(target=_sample, daemon=True).start()
try:
    _peak[0] = max(_peak[0], _self.memory_info().rss)
except Exception:
    pass

# ---- Q2: scheduler + tokenizer(与已发布 diffusers 行同配置) ----
from diffusers import PNDMScheduler
import torch
sch = PNDMScheduler.from_config(A["sched_config"])
sch.set_timesteps(A["steps"])

from transformers import CLIPTokenizer
_SNAP = os.path.join(os.environ.get("USERPROFILE", ""), ".cache", "huggingface",
                     "hub", "models--stable-diffusion-v1-5--stable-diffusion-v1-5",
                     "snapshots")
_tok = None
for _r in sorted(os.listdir(_SNAP)) if os.path.isdir(_SNAP) else []:
    _cand = os.path.join(_SNAP, _r, "tokenizer")
    if os.path.isdir(_cand):
        _tok = _cand
        break
if not _tok:
    raise SystemExit("FATAL(B1): 本地缓存里找不到 tokenizer")
tok = CLIPTokenizer.from_pretrained(_tok)
A["tokenizer"] = _tok
t_init = time.time()


def encode(text):
    ids = tok(text, padding="max_length", max_length=77,
              return_tensors="np").input_ids.astype(np.int64)
    return sess["text_encoder"].run(None, {"input": ids})[0]


# ---- gen(去噪循环) ----
t1 = time.time()
emb = encode(A["prompt"])
unemb = encode("")
_rng = np.random.default_rng(A["seed"])
lat = _rng.standard_normal((1, 4, 64, 64)).astype(np.float32)
emb_full = np.concatenate([unemb, emb], axis=0)   # P-6: batch=2 CFG

first_unet_s = None
for i, t in enumerate(sch.timesteps):
    tt = np.array([float(t)] * 2, dtype=np.float32)
    lat2 = np.concatenate([lat, lat], axis=0).astype(np.float16)
    _tu = time.time()
    noise_pred = sess["unet"].run(None, {
        "sample": lat2, "timestep": tt,
        "encoder_hidden_states": emb_full.astype(np.float16)})[0]
    if i == 0:
        first_unet_s = time.time() - _tu    # R3: 首次执行(含 DML 编译)单列
    noise_uncond, noise_cond = noise_pred[0], noise_pred[1]
    noise_pred = noise_uncond + A["cfg"] * (noise_cond - noise_uncond)
    _st = sch.step(torch.from_numpy(noise_pred), t, torch.from_numpy(lat),
                   return_dict=False)[0]
    lat = _st.detach().cpu().numpy().astype(np.float32)
gen_s = time.time() - t1

t2 = time.time()
img = sess["vae"].run(None, {"input": (lat / 0.18215).astype(np.float32)})[0]
dec_s = time.time() - t2

# ---- R2: 冷启动头条口径到此为止(不含 PNG 落盘/哈希/采样收尾) ----
t_cold_end = time.time()
cold_total_s = t_cold_end - t0

# ---- 收尾: 停采样 + PNG 落盘 + sha(全部在计时窗口之外) ----
_stop.set()
time.sleep(0.5)
try:
    _peak[0] = max(_peak[0], _self.memory_info().rss)
except Exception:
    pass

img_sha, img_path = None, A.get("out")
if img_path:
    from PIL import Image
    arr = np.clip((np.asarray(img)[0].transpose(1, 2, 0) + 1.0) * 127.5,
                  0, 255).astype("uint8")
    os.makedirs(os.path.dirname(img_path) or ".", exist_ok=True)
    if os.path.exists(img_path):
        os.remove(img_path)              # B03: 先删旧,防残留假 OK
    Image.fromarray(arr).save(img_path)
    import hashlib as _hl
    _h = _hl.sha256()
    with open(img_path, "rb") as _f:
        for _b in iter(lambda: _f.read(1 << 20), b""):
            _h.update(_b)
    img_sha = _h.hexdigest()

# ---- R4: 三张图的 profile 全部收口 ----
profiles = []
warnings = []
if A.get("profile"):
    for p in ("text_encoder", "unet", "vae"):
        try:
            pf = sess[p].end_profiling()
            if pf and not os.path.isabs(pf):
                pf = os.path.join(os.getcwd(), pf)
            profiles.append(pf)
        except Exception as e:
            profiles.append(None)
            warnings.append(f"end_profiling {p}: {e}")

# ---- R4: 断言 profile 覆盖了被测负载(不满足则该 gate 无效) ----
prof_total_us = None
prof_by_provider = {}
prof_files = [p for p in profiles if p and os.path.exists(p)]
if prof_files:
    for _pf in prof_files:
        try:
            with open(_pf, encoding="utf-8") as _f:
                _pr = json.load(_f)
            _ev = _pr if isinstance(_pr, list) else _pr.get("traceEvents", [])
            for _e in _ev:
                if not isinstance(_e, dict) or _e.get("cat") != "Node":
                    continue
                if "dur" not in _e:
                    continue
                _a = _e.get("args") or {}
                _p = (_a.get("provider") or _a.get("Execution Provider")
                      or "unknown")
                prof_by_provider[_p] = prof_by_provider.get(_p, 0) + _e["dur"]
        except Exception as e:
            warnings.append(f"read profile {_pf}: {e}")
    prof_total_us = sum(prof_by_provider.values())

print("JSON=" + json.dumps({
    "import_s": round(t_imp - t0, 3),
    "session_s": round(t_sess - t_imp, 3),
    "init_s": round(t_init - t_sess, 3),
    "load_s": round(t_sess - t0, 3),
    "gen_s": round(gen_s, 3),
    "decode_s": round(dec_s, 3),
    "cold_total_s": round(cold_total_s, 3),
    "first_unet_run_s": round(first_unet_s, 3) if first_unet_s else None,
    "providers": sess["unet"].get_providers(),
    "nfe": len(sch.timesteps),
    "profiles": profiles,
    "prof_total_us": prof_total_us,
    "prof_by_provider": prof_by_provider,
    "warnings": warnings,
    "img_shape": list(img.shape),
    "img_sha256": img_sha,
    "mem_peak_bytes": _peak[0] or None,
    "img_mean": round(float(np.asarray(img).mean()), 3),
}))
'''


def run_child(prompt_idx, seed, profile=False, out=None, providers=None,
              want_pid=False, holder=None):
    with open(os.path.join(ONNX, "scheduler-config.json"), encoding="utf-8") as f:
        sched_cfg = json.load(f)["config"]
    pid_file = None
    if want_pid:
        pid_file = os.path.join(E04, "logs", "landing_child.pid")
        if os.path.exists(pid_file):
            os.remove(pid_file)
    args = {
        "onnx": ONNX, "prompt": PROMPTS[prompt_idx], "seed": seed,
        "steps": STEPS, "cfg": CFG, "profile": profile,
        "sched_config": sched_cfg,
        "tokenizer": "openai/clip-vit-large-patch14",
        "out": out,
        "providers": providers,
        "pid_file": pid_file,
    }
    payload = json.dumps(args)
    env = dict(os.environ)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    t0 = time.time()
    pr = subprocess.Popen([VENV_PY, "-c", CHILD_CODE, payload],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="replace", env=env)
    # landing 模式: 轮询 pid_file, 让父进程的 PDH 采样能对准这个 PID
    if want_pid and holder is not None and pid_file:
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                with open(pid_file) as _f:
                    holder["pid"] = int(_f.read().strip())
                break
            except Exception:
                if pr.poll() is not None:
                    break
                time.sleep(0.4)
    try:
        so, se = pr.communicate(timeout=1800)
    except subprocess.TimeoutExpired:
        pr.kill()
        so, se = pr.communicate()
        wall = time.time() - t0
        return None, so, se, wall, -9
    wall = time.time() - t0
    data = None
    for line in (so or "").splitlines():
        if line.startswith("JSON="):
            try:
                data = json.loads(line[5:])
            except Exception:
                pass
    return data, so, se, wall, pr.returncode


def analyze_profile(prof_path):
    """B5: 按 provider 分组统计节点 dur 求和(不是节点数)。
    ORT 的 profile JSON 顶层可能是 list(直接事件数组)或 dict(含 traceEvents)。"""
    with open(prof_path, encoding="utf-8") as f:
        prof = json.load(f)
    events = prof if isinstance(prof, list) else prof.get("traceEvents", [])
    by_prov, by_node = {}, {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("cat") != "Node" or "dur" not in ev:
            continue
        name = ev.get("name", "?")
        dur = ev["dur"]
        args = ev.get("args") or {}
        prov = args.get("provider") or args.get("Execution Provider") or "unknown"
        by_prov[prov] = by_prov.get(prov, 0) + dur
        by_node[name] = by_node.get(name, 0) + dur
    total = sum(by_prov.values())
    pct = {k: (v / total * 100 if total else 0) for k, v in by_prov.items()}
    return {"by_provider_us": by_prov, "total_us": total,
            "pct_by_provider": {k: round(v, 2) for k, v in pct.items()},
            "top_nodes": sorted(by_node.items(), key=lambda x: -x[1])[:10]}


def pdh_sample(pid, counter, tries=3):
    """R5/R9: 按 PID 查 PDH 的 per-process GPU 计数器(Windows 中文系统按 GBK 解)。"""
    cmd = ("powershell.exe -NoProfile -Command "
           "\"(Get-Counter '\\GPU Process Memory(*)\\" + counter +
           "' -ErrorAction SilentlyContinue).CounterSamples | "
           "Where-Object {$_.InstanceName -like '*" + str(pid) +
           "*'} | ForEach-Object { [math]::Round($_.CookedValue) }\"")
    for _ in range(tries):
        try:
            o = subprocess.run(cmd, capture_output=True, timeout=25)
            txt = o.stdout.decode("gbk", errors="replace")
            vals = [int(x) for x in txt.split() if x.strip().lstrip("-").isdigit()]
            if vals:
                return max(vals)
        except Exception:
            pass
    return None


def run_landing(hashes, fp, qc):
    """R4 落点证据(可证版): ORT profiling 度量不到 DML 的 GPU 执行时间
    (6 格实测覆盖率 2.8-5.2%),改用两条可证证据:
      A) 跑 DML 期间该 PID 的 PDH GPU Shared/Dedicated 计数器必须增长
      B) 同一图、同输入, DML 前向耗时 vs 纯 CPU 前向耗时对照
    """
    import threading as th
    out_png = os.path.join(OUTDIR, "landing_dml.png")
    # ---- A) DML 跑 + PDH 采样 ----
    proc_holder = {}
    samples = []
    stop = th.Event()

    def _watch():
        while not stop.is_set():
            pid = proc_holder.get("pid")
            if pid:
                samples.append({
                    "ts": round(time.time(), 2),
                    "shared": pdh_sample(pid, "Shared Usage", tries=1),
                    "dedicated": pdh_sample(pid, "Dedicated Usage", tries=1),
                })
            stop.wait(3.0)

    th.Thread(target=_watch, daemon=True).start()
    # 记录子进程 PID: 通过一个临时标记文件由 run_child 无法直接给, 改为
    # 先起一次空跑拿 PID 太绕 —— 直接在 run_child 里回传 pid。
    data_dml, so, se, wall, rc = run_child(0, 42, out=out_png, want_pid=True,
                                           holder=proc_holder)
    stop.set()
    time.sleep(1)
    if data_dml is None:
        print(f"  landing DML FAIL rc={rc} {(se or '')[-300:]}", flush=True)
        return {"ok": False, "err": "DML run failed"}

    sh = [s["shared"] for s in samples if s.get("shared")]
    de = [s["dedicated"] for s in samples if s.get("dedicated")]
    dml_gen = data_dml["gen_s"]

    # ---- B) 纯 CPU 同图对照 ----
    out_png2 = os.path.join(OUTDIR, "landing_cpu.png")
    data_cpu, so2, se2, wall2, rc2 = run_child(
        0, 42, out=out_png2, want_pid=False, holder={},
        providers=["CPUExecutionProvider"])
    cpu_gen = data_cpu["gen_s"] if data_cpu else None

    res = {
        "dml_gen_s": dml_gen,
        "cpu_gen_s": cpu_gen,
        "dml_providers": data_dml["providers"],
        "cpu_providers": (data_cpu or {}).get("providers"),
        "gpu_shared_max": max(sh) if sh else None,
        "gpu_shared_min": min(sh) if sh else None,
        "gpu_dedicated_max": max(de) if de else None,
        "pdh_samples": len(samples),
        "samples_head": samples[:4],
        "cpu_providers_is_cpu_only": (data_cpu or {}).get("providers") == [
            "CPUExecutionProvider"],
        "child_err": data_dml.get("warnings") or [],
    }
    # 判据 A: GPU 计数器在跑期间有显著读数
    res["A_gpu_counter_grew"] = bool(sh) and (max(sh) > 500 * 1048576)
    # 判据 B: DML 明显快于纯 CPU(同图同输入)
    if cpu_gen and dml_gen:
        res["speedup_vs_cpu"] = round(cpu_gen / dml_gen, 3)
        res["B_dml_faster_than_cpu"] = cpu_gen > dml_gen * 1.2
    else:
        res["speedup_vs_cpu"] = None
        res["B_dml_faster_than_cpu"] = False
    res["ok"] = bool(res["A_gpu_counter_grew"] and res["B_dml_faster_than_cpu"])

    row = {"cell": "landing_p0_s42", "scheme": "onnx-dml", "mode": "landing",
           "prompt_idx": 0, "seed": 42, "run_idx": 0, "steps": STEPS,
           "size": "512x512", "cfg": CFG, "attempt": 0, "ts": now_ts(),
           "fingerprint": fp, "requested_n": 1,
           "seconds_gen": dml_gen, "seconds_total": data_dml.get("cold_total_s"),
           "cpu_gen_s": cpu_gen,
           "providers": data_dml["providers"],
           "landing": res,
           "sha256": data_dml.get("img_sha256"),
           "ok": res["ok"],
           "err": "" if res["ok"] else
                  ("A_FAIL 无GPU计数" if not res["A_gpu_counter_grew"]
                   else "B_FAIL DML未显著快于CPU")}
    emit(row, hashes)
    print("  landing:", json.dumps({k: v for k, v in res.items()
                                    if k != "samples_head"},
                                   ensure_ascii=False)[:600], flush=True)
    print("  VERDICT:", "PASS" if res["ok"] else "FAIL", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["adapter", "timing", "profiling", "landing"])
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--force", action="store_true",
                    help="忽略已有成功行强制重跑(C4: 污染重跑, 上限 2 次)")
    ap.add_argument("--cells", default=None,
                    help="只跑指定格, 逗号分隔如 p0_s42(C4: 同格离散>5% 定向重跑)")
    ap.add_argument("--warmup", type=int, default=0,
                    help="正式采集前先跑 N 个不入表的预热子进程(C4 批首效应: "
                         "实测每次进程启动后首个子进程偏快约 20s, 跨 3 批复现 "
                         "94.0/91.0/94.7s, 属冷机高频而非随机噪声)")
    a = ap.parse_args()

    hashes = freeze_old()
    print(f"冻结校验 OK b4={hashes[0][:16]}… b5={hashes[1][:16]}… "
          f"b4.py={hashes[2][:16]}…", flush=True)
    load_state()

    if a.mode == "adapter":
        info = check_adapter()
        with open(os.path.join(REPRO, f"adapter-{TODAY}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=1, default=str)
        print(json.dumps(info, ensure_ascii=False, indent=1, default=str))
        if info.get("warp_suspected"):
            print("RESULT FAIL warp_suspected", flush=True)
            sys.exit(1)
        print("RESULT PASS", flush=True)
        return

    if a.mode == "timing" and a.n < 3:
        raise SystemExit(f"FATAL(DP-14): --n={a.n} < 3")

    OUT["stages"] = sorted(set(OUT.get("stages", []) + [a.mode]))
    OUT["frozen_src_sha256"] = hashes[0]
    if a.mode == "timing":
        OUT["requested_n"] = a.n
    OUT["offline_window"]["start"] = OUT["offline_window"].get("start") or now_ts()

    qc = scheduler_check()
    print("Q2 scheduler:", json.dumps(qc, ensure_ascii=False), flush=True)
    if not qc["match"]:
        print("  WARN: exported default != published (按 §4.1 需跨栈标签)", flush=True)

    fp = sha256_text(json.dumps({
        "prompts": PROMPTS, "neg": NEG, "model": sha256_file(MODEL),
        # R6: 指纹必须覆盖 external data 全组, 不然只 hash 0.9MB 的 model.onnx
        #     等于没冻结权重
        "onnx": {p: onnx_group_sha(os.path.join(ONNX, p))
                 for p in PRECISION},
        "precision": PRECISION, "size": SIZE, "steps": STEPS, "cfg": CFG,
        "seeds": SEEDS, "sched": qc["published_scheduler_class"],
        # R6: 运行期版本也进指纹(换版本 = 换配方)
        "versions": runtime_versions(),
        # R6: harness 源码自身进指纹(改代码 = 换口径)
        "harness_sha": sha256_file(os.path.abspath(__file__)),
        "sched_config_sha": sha256_file(
            os.path.join(ONNX, "scheduler-config.json")),
    }, sort_keys=True, default=str))[:16]

    OUT["fingerprint"] = fp
    OUT["scheduler_check"] = qc
    print(f"已有 {len(OUT['rows'])} 行 stages={OUT['stages']} n={a.n} fp={fp}",
          flush=True)

    # landing 模式: 独立的落点证据(不进 timing 循环)
    if a.mode == "landing":
        res = run_landing(hashes, fp, qc)
        OUT["offline_window"]["end"] = now_ts()
        OUT["stages"] = sorted(set(OUT.get("stages", []) + ["landing"]))
        save()
        assert_frozen(*hashes, "landing")
        OUT["landing"] = res
        save()
        if not res.get("ok"):
            print("RESULT FAIL landing", flush=True)
            sys.exit(1)
        print("RESULT PASS landing", flush=True)
        return

    # C4 批首效应预热: 跑 N 个子进程但不写行(让系统进入稳态再正式采集)
    if a.warmup and a.mode in ("timing", "profiling"):
        for w in range(a.warmup):
            t_w = time.time()
            try:
                wd = os.path.join(OUTDIR, "_warmup.png")
                wd_data, _s, _e, _wwall, _wrc = run_child(
                    0, 42, out=wd,
                    providers=["DmlExecutionProvider", "CPUExecutionProvider"])
                wgen = (wd_data or {}).get("gen_s")
                print(f"  [warmup {w + 1}/{a.warmup}] gen={wgen}s "
                      f"wall={round(_wwall, 1)}s rc={_wrc}", flush=True)
            except Exception as we:
                print(f"  [warmup {w + 1}] err={we}", flush=True)
            if os.path.exists(os.path.join(OUTDIR, "_warmup.png")):
                try:
                    os.remove(os.path.join(OUTDIR, "_warmup.png"))
                except OSError:
                    pass

    n = a.n if a.mode == "timing" else 1
    want_cells = None
    if a.cells:
        want_cells = {c.strip() for c in a.cells.split(",") if c.strip()}
        print(f"定向重跑格: {sorted(want_cells)}", flush=True)
    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            if want_cells and f"p{p}_s{seed}" not in want_cells:
                continue
            for run in range(n):
                cell = f"onnx_{'cold' if a.mode == 'timing' else 'prof'}_p{p}_s{seed}_r{run}"
                if not a.force and done_ok(cell, fp):
                    print(f"  {cell:<32} skip", flush=True)
                    continue
                # C4 重跑上限 2 次
                if attempt_of(cell) >= 2:
                    print(f"  {cell:<32} skip(重跑上限)", flush=True)
                    continue
                row = {"cell": cell, "scheme": "onnx-dml", "mode": a.mode,
                       "prompt_idx": p, "prompt_text": PROMPTS[p],
                       "prompt_sha256": sha256_text(PROMPTS[p]),
                       "negative_prompt": NEG, "seed": seed, "run_idx": run,
                       "steps": STEPS, "size": "512x512", "cfg": CFG,
                       "sampler": qc["published_scheduler_class"],
                       "scheduler": qc["published_scheduler_class"],
                       "precision": "unet=fp16,te=fp32,vae=fp32",
                       "clip_skip": 1,
                       "requested_n": OUT.get("requested_n"),
                       "attempt": 0, "ts": now_ts(),
                       "timing_scope": "cold_incl_session_create",
                       "shared_mem_included": False,
                       "fingerprint": fp, "cmdline": " ".join(sys.argv),
                       "seconds_total": None, "seconds_gen": None,
                       "seconds_load": None, "seconds_decode": None,
                       "compile_s": None, "mem_peak_bytes": None,
                       "mem_peak_mb": None, "providers": None,
                       "fallback_pct": None, "sha256": None,
                       "ok": False, "err": ""}
                try:
                    out_png = os.path.join(OUTDIR, cell + ".png")
                    data, so, se, wall, rc = run_child(
                        p, seed, profile=(a.mode == "profiling"), out=out_png)
                    if data is None:
                        row["err"] = f"rc={rc} no-json stdout={(so or '')[-400:]} " \
                                     f"stderr={(se or '')[-400:]}"
                    else:
                        # R2: 冷启动头条 = 子进程 cold_total_s(不含 PNG/收尾);
                        #     wall = 父进程看到的进程级总时长,单列供对账
                        row["seconds_total"] = data.get("cold_total_s")
                        row["seconds_gen"] = data["gen_s"]
                        row["seconds_load"] = data["load_s"]
                        row["seconds_decode"] = data["decode_s"]
                        row["seconds_wall"] = round(wall, 2)
                        row["import_s"] = data.get("import_s")
                        row["session_s"] = data.get("session_s")
                        row["init_s"] = data.get("init_s")
                        # R3: 首次执行(含 DML 编译)单列,不再冒充 load_s
                        row["compile_s"] = data.get("first_unet_run_s")
                        row["providers"] = data["providers"]
                        row["nfe"] = data["nfe"]
                        row["img_mean"] = data.get("img_mean")
                        row["sha256"] = data.get("img_sha256")
                        mb = data.get("mem_peak_bytes")
                        row["mem_peak_bytes"] = mb
                        row["mem_peak_mb"] = round(mb / 1048576, 1) if mb else None
                        row["child_warnings"] = data.get("warnings") or []
                        row["ok"] = True
                        if data.get("cold_total_s") is None:
                            row["ok"] = False
                            row["err"] = "R2: 无 cold_total_s"
                        if not row["sha256"]:
                            row["ok"] = False
                            row["err"] = "B03: 无图片 sha256(未出图)"
                        if "DmlExecutionProvider" not in (data["providers"] or []):
                            row["ok"] = False
                            row["err"] = f"B5: unet 未在 DML 上: {data['providers']}"
                        # R4: 三张图 profile 的门禁
                        if a.mode == "profiling":
                            ptu = data.get("prof_total_us")
                            byp = data.get("prof_by_provider") or {}
                            row["prof_total_us"] = ptu
                            row["prof_by_provider"] = byp
                            row["profiles"] = [p for p in (data.get("profiles") or [])
                                               if p]
                            if not ptu:
                                row["ok"] = False
                                row["err"] = (row["err"] +
                                              " | R4: 无 profile 数据").strip(" |")
                            else:
                                # R4 实测结论: ORT profiling 度量不到 DML 的 GPU 执行
                                # 时间(6 格覆盖率稳定 2.8-5.2%, DML kernel 异步、profile
                                # 只记 host 侧提交)。因此本 gate 只能给出
                                # "未记录到 CPU 节点"这一条弱证据, **不能**据此写
                                # "CPU 占比 0%"(那是假绿)。覆盖率如实记进字段;
                                # 覆盖率不足时本行降级为证据不足, 由 landing 模式
                                # (PDH GPU 计数 + DML/CPU 同图对照)兜底判落点。
                                cov = ptu / 1e6 / (data["gen_s"] or 1)
                                row["prof_coverage"] = round(cov, 3)
                                row["prof_gate_usable"] = cov >= 0.2
                                cpu_pct = (100.0 - byp.get("DmlExecutionProvider", 0)
                                           / ptu * 100) if ptu else None
                                row["cpu_pct"] = round(cpu_pct, 3) if cpu_pct is not None else None
                                if cov < 0.2:
                                    # 注意: 这是工具限制不是数据错误, 记 note 不记 err
                                    # (R1: err 非空即失败); 落点结论由 landing 模式给
                                    row["note"] = (
                                        f"R4: profile 覆盖率 {cov:.1%} <20%, "
                                        f"ORT 度量不到 DML GPU 执行时间(工具限制), "
                                        f"本行时间口径不可用, 落点改由 landing 判")
                                elif cpu_pct is not None and cpu_pct > 5:
                                    row["ok"] = False
                                    row["err"] = (row["err"] +
                                                  f" | B5: CPU 时间占比 "
                                                  f"{cpu_pct:.1f}% > 5%").strip(" |")
                                # 归档 profile 原始文件(R21: 不再删)
                                for pf_path in row["profiles"]:
                                    try:
                                        dst = os.path.join(
                                            REPRO,
                                            os.path.basename(pf_path))
                                        shutil.copy2(pf_path, dst)
                                    except Exception:
                                        pass
                except Exception as e:
                    row["err"] = f"{type(e).__name__}: {str(e)[:600]}"
                # R1: err 非空即失败(成功行不得带错误)
                if row.get("err"):
                    row["ok"] = False
                emit(row, hashes)
                print(f"  {cell:<32} total={row['seconds_total'] or 0:6.2f}s "
                      f"gen={row['seconds_gen'] or 0:6.2f}s "
                      f"load={row['seconds_load'] or 0:6.2f}s "
                      f"{'OK' if row['ok'] else 'FAIL:' + str(row['err'])[:70]}",
                      flush=True)

    OUT["offline_window"]["end"] = now_ts()
    save()
    assert_frozen(*hashes, "final")

    by_cell = {}
    for r in OUT["rows"]:
        if r.get("mode") in ("timing", "profiling"):
            by_cell.setdefault(r.get("cell"), []).append(r)
    bad = {c: rs for c, rs in by_cell.items() if not any(x.get("ok") for x in rs)}
    verdict = []
    if bad:
        verdict.append(f"cells_not_ok={len(bad)}")
    # R13: 每个 (p,seed) 组必须有 >= requested_n 个成功行,且成功行不得带 err
    groups = {}
    for r in OUT["rows"]:
        if r.get("mode") != "timing":
            continue
        groups.setdefault((r.get("prompt_idx"), r.get("seed")), []).append(r)
    need = OUT.get("requested_n") or a.n
    for k, rs in sorted(groups.items()):
        okn = len([x for x in rs if x.get("ok") and not x.get("err")])
        if okn < need:
            verdict.append(f"p{k[0]}_s{k[1]}_ok={okn}<{need}")
    if a.mode == "profiling":
        for r in OUT["rows"]:
            if r.get("mode") == "profiling" and r.get("ok") and r.get("err"):
                verdict.append(f"profiling_row_with_err={r.get('cell')}")
    OUT["verdict"] = "pass" if not verdict else "fail: " + "; ".join(verdict)
    save()
    print(f"未通过 cell: {len(bad)}/{len(by_cell)}", flush=True)
    if verdict:
        print(f"RESULT FAIL ({OUT['verdict']})", flush=True)
        sys.exit(1)
    print("RESULT PASS", flush=True)


if __name__ == "__main__":
    main()
