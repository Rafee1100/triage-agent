from src.eval.baselines import author_only_ranker, label_only_ranker, random_ranker
from src.features.extractor import PRFeatures


def _features(
    *,
    pr_number: int,
    priority: str | None = None,
    age_days: float = 1.0,
    merged_count: int = 5,
) -> PRFeatures:
    return PRFeatures(
        pr_number=pr_number,
        title="t",
        author_login="alice",
        lines_added=10,
        lines_deleted=5,
        files_changed=2,
        ticket_priority_label=priority,
        author_merged_pr_count=merged_count,
        author_revert_rate=0.0,
        author_avg_review_comments=5.0,
        pr_age_days=age_days,
        days_since_last_activity=age_days,
    )


def test_random_ranker_is_deterministic_for_same_seed() -> None:
    prs = [_features(pr_number=i) for i in range(1, 6)]
    assert random_ranker(prs, seed=42) == random_ranker(prs, seed=42)


def test_random_ranker_changes_order_with_different_seed() -> None:
    prs = [_features(pr_number=i) for i in range(1, 21)]
    assert random_ranker(prs, seed=1) != random_ranker(prs, seed=2)


def test_random_ranker_returns_all_pr_numbers_exactly_once() -> None:
    prs = [_features(pr_number=i) for i in range(1, 11)]
    ranked = random_ranker(prs)
    assert sorted(ranked) == list(range(1, 11))


def test_label_only_ranker_orders_high_medium_low_none() -> None:
    prs = [
        _features(pr_number=10, priority="low"),
        _features(pr_number=20, priority="high"),
        _features(pr_number=30, priority=None),
        _features(pr_number=40, priority="medium"),
    ]
    assert label_only_ranker(prs) == [20, 40, 10, 30]


def test_label_only_ranker_tiebreaks_by_older_first() -> None:
    prs = [
        _features(pr_number=1, priority="high", age_days=2.0),
        _features(pr_number=2, priority="high", age_days=10.0),
        _features(pr_number=3, priority="high", age_days=5.0),
    ]
    assert label_only_ranker(prs) == [2, 3, 1]


def test_label_only_ranker_case_insensitive() -> None:
    prs = [
        _features(pr_number=1, priority="HIGH"),
        _features(pr_number=2, priority="low"),
    ]
    assert label_only_ranker(prs) == [1, 2]


def test_author_only_ranker_orders_by_merged_count_descending() -> None:
    prs = [
        _features(pr_number=1, merged_count=5),
        _features(pr_number=2, merged_count=40),
        _features(pr_number=3, merged_count=15),
    ]
    assert author_only_ranker(prs) == [2, 3, 1]


def test_author_only_ranker_tiebreaks_by_older_first() -> None:
    prs = [
        _features(pr_number=1, merged_count=20, age_days=3.0),
        _features(pr_number=2, merged_count=20, age_days=12.0),
        _features(pr_number=3, merged_count=20, age_days=7.0),
    ]
    assert author_only_ranker(prs) == [2, 3, 1]


def test_baselines_handle_empty_input() -> None:
    assert random_ranker([]) == []
    assert label_only_ranker([]) == []
    assert author_only_ranker([]) == []
