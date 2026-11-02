"""STEP 1-C：验证 GLM-OCR 冷热差的真实成因 —— 是否为 prompt 缓存。

假设：warm 的 1.14s 是因为 Ollama 命中 prompt 缓存、跳过了视觉编码+prefill；
     真实跑测每张图不同 → 必然缓存未命中 → 耗时应接近 cold。

判别设计（同图同模型，只改 prompt 一个字）：
  A 组 同 prompt 重发   → 命中缓存 → 预期快
  B 组 prompt 改一个字 → 缓存未命中 → 预期慢（若回到 120s 量级则假设成立）

同时读 Ollama 自报的 prompt_eval_count / prompt_eval_duration 定位时间去向。
"""
import base64
import json
import pathlib
import time

import requests

API = "http://127.0.0.1:11434/api/generate"
MODEL = "glm-ocr:latest"
IMG_DIR = pathlib.Path(
    r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/ep11-ocr/output/samples")
OUT = pathlib.Path(r"D:/models/ollama/smoke_cache.json")
IMG = "skew_01.png"


def unload():
    """卸载模型，并确认它真的不在内存里。

    ⚠️ 检查必须用 /api/ps（已加载的模型），不能用 /api/tags —— 后者列的是
    已下载的模型，glm-ocr 已 pull 下来就永远在里面，会导致永远判"卸载失败"。
    """
    try:
        requests.post(API, json={"model": MODEL, "keep_alive": 0}, timeout=120)
    except Exception:
        pass
    for _ in range(20):
        time.sleep(3)
        try:
            ps = requests.get("http://127.0.0.1:11434/api/ps", timeout=30).text
        except Exception:
            ps = ""
        if "glm-ocr" not in ps:
            return True
    return False


def call(s, b64, prompt, keep="1h"):
    t0 = time.time()
    r = s.post(API, json={
        "model": MODEL, "prompt": prompt, "images": [b64],
        "stream": False, "options": {"temperature": 0.0}, "keep_alive": keep,
    }, timeout=1800)
    dt = time.time() - t0
    d = r.json() if r.status_code == 200 else {}
    return {
        "t_s": round(dt, 2),
        "load_duration_s": round((d.get("load_duration") or 0) / 1e9, 3),
        "prompt_eval_count": d.get("prompt_eval_count"),
        "prompt_eval_duration_s": round((d.get("prompt_eval_duration") or 0) / 1e9, 3),
        "eval_count": d.get("eval_count"),
        "eval_duration_s": round((d.get("eval_duration") or 0) / 1e9, 3),
        "total_duration_s": round((d.get("total_duration") or 0) / 1e9, 3),
        "text_len": len(d.get("response", "")),
        "text_head": d.get("response", "")[:90],
    }


def main():
    s = requests.Session()
    b64 = base64.b64encode((IMG_DIR / IMG).read_bytes()).decode()
    res = {"image": IMG, "runs": []}
    print("=" * 74)
    print("STEP 1-C · GLM-OCR 冷热差成因判别（同图，只改 prompt）")
    print("=" * 74)
    print("  图: %s (%.0f KB)" % (IMG, (IMG_DIR / IMG).stat().st_size / 1024))

    # R1 冷启动（首次，模型未驻留）
    print("\n[R1] 冷启动 · 首次请求 · prompt A")
    assert unload(), "卸载失败"
    r = call(s, b64, "Read all the text in this image.")
    r["tag"] = "R1_cold_promptA"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    # R2 同 prompt 重发（预期命中缓存 → 快）
    print("\n[R2] 同 prompt 重发 · prompt A（预期命中缓存）")
    r = call(s, b64, "Read all the text in this image.")
    r["tag"] = "R2_same_promptA"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    # R3 改一个字（预期缓存未命中 → 慢回 cold 量级）
    print("\n[R3] prompt 改一个字 · prompt B（预期缓存未命中）")
    r = call(s, b64, "Read all the text in this imagex.")
    r["tag"] = "R3_changed_promptB"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    # R4 再改一个字（再验一次）
    print("\n[R4] prompt 再改一个字 · prompt C")
    r = call(s, b64, "Read all text in this image.")
    r["tag"] = "R4_changed_promptC"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    # R5 换一张图（模拟真实跑测：每张图都不同）
    print("\n[R5] 换图 table_01 · prompt A（模拟真实跑测：图必然不同）")
    b64b = base64.b64encode((IMG_DIR / "table_01.png").read_bytes()).decode()
    r = call(s, b64b, "Read all the text in this image.")
    r["tag"] = "R5_new_image"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    # R6 同图再重发一次（确认缓存又命中）
    print("\n[R6] table_01 同 prompt 重发")
    r = call(s, b64b, "Read all the text in this image.")
    r["tag"] = "R6_new_image_repeat"
    res["runs"].append(r)
    print("   t=%7.2fs  load=%.1fs  prompt_eval_count=%-6s prompt_eval=%.1fs  eval=%-4s eval_t=%.2fs"
          % (r["t_s"], r["load_duration_s"], r["prompt_eval_count"],
             r["prompt_eval_duration_s"], r["eval_count"], r["eval_duration_s"]))

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已写:", OUT)

    print("\n" + "=" * 74)
    print("【判别结论】")
    by = {x["tag"]: x for x in res["runs"]}
    a, b, c, d_, e, f = (by[k] for k in ["R1_cold_promptA", "R2_same_promptA",
                                         "R3_changed_promptB", "R4_changed_promptC",
                                         "R5_new_image", "R6_new_image_repeat"])
    print("  R1 冷启动        %7.2fs   prompt_eval=%s (%.1fs)" % (a["t_s"], a["prompt_eval_count"], a["prompt_eval_duration_s"]))
    print("  R2 同 prompt     %7.2fs   prompt_eval=%s (%.1fs)" % (b["t_s"], b["prompt_eval_count"], b["prompt_eval_duration_s"]))
    print("  R3 改一字        %7.2fs   prompt_eval=%s (%.1fs)" % (c["t_s"], c["prompt_eval_count"], c["prompt_eval_duration_s"]))
    print("  R4 再改一字      %7.2fs   prompt_eval=%s (%.1fs)" % (d_["t_s"], d_["prompt_eval_count"], d_["prompt_eval_duration_s"]))
    print("  R5 换图          %7.2fs   prompt_eval=%s (%.1fs)" % (e["t_s"], e["prompt_eval_count"], e["prompt_eval_duration_s"]))
    print("  R6 换图重发      %7.2fs   prompt_eval=%s (%.1fs)" % (f["t_s"], f["prompt_eval_count"], f["prompt_eval_duration_s"]))
    cache_hit = b["t_s"] < a["t_s"] * 0.5
    miss_slow = c["t_s"] > a["t_s"] * 0.5
    print("\n  同 prompt 重发显著变快（缓存命中）? %s" % ("✅ 是" if cache_hit else "❌ 否"))
    print("  改一字后回到慢档（缓存未命中）?     %s" % ("✅ 是" if miss_slow else "❌ 否"))
    if cache_hit and miss_slow:
        print("  → 结论：冷热差来自 prompt 缓存，不是模型加载")
        print("  → 真实跑测每张图不同 = 必然缓存未命中 → 应按 R1/R3/R5 那档估排期")


if __name__ == "__main__":
    main()
