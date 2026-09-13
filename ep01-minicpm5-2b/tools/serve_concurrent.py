"""serve_concurrent.py — 起本地 llama-server,并发压测(默认 4 路)。

用法:
  python serve_concurrent.py --llama D:\\tools\\llama --model D:\\models\\MiniCPM5-2B-Q4_K_M.gguf --concurrency 4
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--n", type=int, default=96)
    args = ap.parse_args()

    exe = os.path.join(args.llama, "llama-server.exe")
    if not os.path.exists(exe):
        sys.exit(f"找不到 {exe}")

    srv = subprocess.Popen([exe, "-m", args.model, "-c", str(args.ctx), "-t", str(args.threads),
                            "--port", str(args.port), "--host", "127.0.0.1"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
    base = f"http://127.0.0.1:{args.port}"
    print(f"启动服务:{base}(上下文 {args.ctx},线程 {args.threads})")
    for _ in range(90):
        try:
            if requests.get(base + "/health", timeout=3).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        srv.kill()
        sys.exit("服务未就绪")

    prompts = ["用一句话说明什么是量化。", "用一句话说明什么是注意力机制。",
               "用一句话说明什么是分词器。", "用一句话说明什么是 KV 缓存。",
               "用一句话说明什么是微调。", "用一句话说明什么是 RAG。",
               "用一句话说明什么是智能体。", "用一句话说明什么是多模态。"][:args.concurrency]

    # 单路基线
    t0 = time.time()
    r1 = requests.post(base + "/completion", json={"prompt": prompts[0], "n_predict": args.n,
                                                   "temperature": 0.3, "cache_prompt": False}, timeout=1800).json()
    d1 = time.time() - t0
    n1 = (r1.get("timings") or {}).get("predicted_n") or 0
    print(f"[单路] {d1:.1f}s / {n1} tokens → {n1/max(d1,0.01):.1f} tok/s")

    # 并发
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        res = list(ex.map(lambda p: requests.post(base + "/completion",
            json={"prompt": p, "n_predict": args.n, "temperature": 0.3, "cache_prompt": False},
            timeout=1800).json(), prompts))
    wall = time.time() - t0
    tot = sum(((x.get("timings") or {}).get("predicted_n") or 0) for x in res)
    print(f"[{args.concurrency} 路并发] 墙钟 {wall:.1f}s / 合计 {tot} tokens → {tot/max(wall,0.01):.1f} tok/s")

    srv.terminate()
    try:
        srv.wait(timeout=10)
    except Exception:
        srv.kill()


if __name__ == "__main__":
    main()
