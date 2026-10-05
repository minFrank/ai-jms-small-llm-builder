# ep04 · 真实任务：用本工具生成本期封面 + 补「图里写中文字」的失败证据
# 封面 = 文章自己承诺的「真实任务」；中文测试 = 第三节失败案例①的实测证据
import subprocess, os, sys, datetime, shutil, time

M = "D:/models/txt2img"
MODEL = os.path.join(M, "v1-5-pruned-emaonly.safetensors")
EXE = os.path.join(M, "vulkan", "sd-cli.exe")
OUT = os.path.join(M, "out")
LOG = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img/logs"
os.makedirs(OUT, exist_ok=True)

def run(tag, prompt, w, h, steps, seed, extra=()):
    png = os.path.join(OUT, tag + ".png")
    cmd = [EXE, "-m", MODEL, "-p", prompt, "-W", str(w), "-H", str(h),
           "--steps", str(steps), "-s", str(seed), "--backend", "diffusion=vulkan0",
           "-o", png] + list(extra)
    t0 = time.time()
    with open(os.path.join(LOG, f"raw-{tag}.txt"), "w", encoding="utf-8") as f:
        f.write(f"# {datetime.datetime.now().isoformat()} # cmd: {' '.join(cmd)}\n\n")
        f.flush()
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=M)
    dur = time.time() - t0
    ok = os.path.exists(png)
    print(f"[{tag}] rc={p.returncode} {dur:.1f}s png={'OK ' + str(os.path.getsize(png)) if ok else 'MISSING'}", flush=True)
    return ok

# 1) 封面：2.33:1（公众号封面比例 2.35:1 近似），核显 20 步
cover_prompt = ("minimalist flat illustration of a personal computer on a wooden desk "
                "painting a picture on an easel, soft daylight from a window, "
                "clean composition, muted blue and beige palette, lots of empty space, "
                "digital art")
run("cover_raw", cover_prompt, 896, 384, 20, 42)

# 2) 中文文字失败证据：让它在图里写汉字
cn_prompt = ("a clean white sign board in a forest clearing, "
             "with the chinese characters written clearly on it: 你好世界, "
             "morning light, digital painting")
run("cn_text", cn_prompt, 512, 512, 20, 42)

# 3) 封面缩放到公众号尺寸 900x383 并转 jpg
try:
    from PIL import Image
    src = os.path.join(OUT, "cover_raw.png")
    if os.path.exists(src):
        dst = r"C:/Users/Frank/AppData/Local/hermes/workspace/assets/localai-ep04-cover.jpg"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(src).convert("RGB").resize((900, 383), Image.LANCZOS)
        im.save(dst, quality=90)
        print("封面 →", dst, os.path.getsize(dst), "B", flush=True)
except Exception as e:
    print("封面处理失败:", e, flush=True)
