"""
ARKHÉ Agent Boundary Defense Benchmark — Applied Statistical Evaluation Engine
==============================================================================
Provides robust, non-parametric statistical metrics:
- Wilson score confidence intervals for proportions (Precision, Recall, F1).
- Bootstrap re-sampling (2,000 iterations) for median and mean lead times (N_lead).
- Wilcoxon signed-rank paired test for ordinal lead time comparison.
- McNemar test for paired binary classification discordance.
- Explicit warnings on small sample sizes.
"""

import math
import random
from typing import List, Tuple, Dict, Any, Optional


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Computes Wilson score confidence interval for a binomial proportion.
    Ideal for small sample sizes or when proportion is near 0.0 or 1.0.
    """
    if total == 0:
        return (0.0, 0.0)

    # Standard normal quantile for confidence level (e.g. 1.95996 for 95%)
    z = 1.959964 if abs(confidence - 0.95) < 1e-4 else 1.644853
    p_hat = successes / total

    denominator = 1.0 + (z**2) / total
    centre = (p_hat + (z**2) / (2 * total)) / denominator
    spread = (z * math.sqrt((p_hat * (1.0 - p_hat) + (z**2) / (4 * total)) / total)) / denominator

    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return (round(lower, 4), round(upper, 4))


def bootstrap_ci(
    data: List[float],
    statistic_fn=lambda arr: sorted(arr)[len(arr) // 2],  # default median
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Computes non-parametric bootstrap confidence interval for a given statistic function.
    """
    if not data:
        return {"point_estimate": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n": 0, "warning": "Empty sample"}

    n = len(data)
    rng = random.Random(seed)
    point_est = statistic_fn(data)

    if n < 5:
        return {
            "point_estimate": round(point_est, 4),
            "ci_lower": round(min(data), 4),
            "ci_upper": round(max(data), 4),
            "n": n,
            "warning": f"Sample size (n={n}) is too small for asymptotic bootstrap stability."
        }

    estimates = []
    for _ in range(n_resamples):
        sample = [rng.choice(data) for _ in range(n)]
        estimates.append(statistic_fn(sample))

    estimates.sort()
    alpha = (1.0 - ci) / 2.0
    lower_idx = int(alpha * n_resamples)
    upper_idx = int((1.0 - alpha) * n_resamples) - 1

    ci_lower = estimates[max(0, lower_idx)]
    ci_upper = estimates[min(n_resamples - 1, upper_idx)]

    warning = None
    if n < 30:
        warning = f"Aviso de incerteza: Amostra piloto (n={n}) requer cautela ao inferir significância populacional."

    return {
        "point_estimate": round(point_est, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "n": n,
        "warning": warning
    }


def wilcoxon_signed_rank_test(x: List[float], y: List[float]) -> Dict[str, Any]:
    """
    Computes Wilcoxon signed-rank test for paired observations (x_i vs y_i).
    Used to test whether ARKHÉ anticipation is significantly greater than baseline.
    """
    if len(x) != len(y):
        raise ValueError("Paired samples must have identical lengths")

    diffs = [xi - yi for xi, yi in zip(x, y)]
    # Filter out zero differences
    non_zero_diffs = [d for d in diffs if d != 0]
    n_nonzero = len(non_zero_diffs)

    if n_nonzero < 5:
        return {
            "test": "Wilcoxon signed-rank",
            "w_stat": None,
            "p_value": None,
            "z_score": None,
            "effect_size_r": None,
            "n_pairs": len(x),
            "n_nonzero": n_nonzero,
            "warning": f"Insufficient non-zero pairs ({n_nonzero} < 5) to compute valid Wilcoxon asymptotic distribution."
        }

    # Rank absolute differences
    ranked = sorted(enumerate(non_zero_diffs), key=lambda item: abs(item[1]))
    ranks = [0.0] * n_nonzero

    # Handle ties with average ranks
    i = 0
    while i < n_nonzero:
        j = i
        while j < n_nonzero - 1 and abs(ranked[j + 1][1]) == abs(ranked[i][1]):
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1

    w_pos = sum(ranks[idx] for idx, (_, val) in enumerate(ranked) if val > 0)
    w_neg = sum(ranks[idx] for idx, (_, val) in enumerate(ranked) if val < 0)
    w_stat = min(w_pos, w_neg)

    # Normal approximation for W
    mean_w = n_nonzero * (n_nonzero + 1) / 4.0
    var_w = n_nonzero * (n_nonzero + 1) * (2 * n_nonzero + 1) / 24.0
    std_w = math.sqrt(var_w) if var_w > 0 else 1.0

    z = (w_pos - mean_w) / std_w

    # Two-tailed p-value from standard normal
    p_value = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))

    # Effect size r = z / sqrt(N)
    effect_size_r = z / math.sqrt(n_nonzero)

    return {
        "test": "Wilcoxon signed-rank (paired)",
        "w_stat": round(w_stat, 2),
        "w_pos": round(w_pos, 2),
        "w_neg": round(w_neg, 2),
        "z_score": round(z, 4),
        "p_value": round(p_value, 6),
        "effect_size_r": round(effect_size_r, 4),
        "is_significant_005": p_value < 0.05,
        "is_significant_001": p_value < 0.01,
        "n_nonzero": n_nonzero
    }


def mcnemar_test(contingency_table: List[List[int]]) -> Dict[str, Any]:
    """
    Computes McNemar test for paired binary classifications:
    Table format: [[both_correct, det1_correct_det2_wrong],
                   [det1_wrong_det2_correct, both_wrong]]
    """
    b = contingency_table[0][1]
    c = contingency_table[1][0]

    if (b + c) < 5:
        return {
            "test": "McNemar",
            "chi2": None,
            "p_value": None,
            "warning": f"Discordant pairs sum (b+c={b+c}) is too low for chi-square approximation."
        }

    # Edwards continuity correction
    chi2 = ((abs(b - c) - 1.0) ** 2) / (b + c)
    # p-value for 1 degree of freedom chi2
    p_value = 1.0 - math.erf(math.sqrt(chi2) / math.sqrt(2.0))

    return {
        "test": "McNemar (with continuity correction)",
        "discordant_b": b,
        "discordant_c": c,
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 6),
        "is_significant_005": p_value < 0.05
    }
