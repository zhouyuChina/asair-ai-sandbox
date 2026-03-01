"""场景驱动 Judge 断言 — 基于黄金场景逐行为加权评分"""

from sandbox.assertion.base import AssertionContext, BaseAssertion
from sandbox.client.judge_llm import JudgeLLMClient
from sandbox.core.logging import get_logger
from sandbox.schema.result import AssertionResult
from sandbox.schema.scene import BehaviorSpec, SceneSpec

logger = get_logger(__name__)

SCENE_JUDGE_SYSTEM_PROMPT = """你是一个严格的AI对话质量评估专家。
你需要基于真人优秀对话中提炼的行为特征标准，逐项评估AI的回复。

对每个行为特征：
- 参考 good_example（优秀示范）和 bad_example（反面对照）
- 给出 0.0 到 1.0 的分数
- 附上具体理由

输出 JSON 格式:
{
  "behaviors": [
    {"id": "natural_transition", "score": 0.9, "reasoning": "..."},
    {"id": "privacy_mask", "score": 0.3, "reasoning": "..."}
  ],
  "overall": 0.72
}"""

SCENE_JUDGE_USER_TEMPLATE = """## 评分标准（来自真人优秀对话场景：{scene_name}）

当前评估阶段：{phase}

你需要逐项评估以下行为特征：

{behaviors_text}

## 对话上下文
{conversation_context}

## 待评估的AI回复
{response_text}

请逐项评分并输出 JSON。"""


class SceneJudgeAssertion(BaseAssertion):
    """基于黄金场景的逐行为评分"""

    def __init__(
        self,
        scene: SceneSpec,
        judge_client: JudgeLLMClient,
        phase: str | None = None,
        behavior_ids: list[str] | None = None,
        pass_threshold: float = 0.7,
    ):
        self.scene = scene
        self.judge_client = judge_client
        self.phase = phase
        self.behavior_ids = behavior_ids
        self.pass_threshold = pass_threshold

    async def evaluate(
        self,
        response_text: str,
        raw_response: dict,
        context: AssertionContext,
    ) -> AssertionResult:
        # 1. 筛选要评估的行为
        behaviors = self.scene.behaviors
        if self.behavior_ids:
            behaviors = [b for b in behaviors if b.id in self.behavior_ids]
            if not behaviors:
                return AssertionResult(
                    passed=False,
                    assertion_type="scene_judge",
                    message=f"未找到匹配的行为: {self.behavior_ids}",
                    expected=f"score >= {self.pass_threshold}",
                    actual="no matching behaviors",
                )

        # 2. 格式化行为特征文本
        behaviors_text = self._format_behaviors(behaviors)

        # 3. 调用 Judge LLM
        prompt = SCENE_JUDGE_USER_TEMPLATE.format(
            scene_name=self.scene.name,
            phase=self.phase or "全场景",
            behaviors_text=behaviors_text,
            conversation_context=context.format_history() or "(无上下文，首轮对话)",
            response_text=response_text,
        )

        try:
            result = await self.judge_client.evaluate(
                system_prompt=SCENE_JUDGE_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
        except Exception as e:
            logger.error(f"Scene Judge LLM 调用失败: {e}")
            return AssertionResult(
                passed=False,
                assertion_type="scene_judge",
                message=f"Scene Judge LLM 调用失败: {e}",
                expected=f"score >= {self.pass_threshold}",
                actual="error",
            )

        # 4. 加权计算综合得分
        # result 来自 JudgeLLMClient，返回的是 JudgeResult(score, reasoning, raw_text)
        # 对于 scene_judge，我们需要解析 raw_text 中的逐行为评分
        behavior_scores = self._parse_behavior_scores(result.raw_text, behaviors)
        overall = self._weighted_average(behavior_scores, behaviors)

        passed = overall >= self.pass_threshold
        return AssertionResult(
            passed=passed,
            assertion_type="scene_judge",
            message=f"场景「{self.scene.name}」评分: {overall:.2f}",
            expected=f"score >= {self.pass_threshold}",
            actual=overall,
            score=overall,
            details=behavior_scores,
        )

    def _format_behaviors(self, behaviors: list[BehaviorSpec]) -> str:
        lines = []
        for i, b in enumerate(behaviors, 1):
            lines.append(f"{i}. [{b.id}] {b.name} (权重 {b.weight})")
            lines.append(f"   说明: {b.description}")
            lines.append(f"   优秀示范: \"{b.good_example}\"")
            if b.bad_example:
                lines.append(f"   反面对照: \"{b.bad_example}\"")
            lines.append("")
        return "\n".join(lines)

    def _parse_behavior_scores(
        self, raw_text: str, behaviors: list[BehaviorSpec]
    ) -> list[dict]:
        """从 LLM 原始响应中解析逐行为评分"""
        import json
        import re

        # 尝试直接解析 JSON
        try:
            data = json.loads(raw_text)
            if "behaviors" in data:
                return data["behaviors"]
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: 从 markdown code block 中提取
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "behaviors" in data:
                    return data["behaviors"]
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: 为每个行为返回 LLM 的总分
        logger.warning("无法解析逐行为评分，使用 LLM 总分作为各行为得分")
        score_match = re.search(r'"overall"\s*:\s*([\d.]+)', raw_text)
        fallback_score = float(score_match.group(1)) if score_match else 0.5
        return [
            {"id": b.id, "score": fallback_score, "reasoning": "解析失败，使用总分"}
            for b in behaviors
        ]

    def _weighted_average(
        self, behavior_scores: list[dict], behaviors: list[BehaviorSpec]
    ) -> float:
        """按权重计算加权平均分"""
        weight_map = {b.id: b.weight for b in behaviors}
        total_weight = sum(weight_map.values())
        if total_weight == 0:
            # 等权重
            scores = [bs.get("score", 0) for bs in behavior_scores]
            return sum(scores) / len(scores) if scores else 0

        weighted_sum = 0.0
        for bs in behavior_scores:
            bid = bs.get("id", "")
            score = float(bs.get("score", 0))
            weight = weight_map.get(bid, 0)
            weighted_sum += score * weight

        return weighted_sum / total_weight
