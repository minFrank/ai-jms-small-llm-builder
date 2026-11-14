# ep13 引擎许可登记（LICENSES）— 读自各模型目录 LICENSE 正文，2026-11-07

| 引擎 | 文件 | 识别许可 | 首行 |
|---|---|---|---|
| OXR | LICENSE | **Apache-2.0** | # OXR License |
| PaddleOCR-VL-1.6 | LICENSE | **Apache-2.0** |                                  Apache License |
| Xiaomi-OCR-0 | (无 LICENSE 文件) | **未见许可文件** |  |
| OvisOCR2 | LICENSE | **Apache-2.0** |  |
| MonkeyOCR-pro | (无 LICENSE 文件) | **未见许可文件** |  |
| surya-2.5 | LICENSE | **unknown** |                    AI PUBS OPEN RAIL-M LICENSE (MODIFIED) |

> 说明：仅登记文件内明示内容；「未见许可文件」者发布前须另行核实（G0/G3 判据）。

## 发布前处置（2026-11-12，按「如实披露」路径）

本期采用**披露而非声称已核实**，不编造许可结论。已在成稿「九、本期口径与局限」写入对应声明。

| 引擎 | 处置 | 说明 |
|---|---|---|
| OXR / PaddleOCR-VL-1.6 / OvisOCR2 | 已登记 Apache-2.0 | 模型目录内 LICENSE 正文可查 |
| surya-2.5 | 补正：首行为 `AI PUBS OPEN RAIL-M LICENSE (MODIFIED)` | 原表「识别许可=unknown」过于笼统，实为 **Open RAIL-M 修改版**；其衍生/商用附加条款仍**未核实**，不作合规结论 |
| Xiaomi-OCR-0 / MonkeyOCR-pro-1.2B | 模型目录内**未见 LICENSE 文件** | 上游仓库许可待核；成稿只报实测结果，不对再分发、商用合规作任何结论 |

G3 判据 ⑥ 原按「已登记 + 已披露」判 ok（`gate3.json` 保留原判据值，未改动）。**许可核实仍是建议项**，但不是本次发布的阻断项——阻断项只有用户终审。若后续要商用或再分发模型权重，须先完成上游许可核实。

另：`control/engines.yaml` 的 `xiaomi_vl.model` 路径与磁盘目录名不一致（详见 `SOURCES.md` 现状更正、`docs/data_provenance.md`），属配置登记问题，与许可无关，一并列为发布前待核。
