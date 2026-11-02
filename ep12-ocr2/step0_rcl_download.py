"""STEP 0-A：让 RapidOCRLite 解析并下载 PP-OCRv6 medium 档（与 ep11 PaddleOCR 同档）。

只下载与读取，不跑任何测量。下载落 Global.model_root_dir（指向 D 盘）。
"""
import json
import os
import pathlib
import sys
import time
import traceback

# 模型根目录指到 D 盘
MODEL_ROOT = r"D:/models/ep12-ocr2/rapidocr"
os.makedirs(MODEL_ROOT, exist_ok=True)

import rapidocr
from rapidocr import RapidOCR

print("rapidocr 版本:", getattr(rapidocr, "__version__", "?"))
print("模型根目录:", MODEL_ROOT)

# 先看 RapidOCR 构造参数与默认 config
import inspect
print("RapidOCR.__init__ 签名:", inspect.signature(RapidOCR.__init__))

# 读 config.yaml 找 model_root_dir 键名
cfg = pathlib.Path(rapidocr.__file__).parent / "config.yaml"
ct = cfg.read_text(encoding="utf-8", errors="replace")
for i, l in enumerate(ct.split("\n")):
    if any(k in l for k in ("model_root", "root_dir", "model_dir", "det_model", "rec_model", "use_det", "use_cls", "use_rec", "pre_label")):
        print("  cfg L%-4d %s" % (i + 1, l[:110]))

print("\n=== 尝试用 params 显式指定 medium 档并触发下载 ===")
t0 = time.time()
try:
    ocr = RapidOCR(params={
        "Global.model_root_dir": MODEL_ROOT,
        "Det.model_type": "medium",
        "Rec.model_type": "medium",
        "Det.lang_type": "ch",
        "Rec.lang_type": "ch",
    })
    print("构造成功，耗时 %.1fs" % (time.time() - t0))
except Exception:
    traceback.print_exc()
    print("\n--- 换一种参数形态试 ---")
    try:
        ocr = RapidOCR(params={
            "Global.model_root_dir": MODEL_ROOT,
            "det.model_type": "medium",
            "rec.model_type": "medium",
        })
        print("构造成功（小写键），耗时 %.1fs" % (time.time() - t0))
    except Exception:
        traceback.print_exc()
        ocr = None

print("\n=== 下载目录内容 ===")
mr = pathlib.Path(MODEL_ROOT)
if mr.exists():
    for f in sorted(mr.rglob("*")):
        if f.is_file():
            print("   %-64s %8.3f MB" % (str(f.relative_to(mr))[:64], f.stat().st_size / 1e6))
else:
    print("   目录不存在")

# 也看默认缓存位置有没有落
for p in [pathlib.Path(os.path.expanduser("~/.cache/modelscope"))]:
    if p.exists():
        print("\nmodelscope 缓存 %s:" % p)
        for f in sorted(p.rglob("*.onnx"))[:10]:
            print("   %-70s %8.3f MB" % (str(f)[-70:], f.stat().st_size / 1e6))
