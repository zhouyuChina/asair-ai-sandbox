"""JSON 报告输出"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from sandbox.core.logging import get_logger
from sandbox.schema.result import SuiteResult, SuiteScore

logger = get_logger(__name__)


def generate_json_report(
    suite_result: SuiteResult,
    suite_score: SuiteScore,
    output_dir: str = "./reports",
) -> Path:
    """生成 JSON 报告文件"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = suite_result.suite_name.replace(" ", "_")[:50]
    file_name = f"{safe_name}_{timestamp}.json"
    file_path = output_path / file_name

    report = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": {
            "name": suite_result.suite_name,
            "target": suite_result.target,
        },
        "summary": {
            "total_cases": suite_score.total_cases,
            "passed": suite_score.passed_cases,
            "failed": suite_score.total_cases - suite_score.passed_cases,
            "pass_rate": round(suite_score.pass_rate, 4),
            "avg_overall_score": round(suite_score.avg_overall_score, 4),
            "dimension_averages": {
                k: round(v, 4) for k, v in suite_score.dimension_averages.items()
            },
        },
        "cases": [asdict(cr) for cr in suite_result.case_results],
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON 报告已生成: {file_path}")
    return file_path
