"""黄金场景 Pydantic 模型

从真人优秀对话中提炼的场景定义，用于 scene_judge 断言评分。
"""

from pydantic import BaseModel, Field


class BehaviorSpec(BaseModel):
    """单个优秀行为特征"""

    id: str
    name: str
    description: str
    good_example: str
    bad_example: str | None = None
    weight: float = 0.0


class ConversationPhase(BaseModel):
    """对话阶段模式"""

    phase: str
    turns: str
    key_action: str


class SceneContext(BaseModel):
    """场景触发上下文"""

    trigger: str
    precondition: str | None = None


class SceneSpec(BaseModel):
    """一个完整的黄金场景"""

    id: str
    name: str
    source: str = ""
    description: str
    context: SceneContext
    behaviors: list[BehaviorSpec] = Field(min_length=1)
    conversation_pattern: list[ConversationPhase] | None = None


class SceneFile(BaseModel):
    """场景 YAML 文件根模型"""

    scene: SceneSpec
