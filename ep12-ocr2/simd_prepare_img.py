"""把 ep11 样本图转成裸 BGRA 字节 + 元数据，供 C# 侧 SimdPaddleOCR 直读。

SimdPaddleOCR 的 API 接收交错像素内存，不做图片解码 —— 所以解码放在 Python 侧。
"""
import json
import pathlib

from PIL import Image

SRC = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples")
OUT = pathlib.Path(r"D:/models/ep12-ocr2/simd/raw")
OUT.mkdir(parents=True, exist_ok=True)

meta = {}
for name in ["book_01.png", "table_01.png"]:
    p = SRC / name
    if not p.exists():
        print("缺图:", p)
        continue
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    stride = w * 4
    raw = im.tobytes()
    dest = OUT / (p.stem + ".bgra")
    dest.write_bytes(raw)
    meta[p.stem] = {"w": w, "h": h, "stride": stride, "path": str(dest), "bytes": len(raw)}
    print("  %-14s %dx%d  stride=%d  %.2f MB raw" % (name, w, h, stride, len(raw) / 1e6))

(OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("已写:", OUT / "meta.json")
