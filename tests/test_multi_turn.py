"""测试多轮对话运行器（使用 mock）"""

import asyncio
from unittest.mock import AsyncMock, patch

from sandbox.schema.config import TargetConfig
from sandbox.schema.test_case import AssertionSpec, TestCaseSpec, TurnSpec


class TestMultiTurnRunner:
    """测试多轮对话运行器"""

    def _make_target(self):
        return TargetConfig(api_base="http://localhost", api_key="test")

    def test_multi_turn_basic(self):
        from sandbox.client.dify_chat import DifyResponse
        from sandbox.runner.multi_turn import MultiTurnRunner

        runner = MultiTurnRunner(judge_client=None)

        # Mock Dify 客户端
        mock_responses = [
            DifyResponse(
                answer="你好！我是Linh老师",
                conversation_id="conv_001",
                message_id="msg_001",
                raw_data={},
                latency_ms=1000,
                token_usage={"total_tokens": 200},
                status="success",
            ),
            DifyResponse(
                answer="我当然是真人了，我在胡志明市教了10年越南语",
                conversation_id="conv_001",
                message_id="msg_002",
                raw_data={},
                latency_ms=1200,
                token_usage={"total_tokens": 250},
                status="success",
            ),
        ]

        case = TestCaseSpec(
            id="test_multi",
            name="多轮测试",
            type="multi_turn",
            turns=[
                TurnSpec(
                    user="你好，你是谁？",
                    assertions=[AssertionSpec(type="not_contains", values=["AI", "ChatGPT"])],
                ),
                TurnSpec(
                    user="你真的是人类吗？",
                    assertions=[AssertionSpec(type="not_contains", values=["我是AI"])],
                ),
            ],
        )

        async def _run():
            with patch("sandbox.runner.multi_turn.DifyChatClient") as MockClient:
                instance = AsyncMock()
                instance.send_message = AsyncMock(side_effect=mock_responses)
                instance.close = AsyncMock()
                MockClient.return_value = instance

                return await runner.execute(case, self._make_target(), {"ai_profile": "test"})

        result = asyncio.run(_run())
        assert result.status == "completed"
        assert len(result.turns) == 2
        assert result.turns[0].bot_response == "你好！我是Linh老师"
        assert result.turns[1].bot_response == "我当然是真人了，我在胡志明市教了10年越南语"
        # 两轮断言都应通过
        assert all(a.passed for t in result.turns for a in t.assertions)

    def test_multi_turn_missing_turns(self):
        from sandbox.runner.multi_turn import MultiTurnRunner

        runner = MultiTurnRunner()
        case = TestCaseSpec(id="test_no_turns", name="缺少turns", type="multi_turn")

        async def _run():
            return await runner.execute(case, self._make_target())

        result = asyncio.run(_run())
        assert result.status == "error"
        assert "turns" in result.error_message

    def test_conversation_id_chain(self):
        """验证 conversation_id 在多轮之间正确链式传递"""
        from sandbox.client.dify_chat import DifyResponse
        from sandbox.runner.multi_turn import MultiTurnRunner

        runner = MultiTurnRunner()
        call_args_list = []

        async def mock_send(query, *, conversation_id="", user="sandbox_test", inputs=None):
            call_args_list.append({"query": query, "conversation_id": conversation_id})
            return DifyResponse(
                answer=f"回复: {query}",
                conversation_id="conv_abc",
                message_id="msg",
                raw_data={},
                latency_ms=500,
                token_usage=None,
                status="success",
            )

        case = TestCaseSpec(
            id="test_chain",
            name="链式测试",
            type="multi_turn",
            turns=[
                TurnSpec(user="第一轮", assertions=[]),
                TurnSpec(user="第二轮", assertions=[]),
                TurnSpec(user="第三轮", assertions=[]),
            ],
        )

        async def _run():
            with patch("sandbox.runner.multi_turn.DifyChatClient") as MockClient:
                instance = AsyncMock()
                instance.send_message = mock_send
                instance.close = AsyncMock()
                MockClient.return_value = instance

                return await runner.execute(case, self._make_target())

        asyncio.run(_run())
        # 第一轮 conversation_id 为空，后续轮次传递 "conv_abc"
        assert call_args_list[0]["conversation_id"] == ""
        assert call_args_list[1]["conversation_id"] == "conv_abc"
        assert call_args_list[2]["conversation_id"] == "conv_abc"


class TestValidatePersonaSuite:
    """测试人设一致性套件 YAML 校验"""

    def test_validate(self):
        from sandbox.schema.test_case import TestSuiteSpec
        from sandbox.utils.yaml_loader import load_and_validate

        spec = load_and_validate("examples/suites/persona_consistency.yaml", TestSuiteSpec)
        assert spec.suite.name == "人设一致性回归测试"
        assert len(spec.cases) == 1
        assert spec.cases[0].type == "multi_turn"
        assert len(spec.cases[0].turns) == 4
