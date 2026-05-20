import argparse
import asyncio
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.eval import (
    actual_review_order,
    author_only_ranker,
    kendall_tau,
    label_only_ranker,
    ndcg_at_k,
    random_ranker,
    reconstruct_open_prs_at,
)
from src.features.extractor import (
    compute_dependency_depths,
    detect_cross_pr_references,
    extract,
)
from src.github import GitHubClient
from src.github.models import AuthorProfile, PRContext
from src.pipeline import rank_prs

RANKERS = ["random", "label_only", "author_only", "triagepilot"]
MIN_SNAPSHOT_SIZE = 5
NDCG_K = 5


async def _build_features(
    gh: GitHubClient, owner: str, name: str, prs: list[PRContext]
) -> list:
    files_tasks = [gh.fetch_pr_files(owner, name, pr.number) for pr in prs]
    author_logins = sorted({pr.author.login for pr in prs if pr.author})
    author_tasks = [
        gh.fetch_author_history(owner, name, login) for login in author_logins
    ]
    files_per_pr, author_profiles = await asyncio.gather(
        asyncio.gather(*files_tasks),
        asyncio.gather(*author_tasks),
    )
    profile_lookup = {p.login: p for p in author_profiles}

    cross_refs = detect_cross_pr_references(prs)
    depths = compute_dependency_depths(cross_refs)

    features = []
    for pr, files in zip(prs, files_per_pr):
        login = pr.author.login if pr.author else ""
        author = profile_lookup.get(login) or AuthorProfile(
            login=login or "(ghost)",
            merged_pr_count_in_repo=0,
            revert_rate=0.0,
            avg_review_comments_per_pr=0.0,
        )
        features.append(
            extract(
                pr,
                author,
                files,
                cross_pr_references=cross_refs,
                cross_pr_depths=depths,
            )
        )
    return features


async def evaluate_snapshot(
    gh: GitHubClient,
    owner: str,
    name: str,
    t0: datetime,
    window_days: int,
    limit: int,
) -> dict | None:
    prs = await reconstruct_open_prs_at(gh, owner, name, t0, limit=limit)
    if len(prs) < MIN_SNAPSHOT_SIZE:
        return None

    pr_numbers = [pr.number for pr in prs]
    truth_order = await actual_review_order(
        gh, owner, name, pr_numbers, t0, window_days=window_days
    )

    features = await _build_features(gh, owner, name, prs)

    predictions = {
        "random": random_ranker(features),
        "label_only": label_only_ranker(features),
        "author_only": author_only_ranker(features),
    }

    tp_ranking = await rank_prs(gh=gh, owner=owner, name=name, prs=prs)
    predictions["triagepilot"] = [
        r.pr_number for r in sorted(tp_ranking.prs, key=lambda r: r.rank)
    ]

    metrics = {
        ranker: {
            "ndcg@5": ndcg_at_k(pred, truth_order, k=NDCG_K),
            "kendall_tau": kendall_tau(pred, truth_order),
        }
        for ranker, pred in predictions.items()
    }

    return {
        "t0": t0.isoformat(),
        "n_prs": len(prs),
        "ground_truth": truth_order,
        "predictions": predictions,
        "metrics": metrics,
    }


def evenly_spaced_timestamps(n: int, lookback_days: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=lookback_days)
    if n <= 1:
        return [start + (now - start) / 2]
    step = (now - start) / (n + 1)
    return [start + step * (i + 1) for i in range(n)]


def aggregate(results: list[dict]) -> dict[str, dict[str, float]]:
    out = {}
    for ranker in RANKERS:
        ndcg_vals = [r["metrics"][ranker]["ndcg@5"] for r in results]
        tau_vals = [r["metrics"][ranker]["kendall_tau"] for r in results]
        out[ranker] = {
            "ndcg_mean": statistics.mean(ndcg_vals),
            "ndcg_std": statistics.stdev(ndcg_vals) if len(ndcg_vals) > 1 else 0.0,
            "tau_mean": statistics.mean(tau_vals),
            "tau_std": statistics.stdev(tau_vals) if len(tau_vals) > 1 else 0.0,
        }
    return out


def format_markdown_table(aggregates: dict[str, dict[str, float]]) -> str:
    lines = [
        f"| Ranker | NDCG@{NDCG_K} (mean ± std) | Kendall tau (mean ± std) |",
        "|---|---|---|",
    ]
    for ranker in RANKERS:
        a = aggregates[ranker]
        lines.append(
            f"| {ranker} | {a['ndcg_mean']:.3f} ± {a['ndcg_std']:.3f} "
            f"| {a['tau_mean']:.3f} ± {a['tau_std']:.3f} |"
        )
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="TriagePilot retrospective replay eval")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--snapshots", type=int, default=8)
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument(
        "--out", type=Path, default=Path("data/eval_results.json"),
        help="JSON output path",
    )
    parser.add_argument("--limit", type=int, default=30, help="Max PRs per snapshot")
    args = parser.parse_args()

    if "/" not in args.repo:
        sys.exit("--repo must be owner/name")
    owner, name = args.repo.split("/", 1)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN not set")

    timestamps = evenly_spaced_timestamps(args.snapshots, args.lookback_days)

    results: list[dict] = []
    async with GitHubClient(token) as gh:
        for i, t0 in enumerate(timestamps, 1):
            print(
                f"\n[{i}/{len(timestamps)}] snapshot at t0={t0.isoformat()[:10]}",
                file=sys.stderr,
            )
            try:
                result = await evaluate_snapshot(
                    gh, owner, name, t0, args.window_days, args.limit
                )
            except Exception as exc:
                print(f"  error: {exc}", file=sys.stderr)
                continue
            if result is None:
                print(f"  skipped (fewer than {MIN_SNAPSHOT_SIZE} PRs)", file=sys.stderr)
                continue
            results.append(result)
            for ranker in RANKERS:
                m = result["metrics"][ranker]
                print(
                    f"  {ranker:14s}  NDCG@{NDCG_K}={m['ndcg@5']:.3f}  "
                    f"tau={m['kendall_tau']:+.3f}",
                    file=sys.stderr,
                )

    if not results:
        sys.exit("No valid snapshots collected — repo too small or lookback too short")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {len(results)} snapshot(s) to {args.out}", file=sys.stderr)

    print()
    print(f"# Eval results — {args.repo} ({len(results)} snapshots, "
          f"{args.window_days}-day window)")
    print()
    print(format_markdown_table(aggregate(results)))


if __name__ == "__main__":
    asyncio.run(main())
