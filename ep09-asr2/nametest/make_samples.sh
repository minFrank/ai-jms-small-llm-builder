#!/usr/bin/env bash
# 专名专项:8 句(含不同类专名)用 Windows SAPI Huihui 合成 16k 单声道 wav
set -u
OUT_DIR="D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/nametest/samples"
mkdir -p "$OUT_DIR"
FF="C:/Users/Frank/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg"

# 句子表(文件名|类别|GT 原文)
SENTS=(
  "N_1|品牌|特斯拉的车机接入了豆包大模型"
  "N_2|品牌|欢迎关注 AI 积木师的频道"
  "N_3|人名|李明让王小明把合同发给张总"
  "N_4|术语|二氧化碳和二氧化硅的熔点不同"
  "N_5|中英|把 README 转成 Markdown 格式"
  "N_6|中英|用 Kubernetes 部署 Docker 容器"
  "N_7|品牌|特斯拉车主在蔚来的换电站排队"
  "N_8|对照|今天天气不错适合出去走走"
)

# 生成 refs.json(用 python 拼,避免 shell 转义)
PY="D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
"$PY" - "$OUT_DIR" "${SENTS[@]}" << 'PYEOF'
import json, sys, os
out = sys.argv[1]
refs = {}
for item in sys.argv[2:]:
    fn, cat, text = item.split("|")
    refs[fn + ".wav"] = text
json.dump(refs, open(os.path.join(out, "refs.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("refs.json:", len(refs), "条")
PYEOF

# PowerShell SAPI 逐句合成(raw 22k wav -> ffmpeg 转 16k mono)
for item in "${SENTS[@]}"; do
  fn="${item%%|*}"
  rest="${item#*|}"
  text="${rest#*|}"
  if [ -f "$OUT_DIR/$fn.wav" ]; then
    echo "  skip $fn"
    continue
  fi
  powershell -NoProfile -Command "
    Add-Type -AssemblyName System.Speech;
    \$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;
    \$s.SelectVoice('Microsoft Huihui Desktop');
    \$s.Rate = -1;
    \$s.SetOutputToWaveFile('$OUT_DIR/$fn.raw.wav');
    \$s.Speak('$text');
    \$s.Dispose()" 2>&1 | head -2
  if [ -f "$OUT_DIR/$fn.raw.wav" ]; then
    "$FF" -y -v error -i "$OUT_DIR/$fn.raw.wav" -ar 16000 -ac 1 -c:a pcm_s16le "$OUT_DIR/$fn.wav" && rm -f "$OUT_DIR/$fn.raw.wav"
    echo "  ✓ $fn.wav"
  else
    echo "  ✗ $fn 生成失败"
  fi
done

echo "=== 产物 ==="
ls -la "$OUT_DIR"/*.wav 2>/dev/null | awk '{print "  ", $9, $5"B"}'
echo "=== 时长 ==="
FP="C:/Users/Frank/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe"
for w in "$OUT_DIR"/*.wav; do
  echo "  $(basename "$w"): $("$FP" -v error -show_entries format=duration -of csv=p=0 "$w" 2>/dev/null)s"
done
