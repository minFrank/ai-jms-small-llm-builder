#!/usr/bin/env python
# ep04 · 双后端 × 步数档 跑测
# 纪律（local-ai-runtime skill）：
#  - 干净环境串行跑，同一交付只引用同一批数据
#  - 每格 >=2 次，正文写区间不写单值
#  - 内存：按进程名求和、减基线、峰值与稳态分开报
#  - 每格算完立刻落盘（防中途被杀丢数据）
# 用法: python run_bench.py --runs 2
import argparse, json, os, subprocess, time, datetime, sys

M = r"D:/models/txt2img"
CPU = os.path.join(M, "cpu", "sd-cli.exe")
VULKAN = os.path.join(M, "vulkan", "sd-cli.exe")
MODEL = os.path.join(M, "v1-5-pruned-emaonly.safetensors")
OUT_DIR = os.path.join(M, "out")
LOG_DIR = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs"
PROGRESS = os.path.join(LOG_DIR, "bench-progress.json")

# 测过的所有真实提示词（中性例句，不用自家 slogan）
PROMPTS = [
    "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
]
# 后端 × 步数档
CELLS = [
    ("cpu", 20),
    ("cpu", 8),
    ("vulkan", 20),
    ("vulkan", 8),
]
SIZE = (512, 512)
SEED = 42


def mem_snapshot():
    """按进程名求和（skill 教训：拿到的进程对象内存不可信）"""
    try:
        import psutil
        tot = 0
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                if p.info["name"] and "sd-cli" in p.info["name"]:
                    tot += p.info["memory_info"].rss
            except Exception:
                pass
        return tot
    except ImportError:
        return None


def run_one(backend, steps, prompt_idx, run_idx):
    exe = CPU if backend == "cpu" else VULKAN
    w, h = SIZE
    tag = f"{backend}_s{steps}_p{prompt_idx}_r{run_idx}"
    out_png = os.path.join(OUT_DIR, f"{tag}.png")
    cmd = [exe, "-m", MODEL, "-p", PROMPTS[prompt_idx],
           "-W", str(w), "-H", str(h), "--steps", str(steps),
           "-s", str(SEED), "-o", out_png]
    if backend == "vulkan":
        cmd += ["--backend", "diffusion=vulkan0"]
    raw_log = os.path.join(LOG_DIR, f"raw-{tag}.txt")
    peak = 0
    t0 = time.time()
    with open(raw_log, "w", encoding="utf-8") as f:
        f.write(f"# cmd: {' '.join(cmd)}\n# start: {datetime.datetime.now().isoformat()}\n\n")
        f.flush()
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=M)
        while proc.poll() is None:
            m = mem_snapshot()
            if m:
                peak = max(peak, m)
            time.sleep(0.3)
        rc = proc.returncode
    dur = time.time() - t0
    rec = {
        "cell": tag, "backend": backend, "steps": steps, "size": f"{w}x{h}",
        "prompt_idx": prompt_idx, "run_idx": run_idx, "seed": SEED,
        "seconds": round(dur, 2), "returncode": rc,
        "mem_peak_rss_sum": peak or None,
        "png_bytes": os.path.getsize(out_png) if os.path.exists(out_png) else 0,
        "raw_log": raw_log,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": None,
    }
    # 立刻落盘（单文件，读-改-写，防被杀丢数据）
    rows = []
    if os.path.exists(PROGRESS):
        try:
            rows = json.load(open(PROGRESS, encoding="utf-8"))
        except Exception:
            rows = []
    rows.append(rec)
    tmp = PROGRESS + ".tmp"
    json.dump(rows, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, PROGRESS)  # 原子替换
    print(f"[{tag}] {dur:6.1f}s rc={rc} png={rec['png_bytes']}B peak={peak or 'n/a'}", flush=True)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2, help="每格次数(>=2)")
    ap.add_argument("--only", default=None, help="只跑指定 cell, 如 cpu_s20")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(MODEL):
        print(f"模型缺失: {MODEL}", file=sys.stderr); sys.exit(2)
    print(f"基线(同名进程): {mem_snapshot()}  开始 {datetime.datetime.now()}", flush=True)
    for backend, steps in CELLS:
        for p in range(len(PROMPTS)):
            for r in range(args.runs):
                tag = f"{backend}_s{steps}_p{p}_r{r}"
                if args.only and args.only != tag:
                    continue
                run_one(backend, steps, p, r)
    print("全部完成", flush=True)


if __name__ == "__main__":
    main()
