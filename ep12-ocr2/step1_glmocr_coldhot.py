"""STEP 1-B：分离 GLM-OCR 的冷启动与热态耗时。

第一轮冒烟 skew_01=121.5s / table_01=18.3s，第二轮 1.2s / 6.6s —— 差 100 倍。
本脚本用受控设计把两个 regime 分开量，不靠推测：

  冷启动：每轮先确认模型未驻留（ollama ps 为空），单张计时
  热态  ：模型驻留后，同张图连跑 n=3，看中位与离散

同时记录 Ollama 的 keep_alive 设置，它决定模型何时被卸载。
"""
import base64
import json
import pathlib
import subprocess
import threading
import time

import psutil
import requests

OLL = r"C:\Users\Frank\AppData\Local\Programs\Ollama\ollama.exe"
API = "http://127.0.0.1:11434/api/generate"
MODEL = "glm-ocr:latest"
IMG_DIR = pathlib.Path(
    r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples")
OUT = pathlib.Path(r"D:/models/ollama/smoke_coldhot.json")
HARD_TIMEOUT_S = 1800


def ollama_ps():
    """返回当前驻留的模型列表（文本）。"""
    try:
        r = subprocess.run([OLL, "ps"], capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip()
    except Exception as e:
        return "ERR " + str(e)[:60]


def tree_rss():
    """从 ollama.exe serve 递归整棵树取 RSS 合计（MB）。"""
    total = 0
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            nm = (p.info["name"] or "").lower()
            if nm == "ollama.exe" and any("serve" in str(c) for c in (p.info["cmdline"] or [])):
                total += p.memory_info().rss
                for c in p.children(recursive=True):
                    try:
                        total += c.memory_info().rss
                    except Exception:
                        pass
        except Exception:
            pass
    return total / 1e6


def sampler(stop, buf, interval=0.2):
    peak = 0
    n = 0
    while not stop.is_set():
        cur = tree_rss()
        if cur > peak:
            peak = cur
        n += 1
        buf["peak"] = peak
        buf["n"] = n
        time.sleep(interval)


def one(img, s, keep_alive):
    p = IMG_DIR / img
    b64 = base64.b64encode(p.read_bytes()).decode()
    buf = {"peak": 0.0, "n": 0}
    stop = threading.Event()
    th = threading.Thread(target=sampler, args=(stop, buf), daemon=True)
    th.start()
    t0 = time.time()
    try:
        r = s.post(API, json={
            "model": MODEL, "prompt": "Read all the text in this image.",
            "images": [b64], "stream": False,
            "options": {"temperature": 0.0},
            "keep_alive": keep_alive,
        }, timeout=HARD_TIMEOUT_S)
        dt = time.time() - t0
        d = r.json() if r.status_code == 200 else {}
        return {"t_s": round(dt, 2), "status": r.status_code,
                "eval_count": d.get("eval_count"),
                "load_duration_ns": d.get("load_duration"),
                "prompt_eval_count": d.get("prompt_eval_count"),
                "text_len": len(d.get("response", "")),
                "peak_rss_mb": round(buf["peak"], 1), "samples": buf["n"]}
    except Exception as e:
        return {"t_s": round(time.time() - t0, 2), "status": "err",
                "err": "%s: %s" % (e.__class__.__name__, str(e)[:120]),
                "peak_rss_mb": round(buf["peak"], 1), "samples": buf["n"]}
    finally:
        stop.set()
        th.join(timeout=3)


def unload():
    """卸载模型，让下一次成为冷启动。

    ⚠️ `ollama unload` 在 0.40.11 里不存在（报 "unknown command" 且退出码仍是 0，
    只看退出码会误判成功）。正确做法是调 API：POST /api/generate 传 keep_alive=0。
    """
    try:
        requests.post(API, json={"model": MODEL, "keep_alive": 0}, timeout=120)
    except Exception as e:
        print("   (unload API 异常 %s，继续)" % str(e)[:50])
    # 轮询直到 ps 里真的没有该模型，最多等 60s
    for _ in range(20):
        time.sleep(3)
        if "glm-ocr" not in ollama_ps():
            return True
    return False


def main():
    s = requests.Session()
    res = {"keep_alive_note": "默认 5m；unload 用 keep_alive=0 强制卸载",
           "cold": {}, "warm": {}}
    print("=" * 70)
    print("STEP 1-B · GLM-OCR 冷启动 vs 热态分离测量")
    print("=" * 70)
    print("  初始 ollama ps:\n   " + ollama_ps().replace("\n", "\n   "))

    # ---------- 冷启动：每张先卸载再跑 ----------
    print("\n【冷启动】每张图先 unload 再跑（n=3/图）")
    for img in ["skew_01.png", "table_01.png"]:
        rows = []
        for i in range(3):
            unload()
            before = ollama_ps()
            assert "glm-ocr" not in before, "卸载失败，模型仍驻留: %s" % before[:80]
            r = one(img, s, keep_alive=0)
            r["run"] = i
            rows.append(r)
            print("   %-14s 冷#%d  t=%7.2fs  peak=%6.0f MB  eval=%s  load=%s" % (
                img, i, r["t_s"], r["peak_rss_mb"], r.get("eval_count"),
                ("%.1fs" % (r["load_duration_ns"] / 1e9)) if r.get("load_duration_ns") else "-"))
        res["cold"][img] = rows

    # ---------- 热态：模型驻留后连跑 ----------
    print("\n【热态】先 warmup 一次，再连跑 n=3/图")
    for img in ["skew_01.png", "table_01.png"]:
        one(img, s, keep_alive="1h")     # 预热（不入表）
        rows = []
        for i in range(3):
            r = one(img, s, keep_alive="1h")
            r["run"] = i
            rows.append(r)
            print("   %-14s 热#%d  t=%7.2fs  peak=%6.0f MB  eval=%s" % (
                img, i, r["t_s"], r["peak_rss_mb"], r.get("eval_count")))
        res["warm"][img] = rows

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已写:", OUT)

    import statistics
    print("\n" + "=" * 70)
    print("【汇总】")
    for regime in ("cold", "warm"):
        print("  --- %s ---" % regime)
        for img, rows in res[regime].items():
            ts = [r["t_s"] for r in rows]
            rss = [r["peak_rss_mb"] for r in rows]
            med = statistics.median(ts)
            spread = (max(ts) - min(ts)) / med * 100 if med else 0
            print("    %-14s t: min=%.2f 中位=%.2f max=%.2f  离散=%.1f%%   peak_rss=%.0f MB"
                  % (img, min(ts), med, max(ts), spread, max(rss)))


if __name__ == "__main__":
    main()
