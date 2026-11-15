#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
失败格复现核验：把 slot_0015 里 omnivoice-subprocess 的 11 个失败格重跑一遍，
确认是「可复现的引擎故障」还是「一次性抖动」。
判据：重跑仍失败 = 真故障；重跑成功 = 抖动，原数据不能当失败案例写。
"""
import os, sys, json, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
REF_WAV = r"D:/study/ai-jms/voice_samples/ref_new_16k.wav"
REF_TXT = open(r"D:/study/ai-jms/voice_samples/frank-ref-text-new.txt", encoding="utf-8").read().strip()
URL     = "http://127.0.0.1:3900/generate"
BANK    = json.load(open(r"D:/study/ai-jms/voice_samples/ep25_run/question_bank.json", encoding="utf-8"))
TEXTS   = {q.get("id") or ("q%02d" % i): q["text"] for i, q in enumerate(BANK)}
OUT_DIR = r"D:/study/ai-jms/voice_samples/ep25_run/recheck_subprocess"
os.makedirs(OUT_DIR, exist_ok=True)

FAILED = ["q01","q10","q11","q12","q13","q14","q15","q16","q18","q19","q20"]
# 对照：同轮成功的 3 条，确认服务本身还活着
CONTROL = ["q00","q17","q22"]

def run(engine, qid, timeout=700):
    text = TEXTS.get(qid)
    outp = os.path.join(OUT_DIR, "%s_%s.wav" % (engine, qid))
    if os.path.exists(outp): os.remove(outp)
    t0 = time.perf_counter()
    try:
        with open(REF_WAV, "rb") as f:
            r = requests.post(URL, timeout=timeout,
                files={"ref_audio": (os.path.basename(REF_WAV), f, "audio/wav")},
                data={"engine": engine, "text": text, "ref_text": REF_TXT,
                      "language": "zh", "seed": 1234, "stream": "false"})
        wall = time.perf_counter() - t0
        if r.status_code != 200:
            detail = ""
            try: detail = r.json().get("detail", "")
            except Exception: detail = r.content[:200].decode("utf-8","replace")
            return {"ok": False, "wall": round(wall,1), "err": "HTTP %d: %s" % (r.status_code, str(detail)[:150])}
        with open(outp, "wb") as fh: fh.write(r.content)
        import soundfile as sf
        d, sr = sf.read(outp, dtype="float32")
        dur = len(d)/float(sr); rms = float((d**2).mean())**0.5
        if dur <= 0.05 or rms < 1e-4:
            return {"ok": False, "wall": round(wall,1), "err": "产物异常 dur=%.2f rms=%.4f" % (dur, rms)}
        return {"ok": True, "wall": round(wall,1), "dur": round(dur,2), "rms": round(rms,4), "rtf": round(wall/dur,2)}
    except Exception as e:
        return {"ok": False, "wall": round(time.perf_counter()-t0,1), "err": "异常: %r" % e}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "engine": "omnivoice-subprocess",
       "recheck_failed": FAILED, "control": CONTROL, "results": {}}
print("=== 对照组（上轮成功的 3 条，先确认服务正常）===")
for q in CONTROL:
    r = run("omnivoice-subprocess", q)
    res["results"][q] = {"role": "control", **r}
    print("  %-5s %-6s %6.1fs  %s" % (q, "OK" if r["ok"] else "FAIL", r["wall"], "成功" if r["ok"] else r["err"][:70]))

print("\n=== 失败组（上轮失败的 11 条）===")
for q in FAILED:
    r = run("omnivoice-subprocess", q)
    res["results"][q] = {"role": "failed_orig", **r}
    print("  %-5s %-6s %6.1fs  %s" % (q, "OK" if r["ok"] else "FAIL", r["wall"], "成功" if r["ok"] else r["err"][:70]))

n_ok_ctrl = sum(1 for q in CONTROL if res["results"][q]["ok"])
n_ok_fail = sum(1 for q in FAILED    if res["results"][q]["ok"])
res["control_ok"] = "%d/3" % n_ok_ctrl
res["origfailed_now_ok"] = "%d/11" % n_ok_fail
print("\n" + "="*64)
print("对照组: %d/3 成功" % n_ok_ctrl)
print("原失败组: 重跑后 %d/11 成功" % n_ok_fail)
if n_ok_ctrl == 3 and n_ok_fail == 0:
    print("判定: **可复现的引擎故障**（服务正常、原失败条全部复现）→ 可作为失败案例写入")
elif n_ok_ctrl == 3 and n_ok_fail == 11:
    print("判定: **全部成功 = 原失败是抖动**，不能当失败案例写入，需重跑这 11 格")
elif n_ok_ctrl == 3:
    print("判定: **部分复现** — 需逐条说明，不能一概说『引擎故障』")
else:
    print("判定: **对照组也失败 = 服务本身有问题**，本轮数据整体可疑")

outp = os.path.join(OUT_DIR, "recheck.json")
with open(outp + ".tmp", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1); f.flush(); os.fsync(f.fileno())
os.replace(outp + ".tmp", outp)
print("落盘: %s" % outp)
