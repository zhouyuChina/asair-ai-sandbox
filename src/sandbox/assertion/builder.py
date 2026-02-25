"""断言工厂 — 根据 AssertionSpec 构建对应断言实例"""

from sandbox.assertion.base import BaseAssertion
from sandbox.assertion.performance import LatencyAssertion, TokenUsageAssertion
from sandbox.assertion.string_match import (
    ContainsAssertion,
    EqualsAssertion,
    NotContainsAssertion,
    RegexAssertion,
)
from sandbox.core.exceptions import AssertionError_
from sandbox.schema.test_case import AssertionSpec


def build_assertion(spec: AssertionSpec, **kwargs) -> BaseAssertion:
    """根据断言规格构建对应的断言实例"""
    match spec.type:
        case "contains":
            if spec.value is None:
                raise AssertionError_("contains 断言必须指定 value")
            return ContainsAssertion(value=str(spec.value))

        case "not_contains":
            values = spec.values or ([str(spec.value)] if spec.value is not None else [])
            if not values:
                raise AssertionError_("not_contains 断言必须指定 values 或 value")
            return NotContainsAssertion(values=values)

        case "regex":
            if spec.pattern is None:
                raise AssertionError_("regex 断言必须指定 pattern")
            return RegexAssertion(pattern=spec.pattern)

        case "equals":
            if spec.value is None:
                raise AssertionError_("equals 断言必须指定 value")
            return EqualsAssertion(value=str(spec.value))

        case "latency_ms":
            if spec.max is None:
                raise AssertionError_("latency_ms 断言必须指定 max")
            return LatencyAssertion(max_ms=spec.max)

        case "token_usage":
            if spec.max_total is None:
                raise AssertionError_("token_usage 断言必须指定 max_total")
            return TokenUsageAssertion(max_total=spec.max_total)

        case "llm_judge" | "scene_judge" | "json_path" | "json_field":
            raise AssertionError_(f"断言类型 '{spec.type}' 将在后续阶段实现")

        case _:
            raise AssertionError_(f"未知断言类型: {spec.type}")
