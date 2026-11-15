#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R1 轮修复后的单格冒烟：验证 /generate + multipart 真能出音频。
只调 run_slot.py 里那个改过的 synth_via_service，不另写跑测逻辑。"""
import os, sys, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, r"D:/study/ai-jms/voice_samples/ep25_run")
import run_slot as rs

OUT = r"D:/study/ai-jms/voice_samples/ep25_run/smoke_check.wav"
if os.path.exists(OUT):
    os.remove(OUT)

t0 = time.time()
ok, wall, note = rs.synth_via_service("omnivoice", "今天天气很好。", OUT)
print("ok=%s wall=%.2fs note=%s" % (ok, wall, str(note)[:300]))
if ok:
    valid, vnote = rs.validate_product(OUT)
    print("validate=%s -> %s" % (valid, vnote))
    print("bytes=%d" % os.path.getsize(OUT))
print("total=%.1fs" % (time.time() - t0))
