"""PaddleOCR-VL 官方 README 示例一字不差复刻（验证直载基线行为）。"""
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

model_path = r"D:/models/models/ocr/ep13-docparse/PaddleOCR-VL-1.6"
image_path = r"D:/study/ai-jms/ep13-docparse/runs/demo_paddle.png"
task = "ocr"

image = Image.open(image_path).convert("RGB")
max_pixels = 1280 * 28 * 28
PROMPTS = {"ocr": "OCR:"}

model = AutoModelForImageTextToText.from_pretrained(model_path, torch_dtype=torch.bfloat16).eval()
processor = AutoProcessor.from_pretrained(model_path)

messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": PROMPTS[task]},
    ]
}]
inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
    images_kwargs={"size": {"shortest_edge": processor.image_processor.min_pixels, "longest_edge": max_pixels}},
)
print("input keys:", list(dict(inputs).keys()), "| ids", tuple(inputs["input_ids"].shape), flush=True)
outputs = model.generate(**inputs, max_new_tokens=512, use_cache=True)  # config use_cache=False 是官方仓缺陷，否则 512 tok 要 110 分钟
result = processor.decode(outputs[0][inputs["input_ids"].shape[-1]:-1])
print("=== 官方原样输出 ===")
print(result[:800])
