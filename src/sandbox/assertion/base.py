"""断言协议 / 基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sandbox.schema.result import AssertionResult, TurnResult


@dataclass
class AssertionContext:
    """断言评估上下文"""

    history: list[TurnResult] = field(default_factory=list)
    turn_index: int = 0

    def format_history(self) -> str:
        """格式化对话历史为文本"""
        lines = []
        for turn in self.history:
            lines.append(f"用户: {turn.user_message}")
            lines.append(f"AI: {turn.bot_response}")
        return "\n".join(lines)


class BaseAssertion(ABC):
    """断言基类，所有断言类型必须实现 evaluate 方法"""

    @abstractmethod
    async def evaluate(
        self,
        response_text: str,
        raw_response: dict,
        context: AssertionContext,
    ) -> AssertionResult:
        ...
