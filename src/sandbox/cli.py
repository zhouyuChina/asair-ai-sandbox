"""CLI 入口 — sandbox 命令行工具"""

import asyncio
import sys

import click
from rich.console import Console
from rich.table import Table

from sandbox import __version__
from sandbox.core.config import load_config
from sandbox.core.logging import setup_logging, get_logger
from sandbox.report.json_report import generate_json_report
from sandbox.runner.engine import TestEngine
from sandbox.scoring.scorer import Scorer, SuiteScorer
from sandbox.utils.yaml_loader import load_and_validate
from sandbox.schema.test_case import TestSuiteSpec

logger = get_logger(__name__)
console = Console()


@click.group()
@click.option("--config", "config_path", default="./sandbox.yaml", help="配置文件路径")
@click.option("--verbose", is_flag=True, help="开启详细日志")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, config_path: str, verbose: bool):
    """ASAIR AI Sandbox — Dify 提示词 & Chatflow 测试工具"""
    setup_logging(verbose=verbose)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["verbose"] = verbose


@cli.command()
@click.argument("suite_files", nargs=-1, required=True)
@click.option("--fail-threshold", default=0.0, type=float, help="最低通过评分")
@click.option("--output-dir", default=None, help="报告输出目录")
@click.pass_context
def run(ctx, suite_files: tuple[str, ...], fail_threshold: float, output_dir: str | None):
    """运行测试套件"""
    config_path = ctx.obj["config_path"]

    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        sys.exit(2)

    report_dir = output_dir or config.report.output_dir
    exit_code = 0

    for suite_file in suite_files:
        try:
            suite_spec = load_and_validate(suite_file, TestSuiteSpec)
        except Exception as e:
            console.print(f"[red]套件加载失败 ({suite_file}): {e}[/red]")
            exit_code = 2
            continue

        console.print(f"\n[bold]运行套件: {suite_spec.suite.name}[/bold]")
        console.print(f"  目标: {suite_spec.suite.target}  用例数: {len(suite_spec.cases)}")

        engine = TestEngine(config)
        suite_result = asyncio.run(engine.run_suite(suite_spec))

        # 评分
        scorer = Scorer(config.scoring)
        suite_scorer = SuiteScorer(scorer)
        suite_score = suite_scorer.score_suite(suite_result)

        # 输出结果摘要
        _print_summary(suite_score)

        # 生成报告
        if "json" in config.report.formats:
            report_path = generate_json_report(suite_result, suite_score, output_dir=report_dir)
            console.print(f"  报告: {report_path}")

        # 判定退出码
        if suite_score.avg_overall_score < fail_threshold:
            exit_code = 1
        if suite_score.passed_cases < suite_score.total_cases:
            exit_code = max(exit_code, 1)

    sys.exit(exit_code)


@cli.command()
@click.argument("suite_files", nargs=-1, required=True)
def validate(suite_files: tuple[str, ...]):
    """校验 YAML 文件（不执行）"""
    total_cases = 0
    valid_count = 0

    for suite_file in suite_files:
        try:
            suite_spec = load_and_validate(suite_file, TestSuiteSpec)
            case_count = len(suite_spec.cases)
            total_cases += case_count
            valid_count += 1
            console.print(f"  [green]OK[/green] {suite_file} ({case_count} cases)")
        except Exception as e:
            console.print(f"  [red]FAIL[/red] {suite_file}: {e}")

    console.print(f"\n{valid_count} 个套件有效，共 {total_cases} 个测试用例。")
    if valid_count < len(suite_files):
        sys.exit(2)


def _print_summary(suite_score):
    """打印评分摘要表格"""
    table = Table(title=f"结果: {suite_score.suite_name}")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("通过/总计", f"{suite_score.passed_cases}/{suite_score.total_cases}")
    table.add_row("通过率", f"{suite_score.pass_rate:.1%}")
    table.add_row("综合评分", f"{suite_score.avg_overall_score:.2f}")

    for dim, avg in suite_score.dimension_averages.items():
        table.add_row(f"  {dim}", f"{avg:.2f}")

    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
