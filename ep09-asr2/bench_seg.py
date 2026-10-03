"""FireRedASR2-AED 长音频分段跑测(C 类)。

为什么需要:直接喂 628s 输出 0 字(实测 rtf 0.12、text 空)。
03 期其它引擎靠自带 VAD / 30s 截断处理长音频;这里用手动切 30s 段 +
逐段转写 + 拼接,并已单独验证分段可出字(见 seg_test.log)。

用法:
  bench_seg.py --engine firered --samples-dir <dir> --only C_1_clean.wav,C_3_noise.wav
输出:与 bench_extra.py 同结构的 JSON,便于合并。
"""
import argparse
import importlib.util
import json
import os
import socket
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 禁联网(与 bench_extra 同款判据)----
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
PKG_ROOT = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/FireRedASR2S"

_spec = importlib.util.spec_from_file_location(
    "ep03_asr_bench", os.path.join(EP03, "ep03_asr_bench.py"))
_b03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b03)
TXT = _b03.TXT
cer_fn = _b03.cer

PROC = psutil.Process()


def gt_for(name):
    if name.startswith("A_"):
        return TXT["A"]
    if name.startswith("C_"):
        return TXT["C"]
    return TXT["B"]


def load_audio(path):
    import soundfile as sf

    data, sr = sf.read(path, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="firered")
    ap.add_argument("--samples-dir", required=True)
    ap.add_argument("--only", default="", help="逗号分隔的样本名过滤")
    ap.add_argument("--seg-sec", type=float, default=30.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    files = [f for f in sorted(os.listdir(a.samples_dir))
             if f.endswith(".wav") and f[:2] in ("A_", "B_", "C_")
             and (not only or f in only)]
    print(f"engine={a.engine} | seg={a.seg_sec}s | {len(files)} 样本", flush=True)

    base_rss = PROC.memory_info().rss
    t0 = time.time()
    if a.engine == "funasr":
        # FunASR Nano:分段跑,长音频直接喂会只出 1 字(03 期/C 类实测);
        # vad_model 必须 None —— 传 fsmn-vad 会查 hub revision,禁联网下卡死。
        from funasr import AutoModel
        asr = AutoModel(
            model=r"D:/models/asr/Fun-ASR-Nano-2512",
            vad_model=None, vad_kwargs=None, disable_update=True,
            device="cpu", quantize=False)
        model_name = "Fun-ASR-Nano-2512 (0.6B底座) + 手动分段"
    else:
        sys.path.insert(0, os.path.join(PKG_ROOT, "fireredasr2s"))
        from fireredasr2.asr import FireRedAsr2, FireRedAsr2Config
        cfg = FireRedAsr2Config(
            use_gpu=False, use_half=False, beam_size=3, nbest=1,
            decode_max_len=2048, softmax_smoothing=1.25, aed_length_penalty=0.6,
            eos_penalty=1.0, return_timestamp=False)
        asr = FireRedAsr2.from_pretrained(
            "aed", r"D:/models/asr/FireRedASR2-AED", cfg)
        model_name = "FireRedASR2-AED (1.15B) + 手动分段"
    load_s = time.time() - t0
    rss_load = PROC.memory_info().rss
    print(f"load {load_s:.1f}s | RSS {rss_load/1024/1024:.0f} MB", flush=True)

    seg_dir = os.path.join(a.out + ".seg_tmp")
    os.makedirs(seg_dir, exist_ok=True)
    import soundfile as sf

    rows = []
    peak_rss = rss_load
    for fname in files:
        path = os.path.join(a.samples_dir, fname)
        data, sr = load_audio(path)
        dur = len(data) / sr
        n_seg = max(1, int(dur / a.seg_sec) + (1 if dur % a.seg_sec else 0))
        pieces = []
        t0 = time.time()
        for i in range(n_seg):
            s = int(i * a.seg_sec * sr)
            e = int(min((i + 1) * a.seg_sec * sr, len(data)))
            segp = os.path.join(seg_dir, f"{os.path.splitext(fname)[0]}_{i:03d}.wav")
            sf.write(segp, data[s:e], sr)
            if a.engine == "funasr":
                res = asr.generate(input=segp)
            else:
                res = asr.transcribe([f"seg{i:03d}"], [segp])
            txt = ""
            if isinstance(res, list) and res:
                r0 = res[0]
                txt = str(r0.get("text", "")) if isinstance(r0, dict) else str(r0)
            pieces.append(txt.strip())
        dt = time.time() - t0
        text = "".join(pieces)
        ref = gt_for(fname)
        c = cer_fn(ref, text) if text else None
        peak_rss = max(peak_rss, PROC.memory_info().rss)
        rows.append({
            "sample": fname, "text": text, "chars": len(text),
            "dur": round(dur, 2), "infer_s": round(dt, 2),
            "rtf": round(dt / dur, 3) if dur else None,
            "cer": round(c, 4) if c is not None else None,
            "segments": n_seg, "seg_sec": a.seg_sec, "err": "",
        })
        cer_s = "—" if c is None else f"{c*100:.1f}%"
        print(f"  {fname:<22} {n_seg:>3}段 {len(text):>5}字 "
              f"rtf {dt/dur:5.2f} cer {cer_s:>8}", flush=True)
        # 清掉切片,避免占满 C 盘/temp
        for i in range(n_seg):
            segp = os.path.join(seg_dir,
                                f"{os.path.splitext(fname)[0]}_{i:03d}.wav")
            if os.path.exists(segp):
                os.remove(segp)

    cers = [r["cer"] for r in rows if r["cer"] is not None]
    rtfs = [r["rtf"] for r in rows if r["rtf"]]
    out = {
        "engine": a.engine,
        "model": model_name,
        "mode": "segmented",
        "seg_sec": a.seg_sec,
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
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print()
    print(f"CER avg {out['cer_avg']} | RTF avg {out['rtf_avg']}"
          f" | peak {out['peak_rss_mb']}MB | net {len(_BLOCKED)}")
    print(f"written -> {a.out}")


if __name__ == "__main__":
    main()
