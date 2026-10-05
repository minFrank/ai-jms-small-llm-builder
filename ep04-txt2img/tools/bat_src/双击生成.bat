@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   04 期一键包 · 第二步: 画一张图
echo ============================================
echo.

if not exist "v1-5-pruned-emaonly.safetensors" goto :nomodel
if not exist "prompt.txt" goto :noprompt
if not exist "sd-cli.exe" goto :noexe

set /p DESC=<prompt.txt
echo 你要画的: %DESC%
echo 正在生成, 512x512、20 步, 没有独立显卡的电脑通常要等几分钟...
echo.

sd-cli.exe -m "v1-5-pruned-emaonly.safetensors" --prompt-file prompt.txt -W 512 -H 512 --steps 20 -s 42 -o result.png
if errorlevel 1 goto :failed

echo.
echo [完成] 图已生成: result.png, 就在本文件夹里
echo        想换一张: 用记事本改 prompt.txt 里的句子, 再次双击本文件。
echo.
pause
exit /b 0

:nomodel
echo [停] 没找到模型文件 v1-5-pruned-emaonly.safetensors
echo       请先双击 双击下载模型.bat, 下载完成后再回来。
echo.
echo 当前文件夹是: %cd%
pause
exit /b 1

:noprompt
echo [停] 没找到 prompt.txt, 也就是没有告诉它要画什么
echo       处理办法: 新建一个文本文件, 改名为 prompt.txt, 里面写一句英文描述。
echo.
echo 当前文件夹是: %cd%
dir /b prompt.txt 2>nul
pause
exit /b 1

:noexe
echo [停] 没找到 sd-cli.exe, 也就是画图程序本体
echo       处理办法: 重新解压工具包, 确认本文件和 sd-cli.exe 在同一文件夹。
echo.
echo 当前文件夹是: %cd%
pause
exit /b 1

:failed
echo.
echo [失败] 生成失败。
echo        常见原因一: 内存不足, 先关掉其他程序再试。
echo        常见原因二: prompt.txt 被清空了, 里面要有字。
echo.
pause
exit /b 1
