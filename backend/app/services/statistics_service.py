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

import math
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.experiment import Experiment
from app.models.task import Task
from app.schemas.statistics import (
    TopologySummary,
    ChiSquareResult,
    ResultsSummaryResponse,
    StatisticalAnalysisResponse,
    ResearchDatasetExport
)

ALLOWED_FAILURE_TYPES = [
    "No Failure",
    "Wrong Final Answer",
    "Hallucination / Unsupported Claim",
    "Contradiction",
    "Premature Agreement",
    "Information Loss"
]

ALL_TOPOLOGIES = [
    "STAR",
    "CHAIN",
    "MESH",
    "TREE",
    "UNCONSTRAINED",
    "ACTOR",
    "STREAM",
    "DISTRIBUTED_STATE"
]


def wilson_score_interval(successes: int, total: int) -> tuple[float, float]:
    """Calculates Wilson score 95% confidence interval for binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence z-score
    p_hat = successes / total
    denom = 1 + (z ** 2) / total
    center = p_hat + (z ** 2) / (2 * total)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + (z ** 2) / (4 * total)) / total)
    lower = max(0.0, (center - margin) / denom)
    upper = min(1.0, (center + margin) / denom)
    return round(lower * 100, 1), round(upper * 100, 1)


class StatisticsService:
    """
    Aggregates experimental runs across all 8 topologies and performs Chi-Square tests of independence,
    Cramer's V effect sizes, confidence intervals, and research paper dataset exports.
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
            topo_exps = [e for e in experiments if (e.topology or '').upper() == topo or (topo == "UNCONSTRAINED" and (e.topology or '').upper() == "EMERGENT")]
            count = len(topo_exps)
            if count == 0:
                topo_summaries.append(TopologySummary(topology=topo))
                continue

            s_count = sum(1 for e in topo_exps if e.success)
            fail_count = count - s_count
            acc = round((s_count / count) * 100, 1)
            fail_rate = round((fail_count / count) * 100, 1)
            ci_low, ci_high = wilson_score_interval(s_count, count)
            avg_msgs = round(sum(e.total_messages for e in topo_exps) / count, 1)
            avg_turns = round(sum(e.turns_taken for e in topo_exps) / count, 1)

            # Graph metrics aggregation
            densities = []
            betweennesses = []
            closenesses = []
            ginis = []
            entropies = []

            for e in topo_exps:
                m = e.network_metrics or {}
                if "communication_density" in m:
                    densities.append(m["communication_density"])
                if "betweenness_centrality" in m and isinstance(m["betweenness_centrality"], dict):
                    vals = list(m["betweenness_centrality"].values())
                    if vals:
                        betweennesses.append(sum(vals) / len(vals))
                if "closeness_centrality" in m and isinstance(m["closeness_centrality"], dict):
                    vals = list(m["closeness_centrality"].values())
                    if vals:
                        closenesses.append(sum(vals) / len(vals))
                if "message_gini" in m:
                    ginis.append(m["message_gini"])
                if "shannon_entropy" in m:
                    entropies.append(m["shannon_entropy"])

            avg_density = round(sum(densities) / len(densities), 3) if densities else 0.0
            avg_betweenness = round(sum(betweennesses) / len(betweennesses), 4) if betweennesses else 0.0
            avg_closeness = round(sum(closenesses) / len(closenesses), 4) if closenesses else 0.0
            avg_gini = round(sum(ginis) / len(ginis), 4) if ginis else 0.0
            avg_entropy = round(sum(entropies) / len(entropies), 4) if entropies else 0.0

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
                ci_95_lower=ci_low,
                ci_95_upper=ci_high,
                avg_messages=avg_msgs,
                avg_turns=avg_turns,
                avg_density=avg_density,
                avg_betweenness=avg_betweenness,
                avg_closeness=avg_closeness,
                avg_gini=avg_gini,
                avg_entropy=avg_entropy,
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
            active_topos = [t for t in sorted_by_acc if t.total_runs > 0]
            if active_topos:
                best_topo = active_topos[0]
                recommendations.append(
                    f"{best_topo.topology} achieved the highest empirical accuracy ({best_topo.accuracy}%, 95% CI [{best_topo.ci_95_lower}%, {best_topo.ci_95_upper}%]) with an average of {best_topo.avg_messages} messages per task."
                )

            sorted_by_msgs = sorted(summary.topologies, key=lambda t: t.avg_messages)
            active_by_msgs = [t for t in sorted_by_msgs if t.total_runs > 0]
            if active_by_msgs:
                efficient_topo = active_by_msgs[0]
                recommendations.append(
                    f"{efficient_topo.topology} was the most communication-efficient, utilizing {efficient_topo.avg_messages} messages on average."
                )

        return StatisticalAnalysisResponse(
            summary=summary,
            chi_square_analysis=chi_result,
            recommendations=recommendations
        )

    def _calculate_chi_square(self, experiments: List[Experiment]) -> ChiSquareResult:
        """Computes Chi-Square test of independence: Topologies vs Failure Types and Cramer's V effect size."""
        sample_size = len(experiments)

        if sample_size < 5:
            return ChiSquareResult(
                chi_square=None,
                p_value=None,
                degrees_of_freedom=None,
                is_significant=None,
                cramers_v=None,
                effect_size_label=None,
                interpretation="Insufficient experimental data (N < 5). Run additional benchmark trials to enable Chi-Square statistical testing.",
                contingency_table=None,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        topologies_present = list(dict.fromkeys([e.topology for e in experiments if e.topology] + ALL_TOPOLOGIES))

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
                cramers_v=None,
                effect_size_label=None,
                interpretation="Uniform failure distribution observed across trials. More variance in outcomes is needed to compute Chi-Square independence.",
                contingency_table=None,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        # Build Contingency Table
        table_dict: Dict[str, Dict[str, int]] = {t: {} for t in topologies_present}
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
                cramers_v=None,
                effect_size_label=None,
                interpretation="Only 1 topology has trial data. Run trials across at least 2 distinct topologies to compute Chi-Square independence.",
                contingency_table=table_dict,
                sample_size=sample_size,
                is_sufficient_data=False
            )

        obs = np.array(active_topos_for_matrix)

        if np.all(obs.sum(axis=1) > 0) and np.all(obs.sum(axis=0) > 0):
            try:
                res = stats.chi2_contingency(obs)
                chi2_stat = round(float(res.statistic), 3)
                p_val = round(float(res.pvalue), 4)
                dof = int(res.dof)
                is_sig = p_val < 0.05

                # Cramer's V effect size
                n_total = obs.sum()
                r, c = obs.shape
                min_dim = min(r - 1, c - 1)
                if min_dim > 0 and n_total > 0:
                    v = math.sqrt(chi2_stat / (n_total * min_dim))
                    cramers_v = round(float(v), 3)
                    if cramers_v < 0.1:
                        eff_label = "Negligible effect"
                    elif cramers_v < 0.3:
                        eff_label = "Small to medium effect"
                    elif cramers_v < 0.5:
                        eff_label = "Medium to large effect"
                    else:
                        eff_label = "Large effect size"
                else:
                    cramers_v = None
                    eff_label = None

                if is_sig:
                    interp = (
                        f"Statistically Significant (X² = {chi2_stat}, p = {p_val}, df = {dof}, Cramér's V = {cramers_v} [{eff_label}]). "
                        "The communication topology significantly impacts the frequency and specific categories of multi-agent failures."
                    )
                else:
                    interp = (
                        f"Not Statistically Significant (X² = {chi2_stat}, p = {p_val}, df = {dof}, Cramér's V = {cramers_v} [{eff_label}]). "
                        "No statistically significant difference in failure mode distribution was observed between the topologies at alpha = 0.05."
                    )

                return ChiSquareResult(
                    chi_square=chi2_stat,
                    p_value=p_val,
                    degrees_of_freedom=dof,
                    is_significant=is_sig,
                    cramers_v=cramers_v,
                    effect_size_label=eff_label,
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
                    cramers_v=None,
                    effect_size_label=None,
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
            cramers_v=None,
            effect_size_label=None,
            interpretation="Some topologies currently have 0 trials. Run trials across multiple topologies to complete the contingency matrix.",
            contingency_table=table_dict,
            sample_size=sample_size,
            is_sufficient_data=False
        )

    def get_research_export(self, db: Session) -> Dict[str, Any]:
        """
        Generates a comprehensive, structured JSON export package containing all computed measures,
        network graphs, statistical hypothesis tests, and raw trial transcripts for research paper writing.
        """
        stats_analysis = self.get_statistical_analysis(db)
        summary = stats_analysis.summary
        chi = stats_analysis.chi_square_analysis

        experiments = db.query(Experiment).options(
            joinedload(Experiment.task),
            joinedload(Experiment.messages)
        ).order_by(Experiment.created_at.desc()).all()

        trials_list = []
        for exp in experiments:
            msgs = []
            for m in (exp.messages or []):
                msgs.append({
                    "id": m.id,
                    "turn": m.turn,
                    "sender_id": m.sender_id,
                    "sender_role": m.sender_role,
                    "receiver_id": m.receiver_id,
                    "receiver_role": m.receiver_role,
                    "content": m.content,
                    "model_name": m.model_name,
                    "provider": m.provider,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None
                })

            trials_list.append({
                "experiment_id": exp.id,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
                "topology": exp.topology,
                "num_agents": exp.num_agents,
                "turns_taken": exp.turns_taken,
                "total_messages": exp.total_messages,
                "success": exp.success,
                "failure_type": exp.failure_type,
                "failure_reason": exp.failure_reason,
                "final_answer": exp.final_answer,
                "task": {
                    "id": exp.task.id if exp.task else exp.task_id,
                    "title": exp.task.title if exp.task else None,
                    "category": exp.task.category if exp.task else None,
                    "difficulty": exp.task.difficulty if exp.task else None,
                    "question": exp.task.question if exp.task else None,
                    "expected_answer": exp.task.expected_answer if exp.task else None,
                    "evaluation_criteria": exp.task.evaluation_criteria if exp.task else None,
                },
                "network_metrics": exp.network_metrics or {},
                "messages": msgs
            })

        return {
            "dataset_title": "AgentMesh Multi-Agent Topology Experimental Dataset",
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_experiments": len(experiments),
            "overall_accuracy": summary.overall_accuracy,
            "topologies_analyzed": ALL_TOPOLOGIES,
            "statistical_tests": {
                "chi_square_test_of_independence": {
                    "chi_square_statistic": chi.chi_square,
                    "degrees_of_freedom": chi.degrees_of_freedom,
                    "p_value": chi.p_value,
                    "is_significant": chi.is_significant,
                    "cramers_v_effect_size": chi.cramers_v,
                    "effect_size_label": chi.effect_size_label,
                    "interpretation": chi.interpretation,
                    "contingency_table": chi.contingency_table,
                    "sample_size": chi.sample_size
                },
                "academic_citation": "AgentMesh Multi-Agent Topology Benchmark Lab (2026). Empirical Deliberation and Failure Cascade Analysis Across Topologies."
            },
            "topology_summaries": [t.model_dump() for t in summary.topologies],
            "trials": trials_list
        }


statistics_service = StatisticsService()

