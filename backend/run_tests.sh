#!/bin/bash

# AI Chat System - 测试运行脚本

echo "🧪 AI Chat System - 测试套件"
echo "================================"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 检查参数
if [ "$1" == "all" ]; then
    echo "📋 运行所有测试..."
    python -m pytest tests/ -v
elif [ "$1" == "api" ]; then
    echo "📋 运行 API 测试..."
    python -m pytest tests/test_api.py -v
elif [ "$1" == "llm" ]; then
    echo "📋 运行 LLM 服务测试..."
    python -m pytest tests/test_llm_service.py -v
elif [ "$1" == "conversation" ]; then
    echo "📋 运行对话服务测试..."
    python -m pytest tests/test_conversation_service.py -v
elif [ "$1" == "file" ]; then
    echo "📋 运行文件服务测试..."
    python -m pytest tests/test_file_service.py -v
elif [ "$1" == "coverage" ]; then
    echo "📊 运行测试并生成覆盖率报告..."
    python -m pytest tests/ --cov=services --cov=main --cov-report=html --cov-report=term
    echo ""
    echo "✅ 覆盖率报告已生成: htmlcov/index.html"
elif [ "$1" == "context" ]; then
    echo "🔄 运行上下文记忆集成测试..."
    echo "⚠️  注意：此测试需要真实的 API Key"
    python tests/test_context.py
elif [ "$1" == "quick" ]; then
    echo "⚡ 快速测试（跳过慢速测试）..."
    python -m pytest tests/ -v -m "not slow"
else
    echo ""
    echo "用法: ./run_tests.sh [选项]"
    echo ""
    echo "选项:"
    echo "  all          - 运行所有单元测试"
    echo "  api          - 运行 API 端点测试"
    echo "  llm          - 运行 LLM 服务测试"
    echo "  conversation - 运行对话服务测试"
    echo "  file         - 运行文件服务测试"
    echo "  coverage     - 运行测试并生成覆盖率报告"
    echo "  context      - 运行上下文记忆集成测试（需要真实 API Key）"
    echo "  quick        - 快速测试（跳过慢速测试）"
    echo ""
    echo "示例:"
    echo "  ./run_tests.sh all"
    echo "  ./run_tests.sh api"
    echo "  ./run_tests.sh coverage"
    exit 1
fi

echo ""
echo "✅ 测试完成！"
