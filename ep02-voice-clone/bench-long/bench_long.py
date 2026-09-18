"""长文本实测:15 分钟 / 30 分钟音频

走的就是一键包里的 tools/tts.py —— 读者走哪条路,我这里就走哪条路。
采样:耗时 / 音频时长 / 内存峰值(所有 python 进程之和,扣基线)
输出:bench-long/result.json + result.txt(文章数字的唯一依据)
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

KIT = Path(r"D:\study\ai-jms\ai-jms-small-llm-builder\ep02-voice-clone")
CV = Path(r"C:\Users\Frank\AppData\Roaming\OmniVoice\engines\cosyvoice\CosyVoice")
PY = CV / ".venv" / "Scripts" / "python.exe"
TTS = KIT / "tools" / "tts.py"
BENCH = KIT / "bench-long"
OUT = KIT / "output"
OUT.mkdir(exist_ok=True)


def mem_total_mb():
    """所有 python 进程内存之和(MB)。教训:别只抓单个进程,会拿到包装进程。"""
    try:
        import psutil
    except ImportError:
        # 回退:用 tasklist
        try:
            o = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
                               capture_output=True, text=True, timeout=20).stdout
            tot = 0
            for line in o.splitlines():
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) >= 5:
                    v = parts[4].replace(",", "").replace(" K", "").strip()
                    if v.isdigit():
                        tot += int(v)
            return tot / 1024
        except Exception:
            return 0.0
    tot = 0
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            if p.info["name"] and p.info["name"].lower().startswith("python"):
                tot += p.info["memory_info"].rss
        except Exception:
            pass
    return tot / 1024 / 1024


def audio_duration(path):
    try:
        o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                           capture_output=True, text=True, timeout=60).stdout.strip()
        return float(o)
    except Exception:
        return 0.0


def run_one(tag, text_file, out_name, voice_text, wav):
    print(f"\n{'='*64}\n[{tag}] 开始\n{'='*64}", flush=True)
    base = mem_total_mb()
    peak = [base]
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            peak[0] = max(peak[0], mem_total_mb())
            stop.wait(2.0)

    th = threading.Thread(target=sample, daemon=True)
    th.start()
    t0 = time.time()
    proc = subprocess.run(
        [str(PY), str(TTS), "--text-file", str(text_file), "--out", str(OUT / out_name),
         "--voice", str(wav), "--voice-text-file", str(voice_text)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(KIT))
    elapsed = time.time() - t0
    stop.set()
    th.join(timeout=5)

    out_path = OUT / out_name
    dur = audio_duration(out_path) if out_path.exists() else 0.0
    res = {
        "tag": tag,
        "exit_code": proc.returncode,
        "chars": len(text_file.read_text(encoding="utf-8")),
        "elapsed_s": round(elapsed, 1),
        "audio_s": round(dur, 1),
        "rtf": round(dur / elapsed, 2) if elapsed else 0,
        "mem_base_mb": round(base, 1),
        "mem_peak_mb": round(peak[0], 1),
        "mem_net_mb": round(peak[0] - base, 1),
        "out": str(out_path),
        "stderr_tail": (proc.stderr or "")[-600:],
        "stdout_tail": (proc.stdout or "")[-600:],
    }
    print(f"[{tag}] 退出码 {res['exit_code']} | 耗时 {res['elapsed_s']}s | "
          f"音频 {res['audio_s']}s ({res['audio_s']/60:.1f} 分钟) | "
          f"{res['rtf']} 倍实时 | 内存净 {res['mem_net_mb']}MB", flush=True)
    return res


def main():
    wav = KIT / "我的录音.wav"
    if not wav.exists():
        wav = KIT / "my-recording.wav"
    vt = KIT / "我的录音说的是什么.txt"
    if not vt.exists():
        vt = KIT / "what-i-said.txt"

    targets = sys.argv[1:] or ["15", "30"]
    results = []
    if (BENCH / "result.json").exists():
        try:
            results = json.loads((BENCH / "result.json").read_text(encoding="utf-8"))
            results = [r for r in results if r["tag"] not in targets]
        except Exception:
            results = []

    for t in targets:
        f = BENCH / f"story-{t}min.txt"
        if not f.exists():
            print(f"跳过 {t}:素材不存在")
            continue
        results.append(run_one(f"{t}min", f, f"bench-{t}min.wav", vt, wav))
        (BENCH / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["长文本实测原始数据(一键包 tools/tts.py,与读者同一条路)", "=" * 60,
             f"采样时间:{time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"机器:AMD Ryzen 7 5700G / 27.9GB / 无独立显卡 / Windows 11", ""]
    for r in results:
        lines += [
            f"--- {r['tag']} ---",
            f"素材字符数:{r['chars']}",
            f"退出码:{r['exit_code']}",
            f"耗时:{r['elapsed_s']} 秒({r['elapsed_s']/60:.2f} 分钟)",
            f"音频时长:{r['audio_s']} 秒({r['audio_s']/60:.2f} 分钟)",
            f"生成倍率:{r['rtf']} 倍实时(音频时长 ÷ 耗时)",
            f"内存:基线 {r['mem_base_mb']}MB → 峰值 {r['mem_peak_mb']}MB,净增 {r['mem_net_mb']}MB",
            "",
        ]
    lines += ["说明:内存为所有 python 进程之和减基线,每 2 秒采样一次。",
              "说明:长文本按句自动切段,段数随字数增加。"]
    (BENCH / "result.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n✅ 已写入 bench-long/result.json 与 result.txt")


if __name__ == "__main__":
    main()
