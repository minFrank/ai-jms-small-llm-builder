#!/bin/bash
# ep04 P2 · 1024 档 9 次(3 套 × n=3, cell p0_s42)串行跑测
# 2026-10-11 批复: D1A 全量 / D2A n=3 / D3A 1024 全跑+时间盒 / D4A 冷启动含加载 / D5A 天然后端 / D6A 先小样再全量
# 顺序按「慢的先跑」:ComfyUI 最慢且最可能出问题,先暴露
# 全部写新 progress,不碰已发布文件
cd "$(dirname "$0")/.." || exit 1
PY="D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
L="logs"
MARK="$L/p2-1024-progress.log"

echo "[P2-1024] start $(date '+%F %T')" | tee -a "$MARK"

echo "[P2 1/3] ComfyUI 1024 (最慢,含 20min 时间盒) ..." | tee -a "$MARK"
"$PY" tools/bench5.py --only cold --n 3 --size 1024 --cells p0_s42 \
     --out "$L/bench5-progress-1024.json" > "$L/p2-comfy-1024.log" 2>&1
echo "[P2 1/3] rc=$? at $(date '+%T')" | tee -a "$MARK"

echo "[P2 2/3] diffusers 1024 ..." | tee -a "$MARK"
"$PY" tools/bench7_diffusers.py --size 1024 --cells p0_s42 --n 3 \
     --out "$L/bench7-diffusers-1024.json" > "$L/p2-diff-1024.log" 2>&1
echo "[P2 2/3] rc=$? at $(date '+%T')" | tee -a "$MARK"

echo "[P2 3/3] ONNX 1024 ..." | tee -a "$MARK"
"$PY" tools/bench6.py --mode timing --cells p0_s42 --n 3 --size 1024 --warmup 1 \
     --out "$L/bench6-progress-1024.json" > "$L/p2-onnx-1024.log" 2>&1
echo "[P2 3/3] rc=$? at $(date '+%T')" | tee -a "$MARK"

echo "[P2-1024] done $(date '+%F %T')" | tee -a "$MARK"
