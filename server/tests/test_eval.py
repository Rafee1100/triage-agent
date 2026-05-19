from datetime import datetime, timezone

from src.eval.ground_truth import _first_action_within, _sort_by_action
from src.eval.snapshot import _earliest_review_at, _was_unreviewed_at


T0 = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
T_END = datetime(2026, 4, 15, 0, 0, 0, tzinfo=timezone.utc)
BEFORE = "2026-03-15T12:00:00+00:00"
DURING_EARLY = "2026-04-03T12:00:00+00:00"
DURING_LATE = "2026-04-10T12:00:00+00:00"
AFTER = "2026-05-01T12:00:00+00:00"


def test_earliest_review_returns_none_for_no_reviews() -> None:
    assert _earliest_review_at({"reviews": {"nodes": []}}) is None
    assert _earliest_review_at({}) is None


def test_earliest_review_picks_min_timestamp() -> None:
    node = {"reviews": {"nodes": [{"submittedAt": DURING_LATE}, {"submittedAt": DURING_EARLY}]}}
    assert _earliest_review_at(node) == datetime.fromisoformat(DURING_EARLY)


def test_was_unreviewed_at_true_when_no_reviews() -> None:
    assert _was_unreviewed_at({"reviews": {"nodes": []}}, T0) is True


def test_was_unreviewed_at_true_when_first_review_after_t0() -> None:
    node = {"reviews": {"nodes": [{"submittedAt": DURING_EARLY}]}}
    assert _was_unreviewed_at(node, T0) is True


def test_was_unreviewed_at_false_when_first_review_before_t0() -> None:
    node = {"reviews": {"nodes": [{"submittedAt": BEFORE}]}}
    assert _was_unreviewed_at(node, T0) is False


def test_first_action_within_returns_review_inside_window() -> None:
    pr = {"reviews": {"nodes": [{"submittedAt": DURING_EARLY}]}, "mergedAt": None}
    assert _first_action_within(pr, T0, T_END) == datetime.fromisoformat(DURING_EARLY)


def test_first_action_within_returns_merge_if_earlier_than_review() -> None:
    pr = {
        "reviews": {"nodes": [{"submittedAt": DURING_LATE}]},
        "mergedAt": DURING_EARLY,
    }
    assert _first_action_within(pr, T0, T_END) == datetime.fromisoformat(DURING_EARLY)


def test_first_action_within_ignores_events_outside_window() -> None:
    pr = {"reviews": {"nodes": [{"submittedAt": AFTER}]}, "mergedAt": BEFORE}
    assert _first_action_within(pr, T0, T_END) is None


def test_sort_by_action_orders_earliest_first_with_unreviewed_last() -> None:
    results = [
        (1, datetime.fromisoformat(DURING_LATE)),
        (2, None),
        (3, datetime.fromisoformat(DURING_EARLY)),
    ]
    assert _sort_by_action(results) == [3, 1, 2]


def test_sort_by_action_empty_returns_empty() -> None:
    assert _sort_by_action([]) == []
