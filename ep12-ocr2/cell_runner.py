# -*- coding: utf-8 -*-
"""ep12 单格 runner：一个子进程跑一个格子，跑完即退。

为什么单格一个子进程（skill §4）：Windows 上父进程被杀时，它 subprocess 起的
引擎进程不会跟着死，孤儿同抢 CPU 会让整批耗时静默虚高 1.8-3 倍且零报错。
单格驱动没有孤儿窗口，单格时长也天然躲开前台超时截断。

照抄 ep11 bench_cell.py 的口径（原脚本 L101-135）：
  1. hot 模式先同进程预热 --warmup 次，不计时
  2. 预热收敛判据：最后两轮相差 <2%，不收敛再加跑一轮
  3. 计时只包 eng.infer()，模型元数据统计在计时窗口外
  4. runs 次 infer，取 t_first 与列表
  5. 内存 = 整棵子进程树 Working Set 峰值，每 200 ms 采一次

内存采样按引擎分叉（这是本期实测踩出来的）：
  - Python/.NET 引擎：从本进程递归子进程树
  - glmocr：推理发生在 llama-server.exe，它是 ollama.exe serve 的子进程，
    **不是**本进程的子进程 → 必须从 ollama serve 那棵树采，
    按进程名匹配（只 match 'ollama'）会漏掉 llama-server，低估 83 倍。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
OUT_DIR = r"D:/study/ai-jms/ep12-ocr2-venvs/cells"
os.makedirs(OUT_DIR, exist_ok=True)


def _require_psutil():
    """内存峰值是方案 §4.1 的必测项。缺 psutil 时必须报错，不能静默返回空 ——
    静默会让 peak_rss_mb 全是 0.0，看着像"引擎不占内存"，实际是"没测"。
    实测教训：venv-rapidocrlite 与 venv-easyocr 都缺它，第一轮冒烟内存列全 0.0。
    """
    try:
        import psutil  # noqa: F401
        return True
    except Exception:
        return False


def _tree_wset_pids():
    """本进程 + 全部后代的 pid 列表。"""
    try:
        import psutil
        me = psutil.Process()
        pids = [me.pid]
        for c in me.children(recursive=True):
            pids.append(c.pid)
        return pids
    except Exception:
        return []


def _ollama_tree_pids():
    """从 ollama.exe serve 递归的整棵树 pid（glmocr 专用）。"""
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


class Sampler:
    """内存峰值采样：起独立子进程，每 200 ms 采一次 Working Set。

    ⚠️ 不用线程。线程版在 onnxruntime 推理期间几乎得不到调度 —— 实测 12.7 s
    的格子只采到 3 帧（本该约 63 帧），推理把 CPU 核全占满把采样线程饿死，
    于是 peak 只有 41 MB（= 解释器本身），真实峰值 964 MB 被完全错过。
    独立进程有自己的 OS 调度时间片，不受推理影响。
    """

    def __init__(self, mode="self"):
        self.mode = mode
        self._proc = None
        self._out = None

    def __enter__(self):
        fd, self._out = tempfile.mkstemp(prefix="rss_", suffix=".json",
                                        dir=os.path.dirname(os.path.abspath(__file__)))
        os.close(fd)
        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "sampler_child.py"),
               "--root-pid", str(os.getpid()), "--mode", self.mode,
               "--out", self._out, "--interval", "0.2"]
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)
        except Exception as e:
            raise RuntimeError("内存采样子进程启动失败: %s" % e)
        time.sleep(0.35)          # 让它至少采到一帧
        return self

    def __exit__(self, *a):
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        return False

    def _read(self):
        # 读到坏 JSON 时重试而非立刻返回 {}：原子写已修掉主因，
        # 这里是兜底（首次读时子进程可能还没写过任何一帧）。
        for i in range(6):
            try:
                with open(self._out, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                time.sleep(0.05)
        return {}

    @property
    def peak_mb(self):
        d = self._read()
        return round((d.get("peak_bytes") or 0) / 1e6, 1)

    @property
    def samples(self):
        return self._read().get("samples", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--img", required=True)
    ap.add_argument("--cell", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--session", default="ep12-main")
    args = ap.parse_args()

    t_entry = time.perf_counter()
    rec = {"schema": "ep12-cell-v1", "cell": args.cell, "engine": args.engine,
           "img": os.path.basename(args.img), "imgpath": args.img,
           "runs": args.runs, "warmup": args.warmup,
           "attempt": args.attempt, "session": args.session,
           "py": sys.version.split()[0], "ts": time.time(),
           "threads": {"cpu_count": os.cpu_count()}}
    try:
        import torch
        rec["threads"]["torch_num_threads"] = torch.get_num_threads()
    except Exception:
        pass

    err = ""
    seg = {}
    try:
        # 硬门：内存峰值是必测项，缺 psutil 就停，不许静默出 0.0
        if not _require_psutil():
            raise RuntimeError(
                "psutil 未安装 —— 内存峰值无法采集（方案 §4.1 必测项）。"
                "请先装：pip install psutil")

        t0 = time.perf_counter()
        sys.path.insert(0, BASE)
        import engine_base_ep12 as eb
        seg["t_import"] = round(time.perf_counter() - t0, 6)

        eng = eb.make_engine(args.engine)
        # ⚠️ 走 Ollama 的引擎都必须用 "ollama" 模式采内存：推理发生在
        #    llama-server.exe，它是 ollama.exe serve 的子进程、**不是**本进程的
        #    子进程。用 "self" 只会采到 Python 自己那点内存（实测 lightonocr
        #    读到 232 MB，而模型本身就有 1.02 GB），且这个错零报错。
        samp_mode = "ollama" if args.engine in ("glmocr", "lightonocr") else "self"
        t0 = time.perf_counter()
        with Sampler(samp_mode) as samp:
            eng.load()
            seg["t_session"] = round(time.perf_counter() - t0, 6)
            # ⚠️ 这里不读 peak_rss_mb —— 那时推理还没开始，读到的只是加载期峰值
            #    （实测读到 41 MB，而真实峰值 964 MB）。峰值在推理全部结束后统一读。
            rec["peak_rss_at_load_mb"] = samp.peak_mb
            rec["rss_scope"] = ("ollama-serve 进程树（推理在 llama-server.exe）"
                                if samp_mode == "ollama" else "本进程 + 后代进程树")

            rec["settings"] = eng.settings()

            # 预热（不计时）
            wt = []
            if args.warmup > 0:
                for _ in range(args.warmup):
                    tw = time.perf_counter()
                    r = eng.infer(args.img)
                    wt.append(time.perf_counter() - tw)
                    if r.err:
                        err = "warmup: " + r.err
                        break
            if err:
                raise RuntimeError(err)
            conv = True
            if len(wt) >= 2:
                conv = abs(wt[-1] - wt[-2]) / max(wt[-2], 1e-9) < 0.02
                if not conv:
                    tw = time.perf_counter()
                    r = eng.infer(args.img)
                    wt.append(time.perf_counter() - tw)
                    conv = abs(wt[-1] - wt[-2]) / max(wt[-2], 1e-9) < 0.02
            rec["warmup_times"] = [round(x, 4) for x in wt]
            rec["warmup_converged"] = bool(conv)

            t_infers = []
            text = ""
            extra = {}
            for i in range(args.runs):
                t0 = time.perf_counter()
                r = eng.infer(args.img)
                t_infers.append(time.perf_counter() - t0)
                if i == 0:
                    text = r.text
                    extra = r.extra
                if r.err:
                    err = r.err
                    break

            # 全程峰值：推理全部结束后读（这才是 peak_rss_mb）
            rec["peak_rss_mb"] = samp.peak_mb
            rec["peak_rss_samples"] = samp.samples

        rec["t_infers"] = [round(x, 4) for x in t_infers]
        if t_infers:
            s = sorted(t_infers)
            rec["median"] = round(s[len(s) // 2], 4)
            rec["min"] = round(s[0], 4)
            rec["max"] = round(s[-1], 4)
            rec["spread_pct"] = round((s[-1] - s[0]) / max(s[len(s) // 2], 1e-9) * 100, 2)
        rec["text"] = text
        rec["text_len"] = len(text)
        rec["n_lines"] = len(r.lines) if not err else 0
        rec["extra"] = extra
        rec["err"] = err
    except Exception as e:
        rec["err"] = "%s: %s" % (type(e).__name__, e)
        rec["text"] = ""
        rec["text_len"] = 0

    rec["seg"] = seg
    rec["t_total"] = round(time.perf_counter() - t_entry, 4)
    out = os.path.join(OUT_DIR, args.cell + ".json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print("CELL_DONE cell=%s median=%s n_lines=%s err=%s" % (
        args.cell, rec.get("median"), rec.get("n_lines"), (err or "")[:70]))


if __name__ == "__main__":
    main()
