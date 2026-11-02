"""STEP 2 探针：PaddleOCR-VL 在 paddlex 里的真实调用面。

只做 API 探查，不下载模型、不跑测量。
"""
import subprocess
import sys

VP = sys.executable

code = r'''
import importlib, pkgutil, inspect, traceback

print("paddle/paddlex 版本:")
import paddle
print("  paddle", paddle.__version__)
import paddlex
print("  paddlex", paddlex.__version__)

# 1) paddlex 支持的 pipeline 列表（找 OCR-VL 相关）
print("\n=== paddlex pipelines ===")
try:
    from paddlex import pipelines
    names = [n for n in dir(pipelines) if not n.startswith("_")]
    print("  ", names[:40])
except Exception as e:
    print("  列 pipelines 失败:", str(e)[:120])

# 2) 直接找 VL 相关模块
print("\n=== 含 'vl' 的模块 ===")
hits = []
for m in pkgutil.iter_modules(paddlex.__path__):
    if "vl" in m.name.lower() or "ocr" in m.name.lower():
        hits.append(m.name)
print("  ", hits[:20])

# 3) create_pipeline 的签名与支持的 pipeline 名
print("\n=== paddlex.create_pipeline 签名 ===")
try:
    from paddlex import create_pipeline
    print("  ", inspect.signature(create_pipeline))
except Exception as e:
    print("  ", str(e)[:150])

# 4) 支持的 pipeline 枚举
print("\n=== create_pipeline 支持的 pipeline 名 ===")
try:
    import paddlex.create_pipeline as cp
    src = inspect.getsource(cp)
    import re
    # 抓字符串字面量里的 pipeline 名
    names = sorted(set(re.findall(r'"([a-zA-Z0-9_\-]*(?:ocr|OCR|vl|VL)[a-zA-Z0-9_\-]*)"', src)))
    print("  ", names[:40])
    print("  源码长度:", len(src))
except Exception as e:
    print("  ", str(e)[:150])

# 5) 全局搜 PaddleOCRVL
print("\n=== 全局搜 PaddleOCRVL / PPOCRVL ===")
import pathlib
root = pathlib.Path(paddlex.__file__).parent
found = []
for f in root.rglob("*.py"):
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "PaddleOCRVL" in t or "PPOCRVL" in t or "paddleocr_vl" in t.lower():
        found.append(str(f.relative_to(root)))
print("  命中文件数:", len(found))
for x in found[:12]:
    print("   ", x)
'''
r = subprocess.run([VP, "-c", code], capture_output=True, text=True, timeout=600)
print(r.stdout[-5000:])
if r.returncode != 0:
    print("STDERR:", (r.stderr or "")[-1500:])
