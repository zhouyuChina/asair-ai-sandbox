"""主测试执行引擎"""

import asyncio

from sandbox.core.logging import get_logger
from sandbox.runner.single_turn import SingleTurnRunner
from sandbox.schema.config import SandboxConfig
from sandbox.schema.result import CaseResult, SuiteResult
from sandbox.schema.test_case import TestSuiteSpec
from sandbox.utils.rate_limiter import TokenBucketRateLimiter

logger = get_logger(__name__)


class TestEngine:
    """
    主编排器：加载套件 → 并发执行 → 收集结果

    职责：
    - 解析 target 配置
    - 分发到对应 Runner
    - 通过 Semaphore 控制并发度
    - 汇总结果
    """

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.execution.concurrency)
        self.rate_limiter = TokenBucketRateLimiter(
            rpm=config.execution.rate_limit_rpm,
            burst=config.execution.rate_limit_burst,
        )
        self._single_turn_runner = SingleTurnRunner()

    async def run_suite(self, suite_spec: TestSuiteSpec) -> SuiteResult:
        """执行一个测试套件"""
        target_name = suite_spec.suite.target
        if target_name not in self.config.targets:
            logger.error(f"目标 '{target_name}' 未在配置中定义")
            return SuiteResult(
                suite_name=suite_spec.suite.name,
                target=target_name,
                case_results=[
                    CaseResult(
                        case_id=case.id,
                        status="error",
                        error_message=f"目标 '{target_name}' 未在配置中定义",
                    )
                    for case in suite_spec.cases
                ],
            )

        target_config = self.config.targets[target_name]
        shared_inputs = suite_spec.suite.shared_inputs

        tasks = [
            self._run_case_with_semaphore(case, target_config, shared_inputs)
            for case in suite_spec.cases
        ]

        case_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed: list[CaseResult] = []
        for i, result in enumerate(case_results):
            if isinstance(result, Exception):
                processed.append(
                    CaseResult(
                        case_id=suite_spec.cases[i].id,
                        status="error",
                        error_message=str(result),
                    )
                )
            else:
                processed.append(result)

        return SuiteResult(
            suite_name=suite_spec.suite.name,
            target=target_name,
            case_results=processed,
        )

    async def _run_case_with_semaphore(self, case, target_config, shared_inputs) -> CaseResult:
        async with self.semaphore:
            await self.rate_limiter.acquire()
            runner = self._get_runner(case.type)
            return await runner.execute(case, target_config, shared_inputs)

    def _get_runner(self, case_type: str):
        match case_type:
            case "single_turn":
                return self._single_turn_runner
            case _:
                raise ValueError(f"Runner 类型 '{case_type}' 将在后续阶段实现")
