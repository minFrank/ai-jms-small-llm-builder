"""STEP 1 冒烟：Ollama 原生 /api/generate 跑 GLM-OCR，2 张图回算耗时与内存峰值。

目的（方案 §5）：拿到 GLM-OCR 在本机的真实单页耗时与内存峰值，
据此定全批排期、该引擎的超时值与内存阈值。

选图：skew_01（ep11 实测最慢类别）+ table_01（表格，结构最重）。
设硬超时与看门狗：超时即杀，不留孤儿。
"""
import base64
import json
import os
import pathlib
import threading
import time

import psutil
import requests

IMG_DIR = pathlib.Path(
    r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples")
OUT = pathlib.Path(r"D:/models/ollama/smoke_result.json")
API = "http://127.0.0.1:11434/api/generate"
MODEL = "glm-ocr:latest"
# 硬超时：按方案 §4.2，B 组新引擎先设保守上限 1800s，超时即杀
HARD_TIMEOUT_S = 1800
IMAGES = ["skew_01.png", "table_01.png"]

proc = psutil.Process()  # 占位，实际按子进程树采


def find_ollama_procs():
    """从 ollama.exe serve 出发递归整棵子进程树。

    ⚠️ 不能按"进程名含 ollama"匹配 —— 推理由 llama-server.exe 承担，
    它的名字不含 'ollama'，按名字匹配会整棵漏掉（实测漏 3958.7 MB / 83.6 倍）。
    """
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            nm = (p.info["name"] or "").lower()
            if nm == "ollama.exe" and any("serve" in str(c) for c in (p.info["cmdline"] or [])):
                out.append(p)
                out.extend(p.children(recursive=True))
        except Exception:
            pass
    return out


def sample_rss(stop_evt, buf, interval=0.2):
    """每 200 ms 采一次全部 ollama 进程 RSS，记最大和（整棵进程树 Working Set）。"""
    peak = 0
    samples = 0
    while not stop_evt.is_set():
        total = 0
        for p in find_ollama_procs():
            try:
                total += p.memory_info().rss
            except Exception:
                pass
        if total > peak:
            peak = total
        samples += 1
        buf["peak"] = peak
        buf["samples"] = samples
        time.sleep(interval)


def run_one(img_name, session, results):
    p = IMG_DIR / img_name
    if not p.exists():
        print("  缺图:", p)
        return
    b64 = base64.b64encode(p.read_bytes()).decode()
    print("\n  --- %s (%.0f KB) ---" % (img_name, p.stat().st_size / 1024))

    buf = {"peak": 0, "samples": 0}
    stop = threading.Event()
    th = threading.Thread(target=sample_rss, args=(stop, buf), daemon=True)
    th.start()

    t0 = time.time()
    status = "ok"
    text = ""
    eval_count = None
    err = None
    try:
        r = session.post(API, json={
            "model": MODEL,
            "prompt": "Read all the text in this image.",
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.0},
        }, timeout=HARD_TIMEOUT_S)
        dt = time.time() - t0
        if r.status_code != 200:
            status = "http_%d" % r.status_code
            err = r.text[:300]
            print("  HTTP %d: %s" % (r.status_code, r.text[:200]))
        else:
            d = r.json()
            text = d.get("response", "")
            eval_count = d.get("eval_count")
            print("  耗时 %.1fs | eval_count=%s | 文本 %d 字" % (dt, eval_count, len(text)))
            print("  首 120 字: %s" % text[:120].replace("\n", " ⏎ "))
    except requests.exceptions.Timeout:
        dt = time.time() - t0
        status = "timeout"
        err = "硬超时 %ds 被杀" % HARD_TIMEOUT_S
        print("  ❌ 硬超时 %.0fs，已中止" % dt)
    except Exception as e:
        dt = time.time() - t0
        status = "error"
        err = "%s: %s" % (e.__class__.__name__, str(e)[:200])
        print("  ❌ %s" % err)
    finally:
        stop.set()
        th.join(timeout=3)

    results[img_name] = {
        "image": img_name,
        "status": status,
        "t_s": round(dt, 2),
        "peak_rss_mb": round(buf["peak"] / 1e6, 1),
        "samples": buf["samples"],
        "eval_count": eval_count,
        "text_len": len(text),
        "text_head": text[:600],
        "err": err,
    }
    print("  → 耗时 %.1fs | RSS 峰值 %.0f MB（%d 次采样）"
          % (dt, buf["peak"] / 1e6, buf["samples"]))


def main():
    print("=" * 70)
    print("STEP 1 冒烟 · GLM-OCR via Ollama（CPU）")
    print("=" * 70)
    print("  API  :", API)
    print("  模型 :", MODEL)
    print("  硬超时: %d s" % HARD_TIMEOUT_S)
    print("  处理器数:", os.cpu_count())
    # 空闲内存
    vm = psutil.virtual_memory()
    print("  内存: 总 %.1f GB / 可用 %.1f GB" % (vm.total / 1e9, vm.available / 1e9))

    results = {}
    s = requests.Session()
    for img in IMAGES:
        run_one(img, s, results)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已写:", OUT)

    ok = [v for v in results.values() if v["status"] == "ok"]
    print("\n" + "=" * 70)
    print("【冒烟结论】")
    print("  成功 %d / %d" % (len(ok), len(results)))
    if ok:
        ts = [v["t_s"] for v in ok]
        rss = [v["peak_rss_mb"] for v in ok]
        print("  单页耗时: min %.1fs  max %.1fs" % (min(ts), max(ts)))
        print("  RSS 峰值: min %.0f MB  max %.0f MB (%.2f GB)" % (min(rss), max(rss), max(rss) / 1024))
        print("  → 全批 24 张 × n=3 按最慢单页估算: %.1f min" % (max(ts) * 24 * 3 / 60))
        print("  → 内存阈值（峰值 ×1.3）: %.2f GB" % (max(rss) * 1.3 / 1024))


if __name__ == "__main__":
    main()
