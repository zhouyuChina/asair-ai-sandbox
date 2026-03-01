# ASAIR AI Sandbox — 开发进度

> 打勾条件：代码完成 + 单元测试通过 + 端到端验证通过

## 阶段清单

- [x] **阶段一：基础框架** (2026-02-25)
  - 配置加载（sandbox.yaml + .env 环境变量插值）
  - Dify Chatflow 异步客户端（httpx + 重试）
  - 单轮测试运行器
  - 断言引擎（contains, not_contains, regex, equals, latency_ms, token_usage）
  - 评分系统（用例级 + 套件级）
  - JSON 报告输出
  - CLI 入口（sandbox run / sandbox validate）
  - 验证：22 单元测试通过 + Dify 云端 3 用例端到端通过

- [x] **阶段二：多轮对话 & LLM Judge** (2026-02-27)
  - 多轮对话运行器（conversation_id 链式传递）
  - Judge LLM 客户端（OpenAI 兼容接口）
  - LLM-as-Judge 断言（0~1 评分）
  - 评分系统升级（维度评分）
  - 验证：36 单元测试通过 + 人设一致性多轮 4 轮对话 + LLM Judge 评分端到端通过

- [ ] **阶段三：场景提炼 & 场景 Judge**
  - 场景 Schema（BehaviorSpec, SceneSpec）
  - 场景提炼器（sandbox learn 命令）
  - 场景驱动 Judge 断言（逐行为加权评分）
  - 验证：sandbox learn 输出场景 YAML + 测试用例引用场景评分跑通

- [ ] **阶段四：模拟用户 & 压力测试**
  - 模拟用户 LLM 客户端
  - 模拟用户运行器（LLM 驱动动态对话）
  - Workflow 运行器
  - Streaming 模式支持
  - 验证：30 轮情感操纵压力测试跑通

- [ ] **阶段五：A/B 对比 & 报告 & 优化建议**
  - A/B 对比逻辑（sandbox compare 命令）
  - HTML 报告（Jinja2 模板）
  - A/B 差异报告
  - Prompt 优化顾问（--advise）
  - 验证：A/B 对比 + HTML 报告 + 优化建议全流程跑通

- [ ] **阶段六：打磨 & CI 集成**
  - 错误恢复与优雅降级
  - CLI 进度条（rich 库）
  - 完善文档和示例
  - CI/CD 集成指南
  - 验证：CI 流水线跑通
