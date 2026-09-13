#!/usr/bin/env python
"""把一段文字,用你自己的声音念出来。

用法(通常不用手敲,由「一键生成.bat」调用):
    python tools/tts.py --text-file story.txt --voice 我的录音.wav \
        --voice-text "我录音里念的那句话" --out output/故事.mp3

为什么要有这个文件:CosyVoice 官方的用法对普通人偏难(要自己管模型精度、自己拼多段),
这里把两个必踩的坑都修好了 —— 详见文件末尾注释。
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)


def find_cosy_root() -> str:
    """按优先级找 CosyVoice 的安装位置:环境变量 > 包内 tools/CosyVoice > 本机常见位置。"""
    cands = [
        os.environ.get("COSYVOICE_ROOT", ""),
        os.path.join(HERE, "CosyVoice"),
        os.path.expanduser("~/AppData/Roaming/OmniVoice/engines/cosyvoice/CosyVoice"),
        os.path.expanduser("~/OmniVoice/engines/cosyvoice/CosyVoice"),
        "/opt/CosyVoice",
    ]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "cosyvoice")):
            return c
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True, help="要念的文字(story.txt)")
    ap.add_argument("--voice", required=True, help="你的录音(16k 单声道 wav)")
    ap.add_argument("--voice-text", help="录音里你实际念的那句话(直接用 --voice-text-file 更方便)")
    ap.add_argument("--voice-text-file", help="把上面那句话存成文本文件,传文件路径 —— 推荐,免去命令行转义/编码问题")
    ap.add_argument("--out", required=True, help="输出文件(建议 .mp3)")
    ap.add_argument("--model-dir", default="pretrained_models/Fun-CosyVoice3-0.5B")
    a = ap.parse_args()

    # --voice-text-file 优先:从文件读参考文本。
    # 为什么不靠 bat 传 --voice-text:实测在 chcp 65001 的 bat 里,
    # 中文变量展开会把命令行搞坏(python 报 "the following arguments are required: --out"),
    # 让 python 自己读文件最稳。
    if a.voice_text_file:
        vt_path = os.path.abspath(a.voice_text_file)
        if not os.path.exists(vt_path):
            print(f"× 找不到录音文本文件:{vt_path}")
            return 2
        with open(vt_path, encoding="utf-8-sig") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    a.voice_text = ln
                    break
        if a.voice_text:
            print(f"· 录音文本(读自文件):{a.voice_text[:40]}")
    if not a.voice_text:
        print("× 缺少录音文本:用 --voice-text-file 指定文本文件,或用 --voice-text 直接给")
        return 2

    root = find_cosy_root()
    if not root:
        print("× 没找到 CosyVoice。请先双击「一键安装.bat」,或设置环境变量 COSYVOICE_ROOT。")
        return 2
    if not os.path.exists(a.voice):
        print(f"× 找不到你的录音:{a.voice}")
        return 2
    # 必须在 chdir 之前把路径转成绝对:
    # 下面会切到模型目录去加载引擎,之后相对路径会指向模型目录 ——
    # 实测报错 LibsndfileError: Error opening '...\CosyVoice\我的录音.wav': System error.
    text_abs = os.path.abspath(a.text_file)
    voice_abs = os.path.abspath(a.voice)
    out_abs = os.path.abspath(a.out)

    text = open(text_abs, encoding="utf-8").read().strip()
    if not text:
        print(f"× {a.text_file} 是空的,先写点内容。")
        return 2
    if not os.path.exists(voice_abs):
        print(f"× 找不到录音文件:{voice_abs}")
        return 2
    print(f"· 使用模型目录:{root}")
    print(f"· 用你的录音:{os.path.basename(voice_abs)}")
    print(f"· 要念 {len(text)} 个字")

    os.chdir(root)
    sys.path.insert(0, "third_party/Matcha-TTS")
    sys.path.insert(0, ".")

    import torch.nn as nn          # noqa: E402
    from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402
    import torchaudio              # noqa: E402

    t0 = time.time()
    print("· 正在加载模型(第一次会慢,后面就快了)…")
    m = AutoModel(model_dir=a.model_dir)
    print(f"· 模型加载完成,用了 {time.time()-t0:.0f} 秒")

    # 坑 1:CPU 上必须把权重转成 float32,否则报 dtype 不匹配
    for _n, sub in vars(m.model).items():
        if isinstance(sub, nn.Module):
            sub.float()

    # 坑 2:参考文本必须带这个前缀,缺了引擎会崩
    vt = a.voice_text
    if "<|endofprompt|>" not in vt:
        vt = "You are a helpful assistant.<|endofprompt|>" + vt

    out = out_abs
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wav = os.path.splitext(out)[0] + ".wav"

    t1 = time.time()
    segs = list(m.inference_zero_shot(text, vt, voice_abs, stream=False))
    if not segs:
        print("× 引擎没有返回音频")
        return 3

    # 坑 3(最容易中招):长文本会被引擎切成多段,必须**全部拼接**。
    # 只取第一段的话,一段 380 字的故事成品只有 15 秒 —— 我就是这么踩的。
    parts = []
    for j, seg in enumerate(segs):
        p = wav if j == 0 else wav.replace(".wav", f"_{j}.wav")
        torchaudio.save(p, seg["tts_speech"], m.sample_rate)
        parts.append(p)
    print(f"· 引擎切成 {len(parts)} 段,正在拼接…")
    if len(parts) > 1:
        lst = wav.replace(".wav", "_list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for pp in parts:
                f.write(f"file '{pp}'\n")
        merged = wav.replace(".wav", "_merged.wav")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", merged], check=True, capture_output=True)
        for pp in parts:
            try:
                os.remove(pp)
            except OSError:
                pass
        os.replace(merged, wav)
        try:
            os.remove(lst)
        except OSError:
            pass

    if out.lower().endswith(".mp3"):
        subprocess.run(["ffmpeg", "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "192k", out],
                       check=True, capture_output=True)
        try:
            os.remove(wav)
        except OSError:
            pass

    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", out], capture_output=True, text=True)
    secs = float((dur.stdout or "0").strip() or 0)
    print("")
    print(f"√ 完成!生成音频 {secs:.1f} 秒,用时 {time.time()-t1:.0f} 秒")
    print(f"  文件:{out}")
    print(f"  (生成本身的耗时大约是音频时长的 6 倍,这是纯 CPU 的正常速度)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
