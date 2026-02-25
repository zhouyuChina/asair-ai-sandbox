"""测试结果模型"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssertionResult:
    """单条断言的评估结果"""

    passed: bool
    assertion_type: str
    message: str
    expected: Any | None = None
    actual: Any | None = None
    score: float | None = None
    dimension: str | None = None
    details: Any | None = None


@dataclass
class TurnResult:
    """单轮对话结果"""

    turn_index: int
    user_message: str
    bot_response: str
    latency_ms: float
    token_usage: dict | None = None
    assertions: list[AssertionResult] = field(default_factory=list)


@dataclass
class CaseResult:
    """测试用例结果"""

    case_id: str
    status: str  # "completed" | "error"
    turns: list[TurnResult] = field(default_factory=list)
    final_assertions: list[AssertionResult] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class CaseScore:
    """用例级评分"""

    case_id: str
    passed: bool
    pass_rate: float
    overall_score: float
    dimension_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class SuiteResult:
    """测试套件执行结果"""

    suite_name: str
    target: str
    case_results: list[CaseResult] = field(default_factory=list)


@dataclass
class SuiteScore:
    """套件级评分"""

    suite_name: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    avg_overall_score: float
    dimension_averages: dict[str, float] = field(default_factory=dict)
    case_scores: list[CaseScore] = field(default_factory=list)
