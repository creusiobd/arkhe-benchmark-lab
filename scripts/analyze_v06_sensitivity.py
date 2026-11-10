"""Prospective exact-power sensitivity analysis for ARKHÉ v0.6 McNemar testing."""

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import numpy as np
import yaml
from scipy.stats import binom

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from contracts.preregistration import V06Preregistration


@lru_cache(maxsize=None)
def positive_rejection_boundary(discordant_pairs: int, alpha: float) -> int | None:
    """Return the first positive-direction count rejected by exact two-sided McNemar."""
    for arkhe_wins in range(discordant_pairs // 2 + 1, discordant_pairs + 1):
        tail = binom.cdf(discordant_pairs - arkhe_wins, discordant_pairs, 0.5)
        if min(1.0, 2.0 * tail) <= alpha:
            return arkhe_wins
    return None


def exact_mcnemar_power(
    sample_size: int,
    effect_difference: float,
    discordance_rate: float,
    alpha: float = 0.05,
) -> float:
    """Compute unconditional power over the random number of discordant pairs."""
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    if not 0.0 < effect_difference <= discordance_rate <= 1.0:
        raise ValueError(
            "require 0 < effect_difference <= discordance_rate <= 1"
        )
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")

    arkhe_win_rate = (discordance_rate + effect_difference) / 2.0
    conditional_win_probability = arkhe_win_rate / discordance_rate
    discordant_pairs = np.arange(1, sample_size + 1)
    boundaries = np.array(
        [
            positive_rejection_boundary(int(pair_count), alpha) or 0
            for pair_count in discordant_pairs
        ]
    )
    valid = boundaries > 0
    probability_of_pair_count = binom.pmf(
        discordant_pairs[valid], sample_size, discordance_rate
    )
    probability_of_rejection = binom.sf(
        boundaries[valid] - 1,
        discordant_pairs[valid],
        conditional_win_probability,
    )
    return float(np.sum(probability_of_pair_count * probability_of_rejection))


def minimum_sample_size(
    effect_difference: float,
    discordance_rate: float,
    target_power: float,
    alpha: float = 0.05,
    maximum_sample_size: int = 2_000,
) -> int:
    """Return the first integer sample size meeting the target exact power."""
    if not 0.0 < target_power < 1.0:
        raise ValueError("target_power must be in (0, 1)")
    for sample_size in range(2, maximum_sample_size + 1):
        if (
            exact_mcnemar_power(
                sample_size, effect_difference, discordance_rate, alpha
            )
            >= target_power
        ):
            return sample_size
    raise ValueError("target power was not reached within maximum_sample_size")


def build_report(protocol: V06Preregistration) -> Dict[str, object]:
    """Build a deterministic, pre-data sensitivity report from the protocol."""
    sample_size = protocol.population.total_trajectories
    effect_difference = (
        protocol.primary_hypothesis.minimum_effect_percentage_points / 100.0
    )
    alpha = protocol.primary_hypothesis.alpha
    target_power = protocol.statistics.target_power
    scenarios: List[Dict[str, object]] = []

    for discordance_rate in protocol.statistics.sensitivity_discordance_rates:
        power = exact_mcnemar_power(
            sample_size, effect_difference, discordance_rate, alpha
        )
        scenarios.append(
            {
                "discordance_rate": discordance_rate,
                "arkhe_only_correct_rate": (discordance_rate + effect_difference)
                / 2.0,
                "comparator_only_correct_rate": (
                    discordance_rate - effect_difference
                )
                / 2.0,
                "power": power,
                "minimum_n_for_target_power": minimum_sample_size(
                    effect_difference,
                    discordance_rate,
                    target_power,
                    alpha,
                ),
            }
        )

    design_scenario = next(
        scenario
        for scenario in scenarios
        if scenario["discordance_rate"]
        == protocol.statistics.design_discordance_rate
    )
    return {
        "protocol_id": protocol.protocol_id,
        "protocol_version": protocol.version,
        "method": protocol.statistics.power_method,
        "sample_size": sample_size,
        "minimum_effect_percentage_points": (
            protocol.primary_hypothesis.minimum_effect_percentage_points
        ),
        "alpha": alpha,
        "target_power": target_power,
        "design_discordance_rate": (
            protocol.statistics.design_discordance_rate
        ),
        "design_power": design_scenario["power"],
        "design_adequate": design_scenario["power"] >= target_power,
        "scenarios": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", default="configs/evaluation_protocol_v0.6.yaml")
    args = parser.parse_args()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = BASE_DIR / protocol_path
    protocol = V06Preregistration.model_validate(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    )
    print(json.dumps(build_report(protocol), indent=2))


if __name__ == "__main__":
    main()
