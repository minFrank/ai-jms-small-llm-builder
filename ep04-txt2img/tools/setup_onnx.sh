#!/usr/bin/env bash
# ep04 阶段2: ONNX/DML 独立 venv (B9/DP-01/DP-03)
# 全程原生 D:/ 路径(原生程序不认 /d/)
set -u
PY311="C:/Users/Frank/AppData/Local/hermes/hermes-agent/.hermes-runtime/python/cpython-3.11-windows-x86_64-none/python.exe"
[ -f "$PY311" ] || PY311="$(py -V:Astral/CPython3.11.16 -c "import sys;print(sys.executable)" 2>/dev/null || true)"
echo "PY311=$PY311"
V=D:/ep04/onnx/venv
E=D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img
mkdir -p "$E/logs" "$E/replicate"

if [ ! -f "$V/Scripts/python.exe" ]; then
  uv venv --clear --python "$PY311" "$V" || { echo "FATAL: venv 失败"; exit 3; }
fi
PY="$V/Scripts/python.exe"
echo "PY=$PY"
UVPI="uv pip install --python $PY --default-index https://pypi.org/simple"

echo "=== 1) torch 钉 DP-02 ==="
$UVPI torch==2.14.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3

echo "=== 2) diffusers/transformers 钉 DP-35(与主 venv 一致)==="
$UVPI diffusers==0.40.0 transformers==5.18.0 safetensors==0.8.0 psutil==7.2.2 Pillow==12.3.0 numpy==2.4.6 scipy==1.17.1 2>&1 | tail -4

echo "=== 3) onnx + onnxruntime-directml (DP-03: 与 onnxruntime 同包名互斥)==="
$UVPI onnx==1.23.2 2>&1 | tail -3
$UVPI onnxruntime-directml==1.24.4 2>&1 | tail -3

echo "=== 4) DP-03 断言: 不得同时存在 onnxruntime(非 DML) ==="
"$PY" -m pip list 2>/dev/null | grep -i -E "^onnxruntime|^onnx " || true
"$PY" - <<'PYEOF'
import importlib.metadata as md
names = {d.metadata['Name'].lower() for d in md.distributions()}
dml = 'onnxruntime-directml' in names
plain = 'onnxruntime' in names
print(f"DP-03: directml={dml} plain_onnxruntime={plain}")
if dml and plain:
    raise SystemExit("FATAL(DP-03): onnxruntime 与 onnxruntime-directml 共存(同包名互斥)")
if not dml:
    raise SystemExit("FATAL(DP-03): 缺 onnxruntime-directml")
import onnxruntime as ort
print("providers:", ort.get_available_providers())
print("version:", ort.__version__)
if 'DmlExecutionProvider' not in ort.get_available_providers():
    raise SystemExit("FATAL: 无 DmlExecutionProvider")
print("DML_PROVIDER_OK")
PYEOF

echo "=== 5) DP-02 版本比对(参与出数的库)==="
"$PY" - <<'PYEOF'
def load(p):
    d={}
    for l in open(p, encoding='utf-8', errors='replace'):
        l=l.strip()
        if '==' in l and not l.startswith('#'):
            k,v=l.split('==',1); d[k.lower()]=v
    return d
a=load(r'D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/env-main.txt')
diff=[]
for k in ['torch','numpy','diffusers','transformers','safetensors']:
    try:
        import importlib.metadata as md
        vb = md.version(k)
    except Exception:
        vb = '(无)'
    va = a.get(k,'(无)')
    mark = 'OK' if va==vb else 'DIFF'
    if mark=='DIFF': diff.append(f'{k}: main={va} onnx={vb}')
    print(f'{mark:4} {k:16} main={va} onnx={vb}')
print('DIFF_LIST=' + ('; '.join(diff) if diff else '(全一致)'))
PYEOF

echo "=== 6) freeze 落档 (DP-04) ==="
uv pip freeze --python "$PY" > "$E/env-onnx.txt"
"$PY" -V > "$E/env-onnx-python.txt"
echo "行数 $(wc -l < "$E/env-onnx.txt")"
cat "$E/env-onnx-python.txt"
echo "P2_ENV_DONE"
