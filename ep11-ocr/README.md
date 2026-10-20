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

数字由 `tools/summarize.py` 从 `progress.json` 现算（聚合=每格取最新 attempt）。

### 3.1 热态单页（session 已建好，同进程连续计时；预热不计时）

| 引擎 | 图 | 中位(s) | n | 离散% | CER |
|---|---|---|---|---|---|
| gotocr | book_01.png | 227.66 | 3 | 0.1 | 0.032 |
| gotocr | invoice_01.png | 189.97 | 3 | 0.5 | 0.000 |
| gotocr | lc_01.png | 185.88 | 3 | 0.6 | 0.429 |
| gotocr | shot_01.png | 188.96 | 3 | 0.1 | 0.576 |
| gotocr | skew_01.png | 623.97 | 3 | 1.8 | 0.857 |
| gotocr | table_01.png | 175.75 | 3 | 0.1 | 0.819 |
| paddleocr | book_01.png | 70.50 | 3 | 0.4 | 0.014 |
| paddleocr | book_02.png | 53.18 | 3 | 0.7 | 1.799 |
| paddleocr | hard_01.png | 96.56 | 3 | 0.5 | 0.001 |
| paddleocr | hard_02.png | 18.53 | 3 | 1.1 | 0.000 |
| paddleocr | invoice_01.png | 14.79 | 3 | 0.8 | 0.000 |
| paddleocr | invoice_02.png | 13.00 | 3 | 0.5 | 0.000 |
| paddleocr | lc_01.png | 25.47 | 3 | 0.3 | 0.532 |
| paddleocr | lc_02.png | 86.24 | 3 | 0.3 | 0.032 |
| paddleocr | shot_01.png | 27.85 | 3 | 0.1 | 0.571 |
| paddleocr | shot_02.png | 47.33 | 3 | 0.2 | 1.105 |
| paddleocr | skew_01.png | 72.23 | 3 | 1.0 | 0.013 |
| paddleocr | skew_02.png | 61.74 | 3 | 1.2 | 1.466 |
| paddleocr | table_01.png | 6.45 | 3 | 1.8 | 0.793 |
| paddleocr | table_02.png | 9.42 | 3 | 0.6 | 0.803 |
| rapidocr | book_01.png | 5.72 | 3 | 0.6 | 0.026 |
| rapidocr | book_02.png | 1.97 | 3 | 3.8 | 0.609 |
| rapidocr | hard_01.png | 8.32 | 3 | 4.1 | 0.140 |
| rapidocr | hard_02.png | 1.91 | 3 | 4.9 | 0.165 |
| rapidocr | invoice_01.png | 0.99 | 3 | 5.7 | 0.000 |
| rapidocr | invoice_02.png | 0.79 | 3 | 1.4 | 0.000 |
| rapidocr | lc_01.png | 1.60 | 3 | 4.6 | 0.420 |
| rapidocr | lc_02.png | 7.90 | 3 | 0.7 | 0.033 |
| rapidocr | shot_01.png | 1.68 | 3 | 2.6 | 0.550 |
| rapidocr | shot_02.png | 3.07 | 3 | 3.4 | 1.122 |
| rapidocr | skew_01.png | 5.82 | 3 | 3.7 | 0.026 |
| rapidocr | skew_02.png | 2.19 | 3 | 1.9 | 0.410 |
| rapidocr | table_01.png | 0.40 | 3 | 7.2 | 0.871 |
| rapidocr | table_02.png | 0.39 | 3 | 2.6 | 0.869 |

### 3.2 冷启动（t_spawn → 出字，含解释器启动/导入/建 session/首次执行）

| 引擎 | 图 | 格 | 中位(s) | 残差% | 峰值内存(MB) |
|---|---|---|---|---|---|
| gotocr | invoice_01.png |  | 195.85 | 0.00 | 4857.4 |
| gotocr | invoice_01.png |  | 197.59 | 0.00 | 4857.0 |
| gotocr | invoice_01.png |  | 197.05 | 0.00 | 4858.0 |
| gotocr | table_01.png |  | 182.49 | 0.00 | 4857.8 |
| gotocr | table_01.png |  | 185.17 | 0.00 | 4857.4 |
| gotocr | table_01.png |  | 185.74 | 0.00 | 4857.5 |
| paddleocr | book_01.png |  | 83.20 | 0.00 | 2379.5 |
| paddleocr | book_01.png |  | 82.89 | 0.00 | 2378.0 |
| paddleocr | book_01.png |  | 83.32 | 0.00 | 2376.7 |
| paddleocr | invoice_01.png |  | 27.98 | 0.00 | 1323.2 |
| paddleocr | invoice_01.png |  | 27.86 | 0.00 | 1323.6 |
| paddleocr | invoice_01.png |  | 27.84 | 0.00 | 1324.2 |
| paddleocr | table_01.png |  | 19.57 | 0.00 | 1205.3 |
| paddleocr | table_01.png |  | 19.55 | 0.00 | 1204.3 |
| paddleocr | table_01.png |  | 19.62 | 0.00 | 1203.5 |
| rapidocr | book_01.png |  | 10.51 | 0.00 | 415.5 |
| rapidocr | book_01.png |  | 10.43 | 0.00 | 414.7 |
| rapidocr | book_01.png |  | 10.57 | 0.00 | 415.4 |
| rapidocr | book_02.png |  | 4.55 | 0.00 | 418.6 |
| rapidocr | book_02.png |  | 4.72 | 0.00 | 419.0 |
| rapidocr | book_02.png |  | 4.72 | 0.00 | 420.0 |
| rapidocr | hard_01.png |  | 14.22 | 0.00 | 418.9 |
| rapidocr | hard_01.png |  | 14.35 | 0.00 | 414.5 |
| rapidocr | hard_01.png |  | 14.39 | 0.00 | 415.1 |
| rapidocr | hard_02.png |  | 4.13 | 0.00 | 272.5 |
| rapidocr | hard_02.png |  | 4.10 | 0.00 | 272.1 |
| rapidocr | hard_02.png |  | 4.05 | 0.00 | 271.9 |
| rapidocr | invoice_01.png |  | 2.88 | 0.00 | 218.9 |
| rapidocr | invoice_01.png |  | 2.92 | 0.00 | 219.0 |
| rapidocr | invoice_01.png |  | 2.78 | 0.00 | 218.7 |
| rapidocr | invoice_02.png |  | 2.53 | 0.00 | 213.1 |
| rapidocr | invoice_02.png |  | 2.59 | 0.00 | 212.5 |
| rapidocr | invoice_02.png |  | 2.54 | 0.00 | 212.9 |
| rapidocr | lc_01.png |  | 3.78 | 0.00 | 367.9 |
| rapidocr | lc_01.png |  | 3.81 | 0.00 | 367.1 |
| rapidocr | lc_01.png |  | 3.73 | 0.00 | 368.0 |
| rapidocr | lc_02.png |  | 13.87 | 0.00 | 415.4 |
| rapidocr | lc_02.png |  | 13.71 | 0.00 | 417.2 |
| rapidocr | lc_02.png |  | 13.65 | 0.00 | 419.0 |
| rapidocr | shot_01.png |  | 3.81 | 0.00 | 368.1 |
| rapidocr | shot_01.png |  | 3.87 | 0.00 | 367.6 |
| rapidocr | shot_01.png |  | 3.82 | 0.00 | 366.9 |
| rapidocr | shot_02.png |  | 6.98 | 0.00 | 368.6 |
| rapidocr | shot_02.png |  | 6.75 | 0.00 | 367.9 |
| rapidocr | shot_02.png |  | 6.73 | 0.00 | 367.6 |
| rapidocr | skew_01.png |  | 10.49 | 0.00 | 548.5 |
| rapidocr | skew_01.png |  | 10.58 | 0.00 | 548.2 |
| rapidocr | skew_01.png |  | 10.43 | 0.00 | 548.6 |
| rapidocr | skew_02.png |  | 4.69 | 0.00 | 564.9 |
| rapidocr | skew_02.png |  | 4.70 | 0.00 | 565.2 |
| rapidocr | skew_02.png |  | 4.85 | 0.00 | 565.2 |
| rapidocr | table_01.png |  | 1.75 | 0.00 | 249.6 |
| rapidocr | table_01.png |  | 1.69 | 0.00 | 251.0 |
| rapidocr | table_01.png |  | 1.73 | 0.00 | 250.8 |
| rapidocr | table_02.png |  | 1.87 | 0.00 | 219.0 |
| rapidocr | table_02.png |  | 1.82 | 0.00 | 219.0 |
| rapidocr | table_02.png |  | 1.83 | 0.00 | 219.0 |

- gotocr invoice_01 冷启动 3 次：197.05 / 极差 0.88%
- gotocr table_01 冷启动 3 次：185.17 / 极差 1.76%

### 3.3 体积与内存（自动量取）

| 引擎 | 模型落地体积(MB) | 冷启动峰值内存(MB) |
|---|---|---|
| gotocr | 1368.4 | 5022 |
| paddleocr | 132.7 | 3522 |
| rapidocr | 15.6 | 729 |

### 3.4 补跑批次（23 项任务 → 22 格，全部完成）

- n<3 的 19 格：整格重跑为新 attempt，全部补到 n=3（热态一格=预热 1 次不计时 + 计时 3 次）。
- 离散超标 3 格：定向重跑一次 → rapidocr table_02 10.4%→2.61% 达标；仍 >5% 的 2 格如实标注（invoice_01 5.72%、table_01 7.24%，均为亚秒级页面，绝对极差约 0.057s / 0.029s）——按纪律不为达标反复跑。
- 超时失败格（gotocr skew_01 hot）：单格上限 1200s→5400s 后出数，中位 623.97s、离散 1.83%、CER 0.857；归因=上轮超时窗口过短，不是模型失败。

### 3.5 批量吞吐（热态，用同一套 14 张循环；数字来自 output/batch/*.json）

| 引擎 | 页数 | 成功 | 每页(s) | 页/分钟 | 加载(s) |
|---|---|---|---|---|---|
| paddleocr | 10 | 10 | 48.31 | 1.2 | 13.4 |
| rapidocr | 10 | 10 | 5.27 | 11.4 | 0.6 |
| rapidocr | 100 | 100 | 3.37 | 17.8 | 0.7 |

（吞吐批为独立测量，未受补跑影响。）

### 3.6 断网批（Python socket 层出网拦截）

guard 自检 blocked=True，引擎出网尝试次数=0，失败格=0。逐格明细见 report_ep11.html 第十一节。

| 引擎 | 格数 | 全部 ok |
|---|---|---|
| gotocr | 4 | 是 |
| paddleocr | 16 | 是 |
| rapidocr | 16 | 是 |

手写类本期未覆盖（inbox 为空）。

## 4. 两个坑（本期代价最大的）

1. **冷启动计时窗口被「模型体积统计」污染**：`model_bytes()` 走目录遍历，放在出字之前会让冷启动虚高（GOT 的 1.4 GB 目录尤其明显）。修法：`t_end` 取在出字那一刻，体积统计挪到窗口外。

2. **网页截图不能拿 DOM 文本层当 GT**：DOM 是整页文本（本例 20 万字符），而画面只有一屏，CER 会变成 ~0.999 的无意义值。改用「网页打印成 PDF → 渲染成图 + PDF 文本层 GT」后逐字对应。

3. **固定值超时上限会把能出数的格误判成失败**：GOT skew_01 单页要 10 分钟量级，1200s 的单格上限把它记成 `timeout_killed`（补跑把上限放宽到 5400s 后正常出数，中位 623.97s）。上限要按「单页中位 × 次数 + 加载」给足，不要拍一个固定值。

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