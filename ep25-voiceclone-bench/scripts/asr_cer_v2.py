#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ep25 字准率重算 v2 —— 补数字归一化。

问题：ASR 把中文数字写成阿拉伯数字（"二零二六年" → "2026年"），
      TTS 念得是对的，但原归一化（NFKC + 滤标点）不处理这个，导致
      数字组 CER 被"写法差异"撑到 31.98%，不能反映 TTS 的实际准确率。

做法：**GT 和 ASR 结果走同一套归一化**（对称），写法差异在两边抵消。
      归一化只动数字写法与"百分之"，不动单位词（赫兹/秒/GB 等）——
      单位词的差异可能是真的念错，不能抹掉。
"""
import os, sys, json, re, unicodedata, statistics
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SLOT = r"D:/study/ai-jms/voice_samples/ep25_run/slot_0015"
INP  = os.path.join(SLOT, "asr_cer.json")
OUTP = os.path.join(SLOT, "asr_cer_v2.json")

_D = {"零": "0", "〇": "0", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4",
      "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
_U = {"十": 10, "百": 100, "千": 1000}
_RUN = set(_D) | set(_U) | {"万", "点"}

def _int_part(s):
    """整数部分：纯逐位（无 十百千）→ 直接拼；否则按 十百千 累加"""
    if all(ch in _D for ch in s):
        return "".join(_D[ch] for ch in s)
    total, cur = 0, 0
    for ch in s:
        if ch in _D:
            cur = int(_D[ch])          # _D 的值是字符串，这里必须转 int
        elif ch in _U:
            total += (cur or 1) * _U[ch]; cur = 0
    total += cur
    return str(total)

def _num(m):
    """把一段中文数字转成阿拉伯"""
    run = m.group(0)
    if "点" in run:
        a, b = run.split("点", 1)
        ip = _int_part(a) if a else "0"
        dp = "".join(_D.get(c, "") for c in b)
        return ip + "." + dp
    if "万" in run:
        a, _, b = run.partition("万")
        return str((_int_part(a) if a else 1) * 10000 + (_int_part(b) if b and any(c in _D for c in b) else 0))
    return _int_part(run)

def norm_zh_v2(s):
    """对称归一化 v2：NFKC → 滤标点 → 中文数字转阿拉伯 → 百分之 → % → 去空白小写"""
    s = unicodedata.normalize("NFKC", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "P")
    # 百分之X.X → X.X%   （先于数字转换，避免"百分之"里的"百"被当单位）
    s = re.sub(r"百分之([零〇一二两三四五六七八九十百千万点]+)", r"\1%", s)
    # 一段连续的中文数字
    s = re.sub("[%s]+" % "".join(_RUN), _num, s)
    return re.sub(r"\s+", "", s.lower())

def _ed(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def cer(ground, hyp):
    g, h = norm_zh_v2(ground), norm_zh_v2(hyp)
    if not g:
        return 0.0 if not h else 100.0
    return round(_ed(h, g) * 100.0 / len(g), 2)

def main():
    d = json.load(open(INP, encoding="utf-8"))
    rs = d["results"]

    # 自检：归一化对不对，拿题库原文试
    tests = [
        ("二零二六年十月二十七日", "2026年10月27日"),
        ("百分之十二点六", "12.6%"),
        ("两万四千赫兹", "24000赫兹"),
        ("六百七十九KB", "679KB"),
        ("零点六个B", "0.6个B"),
        ("二点三四GB", "2.34GB"),
        ("十四秒", "14秒"),
        ("二十四", "24"),
    ]
    print("=== 归一化自检（GT 写法 vs ASR 写法，应归一到相同）===")
    allok = True
    for a, b in tests:
        na, nb = norm_zh_v2(a), norm_zh_v2(b)
        ok = na == nb
        allok = allok and ok
        print("  %-16s → %-22s | %-16s → %-22s %s" % (a, na, b, nb, "✓" if ok else "✗"))
    print("  自检: %s" % ("全过" if allok else "**有不一致，结果需谨慎读**"))
    print()

    for r in rs:
        r["cer_v2_pct"] = cer(r["ref_text"], r["asr_text"])
        r["cer_v2_all"] = [cer(r["ref_text"], h) for h in r["asr_hyps"]]

    ok = [r for r in rs if r.get("asr_ok")]
    print("=== 按引擎（v2 归一化后）===")
    print("  %-22s %3s %9s %9s %9s %9s %7s" % ("引擎", "n", "v2中位", "v1中位", "v2均值", "v2最大", "全对"))
    eng = {}
    for r in ok: eng.setdefault(r["engine"], []).append(r)
    for e, xs in sorted(eng.items(), key=lambda kv: statistics.median(x["cer_v2_pct"] for x in kv[1])):
        v2 = [x["cer_v2_pct"] for x in xs]
        v1 = [x["cer_pct"] for x in xs]
        print("  %-22s %3d %8.2f%% %8.2f%% %8.2f%% %8.2f%% %4d/%d"
              % (e[:22], len(v2), statistics.median(v2), statistics.median(v1),
                 sum(v2)/len(v2), max(v2), sum(1 for v in v2 if v == 0.0), len(v2)))

    print("\n=== 按题组（v2 vs v1）===")
    grp = {}
    for r in ok: grp.setdefault(r.get("group") or "?", []).append((r["cer_v2_pct"], r["cer_pct"]))
    for g, pairs in sorted(grp.items()):
        v2 = [p[0] for p in pairs]; v1 = [p[1] for p in pairs]
        print("  %-14s n=%-3d v2中位 %6.2f%%  v1中位 %6.2f%%  Δ %+6.2fpp"
              % (g[:14], len(pairs), statistics.median(v2), statistics.median(v1),
                 statistics.median(v2) - statistics.median(v1)))

    print("\n=== v2 下仍最差的 6 条 ===")
    for w in sorted(ok, key=lambda x: -x["cer_v2_pct"])[:6]:
        print("  %-22s %-5s v2=%6.2f%%" % (w["engine"][:22], w["qid"], w["cer_v2_pct"]))
        print("     题: %s" % w["ref_text"][:44])
        print("     识: %s" % str(w["asr_text"])[:44])

    d["norm_version"] = "v2-对称数字归一化"
    d["norm_selfcheck_pass"] = allok
    tmp = OUTP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, OUTP)
    print("\n落盘: %s" % OUTP)

if __name__ == "__main__":
    main()
