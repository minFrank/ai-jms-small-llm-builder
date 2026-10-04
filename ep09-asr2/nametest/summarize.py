"""专名专项汇总:8 引擎 × 8 句 → CER 矩阵 + 逐句听写样本 + 类别分析。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NT = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep09-asr2/nametest"
REFS = json.load(open(os.path.join(NT, "samples", "refs.json"), encoding="utf-8"))
CAT = {"N_1": "品牌", "N_2": "品牌", "N_3": "人名", "N_4": "术语",
       "N_5": "中英", "N_6": "中英", "N_7": "品牌", "N_8": "对照"}

# 03 期 6 引擎:result_ep03.json {model/sample/...} 或 rows 结构 —— 先探结构
d3 = json.load(open(os.path.join(NT, "result_ep03.json"), encoding="utf-8"))
print("result_ep03 类型:", type(d3).__name__,
      "| keys:", list(d3)[:6] if isinstance(d3, dict) else f"len={len(d3)}")

rows3 = d3 if isinstance(d3, list) else d3.get("rows") or d3.get("results") or []
if rows3:
    print("样例键:", sorted(rows3[0].keys()))

engines = {}  # engine -> {sample: (cer, text)}

def add(engine, sample, cer, text):
    engines.setdefault(engine, {})[sample.replace(".wav", "")] = (cer, text)

for r in rows3:
    m = str(r.get("model") or r.get("engine") or "?")
    s = str(r.get("sample") or "")
    cer = r.get("cer")
    txt = str(r.get("text") or r.get("hyp") or "")
    if cer is None or not s:
        continue
    add(m, s, float(cer), txt)

for eng_file, tag in (("result_funasr.json", "Fun-ASR-Nano"),
                      ("result_firered.json", "FireRedASR2-AED")):
    p = os.path.join(NT, eng_file)
    if not os.path.exists(p):
        print(f"(待跑) {eng_file}")
        continue
    d = json.load(open(p, encoding="utf-8"))
    for r in d["rows"]:
        add(tag, r["sample"], float(r["cer"]), r["text"])

print("\n=== 各引擎覆盖 ===")
for e, d in engines.items():
    print(f"  {e}: {len(d)} 句")

samples = sorted({s for d in engines.values() for s in d})
order = ["Paraformer", "Fun-ASR-Nano", "SenseVoice", "FireRed", "faster-whisper",
         "whisper", "zipformer", "Zipformer"]
eng_names = sorted(engines, key=lambda x: next(
    (i for i, k in enumerate(order) if k.lower() in x.lower()), 99))

# ---- 表1: CER 矩阵(%) ----
print("\n=== CER 矩阵(%) ===")
hdr = "引擎".ljust(24) + "".join(s.replace("N_", "N").center(7) for s in samples) + "  avg".rjust(8)
print(hdr)
matrix = {}
for e in eng_names:
    vals = []
    cells = []
    for s in samples:
        v = engines[e].get(s)
        if v is None:
            cells.append("  —  ".center(7))
        else:
            cells.append(f"{v[0]*100:6.1f} ".center(7))
            vals.append(v[0])
    avg = sum(vals) / len(vals) * 100 if vals else None
    matrix[e] = avg
    print(e[:24].ljust(24) + "".join(cells) + (f"{avg:7.2f}%" if avg is not None else "      —"))

# ---- 表2: 逐句听写(关键句:专名句的听写文本)----
print("\n=== 逐句听写(前 6 引擎 × 8 句)===")
for s in samples:
    print(f"\n[{s} · {CAT.get(s,'')}] GT: {REFS.get(s+'.wav', '?')}")
    for e in eng_names[:8]:
        v = engines[e].get(s)
        if v:
            flag = "✓" if v[0] == 0 else " "
            print(f"  {flag} {e[:22]:<22} {v[0]*100:5.1f}%  {v[1][:44]}")

# ---- 保存矩阵 ----
out = {"matrix_avg_pct": {k: (round(v, 2) if v is not None else None)
                          for k, v in matrix.items()},
       "engines": {e: {s: {"cer": c, "text": t} for s, (c, t) in d.items()}
                   for e, d in engines.items()},
       "refs": REFS, "cat": CAT}
json.dump(out, open(os.path.join(NT, "summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nsaved -> summary.json")
