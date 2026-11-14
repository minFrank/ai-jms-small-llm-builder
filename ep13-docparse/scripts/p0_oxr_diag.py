#!/usr/bin/env python3
"""OXR 直载链路诊断：逐步执行 merge_multimodal 各步，打印 shape/dtype/index 边界。"""
import sys, time, json, traceback
OX = r"D:/models/models/ocr/ep13-docparse/OXR-1.0"
IMG = r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples/hard_02.png"

def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoConfig
    from PIL import Image

    cfg = AutoConfig.from_pretrained(OX, trust_remote_code=True)
    am = dict(getattr(cfg, "auto_map", None) or {})
    am.setdefault("AutoModel", "modeling_oxr.Siglip2NavitModel")
    cfg.auto_map = am
    if getattr(cfg, "vit_config", None) is not None:
        cfg.vit_config.auto_map = {"AutoModel": "modeling_oxr.Siglip2NavitModel"}
    model = AutoModelForCausalLM.from_pretrained(
        OX, config=cfg, trust_remote_code=True, dtype=torch.bfloat16, low_cpu_mem_usage=True)
    model.eval()

    img = Image.open(IMG).convert("RGB")
    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": "Recognize the whole page content of the image."}]}]
    input_ids, pixel_values, grid_thws = model.preprocess_inputs(messages)
    print("input_ids:", tuple(input_ids.shape), "dtype", input_ids.dtype,
          "| min", input_ids.min().item(), "max", input_ids.max().item(), flush=True)
    neg = input_ids[input_ids < 0]
    print("负 id 种类:", sorted(neg.unique().tolist()), "共", neg.numel(), flush=True)
    print("pixel:", None if pixel_values is None else (tuple(pixel_values.shape), pixel_values.dtype),
          "| grid:", None if grid_thws is None else (tuple(grid_thws.shape), grid_thws.dtype),
          grid_thws, flush=True)

    # 逐步 merge
    mask = torch.lt(input_ids, 0)
    wte = model.get_wte()
    print("wte:", tuple(wte.weight.shape), wte.weight.dtype, flush=True)
    e = wte(torch.masked_fill(input_ids, mask, 0))
    print("① 文本 embed OK:", tuple(e.shape), flush=True)

    print("vte:", tuple(model.vte.weight.shape), model.vte.weight.dtype, flush=True)
    print("indicator_token_indices:", model.indicator_token_indices.tolist(), flush=True)
    vi = model.vte(model.indicator_token_indices)
    print("② indicator embed OK:", tuple(vi.shape), flush=True)

    t0 = time.perf_counter()
    vt = model.visual_tokenizer(pixel_values, grid_thws)
    print("③ visual_tokens:", tuple(vt.shape), vt.dtype, "%.1fs" % (time.perf_counter() - t0), flush=True)
    ve = model.vte(vt)
    print("④ visual embed OK:", tuple(ve.shape), flush=True)

    n_atoms = int((input_ids == -300).sum())
    print("VISUAL_ATOM(-300) 数:", n_atoms, "| visual rows:", ve.shape[0], "→", 
          "匹配" if n_atoms == ve.shape[0] else "★不匹配★", flush=True)
    n_ind = {i: int((input_ids == i).sum()) for i in (-301, -302, -303, -304)}
    print("indicator 出现次数:", n_ind, flush=True)

    # 完整 merge
    me = model.merge_multimodal(input_ids=input_ids, pixel_values=pixel_values, grid_thws=grid_thws)
    print("⑤ merge_multimodal OK:", tuple(me.shape), me.dtype, flush=True)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
