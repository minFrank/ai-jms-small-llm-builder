#!/usr/bin/env python
"""把一段文字,用你自己的声音念出来。

用法(通常不用手敲,由「一键生成.bat」调用):
    python tools/tts.py --text-file story.txt --voice 我的录音.wav \
        --voice-text-file 我的录音说的是什么.txt --out output/故事.mp3

设计要点(都是实测踩出来的,别改坏):
  · 分块 + 逐块落盘:长文本按句切成若干块,每块算完立刻写盘并更新进度文件。
    原因:官方写法是「全部算完再返回」,一旦中途断电/被杀/关窗口,
    几小时的算力全部作废,连做到哪都不知道。分块后最坏只损失当前这一块。
  · 断点续跑:重跑时自动跳过已完成的块(--resume 默认开),接着往下算。
  · 流式进度:每块打印「第几块/共几块、该块字数、该块耗时、已生成音频秒数」,
    并写入 logs/tts-progress.json —— 归因用,不留黑箱。
"""
import argparse
import json
import os
import re
import shutil
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



def ensure_16k_wav(voice_path: str, work_dir: str) -> str:
    """把参考录音统一成 16k 单声道 wav，返回可直接喂给模型的文件路径。

    为什么需要（2026-09-19 实测，用包内 venv 跑的）：
      · 手机自带录音机默认存 .m4a。**.m4a 无论改不改名，libsndfile 都读不了**
        （报 LibsndfileError: Format not recognised），而 CosyVoice 正是用它加载参考音频。
      · .mp3 改名成 .wav 反而能读，但采样率是 24000，不是模型要的 16000。
      · 所以「把文件名改成 .wav 就行」是错的 —— 改名不等于转格式。
    这一步用 ffmpeg 转一份临时文件，用户不必懂命令行（自己转最容易转错采样率/声道）。
    """
    try:
        import soundfile as sf
        info = sf.info(voice_path)
        fmt = (getattr(info, "format", "") or "").upper()
        if info.samplerate == 16000 and info.channels == 1 and fmt in ("WAV", "WAVEX"):
            return voice_path
    except Exception:
        pass

    ff = shutil.which("ffmpeg")
    if not ff:
        print("× 录音需要转成 16k 单声道 wav，但没找到 ffmpeg —— 请先双击「一键安装.bat」")
        return voice_path
    conv = os.path.join(work_dir, "_voice-16k.wav")
    print(f"· 录音不是 16k 单声道 wav，用 ffmpeg 自动转一次：{os.path.basename(voice_path)} → _voice-16k.wav")
    r = subprocess.run([ff, "-y", "-i", voice_path, "-ar", "16000", "-ac", "1", conv],
                       capture_output=True)
    if r.returncode != 0 or not os.path.exists(conv):
        print("× 转换失败：", (r.stderr or b"").decode("utf-8", "replace")[-300:])
        return voice_path
    return conv


def split_blocks(text: str, max_chars: int):
    """按句号切块,每块不超过 max_chars 字。

    为什么要自己切:引擎内部也会切句,但那是「一次性调用」的内部行为,
    外面看不到、也存不下来。自己切才能一块一落盘、一块一续跑。
    """
    if max_chars <= 0:
        return [text]
    sents = re.split(r"(?<=[。！？!?；;])", text)
    sents = [s.strip() for s in sents if s.strip()]
    blocks, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > max_chars:
            blocks.append(cur)
            cur = s
        else:
            cur += s
    if cur:
        blocks.append(cur)
    if not blocks:
        blocks = [text]
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True, help="要念的文字(story.txt)")
    ap.add_argument("--voice", required=True,
                    help="你的录音：wav / m4a / mp3 都行，不是 16k 单声道 wav 会自动转")
    ap.add_argument("--voice-text", help="录音里你实际念的那句话(直接用 --voice-text-file 更方便)")
    ap.add_argument("--voice-text-file", help="把上面那句话存成文本文件,传文件路径 —— 推荐,免去命令行转义/编码问题")
    ap.add_argument("--out", required=True, help="输出文件(建议 .mp3)")
    ap.add_argument("--model-dir", default="pretrained_models/Fun-CosyVoice3-0.5B")
    ap.add_argument("--block-chars", type=int, default=300,
                    help="每块多少字(默认 300;越小越抗中断,但固定开销更多)")
    ap.add_argument("--no-resume", action="store_true", help="忽略已完成的分块,从头重算")
    ap.add_argument("--stream", action="store_true",
                    help="流式取段(逐段 yield)。实测其开销需要对照,故默认关;分块落盘本身已足够抗中断")
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

    print(f"· 使用模型目录:{root}")
    print(f"· 用你的录音:{os.path.basename(voice_abs)}")
    print(f"· 要念 {len(text)} 个字")

    out = out_abs
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    wav = os.path.splitext(out)[0] + ".wav"

    # 分块工作目录:进度与已完成块都放这里,被杀也不丢
    work = os.path.splitext(out)[0] + "_blocks"
    os.makedirs(work, exist_ok=True)
    seg_dir = os.path.join(work, "segs")
    os.makedirs(seg_dir, exist_ok=True)
    prog_path = os.path.join(work, "progress.json")

    voice_use = ensure_16k_wav(voice_abs, work)

    blocks = split_blocks(text, a.block_chars)
    print(f"· 切成 {len(blocks)} 块(每块约 {a.block_chars} 字);工作目录:{work}")

    done = {}
    if os.path.exists(prog_path) and not a.no_resume:
        try:
            prev = json.loads(open(prog_path, encoding="utf-8").read())
            if prev.get("block_chars") == a.block_chars and prev.get("chars") == len(text):
                done = {int(k): v for k, v in (prev.get("done") or {}).items()}
                if done:
                    print(f"· 发现上次进度:已完成 {len(done)}/{len(blocks)} 块,接着往下算"
                          f"(想从头算加 --no-resume)")
            else:
                print("· 上次进度与当前文本/分块不一致,忽略,从头算")
        except Exception as e:
            print(f"· 进度文件读不了({str(e)[:60]}),从头算")

    def save_prog(state_done, extra=None):
        """每块落盘后立即写进度 —— 被杀也能看出做到哪。"""
        d = {"chars": len(text), "block_chars": a.block_chars, "blocks": len(blocks),
             "stream": bool(a.stream),
             "done": {str(k): v for k, v in state_done.items()},
             "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
        if extra:
            d.update(extra)
        tmp = prog_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, prog_path)

    save_prog(done, {"stage": "starting"})

    os.chdir(root)
    sys.path.insert(0, "third_party/Matcha-TTS")
    sys.path.insert(0, ".")

    import torch.nn as nn          # noqa: E402
    from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402
    import torchaudio              # noqa: E402

    t0 = time.time()
    print("· 正在加载模型(第一次会慢,后面就快了)…", flush=True)
    m = AutoModel(model_dir=a.model_dir)
    load_s = time.time() - t0
    print(f"· 模型加载完成,用了 {load_s:.0f} 秒", flush=True)

    # 坑 1:CPU 上必须把权重转成 float32,否则报 dtype 不匹配
    for _n, sub in vars(m.model).items():
        if isinstance(sub, nn.Module):
            sub.float()

    # 坑 2:参考文本必须带这个前缀,缺了引擎会崩
    vt = a.voice_text
    if "<|endofprompt|>" not in vt:
        vt = "You are a helpful assistant.<|endofprompt|>" + vt

    t1 = time.time()
    parts = []
    total_audio = 0.0
    per_block = []

    for i, blk in enumerate(blocks):
        seg_path = os.path.join(seg_dir, f"block_{i:04d}.wav")
        cached = i in done and os.path.exists(seg_path)

        if cached:
            dur = float(done[i].get("audio_s", 0) or 0)
            per_block.append(done[i])
            parts.append(seg_path)
            total_audio += dur
            print(f"[块 {i+1}/{len(blocks)}] 复用上次结果 {dur:.1f} 秒音频(跳过)", flush=True)
            continue

        bt = time.time()
        n_seg = 0
        sub_parts = []
        for k, seg in enumerate(m.inference_zero_shot(blk, vt, voice_use, stream=a.stream)):
            sp = seg_path if k == 0 else seg_path.replace(".wav", f"_{k}.wav")
            torchaudio.save(sp, seg["tts_speech"], m.sample_rate)
            sub_parts.append(sp)
            n_seg += 1
        if n_seg == 0:
            print(f"× 第 {i+1} 块没有返回音频,停止")
            save_prog(done, {"stage": f"failed_at_block_{i+1}"})
            return 3

        # 该块内部若又被切成多段,先拼成一个块文件
        if n_seg > 1:
            lst = seg_path.replace(".wav", "_lst.txt")
            with open(lst, "w", encoding="utf-8") as f:
                for sp in sub_parts:
                    f.write(f"file '{sp}'\n")
            merged = seg_path.replace(".wav", "_m.wav")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                            "-c", "copy", merged], check=True, capture_output=True)
            for sp in sub_parts:
                try:
                    os.remove(sp)
                except OSError:
                    pass
            os.replace(merged, seg_path)
            os.remove(lst)

        dur = float((subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", seg_path],
            capture_output=True, text=True).stdout or "0").strip() or 0)
        el = time.time() - bt
        rec = {"block": i + 1, "chars": len(blk), "audio_s": round(dur, 2),
               "elapsed_s": round(el, 1),
               "stream": bool(a.stream),
               # 口径统一：倍率 = 耗时 ÷ 音频时长（与文章「慢约 5.9 倍」一致），
               # 不要用「音频 ÷ 耗时」——同一件事两套口径会让人以为算错了。
               "cost_ratio": round(el / dur, 2) if dur else 0}
        done[i] = rec
        per_block.append(rec)
        parts.append(seg_path)
        total_audio += dur
        save_prog(done, {"stage": f"block_{i+1}_done", "total_audio_s": round(total_audio, 1)})
        print(f"[块 {i+1}/{len(blocks)}] {len(blk)} 字 → {dur:.1f} 秒音频,"
              f"耗时 {el:.0f} 秒(慢 {rec['cost_ratio']} 倍);累计音频 {total_audio/60:.1f} 分钟", flush=True)

    print(f"\n· 全部 {len(parts)} 块完成,正在拼接…", flush=True)

    # 坑 3(最容易中招):长文本会被引擎切成多段,必须**全部拼接**。
    # 只取第一段的话,一段 380 字的故事成品只有 15 秒 —— 我就是这么踩的。
    if len(parts) > 1:
        lst = os.path.join(work, "concat.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for pp in parts:
                f.write(f"file '{pp}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", wav], check=True, capture_output=True)
    else:
        os.replace(parts[0], wav)

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
    el_total = time.time() - t1

    save_prog(done, {"stage": "finished", "total_audio_s": round(secs, 1),
                     "total_elapsed_s": round(el_total, 1),
                     "load_s": round(load_s, 1)})
    print("")
    print(f"√ 完成!生成音频 {secs:.1f} 秒({secs/60:.1f} 分钟),用时 {el_total:.0f} 秒")
    print(f"  文件:{out}")
    print(f"  分块明细:{prog_path}")
    if el_total > 0:
        print(f"  整体:耗时是音频的 {el_total/secs:.2f} 倍(含模型加载 {load_s:.0f} 秒)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
