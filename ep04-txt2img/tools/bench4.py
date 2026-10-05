#!/usr/bin/env python
"""ep04 扩容:四方案同批基准(参考 03 期 ASR 多引擎同机同批口径)。

四方案:
  sdcpp-cpu     stable-diffusion.cpp  CPU 后端
  sdcpp-vulkan  stable-diffusion.cpp  Vulkan 核显后端
  diffusers     HuggingFace diffusers (PyTorch CPU)
  comfyui       ComfyUI --cpu (无头 API)

统一口径:2 prompt × seed 42 × 512×512 × steps 20 × runs 2 = 每方案 4 次生成
内存:按进程标识求和(sd-cli 按名 / torch、comfy 按 pid),不减基线时标注
纪律:一次一个方案(单模型)、每格算完立刻落盘、禁联网 guard
用法: python bench4.py --only diffusers   (逐方案跑,最后汇总)
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import re
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 禁联网(同款 guard:非回环 + 代理端口)----
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
LOG = os.path.join(E04, "logs", "bench4-progress.json")
OUTDIR = os.path.join(MODELS, "out4")
os.makedirs(OUTDIR, exist_ok=True)

PROMPTS = [
    "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
]
ONCE = False
SEEDS, SIZE, STEPS = [42, 43, 44], (512, 512), 20  # 每 prompt 3 个 seed(同 seed 复跑=同图)
MODEL = os.path.join(MODELS, "v1-5-pruned-emaonly.safetensors")

PROGRESS = {"rows": [], "ts_start": time.strftime("%Y-%m-%d %H:%M:%S")}


def save():
    """合并写:先读磁盘现有行、去掉内存已有 cell 的重复,再写 —— 防多进程互相覆盖。"""
    global PROGRESS
    try:
        disk_rows = json.load(open(LOG, encoding="utf-8")).get("rows", [])
    except Exception:
        disk_rows = []
    mem_cells = {r.get("cell") for r in PROGRESS.get("rows", [])}
    merged = [r for r in disk_rows if r.get("cell") not in mem_cells]
    merged += PROGRESS.get("rows", [])
    PROGRESS["rows"] = merged
    with open(LOG + ".tmp", "w", encoding="utf-8") as f:
        json.dump(PROGRESS, f, ensure_ascii=False, indent=1)
    os.replace(LOG + ".tmp", LOG)


def has(cell):
    """断点续跑:该格已成功则跳过。"""
    return any(r.get("cell") == cell and r.get("ok") for r in PROGRESS["rows"])


def load_rows():
    if os.path.exists(LOG):
        try:
            return json.load(open(LOG, encoding="utf-8")).get("rows", [])
        except Exception:
            return []
    return []


class Peak:
    """方案专属的内存采样器(后台线程)。"""

    def __init__(self, mode, pid=None):
        self.mode, self.pid, self.peak, self._stop = mode, pid, 0, threading.Event()

    def _sum(self):
        tot = 0
        try:
            for p in psutil.process_iter(["name", "pid", "memory_info"]):
                n = p.info["name"] or ""
                if self.mode == "sdcli" and "sd-cli" in n:
                    tot += p.info["memory_info"].rss
                elif self.mode == "pid" and p.info["pid"] == self.pid:
                    tot = p.info["memory_info"].rss
                elif self.mode == "comfy" and ("python" in n.lower()
                                                and p.info["pid"] == self.pid):
                    tot = p.info["memory_info"].rss
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


def run_sdcpp(backend):
    exe = os.path.join(MODELS, backend, "sd-cli.exe")
    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            tag = f"sdcpp-{backend}_p{p}_s{seed}"
            if has(tag):
                print(f"  {tag:<28} skip(已有)", flush=True)
                continue
            out = os.path.join(OUTDIR, tag + ".png")
            cmd = [exe, "-m", MODEL, "--prompt", PROMPTS[p],
                   "-W", str(SIZE[0]), "-H", str(SIZE[1]),
                   "--steps", str(STEPS), "-s", str(seed), "-o", out]
            if backend == "vulkan":
                cmd += ["--backend", "diffusion=vulkan0"]
            pk = Peak("sdcli").start()
            t0 = time.time()
            pr = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
            dt = time.time() - t0
            peak = pk.stop()
            ok = os.path.exists(out) and os.path.getsize(out) > 1000
            PROGRESS["rows"].append({
                "cell": tag, "scheme": f"sdcpp-{backend}", "prompt_idx": p,
                "run_idx": seed, "seed": seed, "steps": STEPS, "size": "512x512",
                "seconds": round(dt, 2), "mem_peak": peak or None,
                "ok": ok, "err": "" if ok else (pr.stderr or "")[-300:]})
            save()
            print(f"  {tag:<28} {dt:6.1f}s peak={peak//1048576 if peak else '?'}MB "
                  f"{'OK' if ok else 'FAIL'}", flush=True)
            if ONCE:
                return


def run_diffusers():
    """单次生成脚本放子进程跑(内存独立、崩溃不拖主控)。"""
    one = os.path.join(E04, "tools", "gen_diffusers_one.py")
    for p in range(len(PROMPTS)):
        for seed in SEEDS:
            tag = f"diffusers_p{p}_s{seed}"
            if has(tag):
                print(f"  {tag:<28} skip(已有)", flush=True)
                continue
            out = os.path.join(OUTDIR, tag + ".png")
            t0 = time.time()
            pr = subprocess.run(
                [sys.executable, one, "--prompt", PROMPTS[p], "--out", out,
                 "--seed", str(seed)],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            dt = time.time() - t0
            peak = None
            m = re.search(r"PEAK=(\d+)", pr.stdout or "")
            if m:
                peak = int(m.group(1))
            ok = os.path.exists(out) and os.path.getsize(out) > 1000
            PROGRESS["rows"].append({
                "cell": tag, "scheme": "diffusers", "prompt_idx": p,
                "run_idx": seed, "seed": seed, "steps": STEPS, "size": "512x512",
                "seconds": round(dt, 2), "mem_peak": peak,
                "ok": ok, "err": "" if ok else (pr.stderr or "")[-300:]})
            save()
            print(f"  {tag:<28} {dt:6.1f}s peak={peak//1048576 if peak else '?'}MB "
                  f"{'OK' if ok else 'FAIL'}", flush=True)
            if ONCE:
                return


def run_comfy():
    """起 ComfyUI --cpu,走 /prompt API,收 history 出图。"""
    import urllib.request
    sys.path.insert(0, os.path.join(E04, "ComfyUI"))
    ckpt_dir = os.path.join(E04, "ComfyUI", "models", "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)
    link = os.path.join(ckpt_dir, "v1-5-pruned-emaonly.safetensors")
    if not os.path.exists(link):
        try:
            os.symlink(MODEL, link)
        except OSError:
            import shutil
            shutil.copyfile(MODEL, link)

    log = open(os.path.join(E04, "logs", "comfy_server.log"), "w")
    srv = subprocess.Popen([sys.executable, os.path.join(E04, "ComfyUI", "main.py"),
                            "--cpu", "--port", "8188"],
                           stdout=log, stderr=subprocess.STDOUT,
                           cwd=os.path.join(E04, "ComfyUI"))
    # 等服务
    base = "http://127.0.0.1:8188"
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/system_stats", timeout=2).read()
            break
        except Exception:
            time.sleep(2)
    else:
        print("  !! ComfyUI 服务未起来")
        srv.terminate()
        return

    def submit(prompt_text, out_png, timeout=900):
        wf = {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": SEEDS[0], "steps": STEPS, "cfg": 7.0, "sampler_name": "euler",
                "scheduler": "normal", "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": SIZE[0], "height": SIZE[1], "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": prompt_text, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": "", "clip": ["4", 1]}},
            "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "b4",
                                                        "images": ["9", 0]}},
            "9": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0],
                                                        "vae": ["4", 2]}},
        }
        req = urllib.request.Request(base + "/prompt",
                                     data=json.dumps({"prompt": wf}).encode(),
                                     headers={"Content-Type": "application/json"})
        pid = json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]
        t0 = time.time()
        while True:
            h = json.loads(urllib.request.urlopen(base + f"/history/{pid}",
                                                  timeout=10).read())
            if pid in h:
                outs = h[pid].get("outputs", {})
                for node in outs.values():
                    for im in node.get("images", []):
                        src = os.path.join(E04, "ComfyUI", "output", im["filename"])
                        if os.path.exists(src):
                            import shutil
                            shutil.copyfile(src, out_png)
                return time.time() - t0
            if time.time() - t0 > timeout:
                raise TimeoutError("comfy history timeout")
            time.sleep(2)

    for p in range(len(PROMPTS)):
        for r in range(len(SEEDS)):
            tag = f"comfyui_p{p}_s{SEEDS[0]}"
            if has(tag):
                print(f"  {tag:<28} skip(已有)", flush=True)
                continue
            out = os.path.join(OUTDIR, tag + ".png")
            try:
                dt = submit(PROMPTS[p], out)
                err = ""
            except Exception as e:
                dt, err = time.time() - t0, str(e)[-300:]
            peak = None
            try:
                st = json.loads(urllib.request.urlopen(base + "/system_stats",
                                                       timeout=5).read())
                for dev in st.get("devices", []):
                    peak = dev.get("vram_free") and None
            except Exception:
                pass
            # 内存取 server 进程 RSS
            try:
                peak = psutil.Process(srv.pid).memory_info().rss
            except Exception:
                pass
            ok = os.path.exists(out) and os.path.getsize(out) > 1000
            PROGRESS["rows"].append({
                "cell": tag, "scheme": "comfyui", "prompt_idx": p,
                "run_idx": r, "seed": SEEDS[0], "steps": STEPS, "size": "512x512",
                "seconds": round(dt, 2), "mem_peak": peak,
                "ok": ok, "err": err if not ok else ""})
            save()
            print(f"  {tag:<28} {dt:6.1f}s peak={peak//1048576 if peak else '?'}MB "
                  f"{'OK' if ok else 'FAIL'}", flush=True)
            if ONCE:
                return
    srv.terminate()
    try:
        srv.wait(15)
    except Exception:
        srv.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="跑一格即返回(前台单格,避免超时孤儿)")
    ap.add_argument("--only", choices=["sdcpp-cpu", "sdcpp-vulkan", "diffusers", "comfyui"],
                    required=True)
    a = ap.parse_args()
    global ONCE
    ONCE = a.once
    PROGRESS["rows"] = load_rows()
    print(f"已有 {len(PROGRESS['rows'])} 格(断点续跑)", flush=True)
    print(f"scheme={a.only} | prompt×{len(PROMPTS)} | seeds={SEEDS} | "
          f"{SIZE[0]}x{SIZE[1]} | steps={STEPS} | seeds={SEEDS}", flush=True)
    if a.only.startswith("sdcpp"):
        run_sdcpp(a.only.split("-")[1])
    elif a.only == "diffusers":
        run_diffusers()
    else:
        run_comfy()
    print(f"\ndone. blocked={sorted(set(_BLOCKED)) or 0} rows={len(PROGRESS['rows'])}")


if __name__ == "__main__":
    main()
