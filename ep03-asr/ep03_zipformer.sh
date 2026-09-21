#!/usr/bin/env bash
# 下载并解压 2 个离线中文 zipformer（int8），放入 D:/models/asr/
set -u
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
DST="/d/models/asr"
export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897

FILES=(
  "sherpa-onnx-zipformer-ctc-small-zh-int8-2025-07-16.tar.bz2"
  "sherpa-onnx-zipformer-ctc-zh-int8-2025-07-03.tar.bz2"
)

for f in "${FILES[@]}"; do
  name="${f%.tar.bz2}"
  if [ -d "$DST/$name" ]; then echo "已存在，跳过: $name"; continue; fi
  echo "=== 下载 $f ==="
  curl -L --noproxy '*' -x http://127.0.0.1:7897 -o "$DST/$f" "$REL/$f" -w "  HTTP %{http_code}  %{size_download} 字节\n"
  echo "=== 解压（用 Python tarfile，MSYS tar 会截断）==="
  "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe" - "$DST/$f" "$DST" <<'PYEOF'
import sys, tarfile, pathlib
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
with tarfile.open(src, "r:bz2") as t:
    t.extractall(dst)
    names = t.getnames()
print(f"  解出 {len(names)} 项")
PYEOF
  rm -f "$DST/$f"
done

echo
echo "=== 落盘情况 ==="
for d in "$DST"/sherpa-onnx-zipformer-ctc-small-zh-int8-2025-07-16 "$DST"/sherpa-onnx-zipformer-ctc-zh-int8-2025-07-03; do
  [ -d "$d" ] || { echo "  ❌ 缺: $d"; continue; }
  tot=$(du -sm "$d" | cut -f1)
  echo "  $(basename "$d"): 共 ${tot} MB"
  ls -la "$d" | awk '{printf "      %-46s %8.1f MB\n", $9, $5/1048576}' | tail -8
done
