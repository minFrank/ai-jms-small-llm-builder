# -*- coding: utf-8 -*-
"""ep13 全量进度现算（cron 简报用）。只读，不写任何状态。"""
import json, os, glob, statistics, datetime, collections

EP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = "ep13-full-001"
ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]
NOW = datetime.datetime.now()

out = {}

# 1) batch_state
st = json.load(open(os.path.join(EP, "control", "batch_state.json"), encoding="utf-8"))
out["batch_state"] = st
lp = datetime.datetime.now().fromisoformat(st["last_progress"])
out["last_progress_age_min"] = round((NOW - lp).total_seconds() / 60.0, 1)
sa = datetime.datetime.now().fromisoformat(st["started_at"])
out["batch_elapsed_min"] = round((NOW - sa).total_seconds() / 60.0, 1)

# 2) manifest
man = json.load(open(os.path.join(EP, "samples", "manifest.json"), encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
imgs = sorted(sha2img.values())
out["n_samples"] = len(imgs)

# 3) cells
cells = []
for p in sorted(glob.glob(os.path.join(EP, "cells", RUN, "*.json"))):
    try:
        c = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        cells.append({"_path": p, "status": "PARSE_ERR", "err": str(e)})
        continue
    c["_path"] = os.path.basename(p)
    c["_mtime"] = datetime.datetime.fromtimestamp(os.path.getmtime(p))
    cells.append(c)
out["n_cell_files"] = len(cells)


def terminal(c):
    if c.get("status") not in ("complete", "partial", "failed"):
        return False
    if "schema_err" in str(c.get("err") or ""):
        return False
    return True


def matched(c):
    """cell 的 input.sha256 是否对上 manifest（即属于本全量样本集）"""
    return c.get("input", {}).get("sha256") in sha2img


# 4) 总体进度：156 个 (img, engine) 任务里已完成（terminal 且 sha 匹配）
done_pairs = set()
for c in cells:
    if terminal(c) and matched(c):
        sha = c["input"]["sha256"]
        eng = c.get("engine")
        done_pairs.add((sha2img[sha], eng))
total_tasks = len(imgs) * len(ENGINES)
out["overall"] = {"done": len(done_pairs), "total": total_tasks}

# 4b) 本批（batch_state 所指引擎）进度
cur_eng = (st.get("current") or "").split("×")[-1]
batch_done = sum(1 for k in done_pairs if k[1] == cur_eng)
out["cur_engine"] = cur_eng
out["batch_engine_done"] = batch_done

# 5) 状态分布（按引擎，只算 sha 匹配本样本集的 cell；同 sha+engine 取 mtime 最新）
latest = {}
for c in cells:
    if not matched(c):
        continue
    key = (sha2img[c["input"]["sha256"]], c.get("engine"))
    if key not in latest or c["_mtime"] > latest[key]["_mtime"]:
        latest[key] = c
dist = collections.defaultdict(collections.Counter)
for (img, eng), c in latest.items():
    dist[eng][c.get("status")] += 1
out["dist"] = {e: dict(dist[e]) for e in ENGINES if dist[e]}

# 6) CER / wall（取最新 cell；正常格 cer<0.5）
cers, walls, outliers, noncomplete = [], [], [], []
for (img, eng), c in sorted(latest.items()):
    cer = c.get("cer_median")
    wall = c.get("wall_median")
    if isinstance(wall, (int, float)):
        walls.append(wall)
    if c.get("status") != "complete":
        noncomplete.append("%s×%s[%s]" % (eng, img, c.get("status")))
    if isinstance(cer, (int, float)):
        if cer < 0.5:
            cers.append(cer)
        else:
            outliers.append((round(cer, 3), eng, img))
out["cer_normal_n"] = len(cers)
out["cer_normal_median"] = round(statistics.median(cers), 4) if cers else None
out["outliers"] = sorted(outliers, reverse=True)
out["wall_median_s"] = round(statistics.median(walls), 1) if walls else None
out["wall_n"] = len(walls)
out["noncomplete"] = noncomplete

# 7) 速率：本批 n_run 格耗时
try:
    n_run = int(st["n_run"])
    elapsed = (NOW - sa).total_seconds() / 60.0
    out["rate_min_per_cell"] = round(elapsed / n_run, 1) if n_run else None
    seq_i = int(str(st["seq"]).split("/")[0])
    seq_total = int(str(st["seq"]).split("/")[1])
    remain_cells = seq_total - seq_i
    out["seq"] = st["seq"]
    out["remain_cells_in_batch"] = remain_cells
    out["remain_hours_batch"] = round(remain_cells * elapsed / n_run / 60.0, 2) if n_run else None
    # 全局剩余（按本批速率估）
    out["remain_hours_global"] = round((total_tasks - len(done_pairs)) * elapsed / n_run / 60.0, 1) if n_run else None
except Exception as e:
    out["rate_err"] = str(e)

# 8) 最近 5 个完成 cell 的 mtime（判断是否还在推进）
recent = sorted(cells, key=lambda c: c.get("_mtime") or datetime.datetime.min)[-5:]
out["recent"] = [(c["_path"][:48], c["_mtime"].strftime("%H:%M:%S"), c.get("status")) for c in recent]

print(json.dumps(out, ensure_ascii=False, indent=1))
