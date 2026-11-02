# -*- coding: utf-8 -*-
"""重建被覆盖的第一轮文档级验证章节（Kokoro / CustomVoice 判定）
事实来源：deleg_09f1cdf1 的完成回报（已核实的三分类结论）+ 证据文件 README。"""
import pathlib, shutil, time

REP = pathlib.Path(r"C:/Users/Frank/AppData/Local/hermes/workspace/articles/bench/声音克隆-模型能力验证.md")
if not REP.exists():
    raise SystemExit("报告不存在")

t = REP.read_text(encoding="utf-8", errors="replace")
if "Kokoro" in t:
    print("Kokoro 判定已在位，无需重建")
    raise SystemExit

# 覆盖前备份
bak = REP.with_suffix(".md.bak-restore")
if not bak.exists():
    shutil.copy2(REP, bak)
    print("备份: %s (%.1f KB)" % (bak.name, bak.stat().st_size / 1024))

CHAPTER = """## 文档级验证（第一轮 2026-10-27，本章于同日被覆盖写丢失后按原结论重建）

> **重建说明**：本章原由第一轮任务写入（159 行 / 11.7 KB），第二、三轮以**覆盖写**而非追加的方式落盘，导致本章丢失。以下三分类结论与证据均来自第一轮完成回报，证据文件仍在本机。重建人：主会话。

### 证据文件（仍在本机，可复核）

- `D:/models/test_tmp/README.md`
- `D:/models/test_tmp2/README.md`

### 三分类结论

| 模型 | 许可 | 体积 | 零样本克隆 | 判定 |
|---|---|---|---|---|
| `hexgrad/Kokoro-82M` | `apache-2.0` | 1.23 GiB | **否** | ❌ **出局** |
| `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | `apache-2.0` | 2.32 GiB | **否** | ❌ **出局** |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `apache-2.0` | 4.30 GiB | **否** | ❌ **出局** |
| `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | `apache-2.0` | 约 2.3 GiB | **是** | ✅ 进候选（后经真跑确认） |
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | `apache-2.0` | 约 4.3 GiB | **是** | ✅ 进候选（未实跑） |

### 逐条依据（原文级，非转述）

**1. `Kokoro-82M` 不能零样本克隆**
- `VOICES.md` 确认只有 **54 个固定说话人**（`voice='af_heart'` 等），**接口无 `ref_audio`**
- README 里的 `clone` 一词仅出现在**反向说明**中（原文意为"训练数据未用克隆音频"），**是关键词陷阱，不构成能力证据**
- 第一轮时合成部分**未实测**（已装 `kokoro`，未完成权重下载与生成）

**2. `Qwen3-TTS CustomVoice` 不是克隆**
- `README.md` 明确 `CustomVoice` 只支持 **9 个固定音色**（Vivian / Serena / Uncle_Fu 等）+ **指令控制情绪与语气**，**无 `ref_audio`**
- **真正的零样本克隆在 `Base` 模型**：`generate_voice_clone(ref_audio, ref_text)`，需 **3 秒参考音频**
- 名称易被误解为克隆 —— 本条是选型阶段最重要的纠偏
- 第一轮时合成部分**未实测**

### 第一轮记录的坑（沿用）

1. **Kokoro 的 `clone` 是关键词陷阱** —— 必须看接口有没有 `ref_audio`，不能看词
2. **`CustomVoice` 名称会误导** —— 要按变体（Base / CustomVoice）分辨能力
3. **HF 下载需同时设代理 + `HF_HUB_DISABLE_XET=1`**（Xet 协议会挡下载）
4. **原生 Python 只认 `D:/` `C:/` 路径**，不认 `/d/` `/c/`

### 后续实测对本章的修正（见下章）

第二轮曾误报「2.3 GB 权重未完成下载」，第三轮**逐字节核实为误报**：13 个文件 2399.55 MB = HF 官方值，**缺 0.00 MB**。最终以第三轮「实测级验证（真跑）」为准。

---

"""

# 插到报告最前面（在第一个 ## 之前）
i = t.find("## 实测级验证")
if i < 0:
    i = 0
t2 = t[:i] + CHAPTER + t[i:]
REP.write_text(t2, encoding="utf-8")

v = REP.read_text(encoding="utf-8", errors="replace")
print("\n重建后: %d 行 / %.2f KB" % (len(v.split("\n")), len(v.encode()) / 1024))
print("Kokoro      : %d 次" % v.count("Kokoro"))
print("CustomVoice : %d 次" % v.count("CustomVoice"))
print("54 个固定   : %d 次" % v.count("54 个"))
print("VOICES.md   : %d 次" % v.count("VOICES.md"))
print("真跑章在位  :", "实测级验证（真跑）" in v)
print("音频证据在位:", "qwen3_0_6b_clone" in v)
print("章节数      :", v.count("\n## "))
