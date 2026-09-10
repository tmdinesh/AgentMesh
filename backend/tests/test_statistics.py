import pytest
from app.services.statistics_service import statistics_service
from app.models.experiment import Experiment


def test_chi_square_with_insufficient_data():
    experiments = []
    res = statistics_service._calculate_chi_square(experiments)
    assert res.is_sufficient_data is False
    assert "Insufficient" in res.interpretation


def test_chi_square_with_varied_trials():
    exps = []
    # Star trials (mostly success)
    for i in range(8):
        exps.append(Experiment(topology="STAR", success=True, failure_type="No Failure"))
    for i in range(2):
        exps.append(Experiment(topology="STAR", success=False, failure_type="Premature Agreement"))

    # Chain trials (more failures / information loss)
    for i in range(4):
        exps.append(Experiment(topology="CHAIN", success=True, failure_type="No Failure"))
    for i in range(6):
        exps.append(Experiment(topology="CHAIN", success=False, failure_type="Information Loss"))

    # Mesh trials
    for i in range(7):
        exps.append(Experiment(topology="MESH", success=True, failure_type="No Failure"))
    for i in range(3):
        exps.append(Experiment(topology="MESH", success=False, failure_type="Wrong Final Answer"))

    res = statistics_service._calculate_chi_square(exps)
    assert res.sample_size == 30
    assert res.is_sufficient_data is True
    assert res.chi_square is not None
    assert res.p_value is not None
    assert res.degrees_of_freedom is not None
    # Cramér's V effect size assertions
    assert res.cramers_v is not None
    assert res.cramers_v >= 0.0
    assert any(w in res.effect_size_label for w in ["Negligible", "Small", "Moderate", "Large", "Very Large"])

    # Wilson 95% Confidence Interval assertions
    from app.services.statistics_service import wilson_score_interval
    ci_low, ci_high = wilson_score_interval(8, 10)
    assert 0.0 <= ci_low <= 80.0 <= ci_high <= 100.0
    # Test boundary 0 and total
    zero_low, zero_high = wilson_score_interval(0, 5)
    assert zero_low == 0.0
    assert zero_high > 0.0
