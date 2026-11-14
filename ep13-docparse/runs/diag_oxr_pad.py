import subprocess as _sp, json as _json, threading as _th, queue as _q
import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
OX = "D:/models/models/ocr/ep13-docparse/OXR-1.0"
cfg = AutoConfig.from_pretrained(OX, trust_remote_code=True)
am = dict(getattr(cfg, "auto_map", None) or {})
am.setdefault("AutoModel", "modeling_oxr.Siglip2NavitModel")
cfg.auto_map = am
if getattr(cfg, "vit_config", None) is not None:
    cfg.vit_config.auto_map = {"AutoModel": "modeling_oxr.Siglip2NavitModel"}
tok = AutoTokenizer.from_pretrained(OX, trust_remote_code=True)
m = AutoModelForCausalLM.from_pretrained(OX, config=cfg, trust_remote_code=True,
                                         dtype=torch.float32, low_cpu_mem_usage=True).eval()
tt = getattr(m, "text_tokenizer", None)
print("text_tokenizer:", type(tt).__name__ if tt is not None else None)
if tt is not None:
    print("  eos_token=%r eos_id=%r unk_token=%r unk_id=%r pad_token=%r pad_id=%r" % (
        getattr(tt, "eos_token", None), getattr(tt, "eos_token_id", None),
        getattr(tt, "unk_token", None), getattr(tt, "unk_token_id", None),
        getattr(tt, "pad_token", None), getattr(tt, "pad_token_id", None)))
    # 尝试设置
    try:
        tt.pad_token = tt.eos_token or tt.unk_token or "</s>"
        print("  after str set: pad_token=%r pad_id=%r" % (tt.pad_token, tt.pad_token_id))
    except Exception as e:
        print("  str set fail:", e)
    if tt.pad_token_id is None:
        try:
            tt.add_special_tokens({"pad_token": "<pad_oxr>"})
            print("  after add_special: pad_id=%r vocab=%d" % (tt.pad_token_id, len(tt)))
        except Exception as e:
            print("  add_special fail:", e)
