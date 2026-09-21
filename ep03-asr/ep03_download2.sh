#!/usr/bin/env bash
# 03 期模型补下（断点续传 + 解压后校验）：只补缺失/不完整的，SenseVoice 已完成则跳过
set -u
PX="http://127.0.0.1:7897"
OUT="C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/ep03"
DST="/d/models/asr"; DSTN="D:/models/asr"
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
LOG="$OUT/dl2-$(date +%Y%m%d-%H%M).txt"

{
echo "=============================================================="
echo " 03 期模型补下 · $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================="

# 期望体积（MB，粗略，用于判断是否完整）
check_ok() {   # $1=目录名  $2=最小体积MB
  local d="$DST/$1"; [ -d "$d" ] || return 1
  local sz=$(du -sm "$d" 2>/dev/null | cut -f1)
  [ "${sz:-0}" -ge "$2" ] && return 0 || return 1
}

for spec in \
  "sherpa-onnx-paraformer-zh-2023-09-14:200" \
  "sherpa-onnx-whisper-small:300" ; do
  name="${spec%%:*}"; min="${spec##*:}"
  echo
  echo "### $name（完整性门槛 ${min}MB）###"
  if check_ok "$name" "$min"; then echo "  已完整，跳过"; continue; fi
  rm -rf "$DST/$name"                     # 清掉不完整的解压目录
  if [ ! -s "$DSTN/$name.tar.bz2" ] || [ "$(stat -c%s "$DSTN/$name.tar.bz2")" -lt 1000000 ]; then
    curl -L -C - --max-time 2400 -x "$PX" -o "$DSTN/$name.tar.bz2" "$REL/$name.tar.bz2" 2>/dev/null
  fi
  echo "  tar 体积: $(du -m "$DSTN/$name.tar.bz2" 2>/dev/null | cut -f1) MB"
  if tar -tjf "$DSTN/$name.tar.bz2" >/dev/null 2>&1; then
    echo "  tar 完整性 ✅"
    tar -xjf "$DSTN/$name.tar.bz2" -C "$DST" && echo "  解压 ✅ → $(du -sm "$DST/$name" | cut -f1) MB"
  else
    echo "  ❌ tar 不完整（下次续传）"
  fi
done

echo
echo "### faster-whisper small（HF 走代理，逐个文件校验）###"
FW="$DST/faster-whisper-small"; FWN="$DSTN/faster-whisper-small"
mkdir -p "$FW"
declare -A WANT=([config.json]=2000 [tokenizer.json]=400000 [vocabulary.txt]=400000 [model.bin]=400000000)
for f in config.json tokenizer.json vocabulary.txt model.bin; do
  need=${WANT[$f]}
  cur=$(stat -c%s "$FW/$f" 2>/dev/null || echo 0)
  if [ "$cur" -ge "$need" ]; then echo "  $f 已完整（$((cur/1024)) KB），跳过"; continue; fi
  curl -L -C - --max-time 2400 -x "$PX" -o "$FWN/$f" \
    "https://huggingface.co/Systran/faster-whisper-small/resolve/main/$f" 2>/dev/null
  echo "  $f → $(( $(stat -c%s "$FWN/$f" 2>/dev/null || echo 0) / 1024 )) KB"
done

echo
echo "### 最终清点 ###"
for d in "$DST"/*/; do
  [ -d "$d" ] || continue
  printf "  %6s MB  %s\n" "$(du -sm "$d" 2>/dev/null | cut -f1)" "$(basename "$d")"
done
} > "$LOG" 2>&1

echo "DONE $LOG"
tail -25 "$LOG"
