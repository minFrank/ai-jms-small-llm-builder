# -*- coding: utf-8 -*-
import json, os, glob, statistics, collections, datetime, io, sys

BASE = r"D:/study/ai-jms/ep13-docparse"
CELLDIR = os.path.join(BASE, "cells", "ep13-full-001")

def load(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return json.load(f)

state = load(os.path.join(BASE, "control", "batch_state.json"))

# manifest sha256 -> img
manifest = load(os.path.join(BASE, "samples", "manifest.json"))
sha2img = {}
def walk_manifest(m):
    # accept various shapes
    if isinstance(m, dict):
        # maybe {sha: {...}} or {"samples":[...]}
        for k, v in m.items():
            if isinstance(v, dict):
                s = v.get("sha256") or v.get("sha") or (k if len(str(k)) == 64 else None)
                img = v.get("img") or v.get("image") or v.get("path") or v.get("file") or v.get("name")
                if s and img:
                    sha2img[s] = img
                elif len(str(k)) == 64 and isinstance(v, str):
                    sha2img[k] = v
            elif isinstance(v, str) and len(k) == 64:
                sha2img[k] = v
        if "samples" in m and isinstance(m["samples"], list):
            for v in m["samples"]:
                if isinstance(v, dict):
                    s = v.get("sha256") or v.get("sha")
                    img = v.get("img") or v.get("image") or v.get("path") or v.get("file") or v.get("name")
                    if s and img:
                        sha2img[s] = img
    elif isinstance(m, list):
        for v in m:
            if isinstance(v, dict):
                s = v.get("sha256") or v.get("sha")
                img = v.get("img") or v.get("image") or v.get("path") or v.get("file") or v.get("name")
                if s and img:
                    sha2img[s] = img

walk_manifest(manifest)

files = sorted(glob.glob(os.path.join(CELLDIR, "*.json")))
rows = []
for p in files:
    try:
        c = load(p)
    except Exception as e:
        rows.append({"file": os.path.basename(p), "error": str(e)})
        continue
    inp = c.get("input") or {}
    sha = inp.get("sha256") if isinstance(inp, dict) else None
    rows.append({
        "file": os.path.basename(p),
        "status": c.get("status"),
        "engine": c.get("engine"),
        "cer_median": c.get("cer_median"),
        "wall_median": c.get("wall_median"),
        "sha256": sha,
        "sample": sha2img.get(sha) or (inp.get("img") if isinstance(inp, dict) else None) or (inp.get("name") if isinstance(inp, dict) else None),
        "keys": sorted(c.keys()),
        "mtime": os.path.getmtime(p),
    })

n = len(rows)
status_cnt = collections.Counter(r["status"] for r in rows)
eng_cnt = collections.Counter((r["engine"], r["status"]) for r in rows)
eng_status = collections.defaultdict(collections.Counter)
for r in rows:
    eng_status[r["engine"]][r["status"]] += 1

# sample of cell keys to understand structure
key_shapes = collections.Counter(tuple(r["keys"]) for r in rows)

# CER
cNormal = [r for r in rows if isinstance(r["cer_median"], (int, float)) and r["cer_median"] < 0.5]
cOut = [r for r in rows if isinstance(r["cer_median"], (int, float)) and r["cer_median"] >= 0.5]
cer_med = statistics.median([r["cer_median"] for r in cNormal]) if cNormal else None

walls = [r["wall_median"] for r in rows if isinstance(r["wall_median"], (int, float))]
wall_med = statistics.median(walls) if walls else None

cOut.sort(key=lambda r: -r["cer_median"])

# non-complete
nonc = [r for r in rows if r["status"] != "complete"]

# mtime progression: sorted by mtime, for rate
rows_by_mtime = sorted([r for r in rows if "mtime" in r], key=lambda r: r["mtime"])
mt = [r["mtime"] for r in rows_by_mtime]

out = {
    "now": datetime.datetime.now().isoformat(),
    "state": state,
    "n_cells": n,
    "status_cnt": dict(status_cnt),
    "eng_status": {str(k): dict(v) for k, v in eng_status.items()},
    "key_shapes": [{"n": v, "keys": list(k)} for k, v in key_shapes.most_common(3)],
    "cer_median_normal": cer_med,
    "n_normal": len(cNormal),
    "outliers": [{"engine": r["engine"], "cer": r["cer_median"], "sample": r["sample"], "sha": (r["sha256"] or "")[:12], "file": r["file"]} for r in cOut],
    "wall_median": wall_med,
    "non_complete": [{"file": r["file"], "status": r["status"], "engine": r["engine"]} for r in nonc],
    "mtime_min": datetime.datetime.fromtimestamp(mt[0]).isoformat() if mt else None,
    "mtime_max": datetime.datetime.fromtimestamp(mt[-1]).isoformat() if mt else None,
    "mtime_series": [datetime.datetime.fromtimestamp(x).strftime("%m-%d %H:%M") for x in mt],
    "manifest_entries": len(sha2img),
    "manifest_top": list(sha2img.items())[:3],
}
# per-engine cer medians
per_eng = collections.defaultdict(list)
for r in rows:
    if isinstance(r["cer_median"], (int, float)) and r["cer_median"] < 0.5:
        per_eng[r["engine"]].append(r["cer_median"])
out["per_engine_cer_median"] = {k: statistics.median(v) for k, v in per_eng.items()}
out["per_engine_wall_median"] = {}
wpe = collections.defaultdict(list)
for r in rows:
    if isinstance(r["wall_median"], (int, float)):
        wpe[r["engine"]].append(r["wall_median"])
out["per_engine_wall_median"] = {k: statistics.median(v) for k, v in wpe.items()}
out["n_sha_missing_sample"] = sum(1 for r in rows if r["sha256"] and not r["sample"])

with io.open(os.path.join(BASE, "control", "_prog_report.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
