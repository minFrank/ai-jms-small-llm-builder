#!/usr/bin/env bash
# 回滚 MOSS-TTS-Nano 造成的降级，恢复 VoiceStudio 环境
set -u
V=/d/study/ai-jms/VoiceStudio/.venv/Scripts/python.exe
PIP="$V -m pip"
CLEAN="env -u HTTPS_PROXY -u HTTP_PROXY"

echo "=== 1) 卸载 moss-tts-nano ==="
$CLEAN "$V" -m pip uninstall -y moss-tts-nano 2>&1 | tail -3

echo ""
echo "=== 2) 恢复 torch 2.8.0+cu128 三件套 ==="
$CLEAN "$V" -m pip install --force-reinstall --no-deps \
  torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -6

echo ""
echo "=== 3) 恢复 transformers 5.15.1 ==="
$CLEAN "$V" -m pip install --force-reinstall --no-deps transformers==5.15.1 2>&1 | tail -4

echo ""
echo "=== 4) 恢复 huggingface-hub（取备份里的版本）==="
HFV=$(grep -iE "^huggingface-hub==" /d/models/tts/_pip_before.txt | head -1 | sed 's/.*==//')
echo "目标版本: $HFV"
$CLEAN "$V" -m pip install --force-reinstall --no-deps "huggingface-hub==$HFV" 2>&1 | tail -4

echo ""
echo "=== 5) 恢复 fsspec 2026.7.0 ==="
$CLEAN "$V" -m pip install --force-reinstall --no-deps fsspec==2026.7.0 2>&1 | tail -3

echo ""
echo "=== 6) 复验 ==="
"$V" -c "
import importlib
mods = ['torch','torchvision','torchaudio','transformers','huggingface_hub',
        'fsspec','fastapi','uvicorn','psutil','faster_whisper','numpy',
        'soundfile','librosa','voxcpm','gradio']
for m in mods:
    try:
        mod = importlib.import_module(m)
        print('  %-16s OK   %s' % (m, getattr(mod, '__version__', '?')))
    except Exception as e:
        print('  %-16s FAIL %s' % (m, str(e)[:70]))
try:
    import omnivoice
    print('  %-16s OK   %s' % ('omnivoice', getattr(omnivoice, '__version__', '?')))
except Exception as e:
    print('  %-16s FAIL %s' % ('omnivoice', str(e)[:70]))
"

echo ""
echo "=== 7) 依赖冲突复检 ==="
$CLEAN "$V" -m pip check 2>&1 | head -20
