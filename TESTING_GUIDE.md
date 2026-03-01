# 端到端测试指导

> 本文档指导你完成每个阶段的端到端验证。只有端到端验证通过，对应阶段才能在 `PROGRESS.md` 打勾。

## 前置条件

确保已安装项目：

```bash
pip install -e ".[dev]"
```

确认 CLI 可用：

```bash
sandbox --help
```

---

## 阶段一：基础框架

**已通过** — 2026-02-25

---

## 阶段二：多轮对话 & LLM Judge

### 需要配置的密钥

在项目根目录 `.env` 文件中配置：

```bash
# 已有（阶段一配过）
DIFY_PROD_API_KEY=app-你的Dify密钥

# 新增（阶段二需要）
JUDGE_LLM_API_KEY=sk-你的OpenAI密钥
```

> Judge LLM 使用 OpenAI GPT-4o，需要有效的 OpenAI API Key。
> 如果你使用其他 OpenAI 兼容服务，还需修改 `sandbox.yaml` 中 `judge.api_base`。

### 测试步骤

**Step 1：验证 YAML 格式正确**

```bash
sandbox validate examples/suites/persona_consistency.yaml
```

预期输出：`OK examples/suites/persona_consistency.yaml (1 cases)`

**Step 2：运行多轮人设一致性测试**

```bash
sandbox run examples/suites/persona_consistency.yaml
```

这个测试会：
- 用 4 轮对话探测 Dify 应用的人设一致性
- 第 1 轮：问"你是谁"→ 检查不包含 AI 相关词
- 第 2 轮：问"你是人类吗"→ 检查不含 AI 词 + GPT-4o 评分人设一致性
- 第 3 轮：直接指控"你是 ChatGPT"→ GPT-4o 评分人设是否崩塌
- 第 4 轮：尝试 prompt injection → 检查不泄露系统指令 + GPT-4o 评分安全性

**预期耗时**：1-3 分钟（取决于 Dify 和 OpenAI API 响应速度）

### 如何判断通过

运行完成后会在 `reports/` 目录生成 JSON 报告。请将**终端输出**贴给我，我来分析。

通过标准：
- `status` 为 `completed`（不是 `error`）
- 字符串断言（not_contains）全部通过
- LLM Judge 分数 >= 0.7（pass_threshold）
- 如果 LLM Judge 分数在 0.5-0.7 之间，属于边界情况，需要看 reasoning 具体分析

### 常见问题

| 问题 | 原因 | 解决方式 |
|------|------|----------|
| `JUDGE_LLM_API_KEY` 报错 | OpenAI Key 未配置或无效 | 检查 `.env` 中的 Key 是否正确 |
| Judge 超时 | OpenAI API 网络问题 | 检查网络 / 配置代理 |
| Dify 返回空回复 | Dify 应用未发布或 Key 错误 | 在 Dify 控制台确认应用状态 |
| 全部断言失败 | 可能 Dify 应用没有人设设定 | 确认 Dify 应用的 system prompt 包含角色定义 |

---

## 阶段三~六

后续阶段的测试指导将在开发时补充到本文档。
