"""单轮测试执行器"""

from sandbox.assertion.base import AssertionContext
from sandbox.assertion.builder import build_assertion
from sandbox.client.dify_chat import DifyChatClient
from sandbox.core.logging import get_logger
from sandbox.schema.config import TargetConfig
from sandbox.schema.result import AssertionResult, CaseResult, TurnResult
from sandbox.schema.test_case import TestCaseSpec

logger = get_logger(__name__)


class SingleTurnRunner:
    """单轮测试执行器"""

    async def execute(
        self,
        case: TestCaseSpec,
        target: TargetConfig,
        shared_inputs: dict | None = None,
    ) -> CaseResult:
        if case.input is None:
            return CaseResult(case_id=case.id, status="error", error_message="单轮测试缺少 input 配置")

        client = DifyChatClient(target)
        try:
            # 合并 shared_inputs 和 case 级别 inputs
            inputs = {**(shared_inputs or {}), **(case.input.inputs or {})}
            user = case.input.user or "sandbox_test"

            response = await client.send_message(
                query=case.input.query,
                user=user,
                inputs=inputs,
            )

            # 构建 TurnResult（用于断言上下文）
            turn_result = TurnResult(
                turn_index=0,
                user_message=case.input.query,
                bot_response=response.answer,
                latency_ms=response.latency_ms,
                token_usage=response.token_usage,
            )

            # 评估断言
            assertion_results: list[AssertionResult] = []
            for spec in case.assertions or []:
                assertion = build_assertion(spec)
                # 将延迟和 token 信息注入 raw_response 供性能断言使用
                raw_with_meta = {
                    **response.raw_data,
                    "_latency_ms": response.latency_ms,
                }
                ctx = AssertionContext(history=[turn_result], turn_index=0)
                result = await assertion.evaluate(response.answer, raw_with_meta, ctx)
                assertion_results.append(result)

            turn_result.assertions = assertion_results

            return CaseResult(case_id=case.id, status="completed", turns=[turn_result])

        except Exception as e:
            logger.error(f"用例 {case.id} 执行失败: {e}")
            return CaseResult(case_id=case.id, status="error", error_message=str(e))
        finally:
            await client.close()
