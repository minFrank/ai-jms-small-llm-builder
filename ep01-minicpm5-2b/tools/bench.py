"""bench.py — 用 llama-bench 测 MiniCPM5-2B 的提示处理/生成速度。

用法:
  python bench.py --llama D:\\tools\\llama --model D:\\models\\MiniCPM5-2B-Q4_K_M.gguf
可选:
  --pp 512 --tg 128 --threads 8 --repeat 3
"""
import argparse
import os
import re
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama", required=True, help="llama.cpp 解压目录(含 llama-bench.exe)")
    ap.add_argument("--model", required=True, help="GGUF 模型路径")
    ap.add_argument("--pp", type=int, default=512, help="提示处理测试长度(默认 512)")
    ap.add_argument("--tg", type=int, default=128, help="生成测试长度(默认 128)")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--repeat", type=int, default=3)
    args = ap.parse_args()

    exe = os.path.join(args.llama, "llama-bench.exe")
    if not os.path.exists(exe):
        sys.exit(f"找不到 {exe},请确认 --llama 指向解压目录")
    if not os.path.exists(args.model):
        sys.exit(f"找不到模型文件:{args.model}")

    cmd = [exe, "-m", args.model, "-p", str(args.pp), "-n", str(args.tg),
           "-t", str(args.threads), "-r", str(args.repeat)]
    print("运行:", " ".join(cmd), "\n")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    for l in out.splitlines():
        if "pp" in l or "tg" in l:
            m = re.search(r"\|\s*(pp\d+|tg\d+)\s*\|\s*([\d.]+)", l)
            if m:
                print(f"  → {m.group(1)}: {m.group(2)} t/s")


if __name__ == "__main__":
    main()
