from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional

import json
import requests


class SkyworkRouter:
    """Skywork Router client for chat completions (stream + non-stream)."""

    DEFAULT_ROUTER_URL = "gpt-proxy/chat/completions"

    # Hard-coded model -> router_url mapping
    MODEL_ROUTER: Dict[str, str] = {
        "gpt-4.1": DEFAULT_ROUTER_URL,
        "gpt-4.1-mini": DEFAULT_ROUTER_URL,
        "gpt-4o": DEFAULT_ROUTER_URL,
        "gpt-5": "gpt-proxy/azure/chat/completions",
    }

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or "https://gpt-us.singularity-ai.com").rstrip("/")

    def _resolve_router_url(self, model_name: str) -> str:
        router = self.MODEL_ROUTER.get(model_name, self.DEFAULT_ROUTER_URL)
        return f"{self.base_url}/{router.lstrip('/')}"

    def _build_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "app_key": api_key,
        }

    def chat_completion(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        url = self._resolve_router_url(model_name)
        headers = self._build_headers(api_key)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": 1.0,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code != 200:
            raise Exception(
                f"Skywork Router API error: status={response.status_code}, body={response.text}"
            )
        return response.json()

    def chat_completion_stream(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Iterator[Dict[str, Any]]:
        """
        Currently uses non-stream response and yields chunks to simulate streaming.
        """
        response_json = self.chat_completion(
            api_key=api_key,
            model_name=model_name,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )
        yield response_json
