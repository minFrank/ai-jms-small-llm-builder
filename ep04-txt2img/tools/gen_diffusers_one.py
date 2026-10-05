#!/usr/bin/env python
"""diffusers 单次生成(CPU):从 sd.cpp 同款 safetensors 单文件加载,同 seed 同参。

用法: gen_diffusers_one.py --prompt "..." --out out.png
打印:PEAK=<bytes> 供父进程采集峰值内存
"""
import argparse
import os
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = r"D:/models/txt2img/v1-5-pruned-emaonly.safetensors"
SEED, STEPS, SIZE = 42, 20, (512, 512)


def peak_monitor():
    import psutil
    p = psutil.Process()
    peak = 0
    stop = threading.Event()

    def loop():
        nonlocal peak
        while not stop.is_set():
            peak = max(peak, p.memory_info().rss)
            time.sleep(0.4)
    threading.Thread(target=loop, daemon=True).start()
    return stop, lambda: peak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    stop, get_peak = peak_monitor()
    t0 = time.time()
    import torch
    from diffusers import StableDiffusionPipeline

    torch.manual_seed(a.seed)
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL, torch_dtype=torch.float32, local_files_only=True)
    pipe = pipe.to("cpu")
    pipe.set_progress_bar_config(disable=True)
    load_s = time.time() - t0

    t1 = time.time()
    img = pipe(prompt=a.prompt, num_inference_steps=STEPS, generator=torch.Generator().manual_seed(a.seed),
               width=SIZE[0], height=SIZE[1]).images[0]
    gen_s = time.time() - t1
    img.save(a.out)
    stop.set()
    print(f"LOAD={load_s:.1f} GEN={gen_s:.1f} PEAK={int(get_peak())} OUT={a.out}")


if __name__ == "__main__":
    main()
