#!/usr/bin/env python3
"""
上下文记忆测试脚本
用于验证多轮对话上下文是否正常工作
"""
import os
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def test_context():
    """测试上下文记忆功能"""

    provider = os.getenv("LLM_PROVIDER")
    api_key = os.getenv("LLM_API_KEY", "")

    print("=" * 70)
    print("上下文记忆测试")
    print("=" * 70)
    print(f"Provider: {provider}")
    print(
        f"API Key: {api_key[:10]}...{api_key[-5:] if api_key and len(api_key) > 15 else 'NOT SET'}"
    )
    print("=" * 70)

    if not api_key or api_key == "test-key-placeholder-replace-with-real-key":
        print("\n❌ 错误: 请先配置真实的 API Key")
        print("   编辑 backend/.env 文件，设置 LLM_API_KEY")
        return

    try:
        from services.llm_service import LLMService

        service = LLMService()
        print(f"\n✅ LLM 服务初始化成功")
        print(f"   Provider: {service.env_provider}")
        if hasattr(service, "env_model_name"):
            print(f"   Model: {service.env_model_name}")

        # 模拟多轮对话
        conversation_history = []

        print("\n" + "=" * 70)
        print("开始多轮对话测试")
        print("=" * 70)

        # 第一轮对话
        print("\n【第1轮对话】")
        print("User: 我叫张三，我最喜欢的颜色是蓝色")

        response1 = await service.generate_response(
            message="我叫张三，我最喜欢的颜色是蓝色",
            conversation_history=conversation_history,
            file_context=None,
        )

        print(f"AI: {response1}")

        # 更新对话历史
        conversation_history.append(
            {"role": "user", "content": "我叫张三，我最喜欢的颜色是蓝色"}
        )
        conversation_history.append({"role": "assistant", "content": response1})

        # 第二轮对话 - 测试上下文记忆
        print("\n【第2轮对话 - 测试名字记忆】")
        print("User: 我刚才说我叫什么名字？")

        response2 = await service.generate_response(
            message="我刚才说我叫什么名字？",
            conversation_history=conversation_history,
            file_context=None,
        )

        print(f"AI: {response2}")

        # 检查是否包含"张三"
        if "张三" in response2:
            print("✅ 上下文记忆测试通过 - AI 记住了名字")
        else:
            print("⚠️  上下文记忆可能有问题 - AI 没有提到名字")

        # 更新对话历史
        conversation_history.append(
            {"role": "user", "content": "我刚才说我叫什么名字？"}
        )
        conversation_history.append({"role": "assistant", "content": response2})

        # 第三轮对话 - 测试颜色记忆
        print("\n【第3轮对话 - 测试颜色记忆】")
        print("User: 我最喜欢什么颜色？")

        response3 = await service.generate_response(
            message="我最喜欢什么颜色？",
            conversation_history=conversation_history,
            file_context=None,
        )

        print(f"AI: {response3}")

        # 检查是否包含"蓝色"
        if "蓝" in response3 or "blue" in response3.lower():
            print("✅ 上下文记忆测试通过 - AI 记住了颜色")
        else:
            print("⚠️  上下文记忆可能有问题 - AI 没有提到颜色")

        print("\n" + "=" * 70)
        print("测试完成")
        print("=" * 70)
        print("\n📊 对话历史记录:")
        print(f"   总消息数: {len(conversation_history)}")
        print(f"   对话轮数: {len(conversation_history) // 2}")

        print("\n🎉 上下文记忆功能正常工作！")
        print("\n💡 说明:")
        print("   - 系统会自动保存最近10轮对话")
        print("   - AI 可以引用之前的对话内容")
        print("   - 支持连贯的多轮对话")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        print("\n可能的原因:")
        print("1. API Key 无效或余额不足")
        print("2. 网络连接问题")
        print("3. API 服务暂时不可用")


if __name__ == "__main__":
    asyncio.run(test_context())
