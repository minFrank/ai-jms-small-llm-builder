#!/usr/bin/env python3
"""OXR P0 单页直载测试（判据 ①非空UTF-8 ②长度 ④两次一致 ⑤cold/内存记录）。
路线：transformers 直载（vLLM CPU 不可行时的预案）+ 整页识别 prompt。"""
import sys, os, time, json

OX = r"D:/models/models/ocr/ep13-docparse/OXR-1.0"
IMG = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples/hard_02.png"
OUT = r"D:/study/ai-jms/ep13-docparse/runs/p0_oxr_singlepage.json"

def peak_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 2**20
    except Exception:
        return -1

def main():
    t_import = time.perf_counter()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
    t_import = time.perf_counter() - t_import
    print("[1] import %.2fs | torch %s" % (t_import, torch.__version__), flush=True)

    # ① cold load（计时外的模型加载）
    t0 = time.perf_counter()
    cfg = AutoConfig.from_pretrained(OX, trust_remote_code=True)
    # 官方只走 vLLM 路径：transformers 直载需给视觉子模型补 auto_map（Siglip2Navit 未注册）
    am = dict(getattr(cfg, "auto_map", None) or {})
    am.setdefault("AutoModel", "modeling_oxr.Siglip2NavitModel")
    cfg.auto_map = am
    if hasattr(cfg, "vit_config") and cfg.vit_config is not None:
        cfg.vit_config.auto_map = {"AutoModel": "modeling_oxr.Siglip2NavitModel"}
    tok = AutoTokenizer.from_pretrained(OX, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        OX, config=cfg, trust_remote_code=True, dtype=torch.float32,
        low_cpu_mem_usage=True)
    model.eval()
    # checkpoint 不含 indicator_token_indices（persistent=False）；meta/fast-init 后 buffer 为 0，
    # 需显式恢复 __init__ 的 arange(visual_vocab_size-4, visual_vocab_size)
    _vvs = int(getattr(model.config, "visual_vocab_size", 65536))
    model.indicator_token_indices = torch.arange(_vvs - 4, _vvs, dtype=torch.long)
    print("[2b] indicator_token_indices →", model.indicator_token_indices.tolist(), flush=True)
    # modeling 内部 generate 用 self.text_tokenizer.pad_token_id——为 None 会崩
    for holder in (model, getattr(model, "text_tokenizer", None), tok):
        if holder is not None and getattr(holder, "pad_token_id", None) is None:
            try:
                holder.pad_token = holder.eos_token or holder.unk_token or "</s>"
            except Exception:
                pass
    cold = time.perf_counter() - t0
    print("[2] cold_load %.1fs | peak_rss %.0f MB" % (cold, peak_mb()), flush=True)

    # ② 官方入口：preprocess_inputs(messages) → (input_ids, pixel_values, grid_thws)
    from PIL import Image
    img = Image.open(IMG).convert("RGB")
    prompt = "Recognize the whole page content of the image."
    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": prompt}]}]
    t0 = time.perf_counter()
    input_ids, pixel_values, grid_thws = model.preprocess_inputs(messages)
    prep = time.perf_counter() - t0
    print("[3] preprocess_inputs %.2fs | ids %s | pixel %s | grid %s" % (
        prep, tuple(input_ids.shape),
        None if pixel_values is None else tuple(pixel_values.shape),
        None if grid_thws is None else tuple(grid_thws.shape)), flush=True)

    results = []
    for rep in (1, 2):
        if rep == 1:
            idx = model.indicator_token_indices
            print("[现场] vte.weight %s | indices %s (dtype %s, max %s) | input_ids min/max %s/%s | pixel %s" % (
                tuple(model.vte.weight.shape), idx.tolist(), idx.dtype,
                idx.max().item() if idx.numel() else "-",
                input_ids.min().item(), input_ids.max().item(),
                None if pixel_values is None else (tuple(pixel_values.shape), pixel_values.dtype)), flush=True)
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(
                inputs=input_ids, pixel_values=pixel_values, grid_thws=grid_thws,
                max_new_tokens=2048, do_sample=False,
                eos_token_id=[151643, 151645], pad_token_id=151643)
        wall = time.perf_counter() - t0
        seq = out[0] if hasattr(out, "shape") else out
        # inputs_embeds 路径下 llm.generate 返回纯生成序列（无 prompt）
        if seq.shape[0] >= input_ids.shape[1] and torch.equal(seq[:input_ids.shape[1]], input_ids[0]):
            gen = seq[input_ids.shape[1]:]
        else:
            gen = seq
        ids_list = gen.tolist()
        print("   raw ids 前40:", ids_list[:40], flush=True)
        from collections import Counter
        print("   raw ids 分布 top6:", Counter(ids_list).most_common(6), "| 总数", len(ids_list), flush=True)
        md = tok.decode(gen, skip_special_tokens=True)
        results.append({"rep": rep, "wall_s": round(wall, 2), "len": len(md),
                        "text": md[:2000], "peak_mb": round(peak_mb())})
        print("[rep%d] wall %.1fs | 输出 %d 字符 | peak %.0f MB" % (rep, wall, len(md), peak_mb()), flush=True)
        print("   头 150 字:", md[:150].replace("\n", " "), flush=True)

    # 判据
    ok1 = all(r["len"] > 200 for r in results)                     # ①② 非空+长度
    same = results[0]["text"][:500] == results[1]["text"][:500]    # ④ 两次一致
    verdict = {
        "engine": "oxr", "route": "transformers-direct",
        "cold_load_s": round(cold, 1), "import_s": round(t_import, 2),
        "reps": results, "judge_nonempty_len": ok1, "judge_twice_same": same,
        "has_processor": False,
        "verdict": "PASS" if (ok1 and same) else "FAIL",
    }
    json.dump(verdict, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("判据: 非空+长度=%s | 两次一致=%s → %s" % (ok1, same, verdict["verdict"]), flush=True)
    return 0 if verdict["verdict"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
