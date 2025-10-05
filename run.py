#!/usr/bin/env python3
"""
启动脚本
推荐使用: uv run run.py
"""

import subprocess
import sys
import os

def main():
    """启动Streamlit应用"""
    try:
        # 检查是否在正确的目录
        if not os.path.exists("app.py"):
            print("错误: 未找到app.py文件，请确保在项目根目录运行此脚本")
            sys.exit(1)

        # 启动Streamlit应用
        print("正在启动基金量化分析平台...")
        print("浏览器将自动打开，如果未打开请访问: http://localhost:48501")
        print("按 Ctrl+C 停止应用")

        # 检测是否在uv环境中
        if os.getenv("UV_IN_SCRIPT") == "1" or os.path.exists(os.path.join(os.path.dirname(__file__), ".venv")):
            # 在uv环境中运行
            subprocess.run([
                "uv", "run", "streamlit", "run", "app.py",
                "--server.port", "48501",
                "--server.address", "localhost",
                "--browser.gatherUsageStats", "false"
            ], check=True)
        else:
            # 直接运行
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.port", "48501",
                "--server.address", "localhost",
                "--browser.gatherUsageStats", "false"
            ], check=True)

    except KeyboardInterrupt:
        print("\n应用已停止")
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()