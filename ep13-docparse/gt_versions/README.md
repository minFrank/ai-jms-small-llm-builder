# gt_versions/ —— GT 历史版本快照目录（当前为空）

规格 §3.6 / §4.2 预留此目录用于 GT 的版本化与回滚：每次修改 GT 应生成新 version、回 draft、清签，并在此留存旧版内容快照。

## 现状（2026-11-12 核实）

- **本目录 0 个文件**：v1 的 GT 文本快照从未落盘，v1 内容**不可回溯**。
- 当前唯一签核版本：`gt/manifest.json` → `gt_v=ep13-gt-v2`、`status=signed`、`signed_at=2026-11-08T06:57:34`；26 份 `.txt` 在 `gt/`，字节级佐证见 `gt/gt_audit.json`（26/26 matches_samples_manifest=true）。
- v1→v2 的变化只留有**文字记录**：`gt/manifest.json` 的 `errata` 记 r12 修 `chars`、r13 修 `total_chars`、r14 清除 `book_01`/`hard_01`/`skew_01` 的 U+FFFE 非字符、8 张合成图重渲染、66 格重跑、GT 重标注重签。

## 为什么不补一个 v1 快照

补就等于**编造历史证据**。v1 的原始 26 份文本已不存在，任何「补出来的 v1」都无法验证。因此本次收口选择如实登记缺口，不生成假快照。

若后续要真正补齐版本链，唯一可行路径是：从 ep11 的 18 份原始 GT + `scripts/make_samples_13.py` 的 `DOCS` 源文本重建 v1 候选，并明确标注「重建、非原始落盘」，且不得参与已签核 v2 的任何比对。这属于新实验，不在本期收口范围。

## 两处待核（未擅改签核值）

1. `gt/manifest.json` 的 `content_hash=5266101978…` 与 `control/SOURCES.md` 登记的 **v1** hash 相同；但 v1→v2 内容已变，逻辑上应不同。待核是登记笔误、还是该 hash 另有所指。
2. `total_chars` 头部 24679，`errata` 记 24682，差 3 —— 疑与清除的 3 个 U+FFFE 有关，待核。

> 注意：G0 的逐格 GT 比对用的是 **per-sample `gt_sha256`**（`samples/manifest.json` ↔ cell.fingerprint，156/156 通过），不依赖上面这两个聚合字段，故不阻断数据完整性结论。详见 `docs/data_provenance.md` 偏差 #5。
