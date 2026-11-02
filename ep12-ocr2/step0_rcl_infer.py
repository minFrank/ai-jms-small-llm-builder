"""STEP 0-A：真跑一次推理，触发 RapidOCRLite 下载 PP-OCRv6 medium 权重与字典。

触发后导出 manifest：档位 / rec image_shape / det long_side / 字典文件路径与内容 hash。
只跑 1 张图，不做正式测量。
"""
import hashlib
import json
import os
import pathlib
import time
import traceback

MODEL_ROOT = r"D:/models/ep12-ocr2/rapidocr"
os.makedirs(MODEL_ROOT, exist_ok=True)
IMG = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples/book_01.png"
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/manifest_rcl_step0.json")

from rapidocr import RapidOCR


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


print("图:", IMG, "存在:", pathlib.Path(IMG).exists())
print("触发下载中（medium 档，约 90 MB）...")
t0 = time.time()
try:
    ocr = RapidOCR(params={
        "Global.model_root_dir": MODEL_ROOT,
        "Det.model_type": "medium",
        "Rec.model_type": "medium",
        "Det.lang_type": "ch",
        "Rec.lang_type": "ch",
    })
    res = ocr(IMG)
    print("推理完成 %.1fs" % (time.time() - t0))
    # res 可能是 tuple 或对象
    try:
        txt = res.txts if hasattr(res, "txts") else res[1]
        print("识别行数:", len(txt) if txt else 0)
        if txt:
            print("首行:", str(txt[0])[:60])
    except Exception:
        print("结果类型:", type(res))
except Exception:
    traceback.print_exc()

print("\n=== 下载落盘情况 ===")
mr = pathlib.Path(MODEL_ROOT)
files = []
if mr.exists():
    for f in sorted(mr.rglob("*")):
        if f.is_file():
            files.append(f)
            print("   %-60s %8.3f MB" % (str(f.relative_to(mr))[:60], f.stat().st_size / 1e6))

# 也查 modelscope 默认缓存
for cp in [pathlib.Path(os.path.expanduser("~/.cache/modelscope/hub")),
           pathlib.Path(os.path.expanduser("~/.cache/modelscope"))]:
    if cp.exists():
        ons = sorted(cp.rglob("*.onnx")) + sorted(cp.rglob("*dict*.txt"))
        if ons:
            print("\nmodelscope 缓存 %s:" % cp)
            for f in ons[:14]:
                print("   %-64s %8.3f MB" % (str(f)[-64:], f.stat().st_size / 1e6))
                files.append(f)

# 导出 manifest
res2 = {"engine": "RapidOCRLite", "version": "5.0.0a15", "tier_requested": "medium",
        "model_root": MODEL_ROOT, "files": []}
for f in files:
    res2["files"].append({
        "path": str(f), "mb": round(f.stat().st_size / 1e6, 3), "sha256": sha256_of(f)})
OUT.write_text(json.dumps(res2, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n已写:", OUT, "文件数", len(res2["files"]))
