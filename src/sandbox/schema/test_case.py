"""测试用例 YAML Pydantic 模型

对应测试套件 YAML 文件（suites/*.yaml）。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssertionSpec(BaseModel):
    """断言规格"""

    type: Literal[
        "contains",
        "not_contains",
        "regex",
        "equals",
        "llm_judge",
        "scene_judge",
        "json_path",
        "json_field",
        "latency_ms",
        "token_usage",
    ]
    # 字符串匹配
    value: str | bool | int | float | None = None
    values: list[str] | None = None
    pattern: str | None = None
    # LLM Judge
    criteria: str | None = None
    pass_threshold: float | None = None
    dimensions: list[str] | None = None
    # Scene Judge
    phase: str | None = None
    behaviors: list[str] | None = None
    # JSON
    path: str | None = None
    field: str | None = None
    operator: str | None = None
    value_in: list[Any] | None = None
    assertions: list["AssertionSpec"] | None = None
    # 性能
    max: int | None = None
    max_total: int | None = None


class SingleTurnInput(BaseModel):
    """单轮测试输入"""

    query: str
    inputs: dict[str, Any] | None = None
    user: str | None = None


class TurnSpec(BaseModel):
    """多轮测试中的单轮规格"""

    user: str
    assertions: list[AssertionSpec] = Field(default_factory=list)


class SimulatedUserConfig(BaseModel):
    """模拟用户配置"""

    system_prompt: str
    first_message: str
    max_turns: int = 10
    stop_conditions: list[AssertionSpec] | None = None


class PerformanceBudget(BaseModel):
    """整段对话性能预算"""

    max_avg_latency_ms: int | None = None
    max_total_tokens: int | None = None


class TestCaseSpec(BaseModel):
    """单个测试用例"""

    id: str
    name: str
    type: Literal["single_turn", "multi_turn", "simulated_user", "workflow"]
    # 单轮
    input: SingleTurnInput | None = None
    # 多轮
    turns: list[TurnSpec] | None = None
    judge_scene: str | None = None
    # 模拟用户
    simulated_user_config: SimulatedUserConfig | None = None
    per_turn_assertions: list[AssertionSpec] | None = None
    final_assertions: list[AssertionSpec] | None = None
    # 通用
    assertions: list[AssertionSpec] | None = None
    performance: PerformanceBudget | None = None


class SuiteMetadata(BaseModel):
    """测试套件元数据"""

    name: str
    description: str = ""
    target: str
    tags: list[str] = Field(default_factory=list)
    shared_inputs: dict[str, Any] | None = None


class TestSuiteSpec(BaseModel):
    """测试套件文件根模型"""

    suite: SuiteMetadata
    cases: list[TestCaseSpec]
