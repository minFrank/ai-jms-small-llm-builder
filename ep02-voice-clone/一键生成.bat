@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   本地声音包 · 一键生成
echo ============================================
echo.

rem 找一个能用的 Python
set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  py -3 --version >nul 2>nul && set PY=py -3
)
if "%PY%"=="" (
  echo x 没找到 Python。
  echo   请先安装 Python 3.10 或 3.11:https://www.python.org/downloads/
  echo   安装时务必勾选 "Add Python to PATH"。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

echo [1/3] 检查环境...
%PY% tools\check.py
if errorlevel 1 (
  echo.
  echo 环境还没就绪。若提示缺 CosyVoice,请先双击「一键安装.bat」。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 1
)

echo.
echo [2/3] 读取你的录音与文字...
if not exist "我的录音.wav" (
  echo x 找不到「我的录音.wav」。
  echo   用手机录音机录 20-30 秒,传到电脑,改名成 我的录音.wav 放在这个文件夹。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
if not exist "story.txt" (
  echo x 找不到 story.txt。把要念的文字存成 story.txt 放在这个文件夹。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
if not exist "我的录音说的是什么.txt" (
  echo x 找不到「我的录音说的是什么.txt」。
  echo   把你录音里念的那句话原样写进这个文件（必须一字不差,否则不像）。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
set /p VOICETEXT=<我的录音说的是什么.txt

echo.
echo [3/3] 开始生成（按 6 倍时长估算,380 字约需 11 分钟）...
echo.

rem 关键:合成必须用 CosyVoice 自己的 Python(它装了 torch 等依赖),
rem 用系统 Python 会直接报 "No module named 'torch'"。
set CPY=
if exist "%~dp0tools\CosyVoice\.venv\Scripts\python.exe" set CPY=%~dp0tools\CosyVoice\.venv\Scripts\python.exe
if not defined CPY if exist "%USERPROFILE%\AppData\Roaming\OmniVoice\engines\cosyvoice\CosyVoice\.venv\Scripts\python.exe" set CPY=%USERPROFILE%\AppData\Roaming\OmniVoice\engines\cosyvoice\CosyVoice\.venv\Scripts\python.exe
if not defined CPY (
  echo x 找不到 CosyVoice 的运行环境,请先双击「一键安装.bat」。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
echo · 使用环境:%CPY%
%CPY% tools\tts.py --text-file "story.txt" --voice "我的录音.wav" --voice-text "%VOICETEXT%" --out "output\故事.mp3"
if errorlevel 1 (
  echo.
  echo x 生成失败,请把上面的报错截图发给作者。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 3
)

echo.
echo 完成!音频在 output 文件夹里。
start "" "output"
if not "%KIT_NOPAUSE%"=="1" pause
