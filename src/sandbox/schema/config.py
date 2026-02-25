"""全局配置 Pydantic 模型

对应 sandbox.yaml 配置文件。
"""

from typing import Literal

from pydantic import BaseModel, Field


class TargetConfig(BaseModel):
    """Dify 连接目标配置"""

    api_base: str
    api_key: str
    app_type: Literal["chatflow", "workflow"] = "chatflow"
    response_mode: Literal["blocking", "streaming"] = "blocking"
    timeout: float = 30.0
    max_retries: int = 2


class LLMConfig(BaseModel):
    """LLM 配置（Judge / SimUser 共用结构）"""

    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    temperature: float = 0.0
    timeout: float = 60.0


class ExecutionConfig(BaseModel):
    """执行设置"""

    concurrency: int = 5
    rate_limit_rpm: int = 60
    rate_limit_burst: int = 10
    default_user_prefix: str = "sandbox_test"


class DimensionConfig(BaseModel):
    """评分维度"""

    weight: float = 0.0
    description: str = ""


class ScoringConfig(BaseModel):
    """评分设置"""

    dimensions: dict[str, DimensionConfig] = Field(default_factory=dict)


class ReportConfig(BaseModel):
    """报告输出设置"""

    output_dir: str = "./reports"
    formats: list[Literal["json", "html"]] = Field(default_factory=lambda: ["json", "html"])


class SandboxConfig(BaseModel):
    """sandbox.yaml 全局配置根模型"""

    version: str = "1.0"
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    judge: LLMConfig = Field(default_factory=LLMConfig)
    simulated_user: LLMConfig = Field(default_factory=LLMConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
