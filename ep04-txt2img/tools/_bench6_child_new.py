CHILD_CODE = r'''
import json, os, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# R2: 计时起点放在第一条 import 之前(含解释器启动后的全部开销)
t0 = time.time()

import numpy as np
import onnxruntime as ort

t_imp = time.time()
A = json.loads(sys.argv[1])

opts = ort.SessionOptions()
# R4: log_severity_level=0 才能收到 ORT 的静默回退 warning(原 3 会压掉)
opts.log_severity_level = 0
prov = ["DmlExecutionProvider", "CPUExecutionProvider"]
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
