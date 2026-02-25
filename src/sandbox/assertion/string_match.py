"""字符串匹配断言：contains, not_contains, regex, equals"""

import re

from sandbox.assertion.base import AssertionContext, BaseAssertion
from sandbox.schema.result import AssertionResult


class ContainsAssertion(BaseAssertion):
    """检查响应中是否包含指定字符串"""

    def __init__(self, value: str):
        self.value = value

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        found = self.value in response_text
        return AssertionResult(
            passed=found,
            assertion_type="contains",
            message=f"{'包含' if found else '未包含'} \"{self.value}\"",
            expected=self.value,
            actual="found" if found else "not found",
        )


class NotContainsAssertion(BaseAssertion):
    """检查响应中不包含任何指定字符串"""

    def __init__(self, values: list[str]):
        self.values = values

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        found = [v for v in self.values if v in response_text]
        passed = len(found) == 0
        return AssertionResult(
            passed=passed,
            assertion_type="not_contains",
            message=f"{'通过: 未发现禁止词' if passed else f'失败: 发现禁止词 {found}'}",
            expected=f"不包含 {self.values}",
            actual=f"发现 {found}" if found else "未发现",
        )


class RegexAssertion(BaseAssertion):
    """正则表达式匹配"""

    def __init__(self, pattern: str):
        self.pattern = pattern

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        match = re.search(self.pattern, response_text)
        passed = match is not None
        return AssertionResult(
            passed=passed,
            assertion_type="regex",
            message=f"{'匹配' if passed else '未匹配'} /{self.pattern}/",
            expected=self.pattern,
            actual=match.group() if match else "no match",
        )


class EqualsAssertion(BaseAssertion):
    """完全等于"""

    def __init__(self, value: str):
        self.value = value

    async def evaluate(self, response_text: str, raw_response: dict, context: AssertionContext) -> AssertionResult:
        passed = response_text.strip() == str(self.value).strip()
        return AssertionResult(
            passed=passed,
            assertion_type="equals",
            message=f"{'完全匹配' if passed else '不匹配'}",
            expected=self.value,
            actual=response_text[:200],
        )
