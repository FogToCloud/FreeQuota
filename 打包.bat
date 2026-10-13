@echo off
REM ============================================================
REM FreeQuota 一键打包为 Windows exe（给自己或别人重新构建用）
REM 前提：电脑已装 Python 3.10+，且已勾选「Add to PATH」
REM 用法：双击本文件即可（会打开一个黑色窗口，等它跑完）
REM 产物：dist\FreeQuota\FreeQuota.exe  —— 双击就能用
REM ============================================================
setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 Python，请先到 python.org 安装，并勾选 Add to PATH。
    pause
    exit /b 1
)

echo [1/3] 安装依赖（streamlit / pyinstaller）……
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [2/3] 执行 PyInstaller 打包（首次较慢，请耐心等待）……
python -m PyInstaller FreeQuota.spec

echo [3/3] 完成！
echo 双击 dist\FreeQuota\FreeQuota.exe 即可使用。
echo 首次运行会自动生成 config.json，按提示填入你的免费 Key。
pause
endlocal
