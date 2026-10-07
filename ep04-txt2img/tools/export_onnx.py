#!/usr/bin/env python
"""ep04 阶段2: 从本地单文件导出 ONNX (B1/B2/B3/B4)。

B1  断网加载(已实测 OFFLINE_LOAD_OK,HF 缓存有 config)
B2  导出配方三件套: attention processor 切 math + 显式 opset + dynamo=False
    否则现代 diffusers 的 SDPA 会抛 UnsupportedOperatorError
B3  UNet fp32 >2GB → 强制 external data;sha256 对整组算
B4  混合精度: unet/text_encoder 可 fp16, **VAE decoder 必须 fp32**(fp16 会黑图)
P-4 不用 optimum(会漂移), 纯 torch.onnx.export

用法: python export_onnx.py --part all
"""
import argparse
import hashlib
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = r"D:/models/txt2img/v1-5-pruned-emaonly.safetensors"
OUTDIR = r"D:/ep04/onnx/sd15"
E04 = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep04-txt2img"
OPSET = 17
TIMEBOX_S = 1800   # C9: 导出时间盒 30min
os.makedirs(OUTDIR, exist_ok=True)

# B4: 子模块精度 —— VAE decoder 锁死 fp32(fp16 会黑图)
# text_encoder 实测 fp16 导出产生 dtype 混合坏图(LayerNormalization 的 scale 被 half
# 而 hidden_states 仍 fp32 → ORT 拒载),按 E7 降级到 fp32;代价仅 0.4GB,且该模块
# 每图只跑一次,对头条耗时无感。
PRECISION = {"text_encoder": "fp32", "unet": "fp16", "vae": "fp32"}


def sha256_group(path):
    """B3: external data 是一组文件,sha256 必须覆盖整组。"""
    files = []
    if os.path.isfile(path):
        files = [path]
        base = os.path.splitext(path)[0]
        for ext in (".data", ".onnx_data"):
            cand = base + ext
            if os.path.exists(cand):
                files.append(cand)
        # external data 单文件名可能是 <name>.onnx 的 data 文件
        for cand in (path + "_data", os.path.join(os.path.dirname(path), "weights.pb")):
            if os.path.exists(cand):
                files.append(cand)
    h = hashlib.sha256()
    for f in sorted(set(files)):
        h.update(os.path.basename(f).encode())
        with open(f, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
    return h.hexdigest(), sorted(set(files), key=os.path.basename)


def export_part(pipe, part, dtype):
    import torch
    sub = getattr(pipe, part)
    sub = sub.to(dtype).eval()

    if part == "unet":
        class UnetWrap(torch.nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m

            def forward(self, sample, t, enc):
                return self.m(sample, t, encoder_hidden_states=enc).sample

        model = UnetWrap(sub)
        batch = 2   # P-6: cfg=7 每步要 cond/uncond,导出 batch=2 与实际一致
        lat = torch.randn(batch, 4, 64, 64, dtype=dtype)
        t = torch.tensor([10.0] * batch)
        enc = torch.randn(batch, 77, 768, dtype=dtype)
        args = (lat, t, enc)
    elif part == "text_encoder":
        class TeWrap(torch.nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m

            def forward(self, ids):
                return self.m(ids)[0]

        model = TeWrap(sub)
        args = (torch.ones(1, 77, dtype=torch.long),)
    else:  # vae
        class VaeWrap(torch.nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m

            def forward(self, x):
                return self.m.decode(x).sample

        model = VaeWrap(sub)
        args = (torch.randn(1, 4, 64, 64, dtype=dtype),)

    model = model.eval()
    with torch.no_grad():
        if dtype == torch.float16:
            model = model.half()
        os.makedirs(os.path.join(OUTDIR, part), exist_ok=True)
        opath = os.path.join(OUTDIR, part, "model.onnx")
        for f in os.listdir(os.path.join(OUTDIR, part)):
            os.remove(os.path.join(OUTDIR, part, f))

        # B2: legacy 导出器(dynamo=False)+ 显式 opset + external data
        try:
            torch.onnx.export(
                model, args, opath,
                opset_version=OPSET,
                dynamo=False,
                do_constant_folding=True,
                input_names=["input"] if part != "unet" else ["sample", "timestep", "encoder_hidden_states"],
                output_names=["output"],
                dynamic_axes=None,
                # B3: >2GB 必须 external data
                save_as_external_data=True,
                all_tensors_to_one_file=True,
                location="model.onnx_data",
            )
        except TypeError:
            # 旧签名不收 external data 参数(仍可能超 2GB,由下方检查兜)
            torch.onnx.export(
                model, args, opath,
                opset_version=OPSET,
                dynamo=False,
                do_constant_folding=True,
                input_names=["input"] if part != "unet" else ["sample", "timestep", "encoder_hidden_states"],
                output_names=["output"],
            )
    sha, files = sha256_group(opath)
    sizes = {os.path.basename(f): os.path.getsize(f) for f in files}
    return opath, sha, sizes


def check_onnx(opath):
    """B2: 导出后 onnx.checker"""
    import onnx
    m = onnx.load(opath, load_external_data=False)
    onnx.checker.check_model(m, full_check=False)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all",
                    choices=["all", "text_encoder", "unet", "vae"])
    a = ap.parse_args()

    t_start = time.time()
    import torch
    from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler

    print(f"[{time.strftime('%H:%M:%S')}] 断网加载 (B1)...", flush=True)
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL, torch_dtype=torch.float32, local_files_only=True)
    pipe = pipe.to("cpu")
    pipe.set_progress_bar_config(disable=True)
    print(f"  load ok, default scheduler = {type(pipe.scheduler).__name__}", flush=True)

    # Q2: scheduler 配置存档(断言放 harness 不放这里, 见 REVIEW-p2 Q2.3)
    sched = pipe.scheduler
    sch = {"class": type(sched).__name__, "config": dict(sched.config)}
    eul = EulerDiscreteScheduler.from_config(sched.config)
    sch["euler_config"] = dict(eul.config)
    with open(os.path.join(OUTDIR, "scheduler-config.json"), "w", encoding="utf-8") as f:
        json.dump(sch, f, ensure_ascii=False, indent=1, default=str)
    print("  scheduler config 存档 -> scheduler-config.json", flush=True)

    # B2: attention processor 切 math/legacy,避免 SDPA 导出失败
    if hasattr(pipe, "unet") and hasattr(pipe.unet, "set_attn_processor"):
        try:
            from diffusers.models.attention_processor import AttnProcessor2_0
            # 用 legacy AttnProcessor 强制 math 路径
            from diffusers.models.attention_processor import AttnProcessor
            n = pipe.unet.attn_processors
            pipe.unet.set_attn_processor(AttnProcessor())
            print(f"  unet attn processors -> legacy AttnProcessor ({len(n)} 个)", flush=True)
        except Exception as e:
            print(f"  WARN: 切 attn processor 失败: {e}", flush=True)

    parts = ["text_encoder", "unet", "vae"] if a.part == "all" else [a.part]
    manifest = {"opset": OPSET, "timebox_s": TIMEBOX_S, "parts": {}}
    if os.path.exists(os.path.join(OUTDIR, "manifest.json")):
        with open(os.path.join(OUTDIR, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        manifest.setdefault("parts", {})

    for p in parts:
        dt_str = PRECISION[p]
        dtype = torch.float16 if dt_str == "fp16" else torch.float32
        if time.time() - t_start > TIMEBOX_S:
            raise SystemExit(f"FATAL(C9): 导出时间盒 {TIMEBOX_S}s 到点,停在 {p}")
        print(f"[{time.strftime('%H:%M:%S')}] 导出 {p} ({dt_str})...", flush=True)
        t0 = time.time()
        opath, sha, sizes = export_part(pipe, p, dtype)
        try:
            check_onnx(opath)
            checker = "ok"
        except Exception as e:
            checker = f"FAIL: {str(e)[:200]}"
        dt = time.time() - t0
        manifest["parts"][p] = {
            "path": opath, "precision": dt_str, "sha256": sha,
            "files": sizes, "seconds": round(dt, 1), "checker": checker,
        }
        total = sum(sizes.values())
        print(f"  {p}: {dt:.1f}s total={total/1024**3:.2f}GB "
              f"checker={checker} sha={sha[:16]}…", flush=True)
        print(f"    files={sizes}", flush=True)

    manifest["elapsed_s"] = round(time.time() - t_start, 1)
    with open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"\nmanifest -> {os.path.join(OUTDIR, 'manifest.json')}", flush=True)
    bad = [k for k, v in manifest["parts"].items() if not str(v["checker"]).startswith("ok")]
    if bad:
        print(f"RESULT FAIL checker={bad}", flush=True)
        sys.exit(1)
    print("RESULT PASS", flush=True)


if __name__ == "__main__":
    main()
