#!/bin/bash
# 快速启动脚本

echo "正在启动基金量化分析平台..."

# 检查是否安装了uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到uv，请先安装uv"
    echo "安装方法: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 检查是否存在虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    uv venv
fi

# 同步依赖
echo "同步依赖..."
uv sync

# 启动应用
echo "启动应用..."
echo "应用将在浏览器中打开: http://localhost:48501"
echo "按 Ctrl+C 停止应用"

uv run streamlit run app.py --server.port 48501