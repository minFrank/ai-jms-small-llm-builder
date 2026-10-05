# ep04 · 扩展实测（A 2核降配 / B 分辨率曲线 / C 题材鲁棒性）
# 纪律：串行、每单元即刻落盘、断点续跑（比对单元号+输入特征，一致即复用）
import argparse, json, os, subprocess, time, datetime, sys

M = "D:/models/txt2img"
MODEL = os.path.join(M, "v1-5-pruned-emaonly.safetensors")
CPU = os.path.join(M, "cpu", "sd-cli.exe")
VULKAN = os.path.join(M, "vulkan", "sd-cli.exe")
OUT = os.path.join(M, "out")
LOG = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs"
PROG = os.path.join(LOG, "bench2-progress.json")

PROMPTS = {
    "p0_lake":   "a quiet lake at dawn, mist over the water, pine trees on the far shore, soft light, digital painting",
    "p1_desk":   "a wooden desk by a window, open notebook, cup of tea, morning sunlight, realistic photo",
}
# C 题材鲁棒性：5 类读者常画的题材（每类判一次）
TOPICS = {
    "portrait":  "portrait of an elderly fisherman with wrinkled face, weathered skin, detailed eyes, photorealistic",
    "crowd":     "a busy street market with many people walking, stalls, lanterns, wide angle, illustration",
    "chart":     "a simple bar chart on white background, three blue bars of different heights, clean infographic style",
    "anime":     "anime girl with blue hair standing under cherry blossoms, soft lighting, high quality",
    "macro":     "macro photo of a dew drop on a green leaf, extreme detail, shallow depth of field",
}

def mem_peak():
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
    except Exception:
        return None

def load():
    if os.path.exists(PROG):
        try:
            return json.load(open(PROG, encoding="utf-8"))
        except Exception:
            return []
    return []

def save(rows):
    tmp = PROG + ".tmp"
    json.dump(rows, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, PROG)

def seen(rows, cell):
    return any(r["cell"] == cell for r in rows)

def run(cell, prompt, backend, steps, w, h, threads, cores, topic_tag):
    """跑一个单元。cores>0 时用 start /affinity 限核（Windows 亲和性掩码）"""
    exe = CPU if backend == "cpu" else VULKAN
    png = os.path.join(OUT, f"{cell}.png")
    raw = os.path.join(LOG, f"raw-{cell}.txt")
    cmd = [exe, "-m", MODEL, "-p", prompt, "-W", str(w), "-H", str(h),
           "--steps", str(steps), "-s", "42", "-o", png]
    if backend == "vulkan":
        cmd += ["--backend", "diffusion=vulkan0"]
    if threads and backend == "cpu":
        cmd += ["-t", str(threads)]
    peak = 0
    t0 = time.time()
    with open(raw, "w", encoding="utf-8") as f:
        f.write(f"# {datetime.datetime.now().isoformat()}\n# cell={cell}\n# cmd={' '.join(cmd)}\n\n")
        f.flush()
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=M)
        while p.poll() is None:
            m = mem_peak()
            if m:
                peak = max(peak, m)
            time.sleep(0.3)
        rc = p.returncode
    dur = time.time() - t0
    rec = {"cell": cell, "backend": backend, "steps": steps, "size": f"{w}x{h}",
           "threads": threads, "cores_limit": cores, "topic": topic_tag,
           "prompt": prompt[:60], "seconds": round(dur, 2), "returncode": rc,
           "mem_peak": peak or None,
           "png_bytes": os.path.getsize(png) if os.path.exists(png) else 0,
           "raw": raw, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    rows = load(); rows.append(rec); save(rows)
    print(f"[{cell}] {dur:6.1f}s rc={rc} png={rec['png_bytes']} peak={peak or 0} ", flush=True)
    return rec

def cells(spec):
    """展开任务清单"""
    out = []
    if "A" in spec:      # 2核降配：限制到 2 个逻辑核，重跑关键 4 格
        for b in ("cpu",):
            for s in (20, 8):
                for pn, pv in PROMPTS.items():
                    out.append(dict(cell=f"A_{b}_s{s}_{pn}", prompt=pv, backend=b,
                                    steps=s, w=512, h=512, threads=None, cores=2, topic=pn))
    if "B" in spec:      # 分辨率曲线：512/768/1024 × 双后端 × 20步 × 1句 × 2跑
        for w in (512, 768, 1024):
            for b in ("cpu", "vulkan"):
                for r in (0, 1):
                    out.append(dict(cell=f"B_{b}_{w}_r{r}", prompt=PROMPTS["p0_lake"], backend=b,
                                    steps=20, w=w, h=w, threads=None, cores=0, topic="res"))
    if "C" in spec:      # 题材鲁棒性：5 题材 × 双后端 × 20步 × 1跑
        for tn, tv in TOPICS.items():
            for b in ("cpu", "vulkan"):
                out.append(dict(cell=f"C_{b}_{tn}", prompt=tv, backend=b,
                                steps=20, w=512, h=512, threads=None, cores=0, topic=tn))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="ABC")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    task = cells(args.spec)
    rows = load()
    # 上一版 A 组因 start /affinity 引号坑全部 rc=1，失败单元一律重跑
    fail_cells = {r["cell"] for r in rows if r["returncode"] != 0 and r["cell"].startswith("A_")}
    if fail_cells:
        rows = [r for r in rows if r["cell"] not in fail_cells]
        save(rows)
        print(f"清掉上一版失败的 A 单元 {len(fail_cells)} 个，准备重跑", flush=True)
    todo = [t for t in task if not seen(rows, t["cell"])]
    if args.limit:
        todo = todo[:args.limit]
    print(f"总任务 {len(task)} · 已完成 {len(task) - len([t for t in task if not seen(rows, t['cell'])])} · 本次跑 {len(todo)}", flush=True)
    print(f"基线(同名进程): {mem_peak()} · {datetime.datetime.now()}", flush=True)
    for i, t in enumerate(todo, 1):
        # A 组限核：Windows 下用 START /AFFINITY（2 核 = 掩码 0x3）
        if t["cores"] == 2:
            # 亲和性用 psutil 设（cmd 的 start /affinity 会把第一个引号参数当窗口标题 —— 2026-09-30 实测踩坑）
            import psutil
            exe = CPU
            png = os.path.join(OUT, f"{t['cell']}.png")
            raw = os.path.join(LOG, f"raw-{t['cell']}.txt")
            cmd = [exe, "-m", MODEL, "-p", t["prompt"], "-W", str(t["w"]), "-H", str(t["h"]),
                   "--steps", str(t["steps"]), "-s", "42", "-o", png]
            peak, aff = 0, None
            t0 = time.time()
            with open(raw, "w", encoding="utf-8") as f:
                f.write(f"# {datetime.datetime.now().isoformat()} 亲和性=前2个逻辑核(psutil)\n# {' '.join(cmd)}\n\n")
                f.flush()
                proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=M)
                try:
                    psutil.Process(proc.pid).cpu_affinity([0, 1])   # 限到 2 个逻辑核
                    aff = psutil.Process(proc.pid).cpu_affinity()
                except Exception as e:
                    aff = f"设置失败: {e}"
                while proc.poll() is None:
                    m = mem_peak()
                    if m:
                        peak = max(peak, m)
                    time.sleep(0.3)
                rc = proc.returncode
            dur = time.time() - t0
            rec = dict(t); rec.update(seconds=round(dur, 2), returncode=rc, mem_peak=peak or None,
                                      png_bytes=os.path.getsize(png) if os.path.exists(png) else 0,
                                      affinity=aff, raw=raw,
                                      ts=datetime.datetime.now().isoformat(timespec="seconds"))
            rec.pop("prompt")
            rows = load(); rows.append(rec); save(rows)
            print(f"[{t['cell']}] {dur:6.1f}s rc={rc} png={rec['png_bytes']} peak={peak or 0} aff={aff}", flush=True)
        else:
            run(t["cell"], t["prompt"], t["backend"], t["steps"], t["w"], t["h"],
                t["threads"], t["cores"], t["topic"])
        print(f"  进度 {i}/{len(todo)}", flush=True)
    print("本批完成", flush=True)

if __name__ == "__main__":
    main()
