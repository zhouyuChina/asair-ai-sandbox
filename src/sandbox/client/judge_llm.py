"""Judge LLM 客户端 — 调用 OpenAI 兼容接口评估回复质量"""

import json
import re
from dataclasses import dataclass

from sandbox.client.base import BaseHTTPClient
from sandbox.core.exceptions import SandboxError
from sandbox.core.logging import get_logger
from sandbox.schema.config import LLMConfig

logger = get_logger(__name__)


@dataclass
class JudgeResult:
    """Judge LLM 评估结果"""

    score: float  # 0.0 ~ 1.0
    reasoning: str
    raw_text: str


class JudgeLLMClient(BaseHTTPClient):
    """
    LLM-as-Judge 客户端

    调用 OpenAI 兼容的 /chat/completions 接口，
    解析 JSON 格式的评分结果。
    """

    def __init__(self, config: LLMConfig):
        super().__init__(
            base_url=config.api_base,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=2,
        )
        self.model = config.model
        self.temperature = config.temperature

    async def evaluate(self, system_prompt: str, user_prompt: str) -> JudgeResult:
        """
        调用 LLM 进行评估

        参数：
            system_prompt: 系统提示词（评估规则）
            user_prompt: 用户提示词（待评估内容）
        返回：
            JudgeResult 包含 score, reasoning, raw_text
        """
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = await self._request_with_retry("POST", "/chat/completions", json=payload)
        raw_text = response["choices"][0]["message"]["content"]

        return self._parse_judge_response(raw_text)

    def _parse_judge_response(self, raw_text: str) -> JudgeResult:
        """解析 Judge LLM 的 JSON 响应，带容错处理"""
        # 尝试直接解析 JSON
        try:
            data = json.loads(raw_text)
            return JudgeResult(
                score=float(data["score"]),
                reasoning=data.get("reasoning", ""),
                raw_text=raw_text,
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Fallback: 从 markdown code block 中提取 JSON
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return JudgeResult(
                    score=float(data["score"]),
                    reasoning=data.get("reasoning", ""),
                    raw_text=raw_text,
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Fallback: 用正则提取 score
        score_match = re.search(r'"score"\s*:\s*([\d.]+)', raw_text)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', raw_text)
        if score_match:
            return JudgeResult(
                score=float(score_match.group(1)),
                reasoning=reasoning_match.group(1) if reasoning_match else raw_text[:200],
                raw_text=raw_text,
            )

        # 所有解析方式都失败
        raise SandboxError(f"无法解析 Judge LLM 响应: {raw_text[:500]}")
