#!/usr/bin/env bash
# 03 期样本构建：3 个源音频 × 5 类条件 = 15 组，全部转 16kHz 单声道（ASR 标准输入）
# 源：A=8s 短档(真人) B=17s 中档(真人) C=B 循环拼成 ~10.5 分钟(覆盖「长音频」条件)
# 条件：clean / +bgm / +noise / 1.5x 快语速 / 低音量+混响
# 每个条件都留 ground truth（文本已知），后面算 CER 用
set -u
W="C:/Users/Frank/AppData/Local/hermes/workspace"
SRC="$W/videos/voices"
BGM="$W/videos/bgm/tech-live-loop.m4a"
OUT="$W/articles/series/local-ai/ep03/samples"
mkdir -p "$OUT"
FF="C:/Users/Frank/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg"
FP="C:/Users/Frank/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe"
A="$SRC/frank-voice-ref-16k-new.wav"
B="$SRC/frank-voice-ref.wav"

# ground truth
TXT_A="关注 AI 积木师，带你从 AI 的视角解读和理解生活"
TXT_B="大家好，这里是 AI 积木师。今天用三分钟，把一个 AI 工具拆成看得懂、用得上、装得起的积木块。从今天起，我每天帮你筛一个真正有价值的东西出来。"

echo "=== ① 先做长音频源 C（B 循环 ~10.5 分钟）==="
"$FF" -y -stream_loop 36 -i "$B" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/srcC_long.wav" 2>&1 | tail -1
echo "  C 时长: $("$FP" -v error -show_entries format=duration -of csv=p=0 "$OUT/srcC_long.wav" 2>/dev/null) 秒"

echo
echo "=== ② 三个源 × 五个条件 ==="
for tag in A B C; do
  case $tag in
    A) in="$A";;
    B) in="$B";;
    C) in="$OUT/srcC_long.wav";;
  esac
  echo "── 源 $tag"
  # ① clean
  "$FF" -y -i "$in" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/${tag}_1_clean.wav" 2>&1 | tail -1
  # ② +背景音乐
  "$FF" -y -i "$in" -i "$BGM" -filter_complex "[1:a]volume=0.18,aloop=loop=-1:size=2000000000[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=0" \
     -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/${tag}_2_bgm.wav" 2>&1 | tail -1
  # ③ +噪声
  "$FF" -y -i "$in" -f lavfi -i "anoisesrc=c=pink:r=16000:amplitude=0.05" \
     -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0" \
     -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/${tag}_3_noise.wav" 2>&1 | tail -1
  # ④ 1.5 倍速
  "$FF" -y -i "$in" -filter:a "atempo=1.5" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/${tag}_4_fast1.5x.wav" 2>&1 | tail -1
  # ⑤ 低音量 + 混响
  "$FF" -y -i "$in" -filter:a "volume=0.25,aecho=0.8:0.9:40:0.4" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT/${tag}_5_lowvol_reverb.wav" 2>&1 | tail -1
done

echo
echo "=== ③ 清单（时长 + 体积）==="
for f in "$OUT"/*.wav; do
  d=$("$FP" -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  printf "  %-26s %8.1f 秒  %5s KB\n" "$(basename "$f")" "${d:-0}" "$(( $(stat -c%s "$f") / 1024 ))"
done

echo
echo "=== ④ 写 manifest（ground truth 与条件说明，后面算 CER 用）==="
cat > "$OUT/manifest.json" <<EOF
{
  "TXT_A": "$TXT_A",
  "TXT_B": "$TXT_B",
  "note": "源 C = 源 B 循环 37 次（覆盖 10 分钟以上长音频条件）；条件 4 变速后文本不变",
  "conditions": {"1": "clean", "2": "+bgm(tech-live-loop, 18%)", "3": "+pink noise(0.05)",
                 "4": "atempo 1.5x", "5": "volume 0.25 + aecho"},
  "ground_truth": {"A": "TXT_A", "B": "TXT_B", "C": "TXT_B × 37"}
}
EOF
echo "  manifest.json 写好"
