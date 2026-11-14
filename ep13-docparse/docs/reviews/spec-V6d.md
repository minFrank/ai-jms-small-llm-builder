# ep13 文档解析系列 · 测试方案 + 内容运营平台扩展 规格 V6d（2026-11-04 · 代码设计交叉评审驱动）

> **V6d-errata（2026-11-04 · dsh-r2 驱动）**：S_ALL=156+S_PDF；F-01 上限 1872；成功率两层单位冻结（complete_cell_rate 149/137 cell 级 + engine_success_rate rep 级逐引擎 95%/25/23）；非量化即 A 层。
> **V6d 修订（相对 V6c）**：① lineup 改「6 跑 + 2 归档 N/A」（P0 实证 Tele/dots CPU 不可行）；② sets expected 按 6 引擎重算 S26=156/S24=144；③ 95% 最小样本量重算（总量口径 S26≥149、S24≥137）；④ reps 预算 S26=1872；⑤ surya 参数回填 0.69B、dots 更正 1.7B（官方 README 原文）。依据：dsh-code-r1b 评审 C-11/C-34。

日期：2026-11-03 · **V6d** · 状态：**dsh 方案六轮终判「可开工」（已由代码设计 r1–r4 评审接续，r4 判「可开工」2026-11-04）✅；新增 §4.6 强关联+一键清理；P0 开跑**
**唯一权威源**：本 md；HTML 为渲染副本，改后跑跨文件断言同步（禁单边改）。
期号：ep13/14/15（11-10/11-17/11-24）；横评 ep16–19（12-01 起）；旧稿已废止。
**收敛框架（与 dsh 约定）**：过关 = ①无 P0 ②P1 不含方向/架构级（方向四项——8 引擎名单、指标分层、口径铁律、流程闸门——已两轮确认不再动）③P2 与「实现期自然解决」类不阻塞。

## 0. 期号与路径

| 期 | 日期 | 内容 | 目录 | 控制目录（唯一）|
|---|---|---|---|---|
| ep13 | 2026-11-10 | 专用模型 8 引擎 | `D:/study/ai-jms/ep13-docparse/` | `ep13-docparse/control/` |
| ep14/ep15 | 11-17/11-24 | 框架 3 / VLM 5 | 届时建 | 同规则 |
| ep16–19 | 12-01 起 | LLM 横评（排期表/JSON 已改）| 不动 | 不动 |

## 1. 拍板记录

D1=**C** 挤占 ep13–15 ✅ · D2–D7 全 A ✅ · **P-1=A** 主榜 26 图文字提取、PDF+结构入附录 · **P-2=A** 全精度/量化分层、层内排名、推理参数固定 · **P-3=A** 成功率先行 <95% 不排名。

---

## 2. 测试方案（ep13）

### 2.1 被测、lineup 与样本集

**实跑 6 引擎**：OXR、Xiaomi-OCR-0、PaddleOCR-VL-1.6、OvisOCR2、MonkeyOCR-pro-1.2B、surya-2.5。**归档 2 引擎（N/A 不参与）**：TeleOCR、dots.ocr——P0 复活流程 16 项实验证实 CPU transformers 直载不可行，官方主路径需 vLLM/GPU（归档 JSON：runs/p0_tele_verdict.json、runs/p0_dots_verdict.json）。lineup 外部参照表仍保留 8 行（测没测都可参照）。

**lineup（外部参照表，F-21：OmniDocBench v1.6 分数是该榜 overall 口径，与本测 CER 非同指标——只作背景参照，禁止与本测名次同表合并；as-of 2026-11-03，未列=N/A，厂商宣称标「宣称」）**：

| 引擎 | 参数 | v1.6 overall | 热度 as-of | 出处 |
|---|---|---|---|---|
| OXR | 1.3B | N/A（官方宣称三榜第一）| 3k★/HF 3.8k↓ | github.com/SoMarkAI/OXR |
| TeleOCR | 1.2B | **96.87（榜内最高）** | HF 25.4k↓/1316♥ | HF XingChen-AGI/TeleOCR |
| Xiaomi-OCR-0 | 0.8B | 96.83 | HF 18.5k+GGUF 24.9k↓ | HF xiaomi-research/Xiaomi-OCR-0 |
| OvisOCR2 | 0.8B | 96.58 | HF 84k↓ | HF ATH-MaaS/OvisOCR2 |
| PaddleOCR-VL-1.6 | 0.9B | 96.33（旧文 96.34 作废）| HF 87k↓ | HF PaddlePaddle/PaddleOCR-VL-1.6 |
| MonkeyOCR pro | 1.2B | N/A（宣称中文超自家 3B 版 7.4%）| 6.6k★ | github.com/Yuliang-Liu/MonkeyOCR |
| surya-2.5 | **0.69B**（P0 实算 safetensors 张量）| N/A | 21.6k★ | github.com/datalab-to/surya；HF datalab-to/surya-ocr-2.5 |
| dots.ocr | 1.7B（官方 README 原文「compact 1.7B LLM」；原 3B 作废）| 90.8 | 9.2k★ | github.com/rednote-hilab/dots.ocr |

**样本集 `sets.yaml`（唯一分母；N-04/F-06 闭环）**：

| 集 | 成员 | expected_cells（6 引擎，V6d 重算）|
|---|---|---|
| S26 | 26 图 | **156**（26×6）|
| **S24**（主榜）| 26 图去 † 两张 | **144**（24×6）|
| S_PDF | 试卷 1–2 + 公开文档 1，**page-level**（成员=页，写入 sets.yaml）| = 页数 × 引擎数 |
| S_ALL | S26 ∪ S_PDF 成员表（**展示视图，不产生 cell.set=S_ALL**）| **156** + S_PDF（V6d-errata：原 208 为 8 引擎残留）|

- reps 预算（F-01+X-01）：**target 6 → 超阈扩展至 12，两阶段封顶**；S26 总 reps 上限 156×12=**1872**、S24=144×12=**1728**（V6d 按 6 引擎重算；工期分母按此，按 P0 实测吞吐重算）
- **输入 `InputRef{kind:image|pdf, path, page_no, dpi, sha256}`**（N-05）：主榜统一 300 DPI 页图；原生 PDF 直喂为独立 tier（`supports_native_pdf`，跑不了删 tier 改宣称）；cell 落 `input.kind/page_no/sha256`（命名全仓统一为 `input.*`）

### 2.2 指标与口径

| 指标 | 规则 |
|---|---|
| 可行性 | 三级 + 官方推荐 vs 本测配置；P0 判据 §2.4 |
| **成功率（先行）** | **分两层（F-02）**：`cell_success_rate = n_valid/n_attempt`（仅展示）；`engine_success_rate = Σn_valid/Σn_attempt`（按 engine×layer×set×run）；**成功率两层定义（V6d-errata 冻结单位，R2-04）**：
- **层1 complete_cell_rate = complete 格数 / expected**：S26 ≥ **149**（=156×95% 上取整）、S24 ≥ **137**——**这是 cell 级下限**；
- **层2 engine_success_rate = Σn_valid / Σn_attempt（rep 级）**：逐引擎 ≥95%；**逐引擎 cell 级参考线：S26 每引擎 ≥25 cells、S24 ≥23 cells（=26/24×95% 上取整，cell 单位非 rep）**；
- G1 **两层都查**；日志与聚合字段必须带单位（`_cells` / `_reps` 后缀）；`ranking_eligible` 只存 engine/aggregate，cell 不存 |
| 正文 CER | 同一提取脚本（§3.3）；(S+D+I)/N；valid rep 的 `cer_median` 入 cell |
| 端到端耗时 | `wall_median + wall_iqr + n_valid`（F-04：median 指标名写死 wall）；warmup_reps=1 不计入 |
| 内存 | 进程树 0.2s + 服务型按 PID/端口（`rss_scope={pids,ports,sampler,interval}` 落盘）；teardown 后跨引擎 assert 回落 |
| 结构/表格 | 附录案例（P-1）|

**重复次数预注册（F-01 协议 A，全仓同一组数）**：
`target_valid=6`；`initial_max_attempts=8`；**IQR/median>10% → `extension_target=12`（扩展期内 max_attempts=12）**；**unstable 口径冻结（R2-10）**：`n_attempt 达 12（attempt 硬终止）且 n_valid≥6 且 valid walls 的 IQR/median>10%` → `unstable:true` 只报分布不排名（与 done 同句；6valid/6fail 场景 valid walls=6 个仍按此判，A⑤ 单测固化）；`n_valid<4` → cell `status=failed`；`4≤n_valid<6` → `status=partial`（进分母、不进名次统计、单列）；median≤0 → 报错。
**两阶段即封顶（X-01）：`max_attempts` 初值 8，触发扩展后变 12，没有 16。**
`cell.done := (n_valid≥6 且 IQR 合格) 或 n_attempt ≥ max_attempts(8 或 12) 或 fatal`——**max_attempts 是硬终止，任何阶段到点即停**。
依据 PyTorch `adaptive_autorange` 的 `iqr/median < threshold`（官方原文）。

**计时口径铁律**：加载外置、自报同格对账差>10% 双注、caliber audit 跑测前后各一次（§4.5 G1）。

### 2.3 分层与推理参数（P-2）

> **V6d-errata（R2-19 冻结）**：**非量化（fp32 / bf16）即 A 层，量化（int8/4bit/GGUF 等）即 B 层**——OXR/Paddle/Xiaomi(fp32)/Ovis/Monkey/surya 六引擎全为 A 层；engines.yaml 与 aggregate、G1 按此执行。
A 层全精度 / B 层量化；层内排名；aggregate **必带 `layer`**。固定 batch=1、并发=1、greedy、max_new_tokens 上限 + `trunc_rate` 入 cell。

### 2.4 P0 判据（七条）
① 非空 UTF-8 含 markdown ② 长度>类型下限 ③ 单页 CER<60% ④ 两次输出一致或有解释 ⑤ cold/内存/超时有记录 ⑥ LICENSE+来源已登记 ⑦ 磁盘≥模型总和+10GB。工期按 rep 吞吐重算。

### 2.5 受控环境（N-11）
host manifest：CPU/内存/OS/Python/线程/电源/负载 + **GPU 段（无卡记 `gpu:none`）**；OMP/MKL 固定；idle guard；热降频阈值 + `outlier{reason,action}` + 聚合报 `n_excluded`。

---

## 3. 代码设计

### 3.1 进程架构
runner 单进程调度；每引擎独立 venv 子进程（JSON IPC）；退出核 RSS 回落 + 端口释放。

### 3.2 cell schema（F-03/F-04：真 schema 文件 + 主键修正）

**主键与路径（F-03）**：
- `cell_key = <sample_id>__<engine>__p<page>`（**不含 run_id**；图片 page 固定 1）
- 文件 `cells/<run_id>/<cell_key>.json`（run 只一层，不双套）
- API `GET /api/cells?run_id=&cell_key=`（query，不走 path 参数避免 `/`）

**schema 要素（实现为 `schema/cell.schema.json`，required/type/enum 齐全；写入与聚合两侧 validate，schema 版本+hash 入 session）**：

```
required: [schema, run_id, cell_key, engine, layer, sample_id, set, input, reps,
           target_valid, max_attempts, n_attempt, n_valid, n_fail, status,
           wall_median, wall_iqr, fingerprint, err]
enum:
  status: [complete, partial, failed, skipped]        # F-04 四态
  rep.status: [ok, fail, timeout, skipped]
  layer: [A, B]
  input.kind: [image, pdf]
nullable: [wall_median, wall_iqr, cer_median, err_kind]（failed/skipped 可空）
```

```json
{
  "schema": 6, "run_id": "r-a1", "cell_key": "<uuid>__oxr__p1",
  "engine": "oxr", "layer": "A", "sample_id": "uuid", "set": "S24",
  "input": {"kind":"image","sha256":"...","page_no":1,"dpi":300},
  "reps": [{"n":1,"attempt":1,"status":"ok","wall":2.71,"wall_self":2.6,
            "cer":1.8,"truncated":false,"err_kind":null,"ts":"..."}],
  "target_valid": 6, "max_attempts": 8, "n_attempt": 6, "n_valid": 6, "n_fail": 0,
  "status": "complete", "cell_success_rate": 1.0, "trunc_rate": 0.0,
  "wall_median": 2.71, "wall_iqr": 0.04, "cer_median": 1.8,
  "unstable": false, "engine_session_id": "r-a1/oxr", "peak_rss_mb": 1420,
  "rss_scope": {"pids":[...],"ports":[...],"sampler":"tree+port","interval":0.2},
  "fingerprint": {"git":"...","weights_sha":"...","deps":"...","config_hash":"...",
                  "extract_v":"...","gt_v":"...","gt_hash":"...",   // F-08 加 gt_hash
                  "sample_sha":"...","engine_version":"...","host_manifest_id":"...",
                  "seed":42,"order":7},
  "err": null
}
```
（`ranking_eligible` 不在 cell——F-02）

### 3.3 提取脚本 contract（R-10）
`EXTRACTION_CONTRACT.md` 五类规则 + golden 单测 → 盲审冻结 → `extract_version` 入 fingerprint；GT 归一化独立。

### 3.4 GT 签核（F-08/F-09：单一真源）

- **唯一真源 `gt/<uuid>/manifest.json`**：`{version, hash, status:draft|signed, reviewer, signed_at, supersedes, reason}`（F-09：sample manifest 只存 `gt_current_version` 引用，不存 status/hash）
- API：`POST …/gt/sign`、`…/gt/revoke`（revoke → 回 draft，写审计）；**任何 PUT 生成新 version、置 draft、清签**
- runner 启动：读 GT manifest，校验 `status=signed 且 version+hash == run manifest 冻结值`，不符拒跑
- **cell 记 `gt_v + gt_hash`**（F-08：Gate 0 才能逐 cell 比对当前签名）

### 3.5 runner 健壮性（F-05/F-11 修正）

```python
try:
    while not cell.done:                        # F-13：rep 循环内不查控制
        ...
finally:
    cell.save_raw()          # F-05：先落盘（status/err_kind 先写，永不因校验丢失）
    try:   validate_schema(cell)
    except SchemaErr as e:   cell.schema_err = str(e); cell.save_raw()   # 校验失败也留痕
```
- **CellFatal**（输入坏）→ status=failed、继续下一格；**WorkerFatal** → respawn（预算 1 次/引擎/小时，超则引擎 session 标 unavailable）
- GT 未签/不符也**创建 cell**（`status=skipped, err_kind=gt_unsigned|gt_mismatch`）——F-11：跳过必留痕，缺格清单可区分
- journal 每 rep 追加；retry 有界（1 次+退避）
- `cell.done` 定义见 §2.2（F-01）

### 3.6 目录结构

```
ep13-docparse/
├── engines.yaml · sets.yaml · schema/cell.schema.json
├── engine_base_ep13.py · engine_worker.py · runner.py · ipc.py
├── extract_text.py · EXTRACTION_CONTRACT.md · cer.py · agg.py · validate_schema.py
├── control/task.json + flags + heartbeat          # 唯一控制目录（§4.1 字段）
├── samples/manifest.json（uuid/filename/hash/sets[]/pages[]/gt_current_version/status）
├── samples/SOURCES.md
├── gt/<uuid>.md + gt/<uuid>/manifest.json + gt_versions/…
├── cells/<run_id>/<cell_key>.json
├── sessions/<run_id>.json   # fingerprint + stats_policy_hash + host_manifest_id + 冻结的 sets/gt 版本
├── sessions/engines/<run_id>/<engine>.json        # cold_load_s 会话级（F-12/X-02：含 run_id，不跨 run 覆盖）
├── runs/<run_id>/host_manifest.json + tail.log + audit/
├── venvs/ · models/ · pdfs/ + pdfs/pages_300dpi/ · _figs.py
```

### 3.7 引擎接口（N-05/F-20）

```python
class DocParseEngine:
    name: str; layer: str; supports_native_pdf: bool
    def available(self) -> tuple[bool, str]
    def load(self) -> float                    # 返回值接线 → sessions/engines/<run_id>/<engine>.json（F-12/X-02）
    def infer(self, inp: InputRef) -> dict     # {"markdown","wall_self","extra","truncated"}
    def teardown(self) -> dict                 # 杀 daemon/释放端口 → {"rss_after_mb": n}（F-20：返回值必须接线）
# infer 内禁止隐式加载；warmup_reps=1 不计入
```
主循环：`try: ... finally: rpc(teardown) → assert returned rss_after 回落`（F-20）

### 3.8 runner 主循环（F-11/F-12/F-13 修正）

```python
hb = start_heartbeat(control/, interval=5, process="independent")   # 独立进程（F-14）
run_manifest = freeze(run_id, set=CLI 参数, sets_yaml_hash, gt_versions)   # F-11：set 来自 run，不写死
for engine in seeded(engines, seed):            # seed/order 写入 run_manifest（F-17 固定字段）
    w = spawn_worker(engine)
    cold = rpc(w, "load"); write_session_engine(run_id, engine, cold)      # F-12 接线
    for sample in manifest.active_in(sets.yaml[run_manifest.set]):
        cell = Cell(run_id, sample, engine, input=sample.ref())
        if not gt_ok(sample, run_manifest):     # 校验 version+hash（F-11）
            cell.status="skipped"; cell.err_kind="gt_unsigned|gt_mismatch"
            cell.save_raw(); continue            # 跳过也落盘
        try:
            while not cell.done:
                ...infer/retry/fatal 分支（§3.5）          # F-13：循环内不查控制
        finally:
            cell.save_raw(); validate_soft(cell)
        if control_desired() in ("pause","stop","restart"):  # 格边界：本 cell 已落盘
            ack_and_wait_or_exit()                           # 停在格边界，run 态落 paused/stopped
    r = rpc(w, "teardown"); assert r["rss_after_mb"] <= baseline      # F-20
write_heartbeat_final()
```

### 3.9 IPC 协议（F-19 补 chunk）

- **NDJSON** 走 worker stdout 专用 fd；引擎 print/warning → stderr/日志文件
- 请求 `{v:1, id, cmd, args}`；响应 `{v:1, id, ok, result|error:{code,retryable,msg}}`
- 握手 `hello{protocol_v, engine, pid}`；**单飞**（一问一答；超时 kill+respawn、丢弃迟到响应；respawn 预算见 §3.5）
- **大消息分块**：`{v:1, id, chunk:0, n:3, data:"..."}` … `{chunk:2, n:3, final:true, sha256:"..."}`，接收方按 id 聚合校验后应答
- 每命令独立 timeout（load/infer/teardown 各自上限写死 engines.yaml）

---

## 4. 平台扩展（content-admin 增量）

### 4.1 状态机（F-13~F-16 重写）

**状态**：`idle → running ⇄ pausing → paused → restarting → running`；`→ stopping → stopped`；异常 → `failed`（**终态，恢复=显式 `POST /api/runs/{id}/reset → idle` 后重新 start**）
**健康（独立维度）**：`alive | stale`——**stale 判据（F-14）：连续 15s 无 heartbeat，或 last_progress 超过单格 timeout；同时做进程存在性检查（owner_pid 活着则标 `stalled` 不直接判死）**

| 事件 | 当前态 | 目标态 | guard |
|---|---|---|---|
| **start（F-16）** | idle / stopped | **running** | `POST /api/runs`（create+start 一体，带 set/run_id）；校验 sets/GT/磁盘 |
| pause | running | pausing→paused | runner 在 **sample 边界**（cell 已落盘后）ack；**paused 是 run 级状态，不产生 cell 状态**（F-13）|
| resume | paused | running | 清 desired，下一格恢复 |
| restart | running/paused | restarting→running | 格边界退出，supervisor 按 exit code 拉起并清 flag |
| stop | 任意非终态 | stopping→stopped | 二次确认；stop/crash 由 exit code 区分 |
| crash | running | failed | heartbeat 消失 + 进程不存在 |
| reset（F-16） | failed/stopped | idle | 显式端点，写审计 |

- `control/task.json`：`state, state_seq, desired_state, ack_seq, owner_pid, lease{token,expires_at,renewed_at}, heartbeat_at, run_id, attempt, finished_at, updated_by`
- **lease（F-15）**：TTL 60s、**heartbeat 时自动续期**；所有控制写操作校验 token+epoch（旧 runner 失效）；手动解锁走同 token 校验——替代旧「5 分钟锁」
- flag/状态文件 **tmp+rename 原子写**；API 只写 desired，**runner ack（ack_seq++）后 UI 才显目标态**
- heartbeat 独立进程每 5s（不被推理阻塞）

### 4.2 样本与 GT
UUID 主键、软删、有 cells/跑测中禁删且永不引导删 cells、`samples/SOURCES.md` 唯一（ep12 26 张回填，缺→「待补」）、GT 版本 `version+uuid`、PUT `If-Match` 409、回滚记 actor/reason、**PUT 即清签**。（F-18：§4.2 历史沿革引用更正为 R-20，无 N-20）

### 4.3 数据与审计
D2 只切 S24/S26/S_PDF/S_ALL 显 N；aggregate 必带 `layer` 与 `run_id`，返回 `engine_success_rate/n_valid/ranking_eligible/unstable_list`，`ranking_eligible=false` 不出名次；cells 支持 run_id/cell_key 过滤+分页；口径审计异步 job（job_id+轮询+inputs hash 缓存）。

### 4.4 API 端点表（F-16 补 start）

`POST /api/runs`（create+start：带 set/run_id，执行前置校验）· `GET /api/runs` · `POST /api/runs/{id}/pause|resume|restart|stop|reset`（写 desired_state）· `GET /api/runs/{id}/log` · `GET/POST /api/samples` · `POST /api/samples/{id}/archive` · `GET/PUT /api/samples/{id}/gt` · `POST /api/samples/{id}/gt/sign|revoke` · `GET /api/samples/{id}/gt-versions` · `POST /api/samples/{id}/gt/rollback {version}` · `GET /api/cells?run_id=&cell_key=&set=&engine=&layer=`（F-03：query）· `GET /api/aggregate?run_id=&set=&layer=` · `POST /api/audit/caliber` · `GET /api/audit/{job_id}` · `GET /api/export?…`
**开工前置**：读现有 `routers/bench.py` `POST /{bid}/runs` 语义，结论写回本文再动代码（Q1）。

### 4.5 发布闸门（F-10：四门齐定义）

| 门 | 名称 | 判据（全过）| 产物 |
|---|---|---|---|
| **G0** | 数据完整性 | 按 **run_id 作用域**（F-06）：**分母四态全计** `complete+partial+failed+skipped == expected(run,set)`（F-07）；② **只约束 complete cell `n_valid≥6`**（partial 本就 4–5 valid，单列数量与清单、不进名次、**不致 G0 失败**，G1 确保其不产排名）；**failed/expected ≤2%**；skipped 按 err_kind 单列；GT 逐 cell `gt_v+gt_hash == 当前 signed manifest`（F-08）；**SOURCES 无「待补」**；一致性矩阵按字段分组：全 run 相同 `{extract_v, config_hash}`、逐引擎相同 `{weights_sha, engine_version}`、逐样本相同 `sample_sha/gt_hash`，**seed/order 为 run 冻结值不参与随机性检查**（F-17）；caliber audit `passed` 且 `finished_at>run.started_at` | gate0.json |
| **G1** | 指标与排名 | caliber audit 字段 `{wall_median,self_median,diff_pct,load_in_wall,note}` 逐引擎；无 `diff_pct>10` 未注；`unstable` 引擎已移出名次；engine_success_rate≥95% 且最小样本量达标才 `ranking_eligible` | gate1.json |
| **G2** | 宣称与 lineup | lineup 仅作外部参照、**不与本测名次同表**（F-21）；「宣称」标注在位；热度 as-of 在位；surya 参数已回填或该行标「未核」 | gate2.json |
| **G3** | 发布 | pre_push_check 10 项 + original_guard + 你终审 | gate3.json |

**四态**：`pass/fail/not_run/stale`，not_run 与 stale 同样阻断；期详情聚合 G0–G3 一行。

### 4.6 期资产强关联与一键清理（2026-11-03 用户要求）

**强关联（每期自包含、可追溯）**：
- 期目录 = 代码 + 配置 + 数据 + 产物的**唯一容器**（`ep13-docparse/` 下 `engines.yaml/sets.yaml/control/cells/runs/sessions/samples/gt` 全在内）
- 期根 `EPISODE.json`：`{episode:"ep13", date, code_git, spec_version:"V6d", sets_hash, created}`
- 每个数据文件（cell/run/session/task）必带 `run_id`，`run_id` 必带期号前缀（如 `ep13-r-a1`）——**从任一数据文件可反查到期、代码版本、spec 版本**
- 配置文件哈希写入 run manifest（sets_hash/config_hash），配置改动可被 Gate 0 一致性矩阵发现

**一键清理 `scripts/clean_episode.py <episode>`**：
```
python scripts/clean_episode.py ep13              # dry-run：列出将删内容+总大小，不删
python scripts/clean_episode.py ep13 --data       # 清数据与产物：cells/ runs/ sessions/ control/ outputs/ audit/
                                                  #   （保留代码、engines.yaml、sets.yaml、samples/、gt/、MANIFEST）
python scripts/clean_episode.py ep13 --config     # 清配置与控制态（保留数据；危险，仅重跑前用）
python scripts/clean_episode.py ep13 --models     # 才动 D:/models/models/ocr/ep13-docparse/ 模型（默认永不删）
```
- 确认机制：`--data` 需输入期号回车确认；执行前自动打包数据为 `archive/ep13-<ts>.tar.zst`（可选 `--no-archive`）
- 审计：每次清理写 `CLEANUP.log`（who/when/what/size/archive 路径）
- 模型是跨期共享资产：**默认清理绝不碰模型目录**，必须显式 `--models`

---

## 5. 流程

期号冻结 → **你过目 V6** → **dsh 第四轮（末轮，收敛框架见头部）** → 判定过关 → P0（§2.4）→ 按 rep 吞吐重算工期报你 → 预跑 → 全量 → G0–G3 → 你终审 → 推。
平台第一期与 P0 并行的前提 = 末轮过关。

## 6. 闭环清单

**R-01~25（第一轮）** ✅ 全处置（存档于评审稿 V5 摘要）。
**N-01~15（第二轮）** ✅ 全处置（上一版 V5 §6）。
**F-01~21（第三轮，本文落地）**：

| # | 级 | 问题 | 处置 |
|---|---|---|---|
| F-01 | P0 | 8 次上限与「加跑到 12」互斥 | ✅ §2.2 协议 A：target6/初限8/扩展12 两阶段封顶（X-01 后删 16）、done 含 max_attempts 硬终止、partial 态、上限 1872 |
| F-02 | P1 | 成功率分母层级 | ✅ §2.2 cell 仅展示 / engine 级 95%+最小样本量 / eligible 只在 engine |
| F-03 | P1 | 双 run_id、API path 含 / | ✅ §3.2 cell_key 不含 run、路径一层、API 走 query |
| F-04 | P1 | schema 是实例非 schema | ✅ §3.2 required/enum/nullable 明示、四态 status、wall_median/cer_median 命名 |
| F-05 | P1 | validate 先于 save 失败格丢 | ✅ §3.5 save_raw 先行、validate 失败留痕 |
| F-06 | P1 | Gate 0 无 run 作用域 | ✅ §4.5 G0 按 run_id、expected(run,set) 冻结 |
| F-07 | P1 | G0 ①②③ 互斥 | ✅ 分母四态全计（complete+partial+failed+skipped）、②只约束 complete、③=failed/expected、partial 单列 |
| F-08 | P1 | GT 校验缺 hash | ✅ cell 加 gt_hash、G0 逐 cell 比对、SOURCES 入 G0 |
| F-09 | P1 | GT 双源 | ✅ §3.4 唯一真源 gt manifest，sample 只存引用 |
| F-10 | P1 | Gate 1/2/3 不存在 | ✅ §4.5 G0–G3 全定义 |
| F-11 | P1 | 写死 S24、skip 不留痕 | ✅ §3.8 set 来自 run manifest、GT 问题也建 skipped cell |
| F-12 | P1 | cold_load 没接线 | ✅ §3.6/3.8 load 返回值写会话文件（含 run_id）|
| F-13 | P1 | pause 检查在 rep 循环 | ✅ §3.5/3.8 sample 边界（cell 落盘后）检查+ack |
| F-14 | P1 | stale 判据不可靠 | ✅ §4.1 15s/单格超时双判 + 进程存在性 |
| F-15 | P1 | lease 不续期无 fencing | ✅ §4.1 TTL60s+心跳续期+token/epoch 校验 |
| F-16 | P1 | 无 start 转场/端点 | ✅ §4.1 start/reset 行 + §4.4 `POST /api/runs` |
| F-17 | P1 | 一致性字段不全 | ✅ §4.5 G0 分组一致性矩阵、seed/order 冻结不查随机 |
| F-18 | P2 | 文档双源/N-20 笔误 | ✅ 头部权威源声明 + §4.2 引用更正为 R-20 |
| F-19 | P2 | IPC chunk 未定义 | ✅ §3.9 分块 schema+sha256+per-command timeout |
| F-20 | P2 | teardown 返回值没用 | ✅ §3.7/3.8 rss_after 接线 + finally |
| F-21 | P2 | lineup 分数与 CER 不同指标 | ✅ §2.1 标注「外部参照，禁止与本测名次同表」 |
| X-01 | P1 | done 缺 max_attempts 终止（第四轮新）| ✅ §2.2 done 补 `n_attempt≥max_attempts`，删 16 层 |
| X-02 | P1 | cold 路径缺 run_id（第四轮新）| ✅ §3.6 `sessions/engines/<run_id>/<engine>.json` |
| F-07 复核 | 假闭环 | G0 分母漏 partial | ✅ §4.5 四态全计分母 + ②只约束 complete |
| F-13 复核 | 假闭环 | pause 检查仍在 rep 循环 | ✅ §3.5/3.8 移至 sample 边界，删 paused_boundary |

**遗留**：surya 参数（P0 回填）；横评方案文件名历史保留。
