#!/usr/bin/env bash
# 03 期模型下载：sherpa-onnx 官方模型包（GitHub releases，走代理）+ faster-whisper small（HF 走代理）
# 全部落 D 盘（C 盘紧张）
set -u
PX="http://127.0.0.1:7897"
OUT="C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/ep03"
DST="/d/models/asr"
DSTN="D:/models/asr"          # 原生 curl 只认这个写法（踩过：/d/... 会被判「找不到文件」）
mkdir -p "$OUT" "$DST"
LOG="$OUT/dl-$(date +%Y%m%d-%H%M).txt"
PY="D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"

{
echo "=============================================================="
echo " 03 期模型下载 · $(date '+%Y-%m-%d %H:%M:%S')  （全部落 D:/models/asr）"
echo "=============================================================="
for name in \
  "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17" \
  "sherpa-onnx-paraformer-zh-2023-09-14" \
  "sherpa-onnx-whisper-small" ; do
  if [ -d "$DST/$name" ] && [ -n "$(ls -A "$DST/$name" 2>/dev/null)" ]; then
    echo "  跳过（已存在）: $name"; continue
  fi
  echo
  echo "### $name ###"
  curl -L --max-time 1800 -x "$PX" -o "$DSTN/$name.tar.bz2" "$REL/$name.tar.bz2" \
    -w "  下载: HTTP %{http_code} · %{size_download} 字节 · %{speed_download} B/s\n" 2>&1 | tail -2
  if [ -s "$DST/$name.tar.bz2" ]; then
    tar -xjf "$DST/$name.tar.bz2" -C "$DST" && rm -f "$DST/$name.tar.bz2" && echo "  解压 ✅"
  else
    echo "  ❌ 没下到文件"
  fi
done

echo
echo "### faster-whisper small（HF，走代理）###"
FW="$DST/faster-whisper-small"
mkdir -p "$FW"
for f in config.json model.bin tokenizer.json vocabulary.txt; do
  [ -s "$FW/$f" ] && { echo "  跳过 $f"; continue; }
  code=$(curl -L --max-time 1800 -x "$PX" -o "D:/models/asr/faster-whisper-small/$f" -w "%{http_code} %{size_download}" \
    "https://huggingface.co/Systran/faster-whisper-small/resolve/main/$f")
  echo "  $f → HTTP $code 字节"
done

echo
echo "### 清点（体积要写进文章）###"
for d in "$DST"/*/; do
  [ -d "$d" ] || continue
  echo "  $(du -sm "$d" 2>/dev/null | cut -f1) MB  $(basename "$d")"
  ls -1 "$d" | head -5 | sed 's/^/        /'
done
} > "$LOG" 2>&1

echo "日志: $LOG"
tail -40 "$LOG"
