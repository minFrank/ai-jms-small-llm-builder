"""STEP 0 manifest 门：导出 ep11 venv 里 PaddleOCR 的 PP-OCRv6 权重清单。

严格只读：只扫文件、算 SHA256，不安装、不下载、不修改 ep11 venv。
"""
import hashlib
import json
import os
import pathlib
import sys

SP = pathlib.Path(r"D:/study/ai-jms/ai-radar-trend/.venv/Lib/site-packages")
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/manifest_paddleocr.json")


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# PaddleOCR 3.x 的模型缓存常见位置
cands = [
    SP / "paddleocr" / "_models",
    SP / "paddleocr" / "ppocr" / "utils" / "kie_dict",
    pathlib.Path(os.path.expanduser("~/.paddlex")),
    pathlib.Path(os.path.expanduser("~/paddlex")),
    pathlib.Path(r"D:/models") ,
]
found = []
for root in cands:
    if not root.exists():
        continue
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".pdiparams", ".pdmodel", ".pdmodel.trs",
                                        ".yml", ".yaml", ".txt", ".json"):
            found.append(f)

# 也扫 paddleocr 包内所有 yml（找 PP-OCRv6 配置）
cfgs = []
po = SP / "paddleocr"
if po.exists():
    for f in po.rglob("*.yml"):
        if "v6" in f.name.lower() or "v6" in str(f.parent).lower():
            cfgs.append(f)
    for f in po.rglob("*.yaml"):
        if "v6" in f.name.lower():
            cfgs.append(f)

result = {
    "engine": "PaddleOCR",
    "version": "3.7.0",
    "site_packages": str(SP),
    "note": "只读采集 ep11 venv，未做任何修改",
    "weights": [],
    "configs": [],
}
for f in sorted(set(found))[:60]:
    rel = str(f).replace("\\", "/")
    if "/D:/models/" in rel:
        rel = "D:/models/" + rel.split("/D:/models/")[1]
    else:
        try:
            rel = str(f.relative_to(SP)).replace("\\", "/")
        except Exception:
            rel = str(f)
    result["weights"].append({
        "rel": rel, "mb": round(f.stat().st_size / 1e6, 3), "sha256": sha256_of(f)})
for f in sorted(set(cfgs))[:20]:
    try:
        rel = str(f.relative_to(SP)).replace("\\", "/")
    except Exception:
        rel = str(f)
    result["configs"].append({"rel": rel, "sha256": sha256_of(f)})

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("已写:", OUT, OUT.stat().st_size, "字节")
print("\n找到权重/配置文件 %d 个" % len(result["weights"]))
for r in result["weights"][:25]:
    print("   %-58s %8.3f MB" % (r["rel"][:58], r["mb"]))
print("\nPP-OCRv6 相关配置 %d 个" % len(result["configs"]))
for c in result["configs"][:10]:
    print("   %s" % c["rel"])
