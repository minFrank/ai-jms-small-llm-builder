"""录音来源 A/B 对比（骨架，2026-09-19 预留，尚未跑过）

背景：文章里曾说「微信语音当素材，克隆出来发闷、发飘」。查证后发现——包内文档写了这条，
但我们**没有任何 A/B 实测记录**，属于推断。用户决定：**先不做，后续再测，留个口子**。
所以这个脚本写好了但没跑过；文章里那句已改成不带结论的客观表述。

用途（等要测的时候）：
    python tools/ab_voice_source.py --a 原始录音.wav --b 微信语音.wav \
        --a-text 原始录音说的是什么.txt --b-text 微信语音说的是什么.txt \
        --text-file story.txt

它做的事：用**同一段要念的文字**，分别在两种录音素材上跑一次克隆，输出到
output/ab-<时间戳>/{a,b}/，并打印两边的耗时、音频时长、倍率——便于人工听感 + 数据对照。

判据（跑完再看，现在先别当结论）：
  · 客观：两边音频时长、耗时、倍率差多少（数据可对照）
  · 主观：同一句话在两边听起来是否发闷/发飘（要人耳朵拍板，不写成结论）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent


def run_one(label: str, voice: Path, voice_text_file: Path, text_file: Path, out_dir: Path) -> float:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{label}.mp3"
    cmd = [sys.executable, str(HERE / "tts.py"),
           "--text-file", str(text_file), "--voice", str(voice),
           "--voice-text-file", str(voice_text_file), "--out", str(out)]
    print(f"\n=== [{label}] 素材：{voice.name} ===")
    print("命令：", " ".join(cmd[-8:]))
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(KIT))
    dt = time.time() - t0
    if r.returncode != 0:
        print(f"× [{label}] 失败，退出码 {r.returncode}")
        return -1.0
    if out.exists():
        print(f"· [{label}] 产出 {out}（{out.stat().st_size/1024:.0f} KB），墙钟 {dt/60:.1f} 分钟")
    return dt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="素材 A（原始录音）")
    ap.add_argument("--b", required=True, help="素材 B（微信语音）")
    ap.add_argument("--a-text", required=True, help="A 对应的录音文本")
    ap.add_argument("--b-text", required=True, help="B 对应的录音文本")
    ap.add_argument("--text-file", default="story.txt", help="要念的文字（两边必须同一份）")
    a = ap.parse_args()
    ts = time.strftime("%Y%m%d-%H%M%S")
    base = KIT / "output" / f"ab-{ts}"
    print(f"输出目录：{base}")
    print("⚠️ 这是 2026-09-19 预留的对比脚本：两边各跑一次克隆，长文本会跑很久，")
    print("   别在机器忙着的时候跑；跑完把听感与数据补进 review/TODO-voice-source-ab.md。")
    ta = run_one("a", Path(a.a), Path(a.a_text), Path(a.text_file), base / "a")
    tb = run_one("b", Path(a.b), Path(a.b_text), Path(a.text_file), base / "b")
    print("\n=== 汇总（先看数字，听感要人耳拍板）===")
    print(f"A 墙钟 {ta/60:.1f} 分钟 | B 墙钟 {tb/60:.1f} 分钟")
    print("两边音频时长请用 ffprobe 量：ffprobe -v error -show_entries format=duration -of csv=p=0 文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
