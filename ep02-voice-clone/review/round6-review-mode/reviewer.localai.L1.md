# reviewer.localai.L1

模型 deepseek-chat | 耗时 19s | 输入 24966 字符

{"verdict":"block","findings":[{"severity":"🔴阻断","item":"「约 7G」与「实测 6.94G」口径不一致：正文写「要下约 7G」，但日志合计 7106.6 MB = 6.94 GB，且日志明确写「文章里写的『约 7.1G（模型 5.1G + 运行环境 2.0G）』与实测吻合」——稿件把 7.1G 改成了 7G，与日志结论不符","evidence":"稿件：「要下约 7G 的东西（模型 + 运行环境）」「要下载：约 7G（实测 6.94G —— 其中模型权重 5.05G、运行环境 1.88G，两块加起来）」；日志 runtime-memory-disk.txt：「合计 7106.6 MB (6.94 GB)」「→ 文章里写的『约 7.1G（模型 5.1G + 运行环境 2.0G）』与实测吻合」","fix":"统一为「约 7G（实测 6.94G）」或「约 7.1G」，三处（digest、第一节、第二节表格）保持一致；日志结论句也同步改为 6.94G 口径"},{"severity":"🔴阻断","item":"「加载模型的那几秒会冲到 8G 出头」与日志「约 8.25 GB」不一致，且未说明是净增量还是含基线","evidence":"稿件：「加载模型的那几秒会冲到 8G 出头」；日志 runtime-memory-disk.txt：「峰值（模型加载那一瞬间）：9007 MB」「加载瞬时峰值 9007 MB → 约 8.25 GB」「这是净增量，不含机器上其他程序」","fix":"改为「加载模型瞬间冲到约 8.25G（净增量，不含机器上其他程序）」，并说明 8G 机器为何撑不住"},{"severity":"🔴阻断","item":"「8G 的电脑跑不了」结论与日志「8G 会在加载那一步撑不住」表述强度不同：日志说的是「加载那一步撑不住」，稿件直接下「跑不了」的硬结论，且未说明是加载阶段而非全程","evidence":"稿件：「内存结论先说：8G 的电脑跑不了，16G 可以」「8G 的机器会在加载那一步就撑不住」；日志 runtime-memory-disk.txt：「→ 16G 内存的机器够用；8G 会在加载那一步撑不住」","fix":"改为「8G 的电脑在加载模型那一步会撑不住（跑不了）」，保留「加载那一步」的限定，避免读者误以为全程都不行"},{"severity":"🔴阻断","item":"「模型加载 9–16 秒」区间与日志一致，但正文表格写「多数时候 9–11 秒；机器忙时会到 16 秒」，日志只列了 5 次数据（9/10/11/15/16），未说明「多数时候」的统计依据","evidence":"稿件：「模型加载 9–16 秒（多数时候 9–11 秒；机器忙时会到 16 秒。下图这一次是 10 秒）」；日志 runtime-memory-disk.txt：「9 秒（第一次） 10 秒（第二次） 11 秒（第四次） 15 秒（补测①） 16 秒（补测②）→ 区间 9–16 秒。前几次都是 9–11 秒；补测那两次偏慢」","fix":"「多数时候」改为「前三次都是 9–11 秒」，与日志的 5 次采样对应，避免无依据的统计词"},{"severity":"🟡建议","item":"「比正常播放慢约 5.6–6.8 倍」区间与日志 RTF 区间 5.56–6.78 基本吻合，但正文未说明这是四次实测的 RTF 区间，读者可能误以为是精确换算","evidence":"稿件：「比正常播放慢约 5.6–6.8 倍（四次区间）」；日志 run-2026-09-13.md：「区间 167–192 秒 | 5.56–6.39 | 5.91–6.78」","fix":"保留「约」字，可加一句「这是四次实测的 RTF 区间」"},{"severity":"🟡建议","item":"「最慢的比最快的慢约 15%」与日志「波动约 15%」一致，但 167→192 实际是 14.97%，四舍五入为 15%，可接受；不过「245 秒比 192 秒还慢约 28%」与日志「慢约 30%」不一致","evidence":"稿件：「最慢的比最快的慢约 15%」「同一件事跑出了 245 秒——比最慢的那次（192 秒）还慢约 28%」；日志 run-2026-09-13.md：「四次结果波动约 15%」「这次 245 秒（慢约 30%）」；runtime-memory-disk.txt：「这两次 232–245 秒（慢约 25–30%）」","fix":"统一为「慢约 30%」或「慢约 25–30%」，与日志一致；28% 无日志依据"},{"severity":"🟡建议","item":"「生成 1 分钟的音频，电脑要忙差不多 6 分钟」与日志 RTF 6.19–6.78 一致，但正文未说明这是按哪次 RTF 换算的，且 6 分钟对应 RTF 6.0，略低于实测区间下限","evidence":"稿件：「生成 1 分钟的音频，电脑要忙差不多 6 分钟」；日志 run-2026-09-13.md：RTF 5.56–6.78","fix":"改为「差不多 6–7 分钟」或注明「按 RTF 约 6 倍估算」"},{"severity":"🟡建议","item":"「生成 2 分钟能念完的话，电脑要忙 12–13 分钟」是 6 分钟的倍数推算，但未说明是推算而非实测","evidence":"稿件：「生成 2 分钟能念完的话，电脑要忙 12–13 分钟」；日志无 2 分钟音频的实测记录","fix":"加「按上面的速度推算」字样，避免读者误以为是实测"},{"severity":"🟡建议","item":"「382 字那次被切成 6 段」与日志一致，但「成品音频却只有 15.84 秒」与日志「15.84 秒」一致；不过正文说「第一次测的时候，文案 382 字」，日志 runtime-errors.txt 写「那次输入：382 字」，一致；但「早期观察，无日志」的标注与日志 runtime-errors.txt 的「当时没有留日志」一致，可保留","evidence":"稿件：「我第一次测的时候，文案 382 字，成品音频却只有 15.84 秒」「382 字那次被切成 6 段」；日志 runtime-errors.txt：「那次输入：382 字」「引擎切段数：6 段」「产出文件时长：15.84 秒（只含第 1 段）」「当时没有留日志」","fix":"无需修改，已一致"},{"severity":"🟡建议","item":"「坑二」报错文本与日志逐字一致性未在日志中直接找到对应行，runtime-errors.txt 只记录了「现象」和「修法」，未逐字保留 LibsndfileError 原文","evidence":"稿件：```text LibsndfileError: Error opening '...CosyVoice\\我的录音.wav': System error.```；日志 runtime-errors.txt：「②③的现象在 run-2026-09-13.md 里有记录（成品只有 15.84 秒）」「没有报错，是静默的」——未找到 LibsndfileError 逐字原文","fix":"在 runtime-errors.txt 中补录该报错原文，或稿件标注「报错原文来自当时屏幕记录，未落日志」"},{"severity":"🟡建议","item":"「坑三」报错文本 `tts.py: error: the following arguments are required: --out` 在日志中未找到逐字对应行","evidence":"稿件：```text tts.py: error: the following arguments are required: --out```；日志 runtime-errors.txt 只写「在 chcp 65001 的代码页下，展开后的中文把命令拆坏了」，未保留该报错原文","fix":"在 runtime-errors.txt 中补录该报错原文，或稿件标注来源"},{"severity":"🟡建议","item":"许可结论「可以商用」已补外部核实，与日志 license-check.txt 一致，但正文写「我去官方仓库和模型页核过」，日志只记录了 HF API 和 GitHub LICENSE，未记录「官方仓库」的具体 URL 核对过程","evidence":"稿件：「我去官方仓库和模型页核过，代码和权重都是这个许可」；日志 license-check.txt：「来源：https://huggingface.co/api/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512」「来源：https://huggingface.co/api/models/FunAudioLLM/Fun-CosyVoice3-0.5B」「→ 模型权重也是 apache-2.0」——GitHub LICENSE 未在摘要中给出 URL","fix":"在 license-check.txt 中补 GitHub LICENSE 的 URL 和核对时间，或正文改为「我去 Hugging Face 模型页核过」"},{"severity":"🟡建议","item":"「AI 声明前置」改动后，文末原有 AI 声明段落被删除，但正文开头声明与文末「关于你的录音」段落之间是否重复或缺失需确认——当前稿件开头有声明，文末无重复，无缺失","evidence":"稿件开头：「（先说一句：本文的文字整理有 AI 参与，但所有实测数据、踩坑记录、代码都是我自己跑的，有日志的都在包里可逐条核对。）」；文末：「关于你的录音：录音和文字全程在你自己的电脑上处理，不上传。」——无重复 AI 声明","fix":"无需修改，已一致"},{"severity":"🟡建议","item":"「内存 6.0–6.5G」与日志「稳定运行占用 6800–7230 MB → 6.0–6.5 GB」一致，但正文未说明这是「所有 python 进程之和」的口径，台账 R4 曾因此被扣分","evidence":"稿件：「它平时吃 6.0–6.5G」；日志 runtime-memory-disk.txt：「方法：跑一次合成，每 3 秒采样一次『这台机器上所有 python 进程的内存之和』，取峰值」「稳定运行占用 6800–7230 MB → 6.0–6.5 GB」","fix":"在正文或图说中注明「这是这台机器上所有 python 进程之和」，避免读者误以为是该程序独占"},{"severity":"🟡建议","item":"「16G 的机器够用：8G 出头的峰值，加上系统本身占用，还剩得下浏览器」——8G 出头峰值 + 系统占用，16G 是否「还剩得下浏览器」无日志依据","evidence":"稿件：「16G 的机器够用：8G 出头的峰值，加上系统本身占用，还剩得下浏览器」；日志无 16G 机器上浏览器占用的实测数据","fix":"改为「16G 的机器够用：8G 出头的峰值，加上系统本身占用，通常还剩得下浏览器」，加「通常」限定"},{"severity":"🟡建议","item":"「AMD 核显」与日志「无独立显卡」一致，但日志未明确写「AMD 核显」，只写「无独立显卡」和 CPU 型号","evidence":"稿件：「我这台是 AMD 核显，没有独立显卡」；日志 run-2026-09-13.md：「CPU：AMD Ryzen 7 5700G（8 核 16 线程）」「无独立显卡」","fix":"可保留，5700G 自带核显是事实，但严格说日志未直接写「核显」，建议日志补一句或正文改为「没有独立显卡（CPU 自带核显）」"},{"severity":"🟡建议","item":"「13 个文件」与复刻包文件清单不一致：清单中实际文件数远超 13 个（含 review 目录、__pycache__ 等）","evidence":"稿件：「这个包不大，一共 13 个文件，真正的程序只有两个」；复刻包文件清单：install.bat、logs/、output/、READ_ME_FIRST.md、README.md、review/、start.bat、story.txt、tools/、what-i-said.txt.example、一键安装.bat、一键生成.bat、我的录音.wav、我的录音说的是什么.txt、！先看这个.md——仅顶层就 15 个，加子目录更多","fix":"改为「这个包不大，顶层一共十几个文件」或明确「不含 review 和日志，程序文件只有两个」"},{"severity":"🟡建议","item":"「install.bat / 一键安装.bat 63 / 62 行」「start.bat / 一键生成.bat 96 / 91 行」「tools/tts.py 171 行」「tools/check.py 83 行」——行数无日志依据，复刻包清单未提供行数","evidence":"稿件附录表格中的行数；日志和复刻包清单均未提供文件行数","fix":"在复刻包中补一份文件行数清单，或删除具体行数只保留文件名"}]，

"number_trace":[
{"claim":"约 7G（模型 + 运行环境）","log_file":"runtime-memory-disk.txt","log_line":"合计 7106.6 MB (6.94 GB)","ok":false},
{"claim":"实测 6.94G","log_file":"runtime-memory-disk.txt","log_line":"合计 7106.6 MB (6.94 GB)","ok":true},
{"claim":"模型权重 5.05G","log_file":"runtime-memory-disk.txt","log_line":"pretrained_models 5175.6 MB (5.05 GB)","ok":true},
{"claim":"运行环境 1.88G","log_file":"runtime-memory-disk.txt","log_line":".venv 1927.0 MB (1.88 GB)","ok":true},
{"claim":"内存 6.0–6.5G","log_file":"runtime-memory-disk.txt","log_line":"稳定运行占用 6800–7230 MB → 6.0–6.5 GB","ok":true},
{"claim":"加载峰值 8G 出头","log_file":"runtime-memory-disk.txt","log_line":"峰值（模型加载那一瞬间）：9007 MB → 约 8.25 GB","ok":false},
{"claim":"模型加载 9–16 秒","log_file":"runtime-memory-disk.txt","log_line":"9 秒（第一次） 10 秒（第二次） 11 秒（第四次） 15 秒（补测①） 16 秒（补测②）→ 区间 9–16 秒","ok":true},
{"claim":"167–192 秒","log_file":"run-2026-09-13.md","log_line":"区间 167–192 秒","ok":true},
{"claim":"2 分 47 秒 ~ 3 分 12 秒","log_file":"run-2026-09-13.md","log_line":"167 秒 = 2 分 47 秒；192 秒 = 3 分 12 秒（换算）","ok":true},
{"claim":"28.8 秒成品","log_file":"run-2026-09-13.md","log_line":"生成音频 28.8 秒","ok":true},
{"claim":"比正常播放慢约 5.6–6.8 倍","log_file":"run-2026-09-13.md","log_line":"区间 5.56–6.39 | 5.91–6.78","ok":true},
{"claim":"最慢比最快慢约 15%","log_file":"run-2026-09-13.md","log_line":"四次结果波动约 15%","ok":true},
{"claim":"245 秒比 192 秒慢约 28%","log_file":"run-2026-09-13.md","log_line":"这次 245 秒（慢约 30%）","ok":false},
{"claim":"382 字切成 6 段","log_file":"runtime-errors.txt","log_line":"那次输入：382 字；引擎切段数：6 段","ok":true},
{"claim":"15.84 秒","log_file":"runtime-errors.txt","log_line":"产出文件时长：15.84 秒（只含第 1 段）","ok":true},
{"claim":"117 字","log_file":"run-2026-09-13.md","log_line":"要念 117 个字","ok":true},
{"claim":"切成 2 段","log_file":"run-2026-09-13.md","log_line":"引擎切成 2 段，正在拼接…","ok":true},
{"claim":"13 个文件","log_file":"复刻包文件清单","log_line":"清单中顶层文件 15 个，加子目录更多","ok":false},
{"claim":"install.bat 63 行 / 一键安装.bat 62 行","log_file":"无","log_line":"无日志依据","ok":false},
{"claim":"start.bat 96 行 / 一键生成.bat 91 行","log_file":"无","log_line":"无日志依据","ok":false},
{"claim":"tools/tts.py 171 行","log_file":"无","log_line":"无日志依据","ok":false},
{"claim":"tools/check.py 83 行","log_file":"无","log_line":"无日志依据","ok":false},
{"claim":"AMD Ryzen 7 5700G（8 核 16 线程）","log_file":"run-2026-09-13.md","log_line":"CPU：AMD Ryzen 7 5700G（8 核 16 线程）","ok":true},
{"claim":"27.9G 内存","log_file":"run-2026-09-13.md","log_line":"内存：27.9 G","ok":true},
{"claim":"无独立显卡","log_file":"run-2026-09-13.md","log_line":"无独立显卡","ok":true},
{"claim":"Windows","log_file":"run-2026-09-13.md","log_line":"系统：Windows 11","ok":true},
{"claim":"Apache-2.0 许可","log_file":"license-check.txt","log_line":"→ Apache License 2.0；模型权重也是 apache-2.0","ok":true},
{"claim":"可以商用","log_file":"license-check.txt","log_line":"代码与模型权重均为 Apache-2.0 —— 文章里「免费、可以商用」的结论成立","ok":true}
],

"checked":[
{"no":1,"result":"部分","evidence":"许可结论已补外部核实，与 license-check.txt 一致；但 GitHub LICENSE URL 未在日志摘要中给出，正文「官方仓库」表述略模糊"},
{"no":2,"result":"已改","evidence":"「约 7G 的东西（模型 + 运行环境）」+ 明细 5.05G / 1.88G，与日志一致；但「约 7G」与日志「6.94G」口径仍有细微不一致"},
{"no":3,"result":"已改","evidence":"「内存结论先说：8G 的电脑跑不了，16G 可以」已前置；但「跑不了」与日志「加载那一步撑不住」强度不同"},
{"no":4,"result":"已改","evidence":"补「别自己转格式，脚本用 ffmpeg 自动转；只要把文件名改成 我的录音.wav」，与日志 runtime-errors.txt 的修法一致"},
{"no":5,"result":"已改","evidence":"补「伪造他人发言、冒充真人打语音电话、生成让人误信是本人说的内容」，与台账 R5 处置一致"},
{"no":6,"result":"已改","evidence":"标题加「（早期观察，无日志）」+ 正文开头说明，与 runtime-errors.txt「当时没有留日志」一致"},
{"no":7,"result":"已改","evidence":"表格「9–16 秒」旁注明「下图这一次是 10 秒」，与日志「模型加载完成，用了 10 秒」一致"},
{"no":8,"result":"已改","evidence":"AI 声明已前置到开头，文末无重复，无缺失"},
{"no":9,"result":"已改","evidence":"runtime-memory-disk.txt 已删除矛盾的「5 MB」数据，只留自洽数据 + 记失败教训"}
],

"stats":{"numbers_total":28,"numbers_traced":22}
}