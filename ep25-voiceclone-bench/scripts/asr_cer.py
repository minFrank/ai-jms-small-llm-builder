#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ep25 字准率回验：对 slot_0015 的 88 个 wav 跑 ASR，3 次取多数，算 CER。
用 VoiceStudio 的解释器跑（faster-whisper 1.2.1 在里面）。
"""
import os, sys, json, time, unicodedata, re

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE   = r"D:/study/ai-jms/voice_samples/ep25_run"
SLOT   = os.path.join(BASE, "slot_0015")
OUTP   = os.path.join(SLOT, "asr_cer.json")
MODEL  = "small"        # ep12 验证过的口径：zh 上 small 是可用线，turbo 会掉分
LANG   = "zh"
N_VOTE = 3              # 同一音频转 3 次取多数（压 ASR 随机）

def _norm_zh(s):
    """NFKC -> 滤 Unicode P 类 -> 小写 -> 去空白（沿用 ep12 口径）"""
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "P")
    return re.sub(r"\s+", "", s.lower())

def _edit_matrix(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def cer(ground, hyp):
    g, h = _norm_zh(ground), _norm_zh(hyp)
    if not g:
        return 0.0 if not h else 100.0
    return round(_edit_matrix(h, g) * 100.0 / len(g), 2)

def main():
    from faster_whisper import WhisperModel
    import soundfile as sf

    print("[asr] 加载 %s 模型（CPU/int8）…" % MODEL)
    t0 = time.perf_counter()
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    print("[asr] 加载 %.1fs" % (time.perf_counter() - t0))

    rows = [json.loads(l) for l in open(os.path.join(SLOT, "timing.jsonl"), encoding="utf-8") if l.strip()]
    cells = [r for r in rows if r.get("kind") == "cell" and r.get("ok") and r.get("path")]
    print("[asr] 待回验 %d 格（成功且有音频的）" % len(cells))

    results = []
    done = 0
    t_all = time.perf_counter()
    for c in cells:
        p = c["path"]
        if not os.path.exists(p):
            c.update({"asr_ok": False, "asr_note": "音频文件不在"})
            results.append(c); continue
        hyps, t_asr = [], []
        for _ in range(N_VOTE):
            ta = time.perf_counter()
            try:
                segs, _i = model.transcribe(p, language=LANG, beam_size=5,
                                            vad_filter=False,
                                            condition_on_previous_text=False)
                hyps.append("".join(s.text for s in segs).strip())
            except Exception as e:
                hyps.append("")
            t_asr.append(round(time.perf_counter() - ta, 3))
        # 3 次取多数；无全票取 CER 最低
        from collections import Counter
        cnt = Counter([h for h in hyps if h])
        best_txt, votes = (cnt.most_common(1)[0] if cnt else ("", 0))
        cers = [cer(c["text"], h) for h in hyps]
        if votes >= 2:
            idx = hyps.index(best_txt); cer_final = cers[idx]
        else:
            idx = cers.index(min(cers)); cer_final = cers[idx]; best_txt = hyps[idx]
        c.update({
            "asr_ok": True, "asr_model": MODEL, "asr_lang": LANG,
            "asr_hyps": hyps, "asr_votes": votes, "asr_text": best_txt,
            "cer_pct": cer_final, "cer_all": cers,
            "asr_time_s": t_asr, "ref_text": c.get("text"),
        })
        results.append(c)
        done += 1
        if done % 10 == 0 or done == len(cells):
            print("   [%3d/%d] %-22s %-6s CER=%6.2f%%  votes=%d" %
                  (done, len(cells), c["engine"], c["qid"], cer_final, votes))

    out = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "model": MODEL, "lang": LANG,
           "n_vote": N_VOTE, "total": len(cells), "results": results}
    tmp = OUTP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, OUTP)
    print("\n[asr] 全部 %.1f 分钟  落盘 %s" % ((time.perf_counter()-t_all)/60, OUTP))

if __name__ == "__main__":
    main()
