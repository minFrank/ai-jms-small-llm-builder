import json, os, subprocess, sys, hashlib, time
BASE = os.path.dirname(os.path.abspath(__file__))
PY = "D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
PYG = "D:/models/ocr/got-venv/Scripts/python.exe"


def ver(mod):
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "?")
    except Exception as e:
        return "NOT_IMPORTABLE: %s" % type(e).__name__


snap = {"ts": time.time(), "python": sys.version}
for mod in ("cv2", "numpy", "onnxruntime", "torch", "transformers", "psutil",
            "PIL", "paddle", "paddleocr", "rapidocr_onnxruntime", "pypdfium2"):
    snap[mod] = ver(mod)
try:
    import psutil
    cpu = psutil.cpu_count(logical=False), psutil.cpu_count(logical=True)
    snap["cpu_physical_logical"] = list(cpu)
    snap["mem_total_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
except Exception:
    pass
snap["venv"] = PY
snap["got_venv"] = PYG
snap["got_venv_packages"] = subprocess.run(
    [PYG, "-m", "pip", "list", "--format=freeze"], capture_output=True,
    text=True, encoding="utf-8", errors="replace").stdout.strip().splitlines()
snap["torch_cuda_available"] = None
try:
    import torch
    snap["torch_cuda_available"] = torch.cuda.is_available()
except Exception:
    pass
with open(os.path.join(BASE, "env_snapshot.json"), "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, indent=1)
for p, name in ((PY, "freeze_main.txt"), (PYG, "freeze_got.txt")):
    r = subprocess.run([p, "-m", "pip", "freeze"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    open(os.path.join(BASE, name), "w", encoding="utf-8").write(r.stdout)
    print(name, "sha256", hashlib.sha256(r.stdout.encode()).hexdigest()[:16],
          len(r.stdout.splitlines()), "pkgs")
print(json.dumps({k: v for k, v in snap.items() if k in
                  ("cv2", "numpy", "onnxruntime", "torch", "transformers",
                   "paddle", "paddleocr", "rapidocr_onnxruntime")},
                 ensure_ascii=False))
