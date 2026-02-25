"""Dify Chatflow API 客户端"""

import time
from dataclasses import dataclass

from sandbox.client.base import BaseHTTPClient
from sandbox.schema.config import TargetConfig


@dataclass
class DifyResponse:
    """Dify API 响应的结构化封装"""

    answer: str
    conversation_id: str
    message_id: str
    raw_data: dict
    latency_ms: float
    token_usage: dict | None
    status: str  # "success" | "error"
    error_message: str | None = None


class DifyChatClient(BaseHTTPClient):
    """
    Dify Chatflow API 客户端

    支持：
    - 多轮对话（conversation_id 自动追踪）
    - blocking 模式
    - 延迟和 Token 用量测量
    - 指数退避重试
    """

    def __init__(self, config: TargetConfig):
        super().__init__(
            base_url=config.api_base,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self.config = config

    async def send_message(
        self,
        query: str,
        *,
        conversation_id: str = "",
        user: str = "sandbox_test",
        inputs: dict | None = None,
    ) -> DifyResponse:
        """
        发送消息到 Dify Chatflow API

        参数：
            query: 用户消息内容
            conversation_id: 对话ID，首轮传空字符串
            user: 用户标识
            inputs: Dify 应用输入变量
        """
        payload: dict = {
            "inputs": inputs or {},
            "query": query,
            "response_mode": self.config.response_mode,
            "user": user,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        start_time = time.monotonic()
        response = await self._request_with_retry("POST", "/chat-messages", json=payload)
        latency_ms = (time.monotonic() - start_time) * 1000

        return DifyResponse(
            answer=response["answer"],
            conversation_id=response["conversation_id"],
            message_id=response["message_id"],
            raw_data=response,
            latency_ms=latency_ms,
            token_usage=response.get("metadata", {}).get("usage"),
            status="success",
        )
