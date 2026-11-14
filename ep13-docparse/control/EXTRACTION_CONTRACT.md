# EXTRACTION_CONTRACT（ep13 提取与 CER 规则 · **v2** · 2026-11-05 · 已签核）

**用途**：冻结「引擎输出 → 可比对文本 → CER」的全部规则，签核后 extract_v 固定，任何引擎不享受特殊处理。

## 1. 提取（引擎输出 → 文本）
- 取生成序列 decode 后的完整文本（skip_special_tokens=True）；
- **第一步 · 格式解析（v2 新增，2026-11-05 事故驱动：surya 标签致 CER 虚高、复读致 10.16）**：把输出解析为纯文本——
  - 剥引擎专有标记：`<|...|>` 序列（surya 等）；
  - 剥 HTML 标签：`</?[a-zA-Z][^>]*>`（`<p>` `<h1>` 等）；
  - 剥 markdown 结构符：行首 `#{1,6} `、成对 `**`/`*`/`` ` ``/`~~`、表格分隔行 `|---|`、表格竖线 `|`→空格；
  - **白名单模式**：只剥以上已知结构；正文中普通字符一律不动；
- **第二步 · 只做两件事**：去首尾空白（strip）、统一换行为 `\n`；
- **不做**任何其他归一化：不改大小写、不转全半角、不删标点、不合并空行、不重排阅读顺序（**画面存在的字符永不动**）；
- **判定边界**：剥的是「画面上不存在的结构记号」（标签/标记/格式符），不是画面文字——故不违反零归一化；
- 输出为空或全空白 → 该 rep 记 fail（err_kind=extract_fail），不参与 CER。

## 2. CER 计算
- **CER = (S + D + I) / N**（S=替换、D=删除、I=插入，N=GT 字符数）——含插入项，与学界定义一致；
- 逐字符比对（Unicode code point 级），用标准 Levenshtein 对齐；
- 单元 = 单格（样本×引擎）：cell.cer_median = 该格 valid reps 的 CER 中位数；
- GT 字符数 N=0 的样本不允许（建集时校验，当前 26 份 total_chars>0 ✓）。

## 3. 表格与特殊块
- 表格类 GT 以 `.txt` 为准（与画面文本逐字对应）；`.table.json`（如 table_01）仅作结构参考，**不参与 CER**；
- 公式、图片内文字：一律按画面可见字符转录进 GT，不做 LaTeX 还原。

## 4. 版本与签核
- 本契约 + gt/manifest.json（26 份 sha256）一起签核 → gt_v=ep13-gt-v1、status=signed；
- 此后任何 GT 修改 → 新 version、回 draft、清签（规格 §3.4）；
- cell.fingerprint 记 gt_v + gt_hash，G0 逐 cell 比对。

签核：v1=user(Frank) 2026-11-04 20:13 ｜ **v2=user(Frank) 批准（会话「可」2026-11-05）**，gt_v 不变（GT 内容未动，仅提取解析条款）

## 5. 现状更正（2026-11-12 收口，只增不改）

上面 §4 第一条与签核行里的 `gt_v=ep13-gt-v1` 是**2026-11-05 契约签核时的状态**，作为历史记录保留原貌；它**不是当前值**。

- 当前权威值：`gt/manifest.json` → `gt_v=ep13-gt-v2`、`status=signed`、`signed_at=2026-11-08T06:57:34`。
- 升版原因：r14 修复合成样本页脚/词中断行/不可见字符后，清除 `book_01`/`hard_01`/`skew_01` 的 U+FFFE 非字符，GT 重标注为 v2 并重签；8 张合成图 + 3 张受影响真实样本共 11 样本 × 6 引擎 = 66 格重跑（见 `gt/manifest.json` 的 `errata`、成稿 §六）。
- G0 逐格比对已按 v2 通过：`gates/gate0.json` 记 `per-sample gt_hash==samples_manifest.gt_sha256：156/156；gt_v=ep13-gt-v2`。
- 本契约**提取规则本身**仍为 v2 且未变；仅 GT 版本升 v2。契约的「gt_v 不变」表述只适用于 2026-11-05 那次签核。

遗留待核（不擅自改签核值，见 `docs/data_provenance.md`）：
1. `gt/manifest.json` 的 `content_hash=5266101978…` 与 `SOURCES.md` 登记的 v1 hash 相同，但 v1→v2 内容已变，逻辑上应不同 —— 待核实是登记笔误还是该 hash 另有所指。
2. `total_chars` 头部为 24679，`errata` 记 24682，差 3 —— 待核（疑与 U+FFFE 清除的 3 个非字符有关）。
3. `gt_versions/` 无 v1 快照，v1 内容不可回溯。

