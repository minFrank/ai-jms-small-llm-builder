"""STEP 2-C：PaddleOCR-VL 本机还有没有活路。

两条候选：
  ① Ollama 库里有没有 paddleocr-vl（GLM-OCR 那条已验证可行的路）
  ② vLLM 有没有 CPU 构建，且能否在 AMD 上装（本机 Ryzen 5700G，非 Intel）
"""
import json
import re
import urllib.request

proxy = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
op = urllib.request.build_opener(urllib.request.ProxyHandler(proxy))


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return op.open(r, timeout=45).read().decode("utf-8", "replace")


print("=" * 72)
print("① Ollama 库里有没有 paddleocr-vl")
print("=" * 72)
for q in ["paddleocr", "paddle-ocr", "ppocr", "paddleocr-vl"]:
    try:
        h = get("https://ollama.com/search?q=%s" % q)
        names = sorted(set(re.findall(r'href="/([a-z0-9._-]+/[a-z0-9._-]+)"', h)))
        names = [n for n in names if not n.startswith(("search", "topics", "blog"))][:10]
        print("  q=%-14s → %s" % (q, names if names else "无"))
    except Exception as e:
        print("  q=%-14s 失败 %s" % (q, str(e)[:60]))

print("\n" + "=" * 72)
print("② vLLM 的 CPU 支持状况（本机 AMD Ryzen 5700G）")
print("=" * 72)
try:
    j = json.loads(get("https://pypi.org/pypi/vllm/json"))
    print("  PyPI 最新版:", j["info"]["version"])
    requires = j["info"].get("requires_dist") or []
    torchish = [r for r in requires if re.search(r"torch", r, re.I)][:6]
    print("  torch 相关依赖:", torchish)
    # 有没有单独的 cpu 包
    for pkg in ["vllm-cpu", "vllm_cpu"]:
        try:
            jj = json.loads(get("https://pypi.org/pypi/%s/json" % pkg))
            print("  包 %s 存在, 最新 %s" % (pkg, jj["info"]["version"]))
        except Exception:
            print("  包 %s 在 PyPI 不存在" % pkg)
except Exception as e:
    print("  查询失败:", str(e)[:80])

print("\n  本机 CPU:", end=" ")
try:
    import subprocess
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_Processor).Name"],
                       capture_output=True, text=True, timeout=60)
    print(r.stdout.strip())
except Exception:
    print("?")

print("\n" + "=" * 72)
print("③ paddlex 里 PaddleOCR-VL 的非 genai 路径是否存在")
print("=" * 72)
try:
    import pathlib
    import paddlex
    root = pathlib.Path(paddlex.__file__).parent
    hits = []
    for f in root.rglob("*.py"):
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "PaddleOCRVL" in t or "paddleocr_vl" in t:
            hits.append(str(f.relative_to(root)))
    genai = [h for h in hits if h.startswith("inference/genai")]
    other = [h for h in hits if not h.startswith("inference/genai")]
    print("  命中总数 %d，其中 genai/ 下 %d，其它 %d" % (len(hits), len(genai), len(other)))
    print("  非 genai 的命中（前 12）:")
    for x in other[:12]:
        print("   ", x)
except Exception as e:
    print("  失败:", str(e)[:100])
