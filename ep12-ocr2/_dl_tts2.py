# -*- coding: utf-8 -*-
"""方案一新增两个模型下载：VoxCPM-0.5B + MegaTTS3（合计约 5.48 GB）"""
import os, time, json, pathlib

os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HF_HUB_DISABLE_XET"] = "1"

DEST = pathlib.Path(r"D:/models/tts")
DEST.mkdir(parents=True, exist_ok=True)
log = []

from huggingface_hub import snapshot_download

TARGETS = [
    ("openbmb/VoxCPM-0.5B", "voxcpm-0.5b"),
    ("ByteDance/MegaTTS3", "megatts3"),
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

out = pathlib.Path(r"D:/models/tts/_download_log2.json")
out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n=== 汇总 ===", flush=True)
print(json.dumps(log, ensure_ascii=False, indent=2), flush=True)
print("本轮合计: %.2f GB" % sum(x.get("gb", 0) for x in log if x.get("status") == "ok"), flush=True)
