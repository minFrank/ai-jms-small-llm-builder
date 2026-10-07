#!/usr/bin/env bash
# ComfyUI 独立 venv 搭建(阶段1) - uv 路线
# 设计依据: EXPAND-DESIGN.md + dsh 评审 REVIEW-dsh.md (DP-01/DP-02/DP-04)
set -u
PY311="C:/Users/Frank/AppData/Local/hermes/hermes-agent/.hermes-runtime/python/cpython-3.11-windows-x86_64-none/python.exe"
if [ ! -f "$PY311" ]; then
  PY311="$(py -V:Astral/CPython3.11.16 -c "import sys;print(sys.executable)" 2>/dev/null || true)"
fi
echo "PY311=$PY311"
if [ -z "$PY311" ]; then echo "FATAL: 找不到 Python 3.11"; exit 2; fi

V=D:/ep04/comfy/venv
E=D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img
mkdir -p "$E/logs" "$E/replicate"
if [ ! -f "$V/Scripts/python.exe" ]; then
  uv venv --clear --python "$PY311" "$V" || { echo "FATAL: venv 失败"; exit 3; }
fi
PY="$V/Scripts/python.exe"
echo "PY=$PY"
UVPI="uv pip install --python $PY --default-index https://pypi.org/simple"

# 1) torch 钉现有 venv 版本(DP-02)
$UVPI torch==2.14.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -4
$UVPI torchvision --extra-index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3

# 2) ComfyUI 依赖
"$PY" - <<'PYEOF'
import zipfile
z = zipfile.ZipFile(r'D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/comfy.zip')
n = [x for x in z.namelist() if x.endswith('/requirements.txt') and 'tests' not in x][0]
open(r'D:/ep04/comfy/ComfyUI-src/requirements.txt','wb').write(z.read(n))
print('requirements.txt <-', n)
PYEOF
$UVPI -r D:/ep04/comfy/ComfyUI-src/requirements.txt 2>&1 | tail -6

echo "=== 导入自检 ==="
"$PY" -c "import torch, numpy, PIL, transformers, safetensors, scipy, psutil, torch, torch; print('torch', torch.__version__, '| numpy', numpy.__version__, '| PIL', PIL.__version__)" || echo "FAIL: 导入失败"

echo "=== freeze 落档(DP-04) ==="
"$PY" -m pip freeze > "$E/env-comfy.txt" 2>/dev/null || uv pip freeze --python "$PY" > "$E/env-comfy.txt"
"$PY" -V > "$E/env-comfy-python.txt"
echo "comfy freeze 行数: $(wc -l < "$E/env-comfy.txt")"
cat "$E/env-comfy-python.txt"

echo "=== 与主 venv 版本比对(DP-02) ==="
"$PY" -c "
def load(p):
    d={}
    for l in open(p, encoding='utf-8', errors='replace'):
        l=l.strip()
        if '==' in l and not l.startswith('#'):
            k,v=l.split('==',1); d[k.lower()]=v
    return d
a=load(r'D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/env-main.txt'); b=load(r'D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/env-comfy.txt')
diff=[]
for k in ['torch','numpy','pillow','safetensors','transformers','scipy','psutil']:
    va,vb=a.get(k,'(无)'),b.get(k,'(无)')
    mark='OK' if va==vb else 'DIFF'
    if mark=='DIFF': diff.append(k)
    print(f'{mark:4} {k:14} main={va} comfy={vb}')
print('DIFF_LIST=' + (','.join(diff) if diff else '(全部一致)'))
"
echo "SETUP_DONE"
