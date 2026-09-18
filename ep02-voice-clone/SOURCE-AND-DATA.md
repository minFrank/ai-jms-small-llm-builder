# 第 02 期 · 源码与过程数据索引

> 这篇文章里出现的每个数字、每段报错、每张图，都能在下面找到出处。
> 路径相对 `ep02-voice-clone/`。

## 一、源码（真正在跑的程序只有两个文件）

| 文件 | 行数 | 职责 |
|---|---|---|
| `tools/tts.py` | 299 | 主程序：加载模型 → 按句切分 → 逐句合成 → ffmpeg 拼接 → 输出 wav/mp3 |
| `tools/check.py` | 83 | 环境自检：Python 版本、依赖、模型文件、显存/内存 |
| `install.bat` / `一键安装.bat` | 191 / 190 | 建 venv、装依赖、下模型（首次 7–12G，看下载源） |
| `start.bat` / `一键生成.bat` | 99 / 94 | 找 Python → 调 `tts.py` → 报错时给中文提示 |
| `bench-long/bench_long.py` | 153 | 长文本实测脚本（走同一条 tts.py 路径，采样耗时/内存） |

## 二、过程数据（文章数字 → 文件）

| 文章里的数字 | 出处文件 | 里面是什么 |
|---|---|---|
| 167 / 184 / 175 / 192 秒 | `logs/run-2026-09-13.md` | 四次正常成绩的完整命令与输出 |
| 232 / 245 秒（机器忙时） | `logs/run-2026-09-13.md` | 两次被污染的补测，标注不计入 |
| 382 字 → 11.5 分钟、5.89 倍实时 | `logs/run-2026-09-13.md` | 长文本（上一期素材）的合成记录 |
| 内存净 6.0–6.5G、峰值 8G 出头 | `logs/runtime-memory-disk.txt` | 采样方法 + 原始采样点 + 净值换算 |
| 磁盘 6.94G（HF 源：模型 5.05G + 环境 1.88G）／**对外口径 7–12G（看下载源）** | `logs/runtime-memory-disk.txt` | 目录递归实测；文末有 2026-09-15 的口径更新说明 |
| 坑一/坑二/坑三的报错原文 | `logs/runtime-errors.txt` | Python traceback / cmd 报错逐字 |
| CosyVoice 3 = Apache-2.0 | `logs/license-check.txt` | GitHub LICENSE + HF 两个模型页 |
| 15 / 30 分钟两组新数据 | `bench-long/result-15min.md` / `.json` | 长文本实测原始输出（逐块耗时、内存峰值） |

## 三、自己复现

```
# 1) 安装（首次 7–12G，需联网；看下载源）
双击 install.bat

# 2) 放两样东西：我的录音.wav + 我的录音说的是什么.txt

# 3) 生成
双击 start.bat
```

## 四、2026-09-15 重装复测（一键包端到端验证）

**背景**：为验证「一键包从零能不能装出来、装完能不能真出音频」，在一台干净目录里重跑了
`一键安装.bat` → `一键生成.bat` 全流程。过程中抓到 7 个真问题并逐个修复（见下方表格）。

| 文章里的数字 | 出处文件 | 里面是什么 |
|---|---|---|
| 运行环境 `.venv` 2.92 GB | `logs/run-2026-09-15-reinstall.log` | `[1] 检查落地物` 段，按目录递归实测 |
| 模型 9.08 GB / 40 个文件 | `logs/run-2026-09-15-reinstall.log` | 同上；`[2]` 段含 torch 2.3.1+cpu / numpy 1.26.4 版本确认 |
| 复测 RTF 8.95–10.58 倍（两次） | `logs/run-2026-09-15-reinstall.log` | `[3] 端到端` 段逐段 `yield speech len ..., rtf ...` 原始输出 |
| 复测总耗时 4.9 / 5.7 分钟 | `logs/run-2026-09-15-reinstall.log` | 同上，`退出码 0，耗时 N 分钟` |
| 下载来源与体积差异：HF 5.05G / ModelScope 9.1G | `logs/model-fetch-2026-09-15.md` | 两源文件清单对比：MS 多出 `llm.rl.pt` 1.9G、`flow.decoder.estimator.fp32.onnx` 1.3G、`model.safetensors` 943M、`speech_tokenizer_v3.batch.onnx` 925M |
| ModelScope 下载 9.08G / 13.8 分钟 / 2.8GB/s | `logs/model-fetch-2026-09-15.md` | 下载日志实测 |

### 7 个真问题（修复记录）

| # | 问题 | 现象 | 修法 |
|---|---|---|---|
| 1 | Python 版本闸门缺失 | 3.14 上 `torch==2.3.1` 不存在（只有 2.9+）、numpy 元数据生成失败 | 只接受 3.10/3.11/3.12 + 报错给原因与下载页 |
| 2 | 子模块不走镜像 | `third_party/Matcha-TTS` 克隆 `curl 56` / `early EOF`，无限重试 | `insteadOf` 把 github.com 整体重定向 |
| 3 | 依赖失败被掩盖 | 最后一个小包装成功把 errorlevel 清零，脚本以为依赖 OK（实际没 torch） | 每个 pip 单独检查 + `DEPS_OK` 标志位 |
| 4 | `pkg_resources` 缺失 | `openai-whisper` 构建失败；**装最新 setuptools 无效**（81+ 已移除） | `setuptools<81` + `--no-build-isolation` |
| 5 | Xet 协议挡模型下载 | 下到 75% 崩（`us.aws.cdn.hf.co`），hf-mirror 不代理该链路 | `HF_HUB_DISABLE_XET=1` |
| 6 | 国外 extra-index 源拖慢 | pip 对每包重试 5 次，日志 600+ 行全在干等 | `--retries 1 --timeout 15` |
| 7 | 重跑重复下 5G | 模型已存在仍重新下载 | 检查 `llm.pt` 存在即跳过 |

**另外**：本机实测 HuggingFace 全链路不通（直连 SSL 失败 + hf-mirror 超时 + 代理端口失效），
模型改从 **ModelScope** 下（同一模型、id 一致）—— 已作为 bat 的第三条兜底路径。

### 复测与原数据的差异（如实记录）

| 项 | 原四次（2026-09-13） | 复测两次（2026-09-15） |
|---|---|---|
| RTF | 5.6–6.8 倍 | 8.95–10.58 倍 |
| 117 字耗时 | 167–192 秒 | 约 4.9–5.7 分钟 |
| 环境 | 原装 | 重建（`torch 2.3.1+cpu`） |

差异来源**未做对照实验**，只能说与依赖版本有关；两次复测期间未开其他重活（非并发干扰）。

## 五、审核记录

- `review/README.md` —— 八轮审核逐轮判定与改动清单
- `review/ACCEPTANCE-CRITERIA.md` —— 发布验收标准（A 类 11 项）
- `review/problems-ledger.md` —— 36 条问题、11 类归并

## 六、测试素材来源

| 素材 | 用途 | 来源 |
|---|---|---|
| `story.txt`（幼儿园家长会通知，117 字） | 短文本实测的合成输入 | 本项目自备；泛化文本，不含任何真实幼儿园/人名 |
| `bench-long/story-15min.txt` / `story-30min.txt`（童话《小刺猬捡到一颗星星》，4201 / 8402 字） | 长文本实测的合成输入（15 / 30 分钟档） | 本项目自备（非转载），仅用于长度压测 |
| `我的录音说的是什么.txt` | 告诉脚本「录音里念的是哪句话」 | 品牌口号 |
| `我的录音.wav` | 音色克隆的样本 | **不随包提供**，由使用者自己录（20–30 秒） |

> 长文本素材未随包改动，`result-15min.md` 里「4201 字」的口径与文件实际字数一致。
