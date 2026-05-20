from src.agents.synthesizer import Ranking, RankedPR
from src.telegram.bot import format_brief


def _ranked(
    *,
    pr_number: int,
    rank: int,
    ai_priority: str = "high",
    label_disagreement: bool = False,
    title: str | None = "Sample PR",
    url: str | None = None,
    ticket_priority_label: str | None = None,
) -> RankedPR:
    return RankedPR(
        pr_number=pr_number,
        rank=rank,
        reasoning="r",
        ai_priority=ai_priority,
        label_disagreement=label_disagreement,
        title=title,
        url=url,
        ticket_priority_label=ticket_priority_label,
    )


async def test_brief_includes_header_and_repo_count() -> None:
    ranking = Ranking(prs=[_ranked(pr_number=1, rank=1)])
    brief = await format_brief(ranking, "kubernetes/kubernetes", 27)
    assert "🌅 <b>Good morning.</b>" in brief
    assert "27 open PRs in <code>kubernetes/kubernetes</code>" in brief


async def test_brief_caps_at_top_five() -> None:
    ranking = Ranking(
        prs=[_ranked(pr_number=i, rank=i, title=f"PR title {i}") for i in range(1, 11)]
    )
    brief = await format_brief(ranking, "owner/repo", 10)
    for i in (1, 2, 3, 4, 5):
        assert f"<b>#{i}</b>" in brief
    for i in (6, 7, 8):
        assert f"<b>#{i}</b>" not in brief


async def test_brief_inserts_disagreement_warning_only_when_flagged() -> None:
    ranking = Ranking(
        prs=[
            _ranked(
                pr_number=1, rank=1, label_disagreement=True,
                ticket_priority_label="low", ai_priority="high",
            ),
            _ranked(pr_number=2, rank=2, label_disagreement=False),
        ]
    )
    brief = await format_brief(ranking, "owner/repo", 2)
    assert "Labeled low · AI says high" in brief
    assert brief.count("⚠") == 1


async def test_brief_falls_back_to_constructed_url_when_missing() -> None:
    ranking = Ranking(prs=[_ranked(pr_number=4242, rank=1, url=None)])
    brief = await format_brief(ranking, "kubernetes/kubernetes", 1)
    assert "https://github.com/kubernetes/kubernetes/pull/4242" in brief


async def test_brief_falls_back_to_pr_number_when_title_missing() -> None:
    ranking = Ranking(prs=[_ranked(pr_number=99, rank=1, title=None)])
    brief = await format_brief(ranking, "o/r", 1)
    assert "PR #99" in brief


async def test_brief_ends_with_full_hint() -> None:
    ranking = Ranking(prs=[_ranked(pr_number=1, rank=1)])
    brief = await format_brief(ranking, "o/r", 1)
    assert brief.strip().endswith("Reply /full for the complete queue.")
