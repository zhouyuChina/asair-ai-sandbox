"""场景提炼器 — 从真人聊天记录中提炼黄金场景"""

import json
import re

import yaml

from sandbox.client.judge_llm import JudgeLLMClient
from sandbox.core.logging import get_logger
from sandbox.schema.scene import SceneFile, SceneSpec

logger = get_logger(__name__)

EXTRACT_SYSTEM_PROMPT = """你是一个资深的对话设计分析师。
你的任务是分析真人客服的优秀对话记录，从中提炼出可复用的「场景」。

每个场景需要提炼：
1. 场景 ID、名称、触发条件、前置条件
2. 优秀行为特征（good_example 直接引用原文 + bad_example 反面对照 + 权重）
3. 对话阶段模式（几轮完成、每轮关键动作）

要求：
- 行为特征必须具体可评估，不要笼统描述
- good_example 直接从原文中引用
- bad_example 是该行为的反面对照（你构造的）
- 所有 behavior 的 weight 之和 = 1.0
- 输出严格遵循指定的 YAML 格式

输出格式：
```yaml
scene:
  id: "场景ID"
  name: "场景名称"
  description: "场景说明"
  context:
    trigger: "触发条件"
    precondition: "前置条件（可选）"
  behaviors:
    - id: "行为ID"
      name: "行为名称"
      description: "行为说明"
      good_example: "引用原文"
      bad_example: "反面对照"
      weight: 0.3
  conversation_pattern:
    - phase: "阶段名称"
      turns: "1-2"
      key_action: "关键动作"
```"""

EXTRACT_USER_TEMPLATE = """请分析以下真人聊天记录，提炼出结构化场景。

## 聊天记录
{chat_text}

请输出 YAML 格式的场景描述。"""


class SceneExtractor:
    """从真人聊天记录中提炼黄金场景"""

    def __init__(self, judge_client: JudgeLLMClient):
        self.judge_client = judge_client

    async def extract(self, chat_text: str, source_path: str) -> SceneSpec:
        """
        分析一段真人聊天记录，输出结构化场景

        参数：
            chat_text: 真人聊天记录原文
            source_path: 来源文件路径（记录溯源）
        返回：
            SceneSpec 结构化场景对象
        """
        prompt = EXTRACT_USER_TEMPLATE.format(chat_text=chat_text)
        result = await self.judge_client.evaluate(
            system_prompt=EXTRACT_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        # 从 LLM 返回的文本中提取 YAML
        yaml_text = self._extract_yaml(result.raw_text)
        scene_file = SceneFile.model_validate(yaml.safe_load(yaml_text))
        scene_file.scene.source = source_path
        return scene_file.scene

    def _extract_yaml(self, raw_text: str) -> str:
        """从 LLM 响应中提取 YAML 内容"""
        # 尝试从 code block 中提取
        yaml_match = re.search(r"```(?:yaml)?\s*\n(.*?)```", raw_text, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip()

        # 尝试直接解析（LLM 可能直接返回 YAML）
        if raw_text.strip().startswith("scene:"):
            return raw_text.strip()

        # 如果响应是 JSON 格式，尝试转换
        try:
            data = json.loads(raw_text)
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        except (json.JSONDecodeError, TypeError):
            pass

        # 最后兜底：返回原文让 YAML 解析器尝试
        return raw_text
