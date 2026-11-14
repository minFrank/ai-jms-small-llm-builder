# ep13 数据溯源与已知偏差台账（2026-11-12 收口）

> 用途：把「最终 156 格是怎么来的、哪些地方不是原样落盘、哪些数字不能当权威」一次讲清。
> **收口原则：不重写历史、不为过门回填数值、推理数据一格未动。** 新增证据一律另立文件，保留原证据链。
> 本文与 `control/STATE_NOTES.md`、`control/run_manifest.json`、`gates/*.json` 配套阅读。

## 一、这批数据经历了什么（时间线）

| 时点 | 事件 | 证据 |
|---|---|---|
| 2026-11-04 21:18:39 | 本次 run 首次产生 rep（**run 起始的可验证下界**） | 156 格全部 `reps[].ts` 最小值，见 `control/run_manifest.json` |
| 2026-11-04 | GT v1 签核、EXTRACTION_CONTRACT v1 冻结、冒烟 6/6 + 2/2 | `docs/reviews/README.md` 冒烟段 |
| 2026-11-05 | EXTRACTION_CONTRACT 升 v2（surya 标签/复读事故驱动），GT 内容当时未动 | `control/EXTRACTION_CONTRACT.md` 签核行 |
| 2026-11-08 00:02 | **155 个 cell 在同一分钟被批量重写** | `control/_prog_report.json` 的 `mtime_series` |
| 2026-11-08 06:57:34 | GT 重标注为 **v2** 并重签 | `gt/manifest.json` |
| 2026-11-08 22:54:14 | 末批完成（r14 定向重跑后） | `control/batch_state.json` |
| 2026-11-10 00:54:56 | 四门门控产物定稿 | `gates/summary.json` 原值 |
| 2026-11-12 | 本次收口：补 run_manifest、修门控执行器与 G1 判定、成稿补局限、报告回存 | 见第六节 |

**r14 重跑**：修复 8 张合成图的页脚、词中断行、不可见字符后，8 张合成 + 3 张受影响的真实样本 = 11 样本 × 6 引擎 = **66 格零失败重跑**，GT 重标注 v2。来源：`gt/manifest.json` errata、成稿 §六。

## 二、已知偏差台账（发布引用前逐条对照）

| # | 项目 | 证据 | 影响 | 处置 |
|---|---|---|---|---|
| 1 | **r15/r16 回填** | 抽查 cell 的 `fingerprint` 含「r15 回填：重跑格被 runner 占位 none-smoke 覆盖」「r16 回填」字样 | 最终 156 格**不是跑测瞬间原样落盘** | 不改数据，本文登记；「逐格可追溯」应理解为「当前落盘可逐格核对」，非「落盘后零改动」 |
| 2 | **155 格同分钟批量重写** | `control/_prog_report.json` 的 `mtime_series` | 文件 mtime 不能作为采集时刻使用 | 起始时间改用 `reps[].ts`（见 `run_manifest.json`），不依赖 mtime |
| 3 | **fingerprint 占位值** | cell 内 `git="ep13"`、`deps="see-venv"`、`host_manifest_id="host-1"`、`seed/order=0` | 代码/依赖/主机版本无法从 cell 反查 | 列为待补；`EPISODE.json` 已注明仓库**无 commit 可钉** |
| 4 | **GT v1 快照缺失** | `gt_versions/` 为空；`gt/manifest.json` errata 只有文字记录 | v1 内容不可回溯 | 见 `gt_versions/README.md`；**不伪造** v1 快照 |
| 5 | **GT hash / 字符数自相矛盾** | `content_hash=5266101978…` 与 `SOURCES.md` 登记的 v1 hash 相同（v1→v2 内容已变）；`total_chars` 头部 24679 vs errata 24682 | 签核凭据存疑 | **未擅改**；逐格比对用的是 per-sample `gt_sha256`（156/156 通过），不受影响。列为待核 |
| 6 | **模型身份/路径不一致** | `control/engines.yaml`: `xiaomi_vl.model=…/XiaomiMiMo-VL-7B`，磁盘实际只有 `Xiaomi-OCR-0`；OXR 在 P0 叫 `OXR-1.0`、配置里叫 `OXR-Doc`；`venvs/ovis` 被 xiaomi 与 ovis 共用 | 引擎身份可能被读者质疑 | **未擅改冻结配置**；`SOURCES.md` 已登记。发布前确认实际加载路径（lineup 宣称 0.8B 与 `Xiaomi-OCR-0` 一致） |
| 7 | **dpi 不一致** | 8 张合成 150dpi（spec 要求 300）；抽查 cell `input.dpi=300` 而 `samples/manifest.json` 该样本为 150 | 分辨率口径不统一 | 成稿第九节已披露；未回填 |
| 8 | **S24 † 成员从未预注册** | 两份规格与 `control/sets.yaml` 都未写明 † 是哪两张 | S24 主榜无法产出 | `build_data_report.py` 已声明不出表；`gate_checks.py` 2026-11-12 改为显式「不适用」留痕，不再静默跳过。**见第三节：不建议现在补冻结** |
| 9 | **S_PDF 未跑、结构层缺席** | `pdfs/` 空、`outputs/` 原为空 | 版面/阅读顺序/表格/公式不进分数 | 成稿第九节明确「本期=整页文字转录」；EP14 补 |
| 10 | **三件套未采** | 逐格 rss、timeout 记录缺失 | 内存/超时不可逐格分析 | G3 ⑤按 A 方案「披露即过」，原判据值保留 |
| 11 | **GT 非独立转录** | 8 张合成 GT = 渲染输入字符串；18 张复用 ep11（含 arXiv PDF 页、网页打印）；单人签核 | CER 可能偏低，语言先验与视觉识别难拆 | 成稿第九节披露；EP14 建议补无语言先验对照组 + 独立转录 |
| 12 | **样本非独立/无拍照** | 26 张中 21 个唯一文本（5 组同源）；无真实相机拍照、无手写 | 外推边界受限 | 成稿第九节披露 |
| 13 | **运行态文件是末批残值** | `task.json`/`heartbeat.json` 停在 11-08；`batch_state.json` `n_run=66/n_skip=90` | 易被误当全量统计 | `control/STATE_NOTES.md` 已标注权威数据源 |
| 14 | **旧快照未标废弃** | `control/_prog_report.json`（11-08）的 CER/wall 与 11-10 最终值不同 | 易被误引 | 本文登记；以 `gates/gate1.json` 与 `outputs/` 数据报告为准 |
| 15 | **残缺脚本** | `runs/verify_draft_numbers.py` 仅 13 行、末行截断 | 不可执行 | 保留原文件不动，另附 `runs/verify_draft_numbers.README.md`；不参与任何门控 |
| 16 | **外部依赖** | 唯一权威 spec、模型权重、ep11 样本、成稿均在 C 盘 hermes / D 盘 models | 期目录原本不自包含 | 2026-11-12 已把数据报告回存 `outputs/`；路径改为可配置（`EP13_BASE` / `EP13_REPORT_OUT`）。成稿仍由 hermes 管理 |
| 17 | **版本标识不一** | `EPISODE.json`=V6d、`sets/engines.yaml`=V6d-errata、`samples/manifest.json`+`SOURCES.md`+成稿=V6e；评审稿 v4 的 `<h1>` 写 v3 | 易误判为两份规格 | `EPISODE.json` 加 `spec_version_note` 说明是同一份规格的修订表述；评审稿按项目规则「只增不改」，仅在此登记，不修改历史 HTML |
| 18 | **host_manifest 未落地** | `control/host_manifest.json` 不存在（设计清单 A 组要求 cpu/mem/os/python/threads/gpu/power/load → id 入 fingerprint） | 主机与依赖版本无法从 cell 反查 | `docs/reviews/README.md` 落地状态复核已标为真缺口；未伪造 host 信息 |
| 19 | **process_guard.py 待核** | `scripts/process_guard.py` 未找到（设计清单 B 组要求单实例 lock、cmdline 盘点、kill 前后验活）；冒烟 kill 演练三轮已过 | 进程守护可能由 runner 内联实现，需确认 | 列为待核，未改动运行代码；见 `docs/reviews/README.md` |

## 三、一条建议的撤回：不要现在「冻结 S24 † 两张」

收口前的优化建议里曾列「冻结 S24 的 † 两张成员」。核对后**撤回**：† 成员若在 156 格已跑完后从结果里挑，等于用结果反推预注册口径，正是 `build_data_report.py` 明确拒绝的做法（原文：「不能临时挑选样本充当预注册口径」）。

正确处置：本期不出 S24 主榜、在报告与成稿如实披露；若下期需要 S24，须在**跑测之前**把成员写进规格与 `sets.yaml`。`gate_checks.py` 已把该项从「静默 continue」改为显式「不适用 + 理由」。

## 四、本次收口改了什么（一格推理数据都没动）

| 文件 | 改动 |
|---|---|
| `scripts/gate_checks.py` | G0 优先读 `run_manifest.started_at` 并**真做时序比较**；G1 修 `diff_pct>10`（单位错、恒不触发）、`ref=min(25,23)`（S26 参考线失效）、S24 静默跳过三处 |
| `scripts/run_gates.py` | 加 `locked` 覆盖保护 + `--force`；G3 改为复用已锁定的发布前门产物，不再硬编码 not_run 回退；summary 加 `gates_note` |
| `control/run_manifest.json` | **新建**：run 级起止时间、rep 总数、证据来源与「下界非精确进程时刻」声明 |
| `gates/gate0..2.json` / `summary.json` | 由修正后的执行器重算；`G0 fail→pass`，G1/G2 仍 pass，summary 与 gate3 一致 |
| `gates/gate3.json` | 加 `locked`、`evidence_audit`、`pending_before_publish`；修正 ① 的成稿字节数；**「你终审」保持 false** |
| `archive/` | 备份收口前的 gates 与外部数据报告 |
| `scripts/build_data_report.py` | 输出路径可配置 + 回存 `outputs/`；闸门状态文案改为动态 |
| `outputs/` | 数据报告自留副本（原为空目录） |
| 外部成稿 | 补「九、本期口径与局限」与「写在最后」；`.md.tmp` 备份为 `.bak-20261112`（未删） |
| `control/{STATE_NOTES,EXTRACTION_CONTRACT,SOURCES,LICENSES}.md`、`EPISODE.json` | 现状更正与待核登记（历史原文保留） |

## 五、怎么复现

```bash
cd D:/study/ai-jms/ep13-docparse
python scripts/run_gates.py            # 重算 G0/G1/G2；G3 自动复用已锁定产物
python scripts/run_gates.py --force    # 仅当确实要重算 G3 时（会丢人工实跑证据，慎用）
python scripts/build_data_report.py    # 同时写外部路径 + outputs/
# 自定义路径：
#   EP13_BASE=... EP13_REPORT_OUT=... python scripts/build_data_report.py
```

权威顺序：`gates/gateN.json` > `gates/summary.json` > `outputs/数据报告` > `control/_prog_report.json`（旧快照，勿引）> `control/batch_state.json`（末批残值，勿引）。

## 六、仍待人工完成（不属于代码收口）

1. **按当前成稿重新生成 HTML 并做两次 md2html 渲染对账**（成稿已从 15,742 B 扩到 20,351 B，现存 `.md.html` 27,325 B 对应旧稿）。
2. **模型身份/许可核实**：`engines.yaml` 的 xiaomi 路径、Xiaomi/Monkey 上游许可、surya 的 Open RAIL-M 修改版附加条款。
3. **用户本人终审** → 将 `gates/gate3.json` 的「你终审」置 true、`verdict` 置 pass（**本收口未代签**）。
4. 可选：标题含「文档解析」而实测为「整页文字转录」，是否收敛副标题属发布决策，未擅改。
