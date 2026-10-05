# ep04 · 真跑 .bat 本身（skill 要求：手动调内部命令不算，必须执行 bat 自身）
# 用 python subprocess 以 Windows Unicode 方式执行中文名 bat，规避 MSYS 编码问题
import subprocess, sys, os, datetime, time

KIT = r"D:\models\txt2img\kit"
LOG = r"D:\study\ai-jms\ai-jms-small-llm-builder\ep04-txt2img\logs\bat-test.txt"
DEVNULL = subprocess.DEVNULL

def run(bat, timeout):
    path = os.path.join(KIT, bat)
    t0 = time.time()
    p = subprocess.run(
        ["cmd", "/c", path],
        cwd=KIT,
        stdin=DEVNULL,             # 让 bat 里的 pause 立即返回，等价双击后按一下回车
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    dur = time.time() - t0
    raw = p.stdout or b""
    for enc in ("gbk", "utf-8", "mbcs"):
        try:
            txt = raw.decode(enc)
            break
        except Exception:
            txt = raw.decode("utf-8", errors="replace")
    return p.returncode, dur, txt

lines = [f"# bat 真实执行记录 {datetime.datetime.now().isoformat()}", ""]
ok = True

for bat, to in [("双击下载模型.bat", 300), ("双击生成.bat", 600)]:
    print(f"--- RUN {bat} ---", flush=True)
    try:
        rc, dur, txt = run(bat, to)
    except subprocess.TimeoutExpired:
        lines += [f"## {bat}: TIMEOUT ({to}s)", ""]
        print(f"{bat}: TIMEOUT", flush=True)
        ok = False
        continue
    lines += [f"## {bat}: rc={rc} 耗时={dur:.1f}s", txt, ""]
    print(f"{bat}: rc={rc} {dur:.1f}s", flush=True)
    if rc != 0:
        ok = False

# 产物核验
res = os.path.join(KIT, "result.png")
lines.append(f"result.png: {'存在 ' + str(os.path.getsize(res)) + ' B' if os.path.exists(res) else '缺失'}")
print(lines[-1], flush=True)

os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG, "w", encoding="utf-8").write("\n".join(lines))
print("LOG →", LOG, flush=True)
sys.exit(0 if ok else 1)
