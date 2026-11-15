#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ep25 四时段跑测驱动 v4
用法:  run_slot.py <slot_name>   e.g.  run_slot.py slot_1400
产出:  ep25_run/<slot_name>/audio/*.wav  timing.jsonl  load.json  round.md
设计依据: articles/bench/ep25-四时段跑测设计-v4.md
"""
import os, sys, json, time, gc, io, math, signal, random, hashlib, platform, subprocess

# ---- 输出到 stdout 用 utf-8（Windows 控制台默认 gbk 会炸）----
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ================= 硬路径 =================
RUN_DIR   = r"D:/study/ai-jms/voice_samples/ep25_run"
# 2026-10-29 第二次调整：用户取消四时段分散跑，改为**固定 00:15 单次通宵跑**。
# 单次通宵有约 8.5 小时空档，题量从 10 放回 25（×1 次 = 100 格）。
# R1 实测 omnivoice 单格 289–333s（RTF 38–44），且 rep1/rep2/rep3 之间几乎无差别 ——
# **没有"冷启慢/暖调用快"之分**，每格都这个量级。3 次重复测不出稳定性，故 N_REPS=1。
BANK      = os.path.join(RUN_DIR, "question_bank.json")
REF_WAV   = r"D:/study/ai-jms/voice_samples/ref_new_16k.wav"
REF_TXT   = r"D:/study/ai-jms/voice_samples/frank-ref-text-new.txt"
VS_PY     = r"D:/study/ai-jms/VoiceStudio/.venv/Scripts/python.exe"
VS_PORT   = 3900
GPT_PORT  = 9880
# 2026-10-29：R1 实测 omnivoice 单格 289–333s（RTF 38–44），且 rep1/rep2/rep3
# 之间几乎无差别 —— **没有"冷启慢/暖调用快"之分**，每格都这个量级。
# 3 次重复测不出稳定性，故 N_REPS=1。25 题 × 1 次 × 4 引擎 = 100 格，
# 预计 8–12 小时（长句组更慢），通宵窗口可容。
N_REPS    = 1          # 每条题合成 1 次
ASR_N     = 3          # 每段音频转写 3 次取多数
ASR_MODEL = "small"
ASR_LANG  = "zh"

# ---- rmtree 白名单：只允许删 RUN_DIR 下 ----
def _safe_rmtree(p):
    p = os.path.abspath(p).replace("\\", "/")
    root = os.path.abspath(RUN_DIR).replace("\\", "/")
    assert p.startswith(root) and p != root, "rmtree 白名单拦截: %s" % p
    import shutil; shutil.rmtree(p, ignore_errors=True)

def atomic_write_json(path, obj):
    """tmp -> flush -> fsync -> os.replace"""
    d = os.path.dirname(path); os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

# ================= 环境快照（关空载门后必须的三件事之一）=================
def system_snapshot(sample_seconds=30):
    """CPU 均值/峰值、可用内存、电源计划、后台进程清单"""
    try:
        import psutil
    except Exception:
        return {"error": "psutil 不可用"}
    snap = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "platform": platform.platform()}

    # CPU 采样
    cpu = []
    for _ in range(sample_seconds):
        cpu.append(psutil.cpu_percent(interval=1.0))
    snap["cpu_avg_pct"] = round(sum(cpu) / max(1, len(cpu)), 1)
    snap["cpu_peak_pct"] = round(max(cpu), 1)

    vm = psutil.virtual_memory()
    snap["mem_total_gb"] = round(vm.total / 2**30, 1)
    snap["mem_available_gb"] = round(vm.available / 2**30, 1)

    # 后台进程（CPU>1%）
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            if info.get("cpu_percent", 0) and info["cpu_percent"] > 1.0:
                procs.append({
                    "pid": info["pid"], "name": info["name"],
                    "cpu_pct": info["cpu_percent"],
                    "rss_mb": round((info["memory_info"].rss or 0) / 2**20, 1),
                })
        except Exception:
            pass
    procs.sort(key=lambda x: -x["cpu_pct"])
    snap["busy_procs"] = procs[:15]

    # 电源计划
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=15)
        snap["power_plan"] = (r.stdout or "").strip()
    except Exception as e:
        snap["power_plan"] = "取不到: %s" % e

    return snap

# ================= 引擎可用性（问服务，不自己猜）=================
def query_engines():
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:%d/engines" % VS_PORT, timeout=240) as r:
        return json.loads(r.read().decode("utf-8"))

def engine_lineup():
    """返回 [(engine_id, display_name, supports_cloning, isolation_mode, reason)]"""
    d = query_engines()
    out = []
    for b in d["tts"]["backends"]:
        if not b.get("available"):
            continue
        if not b.get("supports_cloning"):
            continue
        out.append((b["id"], b.get("display_name"), True,
                    b.get("isolation_mode"), b.get("reason")))
    return out

# ================= 产物校验（不只看 mtime）=================
def validate_product(path):
    """必须能解码 + 非静音 + 时长>0"""
    if not os.path.exists(path):
        return False, "文件不存在"
    if os.path.getsize(path) < 1024:
        return False, "字节过少 (%d)" % os.path.getsize(path)
    try:
        import soundfile as sf
        data, sr = sf.read(path, dtype="float32")
    except Exception as e:
        return False, "解码失败: %s" % e
    if data is None or len(data) == 0:
        return False, "空数据"
    dur = len(data) / float(sr)
    if dur <= 0.05:
        return False, "时长过短 (%.3fs)" % dur
    # 非静音: RMS
    rms = float((data ** 2).mean()) ** 0.5
    if rms < 1e-4:
        return False, "静音 (RMS=%.2e)" % rms
    return True, "OK sr=%d dur=%.2fs rms=%.4f" % (sr, dur, rms)

# ================= ASR 回验（每次转写用新对象；3 次取多数）=================
_asr_model_cache = {}
def _get_asr():
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        raise RuntimeError("faster-whisper 不可用: %s" % e)
    if ASR_MODEL not in _asr_model_cache:
        _asr_model_cache[ASR_MODEL] = WhisperModel(ASR_MODEL, device="cpu", compute_type="int8")
    return _asr_model_cache[ASR_MODEL]

def asr_transcribe_once(audio_path):
    """单次转写，返回 (文本, 耗时)。每次都新建转写会话避免状态污染。"""
    import whisper_tokenizer  # noqa  仅为尽早暴露缺失
    model = _get_asr()
    t0 = time.perf_counter()
    segs, _info = model.transcribe(audio_path, language=ASR_LANG,
                                   beam_size=5, vad_filter=False,
                                   condition_on_previous_text=False)
    txt = "".join(s.text for s in segs).strip()
    return txt, (time.perf_counter() - t0)

def _norm_zh(s):
    """NFKC -> 滤 Unicode P 类 -> 小写 -> 去空白（沿用 ep12 口径）"""
    import unicodedata, re
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "P")
    return re.sub(r"\s+", "", s.lower())

def _edit_ratio(a, b):
    """Levenshtein 距离 / len(b)"""
    if not b: return 1.0 if a else 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / float(len(b))

def cer(ground, hyp):
    g, h = _norm_zh(ground), _norm_zh(hyp)
    if not g: return 0.0 if not h else 1.0
    return round(_edit_ratio(h, g) * 100.0, 2)  # %

def cer_vote3(ground, hyps):
    """3 次转写取多数（逐字全票；无全票时取 CER 最低的）"""
    from collections import Counter
    if not hyps: return None, [], []
    c = Counter(hyps)
    top, n = c.most_common(1)[0]
    if n >= 2:
        return cer(ground, top), [cer(ground, h) for h in hyps], top
    cers = [cer(ground, h) for h in hyps]
    i = cers.index(min(cers))
    return cers[i], cers, hyps[i]

# ================= 独立子进程采样 CPU/RSS =================
def start_sampler(pid_target, out_path, interval_ms=200):
    """起独立 python 子进程采样目标 pid 的 CPU% 与 RSS（线程版在推理期会被饿死）"""
    code = r"""
import json, time, sys
try:
    import psutil
    pid = int(sys.argv[1]); out = sys.argv[2]; iv = float(sys.argv[3])
    p = psutil.Process(pid)
    rows = []
    while True:
        try:
            c = p.cpu_percent(interval=None)
            m = p.memory_info().rss
            rows.append((time.time(), round(c, 1), round(m / 2**20, 1)))
        except Exception:
            break
        time.sleep(iv)
except Exception:
    pass
"""
    import tempfile
    script = os.path.join(tempfile.gettempdir(), "_ep25_sampler_%d.py" % os.getpid())
    with open(script, "w", encoding="utf-8") as f:
        f.write(code)
    return subprocess.Popen([sys.executable, script, str(pid_target), out_path, str(interval_ms / 1000.0)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ================= 单次合成（走 VoiceStudio 服务）=================
def synth_via_service(engine_id, text, out_path, timeout=900):
    """调服务合成。返回 (ok, wall_seconds, raw_response_summary)

    端点是 POST /generate，multipart 表单：text/language/ref_text/engine 走
    form 字段，ref_audio 走文件上传。此前写的是 JSON body 打 /tts —— 该路径
    在 openapi.json 里不存在，整轮 300 格全部秒失败 404（2026-10-29 R1 轮实测）。
    """
    import requests  # VoiceStudio venv 自带
    t0 = time.perf_counter()
    try:
        with open(REF_WAV, "rb") as f:
            r = requests.post(
                "http://127.0.0.1:%d/generate" % VS_PORT,
                files={"ref_audio": (os.path.basename(REF_WAV), f, "audio/wav")},
                data={"engine": engine_id, "text": text,
                      "ref_text": _read_ref_text(), "language": "zh",
                      "seed": 1234, "stream": "false"},
                timeout=timeout)
        if r.status_code != 200:
            return False, (time.perf_counter() - t0), \
                "HTTP %d: %s" % (r.status_code, r.content[:300].decode("utf-8", "replace"))
        raw = r.content
        # 若返回音频字节，落盘；若返回 json，取 audio 路径字段
        if raw[:4] == b"RIFF":
            with open(out_path, "wb") as f:
                f.write(raw)
        else:
            try:
                d = json.loads(raw.decode("utf-8"))
                p = d.get("audio_path") or d.get("path")
                if p and os.path.exists(p):
                    import shutil; shutil.copyfile(p, out_path)
                else:
                    return False, (time.perf_counter() - t0), "服务返回非音频且无 audio_path: %s" % str(d)[:200]
            except Exception as e:
                return False, (time.perf_counter() - t0), "响应解析失败: %s" % e
        return True, (time.perf_counter() - t0), "ok"
    except Exception as e:
        return False, (time.perf_counter() - t0), "合成失败: %s" % e

_ref_txt_cache = None
def _read_ref_text():
    global _ref_txt_cache
    if _ref_txt_cache is None:
        try:
            _ref_txt_cache = open(REF_TXT, encoding="utf-8").read().strip()
        except Exception:
            _ref_txt_cache = ""
    return _ref_txt_cache

# ================= 主流程 =================
def main():
    if len(sys.argv) < 2:
        print("用法: run_slot.py <slot_name>"); sys.exit(2)
    slot = sys.argv[1]
    if not slot.startswith("slot_"):
        print("slot 名必须形如 slot_1400"); sys.exit(2)
    slot_dir = os.path.join(RUN_DIR, slot)
    audio_dir = os.path.join(slot_dir, "audio")
    # 白名单内才清
    if os.path.exists(slot_dir):
        _safe_rmtree(slot_dir)
    os.makedirs(audio_dir, exist_ok=True)

    log_path = os.path.join(slot_dir, "timing.jsonl")
    def log(obj):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            f.flush()

    print("[slot] %s  开始 %s" % (slot, time.strftime("%H:%M:%S")))

    # 1) 环境快照（30 秒采样）
    print("[snap] 采样 CPU 30 秒…")
    snap = system_snapshot(30)
    atomic_write_json(os.path.join(slot_dir, "load.json"), snap)
    log({"kind": "snapshot", **snap})
    print("[snap] cpu_avg=%.1f%% cpu_peak=%.1f%% mem_avail=%.1fGB procs=%d"
          % (snap.get("cpu_avg_pct", 0), snap.get("cpu_peak_pct", 0),
             snap.get("mem_available_gb", 0), len(snap.get("busy_procs", []))))

    # 2) 引擎阵容（问服务，含 supports_cloning）
    try:
        lineup = engine_lineup()
    except Exception as e:
        lineup = []
        log({"kind": "lineup_error", "error": str(e)})
    print("[lineup] 可克隆引擎 %d 个: %s" % (len(lineup), [x[0] for x in lineup]))
    atomic_write_json(os.path.join(slot_dir, "lineup.json"), lineup)

    # 3) 题库
    bank = json.load(open(BANK, encoding="utf-8"))
    qs = bank["questions"] if isinstance(bank, dict) and "questions" in bank else bank
    print("[bank] %d 条题" % len(qs))

    # 4) 逐引擎逐题逐次
    total = len(lineup) * len(qs) * N_REPS
    done = 0
    for eng_id, eng_name, clone, iso, reason in lineup:
        eng_dir = os.path.join(audio_dir, eng_id)
        os.makedirs(eng_dir, exist_ok=True)
        print("\n[engine] %s  isolation=%s" % (eng_id, iso))
        # 冷启动：重启计时（服务已启动后的首载）
        t_cold = time.perf_counter()
        first = True
        for qi, q in enumerate(qs):
            qid  = q.get("id") or ("q%02d" % qi)
            text = q.get("text") or q.get("question")
            for rep in range(N_REPS):
                done += 1
                outp = os.path.join(eng_dir, "%s_rep%d.wav" % (qid, rep + 1))
                # 产物先删（白名单内）
                if os.path.exists(outp):
                    os.remove(outp)
                # 采样器
                samp = os.path.join(eng_dir, "_samp_%s_r%d.json" % (qid, rep + 1))
                sampler = start_sampler(os.getpid(), samp, 200)
                t0 = time.perf_counter()
                ok, wall, note = synth_via_service(eng_id, text, outp)
                cold = (time.perf_counter() - t_cold) if first else None
                first = False
                sampler.terminate()
                # 产物校验
                valid, vnote = validate_product(outp) if ok else (False, note)
                dur = 0.0; sr = 0
                if valid:
                    try:
                        import soundfile as sf
                        d_, sr_ = sf.read(out_path if False else outp, dtype="float32")
                        dur = len(d_) / float(sr_); sr = sr_
                    except Exception:
                        pass
                rtf = round(wall / dur, 3) if dur > 0 else None
                rec = {
                    "kind": "cell", "engine": eng_id, "qid": qid, "rep": rep + 1,
                    "group": q.get("group") or "",
                    "text_chars": len(text or ""), "text": text,
                    "wall_s": round(wall, 3), "audio_s": round(dur, 3), "sr": sr,
                    "rtf": rtf, "cold_load_s": round(cold, 3) if cold else None,
                    "ok": ok and valid, "note": note if not ok else vnote,
                    "path": outp if (ok and valid) else None,
                    "ts": time.strftime("%H:%M:%S"),
                }
                log(rec)
                print("   [%3d/%d] %-14s %-6s %-9s  %.2fs  RTF=%s  %s"
                      % (done, total, qid, "rep%d" % (rep + 1), "%.1fs" % dur,
                         wall, ("%.2f" % rtf) if rtf else "NA", "OK" if rec["ok"] else "FAIL"))
                # 断点续跑：每 10 格落盘一次 lineup 进度
                if done % 10 == 0:
                    atomic_write_json(os.path.join(slot_dir, "progress.json"),
                                      {"done": done, "total": total, "engines": [x[0] for x in lineup]})

    # 5) 收尾
    atomic_write_json(os.path.join(slot_dir, "progress.json"),
                      {"done": done, "total": total, "finished": True,
                       "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("\n[slot] %s 完成 %d/%d 格  %s" % (slot, done, total, time.strftime("%H:%M:%S")))

if __name__ == "__main__":
    main()
