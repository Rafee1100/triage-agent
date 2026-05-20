import html

from telegram import Bot

from src.agents.synthesizer import Ranking

TOP_N = 5


def _esc(text: str | None) -> str:
    if not text:
        return ""
    return html.escape(text, quote=False)


async def format_brief(ranking: Ranking, repo: str, total_prs: int) -> str:
    top = sorted(ranking.prs, key=lambda r: r.rank)[:TOP_N]
    lines: list[str] = [
        "🌅 <b>Good morning.</b>",
        f"You have {total_prs} open PRs in <code>{_esc(repo)}</code>. Top {len(top)} to review:",
        "",
    ]
    for pr in top:
        title = _esc(pr.title) or f"PR #{pr.pr_number}"
        url = pr.url or f"https://github.com/{repo}/pull/{pr.pr_number}"
        lines.append(f"⚡ <b>#{pr.rank}</b> — {title}")
        if pr.label_disagreement:
            stated = _esc(pr.ticket_priority_label) or "unknown"
            lines.append(f"   ⚠ Labeled {stated} · AI says {pr.ai_priority}")
        lines.append(f'   📎 <a href="{_esc(url)}">github.com/{_esc(repo)}/pull/{pr.pr_number}</a>')
        lines.append("")
    lines.append("Reply /full for the complete queue.")
    return "\n".join(lines)


async def send_morning_brief(
    chat_id: str,
    bot_token: str,
    ranking: Ranking,
    repo: str,
) -> None:
    text = await format_brief(ranking, repo, len(ranking.prs))
    bot = Bot(token=bot_token)
    async with bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
