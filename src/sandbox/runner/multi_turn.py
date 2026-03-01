"""脚本化多轮对话测试执行器"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sandbox.assertion.base import AssertionContext
from sandbox.assertion.builder import build_assertion
from sandbox.client.dify_chat import DifyChatClient
from sandbox.core.logging import get_logger
from sandbox.schema.config import TargetConfig
from sandbox.schema.result import AssertionResult, CaseResult, TurnResult
from sandbox.schema.test_case import TestCaseSpec

if TYPE_CHECKING:
    from sandbox.client.judge_llm import JudgeLLMClient
    from sandbox.schema.scene import SceneSpec

logger = get_logger(__name__)


class MultiTurnRunner:
    """脚本化多轮对话测试执行器"""

    def __init__(self, judge_client: JudgeLLMClient | None = None):
        self.judge_client = judge_client

    async def execute(
        self,
        case: TestCaseSpec,
        target: TargetConfig,
        shared_inputs: dict | None = None,
        scene: SceneSpec | None = None,
    ) -> CaseResult:
        if not case.turns:
            return CaseResult(case_id=case.id, status="error", error_message="多轮测试缺少 turns 配置")

        client = DifyChatClient(target)
        conversation_id = ""
        turn_results: list[TurnResult] = []

        try:
            for i, turn in enumerate(case.turns):
                # inputs 仅首轮传入
                inputs = shared_inputs if i == 0 else {}

                response = await client.send_message(
                    query=turn.user,
                    conversation_id=conversation_id,
                    inputs=inputs or {},
                )
                conversation_id = response.conversation_id

                # 构建当前轮结果
                turn_result = TurnResult(
                    turn_index=i,
                    user_message=turn.user,
                    bot_response=response.answer,
                    latency_ms=response.latency_ms,
                    token_usage=response.token_usage,
                )

                # 逐轮评估断言
                assertion_results: list[AssertionResult] = []
                ctx = AssertionContext(history=turn_results + [turn_result], turn_index=i)
                raw_with_meta = {**response.raw_data, "_latency_ms": response.latency_ms}

                for spec in turn.assertions:
                    assertion = build_assertion(spec, judge_client=self.judge_client, scene=scene)
                    result = await assertion.evaluate(response.answer, raw_with_meta, ctx)
                    assertion_results.append(result)

                turn_result.assertions = assertion_results
                turn_results.append(turn_result)

            return CaseResult(case_id=case.id, status="completed", turns=turn_results)

        except Exception as e:
            logger.error(f"用例 {case.id} 执行失败: {e}")
            return CaseResult(
                case_id=case.id,
                status="error",
                turns=turn_results,
                error_message=str(e),
            )
        finally:
            await client.close()
