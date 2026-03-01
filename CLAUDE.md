# ASAIR AI Sandbox — 项目上下文

## 项目简介

Dify prompt & chatflow 沙箱测试工具。通过 YAML 定义测试套件，自动调用 Dify API 执行对话、
用断言引擎（字符串匹配 / 正则 / 性能 / LLM Judge）验证回复质量，输出评分报告。

完整设计文档：`docs/design.md`（2145 行，涵盖架构、Schema、CLI、六阶段路线图）。

## 技术栈

- Python 3.12 + asyncio + httpx
- Pydantic v2（Schema 校验）
- Click（CLI）
- Rich（日志 & 未来进度条）
- OpenAI 兼容接口（Judge LLM，当前用 GPT-4o）

## 项目结构

```
src/sandbox/
├── core/           # 异常、日志、全局配置加载（.env 自动加载 + 环境变量插值）
├── schema/         # Pydantic 模型：config / test_case / result
├── client/         # HTTP 客户端：dify_chat（Dify API）/ judge_llm（OpenAI 兼容）
├── assertion/      # 断言引擎：base / string_match / performance / llm_judge / builder
├── runner/         # 执行器：single_turn / multi_turn / engine（总调度）
├── scoring/        # 评分：scorer / dimensions
├── report/         # 报告：json_report
├── utils/          # 工具：yaml_loader / template / rate_limiter
└── cli.py          # CLI 入口（sandbox run / sandbox validate）
```

## 配置文件

- `sandbox.yaml` — 全局配置（Dify target + Judge LLM + 执行参数）
- `.env` — 敏感密钥（DIFY_API_KEY, JUDGE_LLM_API_KEY）
- `examples/suites/*.yaml` — 测试套件定义

## 开发阶段与当前进度

详细进度清单见 `PROGRESS.md`（打勾条件：代码完成 + 单元测试通过 + 端到端验证通过）。

| 阶段 | 内容 | 状态 |
|------|------|------|
| **阶段一** | 基础框架：配置加载、Dify 客户端、单轮测试、字符串/性能断言、JSON 报告、CLI | 已完成 |
| **阶段二** | 多轮对话 & LLM Judge：多轮运行器、Judge LLM 客户端、LLM-as-Judge 断言 | 已完成 |
| **阶段三** | 场景提炼 & 场景 Judge：场景 Schema、sandbox learn、场景驱动评分 | 未开始 |
| **阶段四** | 模拟用户 & 压力测试：LLM 驱动动态对话、Workflow、Streaming | 未开始 |
| **阶段五** | A/B 对比 & 报告：sandbox compare、HTML 报告、Prompt 优化顾问 | 未开始 |
| **阶段六** | 打磨 & CI：错误恢复、进度条、文档、CI/CD 集成 | 未开始 |

### 当前待办

1. **阶段三开发**：场景提炼 & 场景 Judge — 场景 Schema、sandbox learn 命令、场景驱动评分。

## 开发方式

采用**接口先行 + 分层 TDD** 策略：

- **适合 TDD 的模块**（接口清晰、行为可预期）：先写测试再实现
  - 新断言类型（scene_judge、json_path）
  - 新运行器（simulated_user、workflow）
  - 数据解析/转换逻辑（A/B 对比、报告生成）
- **探索性模块**（需要迭代、接口会变）：先实现再补测试
  - 场景提炼器（sandbox learn）— prompt 工程迭代性强
  - Prompt 优化顾问 — 输出格式需反复调整
  - Streaming 模式 — 依赖外部 SSE 行为
- 每个模块先定好输入输出的 Schema 和接口签名
- 每个阶段交付时必须保证测试覆盖完整

## 开发规范

- 每个阶段严格按 `PROGRESS.md` 打勾条件验证，不跳步
- 单元测试使用 pytest + AsyncMock，不依赖外部 API
- 端到端测试需用户配合（配置真实 API Key + 运行确认）
- 用户使用 Dify 云端版（api.dify.ai），Judge LLM 选择 OpenAI GPT-4o
- 代码提交遵循 conventional commits 格式（feat / fix / refactor）
