import argparse
import json
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt

RANKERS = ["random", "label_only", "author_only", "triagepilot"]
RANKER_LABELS = {
    "random": "Random",
    "label_only": "Label-only",
    "author_only": "Author-only",
    "triagepilot": "TriagePilot",
}
RANKER_COLORS = {
    "random": "#a1a1aa",
    "label_only": "#f59e0b",
    "author_only": "#3b82f6",
    "triagepilot": "#10b981",
}


def load_snapshots(path: Path) -> list[dict]:
    with path.open() as f:
        return json.load(f)


def mean_ndcg(snapshots: list[dict], ranker: str) -> tuple[float, float]:
    vals = [s["metrics"][ranker]["ndcg@5"] for s in snapshots]
    mean = statistics.mean(vals)
    std = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return mean, std


def plot_ndcg_bars(
    k8s: list[dict], nextjs: list[dict], out_path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    x_positions = list(range(len(RANKERS)))
    bar_width = 0.38

    k8s_means = [mean_ndcg(k8s, r)[0] for r in RANKERS]
    k8s_stds = [mean_ndcg(k8s, r)[1] for r in RANKERS]
    nextjs_means = [mean_ndcg(nextjs, r)[0] for r in RANKERS]
    nextjs_stds = [mean_ndcg(nextjs, r)[1] for r in RANKERS]

    bars_k8s = ax.bar(
        [x - bar_width / 2 for x in x_positions],
        k8s_means,
        bar_width,
        yerr=k8s_stds,
        label="kubernetes/kubernetes",
        color="#0f172a",
        capsize=4,
    )
    bars_next = ax.bar(
        [x + bar_width / 2 for x in x_positions],
        nextjs_means,
        bar_width,
        yerr=nextjs_stds,
        label="vercel/next.js",
        color="#0ea5e9",
        capsize=4,
    )

    for bars, means in [(bars_k8s, k8s_means), (bars_next, nextjs_means)]:
        for bar, mean in zip(bars, means):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{mean:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#475569",
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels([RANKER_LABELS[r] for r in RANKERS])
    ax.set_ylabel("NDCG@5 (mean ± std)")
    ax.set_title("Ranker quality across snapshots (higher = better)")
    ax.set_ylim(0, 1.0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}", file=sys.stderr)


def plot_per_snapshot_scatter(
    k8s: list[dict], nextjs: list[dict], out_path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))

    def points(snapshots: list[dict]) -> tuple[list[float], list[float]]:
        x = [s["metrics"]["label_only"]["ndcg@5"] for s in snapshots]
        y = [s["metrics"]["triagepilot"]["ndcg@5"] for s in snapshots]
        return x, y

    if k8s:
        x, y = points(k8s)
        ax.scatter(x, y, s=70, color="#0f172a", alpha=0.85, label="kubernetes/kubernetes")
    if nextjs:
        x, y = points(nextjs)
        ax.scatter(x, y, s=70, color="#0ea5e9", alpha=0.85, label="vercel/next.js")

    ax.plot([0, 1], [0, 1], linestyle="--", color="#94a3b8", linewidth=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Label-only NDCG@5")
    ax.set_ylabel("TriagePilot NDCG@5")
    ax.set_title("Per-snapshot: TriagePilot vs label-only\n(above the diagonal = TriagePilot wins)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(linestyle="--", alpha=0.3)
    ax.legend(frameon=False, loc="lower right")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot eval results")
    parser.add_argument("--k8s", type=Path, required=True)
    parser.add_argument("--nextjs", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    k8s = load_snapshots(args.k8s) if args.k8s.exists() else []
    nextjs = load_snapshots(args.nextjs) if args.nextjs.exists() else []

    if not k8s and not nextjs:
        sys.exit("No snapshot data found at either path")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_ndcg_bars(k8s, nextjs, args.out_dir / "ndcg_by_ranker.png")
    plot_per_snapshot_scatter(k8s, nextjs, args.out_dir / "triagepilot_vs_label.png")


if __name__ == "__main__":
    main()
