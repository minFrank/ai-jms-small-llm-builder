# reviewer.localai

模型 deepseek-chat | 耗时 18s | 输入 26170 字符

```json
{
  "verdict": "block",
  "findings": [
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件中「约 7.1G」与日志不一致（日志为 6.94G）",
      "evidence": "稿件 digest 写「要下 6.94G（约 7G）」正确，但正文第一节写「实测 6.94G，约 7G」也正确；然而日志 run-2026-09-13.md 末尾写「文章里写的『约 7.1G（模型 5.1G + 运行环境 2.0G）』与实测吻合」——这是日志自身的过时残留，稿件已改为 6.94G，但日志里还留着 7.1G 的旧表述，属于日志不自洽。",
      "fix": "删除或修正日志 run-2026-09-13.md 末尾那句「约 7.1G」的旧表述，统一为 6.94G。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「8.25G」与日志计算是否吻合需确认",
      "evidence": "稿件写「加载模型那几秒实测冲到约 8.25G（日志峰值 9007MB，扣掉机器上其他程序）」。日志 runtime-memory-disk.txt 写「峰值 9007 MB」「基线 756 MB」「加载模型瞬间冲到约 8.25 GB（这是净增量，不含机器上其他程序）」。9007 − 756 = 8251 MB ≈ 8.25 GB，吻合。但稿件括号里写「扣掉机器上其他程序」，而日志写「这是净增量，不含机器上其他程序」——两者语义一致，但稿件表述「扣掉机器上其他程序」容易被读成「9007 已经扣掉了」，实际是「9007 是总和，8.25 是扣掉后的净增量」。",
      "fix": "改为「日志峰值 9007MB，扣掉基线 756MB 后约 8.25G」或类似明确表述。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「慢约 25–30%」与日志「慢约 30%」不完全一致",
      "evidence": "稿件写「跑出 232 和 245 秒 —— 慢约 25–30%」。日志 runtime-memory-disk.txt 写「前四次 167–192 秒，这两次 232–245 秒（慢约 25–30%）」。日志本身写的是 25–30%，稿件一致。但 run-2026-09-13.md 第五次运行写「这次 245 秒（慢约 30%）」——单次是 30%，区间是 25–30%，稿件用区间正确。",
      "fix": "无需修改，稿件与日志区间一致。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「四次正常成绩：2 分 47 秒 ~ 3 分 12 秒」需核对",
      "evidence": "167 秒 = 2 分 47 秒，192 秒 = 3 分 12 秒。日志 run-2026-09-13.md 四次成绩为 167、184、175、192 秒，区间 167–192 秒。换算正确。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「9–16 秒」加载时间与日志一致",
      "evidence": "日志 runtime-memory-disk.txt 写「9 秒(第一次) 10 秒(第二次) 11 秒(第四次) 15 秒(补测①) 16 秒(补测②) → 区间 9–16 秒」。稿件写「9–16 秒（多数时候 10 秒上下；机器忙时会到 16 秒。下图这一次是 10 秒）」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「15.84 秒」与日志一致",
      "evidence": "runtime-errors.txt 写「产出文件时长:15.84 秒(只含第 1 段)」。稿件坑一写「成品音频却只有 15.84 秒」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「382 字」「6 段」与日志一致",
      "evidence": "runtime-errors.txt 写「那次输入:382 字」「引擎切段数:6 段」。稿件坑一写「文案 382 字」「引擎把 382 字切成 6 段」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「117 个字」与日志一致",
      "evidence": "run-2026-09-13.md 写「文本:`story.txt`,117 个汉字」。稿件第三节写「117 个字」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「28.8 秒」与日志一致",
      "evidence": "run-2026-09-13.md 多次写「生成音频 28.8 秒」。稿件写「28.8 秒」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「6.0–6.5G」与日志一致",
      "evidence": "runtime-memory-disk.txt 写「稳定运行占用 6800–7230 MB → 6.0–6.5 GB」。稿件写「6.0–6.5G」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「5.6–6.8 倍」与日志一致",
      "evidence": "run-2026-09-13.md 四次 RTF 区间：第 1 段 5.56–6.39，第 2 段 5.91–6.78。稿件写「慢约 5.6–6.8 倍（四次区间）」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「15%」稳定性与日志一致",
      "evidence": "run-2026-09-13.md 写「四次结果波动约 15%」。稿件写「最慢的比最快的慢约 15%」。192/167 ≈ 1.15，即慢约 15%。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「6.94G」「5.05G」「1.88G」与日志一致",
      "evidence": "runtime-memory-disk.txt 写「.venv 1927.0 MB (1.88 GB)」「pretrained_models 5175.6 MB (5.05 GB)」「合计 7106.6 MB (6.94 GB)」。稿件写「实测 6.94G，约 7G（模型权重 5.05G + 运行环境 1.88G）」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「13 个文件」与复刻包清单核对",
      "evidence": "复刻包文件清单中，程序文件：install.bat、start.bat、tools/check.py、tools/tts.py、what-i-said.txt.example、一键安装.bat、一键生成.bat = 7 个；加上 README.md、READ_ME_FIRST.md、！先看这个.md、story.txt、我的录音.wav、我的录音说的是什么.txt = 6 个；共 13 个。但稿件附录写「一共 13 个文件，真正的程序只有两个」，而表格里列了 install.bat/一键安装.bat、start.bat/一键生成.bat、tools/tts.py、tools/check.py、what-i-said.txt.example 共 5 类。13 个文件是否包含 logs/ 和 review/ 目录？复刻包清单里 logs/ 有 4 个文件，review/ 有大量文件。如果「13 个文件」只算根目录+tools，需要确认。",
      "fix": "核实「13 个文件」的计数口径，明确是否包含 logs/ 和 review/。"
    },
    {
      "severity": "🔴阻断",
      "item": "数字溯源：稿件「63 / 62」「96 / 91」「171」「83」行数与复刻包实际文件核对",
      "evidence": "复刻包清单中有 install.bat、一键安装.bat、start.bat、一键生成.bat、tools/tts.py、tools/check.py。稿件附录表格写 install.bat/一键安装.bat 63/62 行，start.bat/一键生成.bat 96/91 行，tools/tts.py 171 行，tools/check.py 83 行。这些行数在提供的日志中没有对应记录，无法溯源。",
      "fix": "在日志中补充各文件行数记录，或标注为「文件行数，可打开文件核对」。"
    },
    {
      "severity": "🔴阻断",
      "item": "四张数据齐不齐：效果数据含失败案例，但失败案例「坑一」标注为「早期观察，无日志」",
      "evidence": "稿件坑一明确写「这是最早的一次测试（382 字），当时我没存日志，所以这一条属于『早期观察』，不是有日志的实测」。检查清单第 2 条要求「效果：真实任务的结果，且必须含至少一个失败案例」。坑二、坑三有日志（runtime-errors.txt），坑一无日志但已如实标注。失败案例存在且有日志依据（坑二、坑三）。",
      "fix": "无需修改，已满足要求。"
    },
    {
      "severity": "🔴阻断",
      "item": "绝不推收费模型：稿件未出现收费模型",
      "evidence": "稿件全文未出现需要付费、注册、免费额度的模型。CosyVoice 3 为 Apache-2.0 开源。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "术语闸门：前 5 段是否含禁用词",
      "evidence": "前 5 段（从「晚上九点半」到「不想动手的话，整个过程就是双击两个文件。」）逐段检查：未出现「量化、GGUF、t/s、token、RTF、推理、上下文、参数、权重、LoRA」。但第 4 段出现「要下约 7G 的东西（第二节会说这两块分别是什么）」——「模型」「运行环境」未出现，符合要求。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "许可结论：稿件写明可商用，且与官方许可一致",
      "evidence": "稿件第七节写「免费，而且许可上可以商用。CosyVoice 3 由阿里 FunAudioLLM 开源，模型权重许可是 Apache-2.0」。日志 license-check.txt 写「代码与模型权重均为 Apache-2.0 —— 文章里『免费、可以商用』的结论成立」。一致。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "门槛如实：稿件明说配置要求、下载大小、等待时间",
      "evidence": "稿件第一节写「8G 的电脑跑不了，16G 可以」「要下载：实测 6.94G，约 7G」「生成 1 分钟的音频，电脑要忙差不多 6 分钟」。符合要求。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "失败案例是否真实：坑二、坑三报错文本与日志逐字一致",
      "evidence": "稿件坑二报错「LibsndfileError: Error opening '...CosyVoice\\我的录音.wav': System error.」——runtime-errors.txt 中未找到此条逐字记录，需确认。稿件坑三报错「tts.py: error: the following arguments are required: --out」——runtime-errors.txt 中未找到此条逐字记录，需确认。",
      "fix": "在 runtime-errors.txt 中补充坑二、坑三的完整报错原文，确保逐字一致。"
    },
    {
      "severity": "🔴阻断",
      "item": "标题：含模型名？",
      "evidence": "标题「声音克隆：20 秒录音，电脑用你的声音念任意文字」——不含模型名。符合本系列标题规则。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "跨期重复：与上期（MiniCPM5-2B 无显卡跑分）是否撞车",
      "evidence": "上期为 MiniCPM5-2B 无显卡跑分，本期为 CosyVoice 3 声音克隆。模型不同、主题不同、结论不同。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "对外核查：CosyVoice 3 许可已核实",
      "evidence": "license-check.txt 记录了 HuggingFace API 返回的 license: apache-2.0，来源为 https://huggingface.co/api/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 和 https://huggingface.co/api/models/FunAudioLLM/Fun-CosyVoice3-0.5B。已外部核实。",
      "fix": "无需修改。"
    },
    {
      "severity": "🔴阻断",
      "item": "日志自身不自洽：run-2026-09-13.md 末尾「约 7.1G」与 runtime-memory-disk.txt「6.94G」矛盾",
      "evidence": "run-2026-09-13.md 末尾写「文章里写的『约 7.1G（模型 5.1G + 运行环境 2.0G）』与实测吻合」——但实测合计为 6.94G，且稿件已改为 6.94G。这是日志中的过时残留。",
      "fix": "删除或修正 run-2026-09-13.md 末尾的「约 7.1G」表述。"
    },
    {
      "severity": "🔴阻断",
      "item": "改动痕迹检查：稿件中「补测」「重写」「改为」等字眼",
      "evidence": "稿件第三节写「另有两次补测见下方」「后来为补测内存又跑了两回」——「补测」字眼出现，但上下文自洽，读者能理解是额外测试。稿件坑一写「早期观察，无日志」——已说明。未发现改稿中间状态。",
      "fix": "无需修改。"
    },
    {
      "severity": "🟡建议",
      "item": "稿件「8.25G」表述可更清晰",
      "evidence": "稿件写「加载模型那几秒实测冲到约 8.25G（日志峰值 9007MB，扣掉机器上其他程序）」。日志写「峰值 9007 MB」「基线 756 MB」「加载模型瞬间冲到约 8.25 GB（这是净增量，不含机器上其他程序）」。稿件括号内「扣掉机器上其他程序」与日志「不含机器上其他程序」语义有细微差别。",
      "fix": "改为「日志峰值 9007MB，扣掉基线 756MB 后约 8.25G」。"
    },
    {
      "severity": "🟡建议",
      "item": "稿件「13 个文件」计数口径需明确",
      "evidence": "复刻包清单中文件数量较多（含 review/ 目录下大量文件），稿件附录写「一共 13 个文件」需明确是否只算根目录+tools。",
      "fix": "明确「13 个文件」是否指根目录+tools 下的文件，或改为「根目录和 tools 下共 13 个文件」。"
    },
    {
      "severity": "🟡建议",
      "item": "稿件附录行数（63/62、96/91、171、83）无日志依据",
      "evidence": "提供的日志中没有各文件行数记录。",
      "fix": "在日志中补充行数记录，或标注「行数可打开文件核对」。"
    }
  ],
  "number_trace": [
    {"claim": "6.94G（约 7G）", "log_line": "runtime-memory-disk.txt: 合计 7106.6 MB (6.94 GB)", "ok": true},
    {"claim": "模型权重 5.05G", "log_line": "runtime-memory-disk.txt: pretrained_models 5175.6 MB (5.05 GB)", "ok": true},
    {"claim": "运行环境 1.88G", "log_line": "runtime-memory-disk.txt: .venv 1927.0 MB (1.88 GB)", "ok": true},
    {"claim": "6.0–6.5G 内存", "log_line": "runtime-memory-disk.txt: 稳定运行占用 6800–7230 MB → 6.0–6.5 GB", "ok": true},
    {"claim": "约 8.25G 峰值", "log_line": "runtime-memory-disk.txt: 峰值 9007 MB, 基线 756 MB → 约 8.25 GB", "ok": true},
    {"claim": "167–192 秒", "log_line": "run-2026-09-13.md: 四次成绩 167、184、175、192 秒", "ok": true},
    {"claim": "28.8 秒成品", "log_line": "run-2026-09-13.md: 生成音频 28.8 秒", "ok": true},
    {"claim": "9–16 秒加载", "log_line": "runtime-memory-disk.txt: 9 秒(第一次) 10 秒(第二次) 11 秒(第四次) 15 秒(补测①) 16 秒(补测②)", "ok": true},
    {"claim": "5.6–6.8 倍", "log_line": "run-2026-09-13.md: 第 1 段 RTF 5.56–6.39, 第 2 段 RTF 5.91–6.78", "ok": true},
    {"claim": "15% 波动", "log_line": "run-2026-09-13.md: 四次结果波动约 15%", "ok": true},
    {"claim": "117 字", "log_line": "run-2026-09-13.md: 文本:story.txt,117 个汉字", "ok": true},
    {"claim": "382 字", "log_line": "runtime-errors.txt: 那次输入:382 字", "ok": true},
    {"claim": "6 段", "log_line": "runtime-errors.txt: 引擎切段数:6 段", "ok": true},
    {"claim": "15.84 秒", "log_line": "runtime-errors.txt: 产出文件时长:15.84 秒(只含第 1 段)", "ok": true},
    {"claim": "232 和 245 秒", "log_line": "runtime-memory-disk.txt: 2026-09-14 07:46 用时 245 秒; 2026-09-14 07:51 用时 232 秒", "ok": true},
    {"claim": "慢约 25–30%", "log_line": "runtime-memory-disk.txt: 前四次 167–192 秒,这两次 232–245 秒(慢约 25–30%)", "ok": true},
    {"claim": "13 个文件", "log_line": "复刻包文件清单（需确认计数口径）", "ok": false},
    {"claim": "63/62 行", "log_line": "无日志记录", "ok": false},
    {"claim": "96/91 行", "log_line": "无日志记录", "ok": false},
    {"claim": "171 行", "log_line": "无日志记录", "ok": false},
    {"claim": "83 行", "log_line": "无日志记录", "ok": false}
  ],
  "checked": [
    {"no": 1, "result": "部分", "evidence": "大部分数字可溯源，但「13 个文件」计数口径和附录行数无日志依据；日志 run-2026-09-13.md 末尾「约 7.1G」与实测 6.94G 矛盾。"},
    {"no": 2, "result": "已改", "evidence": "速度、资源、效果（含失败案例坑二坑三）、门槛四张数据齐全。"},
    {"no": 3, "result": "已改", "evidence": "未出现收费模型。"},
    {"no": 4, "result": "已改", "evidence": "前 5 段无禁用术语。"},
    {"no": 5, "result": "已改", "evidence": "第七节写明 Apache-2.0 可商用，与 license-check.txt 一致。"},
    {"no": 6, "result": "已改", "evidence": "明说 8G 跑不了、16G 可以、下载 6.94G、生成 1 分钟要 6 分钟。"},
    {"no": 7, "result": "部分", "evidence": "坑二坑三报错文本在 runtime-errors.txt 中未找到逐字记录，需补充。"},
    {"no": 8, "result": "已改", "evidence": "标题不含模型名，含具体场景入口。"},
    {"no": 9, "result": "已改", "evidence": "与上期模型、主题、结论均不同。"},
    {"no": 10, "result": "已改", "evidence": "许可已通过 HuggingFace API 外部核实。"}
  ],
  "stats": {
    "total_findings": 28,
    "blocking": 25,
    "suggestions": 3,
    "number_trace_ok": 16,
    "number_trace_fail": 5
  }
}
```