"""STEP 1-D：全样本探针 —— 每张图的视觉 token 数与真实冷态耗时。

一跑两得：
  ① prompt_eval_count = 视觉 token 数 → 用于把排期从"区间"收敛成"数"
  ② 每张的真实耗时（每张前卸载模型，避免 §1-C 发现的按图缓存污染）

同时落 peak RSS（整棵 ollama 进程树，含 llama-server.exe）。
"""
import base64
import json
import pathlib
import threading
import time

import psutil
import requests

API = "http://127.0.0.1:11434/api/generate"
PSAPI = "http://127.0.0.1:11434/api/ps"
MODEL = "glm-ocr:latest"
IMG_DIR = pathlib.Path(
    r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples")
OUT = pathlib.Path(r"D:/models/ollama/step1d_probe.json")
PROMPT = "Read all the text in this image."


def tree_rss_mb():
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
    peak = 0.0
    n = 0
    while not stop.is_set():
        cur = tree_rss_mb()
        if cur > peak:
            peak = cur
        n += 1
        buf["peak"] = peak
        buf["n"] = n
        time.sleep(interval)


def unload():
    try:
        requests.post(API, json={"model": MODEL, "keep_alive": 0}, timeout=120)
    except Exception:
        pass
    for _ in range(24):
        time.sleep(3)
        try:
            if "glm-ocr" not in requests.get(PSAPI, timeout=30).text:
                return True
        except Exception:
            pass
    return False


def main():
    imgs = sorted(p for p in IMG_DIR.glob("*.png"))
    print("=" * 90)
    print("STEP 1-D · 全样本探针（视觉 token 数 + 真实冷态耗时）")
    print("=" * 90)
    print("  图片数: %d   模型: %s" % (len(imgs), MODEL))
    print("  口径: 每张前卸载模型（防 §1-C 发现的按图缓存污染）")
    vm = psutil.virtual_memory()
    print("  内存: 总 %.1f GB / 可用 %.1f GB\n" % (vm.total / 1e9, vm.available / 1e9))

    s = requests.Session()
    rows = []
    t_batch = time.time()
    for i, p in enumerate(imgs):
        ok = unload()
        b64 = base64.b64encode(p.read_bytes()).decode()
        buf = {"peak": 0.0, "n": 0}
        stop = threading.Event()
        threading.Thread(target=sampler, args=(stop, buf), daemon=True).start()
        t0 = time.time()
        try:
            r = s.post(API, json={"model": MODEL, "prompt": PROMPT, "images": [b64],
                                  "stream": False, "options": {"temperature": 0.0},
                                  "keep_alive": 0}, timeout=1800)
            dt = time.time() - t0
            d = r.json() if r.status_code == 200 else {}
            row = {
                "img": p.name, "kb": round(p.stat().st_size / 1024, 1),
                "unloaded_ok": ok, "t_s": round(dt, 2), "status": r.status_code,
                "visual_tokens": d.get("prompt_eval_count"),
                "prefill_s": round((d.get("prompt_eval_duration") or 0) / 1e9, 2),
                "gen_tokens": d.get("eval_count"),
                "gen_s": round((d.get("eval_duration") or 0) / 1e9, 2),
                "load_s": round((d.get("load_duration") or 0) / 1e9, 2),
                "peak_rss_mb": round(buf["peak"], 1),
                "text_len": len(d.get("response", "")),
            }
        except Exception as e:
            dt = time.time() - t0
            row = {"img": p.name, "kb": round(p.stat().st_size / 1024, 1),
                   "unloaded_ok": ok, "t_s": round(dt, 2), "status": "err",
                   "err": "%s: %s" % (e.__class__.__name__, str(e)[:120]),
                   "peak_rss_mb": round(buf["peak"], 1)}
        finally:
            stop.set()
        rows.append(row)
        el = time.time() - t_batch
        print("  [%2d/%d] %-14s %6.0fKB  t=%7.2fs  vis_tok=%-6s prefill=%6.2fs  gen=%-4s/%5.2fs  rss=%5.0fMB  累计%5.1fmin"
              % (i + 1, len(imgs), p.name, row["kb"], row["t_s"],
                 row.get("visual_tokens"), row.get("prefill_s") or 0,
                 row.get("gen_tokens"), row.get("gen_s") or 0,
                 row.get("peak_rss_mb") or 0, el / 60), flush=True)

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已写:", OUT)

    ok = [r for r in rows if r.get("visual_tokens")]
    if not ok:
        print("无有效数据")
        return
    toks = sorted(r["visual_tokens"] for r in ok)
    ts = [r["t_s"] for r in ok]
    import statistics
    print("\n" + "=" * 90)
    print("【视觉 token 分布】")
    print("  n=%d  min=%d  中位=%d  max=%d  合计=%d" % (
        len(toks), toks[0], statistics.median(toks), toks[-1], sum(toks)))
    print("  逐张:", toks)
    print("\n【单页耗时分布（冷态，每张前已卸载）】")
    print("  min=%.1fs  中位=%.1fs  max=%.1fs  合计=%.1f min" % (
        min(ts), statistics.median(ts), max(ts), sum(ts) / 60))
    print("\n【排期推算】")
    n_img = len(ok)
    for reps in (1, 3):
        print("  %d 张 × n=%d = %.1f min（按本次实测总和 ×%d）" % (
            n_img, reps, sum(ts) * reps / 60, reps))
    rss = [r["peak_rss_mb"] for r in ok if r.get("peak_rss_mb")]
    if rss:
        print("\n【内存】峰值 max=%.0f MB (%.2f GB)  → 阈值 ×1.3 = %.2f GB" % (
            max(rss), max(rss) / 1024, max(rss) * 1.3 / 1024))


if __name__ == "__main__":
    main()
