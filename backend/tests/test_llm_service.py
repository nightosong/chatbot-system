"""
Unit tests for LLM Service
测试 LLM 服务的各种功能，包括用户配置模型和环境变量模型
"""

import pytest  # type: ignore
from unittest.mock import Mock, patch, AsyncMock
from services.llm_service import LLMService


class TestLLMServiceInitialization:
    """测试 LLM Service 初始化"""

    def test_init_without_env_vars(self, monkeypatch):
        """测试无环境变量时的初始化"""
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        service = LLMService()

        assert service.env_api_key is None
        assert service.env_provider is None

    def test_init_with_env_vars(self, monkeypatch):
        """测试有环境变量时的初始化"""
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("MODEL_NAME", "gemini-1.5-flash")

        service = LLMService()

        assert service.env_api_key == "test-key"
        assert service.env_provider == "gemini"
        assert service.env_model_name == "gemini-1.5-flash"


class TestPlatformConfiguration:
    """测试平台配置"""

    def test_platform_config_structure(self):
        """测试平台配置结构"""
        service = LLMService()

        assert "deepseek" in service.PLATFORM_CONFIG
        assert "kimi" in service.PLATFORM_CONFIG
        assert "qwen" in service.PLATFORM_CONFIG
        assert "openai" in service.PLATFORM_CONFIG
        assert "gemini" in service.PLATFORM_CONFIG

        # 验证每个平台都有必需的字段
        for platform, config in service.PLATFORM_CONFIG.items():
            assert "base_url" in config
            assert "default_model" in config

    def test_get_base_url(self):
        """测试获取 base URL"""
        service = LLMService()

        assert service._get_base_url("deepseek") == "https://api.deepseek.com"
        assert service._get_base_url("kimi") == "https://api.moonshot.cn/v1"
        assert (
            service._get_base_url("qwen")
            == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        assert service._get_base_url("openai") is None
        assert service._get_base_url("gemini") is None

    def test_get_default_model_name(self):
        """测试获取默认模型名称"""
        service = LLMService()

        assert service._get_default_model_name("deepseek") == "deepseek-chat"
        assert service._get_default_model_name("kimi") == "moonshot-v1-8k"
        assert service._get_default_model_name("qwen") == "qwen-turbo"
        assert service._get_default_model_name("openai") == "gpt-3.5-turbo"
        assert service._get_default_model_name("gemini") == "gemini-1.5-flash"


class TestContextBuilding:
    """测试上下文构建"""

    def test_build_context_for_gemini_simple(self):
        """测试简单的 Gemini 上下文构建"""
        service = LLMService()

        context = service._build_context_for_gemini(
            message="Hello", conversation_history=[], file_context=None
        )

        assert "User: Hello" in context
        assert "[File Content]" not in context
        assert "[Conversation History]" not in context

    def test_build_context_for_gemini_with_history(self):
        """测试带历史记录的 Gemini 上下文构建"""
        service = LLMService()
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]

        context = service._build_context_for_gemini(
            message="How are you?", conversation_history=history, file_context=None
        )

        assert "[Conversation History]" in context
        assert "User: Hi" in context
        assert "Assistant: Hello!" in context
        assert "User: How are you?" in context

    def test_build_context_for_gemini_with_file(self):
        """测试带文件上下文的 Gemini 上下文构建"""
        service = LLMService()

        context = service._build_context_for_gemini(
            message="What's in the file?",
            conversation_history=[],
            file_context="File content here",
        )

        assert "[File Content]" in context
        assert "File content here" in context
        assert "[End of File Content]" in context

    def test_build_messages_for_openai_simple(self):
        """测试简单的 OpenAI 消息构建"""
        service = LLMService()

        messages = service._build_messages_for_openai(
            message="Hello", conversation_history=[], file_context=None
        )

        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    def test_build_messages_for_openai_with_history(self):
        """测试带历史记录的 OpenAI 消息构建"""
        service = LLMService()
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]

        messages = service._build_messages_for_openai(
            message="How are you?", conversation_history=history, file_context=None
        )

        assert len(messages) == 4  # system + 2 history + user
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hi"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hello!"

    def test_history_truncation(self):
        """测试历史记录截断（最多20条）"""
        service = LLMService()

        # 创建30条历史记录
        history = []
        for i in range(30):
            history.append({"role": "user", "content": f"Message {i}"})
            history.append({"role": "assistant", "content": f"Response {i}"})

        messages = service._build_messages_for_openai(
            message="Current message", conversation_history=history, file_context=None
        )

        # system + 20 history + current = 22
        assert len(messages) == 22


class TestGenerateResponse:
    """测试响应生成"""

    @pytest.mark.asyncio
    async def test_generate_with_user_config(self, sample_model_config):
        """测试使用用户配置生成响应"""
        service = LLMService()

        with patch.object(
            service, "_generate_with_config", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Test response"

            response = await service.generate_response(
                message="Test message", model_config=sample_model_config
            )

            assert response == "Test response"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_without_any_config(self, monkeypatch):
        """测试无任何配置时抛出错误"""
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        service = LLMService()

        with pytest.raises(ValueError) as exc_info:
            await service.generate_response(message="Test")

        assert "No model configuration available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_with_env_fallback(self, monkeypatch):
        """测试回退到环境变量配置"""
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        service = LLMService()

        with patch.object(
            service, "_generate_with_config", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Env response"

            response = await service.generate_response(
                message="Test message", model_config=None
            )

            assert response == "Env response"
            # 验证使用了环境变量配置
            call_args = mock_generate.call_args[0]
            config = call_args[3]  # model_config 参数
            assert config["provider"] == "gemini"
            assert config["api_key"] == "test-key"


class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_missing_api_key_in_config(self):
        """测试配置中缺少 API key"""
        service = LLMService()

        invalid_config = {
            "provider": "gemini",
            "api_key": "",  # 空的 API key
            "model_name": "gemini-1.5-flash",
        }

        with pytest.raises(Exception) as exc_info:
            await service._generate_with_config(
                message="Test",
                conversation_history=[],
                file_context=None,
                model_config=invalid_config,
            )

        assert "API key is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_model_name_in_config(self):
        """测试配置中缺少模型名称"""
        service = LLMService()

        invalid_config = {
            "provider": "gemini",
            "api_key": "test-key",
            "model_name": "",  # 空的模型名称
        }

        with pytest.raises(Exception) as exc_info:
            await service._generate_with_config(
                message="Test",
                conversation_history=[],
                file_context=None,
                model_config=invalid_config,
            )

        assert "Model name is required" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
