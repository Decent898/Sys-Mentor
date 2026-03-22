#!/bin/bash

# Sys-Mentor 启动脚本 (Linux/Mac)

echo "========================================"
echo "Sys-Mentor - 系统导师"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

echo "[信息] Python 版本:"
python3 --version
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "[信息] 检测到虚拟环境不存在，正在创建..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
    echo "[信息] 虚拟环境创建成功"
    echo ""
fi

# 激活虚拟环境
echo "[信息] 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "[信息] 检查依赖..."
if ! pip list | grep -qi "openai\|rich\|duckduckgo"; then
    echo "[信息] 正在安装依赖..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[警告] 依赖安装可能失败，但继续尝试运行..."
    fi
fi

echo ""
echo "[信息] 启动 Sys-Mentor..."
echo "========================================"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 文件"
    echo ""
    echo "[提示] 请先复制 .env.example 为 .env 并填写 API 密钥"
    echo ""
    read -p "按回车继续运行（部分功能将不可用）..."
fi

# 运行主程序
python main.py

# 恢复环境
deactivate
