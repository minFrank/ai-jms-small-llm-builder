#!/usr/bin/env python3
"""通用 VL 直载单页测试（P0 判据：非空/长度/两次一致/cold/内存）。
用法: p0_vl_test.py <engine_name> <model_dir> <img_path> [prompt]
每引擎独立 venv 跑；自动处理 auto_map/processor/eos/纯生成切片。"""
import sys, os, time, json

def main():
    engine, MODEL, IMG = sys.argv[1], sys.argv[2], sys.argv[3]
    PROMPT = sys.argv[4] if len(sys.argv) > 4 else "Transcribe all the text content of the image into markdown."
    if PROMPT.startswith("@"):
        PROMPT = open(PROMPT[1:], encoding="utf-8").read().strip()
    MAXTOK = int(sys.argv[5]) if len(sys.argv) > 5 else 2048
    OUT = r"D:/study/ai-jms/ep13-docparse/runs/p0_%s_singlepage.json" % engine
    LOG = lambda m: print(m, flush=True)

    t0 = time.perf_counter()
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, AutoProcessor
    from PIL import Image
    LOG("[1] import %.1fs | torch %s" % (time.perf_counter() - t0, torch.__version__))

    # ① cold load
    t0 = time.perf_counter()
    cfg = AutoConfig.from_pretrained(MODEL, trust_remote_code=True)
    import os as _os
    _dt = {"bf16": torch.bfloat16, "fp32": torch.float32, "fp16": torch.float16}[_os.environ.get("P0_DTYPE", "bf16")]
    try:
        from transformers import AutoModelForImageTextToText as _M
        # 官方调用：不带 trust_remote_code/low_cpu_mem_usage（带了会触发 text_config 属性错）
        model = _M.from_pretrained(MODEL, dtype=_dt)
        LOG("[2] 类: AutoModelForImageTextToText（官方原样）")
    except Exception as _e:
        LOG("[2] ImageTextToText 失败（%s）→ CausalLM" % str(_e)[:100])
        model = AutoModelForCausalLM.from_pretrained(
            MODEL, trust_remote_code=True, dtype=_dt, low_cpu_mem_usage=True)
    model.eval()
    tok = None
    proc = None
    try:
        # 5.x 默认 fast processor，与官方训练时的 slow 预处理可能有差异（Qwen2VL 系已知坑）
        try:
            proc = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True, use_fast=False)
            LOG("[2] processor: use_fast=False（官方 slow 预处理）")
        except Exception as _e1:
            LOG("[2] use_fast=False 失败（%s）→ 默认" % str(_e1)[:80])
            proc = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
        tok = getattr(proc, "tokenizer", None) or proc
    except Exception as e:
        LOG("[2] 无 AutoProcessor（%s）→ 用 AutoTokenizer" % str(e)[:100])
        tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    # pad/eos 兜底
    for holder in (model, tok):
        if holder is not None and getattr(holder, "pad_token_id", None) is None:
            try:
                holder.pad_token = getattr(holder, "eos_token", None) or "</s>"
            except Exception:
                pass
    eos = []
    if tok is not None and tok.eos_token_id is not None:
        eos = [tok.eos_token_id] if not isinstance(tok.eos_token_id, list) else list(tok.eos_token_id)
    gc = getattr(model, "generation_config", None)
    if gc is not None and getattr(gc, "eos_token_id", None):
        e2 = gc.eos_token_id
        for x in (e2 if isinstance(e2, list) else [e2]):
            if x is not None and x not in eos:
                eos.append(x)
    cold = time.perf_counter() - t0
    LOG("[2] cold_load %.1fs | eos %s | pad %s" % (cold, eos[:4], getattr(tok, "pad_token_id", None)))

    img = Image.open(IMG).convert("RGB")
    import os as _o
    _sys = _o.environ.get("P0_SYSTEM")
    messages = []
    if _sys:
        messages.append({"role": "system", "content": _sys})
    messages.append({"role": "user", "content": [
        {"type": "image", "image": img}, {"type": "text", "text": PROMPT}]})

    # ② 输入构造：优先官方单链（apply_chat_template tokenize=True + images_kwargs），失败回退拆分链
    t0 = time.perf_counter()
    MAXPX = int(os.environ.get("P0_MAX_PIXELS", 1280 * 28 * 28))
    inputs = None
    if proc is not None and hasattr(proc, "apply_chat_template"):
        try:
            inputs = proc.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True,
                return_dict=True, return_tensors="pt",
                images_kwargs={"size": {"shortest_edge": getattr(proc.image_processor, "min_pixels", None) or 1280 * 28 * 28,
                                        "longest_edge": MAXPX}})
        except Exception as e:
            print("[3] 官方单链失败（%s）→ 回退拆分链" % str(e)[:140], flush=True)
            inputs = None
    if inputs is None:
        if proc is not None:
            try:
                text = proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                text = None
            inputs = proc(images=img, text=text if text else PROMPT, return_tensors="pt")
        else:
            text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tok(text, return_tensors="pt")
    # 图像键名适配（不同 processor 键不同：pixel_values / image / images）
    # 诊断：图像 size 参数与 placeholder 对齐
    if proc is not None and getattr(proc, "image_processor", None) is not None:
        ip = proc.image_processor
        LOG("[3d] image_processor min_pixels=%s max_pixels=%s size=%s" % (
            getattr(ip, "min_pixels", "?"), getattr(ip, "max_pixels", "?"), getattr(ip, "size", "?")))
    _ids = dict(inputs).get("input_ids")
    if _ids is not None:
        _tok_img = getattr(getattr(model, "config", None), "image_token_id", None)
        n_ph = int((_ids == _tok_img).sum()) if _tok_img is not None else -1
        LOG("[3d] image_token_id=%s placeholder数=%s | ids形状=%s | pixel=%s" % (
            _tok_img, n_ph, tuple(_ids.shape),
            tuple(dict(inputs)["pixel_values"].shape) if "pixel_values" in dict(inputs) else None))
    LOG("[3] preprocess %.2fs | keys %s" % (time.perf_counter() - t0, list(dict(inputs).keys())))

    results = []
    import os as _o2
    _nrep = int(_o2.environ.get("P0_REPS", "2"))
    for rep in range(1, _nrep + 1):
        t0 = time.perf_counter()
        with torch.no_grad():
            _force_eos = _o.environ.get("P0_FORCE_EOS") == "1"
            _pen = {}
            if _o.environ.get("P0_REPETITION_PENALTY"):
                _pen["repetition_penalty"] = float(_o.environ["P0_REPETITION_PENALTY"])
            if _o.environ.get("P0_NO_REPEAT_NGRAM"):
                _pen["no_repeat_ngram_size"] = int(_o.environ["P0_NO_REPEAT_NGRAM"])
            _in = {}
            for _k, _v in dict(inputs).items():
                if hasattr(_v, "is_floating_point") and _v.is_floating_point():
                    _in[_k] = _v.to(model.dtype)  # 官方 client: inputs.to(dtype=model.dtype)
                else:
                    _in[_k] = _v
            # 照抄 transformers 5.x _validate_model_kwargs: prepare 参数 ∪ forward 参数（**kwargs 不展开）
            import inspect as _insp
            _allowed = set(_insp.signature(getattr(model, "prepare_inputs_for_generation", model.forward)).parameters)
            _allowed |= set(_insp.signature(model.forward).parameters)
            _dropped = [k for k in _in if k not in _allowed]
            if _dropped:
                print("   过滤多余键(与transformers校验一致):", _dropped, flush=True)
                _in = {k: v for k, v in _in.items() if k in _allowed}
            out = model.generate(**_in, max_new_tokens=MAXTOK, do_sample=False, use_cache=True,
                                 **_pen,
                                 **({"eos_token_id": eos} if (_force_eos and eos) else {}))
        wall = time.perf_counter() - t0
        # 切片：带 prompt 则去 prompt，纯生成则直用
        in_ids = _in.get("input_ids")
        seq = out[0]
        if in_ids is not None and seq.shape[0] >= in_ids.shape[1] and torch.equal(seq[:in_ids.shape[1]], in_ids[0]):
            gen = seq[in_ids.shape[1]:]
        else:
            gen = seq
        ids_l = gen.tolist()
        from collections import Counter
        print("   raw ids 前30:", ids_l[:30], "| 总数", len(ids_l),
              "| top5", Counter(ids_l).most_common(5), flush=True)
        try:
            md = proc.decode(gen) if (proc is not None and hasattr(proc, "decode")) else tok.decode(gen, skip_special_tokens=True)
        except Exception:
            md = tok.decode(gen, skip_special_tokens=True)
        results.append({"rep": rep, "wall_s": round(wall, 1), "len": len(md), "n_tokens": len(ids_l),
                        "text_head": md[:600]})
        LOG("[rep%d] wall %.1fs | %d tok | 输出 %d 字符 | 头: %s" % (rep, wall, len(ids_l), len(md), md[:120].replace("\n", " ")))

    ok_len = all(r["len"] > 200 for r in results)
    same = len(results) < 2 or results[0]["text_head"][:500] == results[1]["text_head"][:500]
    verdict = {"engine": engine, "route": "transformers-direct", "model_dir": MODEL,
               "cold_load_s": round(cold, 1), "reps": results,
               "judge_nonempty_len": ok_len, "judge_twice_same": same,
               "verdict": "PASS" if (ok_len and same) else "FAIL"}
    json.dump(verdict, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    LOG("判据: 非空+长度=%s | 两次一致=%s → %s" % (ok_len, same, verdict["verdict"]))
    return 0 if verdict["verdict"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
