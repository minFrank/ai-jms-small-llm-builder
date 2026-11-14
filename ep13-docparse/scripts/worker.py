"""ep13 worker —— 每引擎独立 venv 的子进程（NDJSON over stdout/stdin）
协议: runner → {"cmd":"hello|load|infer|teardown", ...}  worker → {"ok":bool, ...}
r4 盯点: infer 内禁隐式加载(load 命令显式) / timeout 由 runner kill / 迟到响应丢弃
引擎直载 = P0 已实证路径（官方类 / use_fast=False / 签名过滤 / 官方 prompt）
"""
from __future__ import annotations
import sys, os, json, time, io, traceback

def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

ENGINE = None          # load 后的模型上下文
MODELS = "D:/models/models/ocr/ep13-docparse"     # 本地只读（C 盘零写入）
ENGINES = {
    "paddleocr_vl": dict(repo=MODELS + "/PaddleOCR-VL-1.6",
                         prompt="OCR:", max_new=2048),
    "xiaomi_vl":    dict(repo=MODELS + "/Xiaomi-OCR-0",
                         prompt="Transcribe all the text content of the image into markdown.", max_new=2048),
    "ovis_ocr2":    dict(repo=MODELS + "/OvisOCR2",
                         prompt="Transcribe all the text content of the image into markdown.", max_new=2048),
    "monkey_rec":   dict(repo=MODELS + "/MonkeyOCR-pro-1.2B/Recognition",
                         prompt="Transcribe all the text content of the image into markdown.", max_new=2048),
    "surya_2_5":    dict(repo=MODELS + "/surya-ocr-2.5",
                         prompt="Transcribe all the text content of the image into markdown.", max_new=2048),
    "oxr":          dict(repo=MODELS + "/OXR-1.0",
                         prompt=None, max_new=2048),        # 三服务路径另接
}

def cmd_hello(arg: dict) -> dict:
    import torch, transformers
    return dict(ok=True, protocol_v=1, engine=arg.get("engine"),
                python=sys.version.split()[0], torch=torch.__version__,
                transformers=transformers.__version__)

def cmd_load(arg: dict) -> dict:
    """显式加载（cold_load 记录在 session，worker 只执行）"""
    global ENGINE
    t0 = time.time()
    eng = arg["engine"]
    cfg = ENGINES[eng]
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText, AutoTokenizer
        repo = arg.get("repo") or cfg["repo"]
        if eng == "oxr":
            # P0 p0_oxr_singlepage 专用链（通用直载不适用）：补 auto_map + CausalLM + buffer 恢复
            from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer as ATok
            _c = AutoConfig.from_pretrained(repo, trust_remote_code=True)
            am = dict(getattr(_c, "auto_map", None) or {})
            am.setdefault("AutoModel", "modeling_oxr.Siglip2NavitModel")
            _c.auto_map = am
            if getattr(_c, "vit_config", None) is not None:
                _c.vit_config.auto_map = {"AutoModel": "modeling_oxr.Siglip2NavitModel"}
            _tok = ATok.from_pretrained(repo, trust_remote_code=True)
            _m = AutoModelForCausalLM.from_pretrained(
                repo, config=_c, trust_remote_code=True, dtype=torch.float32,
                low_cpu_mem_usage=True).eval()
            _vvs = int(getattr(_m.config, "visual_vocab_size", 65536))
            _m.indicator_token_indices = torch.arange(_vvs - 4, _vvs, dtype=torch.long)
            # modeling_oxr.generate:978 用 self.text_tokenizer.pad_token_id（None 即崩）
            _tt = getattr(_m, "text_tokenizer", None)
            if _tt is not None and getattr(_tt, "pad_token_id", None) is None:
                _tt.pad_token = getattr(_tt, "eos_token", None) or "<|end_of_text|>"
                if _tt.pad_token_id is None:
                    _tt.add_special_tokens({"pad_token": "<pad_oxr>"})
                if _tt.pad_token_id is None:
                    raise RuntimeError("text_tokenizer.pad_token_id 仍为 None（OXR pad 修复失败）")
            for _h in (_m, _tt, _tok):
                if _h is None or getattr(_h, "pad_token_id", None) is not None: continue
                try: _h.pad_token = getattr(_h, "eos_token", None) or "</s>"
                except Exception: pass
            ENGINE = dict(model=_m, processor=None, tokenizer=_tok, eng=eng, cfg=cfg, eos=[])
            return dict(ok=True, load_wall=round(time.time() - t0, 2))
        _kw = dict(dtype=torch.float32, trust_remote_code=False)   # P0: fp32 CPU
        if eng == "monkey_rec":
            _kw["low_cpu_mem_usage"] = True    # 4.83GB 模型分片加载降峰值（MemoryError 缓解）
        model = AutoModelForImageTextToText.from_pretrained(repo, **_kw)
        processor = AutoProcessor.from_pretrained(repo, trust_remote_code=False)
        tokenizer = AutoTokenizer.from_pretrained(repo, trust_remote_code=False, use_fast=False)
        # eos 收集（P0 同款：tok ∪ generation_config——防 EOS 不被 generate 认致复读）
        eos = []
        if tokenizer.eos_token_id is not None:
            eos = [tokenizer.eos_token_id] if not isinstance(tokenizer.eos_token_id, list) else list(tokenizer.eos_token_id)
        gc = getattr(model, "generation_config", None)
        if gc is not None and getattr(gc, "eos_token_id", None):
            e2 = gc.eos_token_id
            for x in (e2 if isinstance(e2, list) else [e2]):
                if x is not None and x not in eos: eos.append(x)
        ENGINE = dict(model=model, processor=processor, tokenizer=tokenizer, eng=eng, cfg=cfg, eos=eos)
        # warmup（不记账）
        return dict(ok=True, load_wall=round(time.time() - t0, 2))
    except Exception as e:
        return dict(ok=False, err=f"load:{type(e).__name__}:{e}", trace=traceback.format_exc()[-800:])

def cmd_infer(arg: dict) -> dict:
    """P0 路径：签名过滤键 + 官方 prompt + greedy；返回 rep dict"""
    global ENGINE
    if ENGINE is None:
        return dict(ok=False, err="not_loaded")
    t0 = time.time()
    try:
        import torch
        from PIL import Image
        eng, cfg = ENGINE["eng"], ENGINE["cfg"]
        model, processor, tok = ENGINE["model"], ENGINE["processor"], ENGINE["tokenizer"]
        img = Image.open(arg["path"]).convert("RGB")
        if eng == "oxr":
            # P0 专用：preprocess_inputs(messages) → generate → 切片 decode
            _m = ENGINE["model"]
            _prompt = "Recognize the whole page content of the image."
            _msgs = [{"role": "user", "content": [
                {"type": "image", "image": img}, {"type": "text", "text": _prompt}]}]
            t_p0 = time.time()
            input_ids, pixel_values, grid_thws = _m.preprocess_inputs(_msgs)
            prep = time.time() - t_p0
            t_g0 = time.time()
            with torch.no_grad():
                out = _m.generate(inputs=input_ids, pixel_values=pixel_values,
                                  grid_thws=grid_thws, do_sample=False,
                                  max_new_tokens=int(arg.get("max_new", 2048)),
                                  use_cache=True,
                                  eos_token_id=[151643, 151645],
                                  pad_token_id=int(getattr(getattr(_m, "text_tokenizer", None), "pad_token_id", None) or 151643))
            wall_self = time.time() - t_g0
            seq = out[0]
            gen = seq[input_ids.shape[1]:] if seq.shape[0] >= input_ids.shape[1] else seq
            text = ENGINE["tokenizer"].decode(gen, skip_special_tokens=True)
            wall = time.time() - t0
            return dict(ok=True, status="ok", wall=round(wall, 3), wall_self=round(wall_self, 3),
                        text_len=len(text), text=text, truncated=False,
                        err_kind=None, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
        # ---- 输入构造 = P0 单链（p0_vl_test 实证：apply_chat_template 官方链）----
        prompt_txt = cfg["prompt"] or "Please output the text content from the image."
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img}, {"type": "text", "text": prompt_txt}]}]
        MAXPX = 1280 * 28 * 28
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt",
            images_kwargs={"size": {"shortest_edge": getattr(processor.image_processor, "min_pixels", None) or 1280 * 28 * 28,
                                    "longest_edge": MAXPX}})
        # 只转浮点张量（input_ids/attention_mask 保持 long——P0 实证 dtype匹配）
        inputs = {k: (v.to(dtype=model.dtype) if (hasattr(v, "to") and hasattr(v, "is_floating_point") and v.is_floating_point()) else v)
                  for k, v in inputs.items()}
        t_gen0 = time.time()
        with torch.no_grad():
            _eos = ENGINE.get("eos") or []
            out = model.generate(**inputs, do_sample=False, max_new_tokens=int(arg.get("max_new", cfg["max_new"])),
                                 use_cache=True, pad_token_id=tok.pad_token_id or tok.eos_token_id or 0,
                                 **({"eos_token_id": _eos} if _eos else {}))
        wall_self = time.time() - t_gen0
        n_in = inputs["input_ids"].shape[1]
        gen = out[:, n_in:]
        text = tok.batch_decode(gen, skip_special_tokens=True)[0]
        wall = time.time() - t0          # 端到端（预处理起→解码止，engines.yaml 口径）
        return dict(ok=True, status="ok", wall=round(wall, 3), wall_self=round(wall_self, 3),
                    text_len=len(text), text=text, truncated=False,
                    err_kind=None, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
    except Exception as e:
        return dict(ok=False, status="fail", err=f"infer:{type(e).__name__}:{e}",
                    trace=traceback.format_exc()[-800:])

def cmd_teardown(arg: dict) -> dict:
    global ENGINE
    ENGINE = None
    import gc; gc.collect()
    return dict(ok=True)

HANDLERS = {"hello": cmd_hello, "load": cmd_load, "infer": cmd_infer, "teardown": cmd_teardown}

def main() -> None:
    emit(dict(ok=True, event="boot", pid=os.getpid()))
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
        except Exception:
            emit(dict(ok=False, err="bad_json")); continue
        cmd = req.get("cmd")
        if cmd == "exit": emit(dict(ok=True, event="bye")); break
        h = HANDLERS.get(cmd)
        if not h: emit(dict(ok=False, err=f"unknown_cmd:{cmd}")); continue
        emit(h(req))

if __name__ == "__main__":
    main()
