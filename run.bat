@echo off
echo ========================================
echo Sys-Mentor - 系统导师
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [信息] Python 版本:
python --version
echo.

REM 检查虚拟环境
if not exist "venv" (
    echo [信息] 检测到虚拟环境不存在，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [信息] 虚拟环境创建成功
    echo.
)

REM 激活虚拟环境
echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖
echo [信息] 检查依赖...
pip list | findstr /i "openai rich duckduckgo" >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [警告] 依赖安装可能失败，但继续尝试运行...
    )
)

echo.
echo [信息] 启动 Sys-Mentor...
echo ========================================
echo.

REM 检查 .env 文件
if not exist ".env" (
    echo [警告] 未找到 .env 文件
    echo.
    echo [提示] 请先复制 .env.example 为 .env 并填写 API 密钥
    echo.
    echo [提示] 按任意键继续运行（部分功能将不可用）...
    pause >nul
)

REM 运行主程序
python main.py

REM 恢复环境
deactivate >nul 2>&1

pause
