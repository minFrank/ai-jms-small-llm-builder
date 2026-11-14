# ep13 正式跑测 · 实测代码设计 v2

v2 ｜ 2026-11-04 ｜ 依据：dsh-code-r1b 交叉评审 37 条（P0×11 / P1×22 / X×4）逐条处置 + 规格升 V6d

状态：待你评审（r1 判定「需大改」，v2 按 9 条必改清单重写）

v2 改了什么（一句话）：r1 把引擎适配写了主体、数据契约用伪代码带过；v2 反过来——第一层就是协议 A + cell schema + G0–G3 + 分母（与权威源逐字段对齐），引擎层降为第二层（r1 已评为强项，只补进程模型）。规格已同步升 V6d（6 引擎分母/阈值/预算先行落地，消解 C-11/C-34）。

目录

- 对 r1 37 条的处置映射（全闭环）
- 第一层 · 协议 A 显式状态机（C-01/02/03/05/06）
- 第一层 · cell schema v6（C-07/08/09/17/18）
- 第一层 · G0–G3 四门（C-10/12/22/26）
- 第一层 · 分母与预算（V6d 已落地，C-11/31）
- 第二层 · 进程架构：runner + venv worker + NDJSON（C-13/14/15/16）
- 第二层 · GT 签核与提取 contract（C-21/23）
- 第二层 · 计时口径与受控环境（C-18/19/24/25）
- 第三层 · 资产追溯与一键清理（C-27/28/29/30/33）
- 决策冻结（C-34/35/36）与执行流程
- 附录 · 引擎层（r1 保留项 + 补充）

## 0. 对 r1 37 条的处置映射（dsh 要求可闭环，全表）

| 条目 | 处置 | 落在 v2 哪里 |
|---|---|---|
| P0×11：C-01~C-11 | 全部接受 | C-01/02/03/05/06→§1；C-04→§2；C-07/08/09→§2；C-10→§3；C-11→§4（V6d 已改） |
| P1×22：C-12~C-33 | 21 条接受；C-18 部分修正（见下） | C-12/22/26→§3；C-13/14/15/16→§5；C-17/18/19/20/24/25→§2/§7；C-21/23→§6；C-27/28/29/30/33→§8；C-31→§4；C-32→§10 |
| C-18 wall 口径 | 接受但需你拍板：v2 按规格定义 wall=infer 全程（含预处理）、load 外置、OXR 含 D-FINE——这意味着 r1 设计的「纯 generate」作废，P0 已报的单页秒数在正式跑测按新口径重测（P0 数字仅作可行性参考） | §7 |
| X×4：C-34/35/36/37 | 全接受 | C-34→V6d 已改+§9；C-35/36→§9 决策冻结；C-37→本稿结构本身 |

## 1. 第一层 · 协议 A 显式状态机（重写 r1 伪代码）

权威源 §2.2（F-01/X-01）：target_valid=6；initial_max_attempts=8；IQR/median&gt;10% → 扩展至 12；12 次有效仍&gt;10% → unstable；n_valid&lt;4 → failed；4≤n_valid&lt;6 → partial；median≤0 → 报错；max_attempts 硬终止。

```
class CellRunner:                       # C-01/C-02/C-03 修复
    n_attempt = 0;  n_valid = 0        # ★两个计数分离——失败/超时也占 attempt
    max_attempts = 8;  extension = False
    walls = [];  reps = [];  fatal = None

    def run(self):
        while True:                     # 出口只有三个，全失败也必出
            if fatal: break             # ① CellFatal
            if n_attempt &gt;= max_attempts: break   # ② 硬终止（8 或 12）
            n_attempt += 1
            rep = worker.infer(timeout=T_INFER)    # 父进程计时，超时 kill+respawn(§5)
            reps.append(rep)            # status ∈ ok|fail|timeout|skipped 全入账
            if rep.ok:
                n_valid += 1; walls.append(rep.wall)
            # —— 扩展触发（C-01 修复：8→12 显式两阶段）——
            if (not extension and n_attempt &gt;= 8
                    and n_valid &gt;= 6 and iqr_over(walls)):
                extension = True;  max_attempts = 12   # 触发后继续跑到 12
            # —— 达标即停 ——
            if n_valid &gt;= 6 and not iqr_over(walls): break
        return self.finish()

    def finish(self):                   # C-03 四种收尾（规格 §2.2 原文）
        if fatal:                return status="failed",  err_kind=fatal
        if n_valid &lt; 4:          return status="failed"
        if 4 &lt;= n_valid &lt; 6:     return status="partial"        # 进分母、不进名次、单列
        if median(walls) &lt;= 0:   return status="failed", err="median_le_0"   # 报错留痕
        if iqr_over(walls):      return status="complete", unstable=True    # 12 次仍不稳：只报分布不排名
        return status="complete"

    # 单测三例（dsh 要求）：① 6 次达标即停 ② 8 次仍超阈→max=12 继续 ③ 12 次仍超阈→unstable
```

| C-xx | v2 修复 |
|---|---|
| C-01 死分支 | 8→12 由 extension 显式触发后 max_attempts 变 12 继续跑，删除不可达分支 |
| C-02 valid当attempt | n_attempt 每轮先 +1；失败/超时入 reps 占 attempt；三出口保证全失败不死循环 |
| C-03 四收尾缺失 | finish() 逐条实现 failed/partial/unstable/median≤0；status 严格四态 complete\|partial\|failed\|skipped |
| C-05 控制在格中 | rep 循环内零控制检查；控制检查移到 cell save 之后的格边界（§5 伪代码） |
| C-06 心跳 | 独立心跳进程每 5s 原子写 control/task.json（tmp+rename），与推理解耦；stale=连续15s 无心跳且owner_pid 死亡；pid 活着标 stalled 不判死 |

## 2. 第一层 · cell schema v6（逐字段照权威源 §3.2，不再自创）

C-04 修复（F-05）：save_raw 先行，validate 后置——`finally: cell.save_raw(); try: validate(cell) except: cell.schema_err=…; cell.save_raw()`。校验永不作为落盘前置，失败也留原始记录。

```
# 主键与路径（C-07）：
cell_key  = &lt;sample_uuid&gt;__&lt;engine&gt;__p1        # 不含 run_id、无斜杠
文件       cells/&lt;run_id&gt;/&lt;cell_key&gt;.json        # run 只一层（r1 多了 engine 层）
API       GET /api/cells?run_id=&amp;cell_key=      # query 参数
run_id     = ep13-&lt;ts&gt;（一个 run 跑全部 6 引擎，不按引擎拆）
```

| schema 必填（照 §3.2） | 值/说明 |
|---|---|
| required | schema, run_id, cell_key, engine, layer, sample_id, set, input, reps, target_valid, max_attempts, n_attempt, n_valid, n_fail, status, wall_median, wall_iqr, fingerprint, err |
| status enum | complete \| partial \| failed \| skipped（r1 的 done 作废） |
| rep 结构（C-08） | {n, attempt, status∈ok\|fail\|timeout\|skipped, wall, wall_self, cer, truncated, err_kind, ts} |
| 聚合字段 | cell_success_rate, trunc_rate, unstable, engine_session_id, peak_rss_mb, rss_scope{pids,ports,sampler,interval}；ranking_eligible 不在 cell（F-02） |
| input（C-09） | {kind∈image\|pdf, sha256, page_no, dpi} |
| fingerprint（C-09） | {git, weights_sha, deps, config_hash, extract_v, gt_v, gt_hash, sample_sha, engine_version, host_manifest_id, seed, order}——gt_hash 在 fingerprint 内（r1 放顶层作废） |
| cold_load（C-17） | 移出 cell → sessions/engines/&lt;run_id&gt;/&lt;engine&gt;.json（session 级，一次加载一次记录） |
| layer / set（C-20） | layer∈A\|B 每引擎在 engines.yaml 冻结；set∈S26\|S24\|S_PDF 必填 |

实现约束：唯一实现源 `schema/cell.schema.json`（直接从规格 §3.2 生成）；写入侧与聚合侧双 validate；schema 版本+hash 记入 session。r1 的字段表全部作废，以本节为准。

## 3. 第一层 · G0–G3 四门（照权威源 §4.5，删除 r1 自造门号）

| 门 | 判据（照 §4.5 全文执行） | 产物 |
|---|---|---|
| G0 数据完整性（C-10） | 按 run_id 作用域：① 分母四态全计 complete+partial+failed+skipped == expected(run,set)；② 只约束 complete 的 n_valid≥6（partial 单列不致失败）；failed/expected≤2%；skipped 按 err_kind 单列；GT 逐 cell gt_v+gt_hash==signed manifest；SOURCES 无「待补」；一致性按字段分组：全 run 相同 {extract_v, config_hash}、逐引擎相同 {weights_sha, engine_version}、逐样本相同 {sample_sha, gt_hash}、seed/order 为冻结值不参与；caliber audit passed 且 finished_at&gt;run.started_at（不用文件 mtime） | gate0.json |
| G1 指标与排名 | caliber audit 字段 {wall_median, self_median, diff_pct, load_in_wall, note} 逐引擎；无 diff_pct&gt;10 未注；unstable 移出名次；engine_success_rate≥95% 且最小样本量（V6d：S26≥149 / S24≥137）达标才 ranking_eligible | gate1.json |
| G2 宣称与 lineup（C-12 整门补回） | lineup 仅外部参照不与本测同表；「宣称」标注在位；热度 as-of 在位；surya 参数已回填（V6d=0.69B）或标「未核」 | gate2.json |
| G3 发布 | 已有三闸门按规格嵌入本门（pre_push_check 10 项 + original_guard）+ 你终审 | gate3.json |

r1 的「三重前置 + 四门」七门链作废：三闸门不另立门，按规格嵌入 G1（caliber audit）与 G3（pre_push_check/original_guard）。四态 `pass/fail/not_run/stale`，not_run 与 stale 同样阻断；期详情聚合 G0–G3 一行。

C-26 七判据恢复规格原文：②长度&gt;类型下限（非 200 硬编码）③单页 CER&lt;60% ④「或有解释」⑦磁盘 ≥ 模型总和+10GB 跑前做；LICENSE/SOURCES 入 G0 登记，失败阻断非「标注」。

## 4. 第一层 · 分母与预算（规格已升 V6d，先行落地）

| 项 | V6d 值 |
|---|---|
| 实跑阵容 | 6 引擎（OXR/Paddle/Xiaomi/Ovis/Monkey/surya）；Tele、dots 归档 N/A |
| expected_cells | S26=156（26×6）、S24=144（24×6）、S_PDF=页数×6 |
| 95% 最小样本量 | 总量口径 S26≥149 valid、S24≥137 valid（逐引擎参考线 25/23） |
| reps 预算 | S26 上限 156×12=1872、S24=144×12=1728 |
| sets.yaml | 唯一分母文件，跑前冻结 expected_cells 与 sets_yaml_hash 入 run_manifest |

工期（C-31，按 P0 实测吞吐估算）：6 引擎单页实测 60s/161s/241s/993s/308s/983s；warmup+协议 A 期望 ≈7 rep/格（6+1 超阈概率低）→ S26 期望 rep≈1092。按均值 ~350s/rep 估 期望 ≈107 小时；最坏 1872 rep × 最慢引擎占比重加权 ≈ 150–170 小时（分批夜跑）。冒烟先行（D4=B）先拿真实吞吐再出最终排期表。

## 5. 第二层 · 进程架构（r1 缺失的主干，照 §3.1/§3.5/§3.8/§3.9）

```
runner.py（单进程调度，自带 control 状态机）
 ├─ start_heartbeat(control/, interval=5, process="independent")   # C-06 独立心跳
 ├─ run_manifest = freeze(run_id, set=CLI, sets_yaml_hash, gt_versions, seed, order)
 ├─ 每引擎: spawn_worker(engine)                                    # C-13 子进程隔离
 │    └─ 启动于 venvs/&lt;engine&gt;，握手 hello{protocol_v, engine, pid}
 │    └─ NDJSON 走 stdout 专用 fd；引擎日志 → stderr/文件
 │    └─ 单飞一问一答；每命令 timeout 从 engines.yaml 读（load/infer/teardown 各自上限）
 │    └─ 超时: 父进程计时 → kill worker → rep 记 timeout → respawn（预算 1 次/引擎/小时，C-14）
 │    └─ 大消息分块 {v,id,chunk,n,data}…{final,sha256}（markdown 输出可达百 KB）
 ├─ cold = rpc(load) → write_session_engine()                        # C-17 cold 出格
 │    └─ warmup_reps=1 跑一次不记账
 ├─ for sample: cell = CellRunner(...).run() → finally save_raw→validate
 │    └─ CellFatal → status=failed 继续下一格；journal 每 rep 追加（C-15）
 │    └─ 格边界才 control_desired()（pause/stop/restart + ack_seq，C-16）
 └─ rpc(teardown) → assert rss_after≤baseline 且端口释放（C-25）
```

| C-xx | v2 落点 |
|---|---|
| C-13 | runner 单进程 + 每引擎 venv 子进程 + NDJSON 专用 fd + 分块 + 单飞——6 个 venv 的 transformers 版本互斥靠进程隔离成立（r1 进程内直载不成立） |
| C-14 | D2 冻结 30 分钟：写入 engines.yaml 的 timeout.infer=1800、load/teardown 各设；父进程 kill（Python 线程内无法取消，必须进程级）；开跑前做「挂起 1 分钟被杀」演练 |
| C-15 | CellFatal/WorkerFatal 分层、respawn 预算、journal 每 rep 追加、retry 有界（1 次+退避）、try/except/finally 全覆盖 |
| C-16 | control/task.json 全字段状态机：state/state_seq/desired_state/ack_seq/owner_pid/lease{token,expires_at}/heartbeat_at/run_id/attempt/finished_at；lease TTL 60s 续期、fencing、tmp+rename 原子写、restart/reset 语义 |

## 6. 第二层 · GT 签核与提取 contract

| 项 | 做法（C-21/C-23） |
|---|---|
| GT 前置签核 | runner 启动时校验 status=signed 且 version+hash == run_manifest 冻结值，不符拒跑；未签/不符的样本建 status=skipped, err_kind=gt_unsigned\|gt_mismatch 的 cell 并落盘 |
| 提取 contract | 跑测前写 EXTRACTION_CONTRACT.md（五类规则：换行/表格/公式/图片占位/阅读顺序）+ golden 单测（6 引擎各 ≥1 例）→ 盲审 → 冻结 extract_v 入 fingerprint；冻结后禁改 |
| gt_hash 规范化 | 规范化算法（NFC、行尾、尾空白）写死进 contract；gt_v+gt_hash 同入 fingerprint |

## 7. 第二层 · 计时口径与受控环境（C-18/19/24/25）

C-18 wall 口径（r1 作废，按规格重定义，需你确认）：

• wall = 端到端 infer 全程（含图像预处理 + generate + 后处理第一步），load 外置（session 级），warmup 不计入；

• OXR 的 wall 含 D-FINE 版面（端到端语义，版面是其管线第一步）；

• 每 rep 另记 `wall_self`（模型自报/引擎内部分解，能拿到才记）→ 算 `diff_pct` 入 G1 对账；

• caliber audit 跑测前 + 跑测后各一次；

• 后果：P0 的「单页秒数」全部按新口径在正式跑测重测，P0 数字仅作可行性与工期估算参考。

| 项 | 做法 |
|---|---|
| C-19 | 强制 greedy（do_sample=false）、batch=1、并发=1；max_new_tokens 每引擎写死 engines.yaml；trunc_rate 入 cell；prompt 原文+sha256 入 MANIFEST |
| C-24 | 跑前生成 host_manifest.json（cpu=5700G, mem=30GB, os=win11, python 每 venv, threads, gpu:none, power, load）→ id 入 fingerprint；OMP_NUM_THREADS/MKL 固定写死；idle guard（负载&gt;阈值 延迟启动）；热降频记录 outlier{reason,action}；聚合报 n_excluded |
| C-25 | 统一 tree+port 采样（interval=0.2s，含普通引擎）；cell 记 peak_rss_mb/rss_scope；finally rpc teardown + assert rss 回落 + 端口释放 |
| C-32 | 切片判别改显式分支：按 (模型, 是否 inputs_embeds, out 是否含 prompt token ids) 三元组写死分支表，每分支 golden 用例；禁止「智能」字符串启发式；切片前后 sha256/长度入 journal |

## 8. 第三层 · 资产追溯与一键清理（C-27/28/29/30/33）

| 项 | v2 补齐 |
|---|---|
| C-27 资产 | 补 sets.yaml（四集+expected）、engines.yaml（6 引擎 layer/prompt hash/timeout/max_new_tokens/venv 路径）、samples/manifest.json（UUID/sets/sha256/300DPI 页图）、SOURCES.md、pdfs/pages_300dpi/（S_PDF page-level）、InputRef 300DPI+sha256 |
| C-28 清理 | clean_episode 补 --config、期号回车确认、--no-archive、archive/ep13-&lt;ts&gt;.tar.zst、CLEANUP.log 字段 who/when/what/size/archive；--data 明确删除清单（cells/runs/sessions/control/outputs/audit）与白名单保留（scripts/配置/samples/gt/venvs/EPISODE）；模型目录 D:/models/models/ocr/ep13-docparse/ 默认永不删；dry-run 清单单测 |
| C-29 追溯 | EPISODE 补 sets_hash/created/per-engine venv freeze（torch/transformers 版本）；新建 MANIFEST.md 记 config 补丁（P0-PATCH 5 处）、prompt sha256、模型路径；版本字符串统一 V6d（权威文件头已改，r1 的「V6c」引用全部更正） |
| C-30 run_manifest | 启动冻结 set 来源/sets_yaml_hash/gt_versions/seed/order/config_hash/stats_policy_hash → sessions/&lt;run_id&gt;.json；seed+order 入 fingerprint |
| C-33 进程纪律成码 | process_guard.py：单实例 lock、按整串 cmdline 盘点、kill 前 CONFIRM 打印、kill 后 raw socket 验活、端口/RSS 断言；runner 前后调用；clean_episode 复用 |

## 9. 决策冻结与执行流程（C-34/35/36）

已冻结（不再开放）：

D1 → 已由规格 V6d 消解：lineup 已改「6 跑 + 2 归档 N/A」，expected/阈值/预算同步——不再作为决策项。

D2 → 30 分钟/rep，落到 engines.yaml `timeout.infer=1800`，父进程 kill 可中断（含挂起演练）。

D3 → 只留 A：GT 签核+gt_hash 冻结是开跑前置（B 与「未签拒跑」冲突，按 C-35 删除）。

D4 → B：先 3 样本冒烟（最快/最慢/最大图）→ 你确认 cell 格式与数据 → 再全量；冒烟用独立 run_id 不入分母。

| 执行顺序（评审通过后） | 内容 |
|---|---|
| ① 冻结资产 | sets.yaml/engines.yaml/样本 manifest/EXTRACTION_CONTRACT+golden/GT 签核/host_manifest/SOURCES——全部就位才动 runner |
| ② 实现 | schema/cell.schema.json（从 §3.2 生成）→ CellRunner+单测三例 → worker+NDJSON+timeout/respawn → process_guard → 平台四门端点 |
| ③ 闸门自测 | G0–G3 各造一份 fail 样本验证能拦（not_run/stale/failed&gt;2% 分组不一致逐项） |
| ④ 3 样本冒烟 | 独立 run_id；核 cell 全字段/计时口径/超时 kill/落盘校验；报你确认 |
| ⑤ 全量跑测 | 6 引擎 × 分批夜跑；跑前 caliber audit + idle guard；进度按 run_id 实时报 |

## 10. 附录 · 引擎层（r1 §2 保留，仅三处补充）

- 路径 A/B/C 与 P0 全部实证细节原样保留（dsh：「引擎适配细节是强项，v2 不必重写」）；6 引擎 PASS 终表、Tele/dots 归档不变。
- 补充 1：每引擎 engines.yaml 冻结 `layer（A/B 归属）`、`prompt_sha256`、`timeout.{load,infer,teardown}`、`max_new_tokens`——bf16/Xiaomi-fp32 均按「非量化即 A 层」记入（规格 §2.3）。
- 补充 2：worker 启动即打印 `python/torch/transformers` 版本入握手，与 EPISODE venv freeze 对账。
- 补充 3：warmup_reps=1 每引擎 load 后跑一次不记账。

配套：规格 V6d（权威源，已升版）· dsh 评审原文 `review-20261104/dsh-code-r1b-out.txt` · v1 存档 `2026-11-04-…-评审稿.html`。评审意见直接回本会话。