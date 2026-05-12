#!/usr/bin/env bash
# FloatVocab 启动脚本
# 用法：bash init.sh
# 设置 RUN_START_COMMAND=1 可直接启动应用

set -euo pipefail

INSTALL_CMD="pip install -r requirements.txt 2>/dev/null || true"
VERIFY_CMD="python -m pytest tests/ -v"
START_CMD="python app.py"

echo "=== FloatVocab Init ==="
echo "工作目录: $(pwd)"
echo ""

echo "--- 安装依赖 ---"
eval "$INSTALL_CMD"
echo ""

echo "--- 验证基础状态 ---"
if eval "$VERIFY_CMD"; then
    echo ""
    echo "验证通过。"
else
    echo ""
    echo "验证失败。请先修复基础状态再继续开发。"
    exit 1
fi

echo ""
echo "--- 启动命令 ---"
echo "Python GUI: $START_CMD"
echo "Electron:   cd electron && npm run dev"
echo ""

if [[ "${RUN_START_COMMAND:-0}" == "1" ]]; then
    echo "启动应用..."
    eval "$START_CMD"
fi
