"""测试 Judge LLM 客户端和 LLM Judge 断言"""

import asyncio
import json

import pytest

from sandbox.client.judge_llm import JudgeLLMClient, JudgeResult


class TestJudgeResultParsing:
    """测试 Judge 响应解析"""

    def _make_client(self):
        """创建一个 client 实例（不会真正调用 API）"""
        from sandbox.schema.config import LLMConfig

        config = LLMConfig(api_base="http://localhost", api_key="test")
        return JudgeLLMClient(config)

    def test_parse_valid_json(self):
        client = self._make_client()
        result = client._parse_judge_response('{"score": 0.85, "reasoning": "表现不错"}')
        assert result.score == 0.85
        assert result.reasoning == "表现不错"

    def test_parse_json_in_code_block(self):
        client = self._make_client()
        raw = '```json\n{"score": 0.7, "reasoning": "还可以"}\n```'
        result = client._parse_judge_response(raw)
        assert result.score == 0.7

    def test_parse_regex_fallback(self):
        client = self._make_client()
        raw = '评分结果：{"score": 0.6, "reasoning": "一般"} 以上是我的评估。'
        result = client._parse_judge_response(raw)
        assert result.score == 0.6

    def test_parse_failure(self):
        client = self._make_client()
        from sandbox.core.exceptions import SandboxError

        with pytest.raises(SandboxError, match="无法解析"):
            client._parse_judge_response("这里完全没有 JSON")


class TestLLMJudgeAssertion:
    """测试 LLM Judge 断言（使用 mock）"""

    def test_judge_pass(self):
        from unittest.mock import AsyncMock

        from sandbox.assertion.base import AssertionContext
        from sandbox.assertion.llm_judge import LLMJudgeAssertion

        mock_client = AsyncMock()
        mock_client.evaluate.return_value = JudgeResult(score=0.9, reasoning="很好", raw_text="")

        assertion = LLMJudgeAssertion(
            criteria="是否保持人设",
            pass_threshold=0.8,
            judge_client=mock_client,
            dimensions=["persona_consistency"],
        )

        async def _run():
            return await assertion.evaluate("我是Linh老师", {}, AssertionContext())

        result = asyncio.run(_run())
        assert result.passed is True
        assert result.score == 0.9
        assert result.dimension == "persona_consistency"

    def test_judge_fail(self):
        from unittest.mock import AsyncMock

        from sandbox.assertion.base import AssertionContext
        from sandbox.assertion.llm_judge import LLMJudgeAssertion

        mock_client = AsyncMock()
        mock_client.evaluate.return_value = JudgeResult(score=0.3, reasoning="暴露了AI身份", raw_text="")

        assertion = LLMJudgeAssertion(
            criteria="是否保持人设",
            pass_threshold=0.8,
            judge_client=mock_client,
        )

        async def _run():
            return await assertion.evaluate("作为AI，我无法...", {}, AssertionContext())

        result = asyncio.run(_run())
        assert result.passed is False
        assert result.score == 0.3

    def test_judge_error_graceful(self):
        from unittest.mock import AsyncMock

        from sandbox.assertion.base import AssertionContext
        from sandbox.assertion.llm_judge import LLMJudgeAssertion

        mock_client = AsyncMock()
        mock_client.evaluate.side_effect = Exception("API 超时")

        assertion = LLMJudgeAssertion(
            criteria="测试",
            pass_threshold=0.5,
            judge_client=mock_client,
        )

        async def _run():
            return await assertion.evaluate("response", {}, AssertionContext())

        result = asyncio.run(_run())
        assert result.passed is False
        assert "调用失败" in result.message


class TestAssertionBuilderLLMJudge:
    """测试断言工厂的 llm_judge 支持"""

    def test_build_llm_judge(self):
        from unittest.mock import MagicMock

        from sandbox.assertion.builder import build_assertion
        from sandbox.assertion.llm_judge import LLMJudgeAssertion
        from sandbox.schema.test_case import AssertionSpec

        spec = AssertionSpec(type="llm_judge", criteria="测试标准", pass_threshold=0.7)
        mock_client = MagicMock()
        assertion = build_assertion(spec, judge_client=mock_client)
        assert isinstance(assertion, LLMJudgeAssertion)

    def test_build_llm_judge_missing_client(self):
        from sandbox.assertion.builder import build_assertion
        from sandbox.core.exceptions import AssertionError_
        from sandbox.schema.test_case import AssertionSpec

        spec = AssertionSpec(type="llm_judge", criteria="测试", pass_threshold=0.7)
        with pytest.raises(AssertionError_, match="judge LLM"):
            build_assertion(spec, judge_client=None)

    def test_build_llm_judge_missing_criteria(self):
        from unittest.mock import MagicMock

        from sandbox.assertion.builder import build_assertion
        from sandbox.core.exceptions import AssertionError_
        from sandbox.schema.test_case import AssertionSpec

        spec = AssertionSpec(type="llm_judge", pass_threshold=0.7)
        with pytest.raises(AssertionError_, match="criteria"):
            build_assertion(spec, judge_client=MagicMock())
