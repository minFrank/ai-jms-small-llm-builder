# ep13 文档解析 · 设计评审知识库（docs/reviews/）

> 用途：设计文档与实现之间的**落地检查**锚点——每条设计都有对应实现位置与勾选状态。
> 规则：评审文档入库后**只增不改**（历史轮次保留原貌）；实现每完成一个里程碑，回本清单勾状态。

## 文档索引

| 文件 | 说明 | 状态 |
|---|---|---|
| `spec-V6d.md` | **唯一权威源**（2026-11-04 升 V6d：6 引擎分母 156/144、门槛 149/137、reps 1872）| 现行 |
| `code-design-v2.html` | 代码设计评审稿 **v2**（按 dsh r1 37 条重写）| **现行，待终审** |
| `code-design-r1.html` | 代码设计 v1（dsh 判「需大改」）| 历史 |
| `input-r1.md` / `input-v2.md` | 送 dsh 评审的输入材料 | 历史/现行 |
| `dsh-r1-review.txt` | dsh 第一轮交叉评审原文（37 条）| 历史 |
| `dsh-r2-review.txt` | dsh 第二轮复评（37 条闭环核验 + R2 新问题）| （出稿后入库）|
| `workflow-diagram.html` | 全流程图（评审/代码执行/数据发布/兜底 四分支）| 现行 |

上游六轮方案评审原文：`D:\study\deepseek-harness\review-20261103\dsh-round{1..6}-out.txt`

## 落地检查清单（设计条款 → 实现位置）

状态：⬜ 未开始 ｜ 🟡 进行中 ｜ ✅ 完成 ｜ ➖ 不适用

### A. 冻结资产（v2 §9 执行顺序 ①）
- ⬜ `sets.yaml`：S26=156 / S24=144 / S_PDF=页数×6 / expected 冻结
- ⬜ `engines.yaml`：6 引擎 × {layer, prompt_sha256, timeout.load/infer/teardown=1800, max_new_tokens, venv 路径}
- ⬜ `samples/manifest.json`：UUID / 300DPI 页图 / sha256 / sets 归属
- ⬜ `EXTRACTION_CONTRACT.md` + golden 单测（6 引擎各 ≥1 例）→ 盲审冻结 `extract_v`
- ⬜ GT 签核：`status=signed` + version/hash 与 run_manifest 对账（未签拒跑）
- ⬜ `host_manifest.json`：cpu/mem/os/python/threads/**gpu:none**/power/load → id 入 fingerprint
- ⬜ `SOURCES.md` 无「待补」

### B. 实现（v2 §9 ②）
- ⬜ `schema/cell.schema.json`：从 spec V6d §3.2 生成；写入+聚合双侧 validate
- ⬜ `CellRunner`：attempt/valid 分离、8→12 extension、四收尾、**单测三例**（6次达标/8次扩展/12次unstable）
- ⬜ `runner.py`：独立 5s 心跳、格边界控制检查、run_manifest 冻结、warmup=1 不记账
- ⬜ worker：venv 子进程 + NDJSON 专用 fd + 握手/单飞/分块 + 每命令 timeout + respawn 预算
- ⬜ `control/task.json` 状态机：state/desired/ack_seq/lease/heartbeat + tmp+rename 原子写
- ⬜ `process_guard.py`：单实例 lock、cmdline 盘点、kill 前 CONFIRM、kill 后 raw socket 验活
- ⬜ `clean_episode.py`：dry-run/--data/--config/--models/--no-archive、白名单、CLEANUP.log 字段齐
- ⬜ 计时：wall=端到端含预处理（OXR 含 D-FINE）、load 外置 session 级、wall_self/diff_pct 入格

### C. 闸门自测（v2 §9 ③）
- ⬜ G0 fail 样本：not_run / stale / failed>2% / 分组不一致 / caliber 未跑 → 各能拦
- ⬜ G1 fail 样本：diff_pct>10 未注 / 成功率<95% / 低于 149|137 → 能拦
- ⬜ G2 fail 样本：lineup 同表 / 宣称缺 / surya 参数未回填 → 能拦
- ⬜ G3 fail 样本：pre_push_check 故意破坏 → 能拦
- ⬜ 超时演练：挂起 1 分钟被父进程 kill → rep 记 timeout

### D. 冒烟与全量（v2 §9 ④⑤）
- ⬜ 3 样本冒烟（最快/最慢/最大图，独立 run_id）→ 报终审人确认 cell 格式
- ⬜ 跑前 caliber audit + idle guard
- ⬜ 全量 6 引擎 × 分批夜跑（进度按 run_id 报）
- ⬜ 跑后 caliber audit → G0–G3 → gate0-3.json

### 修订记录
- 2026-11-04：知识库建立（r1 评审 → v2 + V6d → dsh r2 复评中）


## 附：dsh r4「可开工」实现期 7 盯点（落地检查必查项）

1. WorkerFatal 超预算必须置 cell.fatal（防 n_attempt 不增死循环）
2. timeout 后必须 kill+respawn/丢弃迟到响应（不能只生成 timeout rep）
3. validate_soft 失败按规格 §3.5 重存 schema_err（finally 不能只 save_raw+validate_soft）
4. A⑤ 夹具固定「6 valid 在第 8 次前出现且第 8 次 IQR>10%」；A⑥ 先定 CellFatal 的 err_kind=cell_fatal
5. B 组 3 条 schema 闭合写进 schema：cer_median required（20 项）、failed wall=0 / skipped reps>0 用 if/then 拒、err_kind 枚举含 cell_fatal
6. failed 全 null 与 A⑤/A⑨ 证据口径统一（median≤0 只断言 status/err）
7. G0 LICENSE 归门确认、非法 skip 允许集合={gt_unsigned,gt_mismatch}、S_PDF 多页 cell_key、S_ALL 只做展示 union


## 冒烟准出（规格 V6e §2.2b，2026-11-04 业界对齐版）

- 依据：IEEE 829 §7/§8 → ISO/IEC/IEEE 29119-3、ISTQB 语境；OCR 行业无专门冒烟标准（已查证）
- **A 层 Exit（6）**：①3引擎ok rep ②≥1格complete ③schema validate ④心跳/task/清零 ⑤kill演练不丢格 ⑥吞吐回填 —— 当前 **6/6 全过**（⑤ kill 演练两轮完成：杀→respawn 新 worker→再杀→预算尽 fatal→save_raw 落盘 validate OK→干净退出、不丢格不死循环；演练中修 2 个实现缺口：EOF→WorkerFatal、_read 轮询进程存活防 1800s 卡死）
- **B 层 Entry（2）**：①真实 CER ②S26 manifest —— **2/2 全过（2026-11-04）**：
  - ① gt/sign 已执行（gt_v=ep13-gt-v1、signed、reviewer=user(Frank)、content_hash=5266101978…）+ EXTRACTION_CONTRACT v1 冻结 + CER 链路接入（worker 回传全文→runner 算 (S+D+I)/N）→ **验证格 ep13-b1-cer-verify：complete 6/6、rep CER 全 0.027356、cer_median=0.027356 非 null、validate OK、残留 0**
  - ② samples/manifest.json 冻结 26 张（18 复用+8 合成，GT 全覆盖零缺）
- Suspension/Resumption + 轮次上限 2 轮 + sign-off 报你

---

## 落地状态复核（2026-11-12 收口，只增不改）

### 一处文档矛盾，先说清

上面 A–D 四组清单至今全是 ⬜，但本文件「冒烟准出」段明记 A 层 6/6、B 层 2/2 全过，且 `cells/ep13-full-001/` 已有 156 格全 complete、`gates/` 已产出 G0–G3。原因是本清单建库后**没有按「实现每完成一个里程碑回本清单勾状态」的规则回勾**，属**文档维护缺口，不是实现缺口**。

按本知识库「评审文档入库后只增不改」的规则，**不改动上方任何历史勾选框**，在此补记实际状态与证据位置。

### 实际状态

| 组 | 状态 | 证据 / 说明 |
|---|---|---|
| A 冻结资产 | 大部分 ✅，1 项真缺口 | `sets.yaml` / `engines.yaml` / `samples/manifest.json` / `EXTRACTION_CONTRACT.md` v2 / GT v2 签核 / `SOURCES.md` 均在位且已冻结；`scripts/test_design.py` 覆盖 schema 正反例。**真缺口：`control/host_manifest.json` 不存在** → cell.fingerprint 的 `host_manifest_id="host-1"`、`deps="see-venv"` 是占位值。另 `engines.yaml` 的 xiaomi 模型路径与磁盘目录名不一致（见 `SOURCES.md` 现状更正） |
| B 实现 | 大部分 ✅，1 项待核 | `schema/cell.schema.json`、`cell_runner.py`（协议 A + 单测）、`runner.py`、`worker.py`、`clean_episode.py`、计时 wall/wall_self 均在位；`run_manifest.json` 于 2026-11-12 补入（见 `control/run_manifest.json`）。**`scripts/process_guard.py` 未找到**——单实例 lock / cmdline 盘点 / kill 前后验活可能由 runner 内联实现，待核；冒烟 kill 演练三轮已过（`cells/ep13-smoke-kill-drill{,2,3}`） |
| C 闸门自测 | ✅（含 2026-11-12 修复） | `test_gate_fixtures.py`、`test_denominators.py` 在位；本次另修复 `gate_checks.py` 三处判定缺陷（`diff_pct` 单位不一致恒不触发、`ref=min(25,23)` 使 S26 参考线失效、S24 静默跳过），并重跑 `run_gates.py` 验证 G0/G1/G2 全 pass |
| D 冒烟与全量 | ✅ | 冒烟 3 样本 + kill 演练三轮；全量 156/156 complete、1,023 次 rep；`gates/gate0..3.json` 与 `outputs/` 数据报告已产出 |

### 仍未闭环（发布前须知）

1. `control/host_manifest.json` 缺失 → 主机/依赖版本无法从 cell 反查；`EPISODE.json` 已注明仓库无 commit 可钉。
2. `scripts/process_guard.py` 是否存在待核。
3. G3 仍为 fail，唯一失败项「你终审」=false（本收口未代签）。
4. 成稿已补「九、本期口径与局限」，需按当前稿重跑 md2html 两次渲染对账。

完整偏差台账见 `docs/data_provenance.md`；运行态文件说明见 `control/STATE_NOTES.md`；临时探针索引见 `control/PROBE_INDEX.md`。

### 修订记录（续）

- 2026-11-12：收口复核，补落地状态、门控执行器修复、run_manifest、成稿局限节、数据报告回存 `outputs/`；历史评审原文与勾选框一律未改。
