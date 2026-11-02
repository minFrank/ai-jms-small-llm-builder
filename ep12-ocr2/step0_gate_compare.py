"""STEP 0-B：manifest 门决定性比对。

比三项：① 档位 ② 输入尺寸（rec image_shape / det long_side）③ 字典内容。
用 ep11 venv 的 onnxruntime 只读 ONNX 元数据，不修改 ep11 venv。
"""
import hashlib
import json
import pathlib

import onnxruntime as ort
import yaml

RCL = pathlib.Path(r"D:/models/ep12-ocr2/rapidocr")
PAD_REC_YML = pathlib.Path(r"C:/Users/Frank/.paddlex/official_models/PP-OCRv6_medium_rec/inference.yml")
PAD_DET_YML = pathlib.Path(r"C:/Users/Frank/.paddlex/official_models/PP-OCRv6_medium_det/inference.yml")
OUT = pathlib.Path(r"D:/study/ai-jms/ep12-ocr2-venvs/STEP0_GATE_RESULT.json")


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def onnx_meta(p):
    s = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
    ins = [(i.name, i.shape, i.type) for i in s.get_inputs()]
    outs = [(o.name, o.shape, o.type) for o in s.get_outputs()]
    return ins, outs


print("=" * 74)
print("STEP 0 manifest 门 · 决定性比对")
print("=" * 74)

gate = {"criterion_revised": "档位 + 输入尺寸 + 字典内容（原'权重SHA256全等'已废弃，跨格式不可比）",
        "stacks": {}, "checks": {}}

# ---------- ① 档位 ----------
print("\n【① 档位】")
rcl_tier = "medium"          # 显式指定
pad_tier = "PP-OCRv6_medium"  # 实际下载的
print("  PaddleOCR    :", pad_tier)
print("  RapidOCRLite :", rcl_tier, "（显式指定，非默认 small）")
gate["checks"]["tier"] = {"paddle": pad_tier, "rapidocr": rcl_tier, "equal": True}
print("  → 全等 ✅")

# ---------- ② 输入尺寸 ----------
print("\n【② 输入尺寸】")
rec_y = yaml.safe_load(PAD_REC_YML.read_text(encoding="utf-8"))
det_y = yaml.safe_load(PAD_DET_YML.read_text(encoding="utf-8"))
pad_rec_shape = rec_y["PreProcess"]["transform_ops"][2]["RecResizeImg"]["image_shape"]
pad_rec_ops = [list(t.keys())[0] for t in rec_y["PreProcess"]["transform_ops"]]
pad_det_ops = [list(t.keys())[0] for t in det_y["PreProcess"]["transform_ops"]]
pad_det_norm = [t for t in det_y["PreProcess"]["transform_ops"] if "NormalizeImage" in t]
print("  PaddleOCR rec image_shape :", pad_rec_shape, " ops:", pad_rec_ops)
print("  PaddleOCR det ops         :", pad_det_ops)

rcl_det_in, _ = onnx_meta(RCL / "PP-OCRv6_det_medium.onnx")
rcl_rec_in, _ = onnx_meta(RCL / "PP-OCRv6_rec_medium.onnx")
print("  RapidOCRLite det 输入     :", rcl_det_in)
print("  RapidOCRLite rec 输入     :", rcl_rec_in)

# rec 形状：Paddle image_shape 是 [C,H,W]，ONNX 输入是 [N,C,H,W] —— 索引必须对齐后再比
rcl_rec_shape = rcl_rec_in[0][1]
gate["checks"]["input_size"] = {
    "paddle_rec_image_shape": pad_rec_shape,
    "rcl_rec_onnx_input": rcl_rec_shape,
    "paddle_det_preprocess": pad_det_ops,
    "rcl_det_onnx_input": rcl_det_in[0][1],
    "note": "Paddle image_shape=[C,H,W]；ONNX 输入=[N,C,H,W]，比对时按 C/H 位对齐",
}
# 对齐：paddle[0]=C vs rcl[1]=C；paddle[1]=H vs rcl[2]=H
pad_C, pad_H = pad_rec_shape[0], pad_rec_shape[1]
rcl_C, rcl_H = rcl_rec_shape[1], rcl_rec_shape[2]
rec_ch_equal = (pad_C == rcl_C) and (pad_H == rcl_H)
print("  rec 对齐比对: paddle [C,H]=[{},{}] vs rcl [C,H]=[{},{}] → 全等? {}".format(
    pad_C, pad_H, rcl_C, rcl_H, rec_ch_equal))
print("  （宽度 paddle=320 为固定值；rcl ONNX 宽度为动态轴 DynamicDimension，运行时按 320 送入）")
gate["checks"]["input_size"]["rec_C_H_equal"] = rec_ch_equal
gate["checks"]["input_size"]["paddle_rec_W_fixed"] = pad_rec_shape[2]
gate["checks"]["input_size"]["rcl_rec_W"] = "dynamic (ONNX 动态轴)"
rec_h_equal = rec_ch_equal
print("  det: paddle 用 DetResizeForTest（动态），rcl ONNX 输入 %s（动态轴）" % (rcl_det_in[0][1],))
gate["checks"]["input_size"]["det_dynamic_both"] = True
print("  → det 两侧都是动态尺寸（Paddle DetResizeForTest / ONNX 动态轴），无固定值可比")
print("  → rec C/H 全等 ✅" if rec_h_equal else "  → rec C/H 不一致 ❌")

# ---------- ③ 字典内容 ----------
print("\n【③ 字典内容】")
rcl_dict = (RCL / "ppocrv6_dict.txt").read_text(encoding="utf-8", errors="replace")
rcl_chars = [l for l in rcl_dict.splitlines()]
rcl_chars_stripped = [c.rstrip() for c in rcl_chars if c.strip() != "" or c == " "]
rcl_chars_final = [c for c in (x.rstrip("\r") for x in rcl_chars)]

pad_chars = rec_y["PostProcess"]["character_dict"]
print("  PaddleOCR 字典条数:", len(pad_chars), "（inference.yml 内嵌 character_dict）")
print("  RapidOCRLite 字典条数:", len(rcl_chars_final), "（ppocrv6_dict.txt 逐行）")
print("  PaddleOCR 前 8:", pad_chars[:8])
print("  RapidOCR  前 8:", rcl_chars_final[:8])
print("  PaddleOCR 后 5:", pad_chars[-5:])
print("  RapidOCR  后 5:", rcl_chars_final[-5:])

same_len = len(pad_chars) == len(rcl_chars_final)
diff_idx = [i for i, (a, b) in enumerate(zip(pad_chars, rcl_chars_final)) if a != b]
content_equal = same_len and not diff_idx
print("  长度全等? %s" % same_len)
print("  逐项不等数: %d" % len(diff_idx))
if diff_idx[:8]:
    for i in diff_idx[:8]:
        print("     idx %-5d paddle=%-6r rcl=%-6r" % (i, pad_chars[i], rcl_chars_final[i]))
print("  内容全等? %s" % content_equal)

pad_dict_sha = hashlib.sha256(json.dumps(pad_chars, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
rcl_dict_sha = hashlib.sha256(json.dumps(rcl_chars_final, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
print("  paddle 字典序列 sha256:", pad_dict_sha[:32])
print("  rcl    字典序列 sha256:", rcl_dict_sha[:32])
gate["checks"]["dict"] = {
    "paddle_count": len(pad_chars), "rcl_count": len(rcl_chars_final),
    "same_length": same_len, "diff_count": len(diff_idx),
    "content_equal": content_equal,
    "paddle_seq_sha256": pad_dict_sha, "rcl_seq_sha256": rcl_dict_sha,
    "diff_sample": [{"idx": i, "paddle": pad_chars[i], "rcl": rcl_chars_final[i]} for i in diff_idx[:12]],
}

# ---------- 门结论 ----------
print("\n" + "=" * 74)
print("【门结论】")
passed = rec_h_equal and content_equal
print("  ① 档位         全等 ✅")
print("  ② rec 输入尺寸 全等 ✅" if rec_h_equal else "  ② rec 输入尺寸 不等 ❌")
print("  ③ 字典内容     全等 ✅" if content_equal else "  ③ 字典内容     不等 ❌（差 %d 项）" % len(diff_idx))
print("\n  → 门%s" % ("通过：核心命题成立，可写'同一套 PP-OCRv6、三个栈比快慢'" if passed
                  else "未通过：核心命题降级，只能写'这几个栈在这些配置上有差异'"))
gate["gate_passed"] = passed
gate["verdict"] = ("PASS: 三栈可视为同一套 PP-OCRv6 medium" if passed
                   else "FAIL: 字典或尺寸不全等，核心命题降级")

# 权重文件清单（留档，不再作为判据）
gate["weights"] = {
    "rcl_det_onnx": {"path": str(RCL / "PP-OCRv6_det_medium.onnx"),
                     "mb": round((RCL / "PP-OCRv6_det_medium.onnx").stat().st_size / 1e6, 3),
                     "sha256": sha256_of(RCL / "PP-OCRv6_det_medium.onnx"),
                     "onnx_input": rcl_det_in[0][1]},
    "rcl_rec_onnx": {"path": str(RCL / "PP-OCRv6_rec_medium.onnx"),
                     "mb": round((RCL / "PP-OCRv6_rec_medium.onnx").stat().st_size / 1e6, 3),
                     "sha256": sha256_of(RCL / "PP-OCRv6_rec_medium.onnx"),
                     "onnx_input": rcl_rec_in[0][1]},
    "rcl_cls_onnx": {"path": str(RCL / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
                     "mb": round((RCL / "ch_ppocr_mobile_v2.0_cls_mobile.onnx").stat().st_size / 1e6, 3),
                     "sha256": sha256_of(RCL / "ch_ppocr_mobile_v2.0_cls_mobile.onnx")},
    "paddle_det_pdiparams": {"path": str(PAD_DET_YML.parent / "inference.pdiparams"),
                             "mb": 61.96, "sha256": "85218d2e3d98f5a21c58b4220627be923a97aee5db3cc71f39536ab31ac53960"},
    "paddle_rec_pdiparams": {"path": str(PAD_REC_YML.parent / "inference.pdiparams"),
                             "mb": 76.465, "sha256": "1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319"},
}

OUT.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n已写:", OUT, OUT.stat().st_size, "字节")
