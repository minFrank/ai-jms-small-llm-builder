# -*- coding: utf-8 -*-
"""热态批量吞吐：用现有样本循环到 N 页，丢弃第 1 页后计时。"""
import argparse
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(BASE, "output", "batch"))
    a = ap.parse_args()

    import sys
    sys.path.insert(0, BASE)
    import engine_base
    from PIL import Image

    imgs = sorted(
        os.path.join(BASE, "output", "samples", f)
        for f in os.listdir(os.path.join(BASE, "output", "samples"))
        if f.endswith(".png"))
    if not imgs:
        raise SystemExit("no samples")
    os.makedirs(a.out, exist_ok=True)

    t_load0 = time.perf_counter()
    eng = engine_base.make_engine(a.engine)
    eng.load()
    t_load = time.perf_counter() - t_load0

    seq = [imgs[i % len(imgs)] for i in range(a.pages)]
    # 预热 1 页（不计时）
    eng.infer(seq[0])
    t0 = time.perf_counter()
    ok, fail = 0, 0
    for i, p in enumerate(seq):
        r = eng.infer(p)
        if r.err:
            fail += 1
        else:
            ok += 1
    wall = time.perf_counter() - t0
    try:
        peak = eng.model_bytes()
    except Exception:
        peak = 0
    rec = {"engine": a.engine, "pages": a.pages, "ok": ok, "fail": fail,
           "load_s": round(t_load, 3), "wall_s": round(wall, 3),
           "s_per_page": round(wall / a.pages, 3),
           "pages_per_min": round(a.pages / wall * 60.0, 2),
           "model_bytes": peak,
           "order": [os.path.basename(p) for p in seq[:5]]}
    outp = os.path.join(a.out, "%s_%d.json" % (a.engine, a.pages))
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
