"""测试工具模块"""

import asyncio
import os

import pytest


class TestTemplate:
    """测试环境变量插值"""

    def test_interpolate_env_basic(self):
        from sandbox.utils.template import interpolate_env

        os.environ["_TEST_VAR"] = "hello"
        assert interpolate_env("${_TEST_VAR}") == "hello"
        del os.environ["_TEST_VAR"]

    def test_interpolate_env_missing(self):
        from sandbox.utils.template import interpolate_env

        with pytest.raises(ValueError, match="环境变量未设置"):
            interpolate_env("${_NONEXISTENT_VAR_12345}")

    def test_interpolate_env_no_vars(self):
        from sandbox.utils.template import interpolate_env

        assert interpolate_env("plain text") == "plain text"

    def test_interpolate_dict(self):
        from sandbox.utils.template import interpolate_dict

        os.environ["_TEST_KEY"] = "secret"
        result = interpolate_dict({"api_key": "${_TEST_KEY}", "timeout": 30})
        assert result["api_key"] == "secret"
        assert result["timeout"] == 30
        del os.environ["_TEST_KEY"]


class TestYAMLLoader:
    """测试 YAML 加载"""

    def test_load_yaml_file_not_found(self, tmp_path):
        from sandbox.utils.yaml_loader import load_yaml
        from sandbox.core.exceptions import YAMLValidationError

        with pytest.raises(YAMLValidationError, match="文件不存在"):
            load_yaml(tmp_path / "nonexistent.yaml")

    def test_load_yaml_valid(self, tmp_path):
        from sandbox.utils.yaml_loader import load_yaml

        f = tmp_path / "test.yaml"
        f.write_text("key: value\nnested:\n  a: 1")
        result = load_yaml(f)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_load_and_validate(self, tmp_path):
        from sandbox.utils.yaml_loader import load_and_validate
        from sandbox.schema.config import LLMConfig

        f = tmp_path / "llm.yaml"
        f.write_text("api_base: http://localhost\nmodel: test-model\n")
        result = load_and_validate(f, LLMConfig)
        assert result.api_base == "http://localhost"
        assert result.model == "test-model"


class TestRateLimiter:
    """测试令牌桶限流器"""

    def test_acquire_within_burst(self):
        from sandbox.utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rpm=60, burst=5)

        async def _run():
            for _ in range(5):
                await limiter.acquire()

        asyncio.run(_run())
        # 5 次获取应该在 burst 内不阻塞


class TestAssertions:
    """测试断言引擎"""

    def test_contains_pass(self):
        from sandbox.assertion.string_match import ContainsAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = ContainsAssertion("hello")
            r = await a.evaluate("say hello world", {}, AssertionContext())
            assert r.passed is True

        asyncio.run(_run())

    def test_contains_fail(self):
        from sandbox.assertion.string_match import ContainsAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = ContainsAssertion("hello")
            r = await a.evaluate("say goodbye", {}, AssertionContext())
            assert r.passed is False

        asyncio.run(_run())

    def test_not_contains_pass(self):
        from sandbox.assertion.string_match import NotContainsAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = NotContainsAssertion(["AI", "ChatGPT"])
            r = await a.evaluate("我是Linh老师", {}, AssertionContext())
            assert r.passed is True

        asyncio.run(_run())

    def test_not_contains_fail(self):
        from sandbox.assertion.string_match import NotContainsAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = NotContainsAssertion(["AI", "ChatGPT"])
            r = await a.evaluate("作为AI助手", {}, AssertionContext())
            assert r.passed is False

        asyncio.run(_run())

    def test_regex_pass(self):
        from sandbox.assertion.string_match import RegexAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = RegexAssertion(r"1[3-9]\d{9}")
            r = await a.evaluate("手机号: 13812345678", {}, AssertionContext())
            assert r.passed is True

        asyncio.run(_run())

    def test_regex_fail(self):
        from sandbox.assertion.string_match import RegexAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = RegexAssertion(r"1[3-9]\d{9}")
            r = await a.evaluate("没有手机号", {}, AssertionContext())
            assert r.passed is False

        asyncio.run(_run())

    def test_equals_pass(self):
        from sandbox.assertion.string_match import EqualsAssertion
        from sandbox.assertion.base import AssertionContext

        async def _run():
            a = EqualsAssertion("确认成功")
            r = await a.evaluate("确认成功", {}, AssertionContext())
            assert r.passed is True

        asyncio.run(_run())


class TestAssertionBuilder:
    """测试断言工厂"""

    def test_build_contains(self):
        from sandbox.assertion.builder import build_assertion
        from sandbox.assertion.string_match import ContainsAssertion
        from sandbox.schema.test_case import AssertionSpec

        spec = AssertionSpec(type="contains", value="hello")
        a = build_assertion(spec)
        assert isinstance(a, ContainsAssertion)

    def test_build_unknown_type(self):
        from sandbox.assertion.builder import build_assertion
        from sandbox.core.exceptions import AssertionError_
        from sandbox.schema.test_case import AssertionSpec

        spec = AssertionSpec(type="contains")  # missing value
        with pytest.raises(AssertionError_):
            build_assertion(spec)


class TestSchemaValidation:
    """测试 Schema 模型"""

    def test_sandbox_config_defaults(self):
        from sandbox.schema.config import SandboxConfig

        config = SandboxConfig()
        assert config.version == "1.0"
        assert config.execution.concurrency == 5

    def test_test_suite_spec(self):
        from sandbox.schema.test_case import TestSuiteSpec

        data = {
            "suite": {"name": "test", "target": "production"},
            "cases": [
                {
                    "id": "t1",
                    "name": "Test 1",
                    "type": "single_turn",
                    "input": {"query": "hello"},
                    "assertions": [{"type": "contains", "value": "world"}],
                }
            ],
        }
        spec = TestSuiteSpec.model_validate(data)
        assert spec.suite.name == "test"
        assert len(spec.cases) == 1
        assert spec.cases[0].assertions[0].type == "contains"


class TestValidateCommand:
    """测试 CLI validate 命令"""

    def test_validate_example_suite(self):
        from sandbox.utils.yaml_loader import load_and_validate
        from sandbox.schema.test_case import TestSuiteSpec

        spec = load_and_validate("examples/suites/phone_extraction.yaml", TestSuiteSpec)
        assert spec.suite.name == "电话号码提取回归测试"
        assert len(spec.cases) == 3


class TestScoring:
    """测试评分系统"""

    def test_score_case_all_passed(self):
        from sandbox.scoring.scorer import Scorer
        from sandbox.schema.config import ScoringConfig
        from sandbox.schema.result import AssertionResult, CaseResult, TurnResult

        scorer = Scorer(ScoringConfig())
        case_result = CaseResult(
            case_id="t1",
            status="completed",
            turns=[
                TurnResult(
                    turn_index=0,
                    user_message="hi",
                    bot_response="hello",
                    latency_ms=100,
                    assertions=[
                        AssertionResult(passed=True, assertion_type="contains", message="ok"),
                        AssertionResult(passed=True, assertion_type="regex", message="ok"),
                    ],
                )
            ],
        )
        score = scorer.score_case(case_result)
        assert score.passed is True
        assert score.pass_rate == 1.0

    def test_score_case_some_failed(self):
        from sandbox.scoring.scorer import Scorer
        from sandbox.schema.config import ScoringConfig
        from sandbox.schema.result import AssertionResult, CaseResult, TurnResult

        scorer = Scorer(ScoringConfig())
        case_result = CaseResult(
            case_id="t1",
            status="completed",
            turns=[
                TurnResult(
                    turn_index=0,
                    user_message="hi",
                    bot_response="hello",
                    latency_ms=100,
                    assertions=[
                        AssertionResult(passed=True, assertion_type="contains", message="ok"),
                        AssertionResult(passed=False, assertion_type="regex", message="fail"),
                    ],
                )
            ],
        )
        score = scorer.score_case(case_result)
        assert score.passed is False
        assert score.pass_rate == 0.5
