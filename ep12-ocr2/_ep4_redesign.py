# -*- coding: utf-8 -*-
"""ep4 文生图稿：修「第六节」错引 + 结尾加问题 + 结构校验"""
import pathlib, re

p = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/series/local-ai/local-ai-04-txt2img.md")
t = p.read_text(encoding="utf-8", errors="replace")
han = lambda s: len(re.findall(r"[一-鿿]", s))

# --- 修两处指向不存在的第六节（既有 bug）---
for old, new in [
    ("条款出处见第六节", "条款出处见文末「参考资料」"),
    ("下载那步的直连实测在第六节", "下载那步的直连实测见文末「参考资料」"),
]:
    c = t.count(old)
    if c:
        t = t.replace(old, new)
    print("  修 %r -> %d 处" % (old[:18], c))

# --- D：结尾加具体问题（源码图之后、AI 声明之前）---
anchor = "> 本文实测部分均由DSH+Hermes两个智能体协同完成，整体内容经笔者编撰与校准后发布。"
assert t.count(anchor) == 1, "D anchor hit %d" % t.count(anchor)
add = ("**最后想听你的：** 你手上是核显还是纯 CPU？打算用它画什么 —— 头像、海报，"
       "还是给孩子做配图？评论区说一声，我按需求补测对应分辨率和题材。\n\n---\n\n")
if "最后想听你的" not in t:
    t = t.replace(anchor, add + anchor)
    print("  + 结尾问题已加")
else:
    print("  结尾问题已存在，跳过")

p.write_text(t, encoding="utf-8")

# --- 校验 ---
v = p.read_text(encoding="utf-8", errors="replace")
print("\n=== 校验 ===")
print("  第六节残留: %d (改前 2)" % v.count("第六节"))
print("  结尾问题在:", "最后想听你的" in v)
i_term = v.find("### 术语"); i_pri = v.find("### 技术原理"); i_two = v.find("## 二、")
print("  术语表位置(在第一节末):", i_pri < i_term < i_two)
print("  全文汉字: %d (改前 5065, %+d)" % (han(v), han(v) - 5065))
print("  屏数: %.1f" % (han(v) / 350.0))
print("  div %d/%d  p %d/%d  tr %d/%d  引图 %d 处" % (
    len(re.findall(r"<div", v)), len(re.findall(r"</div", v)),
    len(re.findall(r"<p[ >]", v)), len(re.findall(r"</p>", v)),
    len(re.findall(r"<tr[ >]", v)), len(re.findall(r"</tr>", v)),
    len(re.findall(r"!\[[^\]]*\]\(", v))))
print("  末行:", repr(v.rstrip().split("\n")[-1][:70]))
print("  交叉引用:")
for k in ["第一节", "第二节", "第三节", "第四节", "第五节", "第六节"]:
    hits = [i for i, l in enumerate(v.split("\n"), 1) if k in l]
    print("    %-6s %d 次 %s" % (k, len(hits), hits[:6]))
