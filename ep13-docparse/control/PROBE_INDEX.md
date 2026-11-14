# control/ 脚本索引（2026-11-12 逻辑归档）

`control/` 下共 106 个 `.py` + 11 个 `.ps1`，其中**绝大多数是跑测期的一次性临时探针**，与正式控制脚本混放。此索引用于区分两者；发布与复现只需看「正式」一栏。

## 正式脚本（7 个，保留原位、参与控制流程）

| 文件 | 作用 |
|---|---|
| `progress_scan.py` | 读 `batch_state.json` + cells 出跑批进度 |
| `ps_batch.ps1` | 批量进程检查 |
| `rep_final.py` | 全量最终统计与格间隔 |
| `rep_cer_check.py` | CER 负值 / null 检查 |
| `rep_mtime.py` | mtime / set / layer 分布 |
| `rep_proc.py` | win32com 进程盘点 |
| `rep_prog.py` | STATE + NFILES 进度 |

契约与配置（非脚本）：`engines.yaml`、`sets.yaml`、`EXTRACTION_CONTRACT.md`、`SOURCES.md`、`LICENSES.md`、`STATE_NOTES.md`、`run_manifest.json`，以及 `task.json` / `heartbeat.json` / `batch_state.json`（末批运行态残值，见 `STATE_NOTES.md`）。
门控与报告主逻辑在 `scripts/`，不在本目录。

## 临时探针（约 110 个，`_` 前缀，逻辑归档、不参与门控）

| 族 | 约数 | 用途 |
|---|---|---|
| `_brief_*` | 23 | 跑批期间即时 / Cron 简报：已完成格数、速率、CER/wall 概览、字段 KEYS 核对 |
| `_progress_*` | 29 | 进度扫描 / 对账 / 快照 / 统计的各轮变体 |
| `_proc*` | 11 | 进程盘点、owner_pid 存活、batch_runner 是否仍在跑 |
| `_rate_*` | 7 | 按 mtime 估算「格/小时」与剩余时间 |
| `_recon*` | 5 | cells 与 samples manifest 的 sha / UUID 对账 |
| `_report_*` | 4 | 按引擎（尤其 OXR）扫描报告数据与速率 |
| `_outlier*` / `_outage*` | 4 | CER≥0.5 离群格时间、断电中断探测 |
| `_diag*` / `_probe*` / `_final*` / `_verify` / `_integrity` / `_liveness` / `_dup` / `_uuidcheck` / `_where*` / `_snapshot` / `_scan2` / `_rep` / `_chk_batch` / `_ps_*` 等 | 其余 | 数据完整性收口、D-FINE 健康、重复 GT sha、心跳、目录残留等一次性检查 |

## 为什么不物理移动到 `archive/`

收口前评估过移动，最终**选择保留原位 + 建立索引**，理由：

1. 这些脚本普遍硬编码 `D:/study/ai-jms/ep13-docparse/control/...` 与彼此的文件名，移动后互相引用会断（已核实 `_brief_*` 族内至少 4 处互相引用）。
2. 它们是跑测期的**历史证据**，原位保留才能复现「当时是怎么盯进度的」；移动反而破坏证据链。
3. 收益只是目录整洁，风险是复现性下降 —— 对一期强调「可追溯」的实测不划算。

因此「归档」以**逻辑标记**实现：本索引即归档清单，所有 `_` 前缀脚本视为 `archive` 类资产，**不参与任何门控、发布或复现命令**。`archive/` 目录实际存放的是收口前 gates 与外部数据报告的备份。

## 已知残缺件

- `runs/verify_draft_numbers.py`：13 行、末行截断，不可执行。见 `runs/verify_draft_numbers.README.md`，保留原文件不动。
- `control/_prog_report.json`（11-08 快照）：CER/wall 与 11-10 最终值不同（r14 重跑 66 格所致），**勿引**；以 `gates/gate1.json` 与 `outputs/` 数据报告为准。
