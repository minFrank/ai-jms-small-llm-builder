@echo off
setlocal
rem 中文 Windows 默认代码页是 GBK:让 python 的输出也按 GBK 走,避免乱码。
rem (不要用 chcp 65001:UTF-8 代码页下 bat 自身的中文行会被解析坏,
rem  实测报 ". was unexpected at this time." / "'…' is not recognized")
set PYTHONIOENCODING=gbk
cd /d "%~dp0"

echo ============================================
echo   本地声音包 · 一键安装（只需跑一次）
echo ============================================
echo.
echo   要下载约 7G 模型文件,请保证磁盘空间和网络。
echo   装好后离线也能用,以后不用再跑这个。
echo.
if not "%KIT_NOPAUSE%"=="1" pause

rem 找 Python:优先 py -3(最可靠),其次 python。
rem 必须校验它能建 venv —— 实测踩过:有的 python(比如随别的软件装进来的)
rem 连 pip 都没有,建 venv 会失败并报 "No module named pip",读者会看懵。
rem 版本优先:3.11 > 3.10 > 任意 3.x。
rem 别直接用 py -3 —— 实测它会挑到最新版(比如 3.14),而 CosyVoice 的依赖
rem 在那么新的版本上很可能装不上。
set PY=
py -3.11 -c "import venv, ensurepip" >nul 2>nul && set PY=py -3.11
if "%PY%"=="" ( py -3.10 -c "import venv, ensurepip" >nul 2>nul && set PY=py -3.10 )
if "%PY%"=="" ( py -3 -c "import venv, ensurepip" >nul 2>nul && set PY=py -3 )
if "%PY%"=="" ( python -c "import venv, ensurepip" >nul 2>nul && set PY=python )
if "%PY%"=="" (
  echo x 没找到能用的 Python^(需要带 venv 和 pip^)。
  echo   请到 https://www.python.org/downloads/ 装 Python 3.10 或 3.11,
  echo   安装时务必勾选 "Add Python to PATH",然后重新运行本脚本。
  echo   注意:Windows 应用商店里的那个 "python" 不行,请装官网版本。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 2
)
echo · 使用 Python:%PY%
%PY% --version

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
  if errorlevel 1 (
    echo.
    echo x 从 GitHub 下载失败 —— 国内网络很常见,不是你的问题。
    echo   正在用国内镜像地址重试...
    rmdir /s /q "%DEST%" 2>nul
    git clone --recursive https://gh-proxy.com/https://github.com/FunAudioLLM/CosyVoice.git "%DEST%"
    if errorlevel 1 (
      echo.
      echo x 镜像也失败了。请手动处理:
      echo   1^) 打开 https://gh-proxy.com/ 或 https://hf-mirror.com/
      echo   2^) 把 https://github.com/FunAudioLLM/CosyVoice 粘进去下载
      echo   3^) 解压后放进:%DEST%
      echo   然后重新运行本脚本。
      if not "%KIT_NOPAUSE%"=="1" pause
      exit /b 3
    )
    echo · 镜像下载成功。
  )
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
  echo x 模型下载失败 —— 国内网络很常见。
  echo   正在用 HF 镜像重试...
  set HF_ENDPOINT=https://hf-mirror.com
  python -c "from huggingface_hub import snapshot_download as s; s('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"
  if errorlevel 1 (
    echo x 镜像也失败。可手动从 https://hf-mirror.com/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 下载,
    echo   放进 %DEST%\pretrained_models\Fun-CosyVoice3-0.5B 后重新运行本脚本。
if not "%KIT_NOPAUSE%"=="1" pause
  exit /b 5
)

echo.
echo 安装完成!以后双击「一键生成.bat」就能用了。
if not "%KIT_NOPAUSE%"=="1" pause
