import random

from src.features.extractor import PRFeatures

__all__ = ["author_only_ranker", "label_only_ranker", "random_ranker"]

_PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


def random_ranker(prs: list[PRFeatures], seed: int = 42) -> list[int]:
    numbers = [pr.pr_number for pr in prs]
    rng = random.Random(seed)
    rng.shuffle(numbers)
    return numbers


def label_only_ranker(prs: list[PRFeatures]) -> list[int]:
    def key(pr: PRFeatures) -> tuple[int, float]:
        priority = _PRIORITY_RANK.get((pr.ticket_priority_label or "").lower(), 0)
        return (-priority, -pr.pr_age_days)

    return [pr.pr_number for pr in sorted(prs, key=key)]


def author_only_ranker(prs: list[PRFeatures]) -> list[int]:
    def key(pr: PRFeatures) -> tuple[int, float]:
        return (-pr.author_merged_pr_count, -pr.pr_age_days)

    return [pr.pr_number for pr in sorted(prs, key=key)]
