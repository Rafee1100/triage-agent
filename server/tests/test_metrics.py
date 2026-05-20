import pytest

from src.eval.metrics import kendall_tau, ndcg_at_k


def test_ndcg_perfect_prediction_is_one() -> None:
    assert ndcg_at_k([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], k=5) == 1.0


def test_ndcg_reversed_prediction_is_strictly_less_than_perfect() -> None:
    perfect = ndcg_at_k([1, 2, 3], [1, 2, 3], k=3)
    reversed_ = ndcg_at_k([3, 2, 1], [1, 2, 3], k=3)
    assert reversed_ < perfect


def test_ndcg_unknown_predictions_get_zero_relevance() -> None:
    score = ndcg_at_k([99, 1, 2], [1, 2, 3], k=3)
    assert 0.0 < score < 1.0


def test_ndcg_empty_inputs_return_zero() -> None:
    assert ndcg_at_k([], [1, 2, 3], k=3) == 0.0
    assert ndcg_at_k([1, 2, 3], [], k=3) == 0.0
    assert ndcg_at_k([1, 2, 3], [1, 2, 3], k=0) == 0.0


def test_ndcg_k_larger_than_ground_truth() -> None:
    score = ndcg_at_k([1, 2, 3], [1, 2, 3], k=10)
    assert score == 1.0


def test_kendall_tau_perfect_is_one() -> None:
    assert kendall_tau([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1.0)


def test_kendall_tau_fully_reversed_is_minus_one() -> None:
    assert kendall_tau([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]) == pytest.approx(-1.0)


def test_kendall_tau_with_single_overlap_returns_zero() -> None:
    assert kendall_tau([1], [1, 2, 3]) == 0.0


def test_kendall_tau_no_overlap_returns_zero() -> None:
    assert kendall_tau([99, 100], [1, 2, 3]) == 0.0
