"""STEP 2-B：查实 PaddleOCR-VL 的推理后端到底有哪些。

判据：paddleocr_vl_09b/ 下除了 _vllm.py 与 _sglang/ 之外，
是否存在不依赖 vLLM/SGLang 的后端（如 transformers / paddle 静态图）。
"""
import pathlib
import re

import paddlex

root = pathlib.Path(paddlex.__file__).parent
base = root / "inference" / "genai" / "models" / "paddleocr_vl_09b"

print("=== paddleocr_vl_09b 目录树 ===")
for f in sorted(base.rglob("*")):
    if f.is_file():
        print("  %-58s %6.1f KB" % (str(f.relative_to(base))[:58], f.stat().st_size / 1024))

print("\n=== __init__.py 全文（看它导出什么、依赖什么后端）===")
init = base / "__init__.py"
if init.exists():
    t = init.read_text(encoding="utf-8", errors="replace")
    print(t[:3000])

print("\n=== 各文件里 import vllm / sglang 的情况 ===")
for f in sorted(base.rglob("*.py")):
    t = f.read_text(encoding="utf-8", errors="replace")
    has_vllm = bool(re.search(r"^\s*(import vllm|from vllm)", t, re.M))
    has_sglang = bool(re.search(r"^\s*(import sglang|from sglang)", t, re.M))
    has_tf = bool(re.search(r"^\s*(import transformers|from transformers)", t, re.M))
    has_torch = bool(re.search(r"^\s*(import torch|from torch)", t, re.M))
    print("  %-46s vllm=%-5s sglang=%-5s transformers=%-5s torch=%s"
          % (str(f.relative_to(base))[:46], has_vllm, has_sglang, has_tf, has_torch))

print("\n=== 判据：有没有第三种后端 ===")
names = [p.name for p in base.iterdir()]
print("  顶层项:", names)
backends = [n for n in names if n.startswith("_") and n.endswith(".py")]
dirs = [n for n in names if n.startswith("_") and n.is_dir()]
print("  后端文件:", backends)
print("  后端目录:", dirs)
other = [n for n in names if n not in backends + dirs and n != "__pycache__"]
print("  其它:", other)
