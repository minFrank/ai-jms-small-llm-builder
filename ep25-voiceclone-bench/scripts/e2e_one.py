#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ep25 真预飞：CosyVoice3 端到端一次。用 VoiceStudio 的解释器跑。"""
import os, sys, io, json, time, wave, contextlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REF_WAV = r"D:/study/ai-jms/voice_samples/ref_new_16k.wav"
REF_TXT = r"D:/study/ai-jms/voice_samples/frank-ref-text-new.txt"
OUT_DIR = r"D:/study/ai-jms/voice_samples/ep25_run/preflight_e2e"
URL     = "http://127.0.0.1:3900/generate"
TEXT    = "关注 AI 积木师，带你从 AI 的视角解读和理解生活"

os.makedirs(OUT_DIR, exist_ok=True)
ref_text = open(REF_TXT, encoding="utf-8").read().strip()
print("参考文本:", ref_text)
print("输入文本:", TEXT)

import requests  # VoiceStudio venv 自带

def one(engine, out_name):
    outp = os.path.join(OUT_DIR, out_name)
    if os.path.exists(outp):
        os.remove(outp)
    t0 = time.perf_counter()
    try:
        with open(REF_WAV, "rb") as f:
            files = {"ref_audio": (os.path.basename(REF_WAV), f, "audio/wav")}
            data = {
                "text": TEXT, "language": "zh", "ref_text": ref_text,
                "engine": engine, "seed": 1234, "stream": "false",
                "num_step": "16", "denoise": "true",
            }
            r = requests.post(URL, files=files, data=data, timeout=900)
        wall = time.perf_counter() - t0
        ct = r.headers.get("Content-Type", "")
        print("\n[%s] HTTP %d  %.2fs  Content-Type=%s  %d 字节"
              % (engine, r.status_code, wall, ct, len(r.content)))
        if r.status_code != 200:
            print("   响应:", r.content[:400].decode("utf-8", "replace"))
            return None
        if r.content[:4] == b"RIFF":
            with open(outp, "wb") as f:
                f.write(r.content)
        else:
            try:
                d = r.json()
                print("   JSON 响应键:", list(d.keys())[:12])
                p = d.get("audio_path") or d.get("path") or d.get("saved_path")
                if p and os.path.exists(p):
                    import shutil; shutil.copyfile(p, outp)
                else:
                    print("   无音频路径:", str(d)[:300])
                    return None
            except Exception as e:
                print("   非 RIFF 非 JSON:", e, r.content[:200])
                return None
        # 校验
        import soundfile as sf
        data_, sr_ = sf.read(outp, dtype="float32")
        dur = len(data_) / float(sr_)
        rms = float((data_ ** 2).mean()) ** 0.5
        rtf = wall / dur if dur > 0 else None
        print("   ✅ 校验通过: %s  %d 字节 / %.2fs / %d Hz / RMS=%.4f / RTF=%.2f"
              % (os.path.basename(outp), os.path.getsize(outp), dur, sr_, rms, rtf))
        return {"engine": engine, "path": outp, "wall_s": round(wall, 3),
                "audio_s": round(dur, 3), "sr": sr_, "rms": round(rms, 5),
                "rtf": round(rtf, 3), "bytes": os.path.getsize(outp)}
    except Exception as e:
        print("[%s] 失败: %r" % (engine, e))
        return None

res = []
for eng in ("cosyvoice", "omnivoice"):
    print("\n" + "=" * 70)
    r = one(eng, "preflight_%s.wav" % eng)
    if r: res.append(r)

outp = os.path.join(OUT_DIR, "e2e_results.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "results": res},
              f, ensure_ascii=False, indent=1)
print("\n" + "=" * 70)
print("跑通 %d 个引擎" % len(res))
print("落盘:", outp)
