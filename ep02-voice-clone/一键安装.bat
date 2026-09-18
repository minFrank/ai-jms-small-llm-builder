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
rem 先按版本号找（官方安装器装的会注册版本号）
for %%V in (3.11 3.10 3.12) do if not defined PY py -%%V -c "import venv, ensurepip" >nul 2>nul && set PY=py -%%V
rem 再兜底找 -V:<公司>/<实现> 形态（uv / 独立发行版装的不注册版本号，
rem 只能用 py -0 里那个 -V: 全名寻址 —— 实测 Astral/CPython3.11.16 就是这样）
if not defined PY for /f "tokens=1" %%A in ('py -0 2^>nul ^| findstr /i "3.11 3.10 3.12"') do if not defined PY set PY=py %%A
if not defined PY goto :PY_PROBLEM
echo · 使用 Python:%PY%（本包要求 3.10 / 3.11 / 3.12）
goto :PY_OK

:PY_PROBLEM
py -3 -c "import sys" >nul 2>nul
if errorlevel 1 goto :NO_PYTHON
echo x 你机器上的 Python 太新了，本包需要 3.10 / 3.11 / 3.12。
echo   CosyVoice 的依赖钉死在 torch 2.3.1 和 numpy 1.26.4 上，
echo   这两个在新版 Python 上装不了。实测 3.14：torch 直接找不到该版本。
echo.
echo   请装一个 Python 3.11，和现有的可以共存：
echo     https://www.python.org/downloads/release/python-3119/
echo   选 Windows installer 64-bit 那一行；装完重新运行本脚本。
echo   注意：Windows 应用商店里的 python 不行，请装官网版本。
if not "%KIT_NOPAUSE%"=="1" pause
exit /b 2

:NO_PYTHON
echo x 没找到 Python。请先装 Python 3.11，再重新运行本脚本：
echo   https://www.python.org/downloads/release/python-3119/
if not "%KIT_NOPAUSE%"=="1" pause
exit /b 2

:PY_OK
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
    rem 关键(实测):--recursive 拉下来的**子模块 URL 仍然是 github.com**,
    rem 只把主仓地址换成镜像没用 —— 子模块照样直连 GitHub 并失败。
    rem 实测卡在 third_party/Matcha-TTS: RPC failed; curl 56 schannel。
    rem 所以用 insteadOf 把 github.com 整体重定向到镜像,主仓与子模块一起走。
    rem 用环境变量传 git 配置,避免 bat 里的引号嵌套问题。
    set GIT_CONFIG_COUNT=1
    set GIT_CONFIG_KEY_0=url.https://gh-proxy.com/https://github.com/.insteadOf
    set GIT_CONFIG_VALUE_0=https://github.com/
    git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git "%DEST%"
    set GIT_CONFIG_COUNT=
    set GIT_CONFIG_KEY_0=
    set GIT_CONFIG_VALUE_0=
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
  )
)

echo.
echo [2/3] 安装运行环境（要几分钟）...
cd /d "%DEST%"
%PY% -m venv .venv
call .venv\Scripts\activate.bat
rem ===== 依赖安装(2026-09-15 实测修正)=====
rem 三个坑叠在一起,少修一个都装不进去:
rem  ① PyPI 直连国内经常中断(torch 单个包就 2G)→ 走清华镜像,失败再回退官方源。
rem  ② openai-whisper 构建时报 "ModuleNotFoundError: No module named 'pkg_resources'"。
rem     **不要**以为"装最新 setuptools 就行" —— 实测 setuptools 81+ 已移除 pkg_resources,
rem     装 84 版照样报这个错。要的是 81 以下的旧版。
rem  ③ 光在 venv 里降级还不够:pip 默认用**构建隔离**,会在临时环境里装最新 setuptools,
rem     所以必须加 --no-build-isolation,让构建用我们这边的 setuptools<81。
rem 关键性能项:CosyVoice 的 requirements.txt 里有**两个国外 extra-index 源**
rem   (download.pytorch.org/whl/cu121 与 aiinfra.pkgs.visualstudio.com) ——
rem 国内访问它们会卡 SSL,而 pip 默认对**每个包重试 5 次**,实测日志 600+ 行里
rem 绝大部分是这种重试警告,进度条一动不动。它们本来就只服务 Linux/CUDA,
rem Windows 用不上 —— 但不能改官方 requirements.txt(那是项目的),
rem 所以把重试次数与超时压到最小,让它快速失败并回落主源。
set PIP_RETRIES=1
set PIP_TIMEOUT=15
set PIP_DISABLE_PIP_VERSION_CHECK=1
python -m pip install --upgrade pip -q -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install "setuptools<81" wheel cython -q -i https://pypi.tuna.tsinghua.edu.cn/simple --retries 1 --timeout 15
if errorlevel 1 python -m pip install "setuptools<81" wheel cython -q
set DEPS_OK=1
pip install --no-build-isolation -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --retries 1 --timeout 15
if errorlevel 1 (
  echo · 国内镜像装失败,改用官方源重试...
  pip install --no-build-isolation -r requirements.txt --retries 1 --timeout 15
)
if errorlevel 1 set DEPS_OK=
pip install huggingface_hub modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple --retries 1 --timeout 15
if errorlevel 1 pip install huggingface_hub modelscope
if not defined DEPS_OK goto :DEPS_FAILED
goto :DEPS_DONE

:DEPS_FAILED
echo x 依赖安装失败(requirements.txt 没装进去)。
echo   上面最后一条 pip 报错就是原因,把它发给作者。
if not "%KIT_NOPAUSE%"=="1" pause
exit /b 4

:DEPS_DONE
if errorlevel 1 ( echo x 依赖安装失败,把报错发给作者。 & pause & exit /b 4 )

echo.
rem 模型已存在就跳过 —— 否则每次重跑本脚本都会重新下 5G(实测很常见:
rem 前面几步失败后重跑,模型其实已经下好了)。判据是权重文件在不在。
if exist "%DEST%\pretrained_models\Fun-CosyVoice3-0.5B\llm.pt" (
  echo · 模型已存在,跳过下载。
  goto :MODEL_DONE
)

echo [3/3] 下载模型文件（约 5G,最慢的一步）...
rem 关键(实测):新版 huggingface_hub 默认启用 Xet 传输,走 us.aws.cdn.hf.co ——
rem 国内连不上,会在下载到一半时报 "CAS Client Error / error sending request for url
rem (https://us.aws.cdn.hf.co/...)"。hf-mirror 不代理 Xet,所以只设 HF_ENDPOINT 没用。
rem 必须关掉 Xet,让它回到普通 HTTP 下载。
set HF_HUB_DISABLE_XET=1
set HF_HUB_ENABLE_HF_TRANSFER=0
python -c "from huggingface_hub import snapshot_download as s; s('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"
if errorlevel 1 (
  echo x 模型下载失败 —— 国内网络很常见。
  echo   正在用 HF 镜像重试...
  set HF_ENDPOINT=https://hf-mirror.com
  python -c "from huggingface_hub import snapshot_download as s; s('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"
   if errorlevel 1 (
     rem 第三条路(实测最稳):ModelScope 有官方同步的同一模型。本机实测 HF 全链路
     rem 不通(直连 SSL 失败 + hf-mirror 超时 + 代理失效)时,只有这条能下下来;
     rem 国内直连实测 2.8GB/s。
     echo   改用 ModelScope 官方镜像下载...
     python -c "from modelscope import snapshot_download as s; s('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"
   )
   if errorlevel 1 (
     echo x 三条路都没成功(HF 直连 / hf-mirror / ModelScope)。
     echo   可手动下载后放进本包:
     echo     ModelScope: https://modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512
     echo     放到 %DEST%\pretrained_models\Fun-CosyVoice3-0.5B 后重新运行本脚本。
     if not "%KIT_NOPAUSE%"=="1" pause
     exit /b 5
   )

echo.
:MODEL_DONE

echo 安装完成!以后双击「一键生成.bat」就能用了。
if not "%KIT_NOPAUSE%"=="1" pause
