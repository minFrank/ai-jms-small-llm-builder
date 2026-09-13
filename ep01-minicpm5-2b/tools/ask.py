"""ask.py — 单次推理(打印回答与性能统计),含"思维链吃 token"的应对默认值。

用法:
  python ask.py --llama D:\\tools\\llama --model D:\\models\\MiniCPM5-2B-Q4_K_M.gguf "什么是 KV 缓存?"
"""
import argparse
import os
import re
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", help="要问的问题")
    ap.add_argument("--llama", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--ctx", type=int, default=4096, help="上下文长度(默认 4096,可显著降低内存)")
    ap.add_argument("--n", type=int, default=400, help="生成上限(默认 400:留足思维链空间)")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.3)
    args = ap.parse_args()

    exe = os.path.join(args.llama, "llama-completion.exe")
    if not os.path.exists(exe):
        sys.exit(f"找不到 {exe}")
    cmd = [exe, "-m", args.model, "-p", args.prompt, "-n", str(args.n), "-t", str(args.threads),
           "-st", "--no-warmup", "--temp", str(args.temp), "-c", str(args.ctx)]
    print("运行:", " ".join(cmd), "\n")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    body = [l for l in out.splitlines() if not re.match(r"^\d+\.\d+\.\d+\.\d+ [IWE] ", l)]
    print("\n".join(body))
    for pat, label in [(r"load time\s*=\s*([\d.]+ ms)", "模型加载"),
                       (r"prompt eval time\s*=\s*([\d.]+ ms\s*/\s*\d+ tokens)", "提示处理"),
                       (r"eval time\s*=\s*([\d.]+ ms\s*/\s*\d+ tokens)", "生成"),
                       (r"total time\s*=\s*([\d.]+ ms\s*/\s*\d+ tokens)", "合计")]:
        m = re.search(pat, out)
        if m:
            print(f"[{label}] {m.group(1)}")


if __name__ == "__main__":
    main()
