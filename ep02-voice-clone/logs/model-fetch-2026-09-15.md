# 模型下载：两个来源的体积对照（2026-09-15 实测）

## 一、为什么会有两个体积

同一个模型（`FunAudioLLM/Fun-CosyVoice3-0.5B-2512`）在两个源上都在，但**下下来的文件不一样**：

| 来源 | 下的体积 | 下的文件 |
|---|---|---|
| HuggingFace / hf-mirror | **5.05 GB** | 只下必需文件 |
| ModelScope | **9.08 GB**（40 个文件） | 整仓库 |

## 二、ModelScope 多下的文件（逐个 du 实测）

| 文件 | 大小 | 说明 |
|---|---|---|
| `llm.rl.pt` | 1.9 GB | RL 训练权重（推理用不到 `llm.pt` 即可） |
| `flow.decoder.estimator.fp32.onnx` | 1.3 GB | onnx 版（本包走 PyTorch 路径） |
| `model.safetensors` | 943 MB | safetensors 格式 |
| `speech_tokenizer_v3.batch.onnx` | 925 MB | batch 版 onnx |

必需文件（两源都有）：`llm.pt` 1.9G、`flow.pt` 1.3G、`speech_tokenizer_v3.onnx` 925M、`hift.pt` 80M。

## 三、ModelScope 下载实测

```
DOWNLOAD_OK: ...\tools\CosyVoice\pretrained_models\Fun-CosyVoice3-0.5B
耗时 829 秒（13.8 分钟）｜ 目录体积 9.08 GB ｜ 文件 40 个
峰值速率 2.83 GB/s（flow.pt 段）
```

## 四、本机网络实测（为什么最后走 ModelScope）

| 目标 | 结果 |
|---|---|
| huggingface.co 直连 | 🔴 SSL 失败 |
| hf-mirror.com | 🔴 连接超时（DNS 能解析到 160.16.86.14） |
| Clash 127.0.0.1:7897 | 🔴 端口在监听，但代理不通（google/github 走它都是 000） |
| ModelScope | ✅ 通，2.8 GB/s |
| 百度 / gitee | ✅ 200 |

## 五、对读者的意义

**国内网络下大概率只能走 ModelScope → 实际要下约 12G（模型 9.1G + 环境 3G）。**
文章里按「7–12G」给区间，就是覆盖这两种情形。
