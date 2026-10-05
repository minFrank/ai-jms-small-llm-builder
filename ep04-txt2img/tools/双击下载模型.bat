@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   04 期一键包 · 第一步: 下载画图模型
echo ============================================
echo.
echo 这一步会下载约 4.3GB 的画图模型, 只需执行一次。
echo 已经下载过的话, 会自动跳过。
echo.

set "MODEL=v1-5-pruned-emaonly.safetensors"
set "URL=https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"

if exist "%MODEL%" goto :exists

echo [1/2] 正在下载模型, 网速慢的话请耐心等待...
curl -L --retry 3 --retry-delay 2 -o "%MODEL%.part" "%URL%"
if errorlevel 1 goto :dlfail

echo [2/2] 校验文件大小...
for %%A in ("%MODEL%.part") do set "SIZE=%%~zA"
if %SIZE% LSS 4000000000 goto :sizfail
move /y "%MODEL%.part" "%MODEL%" >nul
goto :done

:exists
echo [跳过] 模型已存在, 不用再下:
for %%A in ("%MODEL%") do echo         %%~zA 字节
goto :done

:dlfail
echo.
echo [失败] 下载中断。通常是网络不通, 或者系统太老没有 curl。
echo        处理办法: 检查网络后再次双击本文件, 会重新下载。
del "%MODEL%.part" 2>nul
pause
exit /b 1

:sizfail
echo [失败] 只下了 %SIZE% 字节, 应约 42.7 亿字节, 说明下载不完整。
echo        处理办法: 再次双击本文件重新下载即可。
del "%MODEL%.part" 2>nul
pause
exit /b 1

:done
echo.
echo [完成] 模型就绪, 下一步双击 双击生成.bat 画第一张图。
echo.
pause
exit /b 0
