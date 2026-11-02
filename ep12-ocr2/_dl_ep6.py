# -*- coding: utf-8 -*-
"""下载 ep6 两个模型（用户已批准 4.5GB）
- rupeshs/sdxs-512-0.9-openvino   2.81 GB  (openrail++)
- stabilityai/sd-turbo            fp16 1651.7 MB (Stability AI Community License, <$1M 可商用)
"""
import os, sys, time, json, pathlib

os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HF_HUB_DISABLE_XET"] = "1"

DEST = r"D:/models"
os.makedirs(DEST, exist_ok=True)

from huggingface_hub import snapshot_download

TARGETS = [
    ("rupeshs/sdxs-512-0.9-openvino", None),
    ("stabilityai/sd-turbo",
     ["*.fp16*", "text_encoder*", "tokenizer*", "scheduler*", "model_index.json",
      "config.json", "*.json", "*.txt"]),
]

log = []
for rid, inc in TARGETS:
    t0 = time.time()
    print("=" * 70, flush=True)
    print("下载 %s  allow_patterns=%s" % (rid, inc), flush=True)
    try:
        p = snapshot_download(
            repo_id=rid, local_dir=os.path.join(DEST, rid.replace("/", "__")),
            allow_patterns=inc, max_workers=2)
        el = time.time() - t0
        # 实际字节
        tot = sum(f.stat().st_size for f in pathlib.Path(p).rglob("*") if f.is_file())
        print("OK %s -> %s | %.2f MB | %.1f s" % (rid, p, tot / 1048576, el), flush=True)
        log.append({"repo": rid, "path": p, "mb": round(tot / 1048576, 2),
                    "sec": round(el, 1), "status": "ok"})
    except Exception as e:
        print("FAIL %s: %r" % (rid, e), flush=True)
        log.append({"repo": rid, "status": "fail", "err": repr(e)[:400]})

out = pathlib.Path(r"D:/models/_ep6_download_log.json")
out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n日志:", out, flush=True)
print(json.dumps(log, ensure_ascii=False, indent=2), flush=True)
