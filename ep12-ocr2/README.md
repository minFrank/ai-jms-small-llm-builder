# ep12-ocr2 — 续测开源 OCR 六套引擎（同机实测代码与数据）

微信公众号文章《RapidOCRLite、SimdPaddleOCR、PaddleOCR、EasyOCR、GLM-OCR 六套开源 OCR 引擎同机实测速通》的实测代码与逐格原始数据。

## 目录结构

| 路径 | 内容 |
|---|---|
| `engine_base_ep12.py` | 六个引擎的测法定义（load / infer / 计时口径 / 设置快照） |
| `cell_runner.py` | 单格测量 runner：warmup、计时、内存峰值采样（psutil 进程树，0.2s 间隔） |
| `cells/` | **208 条逐格原始记录**（每格一个 JSON：中位耗时、字错率、内存、设置快照） |
| `_agg_v3.py` / `_agg_v3.json` | 总榜聚合（24 张口径，排除带 † 的两张） |
| `_figs_v2.py` / `_figs_v3.py` | 文章图表生成（fig1–fig7） |
| `simd-test/SimdBench/Program.cs` | SimdPaddleOCR 子进程测法（default / controlled 两档 profile 定义） |
| `probe_csharp/` | SimdPaddleOCR 检测参数对齐探测记录 |
| `report_assets/` | 26 张测试样本原图 |
| `_shots/` | 各引擎官网/仓库截图 |
| `samples_provenance.json` | 样本来源清单 |

## 已知计时口径差异（读者核数据前必读）

**SimdPaddleOCR 走子进程**（.NET 程序集，Python 侧只能起子进程），每次 `infer()` 都包含：启动 .NET 进程 + 加载模型 + 推理 + 结果传回。**每次开销约 0.9 秒，占单页耗时的三分之一，不是推理本身。**

其余引擎（RapidOCRLite / PaddleOCR / EasyOCR）模型在 `load()` 阶段预加载，`infer()` 计时窗口里只有推理；GLM-OCR 与 LightOnOCR-3 走 HTTP 调常驻服务。

**逐格核对方法**：

```json
// cells/simdpaddleocr-default__<样本名>.json
"median": 2.76,                  // 含进程启动的总耗时（进总榜的数字）
"extra": { "t_infers_csharp": [1.83] }   // C# 侧纯推理耗时
// median − t_infers_csharp ≈ 0.93s = 进程开销
```

24 张同口径数字：

| | 总榜单页耗时 | 纯推理 | 进程开销 |
|---|---|---|---|
| SimdPaddleOCR 默认档 | 2.77 s | 1.83 s | 0.93 s（34%）|
| SimdPaddleOCR 受控档 | 2.93 s | 1.93 s | 0.98 s（34%）|
| RapidOCRLite medium | 2.67 s | 2.62 s（引擎自报 elapse）| ≈0 |

口径对齐后 SimdPaddleOCR 纯推理比 RapidOCRLite medium 快约三成。**只影响速度一列**；字错率（识别结果）与内存（含子进程树的峰值采样）不受此口径影响。

## 环境

- AMD Ryzen 7 5700G（8 核 16 线程）、30 GB 内存、**无独立显卡**，Windows 11，纯 CPU 推理
- Python 3.11；SimdPaddleOCR 为 .NET 10（`simd-test` 下用 `dotnet build` 自建 SimdBench）
- 模型：PP-OCRv6 medium（各引擎同档；RapidOCRLite / SimdPaddleOCR / PaddleOCR 共用同一套权重，字典 18708 条哈希一致）
- venv（`venv-*`）、NuGet 模型 DLL（`bin/` 单个 132 MB）不入库
