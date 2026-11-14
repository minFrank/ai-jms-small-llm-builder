# ep13 文档解析 · 正式跑测实测代码设计

评审稿 v1 ｜ 2026-11-04 ｜ 依据：P0 六引擎真实跑通代码 + 规格 V6c §3.6–3.9 ＋ P0 攻坚全部实测教训

状态：待你评审，点头后才执行跑测

目录

- 总体架构与目录
- 引擎层 engine_worker（P0 已验证三路径）
- 主循环 runner（协议 A 落地）
- 数据层 cell schema v6 + 版本指纹
- 判据与四道闸门
- 计时口径三处同步
- 进程纪律与一键清理
- P0 教训 → 设计约束对照表
- 待你拍板的 4 个决策点

设计原则一句话：每一行设计都能指回 P0 的一次真实跑通或一次真实翻车——没有纸面推测。评审通过后按此执行 26 样本 × 6 引擎 × 协议 A 的正式跑测。

## 1. 总体架构与目录

ep13-docparse/
├── EPISODE.json            # 期号/代码git commit/spec版本/数据哈希 ← 强关联锚点（你的新需求）
├── scripts/
│   ├── engine_worker.py    # 引擎层：从 p0_vl_test.py 提取（6 引擎已验证）
│   ├── runner.py           # 主循环：协议A + 状态机 + 心跳
│   ├── extract_text.py     # 统一提取（先人工过 6 引擎输出再冻结，冻结后禁改）
│   ├── clean_episode.py    # 一键清理（dry-run → archive → 删）
│   └── p0_*.py / *.py      # P0 原始脚本保留（复现证据）
├── venvs/&lt;engine&gt;/         # 每引擎独立 venv（P0 实证 5.0/5.1/5.22 互不兼容）
├── control/                # 控制文件单源：start/pause/stop（R-04）
├── cells/&lt;run_id&gt;/          # 每格一文件：&lt;run_id&gt;/&lt;engine&gt;/&lt;sample&gt;.json
├── runs/ sessions/         # 跑测记录、会话日志
├── samples/ gt/ gt_versions/ # 样本与 GT（gt_hash 入格）
├── schema/                 # cell schema v6 + jsonschema
└── CLEANUP.log             # 每次清理留痕

强关联（你的需求）：任一 cell 文件 → `run_id` 含期号 → `EPISODE.json` 记录 git commit / spec 版本 / GT 哈希 → 可反查「这份数据是哪版代码+哪版方案+哪份 GT 产的」。一键清理：`clean_episode.py ep13` 默认 dry-run 列清单+总大小；`--data` 先自动打包 archive 再删；`--models` 显式才碰（跨期共享，默认永不删）；每次写 CLEANUP.log。

## 2. 引擎层 engine_worker（P0 已验证三路径）

### 路径 A：标准 VLM 直载（5 引擎已通）

load:   AutoModelForImageTextToText.from_pretrained(dir, dtype=bf16)  # 官方类；不带 trust_remote_code/low_cpu_mem_usage（Paddle 实证会触发 text_config 错）
        AutoProcessor(use_fast=False)          # 5.x 默认 fast 预处理与训练时不一致（Qwen 系已知坑）
prep:   官方单链 apply_chat_template(tokenize=True, images_kwargs={size})
        失败 → 官方等价拆分链 processor(text=..., images=...)
gen:    inputs.to(dtype=model.dtype)           # 官方 client 明确要求，漏了输出退化（Tele 实证）
        按 prepare ∪ forward 签名过滤多余键     # 照抄 transformers 5.x _validate_model_kwargs（dots 实证 mm_token_type_ids）
        use_cache=True                         # 官方仓 use_cache=False 是缺陷（512tok 要 110 分钟）
        官方 prompt + 官方 sampling，一个不多传  # Tele 教训：自造长句 prompt → spotting 输出
切片:   inputs_embeds 路径智能判别（带 prompt 去 prompt，纯生成直用）# OXR 实证

### 路径 B：OXR 三服务（已通）

D-FINE 版面服务（CPU 0.93s/页）→ OXR 识别（preprocess_inputs → generate，60s/页）
补丁：indicator_token_indices 显式恢复 arange（checkpoint 不含该 buffer）+ eos [151643,151645]

### 路径 C：不可行归档（TeleOCR / dots.ocr）

两引擎复活流程共 16 项实验全部排除（详见 §8 末行），官方主路径为 vLLM/GPU，本机不可行。lineup 中标 N/A 并附归档 JSON 引用，不参与排名、不产数据。未来有 GPU 条件按归档档案直接续。

### 6 引擎阵容（P0 终表）

| 引擎 | 路径 | cold | 单页 wall（P0 实测） | P0 判定 |
|---|---|---|---|---|
| OXR-1.0 | B 三服务 | 8.5s | 60s | PASS |
| PaddleOCR-VL-1.6 | A | 2.1s | 161s/512tok | PASS |
| Xiaomi-OCR-0 | A（fp32） | 4.6s | 241s | PASS |
| OvisOCR2 | A | 2.8s | 993s（qwen3_5 CPU 慢） | PASS |
| Monkey Recognition | A | 3.7s | 308s | PASS |
| surya-ocr-2.5 | A | 2.1s | 983s（qwen3_5 CPU 慢） | PASS |
| TeleOCR | C 归档 | — | — | N/A |
| dots.ocr | C 归档 | — | — | N/A |

注：OXR 版面层 D-FINE 单独计（0.93s/页），OXR 识别 60s/页为整页直喂；正式跑测每格计时以 generate 边界为准（§6）。

## 3. 主循环 runner（协议 A 落地）

for engine in 按 seeded 随机化的顺序:          # seeded：跑测顺序可复现（防顺序偏置）
  for sample in 26 张样本:
    while True:                                # 协议 A 重试环
      检查 control/pause|stop → 格间安全停（当前格跑完才停，R 停止语义 A）
      cell = run_cell(engine, sample)          # 心跳写在 sample 边界（cell 落盘后）
      reps.push(cell)                          # 每 rep: ok/失败原因/截断标记
      n = len(valid_reps)
      if n >= 6:
        if IQR/median &lt;= 10%: break            # 达标
        if n &gt;= 8: break                       # max_attempts 到（协议A：超阈固定加跑至12封顶）
      if n &gt;= 12: break                        # 硬封顶
    落盘 cell（jsonschema 校验在 save 之前）    # F-05：校验失败也留失败记录，不吞格

| 协议 A 参数（规格 §2.2 定稿） | 值 |
|---|---|
| n_target | 6（有效 rep） |
| max_attempts | 8 |
| 超阈规则 | IQR/中位 &gt; 10% → 固定加跑至 12 封顶（初版「或注明」自由裁量已删，R-13 闭环） |
| 停止语义 | 格间安全停（当前格跑完才停）+ start 转场（F-16） |

## 4. 数据层 cell schema v6 + 版本指纹

{
  "cell_id":  "ep13-20261104-143000-oxr/book_01",   # run_id 内嵌期号（N-01 主键唯一）
  "run_id":   "ep13-20261104-143000-oxr",
  "engine":   "oxr", "sample": "book_01",
  "reps": [ {"rep":1, "wall_s":60.1, "ok":true,  "text":"...", "truncated":false},
            {"rep":2, "wall_s":60.2, "ok":false, "fail_reason":"timeout"} ],
  "status":   "done | failed | skipped | partial",   # N-03 失败态显式化
  "gt_hash":  "sha256:...",                          # N-08 入格
  "version":  {"git":"e7431c2", "spec":"V6c",
               "weights_sha":"...", "deps":{"torch":"2.15.0+cpu", ...}},  # 版本指纹入格
  "timing":   {"boundary":"generate()调用→返回", "cold_load_s":8.5},
  "judges":   {"nonempty":true, "len_ok":true, "twice_same":true, "cer":null}
}

- 强关联链：cell → run_id（期号）→ EPISODE.json（git/spec/GT 哈希）→ 代码库可反查
- 落盘前 jsonschema 校验（validate 在 save 之前，F-05）；校验失败写入 `status=failed` + 原因，绝不静默丢格
- 失败格也入账：缺格在 G0 闸门阻断发布（not_run 与 stale 同罪）

## 5. 判据与四道闸门

| 闸门 | 检查项（全部量化） | 失败动作 |
|---|---|---|
| G0 数据完整性 | 预期格数=实有格数；每格 rep 数达标；版本指纹全格一致；审计时效（控制文件 mtime 在本期内） | 阻断发布 |
| G1 结构校验 | jsonschema v6 逐格；gt_hash 与签核 GT 一致（N-08） | 阻断 |
| G2 口径审计 | bench_caliber_audit：wall vs 自报对账、正文口径注存在性 | 阻断（exit=1） |
| G3 判据汇总 | 七判据逐引擎：非空UTF-8 / &gt;200字符 / 两次一致 / cold记录 / peak内存 / LICENSE登记 / CER sanity | 降级标注 |

发布链顺序固定：`pre_push_check（10项格式）→ original_guard（原创自洽）→ bench_caliber_audit（口径）→ G0–G3`。前三闸门已在库（ep12 实证），G0–G3 为本期新增。

## 6. 计时口径三处同步（ep12 教训制度化）

- wall 定义：`generate()` 调用→返回（纯推理），不含 load、不含 preprocess
- cold_load 单列：from_pretrained 计时独立字段，禁止与 wall 混算
- 三处同步：代码注释（timing.boundary 字段）＋ 方案文档 ＋ 文章正文——bench_caliber_audit 闸门自动核对后两处
- 服务型引擎（D-FINE/OXR daemon）按端口/PID 采样内存（R-14），不按主进程

## 7. 进程纪律与一键清理（本次 P0 教训固化）

P0 实翻车两起，已成规则：
① 误杀活服务——netstat 的 LISTENING pid 是 wrapper 父，socket 在子进程 → 杀前 CONFIRM 打印完整 cmdline，杀后 raw socket 验服务（307/404=活，urllib 会误报 10061）；
② 孤儿进程——6 个 ep12 sampler 残留 → 跑测单实例，每轮前后进程盘点（PowerShell 按整串 cmdline 匹配）。

# 一键清理（默认全部 dry-run）
python scripts/clean_episode.py ep13             # 列将删清单+总大小，不动手
python scripts/clean_episode.py ep13 --data      # 打包 archive → 删（可回滚）
python scripts/clean_episode.py ep13 --models    # 显式才碰模型（跨期共享，默认永不删）

## 8. P0 教训 → 设计约束对照表（每条都有实证）

| # | P0 实测发现 | 转化为设计约束 |
|---|---|---|
| 1 | 5.22 无 rope_type='default'（Paddle/Tele 两家中招） | venv 版本钉死写入 EPISODE.json；config 补丁记入 MANIFEST |
| 2 | 官方仓 use_cache=False 缺陷（110 分钟 vs 161 秒） | engine_worker 强制 use_cache=True |
| 3 | 自造 prompt → spotting/复读输出（Paddle、Tele） | prompt 一律取自官方仓库原文，入 MANIFEST 留 hash |
| 4 | 漏 inputs.to(dtype) 输出退化（Tele） | gen 段固定 dtype 对齐，代码评审项 |
| 5 | mm_token_type_ids 被 generate 拒（dots） | 按 prepare ∪ forward 签名过滤（照抄 transformers 校验） |
| 6 | OXR buffer 未初始化 → 零输出 | 加载后显式恢复关键 buffer + 断言打印 |
| 7 | 大图 OOM（book_01 9072 patch） | 样本全量前先过内存预检；qwen3_5 两引擎单页 16 分钟 → rep 超时上限见 D2 |
| 8 | Tele/dots CPU 不可行（16 项实验归档） | 路径 C 归档机制；lineup 标 N/A 不排名 |

## 9. 待你拍板的 4 个决策点

D1 · Tele/dots 在 lineup 的呈现

A（推荐）：保留在名单标 N/A · CPU不可行 + 归档链接——诚实呈现「测过、不可行」

B：从名单移除，仅在正文附一段说明

选 A 的理由：读者能看到我们试过什么，归档可复现；不占排名位。

D2 · 单 rep 超时上限

A（推荐）：30 分钟/rep——覆盖已知最慢（Ovis 16.5 分钟 + 余量），超时记 `ok=false, fail_reason=timeout` 入 G0

B：60 分钟（更宽，但一格卡住拖整天）

依据：P0 实测最慢 rep=996s；官方预处理链 55 分钟未完的 Tele 实验已证明无上限不可行。

D3 · CER（字错率）接入时机

A（推荐）：跑测前接 GT（gt manifest+签核，N-07），G3 含 CER sanity——一步到位

B：首轮先跑「一致性判据」（非空/两次一致），CER 第二轮补——更快出首版数据

CER=(S+D+I)/N 含插入项 I（术语红线已核）；GT 未签核则 G1 直接阻断。

D4 · 执行授权

本稿评审通过后：

A（推荐）：直接开跑（6 引擎 × 26 样本 × 协议 A），预计总时长按 D2 上限估算后附表

B：先跑 3 样本冒烟 → 你确认数据格式 → 再全量

配套文件：规格 V6c（唯一权威源）· P0 判据 JSON×8 · 复活归档 JSON×2 · 本稿 HTML。评审意见直接回本会话，逐条改后出 v2。