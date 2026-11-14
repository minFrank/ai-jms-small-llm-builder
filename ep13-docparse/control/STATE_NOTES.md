# control/ 运行态文件说明（2026-11-12 收口，只增不改）

`control/` 下三个 JSON 是**跑测期的运行状态快照**，不是全量统计。为避免被误引，特此标注；原文件数值一律保留、不回填、不篡改。

| 文件 | 当前值 | 性质 | 应改读哪里 |
|---|---|---|---|
| `task.json` | `state=done`、`last_progress/finished_at=2026-11-08T22:54:14` | 末批 runner 的状态机残值 | 全量状态看 `gates/summary.json`（156/156 complete） |
| `heartbeat.json` | `hb_at=2026-11-08T22:54:13`、`owner_pid=34656` | 最后一次心跳，跑完即停 | 无需再读；进程已退出 |
| `batch_state.json` | `n_run=66 / n_skip=90`、`desired=running`、`seq=done` | **r14 定向重跑 66 格**的末批残值，不是 156 格全量 | 分母与 rep 数看 `control/run_manifest.json` 与 `gates/gate1.json` |

注意：`batch_state.json` 的 `desired=running` 与 `seq=done` 并存，是历史状态机未收尾所致，**不代表仍有进程在跑**（已核实 `owner_pid` 不存在、无 batch_runner/runner 进程）。

## 权威数据源（发布引用请用这些）

| 想查什么 | 文件 |
|---|---|
| 全量格数与状态 | `gates/summary.json` |
| run 起始/结束时间、rep 总数 | `control/run_manifest.json` |
| 逐引擎成功率、耗时、资格 | `gates/gate1.json` |
| 四门结论 | `gates/gate0..3.json` |
| 样本与 GT 指纹 | `samples/manifest.json`、`gt/manifest.json`、`gt/gt_audit.json` |
| 数据回填与已知偏差 | `docs/data_provenance.md` |

> 2026-11-12 收口原则：历史事件不重写、不为让门控好看而回填数值。所有新增信息另立文件，保留原证据链。
