# 先看这个(READ ME FIRST)

这个文件夹有两种入口,**用哪个都一样**:

| 想做什么 | 中文名 | 英文名 |
|---|---|---|
| 第一步:安装(只需一次) | `一键安装.bat` | `install.bat` |
| 第三步:生成音频 | `一键生成.bat` | `start.bat` |

> 为什么有两个?因为有些网盘 / 解压工具会把**中文文件名搞乱**。
> 两个文件内容一样,而且**互相兼容** —— 你放哪种名字的录音素材它都认。

## 三步

1. **双击安装**(`一键安装.bat` 或 `install.bat`)—— 会下载约 7–12G（模型+环境，看下载源）,慢,但只需一次
2. **放三样东西**到这个文件夹:

   | 放什么 | 英文名(推荐) | 中文名 |
   |---|---|---|
   | 你的录音(手机录音机录 20–30 秒) | `my-recording.wav` | `我的录音.wav` |
   | 录音里你念的那句话(一字不差) | `what-i-said.txt` | `我的录音说的是什么.txt` |
   | 要念的文字 | `story.txt` | `story.txt` |

3. **双击生成**(`一键生成.bat` 或 `start.bat`)—— 结果在 `output\story.mp3`

## 要等多久

电脑忙 **5.6–6.8 分钟**,换来 **1 分钟**成品(没有独立显卡的正常速度)。
所以要念 10 分钟的内容,大约等半小时。

## 前提

- 内存 **16G 起**(8G 跑不动)
- 磁盘留 **10G** 以上
- **不需要独立显卡**
- 别拿微信语音当录音素材(压缩太狠,出来的声音会发闷)

## 出问题

- 提示缺 Python → 装 Python 3.10/3.11,安装时勾选 "Add Python to PATH"
- 提示缺 git → 装 Git:https://git-scm.com/downloads
- 模型下载失败 → 国内网络先设镜像再重试:`set HF_ENDPOINT=https://hf-mirror.com`
- 其他报错 → 截图发给作者

详细说明与实测数据见 `README.md`;原始运行日志见 `logs/`。

## Community (WeChat official account)

Usage notes, measured data and updates for this package are posted on the WeChat
official account "AI 积木师" (search the name inside WeChat to follow).

Questions are welcome there.

