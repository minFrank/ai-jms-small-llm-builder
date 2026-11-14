#!/usr/bin/env python3
"""ep13 P0 模型下载（规格 V6d）：7 个已确认 repo → D:/models/models/ocr/ep13-docparse/
进度与结果写 download.log；逐个重试 2 次；surya 待核不在此列。"""
import os, time, json, traceback, shutil

DEST = r"D:/models/models/ocr/ep13-docparse"
LOG = os.path.join(DEST, "download.log")
MANIFEST = os.path.join(DEST, "MANIFEST.json")

MODELS = [
    ("OXR-1.0",              "SoMarkAI/OXR-1.0"),
    ("Xiaomi-OCR-0",         "xiaomi-research/Xiaomi-OCR-0"),
    ("PaddleOCR-VL-1.6",     "PaddlePaddle/PaddleOCR-VL-1.6"),
    ("OvisOCR2",             "ATH-MaaS/OvisOCR2"),
    ("TeleOCR",              "XingChen-AGI/TeleOCR"),
    ("MonkeyOCR-pro-1.2B",   "echo840/MonkeyOCR-pro-1.2B"),
    ("dots.ocr",             "rednote-hilab/dots.ocr"),
]

def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def size(p):
    return sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(p) for x in fs)

def main():
    from huggingface_hub import snapshot_download
    os.makedirs(DEST, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST):
        try: manifest = json.load(open(MANIFEST, encoding="utf-8"))
        except: manifest = {}
    results = []
    for name, repo in MODELS:
        local = os.path.join(DEST, name)
        # 只认 MANIFEST 记录的完整下载（防半成品被 SKIP——0.88/3.2GB 教训）
        rec = manifest.get(name)
        if rec and os.path.isdir(local) and size(local) >= 0.95 * rec.get("size_bytes", 0) and rec.get("size_bytes", 0) > 1e8:
            log("SKIP %s（manifest 完整 %.2f GB）" % (name, size(local)/1e9))
            results.append((name, "skip", size(local)))
            continue
        if os.path.isdir(local):
            log("CLEAR %s（半成品/无 manifest，%.2f GB，删除重下）" % (name, size(local)/1e9))
            shutil.rmtree(local, ignore_errors=True)
        ok = False
        for attempt in (1, 2):
            try:
                log("GET %s ← %s（第 %d 次）" % (name, repo, attempt))
                t0 = time.time()
                snapshot_download(repo_id=repo, local_dir=local,
                                  max_workers=4,
                                  ignore_patterns=["*.gguf", "*.bin.quant", "onnx/*"])
                dt = time.time() - t0
                sz = size(local)
                log("DONE %s %.2f GB 用时 %.0fs" % (name, sz/1e9, dt))
                manifest[name] = {"repo": repo, "path": local, "size_bytes": sz,
                                  "downloaded_at": time.strftime("%Y-%m-%d %H:%M"),
                                  "source_url": "https://huggingface.co/" + repo}
                json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                results.append((name, "ok", sz))
                ok = True
                break
            except Exception as e:
                log("FAIL %s 第%d次: %s" % (name, attempt, str(e)[:200]))
                time.sleep(5)
        if not ok:
            results.append((name, "fail", 0))
    log("==== 全部完成 ====")
    for n, s, b in results:
        log("  %-24s %-5s %.2f GB" % (n, s, b/1e9))
    # 汇总 + 磁盘检查
    d_free = shutil.disk_usage("D:/").free / 1e9
    total = sum(b for _, s, b in results if s in ("ok", "skip")) / 1e9
    log("模型合计 %.2f GB | D 盘剩余 %.0f GB" % (total, d_free))
    fails = [n for n, s, _ in results if s == "fail"]
    log("FAILS: %s" % (fails if fails else "无"))
    return 1 if fails else 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        log("FATAL: " + traceback.format_exc()[-500:])
        raise SystemExit(2)
