"""EXTRACTION_CONTRACT v2 · 格式解析（白名单剥结构记号 → 纯文本）"""
import re
_ENGINE_TAG = re.compile(r"<\|[^|]*\|>")                 # <|Text|> <|25|>
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")               # <p> </p> <h1>
_MD_HEAD = re.compile(r"^#{1,6}\s+", re.M)               # 行首标题
_MD_EMPH = re.compile(r"(\*\*|__|~~|`)(.+?)\1")          # 成对强调
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}[-:|\s]*$", re.M)  # |---| 行
_PIPE = re.compile(r"\|")

def extract(text: str) -> str:
    t = text
    t = _ENGINE_TAG.sub("", t)
    t = _HTML_TAG.sub("", t)
    t = _MD_TABLE_SEP.sub("", t)
    t = _MD_HEAD.sub("", t)
    t = _MD_EMPH.sub(r"\2", t)
    t = _PIPE.sub(" ", t)                                  # 表格竖线→空格
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()
