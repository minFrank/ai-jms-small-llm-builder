@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   Local Voice Kit - Install (run ONCE only)
echo   本地声音包 · 一键安装（只需跑一次）
echo ============================================
echo.
echo   要下载约 7G 模型文件,请保证磁盘空间和网络。
echo   装好后离线也能用,以后不用再跑这个。
echo.
if not "%KIT_NOPAUSE%"=="1" pause

set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" ( py -3 --version >nul 2>nul && set PY=py -3 )
if "%PY%"=="" (
  echo x 没找到 Python。请先装 Python 3.10/3.11 并勾选 Add Python to PATH。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

where git >nul 2>nul
if errorlevel 1 (
  echo x 没找到 git。请先装 Git:https://git-scm.com/downloads
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)

set DEST=%~dp0tools\CosyVoice
if exist "%DEST%\cosyvoice" (
  echo · 已经装过了,跳过下载。
) else (
  echo [1/3] 下载 CosyVoice 源码（含第三方依赖,可能要几分钟）...
  git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git "%DEST%"
  if errorlevel 1 ( echo x 下载失败,检查网络后重试。 & pause & exit /b 3 )
)

echo.
echo [2/3] 安装运行环境（要几分钟）...
cd /d "%DEST%"
%PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
pip install huggingface_hub modelscope
if errorlevel 1 ( echo x 依赖安装失败,把报错发给作者。 & pause & exit /b 4 )

echo.
echo [3/3] 下载模型文件（约 5G,最慢的一步）...
python -c "from huggingface_hub import snapshot_download as s; s('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"
if errorlevel 1 (
  echo x 模型下载失败。国内网络可先设镜像后重试:
  echo     set HF_ENDPOINT=https://hf-mirror.com
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 5
)

echo.
echo 安装完成!以后双击 start.bat 就能用了。
if not "%KIT_NOPAUSE%"=="1" pause
