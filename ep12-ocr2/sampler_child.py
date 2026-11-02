# -*- coding: utf-8 -*-
"""ep12 内存采样子进程：独立进程采 Working Set 峰值，每 200 ms 一次。

为什么必须是独立进程而不是线程（实测踩出来的）：
  线程版在 onnxruntime 推理期间几乎得不到调度 —— 12.7 s 的格子只采到 3 帧
  （本该约 63 帧），推理把 CPU 核全占满把采样线程饿死，于是**错过真实峰值**。
  独立进程有自己的 OS 调度时间片，不受推理进程影响。

两种采样域（--mode）：
  self    从 --root-pid 递归取整棵子进程树（Python / .NET 引擎）
  ollama  从 ollama.exe serve 递归整棵树（glmocr 专用 —— 推理在 llama-server.exe，
          它是 ollama 的子进程而非本进程的子进程，按进程名匹配会低估 83 倍）

用法：python sampler_child.py --root-pid <pid> --mode self --out <json> --interval 0.2
父进程停掉它时发 Ctrl/BREAK 或直接 kill；它每轮都把当前 peak 写盘，
父进程读盘即可，即使被 kill 也已留痕。
"""
import argparse
import json
import os
import time


def wset(pid):
    try:
        import psutil
        return psutil.Process(pid).memory_info().wset
    except Exception:
        return 0


def tree_pids(root_pid):
    try:
        import psutil
        me = psutil.Process(root_pid)
        pids = [root_pid]
        for c in me.children(recursive=True):
            pids.append(c.pid)
        return pids
    except Exception:
        return [root_pid]


def ollama_pids():
    try:
        import psutil
        pids = []
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                nm = (p.info.get("name") or "").lower()
                cl = " ".join(p.info.get("cmdline") or []).lower()
            except Exception:
                continue
            if nm == "ollama.exe" or cl.startswith("ollama serve") or " ollama serve" in cl:
                pids.append(p.info["pid"])
                for c in p.children(recursive=True):
                    pids.append(c.pid)
        return pids
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-pid", type=int, required=True)
    ap.add_argument("--mode", default="self", choices=["self", "ollama"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=0.2)
    args = ap.parse_args()

    get = ollama_pids if args.mode == "ollama" else (lambda: tree_pids(args.root_pid))
    peak = 0
    n = 0
    t0 = time.time()
    while True:
        tot = 0
        for pid in get():
            tot += wset(pid)
        if tot > peak:
            peak = tot
        n += 1
        # ⚠️ 必须原子写：原来直接 open(out,"w") 会先截断再写，
        #    父进程若恰好在截断后、写完前读到，就拿到半截 JSON →
        #    json.load 失败 → _read() 返回 {} → peak 静默变 0.0（2026-10-26 实测
        #    lightonocr__book_02 采了 556 帧、加载期还读到 1590.6 MB，
        #    最终峰值却是 0.0）。写临时文件再 os.replace，读者永远只见完整内容。
        try:
            tmp = args.out + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"peak_bytes": peak, "samples": n,
                           "mode": args.mode, "elapsed_s": round(time.time() - t0, 2)},
                          f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, args.out)
        except Exception:
            pass
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
