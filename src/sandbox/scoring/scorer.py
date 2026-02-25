"""用例级 & 套件级评分"""

from sandbox.schema.config import ScoringConfig
from sandbox.schema.result import AssertionResult, CaseResult, CaseScore, SuiteResult, SuiteScore


class Scorer:
    """用例级评分器"""

    def __init__(self, scoring_config: ScoringConfig):
        self.dimensions = scoring_config.dimensions

    def score_case(self, case_result: CaseResult) -> CaseScore:
        all_assertions = self._flatten_assertions(case_result)

        if not all_assertions:
            return CaseScore(
                case_id=case_result.case_id,
                passed=case_result.status == "completed",
                pass_rate=1.0 if case_result.status == "completed" else 0.0,
                overall_score=1.0 if case_result.status == "completed" else 0.0,
            )

        # 1. 二元通过/失败
        passed = all(a.passed for a in all_assertions)
        pass_rate = sum(1 for a in all_assertions if a.passed) / len(all_assertions)

        # 2. 维度评分（从带 score 的断言中提取）
        dimension_scores: dict[str, float] = {}
        for dim_name in self.dimensions:
            dim_assertions = [a for a in all_assertions if a.dimension == dim_name and a.score is not None]
            if dim_assertions:
                dimension_scores[dim_name] = sum(a.score for a in dim_assertions) / len(dim_assertions)

        # 3. 加权综合评分
        overall = 0.0
        total_weight = 0.0
        for dim_name, dim_config in self.dimensions.items():
            if dim_name in dimension_scores:
                overall += dimension_scores[dim_name] * dim_config.weight
                total_weight += dim_config.weight
        overall_score = overall / total_weight if total_weight > 0 else pass_rate

        return CaseScore(
            case_id=case_result.case_id,
            passed=passed,
            pass_rate=pass_rate,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
        )

    def _flatten_assertions(self, case_result: CaseResult) -> list[AssertionResult]:
        """提取用例中所有断言结果"""
        results = []
        for turn in case_result.turns:
            results.extend(turn.assertions)
        results.extend(case_result.final_assertions)
        return results


class SuiteScorer:
    """套件级评分聚合"""

    def __init__(self, scorer: Scorer):
        self.scorer = scorer

    def score_suite(self, suite_result: SuiteResult) -> SuiteScore:
        case_scores = [self.scorer.score_case(cr) for cr in suite_result.case_results]

        if not case_scores:
            return SuiteScore(
                suite_name=suite_result.suite_name,
                total_cases=0,
                passed_cases=0,
                pass_rate=0.0,
                avg_overall_score=0.0,
            )

        total = len(case_scores)
        passed = sum(1 for cs in case_scores if cs.passed)
        avg_score = sum(cs.overall_score for cs in case_scores) / total

        # 维度平均
        dim_sums: dict[str, list[float]] = {}
        for cs in case_scores:
            for dim, score in cs.dimension_scores.items():
                dim_sums.setdefault(dim, []).append(score)
        dim_avgs = {dim: sum(scores) / len(scores) for dim, scores in dim_sums.items()}

        return SuiteScore(
            suite_name=suite_result.suite_name,
            total_cases=total,
            passed_cases=passed,
            pass_rate=passed / total,
            avg_overall_score=avg_score,
            dimension_averages=dim_avgs,
            case_scores=case_scores,
        )
