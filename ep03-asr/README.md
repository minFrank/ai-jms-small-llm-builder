# ep03 · 本地语音识别实测（4 个开源模型 × 15 组样本）

纯 CPU 实测：同一台机器、同一批样本、同一套脚本跑完 4 个模型，共 60 条明细。

## 环境

- CPU：AMD Ryzen 7 5700G（8 核 16 线程）· 内存 27.9 GB · **无独显、无 CUDA**、无 Docker
- Windows 11 · Python 3.11 · `sherpa-onnx 1.13.8` · `faster-whisper 1.2.1` · `ffmpeg 9.0.1`
- 模型全部放在数据盘（不占系统盘）：`/d/models/asr/`

## 测了哪 4 个模型（都是开源、可商用/宽松许可）

| 目录 | 来源 | 部署体积 |
|---|---|---|
| `sherpa-onnx-paraformer-zh-2023-09-14` | GitHub releases（k2-fsa/sherpa-onnx，`asr-models` tag） | 243 MB |
| `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17` | 同上（danielding 系列同名发布） | 239 MB |
| `sherpa-onnx-whisper-small` | 同上 | 112 MB（int8 编码器+解码器） |
| `faster-whisper-small` | HuggingFace `Systran/faster-whisper-small` | 464 MB |

下载：`sherpa-onnx` 系走 GitHub releases（`REL=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models`），
faster-whisper 走 `https://huggingface.co/Systran/faster-whisper-small/resolve/main/`。
> 本机实测：`modelscope` 那条路走不通（仓 id 404），HF 与 GitHub releases 走代理（Clash 7897）可下。

## 样本（3 源 × 5 条件 = 15 组）

- 源：A 档 8 秒真人短录音 / B 档 17 秒 / C 档 **10.5 分钟**（**由真人短录音循环拼成，非真实 10 分钟连续讲话**）
- 条件：干净 / 加背景音乐 / 加噪 / 1.5× 变速 / 低音量+混响
- 参考文本：3 段已知原文（`ep03_asr_bench.py` 内的 MAN），CER 用编辑距离逐字比对

## 跑法

```bash
python ep03_asr_bench.py            # 4 模型 × 15 组，输出 results/result.json + 逐组日志
python figs.py                      # 出 4 张证据图（纯 PIL，无需 matplotlib）
```

## 结果摘要（详见 results/result.json）

| 模型 | 部署体积 | 平均倍速 | CER 中位 | CER 最差 |
|---|---|---|---|---|
| Paraformer-zh | 243 MB | 30.8× | **0.35%** | 1.77% |
| SenseVoice-Small | 239 MB | 25.2× | 4.55% | 13.64% |
| faster-whisper small | 486 MB | 5.0× | 9.09% | 18.18% |
| Whisper-small (ONNX) | 112 MB | 11.3× | 27.27% | **96.15%** |
| Zipformer-CTC small int8 | **63 MB** | **45.7×** | 17.29% | 45.45% |
| Zipformer-CTC zh int8 | 367 MB | 29.1× | 18.11% | 45.45% |

> 六模型共 80 条有效明细（两个 zipformer 各 10 组：C 档长音频**跑不了**，见下方边界）。

## 降配复验（限 2 个逻辑核，同 3 个代表样本）

| 模型 | A 档 8 秒 | B 档 17 秒 | C 档 10.5 分钟 | 衰减 |
|---|---|---|---|---|
| Paraformer-zh | 14.0× | 17.6× | **3.1×** | 约 40% |
| SenseVoice-Small | 14.5× | 14.9× | 2.0× | 约 56% |
| faster-whisper small | 1.9× | 3.3× | 3.6× | 约 50% |
| Whisper-small (ONNX) | 2.1× | 1.6× | 24.8×（截断） | 约 70% |
| Zipformer-CTC small int8 | 30.3× | 30.4× | **失败** | — |
| Zipformer-CTC zh int8 | 12.9× | 13.2× | **失败** | — |

结论：**限到 2 核，Paraformer 在 10.5 分钟长音频上仍有 3.1 倍实时、CER 0.4%** —— 「低配电脑能不能用」这句有据了。

**已知边界（如实标注，别当结论外推）**

1. C 档 10.5 分钟是**合成长音频**（短录音循环），不是真实连续讲话；
2. 「带口音」样本**未测**（缺公开带口音测试集）；
3. **Whisper-small (ONNX) 长音频截断已由库自己确认**（原始日志）：
   `offline-recognizer-whisper-impl.h:DecodeStream:99 Only waves less than 30 seconds are supported.
   We process only the first 30 seconds and discard the remaining data` —— 628 秒音频只处理前 30 秒；
4. **两个 Zipformer 是 CTC 解码、未配语言模型**（精度低于带 LM 的模型属预期），且**长音频会崩**：
   `Failed to allocate memory for requested buffer of size 31568306688`（约 31.5 GB）→ 长录音必须先自行切段；
4. CER 口径保守：数字/标点转写差异（「三→3」「AI→a i」）也计入错误。
