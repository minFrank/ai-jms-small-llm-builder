# ep04 · 一键包 bat 的正确落地方式（教训：write_file 产出 LF，会被 cmd 拆行）
# 必须：GBK 编码（中文 Windows cmd 默认 OEM=936）+ CRLF 换行（LF 会把 echo 中文行拆碎）
import os, shutil, sys

SRC = os.path.join(os.path.dirname(__file__), "bat_src")
DST_KIT = r"D:\models\txt2img\kit"
TOOLS = os.path.dirname(os.path.abspath(__file__))

names = ["双击下载模型.bat", "双击生成.bat"]
if not os.path.isdir(SRC):
    print("缺少 bat_src 目录", file=sys.stderr)
    sys.exit(2)

for n in names:
    p = os.path.join(SRC, n)
    raw = open(p, "rb").read().decode("utf-8")
    crlf = raw.replace("\r\n", "\n").replace("\n", "\r\n")
    data = crlf.encode("gbk")
    for dst_dir in (TOOLS, DST_KIT):
        os.makedirs(dst_dir, exist_ok=True)
        open(os.path.join(dst_dir, n), "wb").write(data)
    # 危险尾字节扫描（GBK 第二字节若为 \|&<>"^( ) 会被 cmd 误切）
    DANG = {0x5C, 0x7C, 0x26, 0x3C, 0x3E, 0x22, 0x5E, 0x28, 0x29}
    bad, i = 0, 0
    while i < len(data):
        b = data[i]
        if 0x81 <= b <= 0xFE and i + 1 < len(data):
            if data[i + 1] in DANG:
                bad += 1
            i += 2
        else:
            i += 1
    has_crlf = b"\r\n" in data
    print(f"{n}: {len(data)}B GBK CRLF={has_crlf} 危险尾字节={bad}")
