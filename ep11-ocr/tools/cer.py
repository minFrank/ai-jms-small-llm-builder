# -*- coding: utf-8 -*-
"""CER 口径（归一化 v1）。中文主口径：空格不敏感。

归一化顺序（norm_version = "v1"）：
  1) unicodedata.normalize("NFKC")   全角→半角、兼容字符折叠
  2) 去所有空白字符（主口径）；空格敏感口径保留单空格折叠（norm_ws）
  3) 去中英文标点（PUNCT 集合，逐字符删除）
  4) 英文小写化
CER = 编辑距离 / len(归一化后 GT)；分母 0 记 None（GT 空），单列不进中位数。
"""
import unicodedata

PUNCT = set("，。、；：？！“”‘’（）《》【】—…·　,.;:?!\"'()<>[]{}-_~/\\|@#$%^&*+=`~")
PUNCT |= set("　")


def _strip_punct(s):
    return "".join(ch for ch in s if ch not in PUNCT
                   and unicodedata.category(ch)[0] not in ("P", "S"))


def normalize(s, drop_ws=True):
    s = unicodedata.normalize("NFKC", s or "")
    s = _strip_punct(s)
    s = s.lower()
    if drop_ws:
        s = "".join(ch for ch in s if not ch.isspace())
    else:
        s = " ".join(s.split())
    return s


def lev(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref, hyp, drop_ws=True):
    r = normalize(ref, drop_ws)
    h = normalize(hyp, drop_ws)
    if not r:
        return None
    return lev(r, h) / float(len(r))


NORM_VERSION = "v1-nfkc-strip-punct-lower-%s" % ("nows" if True else "ws")


def selftest():
    """金标准对：锁归一化与 CER 口径。"""
    cases = [
        # (ref, hyp, drop_ws, expect_cer)
        ("增值税电子普通发票", "增值税电子普通发票", True, 0.0),
        ("增值税电子普通发票", "增值税电子普通发票", False, 0.0),
        ("金额：￥1,234.56", "金额:1,234.56", True, 0.0),   # 全半角标点差异不计
        ("金额：1,234.56", "金额 1 234 56", True, 0.0),     # 空格差异不计（主口径）
        ("金额：1,234.56", "金额 1 234 56", False, 0.375),  # 空格敏感口径会算错
        ("ABC", "ABC", True, 0.0),
        ("ABC", "abc", True, 0.0),
        ("发票号码 25893417", "发票号码 25893471", True, 2 / 12.0),
        ("", "anything", True, None),                       # GT 空 -> None
    ]
    ok = True
    for ref, hyp, dw, exp in cases:
        got = cer(ref, hyp, dw)
        if exp is None:
            good = got is None
        else:
            good = got is not None and abs(got - exp) < 1e-9
        if not good:
            ok = False
            print("SELFTEST FAIL ref=%r hyp=%r drop_ws=%s got=%s expect=%s"
                  % (ref, hyp, dw, got, exp))
    # 编辑距离基本性质
    assert lev("kitten", "sitting") == 3
    assert lev("", "abc") == 3
    print("CER selftest: %s" % ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
