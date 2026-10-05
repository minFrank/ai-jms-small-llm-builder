#!/bin/bash
# ep04 三方案扩样本自动续跑:每轮检查缺哪格就跑哪个方案,直到 18 格全 ok。
# (后台任务偶发中途死,靠外层循环+断点续跑兜底)
cd "$(dirname "$0")"
PY="D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"

check() {  # 返回未完成方案(按顺序),全完返回空
  "$PY" - <<'EOF'
import json, sys
try:
    d = json.load(open('logs/bench4-progress.json', encoding='utf-8'))
except Exception:
    sys.exit(0)
ok = {r['scheme'] for r in d['rows'] if '_s' in r['cell'] and r['ok']}
need = [s for s in ['diffusers', 'sdcpp-cpu', 'sdcpp-vulkan'] if s not in ok]
print(need[0] if need else '')
EOF
}

for round in $(seq 1 40); do
  TARGET=$(check)
  if [ -z "$TARGET" ]; then
    echo "ALL 18 CELLS DONE ($(date +%H:%M:%S))"
    exit 0
  fi
  echo "[round $round] 跑 $TARGET ($(date +%H:%M:%S))"
  "$PY" tools/bench4.py --only "$TARGET" >> "logs/auto_${TARGET}.log" 2>&1
  RC=$?
  echo "[round $round] $TARGET exit=$RC"
  # 格子还没完就说明中途死了/超时,稍候重来(断点续跑会跳过已完成)
  sleep 15
done
echo "GAVE UP after 40 rounds"
exit 1
