# ep13 来源登记（SOURCES）— 2026-11-07

## 模型（D:/models/models/ocr/ep13-docparse/，全部本地只读，C 盘零写入）
| 引擎 | 来源 | 下载日期 |
|---|---|---|
| OXR 1.0 | github.com/SoMarkAI/OXR → HF（3.16GB，MANIFEST 登记） | 2026-11-03 |
| PaddleOCR-VL-1.6 | HF PaddlePaddle/PaddleOCR-VL-1.6（1.93GB） | 2026-11-03 |
| Xiaomi-OCR-0 | HF（1.75GB） | 2026-11-03 |
| OvisOCR2 | HF（1.73GB） | 2026-11-03 |
| MonkeyOCR-pro-1.2B | HF（4.83GB，Recognition 子模型） | 2026-11-03 |
| surya-ocr-2.5 | HF datalab-to/surya-ocr-2.5（2.0GB，P0 实算 0.69B） | 2026-11-04 |
| 归档：TeleOCR / dots.ocr | HF + GitHub（复活实验 16 项，CPU 不可行归档） | 2026-11-03/04 |

## 样本（samples/manifest.json，26 张 sha256 冻结）
- 18 张复用 ep11-ocr（其来源：arXiv 2409.01704 PDF 页 + 真实网页 Chrome 打印 + 合成版面，见 ep11 make_samples.py）
- 8 张本机合成（cn_doc/contract/menu/poster/paper/form/resume/mixed，GT=源文本逐字，脚本 make_samples_13.py（评审材料副本在评审目录根））

## GT（gt/manifest.json）
- gt_v=ep13-gt-v1、status=signed、reviewer=user(Frank)、26 份 content_hash=5266101978d42ef6…

## 代码与规格
- 规格 V6e：hermes plans/2026-11-03-docparse-bench-console-spec.md（唯一权威源）
- 评审：ep13-docparse/docs/reviews/（dsh r1–r4 + 设计稿 v1–v4）

## 现状更正（2026-11-12 收口，只增不改）

上方「GT」段的 `gt_v=ep13-gt-v1` + `content_hash=5266101978…` 是 **2026-11-07 登记时的历史记录**，保留原貌但不是当前值：

- 当前 `gt/manifest.json` 为 `gt_v=ep13-gt-v2`、`status=signed`、`signed_at=2026-11-08T06:57:34`、`total_chars=24679`。
- r14 重跑 66 格后 GT 重标注为 v2 并重签；G0 逐格比对已按 v2 通过（156/156）。
- 登记的 v1 hash 与当前 `content_hash` 相同，逻辑上存疑；`total_chars` 24679/24682 两值并存。二者均**未擅改**，列为待核，见 `docs/data_provenance.md`。

规格版本口径：本文件与 `samples/manifest.json` 记 V6e，`EPISODE.json` / `engines.yaml` / `sets.yaml` 记 V6d / V6d-errata。权威源正文标题为 V6d、§2.2b 增补为 V6e，**两者指同一份规格的不同修订表述**，非两份规格；`EPISODE.json` 已加 `spec_version_note` 说明。

模型目录名待核：`control/engines.yaml` 中 `xiaomi_vl.model` 写 `.../XiaomiMiMo-VL-7B`，而磁盘 `D:/models/models/ocr/ep13-docparse/` 下实际只有 `Xiaomi-OCR-0`（与 lineup 的 0.8B 一致）。该 yaml 字段疑似冻结时旧值，**未擅改**，见 `docs/data_provenance.md`；发布前请确认实际加载路径。
