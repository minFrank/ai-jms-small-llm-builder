#!/usr/bin/env python3
"""ep13 期资产一键清理（规格 §4.6）。默认 dry-run。"""
import sys, os, shutil, json, time, tarfile

EP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ep13-docparse/
DATA_DIRS = ["cells", "runs", "sessions", "control", "outputs", "archive"]
CONFIG_FILES = ["engines.yaml", "sets.yaml"]
LOG = os.path.join(EP, "CLEANUP.log")

def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024: return "%.1f%s" % (n, u)
        n /= 1024
    return "%.1fTB" % n

def size(p):
    if os.path.isfile(p): return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs)

def targets(kind):
    if kind == "data":     return [os.path.join(EP, d) for d in DATA_DIRS]
    if kind == "config":   return [os.path.join(EP, f) for f in CONFIG_FILES] + [os.path.join(EP, "control")]
    if kind == "models":   return [r"D:/models/models/ocr/ep13-docparse"]
    return []

def main():
    args = sys.argv[1:]
    ep = args[0] if args else None
    kind = "data"
    for a in args[1:]:
        if a in ("--data", "--config", "--models"): kind = a[2:]
        if a == "--no-archive": pass
    if ep != "ep13":
        print("用法: clean_episode.py ep13 [--data|--config|--models]   （默认 dry-run + --data）")
        print("注意: 模型默认永不清理，必须显式 --models；dry-run 不删任何东西。")
        return 1
    tgts = [p for p in targets(kind) if os.path.exists(p)]
    if not tgts:
        print("无 %s 目标可清。" % kind); return 0
    total = sum(size(p) for p in tgts)
    print("=== DRY-RUN：将清理 %s（共 %s）===" % (kind, human(total)))
    for p in tgts: print("  %s  %s" % (p, human(size(p))))
    if "--yes" not in args:
        print("（确认无误后加 --yes 执行；数据类清理会先打包 archive）")
        return 0
    if kind == "models":
        print("拒绝自动删模型：模型是跨期共享资产，请手动确认后删除目录。"); return 1
    if kind == "data" and "--no-archive" not in args:
        arc = os.path.join(EP, "archive", "ep13-%s.tar.zst" % time.strftime("%Y%m%d-%H%M%S"))
        # 用 tar（zst 不可用时退 gzip）
        arc = arc.replace(".zst", ".tar.gz")
        with tarfile.open(arc, "w:gz") as tf:
            for p in tgts:
                if os.path.basename(p) == "archive": continue
                tf.add(p, arcname=os.path.relpath(p, EP))
        print("已打包: %s (%s)" % (arc, human(os.path.getsize(arc))))
    for p in tgts:
        shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("%s kind=%s size=%s by=%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), kind, human(total), os.environ.get("USERNAME", "?")))
    print("完成。清理记录 → CLEANUP.log")
    return 0

if __name__ == "__main__":
    sys.exit(main())
