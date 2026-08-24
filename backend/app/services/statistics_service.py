import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.experiment import Experiment
from app.models.task import Task
from app.schemas.statistics import (
    TopologySummary,
    ChiSquareResult,
    ResultsSummaryResponse,
    StatisticalAnalysisResponse
)

ALLOWED_FAILURE_TYPES = [
    "No Failure",
    "Wrong Final Answer",
    "Hallucination / Unsupported Claim",
    "Contradiction",
    "Premature Agreement",
    "Information Loss"
]

ALL_TOPOLOGIES = ["STAR", "CHAIN", "MESH", "UNCONSTRAINED"]


class StatisticsService:
    """
    Aggregates experimental runs across topologies and performs Chi-Square tests of independence.
    """

    def get_summary(self, db: Session) -> ResultsSummaryResponse:
        experiments = db.query(Experiment).all()
        total_exp = len(experiments)

        if total_exp == 0:
            return ResultsSummaryResponse(
                total_experiments=0,
                overall_accuracy=0.0,
                topologies=[],
                failure_distribution={},
                tasks_tested_count=0
            )

        success_count = sum(1 for e in experiments if e.success)
        overall_accuracy = round((success_count / total_exp) * 100, 1)

        # Global failure distribution
        global_failures: Dict[str, int] = {}
        for e in experiments:
            f = e.failure_type or ("No Failure" if e.success else "Wrong Final Answer")
            global_failures[f] = global_failures.get(f, 0) + 1

        # Per-topology breakdown
        topo_summaries: List[TopologySummary] = []

        for topo in ALL_TOPOLOGIES:
            topo_exps = [e for e in experiments if e.topology == topo]
            count = len(topo_exps)
            if count == 0:
                topo_summaries.append(TopologySummary(topology=topo))
                continue

            s_count = sum(1 for e in topo_exps if e.success)
            fail_count = count - s_count
            acc = round((s_count / count) * 100, 1)
            fail_rate = round((fail_count / count) * 100, 1)
            avg_msgs = round(sum(e.total_messages for e in topo_exps) / count, 1)
            avg_turns = round(sum(e.turns_taken for e in topo_exps) / count, 1)

            # Average communication density
            densities = []
            for e in topo_exps:
                m = e.network_metrics
                if m and "communication_density" in m:
                    densities.append(m["communication_density"])
            avg_density = round(sum(densities) / len(densities), 3) if densities else 0.0

            # Topology failure breakdown
            f_map: Dict[str, int] = {}
            for e in topo_exps:
                ft = e.failure_type or ("No Failure" if e.success else "Wrong Final Answer")
                f_map[ft] = f_map.get(ft, 0) + 1

            topo_summaries.append(TopologySummary(
                topology=topo,
                total_runs=count,
                successful_runs=s_count,
                failed_runs=fail_count,
                accuracy=acc,
                failure_rate=fail_rate,
                avg_messages=avg_msgs,
                avg_turns=avg_turns,
                avg_density=avg_density,
                failure_breakdown=f_map
            ))

        tasks_count = len(set(e.task_id for e in experiments))

        return ResultsSummaryResponse(
            total_experiments=total_exp,
            overall_accuracy=overall_accuracy,
            topologies=topo_summaries,
            failure_distribution=global_failures,
            tasks_tested_count=tasks_count
        )

    def get_statistical_analysis(self, db: Session) -> StatisticalAnalysisResponse:
        summary = self.get_summary(db)
        experiments = db.query(Experiment).all()

        chi_result = self._calculate_chi_square(experiments)

        recommendations = []
        if summary.total_experiments < 6:
            recommendations.append("Run at least 2-3 repetitions across each topology (10+ experiments) for statistical significance.")
        else:
            # Generate research takeaways
            sorted_by_acc = sorted(summary.topologies, key=lambda t: t.accuracy, reverse=True)
            if sorted_by_acc and sorted_by_acc[0].total_runs > 0:
                best_topo = sorted_by_acc[0]
                recommendations.append(f"{best_topo.topology} achieved the highest accuracy ({best_topo.accuracy}%) with an average of {best_topo.avg_messages} messages per task.")

            sorted_by_msgs = sorted(summary.topologies, key=lambda t: t.avg_messages)
            if sorted_by_msgs and sorted_by_msgs[0].total_runs > 0:
                efficient_topo = sorted_by_msgs[0]
                recommendations.append(f"{efficient_topo.topology} was the most communication-efficient, utilizing {efficient_topo.avg_messages} messages on average.")

        return StatisticalAnalysisResponse(
            summary=summary,
            chi_square_analysis=chi_result,
            recommendations=recommendations
        )

    def _calculate_chi_square(self, experiments: List[Experiment]) -> ChiSquareResult:
        """Computes Chi-Square test of independence: Topologies vs Failure Types."""
        sample_size = len(experiments)

        if sample_size < 5:
            return ChiSquareResult(
                chi_square=None,
                p_value=None,
                degrees_of_freedom=None,
                is_significant=None,
                interpretation="Insufficient experimental data (N < 5). Run additional benchmark trials across Star, Chain, Mesh, and Unconstrained topologies to enable Chi-Square statistical testing.",
                contingency_table=None,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        # Include all topologies present in experiment data or from standard list
        topologies_present = list(dict.fromkeys([e.topology for e in experiments if e.topology] + ALL_TOPOLOGIES))
        
        # Find active failure types
        observed_failures = set()
        for e in experiments:
            ft = e.failure_type or ("No Failure" if e.success else "Wrong Final Answer")
            observed_failures.add(ft)

        failure_types = sorted(list(observed_failures))
        if len(failure_types) < 2:
            return ChiSquareResult(
                chi_square=None,
                p_value=None,
                degrees_of_freedom=None,
                is_significant=None,
                interpretation="Uniform failure distribution observed across trials. More variance in outcomes is needed to compute Chi-Square independence.",
                contingency_table=None,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        # Build Contingency Table
        matrix = []
        table_dict: Dict[str, Dict[str, int]] = {t: {} for t in topologies_present}

        # Filter topologies that actually have at least 1 experiment for matrix chi2 calculation
        active_topos_for_matrix = []
        for topo in topologies_present:
            topo_exps = [e for e in experiments if e.topology == topo]
            row = []
            for ft in failure_types:
                cnt = sum(1 for e in topo_exps if (e.failure_type or ("No Failure" if e.success else "Wrong Final Answer")) == ft)
                row.append(cnt)
                table_dict[topo][ft] = cnt
            if len(topo_exps) > 0:
                active_topos_for_matrix.append(row)

        if len(active_topos_for_matrix) < 2:
            return ChiSquareResult(
                chi_square=None,
                p_value=None,
                degrees_of_freedom=None,
                is_significant=None,
                interpretation="Only 1 topology has trial data. Run trials across at least 2 distinct topologies to compute Chi-Square independence.",
                contingency_table=table_dict,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        obs = np.array(active_topos_for_matrix)

        # Ensure we don't have all-zero rows or columns
        if np.all(obs.sum(axis=1) > 0) and np.all(obs.sum(axis=0) > 0):
            try:
                res = stats.chi2_contingency(obs)
                chi2_stat = round(float(res.statistic), 3)
                p_val = round(float(res.pvalue), 4)
                dof = int(res.dof)
                is_sig = p_val < 0.05

                if is_sig:
                    interp = (
                        f"Statistically Significant (X² = {chi2_stat}, p = {p_val}, df = {dof}, p < 0.05). "
                        "The communication topology significantly impacts the frequency and specific categories of multi-agent failures."
                    )
                else:
                    interp = (
                        f"Not Statistically Significant (X² = {chi2_stat}, p = {p_val}, df = {dof}, p >= 0.05). "
                        "No statistically significant difference in failure mode distribution was observed between the topologies at alpha = 0.05."
                    )

                return ChiSquareResult(
                    chi_square=chi2_stat,
                    p_value=p_val,
                    degrees_of_freedom=dof,
                    is_significant=is_sig,
                    interpretation=interp,
                    contingency_table=table_dict,
                    sample_size=sample_size,
                    is_sufficient_data=True
                )
            except Exception as e:
                return ChiSquareResult(
                    chi_square=None,
                    p_value=None,
                    degrees_of_freedom=None,
                    is_significant=None,
                    interpretation=f"Could not compute Chi-Square with current sample distribution: {e}",
                    contingency_table=table_dict,
                    sample_size=sample_size,
                    is_sufficient_data=False
                )

        return ChiSquareResult(
            chi_square=None,
            p_value=None,
            degrees_of_freedom=None,
            is_significant=None,
            interpretation="Some topologies currently have 0 trials. Run trials across Star, Chain, Mesh, and Unconstrained to complete the contingency matrix.",
            contingency_table=table_dict,
            sample_size=sample_size,
            is_sufficient_data=False
        )


statistics_service = StatisticsService()
