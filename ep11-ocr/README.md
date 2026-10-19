# ep11 · 本地 OCR 实测（无独立显卡，5700G 纯 CPU）

栏目「本地无显卡 AI」第 11 期的复刻包。**所有数字由本目录脚本从 `progress.json` 现算，报告 HTML 里的每个数字都可由 `tools/assert_report.py` 复核。**

交付形态：**数据报告**（`report_ep11.html`），未写稿、未推草稿箱。

## 1. 环境要求

| 项 | 值 |
|---|---|
| CPU / 内存 | AMD Ryzen 7 5700G（8 核 16 线程）/ 30.0 GB |
| 独立显卡 | 无（torch.cuda.is_available = False） |
| Python | 3.11.16 |
| onnxruntime / opencv | 1.29.0 / 4.10.0 |
| rapidocr-onnxruntime | 1.4.4 |
| paddlepaddle / paddleocr | 3.3.1 / 3.7.0 |
| torch / transformers | 2.14.1+cpu / 5.18.0 |
| GOT 独立 venv | `D:/models/ocr/got-venv/Scripts/python.exe`（transformers 4.37.2 + torchvision + verovio） |
| 模型落盘 | `D:/models/ocr/`（GOT-OCR2.0 CPU 权重 1368.4 MB） |

## 2. 三步跑起来

```bash
# 1) 建样本 + GT（会联网取 arXiv 2409.01704 与两个真实网页）
python make_samples.py
# 2) 串行跑全部阶段（同一时刻只有一个测量进程）
python -u runner.py
# 3) 聚合 + 只读断言
python summarize.py && python assert_report.py
```

断网批单独一份 progress：`python -u offline_runner.py`；修正 GT 后的定向重跑：`python -u fixup_runner.py`。

## 3. 实测数据（节选，完整见 report_ep11.html）

### 3.1 热态单页（session 已建好，同进程连续计时）

| 引擎 | 图 | 中位(s) | n | 离散% | CER |
|---|---|---|---|---|---|
| gotocr | book_01.png | 225.21 | 1 | 0.0 | 0.032 |
| gotocr | invoice_01.png | 189.32 | 1 | 0.0 | 0.000 |
| gotocr | lc_01.png | 187.59 | 1 | 0.0 | 0.999 |
| gotocr | shot_01.png | 187.03 | 1 | 0.0 | 0.999 |
| gotocr | skew_01.png | - | 0 | - | - |
| gotocr | table_01.png | 175.64 | 1 | 0.0 | 0.819 |
| paddleocr | book_01.png | 70.50 | 3 | 0.4 | 0.014 |
| paddleocr | book_02.png | 53.37 | 1 | 0.0 | 1.799 |
| paddleocr | hard_01.png | 96.27 | 1 | 0.0 | 0.001 |
| paddleocr | hard_02.png | 18.46 | 2 | 1.4 | 0.000 |
| paddleocr | invoice_01.png | 14.79 | 3 | 0.8 | 0.000 |
| paddleocr | invoice_02.png | 12.89 | 2 | 0.9 | 0.000 |
| paddleocr | lc_01.png | 25.06 | 1 | 0.0 | 0.532 |
| paddleocr | lc_02.png | 85.83 | 2 | 0.1 | 0.032 |
| paddleocr | shot_01.png | 27.55 | 1 | 0.0 | 0.571 |
| paddleocr | shot_02.png | 46.93 | 1 | 0.0 | 1.105 |
| paddleocr | skew_01.png | 71.28 | 1 | 0.0 | 0.013 |
| paddleocr | skew_02.png | 60.99 | 1 | 0.0 | 1.466 |
| paddleocr | table_01.png | 6.45 | 3 | 1.8 | 0.793 |
| paddleocr | table_02.png | 9.23 | 2 | 2.1 | 0.803 |
| rapidocr | book_01.png | 5.72 | 3 | 0.6 | 0.026 |
| rapidocr | book_02.png | 1.97 | 3 | 3.8 | 0.609 |
| rapidocr | hard_01.png | 8.32 | 3 | 4.1 | 0.140 |
| rapidocr | hard_02.png | 1.91 | 3 | 4.9 | 0.165 |
| rapidocr | invoice_01.png | 1.03 | 3 | 7.6 | 0.000 |
| rapidocr | invoice_02.png | 0.79 | 3 | 1.4 | 0.000 |
| rapidocr | lc_01.png | 1.60 | 3 | 4.6 | 0.420 |
| rapidocr | lc_02.png | 7.90 | 3 | 0.7 | 0.033 |
| rapidocr | shot_01.png | 1.68 | 3 | 2.6 | 0.550 |
| rapidocr | shot_02.png | 3.07 | 3 | 3.4 | 1.122 |
| rapidocr | skew_01.png | 5.82 | 3 | 3.7 | 0.026 |
| rapidocr | skew_02.png | 2.19 | 3 | 1.9 | 0.410 |
| rapidocr | table_01.png | 0.48 | 3 | 12.3 | 0.871 |
| rapidocr | table_02.png | 0.41 | 3 | 10.4 | 0.869 |

### 3.2 冷启动（t_spawn → 出字，含解释器启动/导入/建 session/首次执行）

| 引擎 | 图 | 格 | 中位(s) | 残差% | 峰值内存(MB) |
|---|---|---|---|---|---|
| gotocr | invoice_01.png |  | 195.85 | 0.00 | 4857 |
| gotocr | table_01.png |  | 182.49 | 0.00 | 4858 |
| paddleocr | book_01.png |  | 83.20 | 0.00 | 2380 |
| paddleocr | book_01.png |  | 82.89 | 0.00 | 2378 |
| paddleocr | book_01.png |  | 83.32 | 0.00 | 2377 |
| paddleocr | invoice_01.png |  | 27.98 | 0.00 | 1323 |
| paddleocr | invoice_01.png |  | 27.86 | 0.00 | 1324 |
| paddleocr | invoice_01.png |  | 27.84 | 0.00 | 1324 |
| paddleocr | table_01.png |  | 19.57 | 0.00 | 1205 |
| paddleocr | table_01.png |  | 19.55 | 0.00 | 1204 |
| paddleocr | table_01.png |  | 19.62 | 0.00 | 1204 |
| rapidocr | book_01.png |  | 10.51 | 0.00 | 416 |
| rapidocr | book_01.png |  | 10.43 | 0.00 | 415 |
| rapidocr | book_01.png |  | 10.57 | 0.00 | 415 |
| rapidocr | book_02.png |  | 4.55 | 0.00 | 419 |
| rapidocr | book_02.png |  | 4.72 | 0.00 | 419 |
| rapidocr | book_02.png |  | 4.72 | 0.00 | 420 |
| rapidocr | hard_01.png |  | 14.22 | 0.00 | 419 |
| rapidocr | hard_01.png |  | 14.35 | 0.00 | 414 |
| rapidocr | hard_01.png |  | 14.39 | 0.00 | 415 |
| rapidocr | hard_02.png |  | 4.13 | 0.00 | 272 |
| rapidocr | hard_02.png |  | 4.10 | 0.00 | 272 |
| rapidocr | hard_02.png |  | 4.05 | 0.00 | 272 |
| rapidocr | invoice_01.png |  | 2.88 | 0.00 | 219 |
| rapidocr | invoice_01.png |  | 2.92 | 0.00 | 219 |
| rapidocr | invoice_01.png |  | 2.78 | 0.00 | 219 |
| rapidocr | invoice_02.png |  | 2.53 | 0.00 | 213 |
| rapidocr | invoice_02.png |  | 2.59 | 0.00 | 212 |
| rapidocr | invoice_02.png |  | 2.54 | 0.00 | 213 |
| rapidocr | lc_01.png |  | 3.78 | 0.00 | 368 |
| rapidocr | lc_01.png |  | 3.81 | 0.00 | 367 |
| rapidocr | lc_01.png |  | 3.73 | 0.00 | 368 |
| rapidocr | lc_02.png |  | 13.87 | 0.00 | 415 |
| rapidocr | lc_02.png |  | 13.71 | 0.00 | 417 |
| rapidocr | lc_02.png |  | 13.65 | 0.00 | 419 |
| rapidocr | shot_01.png |  | 3.81 | 0.00 | 368 |
| rapidocr | shot_01.png |  | 3.87 | 0.00 | 368 |
| rapidocr | shot_01.png |  | 3.82 | 0.00 | 367 |
| rapidocr | shot_02.png |  | 6.98 | 0.00 | 369 |
| rapidocr | shot_02.png |  | 6.75 | 0.00 | 368 |
| rapidocr | shot_02.png |  | 6.73 | 0.00 | 368 |
| rapidocr | skew_01.png |  | 10.49 | 0.00 | 548 |
| rapidocr | skew_01.png |  | 10.58 | 0.00 | 548 |
| rapidocr | skew_01.png |  | 10.43 | 0.00 | 549 |
| rapidocr | skew_02.png |  | 4.69 | 0.00 | 565 |
| rapidocr | skew_02.png |  | 4.70 | 0.00 | 565 |
| rapidocr | skew_02.png |  | 4.85 | 0.00 | 565 |
| rapidocr | table_01.png |  | 1.75 | 0.00 | 250 |
| rapidocr | table_01.png |  | 1.69 | 0.00 | 251 |
| rapidocr | table_01.png |  | 1.73 | 0.00 | 251 |
| rapidocr | table_02.png |  | 1.87 | 0.00 | 219 |
| rapidocr | table_02.png |  | 1.82 | 0.00 | 219 |
| rapidocr | table_02.png |  | 1.83 | 0.00 | 219 |

### 3.3 体积与内存（自动量取）

| 引擎 | 模型落地体积(MB) | 冷启动峰值内存(MB) |
|---|---|---|
| gotocr | 1368.4 | 4858 |
| paddleocr | 132.7 | 3521 |
| rapidocr | 15.6 | 729 |

### 3.4 批量吞吐（热态，用同一套 14 张循环）

| 引擎 | 页数 | 每页(s) | 页/分钟 | 加载(s) |
|---|---|---|---|---|
| paddleocr | 10 | 48.31 | 1.2 | 13.4 |
| rapidocr | 10 | 5.27 | 11.4 | 0.6 |
| rapidocr | 100 | 3.37 | 17.8 | 0.7 |

### 3.5 断网批（Python socket 层出网拦截）

guard 自检 blocked=True，引擎出网尝试次数=0，失败格=0。

| 引擎 | 图 | 模式 | 状态 | CER |
|---|---|---|---|---|
| gotocr | invoice_01.png | cold | ok | 0.000 |
| gotocr | invoice_01.png | hot | ok | 0.000 |
| gotocr | table_01.png | cold | ok | 0.819 |
| gotocr | table_01.png | hot | ok | 0.819 |
| paddleocr | book_01.png | cold | ok | 0.014 |
| paddleocr | book_01.png | hot | ok | 0.014 |
| paddleocr | book_02.png | hot | ok | 1.799 |
| paddleocr | hard_01.png | hot | ok | 0.001 |
| paddleocr | hard_02.png | hot | ok | 0.000 |
| paddleocr | invoice_01.png | cold | ok | 0.000 |
| paddleocr | invoice_01.png | hot | ok | 0.000 |
| paddleocr | invoice_02.png | hot | ok | 0.000 |
| paddleocr | lc_01.png | hot | ok | 0.532 |
| paddleocr | lc_02.png | hot | ok | 0.032 |
| paddleocr | shot_01.png | hot | ok | 0.571 |
| paddleocr | shot_02.png | hot | ok | 1.105 |
| paddleocr | skew_01.png | hot | ok | 0.013 |
| paddleocr | skew_02.png | hot | ok | 1.466 |
| paddleocr | table_01.png | hot | ok | 0.793 |
| paddleocr | table_02.png | hot | ok | 0.803 |
| rapidocr | book_01.png | cold | ok | 0.026 |
| rapidocr | book_01.png | hot | ok | 0.026 |
| rapidocr | book_02.png | hot | ok | 0.609 |
| rapidocr | hard_01.png | hot | ok | 0.140 |
| rapidocr | hard_02.png | hot | ok | 0.165 |
| rapidocr | invoice_01.png | cold | ok | 0.000 |
| rapidocr | invoice_01.png | hot | ok | 0.000 |
| rapidocr | invoice_02.png | hot | ok | 0.000 |
| rapidocr | lc_01.png | hot | ok | 0.420 |
| rapidocr | lc_02.png | hot | ok | 0.033 |
| rapidocr | shot_01.png | hot | ok | 0.550 |
| rapidocr | shot_02.png | hot | ok | 1.122 |
| rapidocr | skew_01.png | hot | ok | 0.026 |
| rapidocr | skew_02.png | hot | ok | 0.410 |
| rapidocr | table_01.png | hot | ok | 0.871 |
| rapidocr | table_02.png | hot | ok | 0.869 |

## 4. 两个坑（本期代价最大的）

1. **冷启动计时窗口被「模型体积统计」污染**：`model_bytes()` 走目录遍历，放在出字之前会让冷启动虚高（GOT 的 1.4 GB 目录尤其明显）。修法：`t_end` 取在出字那一刻，体积统计挪到窗口外。

2. **网页截图不能拿 DOM 文本层当 GT**：DOM 是整页文本（本例 20 万字符），而画面只有一屏，CER 会变成 ~0.999 的无意义值。改用「网页打印成 PDF → 渲染成图 + PDF 文本层 GT」后逐字对应。

## 5. 样本与 GT

| 图 | 类别 | 来源 | 尺寸 |
|---|---|---|---|
| book_01 | 书页 | real_pdf | 1347×1743 |
| book_02 | 书页 | real_pdf | 1347×1743 |
| shot_01 | 截图 | real_web_pdf | 1224×1584 |
| shot_02 | 截图 | real_web_pdf | 1224×1584 |
| invoice_01 | 电子发票 | synthetic | 1100×694 |
| invoice_02 | 电子发票 | synthetic | 1050×720 |
| table_01 | 表格 | synthetic | 1088×540 |
| table_02 | 表格 | synthetic | 1138×742 |
| hard_02 | 混合难例 | synthetic | 1020×445 |
| hard_01 | 混合难例 | real_pdf | 1347×1743 |
| skew_01 | 倾斜拍照 | real_pdf+degrade | 1671×2015 |
| skew_02 | 倾斜拍照 | real_pdf+degrade | 1825×2123 |
| lc_01 | 低对比反光 | real_web+degrade | 1224×1584 |
| lc_02 | 低对比反光 | real_pdf+degrade | 1347×1743 |

**GT 完备性**：`real_web_pdf` 与 `book_02`（整页插图）的 PDF 文本层**不含图内栅格文字与部分渲染元素**，这三类图的 CER 不能当准确率读；其余来源的 GT 与画面逐字对应。

手写类**本期未覆盖**（作者 inbox 为空，按批复降级为 7 类 14 张）。

## 6. 许可

RapidOCR（Apache-2.0）、PaddleOCR（Apache-2.0）、GOT-OCR2.0（Apache-2.0，第三方 CPU 转换仓库 `RufusRubin777/GOT-OCR2_0_CPU`）。本目录脚本与数据随仓库许可。

## 7. 原始日志

`logs/` 不入库（用户要求）。逐格日志文件名形如 `{engine}__{img}__{mode}_a{attempt}.txt`，报告与 result.json 里的每一行都能对到一个日志文件。