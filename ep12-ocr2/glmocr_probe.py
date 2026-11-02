import pathlib
import re

import glmocr
from glmocr.config import MaaSApiConfig

root = pathlib.Path(glmocr.__file__).parent
print("=== 包内 ollama / example / deploy 相关文件 ===")
found = []
for f in sorted(root.rglob("*")):
    if f.is_file() and re.search(r"ollama|example|deploy|Modelfile", str(f), re.I):
        found.append(f)
        print("  ", f.relative_to(root), "(%.1f KB)" % (f.stat().st_size / 1024))
if not found:
    print("  （无）")

print("\n=== ocr_client.py 如何调用 OCR 模型 ===")
oc = root / "ocr_client.py"
if oc.exists():
    t = oc.read_text(encoding="utf-8", errors="replace")
    print("  行数:", len(t.split("\n")))
    for i, l in enumerate(t.split("\n")):
        if re.search(r"(requests|aiohttp|httpx|api_url|openai|/v1/|chat/completions|\.post\()", l):
            print("   L%-4d %s" % (i + 1, l.strip()[:120]))
else:
    print("  文件不存在")

print("\n=== MaaS 默认配置（数据上传风险核查）===")
m = MaaSApiConfig()
print("  enabled =", m.enabled, "  ← 默认 True")
print("  api_url =", m.api_url)
print("  model   =", m.model)

print("\n=== 三处 grep 结论 ===")
print("  glmocr SDK 本体无 transformers/vllm/sglang/ollama 本地 OCR 推理代码")
print("  唯一 transformers import 在 layout/layout_detector.py → 版面模型（PP-DocLayout-V3），非 OCR 模型")
print("  → OCR 侧只能走 HTTP(OpenAI 兼容) 或 MaaS 云 API")
