# ep04 扩测设计 v2:ComfyUI + DirectML/ONNX 核显路线

> 状态:**设计已过评审**(流程:dsh 优先;本轮 dsh 可用 → `REVIEW-dsh.md` 299 行/27 条 DoD;代码二审 `REVIEW-bench5.md`/`REVIEW-bench5-r2.md`)
> 日期:2026-10-06

## 1. 背景与目标

ep4 现稿已测 2 引擎(sd.cpp / diffusers)× 2 后端(纯 CPU / Vulkan 核显)。
两个缺口:

| 缺口 | 为什么补 | 现状(预检实测) |
|---|---|---|
| **ComfyUI** | 中文社区最常问的工作流框架,现稿「本期没测的」第一条 | `comfy.zip` sha256=`52398422ad070f6b…`(1451 文件);解压到短路径 `D:/ep04/comfy/ComfyUI-src`(1244 文件,含 `main.py`);独立 venv 已建并装齐 |
| **DirectML/ONNX 核显** | 第二条让核显干活的路,与 sd.cpp 的 Vulkan 对照 | 主 venv `onnxruntime 1.29.0` 只有 `CPU/Azure` provider,无 DmlExecutionProvider |

**目标**:同机、同种子(42/43/44)、同 prompt(2 句)、同 512×512、同 20 步、断网,扩成五方案对照。

**数据边界(dsh C1/C11)**:已发布的 `bench4-progress.json` **冻结不动**(带日期副本 + sha256),
新数据只进新文件 `bench5-progress.json`(schema_version=2,append-only,行带 `attempt`);`bench4.py` 语义不改。

## 2. 选型定案(依 REVIEW-dsh.md §2)

**路线 B → B1 `onnxruntime-directml`**(B2 `torch-directml` 一票否决:只支持 torch≤2.4,装它会降级现有
torch 2.14.1,摧毁已发布数据的复现环境;README 自称 Alpha、上游不活跃)。降级顺序写死:
`DML fp16 → DML fp32 → 如实记失败`,**全程不回退 B2**。

**ComfyUI → 独立 venv**(复用被否决:`requirements.txt` 不含 torch,依赖解析可能重算/降级 torch 污染主 venv;
与 ORT-DML 同包名互斥叠加 → 两两隔离)。

## 3. 执行前预检(实测,非假设)

| # | 项 | 实测结果 |
|---|---|---|
| 1 | `onnxruntime-directml` 版本门槛 | 最新 **1.24.4**,`requires_python>=3.11` —— 设计 v1「停在 1.17 系、numpy<2 钉死」**已过时**,按实装版本 `Requires-Dist` 现场复核 |
| 2 | ComfyUI `requirements.txt` / README | 无 torch 条目;README 称 **Python 3.13 最稳、3.14 可用**(本机 3.11.16 跑通 0.38.0,见冒烟) |
| 3 | 本机解释器 | `py -3.11` 不存在,真实为 `py -V:Astral/CPython3.11.16`;`-m venv` 静默不落地 → 改 `uv venv --clear --python` |
| 4 | 主 venv freeze 基线 | `env-main.txt` 124 行(torch 2.14.1+cpu / numpy 2.4.6 / transformers 5.18.0) |
| 5 | `bench4.py` comfy 分支 | **已实现**(L204–317,含服务式 `/prompt` API),dsh 原判「未验证空分支」不成立;但有 5 处不达标(见 §5) |
| 6 | `bench4-progress.json` schema | `{rows, ts_start}`,30 行,行键 `cell/scheme/prompt_idx/run_idx/seed/steps/size/seconds/mem_peak/ok/err` |
| 7 | D 盘 | 732G 总 / 581G 可用 → 一切落 `D:/ep04/` 短路径(W3/W7) |
| 8 | ComfyUI 冒烟 | **通过**:0.38.0 起服务、`/system_stats` 通、frontend 1.53.10 + 模板 0.11.76 齐 |

**Windows 坑(本轮实踩)**:原生程序(uv/git/python)不认 `/d/` MSYS 路径,一律传 `D:/`;
`uv venv` 不带 pip → 装包用 `uv pip install --python <venv>`;清华镜像缺 `comfyui-workflow-templates-media-assets-02`
→ 改官方 PyPI(`--default-index https://pypi.org/simple`)。

## 4. 验收判据(评审后版本)

设计 v1 的 6 条保留,按 dsh 的 27 条 DoD 补充(**最小必保 10 条**):
DP-01 环境隔离、DP-05 落点实测证据、DP-06 回退节点门禁、DP-08 可比字段齐全、DP-09 耗时口径一致、
DP-10 进程树 RSS + 共享显存列、DP-12 旧数据 deep-equal 断言、DP-14 每格 n≥3 报 median、
DP-16 种子 sha256 自证、DP-20 断网可证。
完整清单见 `REVIEW-dsh.md` §6。

**可比性铁律(dsh §4.1)**:五方案表**不是全交叉因子设计**,正文只允许两类结论句 ——
①同落点比引擎;②同引擎比落点;跨栈句必须带「不可归因单一变量」标签;五格图只画同口径列。

**跨期漂移(dsh C12/DP-19)**:新增数据与已发布数据**不同天** → 必须重跑 sd.cpp 纯 CPU 当锚点,
漂移 >5% 时表头标漂移区间(「同机 ≠ 同时」)。

## 5. 阶段划分(评审建议:两阶段独立交付)

| 阶段 | 内容 | 状态 |
|---|---|---|
| **阶段 1 ComfyUI** | 独立 venv → 冷启动 n≥3 → 暖态单列 → 锚点复测 → 证据/复刻包 | 环境✅ 冒烟✅ 代码过二审 |
| **阶段 2 ONNX/DML** | 独立 venv → 下模型(尾部风险最大)→ 导出校验 → n≥3 → 同栈 CPU 锚点 | 未开工 |

**为什么这样排**:判据 4 允许 ONNX/DML 如实失败,阶段 1 的成果不该被阶段 2 的下载风险拖住。

## 6. 代码:新模块 `bench5.py`(不改 bench4)

dsh 代码二审(REVIEW-bench5.md)**判定「不可直接开跑」,13 条阻断 B01–B13**,其中 4 条会**静默产假**:

| 阻断 | 危害 | 修法 |
|---|---|---|
| B03 残留出图 | 上轮的图冒充本轮 → 假 OK + 假「两轮同 sha」 | 每格独立 `--output-directory` + 开跑前清目录 + 只认 history 返回文件 + mtime 断言 |
| B01/B02 冷启动退化 | 端口残留 → 热态冒充冷启动 | 开跑前断言端口空闲;`kill_tree` 递归回收 + 校验端口释放 |
| B04 种子自检 fail-open | `None==None` 判 PASS、DIFF 只打印 | 非空断言 + 同格全部 run 全比 + fail → `exit 1` |
| B10 静默成功 | history 有条目即成功、全格失败仍 exit 0 | 显式 `status_str=="success"` + `finally` 采样 + 失败 `exit 1` |
| B05/B06/B07/B08/B09/B11/B12/B13 | 落点证据、冻结覆盖、CLI 漏跑、指纹、锚点残破、断网无证、schema 缺键、复刻包缺件 | 见评审文件逐条 |

**已确认做对**(dsh 二审明确):C11 新模块不动旧数据、冷启动计时起点在 `Popen` 之前(含 import+加载)、
每轮重启规避 ComfyUI 权重常驻、`.tmp + os.replace` 原子落盘。

## 7. 工作量(评审修正后)

阶段 1 约 90–150 分钟;阶段 2 约 150–240 分钟;图表正文+流水线约 90 分钟 → 合计 **5.5–8 小时**。
