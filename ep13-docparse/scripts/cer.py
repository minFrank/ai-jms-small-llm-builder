"""CER = (S+D+I)/N（EXTRACTION_CONTRACT v1）——Unicode code point 逐字符 Levenshtein"""
def cer(ref: str, hyp: str) -> float:
    ref = ref.strip(); hyp = hyp.strip()
    if not ref: raise ValueError("GT 空（建集时已校验）")
    n, m = len(ref), len(hyp)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ref[i-1] != hyp[j-1]))
        prev = cur
    return prev[m] / n        # S+D+I 全在编辑距离里
