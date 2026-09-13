#!/usr/bin/env python
"""环境自检:缺什么、下没下模型,一次性说清楚(不用你懂命令行)。"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)


def main() -> int:
    ok = True
    print("=" * 46)
    print("  本地声音包 · 环境自检")
    print("=" * 46)

    # Python
    print(f"[1] Python:{sys.version.split()[0]}  → OK")

    # ffmpeg
    ff = shutil.which("ffmpeg")
    print(f"[2] ffmpeg:{'找到' if ff else '× 没找到(需要用 ffmpeg 转换音频)'}")
    ok = ok and bool(ff)

    # 内存
    try:
        import ctypes
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = MS(); st.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        gb = st.ullTotalPhys / 1024**3
        warn = "  ← 建议 16G 以上" if gb < 15 else ""
        print(f"[3] 内存:{gb:.1f} G{warn}")
        if gb < 15:
            print("    (8G 的机器跑起来会很吃力,可以先试短文本)")
    except Exception:
        print("[3] 内存:读取失败(不影响使用)")

    # ffprobe
    fp = shutil.which("ffprobe")
    print(f"[4] ffprobe:{'找到' if fp else '× 没找到'}")

    # CosyVoice
    sys.path.insert(0, HERE)
    from tts import find_cosy_root
    root = find_cosy_root()
    if root:
        w = os.path.join(root, "pretrained_models", "Fun-CosyVoice3-0.5B")
        has_w = os.path.isdir(w)
        print(f"[5] CosyVoice:{root}")
        print(f"    模型文件:{'已就绪' if has_w else '× 缺失(需运行一键安装)'}")
        ok = ok and has_w
    else:
        print("[5] CosyVoice:× 未安装 → 请先双击「一键安装.bat」")
        ok = False

    # 输入文件
    v = os.path.join(KIT, "我的录音.wav")
    t = os.path.join(KIT, "story.txt")
    print(f"[6] 你的录音:{'找到' if os.path.exists(v) else '× 还没有,把录音放进来并改名「我的录音.wav」'}")
    print(f"[7] 要念的文字:{'找到' if os.path.exists(t) else '× 还没有 story.txt'}")

    print("=" * 46)
    print("  结论:" + ("一切就绪,可以双击「一键生成.bat」了" if ok else "还缺东西,见上面的 ×"))
    print("=" * 46)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
