#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ep25 字准率重算 v3 —— 修 v2 的两个 bug。

v2 的自检抓出两个问题（不放过的那种）：
  1) 小数点被滤掉：`.` 和 `%` 都是 Unicode P 类，在 NFKC 之后的 P 过滤里被删，
     导致 "12.6%" → "126"、"2.34GB" → "234gb"。数字组 CER 被这个扭曲。
  2) ASR 输出繁简不稳定：88 条转写里 49 条（56%）含繁体字，四家引擎均匀分布
     （13/14/14/8），是 faster-whisper 的行为、不是被测引擎的问题。
     不归一化的话，"他喜欢音乐" vs "他喜歡音樂" 会被算成 31.58% 的错误。

v3 做法：
  - 繁→简映射表（数据驱动：只映射本次真出现过的字 + 少量高频安全字）
  - 数字归一化提前到 P 过滤之前，小数点用占位符保护
  - GT 与 hyp 走同一套（对称），写法差异两边抵消
"""
import os, sys, json, re, unicodedata, statistics
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SLOT = r"D:/study/ai-jms/voice_samples/ep25_run/slot_0015"
# 优先读 v2（含 cer_v2_pct），没有就退回 v1（含 cer_pct）
INP  = os.path.join(SLOT, "asr_cer_v2.json")
if not os.path.exists(INP):
    INP = os.path.join(SLOT, "asr_cer.json")
OUTP = os.path.join(SLOT, "asr_cer_v3.json")

# 繁→简：本次数据真出现的 10 组 + 少量高频安全字
T2S = {
    "個":"个","參":"参","後":"后","數":"数","於":"于","樂":"乐",
    "歡":"欢","說":"说","這":"这","長":"长",
    "來":"来","點":"点","東":"东","開":"开","關":"关","發":"发",
    "現":"现","實":"实","應":"应","該":"该","時":"时","間":"间",
    "問":"问","題":"题","語":"语","話":"话","過":"过","還":"还",
    "門":"门","電":"电","車":"车","買":"买","賣":"卖","價":"价",
    "員":"员","場":"场","廣":"广","經":"经","產":"产","術":"术",
    "藝":"艺","認":"认","請":"请","機":"机","條":"条","練":"练",
    "結":"结","處":"处","從":"从","對":"对","為":"为","與":"与",
    "萬":"万","億":"亿","幾":"几","們":"们","無":"无","麼":"么",
}

_D = {"零":"0","〇":"0","一":"1","二":"2","两":"2","三":"3","四":"4",
      "五":"5","六":"6","七":"7","八":"8","九":"9"}
_U = {"十":10,"百":100,"千":1000}
_RUN = set(_D) | set(_U) | {"万","点"}
_DOT = "\x01"          # 小数点占位符，扛过 P 过滤

def _int_part(s):
    if all(ch in _D for ch in s):
        return "".join(_D[ch] for ch in s)
    total, cur = 0, 0
    for ch in s:
        if ch in _D:
            cur = int(_D[ch])
        elif ch in _U:
            total += (cur or 1) * _U[ch]; cur = 0
    return str(total + cur)

def _num(m):
    run = m.group(0)
    if "点" in run:
        a, _, b = run.partition("点")
        return (_int_part(a) if a else "0") + _DOT + "".join(_D.get(c, "") for c in b)
    if "万" in run:
        a, _, b = run.partition("万")
        head = _int_part(a) if a else "1"
        tail = _int_part(b) if b and any(c in _D for c in b) else "0"
        return str(int(head) * 10000 + int(tail))
    return _int_part(run)

def norm(s):
    """对称归一化 v3"""
    if not s:
        return ""
    # 1) 繁→简
    s = "".join(T2S.get(ch, ch) for ch in s)
    # 2) 百分之X → X%（先于数字转换）
    s = re.sub(r"百分之([零〇一二两三四五六七八九十百千万点]+)", r"\1%", s)
    # 3) 中文数字 → 阿拉伯（此时 '.' 还在，可安全产出）
    s = re.sub("[%s]+" % "".join(sorted(_RUN)), _num, s)
    # 4) 已有阿拉伯小数点先保护起来
    s = re.sub(r"(?<=\d)\.(?=\d)", _DOT, s)
    # 5) NFKC + 滤标点
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "P")
    # 6) 还原小数点、去空白、小写
    s = s.replace(_DOT, ".")
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
    g, h = norm(ground), norm(hyp)
    if not g:
        return 0.0 if not h else 100.0
    return round(_ed(h, g) * 100.0 / len(g), 2)

def main():
    # ---- 自检：v2 挂掉的那几组必须过 ----
    tests = [
        ("二零二六年十月二十七日", "2026年10月27日"),
        ("百分之十二点六",         "12.6%"),
        ("两万四千赫兹",           "24000赫兹"),
        ("六百七十九KB",           "679KB"),
        ("零点六个B",              "0.6个B"),
        ("二点三四GB",             "2.34GB"),
        ("十四秒",                 "14秒"),
        ("他喜欢音乐，更乐于助人", "他喜歡音樂,更樂於助人"),
    ]
    print("=== 归一化自检 ===")
    allok = True
    for a, b in tests:
        na, nb = norm(a), norm(b)
        ok = na == nb
        allok &= ok
        print("  %-16s → %-22s | %-20s → %-22s %s" % (a[:16], na, b[:20], nb, "✓" if ok else "✗"))
    print("  自检: %s\n" % ("全过" if allok else "**仍有不一致，结果需谨慎读**"))

    d = json.load(open(INP, encoding="utf-8"))
    rs = d["results"]
    for r in rs:
        r["cer_v3_pct"] = cer(r["ref_text"], r["asr_text"])
        r["cer_v3_norm_ref"] = norm(r["ref_text"])
        r["cer_v3_norm_hyp"] = norm(r["asr_text"])

    ok = [r for r in rs if r.get("asr_ok")]
    print("=== 按引擎（v3）===")
    print("  %-22s %3s %8s %8s %8s %8s %6s" % ("引擎","n","v3中位","v2中位","v1中位","v3最大","全对"))
    eng = {}
    for r in ok: eng.setdefault(r["engine"], []).append(r)
    for e, xs in sorted(eng.items(), key=lambda kv: statistics.median(x["cer_v3_pct"] for x in kv[1])):
        v3 = [x["cer_v3_pct"] for x in xs]
        v2 = [x.get("cer_v2_pct", -1) for x in xs]
        v1 = [x.get("cer_pct",    -1) for x in xs]
        print("  %-22s %3d %7.2f%% %7.2f%% %7.2f%% %7.2f%% %3d/%d"
              % (e[:22], len(v3), statistics.median(v3), statistics.median(v2),
                 statistics.median(v1), max(v3), sum(1 for v in v3 if v == 0.0), len(v3)))

    print("\n=== 按题组 ===")
    grp = {}
    for r in ok: grp.setdefault(r.get("group") or "?", []).append((r["cer_v3_pct"], r.get("cer_pct", -1)))
    for g, p in sorted(grp.items()):
        v3 = [x[0] for x in p]; v1 = [x[1] for x in p]
        print("  %-14s n=%-3d v3中位 %6.2f%%  v1中位 %6.2f%%  Δ %+6.2fpp"
              % (g[:14], len(p), statistics.median(v3), statistics.median(v1),
                 statistics.median(v3) - statistics.median(v1)))

    print("\n=== v3 下仍最差的 6 条 ===")
    for w in sorted(ok, key=lambda x: -x["cer_v3_pct"])[:6]:
        print("  %-22s %-5s v3=%6.2f%%" % (w["engine"][:22], w["qid"], w["cer_v3_pct"]))
        print("     题归一: %s" % w["cer_v3_norm_ref"][:50])
        print("     识归一: %s" % w["cer_v3_norm_hyp"][:50])

    d["norm_version"] = "v3-繁简归一+小数点保护"
    d["norm_selfcheck_pass"] = allok
    tmp = OUTP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, OUTP)
    print("\n落盘: %s" % OUTP)

if __name__ == "__main__":
    main()
