"""STEP 0 manifest 门：导出 RapidOCRLite 两个配置的权重清单。

目的：为核心命题（同一套 PP-OCRv6、三个栈比快慢）提供 SHA256 / 输入尺寸 / 字典三项比对素材。
只读采集，不跑测量。
"""
import hashlib
import json
import os
import pathlib
import sys

PKG = pathlib.Path(sys.prefix) / "Lib" / "site-packages" / "rapidocr"
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/manifest_rapidocrlite.json")


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root: pathlib.Path):
    rows = []
    if not root.exists():
        return rows
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix in (".onnx", ".json", ".txt", ".yaml", ".yml"):
            rows.append({
                "rel": str(f.relative_to(PKG)).replace("\\", "/"),
                "mb": round(f.stat().st_size / 1e6, 3),
                "sha256": sha256_of(f),
            })
    return rows


result = {"engine": "RapidOCRLite", "import_name": "rapidocr",
          "pkg_dir": str(PKG), "configs": {}}

# 配置一：lite（内置 Indra 权限，OpenRAIL-M）
lite_root = PKG / "models" / "lite"
lite_files = scan(lite_root)
meta = None
mp = lite_root / "meta.json"
if mp.exists():
    raw = json.loads(mp.read_text(encoding="utf-8"))
    meta = {k: (v if k != "vocab" else "<vocab 字典，%d 字符>" % len(json.loads(v).get("chars", [])))
            for k, v in raw.items()}
    # 真实字典长度与哈希（比对要用真值，不用占位）
    try:
        vocab = json.loads(raw["vocab"])
        chars = vocab.get("chars", [])
        meta["vocab_len"] = len(chars)
        meta["vocab_sha256_"] = hashlib.sha256(
            json.dumps(chars, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        meta["vocab_first20"] = chars[:20]
        meta["vocab_cjk_count"] = sum(1 for c in chars if "\u4e00" <= c <= "\u9fff")
    except Exception as e:
        meta["vocab_parse_err"] = str(e)

result["configs"]["lite"] = {
    "desc": "内置 Indra OCR 权重（datalab-to/indra-ocr）",
    "license": "AI PUBS OPEN RAIL-M LICENSE (MODIFIED) —— 非 Apache-2.0，限商用",
    "det_long_side": meta.get("det_long_side") if meta else None,
    "files": lite_files,
    "meta": meta,
}

# 配置二：默认 PP-OCRv6（Apache-2.0，缺的按 default_models.yaml 从 ModelScope 下载）
ppocr_root = PKG / "models"
ppocr_files = [r for r in scan(ppocr_root) if not r["rel"].startswith("lite/")]
dm = PKG / "default_models.yaml"
result["configs"]["ppocrv6"] = {
    "desc": "官方 PP-OCRv6 tiny/small/medium ONNX",
    "license": "Apache-2.0（来源 PaddleOCR 生态）",
    "default_models_yaml_exists": dm.exists(),
    "default_models_yaml_sha256": sha256_of(dm) if dm.exists() else None,
    "bundled_files": ppocr_files,
    "note": "缺失模型按 default_models.yaml 从 ModelScope 下载，落 Global.model_root_dir，校验 SHA256",
}

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("已写:", OUT, OUT.stat().st_size, "字节")
print("\n=== lite 配置 ===")
print("  det_long_side:", result["configs"]["lite"]["det_long_side"])
print("  权重文件:")
for r in lite_files:
    print("    %-22s %7.3f MB  %s" % (r["rel"], r["mb"], r["sha256"][:24]))
if meta:
    print("  字典长度:", meta.get("vocab_len"), " 其中 CJK:", meta.get("vocab_cjk_count"))
    print("  字典 sha256:", str(meta.get("vocab_sha256_"))[:32])
    print("  字典前 20:", meta.get("vocab_first20"))
print("\n=== PP-OCRv6 配置 ===")
print("  default_models.yaml 存在:", result["configs"]["ppocrv6"]["default_models_yaml_exists"])
print("  已内置文件数:", len(ppocr_files))
for r in ppocr_files:
    print("    %-34s %7.3f MB" % (r["rel"], r["mb"]))
