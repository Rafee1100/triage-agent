from src.agents.critic import RankAdjustment, RankingCritique
from src.agents.synthesizer import Ranking, RankedPR
from src.pipeline import apply_critic_adjustments


def _ranking(numbers: list[int]) -> Ranking:
    return Ranking(
        prs=[
            RankedPR(
                pr_number=n,
                rank=i + 1,
                reasoning=f"r{n}",
                ai_priority="medium",
                label_disagreement=False,
            )
            for i, n in enumerate(numbers)
        ]
    )


def test_apply_no_adjustments_returns_input() -> None:
    ranking = _ranking([10, 20, 30])
    critique = RankingCritique(adjustments=[], overall_assessment="ok")
    out = apply_critic_adjustments(ranking, critique)
    assert [p.pr_number for p in out.prs] == [10, 20, 30]


def test_apply_swaps_pr_to_new_rank() -> None:
    ranking = _ranking([10, 20, 30, 40])
    critique = RankingCritique(
        adjustments=[
            RankAdjustment(pr_number=30, new_rank=1, reason="blast_radius=0.9")
        ],
        overall_assessment="ok",
    )
    out = apply_critic_adjustments(ranking, critique)
    assert [p.pr_number for p in out.prs] == [30, 10, 20, 40]
    assert [p.rank for p in out.prs] == [1, 2, 3, 4]


def test_apply_caps_at_three_adjustments() -> None:
    ranking = _ranking([1, 2, 3, 4, 5])
    critique = RankingCritique(
        adjustments=[
            RankAdjustment(pr_number=5, new_rank=1, reason="r"),
            RankAdjustment(pr_number=4, new_rank=2, reason="r"),
            RankAdjustment(pr_number=3, new_rank=3, reason="r"),
        ],
        overall_assessment="ok",
    )
    out = apply_critic_adjustments(ranking, critique)
    ranks = [p.rank for p in out.prs]
    numbers = [p.pr_number for p in out.prs]
    assert ranks == [1, 2, 3, 4, 5]
    assert sorted(numbers) == [1, 2, 3, 4, 5]


def test_apply_clamps_new_rank_within_bounds() -> None:
    ranking = _ranking([10, 20, 30])
    critique = RankingCritique(
        adjustments=[
            RankAdjustment(pr_number=30, new_rank=99, reason="r")
        ],
        overall_assessment="ok",
    )
    out = apply_critic_adjustments(ranking, critique)
    assert out.prs[-1].pr_number == 30
    assert [p.rank for p in out.prs] == [1, 2, 3]


def test_apply_ignores_unknown_pr_number() -> None:
    ranking = _ranking([10, 20])
    critique = RankingCritique(
        adjustments=[
            RankAdjustment(pr_number=999, new_rank=1, reason="r")
        ],
        overall_assessment="ok",
    )
    out = apply_critic_adjustments(ranking, critique)
    assert [p.pr_number for p in out.prs] == [10, 20]
