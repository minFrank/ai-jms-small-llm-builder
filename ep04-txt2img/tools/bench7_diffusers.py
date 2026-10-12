#!/usr/bin/env python
"""ep04 补测 · diffusers 维度扩展(768/1024、题材)

为什么有这个脚本:bench4.py 被 bench5/bench6 的冻结判据 C11 锁死(源码改动即 FATAL),
而它的 run_diffusers() 只支持 512x512、只写已发布的 bench4-progress.json ——
本脚本**逐条照抄**其口径,只把 size 与落盘路径参数化:

  对齐 bench4.run_diffusers 的部分
    - 子进程跑 gen_diffusers_one.py(内存独立、崩溃不拖主控)
    - 墙钟计时(包住整个 subprocess,等价 cold_total_incl_load)
    - PEAK 从 stdout 的 PEAK= 提取
    - row 字段同名同义(多记 sha256 与 timing_scope)
    - 同 prompt(2 句逐字同)、seed 42/43/44、steps 20、cfg 7.0

  新增判据(与 bench5/bench6 同级)
    - DP-14: --n >= 3,每格报中位
    - DP-16: 同格各 run 的 png sha256 必须全同
    - DP-20: socket 断网 guard(bench4/bench5_topics 同款)

用法:
  python tools/bench7_diffusers.py --size 768 --cells p0_s42 --n 3 \
         --out logs/bench7-diffusers-768.json
"""
import argparse
import collections
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 离线 guard(bench4 同款:非回环 + 代理端口一律拦)----
_orig = socket.socket.connect
_BLOCKED = []
_PROXY = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888}


def _g(self, address, *a, **k):
    host = str(address[0]) if isinstance(address, tuple) and address else str(address)
    port = int(address[1]) if isinstance(address, tuple) and len(address) > 1 else 0
    if host not in ("127.0.0.1", "::1", "localhost"):
        _BLOCKED.append("%s:%s" % (host, port))
        raise OSError("[offline-guard] blocked %s:%s" % (host, port))
    if port in _PROXY:
        _BLOCKED.append("%s:%s (proxy)" % (host, port))
        raise OSError("[offline-guard] blocked proxy %s" % port)
    return _orig(self, address, *a, **k)


socket.socket.connect = _g

MODELS = r"D:/models/txt2img"
E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
ONE = os.path.join(E04, "tools", "gen_diffusers_one.py")
OUTDIR = os.path.join(MODELS, "out7")
# 与 bench4.py L61-64 逐字一致(可比性前提)
PROMPTS = [
    "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
]
SEEDS = [42, 43, 44]
STEPS, CFG = 20, 7.0
TIMING_SCOPE = "cold_total_incl_load"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    global PROMPTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=512,
                    help="正方形边长;默认 512 与已发布口径一致,补 768/1024 时才传")
    ap.add_argument("--out", required=True, help="progress 落盘路径(必须是新文件)")
    ap.add_argument("--cells", default=None, help="只跑指定格, 逗号分隔如 p0_s42")
    ap.add_argument("--n", type=int, default=3, help="每格轮数(DP-14: >=3)")
    ap.add_argument("--topics-file", default=None,
                    help="五类题材 JSON(替换 PROMPTS);不传则用已发布的 p0/p1 两题")
    a = ap.parse_args()
    if a.n < 3:
        raise SystemExit("FATAL(DP-14): --n=%d < 3,拒绝开跑" % a.n)
    if a.topics_file:
        _tj = json.load(open(a.topics_file, encoding="utf-8"))
        PROMPTS = list(_tj["topics"].values())
        print("[补测] 题材 prompt %d 个: %s" % (len(PROMPTS), ",".join(_tj["topics"].keys())), flush=True)
    if os.path.basename(a.out) == "bench4-progress.json":
        raise SystemExit("FATAL(C1): 不得写已发布的 bench4-progress.json")

    size_t = (a.size, a.size)
    os.makedirs(OUTDIR, exist_ok=True)
    rows = []
    if os.path.exists(a.out):
        try:
            rows = json.load(open(a.out, encoding="utf-8")).get("rows", [])
        except Exception as e:
            raise SystemExit("FATAL(B06): %s 解析失败(拒绝用空历史覆盖): %s" % (a.out, e))
    want = {c.strip() for c in a.cells.split(",") if c.strip()} if a.cells else None
    ts_start = time.strftime("%Y-%m-%d %H:%M:%S")
    print("[补测] SIZE=%s progress -> %s (不覆盖已发布文件)" % (size_t, a.out), flush=True)
    if want:
        print("[补测] 定向跑格: %s" % sorted(want), flush=True)

    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            key = "p%d_s%d" % (p, seed)
            if want and key not in want:
                continue
            for run in range(a.n):
                cell = "diffusers_%s_r%d" % (key, run)
                if any(r.get("cell") == cell and r.get("ok") for r in rows):
                    print("  %-34s skip" % cell, flush=True)
                    continue
                out = os.path.join(OUTDIR, cell + ".png")
                t0 = time.time()
                pr = subprocess.run(
                    [sys.executable, ONE, "--prompt", PROMPTS[p], "--out", out,
                     "--seed", str(seed), "--size", str(a.size)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                dt = time.time() - t0
                peak = None
                m = re.search(r"PEAK=(\d+)", pr.stdout or "")
                if m:
                    peak = int(m.group(1))
                ok = os.path.exists(out) and os.path.getsize(out) > 1000
                rows.append({
                    "cell": cell, "scheme": "diffusers", "prompt_idx": p,
                    "run_idx": run, "seed": seed, "steps": STEPS, "cfg": CFG,
                    "size": "%dx%d" % size_t, "timing_scope": TIMING_SCOPE,
                    "seconds": round(dt, 2), "mem_peak": peak,
                    "sha256": sha256_file(out) if ok else "",
                    "ok": ok, "err": "" if ok else (pr.stderr or "")[-300:],
                })
                tmp = a.out + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({"rows": rows, "ts_start": ts_start}, f,
                              ensure_ascii=False, indent=1)
                os.replace(tmp, a.out)
                print("  %-34s %6.1fs peak=%-8s %s" % (
                    cell, dt, ("%dMB" % (peak // 1048576)) if peak else "?",
                    "OK" if ok else "FAIL"), flush=True)

    # DP-16: 同格各 run 的 sha256 必须全同
    g = collections.defaultdict(set)
    for r in rows:
        m2 = re.match(r"diffusers_(p\d+_s\d+)_r\d+$", r.get("cell", ""))
        if m2 and r.get("sha256"):
            g[m2.group(1)].add(r["sha256"])
    print("\n=== 种子自检(DP-16: 同格各 run sha256 必须全同) ===", flush=True)
    bad = 0
    for k, v in sorted(g.items()):
        st = "SAME PASS" if len(v) == 1 else "FAIL(%d 种)" % len(v)
        if len(v) != 1:
            bad += 1
        print("  %s: n=%d %s" % (k, len(v), st), flush=True)

    import statistics as stx
    secs = [r["seconds"] for r in rows if r.get("ok")]
    if secs:
        med = stx.median(secs)
        spread = 100.0 * (max(secs) - min(secs)) / med if med else 0.0
        print("seconds 中位 %.1f 范围 %.1f-%.1f 极差比 %.1f%%" % (
            med, min(secs), max(secs), spread), flush=True)
        if spread > 5.0:
            print("警告: 极差比 >5%% 判据(DP-14),该格建议加预热重跑", flush=True)
    print("离线证据: non-loopback 尝试 %d 次" % len(_BLOCKED), flush=True)
    print("RESULT " + ("PASS" if bad == 0 else "FAIL"), flush=True)


if __name__ == "__main__":
    main()
