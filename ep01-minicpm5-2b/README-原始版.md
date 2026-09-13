# MiniCPM5-2B 本地实测复刻包

在**没有独立显卡**的 Windows 机器上,把 2.5B 小模型跑起来并测出真实数据的最小工具集。

配套文章:「AI 创意｜9月11日:无显卡跑 2.5B 模型」(公众号 AI 积木师)

## 一、环境要求

| 项 | 最低 | 本文实测环境 |
|---|---|---|
| 操作系统 | Windows 10/11 x64 | Windows 11 |
| 内存 | 8GB(限 4K 上下文) | 28GB |
| 显卡 | **不需要**(纯 CPU) | 无独显 |
| 磁盘 | 4GB(模型 1.56GB + 运行时 20MB) | — |
| 其他 | Python 3.9+(仅在跑并发脚本时需要) | Python 3.11 |

## 二、三步跑起来

```bash
# 1) 下载 llama.cpp 的 Windows CPU 版(约 18MB,免编译)
#    到 https://github.com/ggml-org/llama.cpp/releases 找最新的
#    llama-bXXXXX-bin-win-cpu-x64.zip,解压到一个目录,例如 D:\tools\llama

# 2) 下载模型(选 Q4_K_M 这一档,1.56GB)
#    https://huggingface.co/openbmb/MiniCPM5-2B-GGUF  ->  MiniCPM5-2B-Q4_K_M.gguf
#    放到 D:\models\MiniCPM5-2B-Q4_K_M.gguf

# 3) 跑一句话
D:\tools\llama\llama-completion.exe ^
  -m D:\models\MiniCPM5-2B-Q4_K_M.gguf ^
  -c 4096 -t 8 -n 200 ^
  -p "用一句话解释什么是模型量化。"
```

> **关键提醒**:必须加 `-c 4096`(或更小)。不加的话模型会按自带的 128K 上下文加载,内存直接吃到 7.7GB;限到 4096 后只要 2.5GB。

## 三、实测数据(AMD Ryzen 7 5700G · 8 核 16 线程 · 28GB · 无独显)

| 量化档 | 文件大小 | 提示处理 | 生成速度 | 内存峰值 |
|---|---|---|---|---|
| **Q4_K_M** | 1.45 GiB | **143.8 t/s** | **18.02 t/s** | 2488 MB |
| Q8_0 | 2.49 GiB | 68.2 t/s | 11.67 t/s | 2512 MB |

其他维度:

| 场景 | 结果 |
|---|---|
| 上下文 → 内存 | 默认 128K:7.7GB;限 4096:2.5GB |
| 线程曲线 | 4→15.4 / **8→16.2** / 16→15.8 t/s(**8 最优**) |
| 并发吞吐 | 单路 16.4 → 4 路 **33.6** t/s(8 路另批次约 52 t/s) |
| 长上下文 | 8 千字"大海捞针"命中;读题约 107 t/s(约 25 秒) |
| 资源占用 | CPU 峰值 37%,进程内存峰值 2.7GB |

## 四、脚本用法

```bash
# 基准测试(需要先装好 llama-bench,随 llama.cpp 一起提供)
python bench.py --llama D:\tools\llama --model D:\models\MiniCPM5-2B-Q4_K_M.gguf

# 单次问答(打印输出与性能统计)
python ask.py --llama D:\tools\llama --model D:\models\MiniCPM5-2B-Q4_K_M.gguf "什么是 KV 缓存?"

# 并发测试(起本地服务,同时发 4 路请求)
python serve_concurrent.py --llama D:\tools\llama --model D:\models\MiniCPM5-2B-Q4_K_M.gguf --concurrency 4
```

## 五、两个必须知道的坑(实测踩到)

1. **思维链会"吃掉"答案**:模型习惯先输出大段推演 `…`,默认 200 token 预算常在推演阶段就用完,答案被截断。
   → 输出预算给到 **400 以上**,或明确要求"直接给答案"。
2. **长文摘要有"复读"倾向**:把 5,000 字以上的文章丢给它摘要,它可能照抄原文。
   → 指令里写明"用你自己的话写 3 个要点,不要照抄原文句子",并把预算放大到 **1200 以上**。

## 六、许可

- 模型:MiniCPM5-2B(Apache-2.0,可商用,可封装自己用)
- 推理引擎:llama.cpp(MIT)
- 本复刻包:MIT

## 七、原始日志

`runtime-*.txt`、`quality-*.txt`、`summary-runtime.txt` 是文章里那几张运行截图的**原始输出**(未经修改),可用于逐字核对数据。
