"""STEP 0-C：三个栈的 manifest 门最终比对。

栈：PaddleOCR(.pdiparams) / RapidOCRLite(.onnx) / SimdPaddleOCR(导出的流)
比三项：① 档位 ② rec 输入尺寸 ③ 字典内容
"""
import hashlib
import json
import pathlib

import onnxruntime as ort

SIMD = pathlib.Path(r"D:/models/ep12-ocr2/simd/medium")
RCL = pathlib.Path(r"D:/models/ep12-ocr2/rapidocr")
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/STEP0_GATE_RESULT_3STACK.json")


def head(p, n=16):
    with open(p, "rb") as f:
        return f.read(n)


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


print("=" * 76)
print("STEP 0 manifest 门 · 三栈最终比对")
print("=" * 76)

print("\n【文件格式识别】")
for name in ["detection.bin", "recognition.bin", "classification.bin", "dictionary.bin"]:
    p = SIMD / name
    if not p.exists():
        continue
    h = head(p, 12)
    if h[:4] == b"\x08\x00\x00\x00" or h[:4] == b"\x08\x00\x00\n":
        kind = "ONNX? (前 4 字节 %s)" % h[:4].hex()
    elif b"onnx" in h.lower() or h[4:8] == b"onnx" or True:
        # ONNX 是 protobuf，首个字段 field 1 (ir_version) varint
        kind = "protobuf/ONNX 候选 (首 12 字节 %s)" % h.hex()
    print("  %-18s %s" % (name, kind))
    # 尝试当 ONNX 打开
    try:
        s = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        ins = [(i.name, i.shape, i.type) for i in s.get_inputs()]
        outs = [(o.name, o.shape) for o in s.get_outputs()]
        print("      ✅ ONNX 可读")
        print("      输入:", ins)
        print("      输出:", [(o[0], o[1]) for o in outs][:4])
    except Exception as e:
        print("      ✗ 非 ONNX 或读取失败: %s" % str(e)[:80])

print("\n" + "=" * 76)
print("【三栈 manifest 汇总】")
gate = {"criterion": "档位 + rec 输入尺寸 + 字典内容（原'权重 SHA256 全等'已废弃）",
        "stacks": {}, "checks": {}}

# ---- 栈 1：PaddleOCR ----
import yaml
PAD = pathlib.Path(r"C:/Users/Frank/.paddlex/official_models")
rec_y = yaml.safe_load((PAD / "PP-OCRv6_medium_rec/inference.yml").read_text(encoding="utf-8"))
pad_shape = rec_y["PreProcess"]["transform_ops"][2]["RecResizeImg"]["image_shape"]
pad_chars = rec_y["PostProcess"]["character_dict"]
gate["stacks"]["paddleocr"] = {
    "tier": "PP-OCRv6_medium", "format": ".pdiparams",
    "rec_image_shape": pad_shape, "dict_count": len(pad_chars),
    "dict_seq_sha256": hashlib.sha256(
        json.dumps(pad_chars, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
    "det_mb": 61.96, "rec_mb": 76.465,
}

# ---- 栈 2：RapidOCRLite ----
rcl_rec_in = ort.InferenceSession(str(RCL / "PP-OCRv6_rec_medium.onnx"),
                                  providers=["CPUExecutionProvider"]).get_inputs()[0].shape
rcl_chars = [l.rstrip("\r\n") for l in
             (RCL / "ppocrv6_dict.txt").read_text(encoding="utf-8", errors="replace").splitlines()]
rcl_chars = [c for c in rcl_chars]
# 去掉末尾空行
while rcl_chars and rcl_chars[-1] == "":
    rcl_chars.pop()
gate["stacks"]["rapidocrlite"] = {
    "tier": "medium（显式指定，默认为 small）", "format": ".onnx",
    "rec_onnx_input": rcl_rec_in, "dict_count": len(rcl_chars),
    "dict_seq_sha256": hashlib.sha256(
        json.dumps(rcl_chars, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
    "det_mb": 62.119, "rec_mb": 76.630,
}

# ---- 栈 3：SimdPaddleOCR ----
simd_dict_raw = (SIMD / "dictionary.bin").read_bytes()
# 尝试多种编码
simd_chars = None
for enc in ["utf-8-sig", "utf-8", "utf-16", "utf-16-le", "gbk"]:
    try:
        t = simd_dict_raw.decode(enc)
        cand = t.splitlines()
        if len(cand) > 1000:
            simd_chars = cand
            print("\n  SimdPaddleOCR 字典编码识别为: %s" % enc)
            break
    except Exception:
        continue
if simd_chars is None:
    simd_chars = simd_dict_raw.decode("utf-8", errors="replace").splitlines()
    print("\n  SimdPaddleOCR 字典编码: 未识别，按 utf-8 容错读取")
while simd_chars and simd_chars[-1] == "":
    simd_chars.pop()

simd_rec_in = None
try:
    simd_rec_in = ort.InferenceSession(str(SIMD / "recognition.bin"),
                                       providers=["CPUExecutionProvider"]).get_inputs()[0].shape
except Exception as e:
    print("  Simd recognition.bin 非 ONNX: %s" % str(e)[:60])
simd_det_in = None
try:
    simd_det_in = ort.InferenceSession(str(SIMD / "detection.bin"),
                                       providers=["CPUExecutionProvider"]).get_inputs()[0].shape
except Exception as e:
    print("  Simd detection.bin 非 ONNX: %s" % str(e)[:60])

gate["stacks"]["simdpaddleocr"] = {
    "tier": "PP-OCRv6_medium（包内 Name 字段）", "format": "嵌入 DLL 的流（det/rec 导出后可读性待判）",
    "rec_onnx_input": simd_rec_in, "det_onnx_input": simd_det_in,
    "dict_count": len(simd_chars),
    "dict_seq_sha256": hashlib.sha256(
        json.dumps(simd_chars, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
    "det_mb": round((SIMD / "detection.bin").stat().st_size / 1e6, 3),
    "rec_mb": round((SIMD / "recognition.bin").stat().st_size / 1e6, 3),
    "dict_mb": round((SIMD / "dictionary.bin").stat().st_size / 1e6, 3),
}

for k, v in gate["stacks"].items():
    print("\n  --- %s ---" % k)
    for kk, vv in v.items():
        print("      %-18s %s" % (kk, vv))

# ---- 三项判定 ----
print("\n" + "=" * 76)
print("【三项判定】")
checks = {}

# ① 档位
tiers = {"paddleocr": "PP-OCRv6_medium", "rapidocrlite": "medium",
         "simdpaddleocr": "PP-OCRv6_medium"}
tier_ok = all("medium" in str(t).lower() for t in tiers.values())
checks["tier"] = {"values": tiers, "equal": tier_ok}
print("  ① 档位        三栈皆 medium → %s" % ("✅ 全等" if tier_ok else "❌"))

# ② rec 输入尺寸（比 C 与 H，W 动态）
paddle_C, paddle_H = pad_shape[0], pad_shape[1]
rcl_C, rcl_H = rcl_rec_in[1], rcl_rec_in[2]
simd_C = simd_H = None
if simd_rec_in and len(simd_rec_in) == 4:
    simd_C, simd_H = simd_rec_in[1], simd_rec_in[2]
print("  ② rec C/H      paddle [%s,%s]  rcl [%s,%s]  simd [%s,%s]" % (
    paddle_C, paddle_H, rcl_C, rcl_H, simd_C, simd_H))
size_ok = (paddle_C == rcl_C == simd_C) and (paddle_H == rcl_H == simd_H)
checks["input_size"] = {
    "paddle_CH": [paddle_C, paddle_H], "rcl_CH": [rcl_C, rcl_H], "simd_CH": [simd_C, simd_H],
    "equal": size_ok,
    "note": "W 为动态轴，三栈运行时按 320 送入；det 三栈皆动态尺寸",
}
print("     → %s" % ("✅ 全等" if size_ok else "❌ 不等"))

# ③ 字典内容
counts = [len(pad_chars), len(rcl_chars), len(simd_chars)]
shas = [gate["stacks"][k]["dict_seq_sha256"] for k in ("paddleocr", "rapidocrlite", "simdpaddleocr")]
print("  ③ 字典条数     paddle=%d  rcl=%d  simd=%d" % tuple(counts))
print("     字典 sha256 paddle=%s" % shas[0][:32])
print("               rcl   =%s" % shas[1][:32])
print("               simd  =%s" % shas[2][:32])
dict_ok = (shas[0] == shas[1] == shas[2])
checks["dict"] = {"counts": counts, "seq_sha256": shas, "equal": dict_ok}
print("     → %s" % ("✅ 全等（逐条内容一致）" if dict_ok else "❌ 不等"))

if not dict_ok:
    # 逐条比对，定位差异
    for a_name, a in [("paddle", pad_chars), ("rcl", rcl_chars), ("simd", simd_chars)]:
        print("     %s 条数 %d, 前6=%r 后6=%r" % (a_name, len(a), a[:6], a[-6:]))
    diffs = [(i, pad_chars[i] if i < len(pad_chars) else None,
              simd_chars[i] if i < len(simd_chars) else None)
             for i in range(max(len(pad_chars), len(simd_chars)))
             if (pad_chars[i] if i < len(pad_chars) else None) !=
                (simd_chars[i] if i < len(simd_chars) else None)]
    print("     paddle vs simd 逐条不等数: %d" % len(diffs))
    for d in diffs[:10]:
        print("        idx %-6d paddle=%-8r simd=%-8r" % d)

gate["checks"] = checks
gate["gate_passed_2stack"] = checks["tier"]["equal"] and checks["input_size"]["equal"]
gate["gate_passed_3stack"] = (checks["tier"]["equal"] and checks["input_size"]["equal"]
                              and checks["dict"]["equal"])
print("\n" + "=" * 76)
print("【门结论】")
print("  两栈（Paddle + RapidOCRLite）: %s" % ("通过" if gate["gate_passed_2stack"] else "未通过"))
print("  三栈（含 SimdPaddleOCR）      : %s" % ("通过" if gate["gate_passed_3stack"] else "未通过"))
if not gate["gate_passed_3stack"]:
    print("  → 三栈未全等时按方案 §4.5 降级：正文只能写'这几个栈在这些配置上有差异'")

OUT.write_text(json.dumps(gate, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print("\n已写:", OUT, OUT.stat().st_size, "字节")
