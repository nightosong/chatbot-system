"""
LLM Service - Handles AI model interactions
Supports multiple providers: Gemini, OpenAI, DeepSeek, Kimi, QWen, etc.

主要功能：
1. 支持用户通过前端界面配置模型（推荐方式）
2. 支持通过环境变量配置默认模型（向后兼容）
"""

import os
import requests
from typing import Any
from google import genai  # type: ignore
from openai import OpenAI


class LLMService:
    """Service for interacting with LLM providers"""

    # 支持的平台及其配置
    PLATFORM_CONFIG = {
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-chat",
        },
        "kimi": {
            "base_url": "https://api.moonshot.cn/v1",
            "default_model": "moonshot-v1-8k",
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "default_model": "qwen-turbo",
        },
        "skywork_router": {
            "base_url": "https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions",
            "default_model": "gpt-4.1",
        },
        "openai": {"base_url": None, "default_model": "gpt-3.5-turbo"},
        "gemini": {"base_url": None, "default_model": "gemini-1.5-flash"},
    }

    def __init__(self):
        """
        初始化 LLM Service

        支持两种模式：
        1. 用户配置模式（推荐）：完全通过前端传入的配置使用模型
        2. 环境变量模式（向后兼容）：从 .env 读取默认配置
        """
        # 尝试从环境变量读取配置（可选，用于向后兼容）
        self.env_provider = os.getenv("LLM_PROVIDER")
        self.env_api_key = os.getenv("LLM_API_KEY")
        self.env_model_name = os.getenv("MODEL_NAME")

        # 如果环境变量中有完整配置，记录日志
        if self.env_api_key and self.env_provider:
            print(f"✓ Loaded default model from environment: {self.env_provider}")
            if self.env_model_name:
                print(f"  Model: {self.env_model_name}")
        else:
            print(
                "ℹ️  No default model in environment. Will use user-configured models."
            )

    async def generate_response(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        file_context: str | None = None,
        model_config: dict[str, Any] | None = None,
        language: str | None = None,
    ) -> str:
        """
        生成 AI 响应

        Args:
            message: 用户当前消息
            conversation_history: 历史对话记录 [{"role": "user/assistant", "content": "..."}]
            file_context: 上传文件的内容
            model_config: 用户配置的模型信息（优先使用）
            language: 用户语言偏好（如 'zh-CN', 'en-US', 'auto' 等）

        Returns:
            AI 生成的响应文本

        Raises:
            ValueError: 当没有提供任何模型配置时
        """
        if conversation_history is None:
            conversation_history = []

        # 优先使用用户配置的模型
        if model_config:
            return await self._generate_with_config(
                message, conversation_history, file_context, model_config, language
            )

        # 回退到环境变量配置
        if self.env_api_key and self.env_provider:
            env_config = {
                "provider": self.env_provider,
                "api_key": self.env_api_key,
                "model_name": self.env_model_name
                or self._get_default_model_name(self.env_provider),
                "base_url": self._get_base_url(self.env_provider),
            }
            return await self._generate_with_config(
                message, conversation_history, file_context, env_config, language
            )

        # 没有任何配置
        raise ValueError(
            "No model configuration available. "
            "Please configure a model in the web interface (Settings → Model Configuration) "
            "or set LLM_PROVIDER and LLM_API_KEY in the .env file."
        )

    def _get_base_url(self, provider: str) -> str | None:
        """获取指定平台的 base URL"""
        config = self.PLATFORM_CONFIG.get(provider.lower(), {})
        return config.get("base_url")

    def _get_default_model_name(self, provider: str) -> str:
        """获取指定平台的默认模型名称"""
        config = self.PLATFORM_CONFIG.get(provider.lower(), {})
        return config.get("default_model", "gpt-3.5-turbo")

    def _get_language_system_prompt(self, language: str | None) -> str:
        """根据语言代码获取对应的 system prompt"""
        if not language or language == "auto":
            return ""

        language_prompts = {
            "zh-CN": "请使用简体中文回答所有问题。无论用户使用什么语言提问，你都必须用简体中文回复。",
            "en-US": "Please answer all questions in English. No matter what language the user uses, you must reply in English.",
            "ja-JP": "すべての質問に日本語で答えてください。ユーザーがどの言語を使用しても、日本語で返信する必要があります。",
            "ko-KR": "모든 질문에 한국어로 답변해 주세요. 사용자가 어떤 언어를 사용하든 한국어로 답변해야 합니다。",
            "fr-FR": "Veuillez répondre à toutes les questions en français. Quelle que soit la langue utilisée par l'utilisateur, vous devez répondre en français.",
            "de-DE": "Bitte beantworten Sie alle Fragen auf Deutsch. Unabhängig davon, welche Sprache der Benutzer verwendet, müssen Sie auf Deutsch antworten.",
            "es-ES": "Por favor, responde a todas las preguntas en español. No importa qué idioma use el usuario, debes responder en español.",
        }

        return language_prompts.get(language, "")

    def _build_context_for_gemini(
        self,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        language: str | None = None,
    ) -> str:
        """构建 Gemini 的上下文字符串"""
        context_parts = []

        # 添加语言 system prompt
        language_prompt = self._get_language_system_prompt(language)
        if language_prompt:
            context_parts.append(f"[Language Instruction]\n{language_prompt}\n")

        # 添加文件上下文
        if file_context:
            context_parts.append(
                f"[File Content]\n{file_context}\n[End of File Content]\n"
            )

        # 添加对话历史（最近10轮对话，即20条消息）
        if conversation_history:
            context_parts.append("[Conversation History]")
            for msg in conversation_history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                role_label = "User" if role == "user" else "Assistant"
                context_parts.append(f"{role_label}: {content}")
            context_parts.append("[End of History]\n")

        # 添加当前消息
        context_parts.append(f"User: {message}")

        return "\n".join(context_parts)

    def _build_messages_for_openai(
        self,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """构建 OpenAI 兼容的 messages 数组"""
        messages = []

        # 系统提示
        system_content = "You are a helpful AI assistant."

        # 添加语言约束
        language_prompt = self._get_language_system_prompt(language)
        if language_prompt:
            system_content += f"\n\n{language_prompt}"

        # 添加文件上下文
        if file_context:
            system_content += (
                f"\n\n[File Content]\n{file_context}\n[End of File Content]"
            )
        messages.append({"role": "system", "content": system_content})

        # 历史对话（最近10轮，即20条消息）
        if conversation_history:
            for msg in conversation_history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # 当前消息
        messages.append({"role": "user", "content": message})

        return messages

    async def _generate_with_config(
        self,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        model_config: dict[str, Any],
        language: str | None = None,
    ) -> str:
        """
        使用指定的模型配置生成响应

        Args:
            message: 用户消息
            conversation_history: 对话历史
            file_context: 文件上下文
            model_config: 模型配置 {provider, api_key, model_name, base_url}
            language: 语言设置

        Returns:
            AI 生成的响应
        """
        try:
            provider = model_config.get("provider", "").lower()
            api_key = model_config.get("api_key")
            model_name = model_config.get("model_name")
            base_url = model_config.get("base_url")

            # 验证必需字段
            if not api_key:
                raise ValueError(f"API key is required for {provider}")
            if not model_name:
                raise ValueError(f"Model name is required for {provider}")

            # 根据 provider 选择生成方式
            if provider == "gemini":
                return await self._generate_gemini_response(
                    api_key,
                    model_name,
                    message,
                    conversation_history,
                    file_context,
                    language,
                )
            elif provider == "skywork_router":
                return await self._generate_skywork_router_response(
                    api_key,
                    model_name,
                    message,
                    conversation_history,
                    file_context,
                    language,
                )

            else:
                return await self._generate_openai_response(
                    api_key,
                    model_name,
                    base_url,
                    message,
                    conversation_history,
                    file_context,
                    language,
                )

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Model API error {error_msg}")
            raise Exception(f"Failed to generate response: {error_msg}")

    async def _generate_skywork_router_response(
        self,
        api_key: str,
        model_name: str,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        language: str | None = None,
    ) -> str:
        """使用 Skywork Router 生成响应（参考 Go 实现）"""
        # API URL
        url = "https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions"

        # 构建请求头（使用 app_key 而不是 Authorization）
        headers = {
            "Content-Type": "application/json",
            "app_key": api_key,  # 关键：使用 app_key header
        }

        # 构建 messages（OpenAI 兼容格式）
        messages = self._build_messages_for_openai(
            message, conversation_history, file_context, language
        )

        # 构建请求体
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 1.0,
            "stream": False,
        }

        try:
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=60)

            # 检查状态码
            if response.status_code != 200:
                error_msg = f"Skywork Router API error: status={response.status_code}, body={response.text}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            # 解析响应
            resp_json = response.json()

            # 提取响应内容
            if "choices" not in resp_json or len(resp_json["choices"]) == 0:
                raise Exception("Empty choices in Skywork Router response")

            content = resp_json["choices"][0]["message"]["content"]

            return content or ""

        except requests.exceptions.Timeout:
            raise Exception("Skywork Router API timeout after 60 seconds")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Skywork Router API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Skywork Router response: {str(e)}")

    async def _generate_gemini_response(
        self,
        api_key: str,
        model_name: str,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        language: str | None = None,
    ) -> str:
        """使用 Gemini 生成响应"""
        os.environ["GOOGLE_API_KEY"] = api_key
        client = genai.Client()

        full_prompt = self._build_context_for_gemini(
            message, conversation_history, file_context, language
        )

        response = client.models.generate_content(
            model=model_name, contents=full_prompt
        )
        return response.text

    async def _generate_openai_response(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None,
        message: str,
        conversation_history: list[dict],
        file_context: str | None,
        language: str | None = None,
    ) -> str:
        """使用 OpenAI 兼容 API 生成响应"""
        # 初始化客户端
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # 构建消息
        messages = self._build_messages_for_openai(
            message, conversation_history, file_context, language
        )

        # 调用 API
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""
