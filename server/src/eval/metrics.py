import math

from scipy.stats import kendalltau as _kt

__all__ = ["kendall_tau", "ndcg_at_k"]


def ndcg_at_k(predicted: list[int], ground_truth: list[int], k: int = 5) -> float:
    if not predicted or not ground_truth or k <= 0:
        return 0.0

    n_truth = len(ground_truth)
    truth_position = {pr: i for i, pr in enumerate(ground_truth)}

    def relevance(pr_num: int) -> float:
        pos = truth_position.get(pr_num)
        if pos is None:
            return 0.0
        return float(n_truth - pos)

    dcg = sum(
        relevance(pr) / math.log2(i + 2)
        for i, pr in enumerate(predicted[:k])
    )
    idcg = sum(
        (n_truth - i) / math.log2(i + 2)
        for i in range(min(k, n_truth))
    )
    return dcg / idcg if idcg > 0 else 0.0


def kendall_tau(predicted: list[int], ground_truth: list[int]) -> float:
    common = set(predicted) & set(ground_truth)
    if len(common) < 2:
        return 0.0

    predicted_rank = {pr: i for i, pr in enumerate(predicted)}
    truth_rank = {pr: i for i, pr in enumerate(ground_truth)}

    p_ranks = [predicted_rank[pr] for pr in common]
    t_ranks = [truth_rank[pr] for pr in common]

    tau, _ = _kt(p_ranks, t_ranks)
    if math.isnan(tau):
        return 0.0
    return float(tau)
