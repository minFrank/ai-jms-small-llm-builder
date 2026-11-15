# ep25 · 无显卡声音克隆四跑法实测

对应文章：《CosyVoice3、VoxCPM2、VoiceStudio 无显卡实测：差五倍》（AI 积木师 · local-ai 第 25 期）

## 测了什么

- **机器**：AMD Ryzen 7 5700G（8 核 16 线程）、30 GB 内存、**无独立显卡**，纯 CPU 推理
- **跑法**：CosyVoice3（阿里）、VoxCPM2（面壁）、VoiceStudio 内建、VoiceStudio 子进程
- **参考音频**：同一段 8 秒、16 kHz 的真人录音（作者本人），四个引擎共用
- **题目**：25 条中文题 × 5 组（基准短句、多音字、长句与停顿、数字与英文夹杂、语气与情感），每条 15–69 字
- **规模**：主时段 4 引擎 × 25 题 = 100 格全跑完，另两个时段 51 格只做耗时观测，合计 151 格（138 格成功）

## 结果（主时段中位）

| 跑法 | 成功格 | 单次中位耗时 | 中位 RTF | 字错率中位 |
|---|---|---|---|---|
| CosyVoice3 | 25 / 25 | 58.7 秒 | 7.86 | 1.54% |
| VoxCPM2 | 25 / 25 | 191.2 秒 | 35.25 | 2.33% |
| VoiceStudio 子进程 | 14 / 25 | 280.9 秒 | 45.42 | 0.00%（9/14 零错） |
| VoiceStudio 内建 | 24 / 25 | 293.0 秒 | 39.01 | 0.00%（13/24 零错） |

失败 12 格全落在 VoiceStudio：子进程 11 格（HTTP 500 中止）、内建 1 格（HTTP 503，服务自己 600 秒兜底）。
11 个失败题重跑全部复现失败，3 个成功题对照全部通过。

字错率由语音转文字模型回读比对得出，未做人工听感评价、未做统计检验。

## 目录

```
listen/   3 条试听音频（文章内嵌不了，微信接口不收音频卡片）
  cosyvoice/q14_rep1.wav     最快引擎念长句 17.0s
  omnivoice/q11_rep1.wav     内建模式，字错率 0.00% 17.6s
  voxcpm2/q10_rep1.wav       VoxCPM2 念长句 16.5s
data/
  slot_0015/timing.jsonl     逐格耗时（engine/question/kind/wall_s/audio_s/ok/…）
  slot_0015/asr_cer_v3.json  逐格字错率（v3 口径）
  ep25-中文题库-25条.json     25 道题全文
  ep25-数据汇总.json          汇总数字
scripts/ 跑测（run_slot.py）、字错率（asr_cer_v3.py）、重跑复现（recheck_failed.py）、画图（make_figs*.py）
figs/    文章 6 张配图
```

完整跑测音频 145 个（57.8 MB）未入库，需要可从对应期的实测包取。

## 复现

```bash
python scripts/run_slot.py      # 主时段 100 格
python scripts/asr_cer_v3.py    # 字错率回读
python scripts/recheck_failed.py # 失败题重跑复现
```

## 许可

- 本目录脚本：MIT（见仓库根 [LICENSE](LICENSE)）
- 模型权重：CosyVoice3 / VoxCPM2 为 Apache-2.0；VoiceStudio 为 AGPL-3.0 应用 + Apache-2.0 模型（内置 OmniVoice）
- 试听音频的音色为作者本人录音，用于展示声音克隆效果
