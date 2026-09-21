"""ep03_asr_bench.py —— 03 期《把录音转成文字》实测 harness

跑法：3 个本地 ASR 模型 × 15 组样本，量四件事（对应用户定的四样数据）：
  ① 速度：墙钟耗时 + 实时倍速（audio_seconds / wall_seconds）
  ② 资源：进程峰值内存（psutil 可用则用，否则跳过）
  ③ 质量：CER（字符错误率，对标 manifest 里的 ground truth）
  ④ 门槛：模型体积（脚本另外量）+ 是否需要显卡（本机无显卡，天然覆盖）

模型（全部开源免费、CPU 可跑）：
  sensevoice  sherpa-onnx SenseVoice-Small（多语种，中文强）
  paraformer  sherpa-onnx Paraformer-zh（中文专精）
  whisper     sherpa-onnx Whisper-small（ONNX）
  fw          faster-whisper small（CTranslate2，另一套运行时做对照）

用法：python ep03_asr_bench.py [--models sensevoice,paraformer,whisper,fw] [--limit N]
输出：result.json（逐条明细）+ 终端表格（可直接抄进文章）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import wave
from pathlib import Path

ASR_DIR = Path("D:/models/asr")
SAMPLES = Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/ep03/samples")
OUT = Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/ep03")
MAN = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
TXT = {"A": MAN["TXT_A"], "B": MAN["TXT_B"], "C": MAN["TXT_B"] * 37}

try:
    import psutil
except Exception:          # 没有就跳过内存项，不阻断
    psutil = None


def load_wav(p: Path):
    """读 16k 单声道 PCM 为 float32（sherpa-onnx 1.13.8 的 OfflineStream 没有 accept_wave_file，
    要用 accept_waveform(sample_rate, samples)）。"""
    import numpy as np
    with wave.open(str(p), "rb") as w:
        assert w.getframerate() == 16000, f"采样率不是 16k: {w.getframerate()}"
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype("float32") / 32768.0


def audio_seconds(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def normalize(s: str) -> str:
    """CER 前归一：去标点/空白，中文全角转半角字母数字，英文小写。"""
    s = s.lower()
    s = re.sub(r"[\s，。、；：！？,.;:!?\"'“”‘’（）()\[\]【】\-—…·]", "", s)
    return s


def cer(ref: str, hyp: str) -> float:
    """字符错误率（Levenshtein 距离 / 参考长度）。"""
    r, h = normalize(ref), normalize(hyp)
    if not r:
        return 0.0
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / len(r)


def find(d: Path, *pats):
    for pat in pats:
        hits = sorted(d.rglob(pat))
        if hits:
            return hits[0]
    return None


def build(model_key: str):
    """返回 (callable(audio_path) -> text, 模型体积MB, 说明)。"""
    import sherpa_onnx
    if model_key == "sensevoice":
        d = ASR_DIR / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
        m, tok = find(d, "model.int8.onnx", "model.onnx"), find(d, "*tokens.txt")
        print(f"   模型文件: {m.name}")
        rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(m), tokens=str(tok), use_itn=True, language="zh", num_threads=8)
    elif model_key == "paraformer":
        d = ASR_DIR / "sherpa-onnx-paraformer-zh-2023-09-14"
        m, tok = find(d, "model.int8.onnx", "model.onnx"), find(d, "*tokens.txt")
        rec = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=str(m), tokens=str(tok), num_threads=8)
    elif model_key == "whisper":
        d = ASR_DIR / "sherpa-onnx-whisper-small"
        # 显式配对：编码器与解码器必须同档（都 int8 或都 fp32），不能混搭
        enc_i, dec_i = find(d, "*encoder*int8*.onnx"), find(d, "*decoder*int8*.onnx")
        if enc_i and dec_i:
            enc, dec = enc_i, dec_i
        else:
            enc, dec = find(d, "*encoder*.onnx"), find(d, "*decoder*.onnx")
        tok = find(d, "*tokens.txt")
        m = enc                     # 体积统计用的是这个（此前漏了这行 → whisper 初始化报未赋值）
        print(f"   whisper 配对: {enc.name} + {dec.name}")
        rec = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(enc), decoder=str(dec), tokens=str(tok), language="zh", num_threads=8)
    elif model_key == "fw":
        from faster_whisper import WhisperModel
        wm = WhisperModel(str(ASR_DIR / "faster-whisper-small"), device="cpu", compute_type="int8",
                          cpu_threads=8)
        size = sum(f.stat().st_size for f in (ASR_DIR / "faster-whisper-small").rglob("*") if f.is_file()) / 1e6
        return (lambda p: "".join(s.text for s in wm.transcribe(str(p), language="zh", beam_size=1)[0])), size / 1e6, "faster-whisper small (CT2, int8)"
    else:
        raise SystemExit(f"未知模型 {model_key}")

    pack_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1e6
    used_mb = m.stat().st_size / 1e6            # 实际加载的那个文件
    size = used_mb
    globals()["_pack_mb"] = round(pack_mb, 1)

    def run(path: Path) -> str:
        s = rec.create_stream()
        s.accept_waveform(16000, load_wav(path))
        rec.decode_stream(s)
        return s.result.text
    return run, size, model_key


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="sensevoice,paraformer,whisper,fw")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 组（快速冒烟）")
    a = ap.parse_args()

    samples = sorted(SAMPLES.glob("*.wav"))
    samples = [s for s in samples if not s.name.startswith("srcC")]
    if a.limit:
        samples = samples[:a.limit]

    rows = []
    for key in [m.strip() for m in a.models.split(",") if m.strip()]:
        try:
            run, size_mb, desc = build(key)
            _pack = globals().get("_pack_mb", None)
        except Exception as exc:
            print(f"❌ {key} 初始化失败: {str(exc)[:160]}")
            rows.append({"model": key, "error": str(exc)[:200]})
            continue
        print(f"\n══ {key}（部署文件 {size_mb:.0f} MB / 整包 {globals().get('_pack_mb')} MB）{desc}")
        for sp in samples:
            tag = sp.name.split("_")[0]
            secs = audio_seconds(sp)
            proc = psutil.Process() if psutil else None
            t0 = time.time()
            try:
                text = run(sp)
                err = ""
            except Exception as exc:
                text, err = "", str(exc)[:160]
            wall = time.time() - t0
            peak = (proc.memory_info().rss / 1e6) if proc else None
            c = cer(TXT[tag], text) if text else None
            rows.append({"model": key, "size_mb": round(size_mb, 1), "pack_mb": _pack, "sample": sp.name, "audio_s": round(secs, 1),
                         "wall_s": round(wall, 2), "rtf_x": round(secs / wall, 2) if wall else None,
                         "peak_rss_mb": round(peak, 1) if peak else None,
                         "cer": round(c, 4) if c is not None else None,
                         "text": text[:400], "error": err})
            print(f"   {sp.name:24s} {secs:7.1f}s → {wall:7.2f}s（{secs/wall:5.2f}×） "
                  f"CER {'—' if c is None else f'{c*100:5.2f}%'} {err[:60]}")

    # 不要覆盖：按 (model, sample) 合并进 result.json
    # （踩过：补跑单个模型时把整份结果冲掉了，前几个模型的原始文本全丢）
    dest = OUT / "result.json"
    merged = {}
    if dest.exists():
        try:
            for r in json.loads(dest.read_text(encoding="utf-8")):
                merged[(r.get("model"), r.get("sample"))] = r
        except Exception:
            pass
    for r in rows:
        merged[(r.get("model"), r.get("sample"))] = r
    dest.write_text(json.dumps(list(merged.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n明细：{dest}（累计 {len(merged)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
