"""dots.ocr 官方 demo_hf.py 复刻（复活实验）：process_vision_info 图像路径 + CPU 适配。
官方差异修复记录:
- 去 attn_implementation=flash_attention_2 (CPU 无; 官方注释亦承认)
- device_map="cpu"
- max_new_tokens 24000→2048 (CPU 成本)
"""
import sys, os, time, json
os.environ.setdefault("LOCAL_RANK", "0")

import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from qwen_vl_utils import process_vision_info

MODEL = r"D:/models/models/ocr/ep13-docparse/dots.ocr"
IMG = r"D:/study/ai-jms/ep13-docparse/runs/demo_paddle.png"
PROMPT_FILE = r"D:/study/ai-jms/ep13-docparse/runs/dots_prompt.txt"
OUT = r"D:/study/ai-jms/ep13-docparse/runs/p0_dots_revive.json"
MAXTOK = int(sys.argv[1]) if len(sys.argv) > 1 else 2048

def main():
    t0 = time.perf_counter()
    # 官方 issue#1 CPU 步骤: attn_implementation 用 sdpa (flash_attention_2→sdpa, CPU推荐)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True,
        attn_implementation="sdpa")
    model.eval()
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    print("[load] %.1fs" % (time.perf_counter() - t0), flush=True)

    prompt = open(PROMPT_FILE, encoding="utf-8").read().strip()
    messages = [{"role": "user", "content": [
        {"type": "image", "image": IMG},
        {"type": "text", "text": prompt}]}]

    # 官方路径: apply_chat_template tokenize=False + process_vision_info
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs,
                       padding=True, return_tensors="pt")
    print("[prep] keys:", list(dict(inputs).keys()), "| ids", tuple(inputs["input_ids"].shape), flush=True)

    # 照抄 transformers 5.x 校验: prepare ∪ forward 参数（**kwargs 不展开）
    import inspect
    allowed = set(inspect.signature(model.prepare_inputs_for_generation).parameters)
    allowed |= set(inspect.signature(model.forward).parameters)
    dropped = [k for k in inputs if k not in allowed]
    if dropped:
        print("[filter] 剔除:", dropped, flush=True)
        inputs = {k: v for k, v in dict(inputs).items() if k in allowed}
    in_ids = inputs["input_ids"]  # dict化后保留引用供切片

    results = []
    for rep in (1, 2):
        t0 = time.perf_counter()
        with torch.no_grad():
            gen_ids = model.generate(**inputs, max_new_tokens=MAXTOK, do_sample=False, use_cache=True)
        wall = time.perf_counter() - t0
        trimmed = [out[len(inn):] for inn, out in zip(in_ids, gen_ids)]
        raw = trimmed[0].tolist()
        from collections import Counter
        print("   raw ids 前40:", raw[:40], "| 总数", len(raw),
              "| top8", Counter(raw).most_common(8), flush=True)
        out_text = processor.batch_decode(trimmed, skip_special_tokens=True,
                                          clean_up_tokenization_spaces=False)[0]
        results.append({"rep": rep, "wall_s": round(wall, 1), "len": len(out_text),
                        "text_head": out_text[:600]})
        print("[rep%d] wall %.1fs | %d 字符 | 头: %s" % (rep, wall, len(out_text),
              out_text[:150].replace("\n", " ")), flush=True)

    ok = all(r["len"] > 200 for r in results)
    same = results[0]["text_head"][:500] == results[1]["text_head"][:500]
    verdict = {"engine": "dots-revive-official", "route": "demo_hf-process_vision_info",
               "reps": results, "judge_nonempty_len": ok, "judge_twice_same": same,
               "verdict": "PASS" if (ok and same) else "FAIL"}
    json.dump(verdict, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("判据: 非空=%s 一致=%s → %s" % (ok, same, verdict["verdict"]), flush=True)
    return 0 if verdict["verdict"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
