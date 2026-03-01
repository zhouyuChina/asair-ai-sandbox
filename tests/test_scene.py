"""阶段三单元测试 — 场景 Schema、SceneJudgeAssertion、Builder、Extractor"""

import asyncio
import json
from unittest.mock import AsyncMock

from sandbox.assertion.base import AssertionContext
from sandbox.assertion.builder import build_assertion
from sandbox.client.judge_llm import JudgeResult
from sandbox.schema.result import TurnResult
from sandbox.schema.scene import BehaviorSpec, SceneContext, SceneFile, SceneSpec
from sandbox.schema.test_case import AssertionSpec


# ─── 测试数据 ───────────────────────────────────────────────

def _make_scene() -> SceneSpec:
    return SceneSpec(
        id="phone_collection",
        name="电话号码收集",
        source="chats/test.txt",
        description="收集手机号场景",
        context=SceneContext(trigger="用户咨询产品"),
        behaviors=[
            BehaviorSpec(
                id="natural_transition",
                name="自然过渡",
                description="不生硬地引出收号",
                good_example="方便留个手机号吗？",
                bad_example="请提供手机号。",
                weight=0.6,
            ),
            BehaviorSpec(
                id="privacy_mask",
                name="隐私保护",
                description="手机号脱敏",
                good_example="139****5678",
                bad_example="13912345678",
                weight=0.4,
            ),
        ],
    )


# ─── Schema 测试 ───────────────────────────────────────────

class TestSceneSchema:
    """场景 Schema 校验"""

    def test_scene_spec_basic(self):
        scene = _make_scene()
        assert scene.id == "phone_collection"
        assert len(scene.behaviors) == 2
        assert scene.behaviors[0].weight + scene.behaviors[1].weight == 1.0

    def test_scene_file_model(self):
        scene = _make_scene()
        scene_file = SceneFile(scene=scene)
        data = scene_file.model_dump()
        assert data["scene"]["id"] == "phone_collection"

    def test_scene_from_yaml(self):
        import yaml

        yaml_text = """
scene:
  id: test_scene
  name: 测试场景
  description: 测试
  context:
    trigger: 用户提问
  behaviors:
    - id: b1
      name: 行为1
      description: 描述
      good_example: 好的示例
      weight: 1.0
"""
        data = yaml.safe_load(yaml_text)
        scene_file = SceneFile.model_validate(data)
        assert scene_file.scene.id == "test_scene"
        assert len(scene_file.scene.behaviors) == 1

    def test_validate_example_scene(self):
        from sandbox.utils.yaml_loader import load_and_validate

        scene_file = load_and_validate("examples/scenes/phone_collection.yaml", SceneFile)
        assert scene_file.scene.id == "phone_collection"
        assert len(scene_file.scene.behaviors) == 5


# ─── SceneJudgeAssertion 测试 ──────────────────────────────

class TestSceneJudgeAssertion:
    """场景驱动 Judge 断言"""

    def test_scene_judge_pass(self):
        """行为评分高于阈值 → 通过"""
        from sandbox.assertion.scene_judge import SceneJudgeAssertion

        scene = _make_scene()
        mock_client = AsyncMock()
        # LLM 返回逐行为评分 JSON
        behavior_response = json.dumps({
            "behaviors": [
                {"id": "natural_transition", "score": 0.9, "reasoning": "过渡自然"},
                {"id": "privacy_mask", "score": 0.8, "reasoning": "做了脱敏"},
            ],
            "overall": 0.86,
        })
        mock_client.evaluate.return_value = JudgeResult(
            score=0.86, reasoning="整体不错", raw_text=behavior_response,
        )

        assertion = SceneJudgeAssertion(
            scene=scene, judge_client=mock_client, pass_threshold=0.7,
        )

        async def _run():
            ctx = AssertionContext(
                history=[TurnResult(turn_index=0, user_message="你好", bot_response="你好呀", latency_ms=100)],
            )
            result = await assertion.evaluate("方便留个手机号吗？", {}, ctx)
            assert result.passed is True
            assert result.assertion_type == "scene_judge"
            assert result.score is not None
            # 加权: 0.9*0.6 + 0.8*0.4 = 0.54 + 0.32 = 0.86
            assert abs(result.score - 0.86) < 0.01
            assert result.details is not None
            assert len(result.details) == 2

        asyncio.run(_run())

    def test_scene_judge_fail(self):
        """行为评分低于阈值 → 失败"""
        from sandbox.assertion.scene_judge import SceneJudgeAssertion

        scene = _make_scene()
        mock_client = AsyncMock()
        behavior_response = json.dumps({
            "behaviors": [
                {"id": "natural_transition", "score": 0.3, "reasoning": "太生硬"},
                {"id": "privacy_mask", "score": 0.2, "reasoning": "没有脱敏"},
            ],
            "overall": 0.26,
        })
        mock_client.evaluate.return_value = JudgeResult(
            score=0.26, reasoning="差", raw_text=behavior_response,
        )

        assertion = SceneJudgeAssertion(
            scene=scene, judge_client=mock_client, pass_threshold=0.7,
        )

        async def _run():
            ctx = AssertionContext()
            result = await assertion.evaluate("请提供手机号", {}, ctx)
            assert result.passed is False
            # 加权: 0.3*0.6 + 0.2*0.4 = 0.18 + 0.08 = 0.26
            assert abs(result.score - 0.26) < 0.01

        asyncio.run(_run())

    def test_scene_judge_filter_behaviors(self):
        """指定 behavior_ids 筛选部分行为评估"""
        from sandbox.assertion.scene_judge import SceneJudgeAssertion

        scene = _make_scene()
        mock_client = AsyncMock()
        behavior_response = json.dumps({
            "behaviors": [
                {"id": "privacy_mask", "score": 0.9, "reasoning": "脱敏到位"},
            ],
            "overall": 0.9,
        })
        mock_client.evaluate.return_value = JudgeResult(
            score=0.9, reasoning="好", raw_text=behavior_response,
        )

        assertion = SceneJudgeAssertion(
            scene=scene,
            judge_client=mock_client,
            behavior_ids=["privacy_mask"],
            pass_threshold=0.7,
        )

        async def _run():
            ctx = AssertionContext()
            result = await assertion.evaluate("139****5678", {}, ctx)
            assert result.passed is True
            assert abs(result.score - 0.9) < 0.01

        asyncio.run(_run())

    def test_scene_judge_error_graceful(self):
        """LLM 调用失败 → 优雅降级"""
        from sandbox.assertion.scene_judge import SceneJudgeAssertion

        scene = _make_scene()
        mock_client = AsyncMock()
        mock_client.evaluate.side_effect = Exception("API 超时")

        assertion = SceneJudgeAssertion(
            scene=scene, judge_client=mock_client, pass_threshold=0.7,
        )

        async def _run():
            ctx = AssertionContext()
            result = await assertion.evaluate("test", {}, ctx)
            assert result.passed is False
            assert "调用失败" in result.message

        asyncio.run(_run())

    def test_scene_judge_no_matching_behaviors(self):
        """指定不存在的 behavior_ids → 返回失败"""
        from sandbox.assertion.scene_judge import SceneJudgeAssertion

        scene = _make_scene()
        mock_client = AsyncMock()

        assertion = SceneJudgeAssertion(
            scene=scene,
            judge_client=mock_client,
            behavior_ids=["nonexistent"],
            pass_threshold=0.7,
        )

        async def _run():
            ctx = AssertionContext()
            result = await assertion.evaluate("test", {}, ctx)
            assert result.passed is False
            assert "未找到" in result.message

        asyncio.run(_run())


# ─── Builder 集成测试 ──────────────────────────────────────

class TestAssertionBuilderSceneJudge:
    """断言工厂 scene_judge 集成"""

    def test_build_scene_judge(self):
        scene = _make_scene()
        mock_client = AsyncMock()

        spec = AssertionSpec(
            type="scene_judge",
            phase="信息收集",
            behaviors=["privacy_mask"],
            pass_threshold=0.8,
        )
        assertion = build_assertion(spec, judge_client=mock_client, scene=scene)
        assert assertion.__class__.__name__ == "SceneJudgeAssertion"

    def test_build_scene_judge_missing_scene(self):
        mock_client = AsyncMock()
        spec = AssertionSpec(type="scene_judge")

        try:
            build_assertion(spec, judge_client=mock_client, scene=None)
            assert False, "应该抛出异常"
        except Exception as e:
            assert "judge_scene" in str(e)

    def test_build_scene_judge_missing_client(self):
        scene = _make_scene()
        spec = AssertionSpec(type="scene_judge")

        try:
            build_assertion(spec, judge_client=None, scene=scene)
            assert False, "应该抛出异常"
        except Exception as e:
            assert "judge LLM" in str(e)


# ─── Extractor 测试 ────────────────────────────────────────

class TestSceneExtractor:
    """场景提炼器"""

    def test_extract_from_chat(self):
        from sandbox.extractor.scene_extractor import SceneExtractor

        mock_client = AsyncMock()
        # 模拟 LLM 返回的 YAML
        yaml_response = """```yaml
scene:
  id: greeting_scene
  name: 问候场景
  description: 用户问好
  context:
    trigger: 用户发起对话
  behaviors:
    - id: warm_greeting
      name: 热情问候
      description: 用热情的语气回应
      good_example: "你好呀！很高兴见到你"
      bad_example: "你好"
      weight: 1.0
```"""
        mock_client.evaluate.return_value = JudgeResult(
            score=0.0, reasoning="", raw_text=yaml_response,
        )
        mock_client.close = AsyncMock()

        extractor = SceneExtractor(mock_client)

        async def _run():
            scene = await extractor.extract("用户: 你好\nAI: 你好呀！", source_path="test.txt")
            assert scene.id == "greeting_scene"
            assert scene.source == "test.txt"
            assert len(scene.behaviors) == 1
            assert scene.behaviors[0].id == "warm_greeting"

        asyncio.run(_run())

    def test_extract_yaml_from_code_block(self):
        from sandbox.extractor.scene_extractor import SceneExtractor

        extractor = SceneExtractor(AsyncMock())
        raw = """这是一些前置文字

```yaml
scene:
  id: test
  name: 测试
```

这是一些后续文字"""
        result = extractor._extract_yaml(raw)
        assert "scene:" in result
        assert "id: test" in result

    def test_extract_yaml_direct(self):
        from sandbox.extractor.scene_extractor import SceneExtractor

        extractor = SceneExtractor(AsyncMock())
        raw = "scene:\n  id: test\n  name: 测试"
        result = extractor._extract_yaml(raw)
        assert result == raw
