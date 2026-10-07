# ep04 扩测阶段 2 设计补充:ONNX/DML 路线改走「本地自导出」

> 状态:待评审(流程:dsh 优先)｜日期:2026-10-06
> 触发:HF 下载路线全线失效,实测数据见 §1

## 1. 为什么改路线(实测,非推演)

原设计(§4 路线 B)写「下 HF 现成 ONNX 包」。执行前实测:

| 探测 | 结果 |
|---|---|
| `huggingface.co/api/models/*` 直连 | **000**(连不上) |
| `hf-mirror.com` 直连/跟随 308 | **000 / 401** |
| 走 Clash(127.0.0.1:7897)→ HF API | **401**(网络通,但 HF 已强制登录,无 token) |
| HF `resolve/*` 直链(不走 API,走代理) | **401** |
| ModelScope API | **200**(通,但未检索到可用的 SD1.5 ONNX 包) |
| ModelScope dolphin 搜索接口 | 404(接口不存在) |

结论:**下载现成 ONNX 不可行**(不是网络问题,是 HF 强制鉴权,本机无 HF token)。
这正是 dsh 预检项 O2 要求「先下模型再写代码」的价值 —— 若按原计划先写代码再下载,会卡在最后一步。

## 2. 新路线:本地单文件 → 自导出 ONNX

**可行性已实测**(非假设):

```
StableDiffusionPipeline.from_single_file(
    'D:/models/txt2img/v1-5-pruned-emaonly.safetensors',
    local_files_only=True)   → LOADED ok, scheduler=PNDMScheduler
```

即:本地 4.27GB 单文件可直接转成 diffusers 管线,**零下载**。

### 步骤
1. 独立 venv `D:/ep04/onnx/venv`(**不复用 ComfyUI venv**:阶段 2 装 `onnxruntime-directml`,
   与 `onnxruntime` 同包名互斥,且 ComfyUI venv 已被阶段 1 数据背书,不可再动 —— dsh W1/DP-03)
2. 装 `torch==2.14.1+cpu`(钉 DP-02)+ `diffusers` + `onnx` + `onnxruntime-directml==1.24.4`
   (预检实测最新版,`requires_python>=3.11`,本机 3.11.16 满足)
3. 导出三个子模块:`text_encoder` / `unet` / `vae`(fp32 先行)
4. `onnxruntime-directml` 提供 `DmlExecutionProvider`,跑与阶段 1 完全相同的 6 格 × 3 轮

### 口径对齐(与阶段 1、已发布三方案)
- 同 prompt(2 句)、同 seed(42/43/44)、同 512×512、同 20 步、同 cfg 7.0、同断网
- 但 **scheduler 不同**:diffusers 管线默认 `PNDMScheduler`,而 sd.cpp/diffusers 已发布数据
  用的是 `euler + normal`(bench4 口径)→ **必须在导出时显式换成 `EulerDiscreteScheduler`**,
  否则第五格与前四格不可比(DP-08/DP-11)。这条已列入导出脚本的断言。
- 「耗时」口径:冷启动含模型加载,与阶段 1 `timing_scope=cold_total_incl_load` 一致

## 3. 风险与失败预案(dsh C9/判据 4)

| 风险 | 预案 |
|---|---|
| `onnx`/`optimum` 装不上(网络) | 装包失败即记「卡在哪一行」,阶段 2 如实报失败,不写「应该能跑」 |
| 导出的 ONNX 在 DML 上崩(TDR/设备丢失) | dsh G1:降级顺序 fp16 → fp32 → 如实记,**不回退 torch-directml** |
| **静默回退 CPU**(dsh G2 最危险) | 跑前断言 `DmlExecutionProvider` 在 `get_available_providers()`;跑后用 profiling 统计 CPU 节点数,回退显著则该行**不得**标核显 |
| 导出耗时长 | 时间盒:导出 >30min 停并记录(C9) |
| 内存口径不可比(dsh G5/C14) | 主表加「是否计入共享显存」列;DML 行标注「GPU 侧分配未计入」,另用 PDH 计数器 `\GPU Adapter Memory(*)\Shared Usage` 单列 |

## 4. 判据(沿用 REVIEW-dsh.md §6 的 DP-01~DP-27)

阶段 2 额外必保:
- **DP-05/06/07**:每行记 `providers` 实测 + 回退节点数 + 「实测落点」列
- **DP-19 锚点**:同天复测已发布 CPU 基准行,漂移 >5% 则表头标漂移区间
- **DP-12**:导出前冻结 `bench4-progress.json`(阶段 1 已建,直接复用同一冻结副本)

## 5. 排期

导出 60–90 分钟、建 venv 30 分钟、跑测 60 分钟、证据整理 60 分钟 → 约 4 小时。
**建议仍在阶段 1 全绿之后再开工**(两阶段独立交付,阶段 1 成果不被阶段 2 拖住)。

## 6. 请评审

1. 本地自导出这条路线,有没有我没想到的硬伤?(fp32 导出体积、DML 对 ops 的支持面)
2. scheduler 必须换成 `euler` 才可比 —— 这个判断对吗?还是应该在表注里声明「第五格 scheduler 不同」而不换?
3. 「静默回退 CPU」的门禁,profiling 节点数阈值怎么定才不武断?
4. PDH 计数器读共享显存,在本机(Radeon Vega 8)上可行吗?有没有更稳的替代?
