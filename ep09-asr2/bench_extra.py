"""ep09 新增两引擎的对比跑测:FunASR(Fun-ASR-Nano-2512)与 FireRedASR2-AED。

- CER 用 03 期同一套 normalize/cer(import ep03_asr_bench),保证口径可比
- 每个引擎独立进程跑(内存基线干净)
- 全程禁联网(非回环拦、代理端口 7897 等也拦)
- 输出 JSON:逐样本 text/cer/rtf + 引擎级 load/peak/平均

用法:
  bench_extra.py --engine funasr   --out ep09-asr2/extra_funasr.json
  bench_extra.py --engine firered  --out ep09-asr2/extra_firered.json
"""
import argparse
import importlib.util
import json
import os
import socket
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 禁联网(数据不上传硬验证)----
_orig_connect = socket.socket.connect
_BLOCKED = []
_PROXY_PORTS = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888}


def _guarded(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host, port = str(address[0]), int(address[1])
    else:
        host, port = str(address), 0
    is_loop = host in ("127.0.0.1", "::1", "localhost")
    if not is_loop:
        _BLOCKED.append(f"{host}:{port}")
        raise OSError(f"[offline-guard] blocked outbound -> {host}:{port}")
    if port in _PROXY_PORTS:
        _BLOCKED.append(f"{host}:{port} (proxy)")
        raise OSError(f"[offline-guard] blocked proxy egress -> {host}:{port}")
    return _orig_connect(self, address, *a, **k)


socket.socket.connect = _guarded

# 自检(直连 + 走代理),确认 hook 真的生效;结果不计入 _BLOCKED
_selftest = []
try:
    try:
        socket.create_connection(("1.1.1.1", 80), timeout=3)
        _selftest.append("direct=LEAKED")
    except OSError:
        _selftest.append("direct=BLOCKED")
    import requests

    try:
        requests.get("http://example.com", timeout=5)
        _selftest.append("requests/proxy=LEAKED")
    except OSError:
        _selftest.append("requests/proxy=BLOCKED")
except Exception as _e:
    _selftest.append(f"selftest={type(_e).__name__}")
SELFTEST = " | ".join(_selftest)
_BLOCKED.clear()

import psutil  # noqa: E402

EP03 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep03-asr"
SAMPLES = os.path.join(EP03, "samples")
PKG_ROOT = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/FireRedASR2S"

# 复用 03 期同口径的归一化与 CER(带 __main__ 保护,可安全 import)
_spec = importlib.util.spec_from_file_location(
    "ep03_asr_bench", os.path.join(EP03, "ep03_asr_bench.py"))
_b03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b03)
cer_fn, normalize_fn = _b03.cer, _b03.normalize
TXT = _b03.TXT

PROC = psutil.Process()


def gt_for(name: str) -> str:
    if name.startswith("A_"):
        return TXT["A"]
    if name.startswith("C_"):
        return TXT["C"]          # TXT_B × 37(10 分钟长音频)
    return TXT["B"]


def samples(d=SAMPLES):
    """只收 A_/B_/C_ 前缀 —— C 目录里还有 srcC_long.wav 这类源文件,
    没有对应 GT,跑了会把平均 CER 拉爆(2026-10-02 实测:16 个里有 1 个是源)。"""
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".wav") and f[:2] in ("A_", "B_", "C_"):
            out.append(os.path.join(d, f))
    return out


def run_funasr():
    from funasr import AutoModel

    t0 = time.time()
    # 2026-10-02 实测:A/B(≤17s)可以不开 VAD;但 C 类 628s 不开 VAD 只出 1~3 字
    # (CER 100%),必须开。1.4.16 开 VAD 后首次 inference 会 KeyError 'prev_samples',
    # 用空数组预置 cache 绕开(FSMN-VAD 的流式缓存初值)。
    # 2026-10-02 23:09 实测:vad_model 传模型名 "fsmn-vad" 时,即使本地已有缓存,
    # modelscope 也会先查 hub 的 revision,在禁联网 guard 下会 retry 5 次后卡死
    # (进程 6 分钟 CPU 仅 0.12s)。改成传已缓存的本地目录 → 彻底不联网。
    _vad = os.environ.get("FUNASR_VAD", "1") == "1"
    _VAD_LOCAL = (r"C:/Users/Frank/.cache/modelscope/models"
                  r"/iic--speech_fsmn_vad_zh-cn-16k-common-pytorch/snapshots/master")
    model = AutoModel(
        model=r"D:/models/asr/Fun-ASR-Nano-2512",
        device="cpu",
        disable_update=True,
        vad_model=_VAD_LOCAL if _vad else None,
        vad_kwargs={"max_single_segment_time": 30000} if _vad else {},
    )
    load_s = time.time() - t0

    import torch

    def one(wav):
        t0 = time.time()
        # 预置 prev_samples 绕开 1.4.16 的 KeyError('prev_samples')。
        # ⚠ 必须是 torch.Tensor —— 传 numpy 会报
        #   TypeError: expected Tensor as element 0 in arg (2026-10-02 实测,
        #   当时 15 个样本全部 0 字)。
        res = model.generate(
            input=wav,
            cache={"language": "auto", "prev_samples": torch.zeros(0)},
            language="auto", use_itn=False, batch_size_s=60)
        dt = time.time() - t0
        txt = ""
        if isinstance(res, list):
            txt = "".join(str(r.get("text", "")) for r in res if isinstance(r, dict))
        else:
            txt = str(res or "")
        return txt.strip(), dt
    return model, load_s, one


def run_firered():
    sys.path.insert(0, os.path.join(PKG_ROOT, "fireredasr2s"))
    from fireredasr2.asr import FireRedAsr2, FireRedAsr2Config

    cfg = FireRedAsr2Config(
        use_gpu=False, use_half=False, beam_size=3, nbest=1,
        # 03 期官方示例给 300,A/B(20~50 字)够用;C 类 GT 是 1000+ 字,
        # 300 会截断 → 这里放 2048(上游默认 0=不限,但无上限在 CPU 上有跑飞风险)
        decode_max_len=int(os.environ.get("FR_DECODE_MAX_LEN", "2048")),
        softmax_smoothing=1.25, aed_length_penalty=0.6,
        eos_penalty=1.0, return_timestamp=False)
    t0 = time.time()
    asr = FireRedAsr2.from_pretrained("aed", r"D:/models/asr/FireRedASR2-AED", cfg)
    load_s = time.time() - t0

    def one(wav):
        t0 = time.time()
        res = asr.transcribe([os.path.splitext(os.path.basename(wav))[0]], [wav])
        dt = time.time() - t0
        txt = ""
        if isinstance(res, list) and res:
            r0 = res[0]
            txt = str(r0.get("text", "")) if isinstance(r0, dict) else str(r0)
        return txt.strip(), dt
    return asr, load_s, one


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, choices=["funasr", "firered"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples-dir", default=SAMPLES,
                    help="C 类长音频在 workspace 下的 ep03/samples")
    a = ap.parse_args()

    base_rss = PROC.memory_info().rss
    print(f"engine: {a.engine} | base {base_rss/1024/1024:.0f} MB", flush=True)

    _, load_s, one = run_funasr() if a.engine == "funasr" else run_firered()
    rss_load = PROC.memory_info().rss
    print(f"load  : {load_s:.2f}s | RSS {rss_load/1024/1024:.0f} MB", flush=True)

    rows = []
    peak_rss = rss_load
    for wav in samples(a.samples_dir):
        name = os.path.basename(wav)
        ref = gt_for(name)
        try:
            text, dt = one(wav)
            err = ""
        except Exception as e:
            text, dt, err = "", 0.0, f"{type(e).__name__}: {e}"
        import soundfile as sf

        dur = sf.info(wav).duration
        c = cer_fn(ref, text) if text else None
        peak_rss = max(peak_rss, PROC.memory_info().rss)
        rows.append({
            "sample": name, "text": text, "chars": len(text),
            "dur": round(dur, 2), "infer_s": round(dt, 2),
            "rtf": round(dt / dur, 3) if dur else None,
            "cer": round(c, 4) if c is not None else None,
            "err": err,
        })
        print(f"  {name:<18} {len(text):>4}字  rtf {dt/dur:5.2f}  "
              f"cer {('—' if c is None else f'{c*100:5.2f}%')}  {err[:50]}",
              flush=True)

    cers = [r["cer"] for r in rows if r["cer"] is not None]
    rtfs = [r["rtf"] for r in rows if r["rtf"]]
    out = {
        "engine": a.engine,
        "model": ("Fun-ASR-Nano-2512 (800M)" if a.engine == "funasr"
                  else "FireRedASR2-AED (1.15B)"),
        "load_s": round(load_s, 2),
        "rss_after_load_mb": round(rss_load / 1024 / 1024),
        "peak_rss_mb": round(peak_rss / 1024 / 1024),
        "net_blocked": sorted(set(_BLOCKED)),
        "guard_selftest": SELFTEST,
        "cer_avg": round(sum(cers) / len(cers), 4) if cers else None,
        "rtf_avg": round(sum(rtfs) / len(rtfs), 3) if rtfs else None,
        "rtf_max": round(max(rtfs), 3) if rtfs else None,
        "rows": rows,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print()
    print(f"CER avg {out['cer_avg']} | RTF avg {out['rtf_avg']} max {out['rtf_max']}")
    print(f"peak {out['peak_rss_mb']} MB | net {len(_BLOCKED)} | guard {SELFTEST}")
    print(f"written -> {a.out}")


if __name__ == "__main__":
    main()
