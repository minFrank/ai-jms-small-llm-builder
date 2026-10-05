#!/usr/bin/env python
"""ep04 题材扩样:狗猫 / 汽车 / 衣服 / 自行车 × 三方案(sd.cpp核显 / sd.cpp纯CPU / diffusers)。

口径与空载干净批 bench4 完全一致:512x512 · steps 20 · seed 42 · 串行 · 出网 0。
独立进度文件 logs/bench5-topics.json(不动已交付的 bench4 干净批)。
用法: D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe tools/bench5_topics.py [--only <scheme>]
"""
import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 离线 guard:非回环 + 代理端口一律拦(bench4 同款)----
_orig = socket.socket.connect
_BLOCKED = []
_PROXY = {7897, 7890, 7891, 7892, 7893, 1080, 10808, 10809, 8080, 8118, 8888}


def _g(self, address, *a, **k):
    host = str(address[0]) if isinstance(address, tuple) and address else str(address)
    port = int(address[1]) if isinstance(address, tuple) and len(address) > 1 else 0
    if host not in ("127.0.0.1", "::1", "localhost"):
        _BLOCKED.append(f"{host}:{port}")
        raise OSError(f"[offline-guard] blocked {host}:{port}")
    if port in _PROXY:
        _BLOCKED.append(f"{host}:{port} (proxy)")
        raise OSError(f"[offline-guard] blocked proxy {port}")
    return _orig(self, address, *a, **k)


socket.socket.connect = _g
try:
    socket.create_connection(("1.1.1.1", 80), timeout=3)
    _BLOCKED.append("LEAK")
except OSError:
    pass
_BLOCKED.clear()

import psutil  # noqa: E402

MODELS = r"D:/models/txt2img"
E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
LOG = os.path.join(E04, "logs", "bench5-topics.json")
OUTDIR = os.path.join(MODELS, "out4")
os.makedirs(OUTDIR, exist_ok=True)

MODEL = os.path.join(MODELS, "v1-5-pruned-emaonly.safetensors")
PY = r"D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe"
ONE = os.path.join(E04, "tools", "gen_diffusers_one.py")

SIZE, STEPS, SEED = (512, 512), 20, 42
SCHEMES = ["sdcpp-vulkan", "diffusers", "sdcpp-cpu"]

# 4 类常画题材(与原 C 组同一位置追加:每类 × 3 方案 × 1 跑)
TOPICS = {
    "dogcat":  "a golden retriever and a tabby cat sitting together on green grass, warm afternoon light, photorealistic",
    "car":     "a red sports car parked on a wet city street at dusk, glossy reflections, side view, photorealistic",
    "clothes": "a blue denim jacket on a wooden hanger against a plain white wall, product photo, soft studio lighting",
    "bicycle": "a vintage road bicycle leaning against an old brick wall, morning sunlight, photorealistic",
}

PROGRESS = {"rows": [], "ts_start": time.strftime("%Y-%m-%d %H:%M:%S")}


def load_rows():
    if os.path.exists(LOG):
        try:
            return json.load(open(LOG, encoding="utf-8")).get("rows", [])
        except Exception:
            return []
    return []


def save():
    """合并写:先读磁盘现有行、去掉内存已有 cell 的重复,防中途被杀丢数据。"""
    try:
        disk_rows = json.load(open(LOG, encoding="utf-8")).get("rows", [])
    except Exception:
        disk_rows = []
    mem_cells = {r.get("cell") for r in PROGRESS["rows"]}
    merged = [r for r in disk_rows if r.get("cell") not in mem_cells] + PROGRESS["rows"]
    PROGRESS["rows"] = merged
    with open(LOG + ".tmp", "w", encoding="utf-8") as f:
        json.dump(PROGRESS, f, ensure_ascii=False, indent=1)
    os.replace(LOG + ".tmp", LOG)


def has(cell):
    return any(r.get("cell") == cell and r.get("ok") for r in PROGRESS["rows"])


class Peak:
    """sd-cli 按进程名求和采样(同 bench4 口径)。"""

    def __init__(self):
        self.peak, self._stop = 0, threading.Event()

    def _sum(self):
        tot = 0
        try:
            for p in psutil.process_iter(["name", "memory_info"]):
                n = p.info["name"] or ""
                if "sd-cli" in n:
                    tot += p.info["memory_info"].rss
        except Exception:
            pass
        return tot

    def run(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, self._sum())
            time.sleep(0.5)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        return self

    def stop(self):
        self._stop.set()
        return self.peak


def baseline():
    tot = 0
    for p in psutil.process_iter(["name", "memory_info"]):
        n = p.info["name"] or ""
        if "sd-cli" in n:
            tot += p.info["memory_info"].rss
    return tot


def run_one(scheme, topic, prompt):
    cell = f"T_{scheme}_{topic}"
    if has(cell):
        print(f"  {cell:<32} skip(已有)", flush=True)
        return
    out = os.path.join(OUTDIR, cell + ".png")
    raw = os.path.join(E04, "logs", f"raw-{cell}.txt")
    err = ""
    peak = None
    t0 = time.time()
    if scheme == "diffusers":
        pr = subprocess.run([sys.executable, ONE, "--prompt", prompt, "--out", out,
                             "--seed", str(SEED)],
                            capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        with open(raw, "w", encoding="utf-8") as f:
            f.write(f"# {datetime.datetime.now().isoformat()} cell={cell}\n"
                    f"# {' '.join(pr.args)}\n\n{pr.stdout}\n{pr.stderr}")
        m = re.search(r"PEAK=(\d+)", pr.stdout or "")
        if m:
            peak = int(m.group(1))
    else:
        backend = scheme.split("-")[1]
        exe = os.path.join(MODELS, backend, "sd-cli.exe")
        cmd = [exe, "-m", MODEL, "--prompt", prompt,
               "-W", str(SIZE[0]), "-H", str(SIZE[1]),
               "--steps", str(STEPS), "-s", str(SEED), "-o", out]
        if backend == "vulkan":
            cmd += ["--backend", "diffusion=vulkan0"]
        pk = Peak().start()
        with open(raw, "w", encoding="utf-8") as f:
            f.write(f"# {datetime.datetime.now().isoformat()} cell={cell}\n"
                    f"# {' '.join(cmd)}\n\n")
            f.flush()
            pr = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=MODELS)
            pr.wait()
            peak = pk.stop()
    dt = time.time() - t0
    ok = os.path.exists(out) and os.path.getsize(out) > 1000
    if not ok:
        err = f"rc={getattr(pr, 'returncode', '?')} png缺失或过小"
    PROGRESS["rows"].append({
        "cell": cell, "scheme": scheme, "topic": topic, "prompt": prompt,
        "seed": SEED, "steps": STEPS, "size": "512x512",
        "seconds": round(dt, 2), "mem_peak": peak, "ok": ok, "err": err,
        "png_bytes": os.path.getsize(out) if os.path.exists(out) else 0,
        "raw": raw, "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    save()
    print(f"  {cell:<32} {dt:6.1f}s peak={(peak or 0) // 1048576}MB "
          f"{'OK' if ok else 'FAIL'}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=SCHEMES, default=None)
    a = ap.parse_args()
    PROGRESS["rows"] = load_rows()
    print(f"已有 {len(PROGRESS['rows'])} 格(断点续跑) · 基线同名进程 {baseline()}B", flush=True)
    print(f"口径: {SIZE[0]}x{SIZE[1]} | steps={STEPS} | seed={SEED} | 串行 | 出网 0", flush=True)
    schemes = [a.only] if a.only else SCHEMES
    for s in schemes:
        print(f"\n== {s} ==", flush=True)
        for topic, prompt in TOPICS.items():
            try:
                run_one(s, topic, prompt)
            except Exception:
                import traceback
                print(f"  !! {s}/{topic} 异常:\n{traceback.format_exc()}", flush=True)
                save()
    print(f"\ndone. rows={len(PROGRESS['rows'])} blocked={sorted(set(_BLOCKED)) or 0}", flush=True)


if __name__ == "__main__":
    main()
