# -*- coding: utf-8 -*-
"""ep12 跑测 driver：逐格拉起子进程，断点续跑。

开跑前的硬检查（skill §4：别凭记忆报数字）：
  1. 只读算一遍任务清单，打印 总数/已完成/剩余
  2. 每格目标产物先删（防上一轮残留冒充本轮成果）
  3. 断言样本图与 GT 的 hash 与跑前一致（方案 §3.1 data_hash）
  4. 检查没有别的测量进程在跑（并发测量会互相抢 CPU）

跑法：单格一个子进程，外层循环逐格拉起。progress append-only + attempt 计数。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

BASE = r"D:/study/ai-jms/ep12-ocr2-venvs"
E11 = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr"
E12 = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep12-ocr2"
CELLS = os.path.join(BASE, "cells")
PROGRESS = os.path.join(BASE, "progress_ep12.jsonl")

# 每个引擎有独立 venv（方案 §2.1 隔离），driver 必须按引擎选解释器。
# 实测教训：写死 ep11 的 venv 会让 rapidocrlite 报 ModuleNotFoundError，
# 而这个错**不带 traceback 前缀、退出码仍是 0**，只看日志尾像"跑完了"。
VENV = {
    "rapidocrlite-medium": os.path.join(BASE, "venv-rapidocrlite/Scripts/python.exe"),
    "rapidocrlite-small":  os.path.join(BASE, "venv-rapidocrlite/Scripts/python.exe"),
    "rapidocrlite-lite":   os.path.join(BASE, "venv-rapidocrlite/Scripts/python.exe"),
    "paddleocr":           r"D:/study/ai-jms/ai-radar-trend/.venv/Scripts/python.exe",
    "easyocr":             os.path.join(BASE, "venv-easyocr/Scripts/python.exe"),
    # simdpaddleocr 的 runner 是 Python、引擎是 dotnet 子进程 → 任一有 psutil 的解释器都行
    "simdpaddleocr":       os.path.join(BASE, "venv-easyocr/Scripts/python.exe"),
    "simdpaddleocr-default": os.path.join(BASE, "venv-easyocr/Scripts/python.exe"),
    "glmocr":              os.path.join(BASE, "venv-glmocr/Scripts/python.exe"),
    # lightonocr 与 glmocr 同走 Ollama HTTP 接口，复用同一解释器即可
    "lightonocr":          os.path.join(BASE, "venv-glmocr/Scripts/python.exe"),
}


def py_for(engine):
    p = VENV.get(engine)
    if not p or not os.path.exists(p):
        raise SystemExit("FATAL 引擎 %s 没有可用解释器（%s）" % (engine, p))
    return p

# 引擎 → 单次推理超时上限（秒）。
#
# ⚠️ 这里给的是**单次推理**的上限，整格超时由 cell_timeout() 按
#    (warmup + runs) × 单次上限 现算。
#
# 为什么不能直接拿它当整格超时（2026-10-25 实测踩到）：
#   一格 = warmup 2 次 + runs 3 次 = 5 次推理。paddleocr 单次约 70 s，
#   5 次就是 350 s，而我当时把整格超时拍成 300 s → 首格就被杀，
#   日志只留一句 TIMEOUT，看起来像"引擎挂了"，其实是盒子设小了（skill §4）。
#
# 取值依据（ep11 实测单页最大值 × 1.3 余量）：
#   rapidocr 类 97s → 130s；paddleocr 同量级 → 150s；
#   simdpaddleocr 冒烟最大 7.9s → 40s；easyocr 冒烟最大 10.6s → 60s；
#   glmocr 实测单页最大 150.3s → 400s。
PER_INFER_TIMEOUT = {
    "rapidocrlite-medium": 130, "rapidocrlite-lite": 130,
    "rapidocrlite-small":  130,
    "paddleocr": 150, "easyocr": 60,
    "simdpaddleocr": 40, "simdpaddleocr-default": 40,
    "glmocr": 400,
    # lightonocr 暂借 glmocr 的 400s；冒烟拿到真实单页耗时后按实测 ×1.3 改
    "lightonocr": 400,
}


def cell_timeout(engine, warmup, runs):
    """整格超时 = (warmup + runs) × 单次上限，再加 120 s 装载余量。"""
    per = PER_INFER_TIMEOUT.get(engine, 300)
    return (warmup + runs) * per + 120
MEM_LIMIT_MB = {"rapidocrlite-medium": 950, "rapidocrlite-lite": 950,
                "paddleocr": 4470, "easyocr": 6000,
                "simdpaddleocr": 2000, "simdpaddleocr-default": 2000,
                "glmocr": 4850,
                # LightOnOCR-3 权重 1.02GB（Q8_0）小于 GLM-OCR 的 2.66GB（F16），
                # 阈值暂按 ep11 引擎阈值 ×1.3 取保守值，实测峰值出来后再校准
                "lightonocr": 3500}

ENGINES = ["rapidocrlite-medium", "rapidocrlite-lite", "simdpaddleocr",
           "simdpaddleocr-default", "paddleocr", "easyocr", "glmocr",
           "lightonocr"]


def samples():
    """样本清单 = ep11 的 18 张 + ep12 新增 8 张。"""
    out = []
    for d, tag in ((os.path.join(E11, "output", "samples"), "ep11"),
                   (os.path.join(E12, "output", "samples"), "ep12")):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(".png"):
                out.append((os.path.join(d, f), tag))
    return out


def gt_path(img):
    b = os.path.splitext(os.path.basename(img))[0]
    for d in (os.path.join(E12, "gt"), os.path.join(E11, "gt")):
        p = os.path.join(d, b + ".txt")
        if os.path.exists(p):
            return p
    return None


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def load_progress():
    done = {}
    if not os.path.exists(PROGRESS):
        return done
    with open(PROGRESS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("status") == "ok":
                c = r.get("cell")
                if c and (c not in done or r.get("attempt", 0) >= done[c].get("attempt", 0)):
                    done[c] = r
    return done


def append(r):
    with open(PROGRESS, "a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")


def other_measures():
    """有没有别的测量进程在跑（并发测量会互相抢 CPU）。

    ⚠️ 别用裸子串匹配 —— 实测把发起这条命令的 bash 自己匹配了进去
    （它的 cmdline 里含 "cell_runner.py"），于是 FATAL 拦下自己。
    正解（skill §4）：按**脚本完整路径**认实例、按**可执行名**认引擎进程，
    并排除自己与祖先链。
    """
    try:
        import psutil
    except Exception:
        return []
    me = psutil.Process()
    own = {me.pid}
    try:
        for a in me.parents():
            own.add(a.pid)
    except Exception:
        pass
    runner_abs = os.path.abspath(os.path.join(BASE, "cell_runner.py")).lower()
    hits = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "exe"]):
        pid = p.info.get("pid")
        if pid in own:
            continue
        exe = (p.info.get("exe") or "").lower()
        if "python" not in exe and "dotnet" not in exe:
            continue                      # 只认 Python / .NET 进程
        cl = " ".join(p.info.get("cmdline") or [])
        cll = cl.lower()
        if runner_abs in cll:             # 完整路径命中 = 真的在跑我们的 runner
            hits.append((pid, cl[:100]))
        elif "simdbench" in cll and "build" not in cll and "run" not in cll.split("simdbench")[0][-8:]:
            hits.append((pid, cl[:100]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", default=",".join(ENGINES))
    ap.add_argument("--limit-per-engine", type=int, default=0,
                    help=">0 时每引擎只跑前 N 张（冒烟用）")
    ap.add_argument("--smoke", action="store_true", help="冒烟：每引擎前 2 张 × 1 次推理")
    ap.add_argument("--force", action="store_true", help="忽略已完成，重跑")
    args = ap.parse_args()

    eng_list = [e.strip() for e in args.engines.split(",") if e.strip()]
    runs = 1 if args.smoke else 3
    warmup = 0 if args.smoke else 2
    lim = 2 if args.smoke else args.limit_per_engine

    imgs = samples()
    if not imgs:
        print("FATAL 没有样本图"); return 2

    # 硬检查 1：并发测量
    busy = other_measures()
    if busy:
        print("FATAL 已有测量进程在跑（并发会互相抢 CPU）:")
        for pid, cl in busy:
            print("   pid=%s %s" % (pid, cl))
        return 3

    # 硬检查 2：GT 存在性（只读，不改）
    missing = [i for i, _ in imgs if gt_path(i) is None]
    if missing:
        print("FATAL 以下样本缺 GT:")
        for m in missing[:10]:
            print("   ", m)
        return 4

    # 硬检查 3：任务清单只读算一遍
    todo_all = []
    for e in eng_list:
        use = imgs[:lim] if lim else imgs
        for img, tag in use:
            todo_all.append((e, img, tag))
    done = {} if args.force else load_progress()
    pending = [t for t in todo_all
               if ("%s__%s" % (t[0], os.path.splitext(os.path.basename(t[1]))[0])) not in done]

    print("=" * 84)
    print("ep12 跑测 driver   smoke=%s  force=%s" % (args.smoke, args.force))
    print("=" * 84)
    print("  样本: %d 张（ep11 复用 %d + ep12 新增 %d）" % (
        len(imgs), sum(1 for _, t in imgs if t == "ep11"),
        sum(1 for _, t in imgs if t == "ep12")))
    print("  引擎: %d 个 — %s" % (len(eng_list), ", ".join(eng_list)))
    print("  每格 runs=%d warmup=%d" % (runs, warmup))
    print("  总格数: %d    已完成: %d    剩余: %d" % (
        len(todo_all), len(todo_all) - len(pending), len(pending)))
    print("  预计推理次数: %d" % (len(pending) * runs))
    print("=" * 84)

    # 抽样打印 hash，供跑后校验
    probe = imgs[0][0]
    print("  data_hash 抽样: %s = %s" % (os.path.basename(probe), sha16(probe)))
    gtp = gt_path(probe)
    print("  GT hash 抽样:   %s = %s" % (os.path.basename(gtp), sha16(gtp)))
    print("=" * 84, flush=True)

    if not pending:
        print("没有待跑的格子。")
        return 0

    t_batch = time.time()
    n_ok = n_err = 0
    for i, (eng, img, tag) in enumerate(pending):
        b = os.path.splitext(os.path.basename(img))[0]
        cell = "%s__%s" % (eng, b)
        outp = os.path.join(CELLS, cell + ".json")
        # 硬检查 4：目标产物先删，只认本轮新生成的
        if os.path.exists(outp):
            try:
                os.remove(outp)
            except OSError:
                pass
        old_ts = os.path.getmtime(outp) if os.path.exists(outp) else 0

        cmd = [py_for(eng), os.path.join(BASE, "cell_runner.py"),
               "--engine", eng, "--img", img, "--cell", cell,
               "--runs", str(runs), "--warmup", str(warmup)]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=cell_timeout(eng, warmup, runs),
                               cwd=BASE)
            tail = (r.stdout or "").strip().splitlines()
            last = tail[-1] if tail else "(无输出)"
        except subprocess.TimeoutExpired:
            last = "TIMEOUT 超 %ds 被杀（(warmup+runs)=%d × 单次%d + 120）" % (
                cell_timeout(eng, warmup, runs), warmup + runs,
                PER_INFER_TIMEOUT.get(eng, 300))
        el = time.time() - t0

        rec = {"cell": cell, "engine": eng, "img": os.path.basename(img),
               "src": tag, "status": "ok", "wall_s": round(el, 2),
               "ts": time.time(), "attempt": 1}
        # 只认本轮新产物
        if not os.path.exists(outp) or os.path.getmtime(outp) <= old_ts:
            rec["status"] = "no_output"
            n_err += 1
        else:
            try:
                d = json.load(open(outp, encoding="utf-8"))
                rec.update({k: d.get(k) for k in
                            ("median", "min", "max", "spread_pct", "t_infers",
                             "peak_rss_mb", "peak_rss_samples", "peak_rss_at_load_mb",
                             "text_len", "n_lines", "err",
                             "warmup_times", "warmup_converged", "settings",
                             "rss_scope", "t_total", "extra", "py", "seg")})
                if d.get("err"):
                    rec["status"] = "engine_err"
                    n_err += 1
                else:
                    n_ok += 1
            except Exception as e:
                rec["status"] = "read_err"
                rec["err"] = str(e)
                n_err += 1
        append(rec)
        print("  [%3d/%d] %-34s %6.1fs  %s" % (
            i + 1, len(pending), cell[:34], el, last[:64]), flush=True)

    print("\n" + "=" * 84)
    print("本轮完成: %d 格  ok=%d  异常=%d  总耗时 %.1f min" % (
        len(pending), n_ok, n_err, (time.time() - t_batch) / 60))
    print("progress: %s" % PROGRESS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
