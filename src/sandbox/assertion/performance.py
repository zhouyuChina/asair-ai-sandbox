"""性能断言：latency_ms, token_usage"""

from sandbox.assertion.base import AssertionContext, BaseAssertion
from sandbox.schema.result import AssertionResult


class LatencyAssertion(BaseAssertion):
    """检查响应延迟是否在阈值内"""

    def __init__(self, max_ms: int):
        self.max_ms = max_ms

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        # 从最近一轮结果中获取延迟
        if context.history:
            latest = context.history[-1]
            latency = latest.latency_ms
        else:
            latency = raw_response.get("_latency_ms", 0)

        passed = latency <= self.max_ms
        return AssertionResult(
            passed=passed,
            assertion_type="latency_ms",
            message=f"延迟 {latency:.0f}ms {'<=' if passed else '>'} {self.max_ms}ms",
            expected=f"<= {self.max_ms}ms",
            actual=f"{latency:.0f}ms",
        )


class TokenUsageAssertion(BaseAssertion):
    """检查 Token 用量是否在阈值内"""

    def __init__(self, max_total: int):
        self.max_total = max_total

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        # 从最近一轮结果中获取 token 用量
        total_tokens = 0
        if context.history:
            latest = context.history[-1]
            if latest.token_usage:
                total_tokens = latest.token_usage.get("total_tokens", 0)

        passed = total_tokens <= self.max_total
        return AssertionResult(
            passed=passed,
            assertion_type="token_usage",
            message=f"Token {total_tokens} {'<=' if passed else '>'} {self.max_total}",
            expected=f"<= {self.max_total}",
            actual=str(total_tokens),
        )
