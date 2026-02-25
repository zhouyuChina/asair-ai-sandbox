"""LLM-as-Judge 断言 — 用独立 LLM 对回复质量进行客观评估"""

from sandbox.assertion.base import AssertionContext, BaseAssertion
from sandbox.client.judge_llm import JudgeLLMClient
from sandbox.core.logging import get_logger
from sandbox.schema.result import AssertionResult

logger = get_logger(__name__)

JUDGE_SYSTEM_PROMPT = """你是一个严格的AI对话质量评估专家。
你需要根据给定的评估标准，对AI助手的回复进行客观评分。

评分规则：
- 给出 0.0 到 1.0 之间的分数
- 0.0 = 完全不满足标准
- 0.5 = 部分满足
- 1.0 = 完全满足
- 必须输出 JSON 格式: {"score": 0.85, "reasoning": "..."}

重要：你的评分必须基于事实和具体证据，不能主观臆断。"""

JUDGE_USER_TEMPLATE = """## 评估标准
{criteria}

## 对话上下文
{conversation_context}

## 待评估的AI回复
{response_text}

请严格按照评估标准进行评分，输出 JSON 格式。"""


class LLMJudgeAssertion(BaseAssertion):
    """使用 LLM 评估回复质量"""

    def __init__(
        self,
        criteria: str,
        pass_threshold: float,
        judge_client: JudgeLLMClient,
        dimensions: list[str] | None = None,
    ):
        self.criteria = criteria
        self.pass_threshold = pass_threshold
        self.judge_client = judge_client
        self.dimensions = dimensions

    async def evaluate(
        self,
        response_text: str,
        raw_response: dict,
        context: AssertionContext,
    ) -> AssertionResult:
        prompt = JUDGE_USER_TEMPLATE.format(
            criteria=self.criteria,
            conversation_context=context.format_history() or "(无上下文，首轮对话)",
            response_text=response_text,
        )

        try:
            judge_result = await self.judge_client.evaluate(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
        except Exception as e:
            logger.error(f"LLM Judge 调用失败: {e}")
            return AssertionResult(
                passed=False,
                assertion_type="llm_judge",
                message=f"LLM Judge 调用失败: {e}",
                expected=f"score >= {self.pass_threshold}",
                actual="error",
            )

        passed = judge_result.score >= self.pass_threshold
        # 关联到第一个评分维度（如果指定了的话）
        dimension = self.dimensions[0] if self.dimensions else None

        return AssertionResult(
            passed=passed,
            assertion_type="llm_judge",
            message=judge_result.reasoning,
            expected=f"score >= {self.pass_threshold}",
            actual=judge_result.score,
            score=judge_result.score,
            dimension=dimension,
        )
