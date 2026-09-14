"""第 02 期 · 改稿机械自检

目的:AI 审查适合判断"好不好读",但机械问题(数字不一致、黑话漏网、重复句、
引用了不存在的东西)应该用脚本一次扫干净 —— 不该轮到 AI 每轮再报一遍。

用法:python selfcheck_article.py <文章.md>
"""
import re
import sys
from pathlib import Path

TERMS = ["量化", "GGUF", "t/s", "token", "RTF", "推理", "上下文", "参数", "权重", "LoRA",
         "采样平台", "基线", "口径", "生成倍率", "倍实时", "一键出片", "端到端"]
BLACKLIST_PHRASES = ["一键出片", "一键搞定", "秒出", "神器", "颠覆", "封神", "逆天", "必看", "无敌"]


def check(path: Path) -> int:
    md = path.read_text(encoding="utf-8")
    fm_raw = md.split("---")[1]
    fm = dict(re.findall(r"^(\w+):\s*(.+)$", fm_raw, re.M))
    body = md.split("---", 2)[-1]
    lines = body.splitlines()
    problems = []

    # ---------- ① 章节编号连续性 ----------
    nums = []
    for ln in lines:
        m = re.match(r"^## ([一二三四五六七八九十]+)、", ln)
        if m:
            nums.append(m.group(1))
    order = "一二三四五六七八九十"
    idx = [order.index(n) for n in nums if n in order]
    for i in range(1, len(idx)):
        if idx[i] != idx[i - 1] + 1:
            problems.append(f"[章节编号] 从「{order[idx[i-1]]}」跳到「{order[idx[i]]}」—— 中间那节可能被删了")
    print(f"① 章节编号：{'、'.join(nums)}")
    if not nums:
        problems.append("[章节编号] 一个「## X、」都没找到")

    # ---------- ② 前 5 段术语闸门 ----------
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    head5 = " ".join(paragraphs[:5])
    hit_terms = [t for t in TERMS if t in head5]
    print(f"② 前 5 段术语：{hit_terms if hit_terms else '无'}")
    if hit_terms:
        problems.append(f"[术语闸门] 前 5 段出现术语：{hit_terms}")

    # ---------- ③ 全文黑话/夸大词 ----------
    hits = [p for p in BLACKLIST_PHRASES if p in md]
    print(f"③ 黑话/夸大词：{hits if hits else '无'}")
    if hits:
        problems.append(f"[用语] 出现不该有的词：{hits}")
    # 全文技术词(应只出现在技术节/附录)
    late = [t for t in TERMS if t in md]
    print(f"   全文出现的术语(应只在技术节/附录)：{late if late else '无'}")

    # ---------- ④ 数字三处一致：digest / 正文表格 / 正文句子 ----------
    def nums_in(text):
        return set(re.findall(r"\d+(?:\.\d+)?", text))
    digest_nums = nums_in(fm.get("digest", ""))
    body_nums = nums_in(body)
    only_digest = {n for n in digest_nums if n not in body_nums and len(n) >= 2}
    print(f"④ 参数型数字：digest {len(digest_nums)} 个 | 正文 {len(body_nums)} 个")
    if only_digest:
        print(f"   ⚠ digest 里有、正文里找不到的：{sorted(only_digest)[:10]}")
        problems.append(f"[数字] digest 与正文不一致：{sorted(only_digest)[:6]}")

    # 内存/体积/耗时三个关键指标在各处的写法
    key_patterns = {
        "内存(静态占用)": r"6\.\d[–\-—]6\.\dG",
        "内存(峰值)": r"8G 出头|8\.\dG|9G",
        "体积": r"约 7G|7\.1G|6\.94G|5\.05G|1\.88G",
        "耗时区间": r"167[–\-—]192",
        "加载时间": r"9[–\-—]16 秒|9[–\-—]11 秒",
        "速度倍率": r"5\.\d[–\-—]6\.\d 倍|5\.6 倍|差不多 6 分钟",
    }
    print("   关键指标在全文的写法：")
    for name, pat in key_patterns.items():
        found = re.findall(pat, body)
        uniq = sorted(set(found))
        print(f"     {name}: {uniq if uniq else '（未出现）'} × {len(found)}")

    # ---------- ④b 同一指标是否出现互相冲突的写法 ----------
    # 教训:我改稿时把内存峰值从 9G 改成「8G 出头」,但别处的 9G 没清干净,两个值并存。
    conflicts = [
        ("内存峰值", [r"(?<![\d.])9G(?! 出头)", r"8G 出头"], "同一个指标出现了两个不同的值"),
        ("加载时间", [r"9[–\-—]11 秒", r"9[–\-—]16 秒"], "两个区间并存,读者不知看哪个"),
        ("静态内存", [r"6\.2[–\-—]6\.5G", r"6\.0[–\-—]6\.5G"], "两个区间并存"),
        ("体积旧口径", [r"7\.1G"], "还在用旧口径 7.1G(实测是 6.94G)"),
    ]
    for name, pats, why in conflicts:
        present = [p for p in pats if re.search(p, body)]
        if len(present) > 1:
            problems.append(f"[口径冲突] {name}:{why}(命中 {present})")
            print(f"   ⚠ {name}：多个写法并存 → {present}")

    # ---------- ④c 同一事实重复强调(次数异常) ----------
    # 教训:8G 那件事被反复说了三遍,读者以为漏看了什么。
    for kw, limit in [("8G", 6), ("16G", 6), ("不用独立显卡", 3), ("没有独立显卡", 3)]:
        c = body.count(kw)
        if c > limit:
            problems.append(f"[重复] 「{kw}」在正文出现 {c} 次(上限 {limit})—— 同一件事别反复讲")
            print(f"   ⚠ 「{kw}」出现 {c} 次(上限 {limit})")
        else:
            print(f"   · 「{kw}」出现 {c} 次")

    # ---------- ⑤ 重复句 ----------
    sents = []
    for ln in lines:
        if ln.startswith(("|", "#", "*", ">", "```", "!")) or len(ln) < 25:
            continue
        for s in re.split(r"[。！？]", ln):
            s = s.strip()
            if len(s) >= 25:
                sents.append(s)
    seen, dup = {}, []
    for s in sents:
        k = re.sub(r"[，、,0-9]", "", s)[:22]
        if k in seen and k:
            dup.append((seen[k], s))
        else:
            seen[k] = s
    print(f"⑤ 疑似重复句：{len(dup)} 组")
    for a, b in dup[:5]:
        print(f"     · {a[:45]}…  ↔  {b[:45]}…")
    if dup:
        problems.append(f"[重复] {len(dup)} 组疑似重复句")

    # ---------- ⑥ 引用的东西是否存在 ----------
    print("⑥ 引用存在性检查：")
    # "第 X 节" 是否存在
    for m in re.finditer(r"第([一二三四五六七八九十]+)节", body):
        n = m.group(1)
        if not any(re.match(rf"^## {n}、", ln) for ln in lines):
            problems.append(f"[引用] 文中提到「第{n}节」,但没有这个章节")
            print(f"     ✗ 引用了「第{n}节」但该节不存在")
    # 「X 倍」「X 秒」这类被引用的数字是否真的出现过
    for m in re.finditer(r"和「([^」]{1,14})」说的是同一件事", body):
        if m.group(1) not in body.replace(m.group(0), ""):
            problems.append(f"[引用] 说「和「{m.group(1)}」说的是同一件事」,但全文别处没出现过它")
            print(f"     ✗ 引用了不存在的「{m.group(1)}」")
    # 图文件是否存在
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", body):
        p = Path(m.group(1))
        if not p.exists():
            problems.append(f"[图] 图片不存在:{p.name}")
            print(f"     ✗ 图片缺失:{p.name}")
    print("     （上面没有 ✗ 即通过）")

    # ---------- ⑦ frontmatter 基本项 ----------
    for k in ["title", "digest", "brand", "series", "episode"]:
        if k not in fm:
            problems.append(f"[frontmatter] 缺字段 {k}")
    # 引号配对
    for k in ["title", "digest", "scarcity_note"]:
        v = fm.get(k, "")
        if v.count("「") != v.count("」"):
            problems.append(f"[frontmatter] {k} 的「」引号不配对")
    if len(fm.get("title", "")) > 35:
        problems.append("[标题] 超过 35 字")
    print(f"⑦ frontmatter：title {len(fm.get('title',''))} 字 | digest 有 | 引号配对")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if problems:
        print(f"发现 {len(problems)} 个机械问题：")
        for p in problems:
            print("  ⚠ " + p)
        return 1
    print("✅ 机械自检全部通过")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"C:\Users\Frank\AppData\Local\hermes\workspace\articles\series\local-ai\local-ai-02-bedtime-story.md")
    sys.exit(check(target))
