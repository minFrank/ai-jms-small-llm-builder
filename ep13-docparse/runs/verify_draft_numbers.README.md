# runs/verify_draft_numbers.py 状态说明（2026-11-12）

`verify_draft_numbers.py` 是跑测期用于核对草稿数字的一次性校验脚本，**当前残缺**：

- 文件仅 13 行，末行停在 `if not c.get("unstable") and c.get("cer_median") is not N...`，语法不完整，**不可执行**。
- 从上下文推断，被截断处应为 `is not None`，后续逻辑（按引擎聚合 CER 中位）已无从考证。

## 处置

**保留原文件原样，不删、不猜补、不重写。** 理由：它是跑测期的历史痕迹，猜补出来的「可运行版本」不是当时的证据，反而会造成误导。

- 它**不参与任何门控**（G0–G3 由 `scripts/run_gates.py` + `scripts/gate_checks.py` 执行）。
- 当前权威数字来源：`gates/gate1.json`（逐引擎成功率 / caliber）、`gates/rank_set.json`、`gates/stats_test.json`、`outputs/2026-11-10-ep13-数据报告.html`。
- 如需恢复这类校验，正确做法是**新建** `scripts/verify_report_numbers.py`，从 `cells/` 现算并与成稿/报告逐项对账，而不是修这个残件。

同类情况见 `control/PROBE_INDEX.md`、`docs/data_provenance.md` 偏差 #15。
