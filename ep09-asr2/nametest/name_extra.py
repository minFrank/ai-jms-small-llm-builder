"""专名专项:Fun-ASR-Nano + FireRedASR2-AED 跑 8 句 TTS 专名句。

与 03 期同口径:refs.json 给 GT、cer()/normalize 复用 ep03_asr_bench、
禁联网 guard、每引擎独立进程内顺序跑(两模型不共存)。
用法: python name_extra.py --engine funasr|firered
"""
import argparse
import importlib.util
import json
import os
import socket
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 禁联网(与 bench_extra 同款)----
_orig_connect = socket.socket.connect
_BLOCKED = []
_PROXY_PORTS = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888}


def _guarded(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host, port = str(address[0]), int(address[1])
    else:
        host, port = str(address), 0
    if host not in ("127.0.0.1", "::1", "localhost"):
        _BLOCKED.append(f"{host}:{port}")
        raise OSError(f"[offline-guard] blocked {host}:{port}")
    if port in _PROXY_PORTS:
        _BLOCKED.append(f"{host}:{port} (proxy)")
        raise OSError(f"[offline-guard] blocked proxy {host}:{port}")
    return _orig_connect(self, address, *a, **k)


socket.socket.connect = _guarded
try:
    socket.create_connection(("1.1.1.1", 80), timeout=3)
    _BLOCKED.append("direct=LEAKED")
except OSError:
    pass
_BLOCKED.clear()

EP03 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep03-asr"
NT = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/nametest"
_spec = importlib.util.spec_from_file_location("b03", os.path.join(EP03, "ep03_asr_bench.py"))
_b03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b03)
cer_fn, normalize = _b03.cer, _b03.normalize

REFS = json.load(open(os.path.join(NT, "samples", "refs.json"), encoding="utf-8"))
FILES = sorted(f for f in os.listdir(os.path.join(NT, "samples")) if f.endswith(".wav"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["funasr", "firered"], required=True)
    a = ap.parse_args()

    t0 = time.time()
    if a.engine == "funasr":
        from funasr import AutoModel
        model = AutoModel(model=r"D:/models/asr/Fun-ASR-Nano-2512",
                          vad_model=None, vad_kwargs=None, disable_update=True,
                          device="cpu", quantize=False)
        tag = "Fun-ASR-Nano"
    else:
        sys.path.insert(0, r"D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/FireRedASR2S/fireredasr2s")
        from fireredasr2.asr import FireRedAsr2, FireRedAsr2Config
        cfg = FireRedAsr2Config(use_gpu=False, use_half=False, beam_size=3, nbest=1,
                                decode_max_len=2048, softmax_smoothing=1.25,
                                aed_length_penalty=0.6, eos_penalty=1.0,
                                return_timestamp=False)
        model = FireRedAsr2.from_pretrained("aed", r"D:/models/asr/FireRedASR2-AED", cfg)
        tag = "FireRedASR2-AED"
    load_s = time.time() - t0
    print(f"[{tag}] load {load_s:.1f}s", flush=True)

    rows = []
    for f in FILES:
        wav = os.path.join(NT, "samples", f)
        t1 = time.time()
        if a.engine == "funasr":
            res = model.generate(input=wav)
        else:
            res = model.transcribe([os.path.splitext(f)[0]], [wav])
        dt = time.time() - t1
        txt = ""
        if isinstance(res, list) and res:
            r0 = res[0]
            txt = str(r0.get("text", "")) if isinstance(r0, dict) else str(r0)
        txt = txt.strip()
        ref = REFS[f]
        c = cer_fn(ref, txt)
        rows.append({"sample": f, "ref": ref, "text": txt, "cer": round(c, 4),
                     "dur": round(len(txt) and 0 or 0, 2), "infer_s": round(dt, 2)})
        print(f"  {f}  CER {c*100:5.2f}%  {dt:4.2f}s  ->  {txt}", flush=True)

    out = {"engine": a.engine, "model": tag, "load_s": round(load_s, 1),
           "rows": rows, "net_blocked": sorted(set(_BLOCKED)),
           "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    p = os.path.join(NT, f"result_{a.engine}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cers = [r["cer"] for r in rows]
    print(f"\n[{tag}] CER avg {sum(cers)/len(cers)*100:.2f}% | net {len(_BLOCKED)} | {p}")


if __name__ == "__main__":
    main()
