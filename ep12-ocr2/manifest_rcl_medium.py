"""STEP 0 manifest 门：让 RapidOCRLite 解析 medium 档配置，取其 det/rec 的 SHA256 与字典。

只做模型解析与下载（Medium 档，与 ep11 PaddleOCR 同档），不跑测量。
"""
import hashlib
import json
import os
import pathlib
import sys

import yaml

PKG = pathlib.Path(sys.prefix) / "Lib" / "site-packages" / "rapidocr"
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/manifest_rapidocrlite_medium.json")
dmp = PKG / "default_models.yaml"


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


raw = yaml.safe_load(dmp.read_text(encoding="utf-8"))
routes = raw.get("model_routes", raw)

# 逐层找 PP-OCRv6 下的 onnx 段
def find(node, path=""):
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            hits += find(v, path + "/" + str(k))
    elif isinstance(node, list):
        pass
    return hits


target = None
for topk, topv in routes.items():
    if not isinstance(topv, dict):
        continue
    for k, v in topv.items():
        if k == "PP-OCRv6" and isinstance(v, dict):
            target = v
            print("找到 PP-OCRv6 段，父键:", topk)
            break
    if target:
        break

res = {"engine": "RapidOCRLite", "version": "5.0.0a15", "ppocrv6": {}}
if target:
    print("  子键:", list(target.keys()))
    for kind in ("det", "rec"):
        block = target.get(kind)
        if not isinstance(block, dict):
            continue
        print("\n  --- %s ---" % kind)
        for name, cfg in block.items():
            if not isinstance(cfg, dict):
                continue
            if "lite" in name:
                continue
            md = cfg.get("model_dir", "")
            sh = cfg.get("SHA256", "")
            du = cfg.get("dict_url", "")
            print("    %-30s" % name)
            print("       URL :", str(md)[:110])
            print("       SHA :", sh)
            if du:
                print("       dict:", str(du)[:110])
            res["ppocrv6"].setdefault(kind, {})[name] = {
                "url": md, "declared_sha256": sh, "dict_url": du}

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n已写:", OUT)
print("\n=== 与 PaddleOCR 侧的可比性初判 ===")
print("  PaddleOCR 实际用: PP-OCRv6_medium (det 61.96MB / rec 76.47MB, .pdiparams)")
print("  RapidOCRLite 默认: model_type=small, ocr_version=PP-OCRv6 (config.yaml L145)")
print("  → 档位不等：medium vs small。可统一后再比")
print("  → 格式不等：.pdiparams vs .onnx → SHA256 跨格式不可比")
