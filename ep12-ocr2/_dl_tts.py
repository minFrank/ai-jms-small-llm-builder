# -*- coding: utf-8 -*-
"""方案 B：下载 VoxCPM2 + MOSS-TTS-Nano 权重（引擎代码已在 VoiceStudio，只差权重）"""
import os, sys, time, json, pathlib

os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HF_HUB_DISABLE_XET"] = "1"

DEST = pathlib.Path(r"D:/models/tts")
DEST.mkdir(parents=True, exist_ok=True)
log = []

from huggingface_hub import snapshot_download

TARGETS = [
    ("openbmb/VoxCPM2", "voxcpm2"),
    ("OpenMOSS-Team/MOSS-TTS-Nano-100M", "moss-tts-nano-100m"),
]
for rid, sub in TARGETS:
    t0 = time.time()
    print("=" * 72, flush=True)
    print("下载 %s" % rid, flush=True)
    try:
        p = snapshot_download(repo_id=rid, local_dir=str(DEST / sub), max_workers=2)
        el = time.time() - t0
        tot = sum(f.stat().st_size for f in pathlib.Path(p).rglob("*") if f.is_file())
        print("OK %s -> %.2f GB | %.1f s" % (rid, tot / 1073741824, el), flush=True)
        log.append({"repo": rid, "path": p, "gb": round(tot / 1073741824, 3),
                    "sec": round(el, 1), "status": "ok"})
    except Exception as e:
        print("FAIL %s: %r" % (rid, e), flush=True)
        log.append({"repo": rid, "status": "fail", "err": repr(e)[:400]})

out = pathlib.Path(r"D:/models/tts/_download_log.json")
out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n=== 汇总 ===", flush=True)
print(json.dumps(log, ensure_ascii=False, indent=2), flush=True)
gb = sum(x.get("gb", 0) for x in log if x.get("status") == "ok")
print("成功下载合计: %.2f GB" % gb, flush=True)
