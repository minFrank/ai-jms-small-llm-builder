@echo off
setlocal
rem 中文 Windows 默认代码页是 GBK:让 python 的输出也按 GBK 走,避免乱码。
rem (不要用 chcp 65001:UTF-8 代码页下 bat 自身的中文行会被解析坏,
rem  实测报 ". was unexpected at this time." / "'…' is not recognized")
set PYTHONIOENCODING=gbk
cd /d "%~dp0"

echo ============================================
echo   Local Voice Kit - Generate
echo   本地声音包 · 一键生成
echo ============================================
echo.

rem 找一个能用的 Python
set PY=
py -3.11 -c "import venv" >nul 2>nul && set PY=py -3.11
if "%PY%"=="" ( py -3.10 -c "import venv" >nul 2>nul && set PY=py -3.10 )
if "%PY%"=="" ( py -3 -c "import venv" >nul 2>nul && set PY=py -3 )
if "%PY%"=="" ( where python >nul 2>nul && set PY=python )
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
  echo 环境还没就绪。若提示缺 CosyVoice,请先运行 install.bat（或「一键安装.bat」）。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 1
)

echo.
echo [2/3] 读取你的录音与文字...

rem 录音与录音文本:英文名优先,没放英文名就找中文名 —— 两种都认
set VOICEWAV=
rem 格式不限（wav / m4a / mp3）：不是 16k 单声道 wav 时，tts.py 会用 ffmpeg 自动转
for %%E in (wav m4a mp3 WAV M4A MP3) do (
  if not defined VOICEWAV if exist "my-recording.%%E" set VOICEWAV=my-recording.%%E
  if not defined VOICEWAV if exist "我的录音.%%E" set VOICEWAV=我的录音.%%E
)
if not defined VOICEWAV (
  echo x 找不到录音文件。
  echo   放一个 my-recording.wav / .m4a / .mp3（或中文名「我的录音.*」）到这个文件夹。
  echo   手机录音机默认存 m4a,直接放进来就行,脚本会自动转格式。
  echo   用手机录音机录 20-30 秒,别用微信语音,那是压缩过的。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

set SAIDTXT=
if exist "what-i-said.txt" set SAIDTXT=what-i-said.txt
if not defined SAIDTXT if exist "我的录音说的是什么.txt" set SAIDTXT=我的录音说的是什么.txt
if not defined SAIDTXT (
  echo x 找不到录音文本。
  echo   放一个 what-i-said.txt（或「我的录音说的是什么.txt」）,
  echo   把你录音里念的那句话原样写进去,必须一字不差。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

if not exist "story.txt" (
  echo x 找不到 story.txt。把要念的文字存成 story.txt 放在这个文件夹。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

echo · 用录音:%VOICEWAV%
echo · 用文本:%SAIDTXT%

echo.
echo [3/3] 开始生成...
echo.

rem 关键:合成必须用 CosyVoice 自己的 Python（它装了 torch 等依赖）,
rem 用系统 Python 会直接报 "No module named 'torch'"。
set CPY=
if exist "%~dp0tools\CosyVoice\.venv\Scripts\python.exe" set CPY=%~dp0tools\CosyVoice\.venv\Scripts\python.exe
if not defined CPY if exist "%USERPROFILE%\AppData\Roaming\OmniVoice\engines\cosyvoice\CosyVoice\.venv\Scripts\python.exe" set CPY=%USERPROFILE%\AppData\Roaming\OmniVoice\engines\cosyvoice\CosyVoice\.venv\Scripts\python.exe
if not defined CPY (
  echo x 找不到 CosyVoice 的运行环境,请先运行 install.bat（或「一键安装.bat」）。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
echo · 使用环境:%CPY%
%CPY% tools\tts.py --text-file "story.txt" --voice "%VOICEWAV%" --voice-text-file "%SAIDTXT%" --out "output\story.mp3"
if errorlevel 1 (
  echo.
  echo x 生成失败,请把上面的报错截图发给作者。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 3
)

echo.
echo 完成!音频在 output 文件夹里(output\story.mp3)。
start "" "output"
if not "%KIT_NOPAUSE%"=="1" pause
