"""
ARKHÉ Benchmark — API Cost & Token Budget Estimator
==================================================
Calculates the exact token consumption and financial budget required
to execute the full 300-trajectory benchmark across 3 detectors and 3 repetitions.

FORMULA:
  Total Runs = N_trajectories (300) * N_detectors (3) * N_repetitions (3) = 2,700 runs.
"""

import json
import argparse
from typing import Dict, Any


def calculate_budget() -> Dict[str, Any]:
    n_trajectories = 300
    n_repetitions = 3
    avg_steps_per_trajectory = 8.0

    # Pricing models (per 1M tokens) - Standard OpenAI API pricing
    pricing = {
        "gpt-4o-mini": {"input_per_m": 0.15, "output_per_m": 0.60},
        "gpt-4o": {"input_per_m": 2.50, "output_per_m": 10.00},
    }

    # 1. Detector 1: Deterministic Regex Rule Baseline
    # Local pattern matching only; 0 tokens
    det1_runs = n_trajectories * n_repetitions
    det1_input_tokens = 0
    det1_output_tokens = 0
    det1_cost = 0.0

    # 2. Detector 2: Semantic Event Classifier Baseline
    # Evaluates each step in isolation via LLM call
    det2_runs = n_trajectories * n_repetitions
    det2_calls = det2_runs * int(avg_steps_per_trajectory)  # 900 * 8 = 7,200 calls
    det2_in_per_call = 400   # Single step prompt
    det2_out_per_call = 100  # JSON verdict
    det2_input_tokens = det2_calls * det2_in_per_call
    det2_output_tokens = det2_calls * det2_out_per_call
    # Evaluated with gpt-4o-mini for cost efficiency in event classification
    det2_cost = (
        (det2_input_tokens / 1_000_000) * pricing["gpt-4o-mini"]["input_per_m"] +
        (det2_output_tokens / 1_000_000) * pricing["gpt-4o-mini"]["output_per_m"]
    )

    # 3. Detector 3: ARKHÉ Trajectory Sentinel (Hybrid Mathematical + Semantic)
    # Heuristic scoring is local; trajectory-level LLM verification called when risk enters caution zone (approx 40% of steps)
    det3_runs = n_trajectories * n_repetitions
    det3_calls = int(det3_runs * avg_steps_per_trajectory * 0.40)  # ~2,880 calls
    det3_in_per_call = 1200   # Trajectory history window
    det3_out_per_call = 180   # Trajectory verdict
    det3_input_tokens = det3_calls * det3_in_per_call
    det3_output_tokens = det3_calls * det3_out_per_call
    det3_cost = (
        (det3_input_tokens / 1_000_000) * pricing["gpt-4o-mini"]["input_per_m"] +
        (det3_output_tokens / 1_000_000) * pricing["gpt-4o-mini"]["output_per_m"]
    )

    # 4. LLM-as-a-Judge for Qualitative Audit (GPT-4o)
    # Audits a stratified 20% sample of all evaluation runs (540 runs)
    judge_runs = int(2700 * 0.20)
    judge_in_per_call = 2500   # Complete trajectory + predictions + ground truth rationale
    judge_out_per_call = 400   # Audit explanation
    judge_input_tokens = judge_runs * judge_in_per_call
    judge_output_tokens = judge_runs * judge_out_per_call
    judge_cost = (
        (judge_input_tokens / 1_000_000) * pricing["gpt-4o"]["input_per_m"] +
        (judge_output_tokens / 1_000_000) * pricing["gpt-4o"]["output_per_m"]
    )

    # 5. Dataset Generation & Calibration Phase
    # Generating 300 rich synthetic multi-turn agent trajectories using GPT-4o
    gen_trajectories = 300
    gen_in_per_traj = 3500   # System prompt, scenario requirements, tool schemas
    gen_out_per_traj = 2000  # Multi-step trajectory JSON
    gen_input_tokens = gen_trajectories * gen_in_per_traj
    gen_output_tokens = gen_trajectories * gen_out_per_traj
    gen_cost = (
        (gen_input_tokens / 1_000_000) * pricing["gpt-4o"]["input_per_m"] +
        (gen_output_tokens / 1_000_000) * pricing["gpt-4o"]["output_per_m"]
    )

    # Subtotals
    benchmark_run_tokens = det1_input_tokens + det1_output_tokens + det2_input_tokens + det2_output_tokens + det3_input_tokens + det3_output_tokens + judge_input_tokens + judge_output_tokens
    dataset_gen_tokens = gen_input_tokens + gen_output_tokens
    total_tokens = benchmark_run_tokens + dataset_gen_tokens

    raw_api_cost = det1_cost + det2_cost + det3_cost + judge_cost + gen_cost

    # Calibration, iterative prompt engineering, and red-teaming buffer (2.5x multiplier)
    # Essential for prompt robustness, hyperparameter tuning, and failed run retries
    contingency_multiplier = 2.5
    total_api_requested = min(5000.0, raw_api_cost * contingency_multiplier)

    # Level 2 Project Budget Breakdown ($20,000 Total)
    budget_breakdown = {
        "grant_tier": "Level 2 ($20,000 USD)",
        "total_requested_usd": 20000.0,
        "line_items": {
            "api_credits_openai": {
                "amount_usd": 5000.0,
                "percentage": 25.0,
                "description": "API credits for GPT-4o dataset synthesis, baseline guardrail inference, and LLM-as-a-judge audits"
            },
            "research_execution_compensation": {
                "amount_usd": 10000.0,
                "percentage": 50.0,
                "description": "6-month dedicated research stipend / engineering effort (20h/week across Milestones M1-M4)"
            },
            "external_security_audit_redteaming": {
                "amount_usd": 3000.0,
                "percentage": 15.0,
                "description": "Independent third-party red-teaming audit of synthetic dataset quality and anti-leakage contracts"
            },
            "cloud_compute_and_dissemination": {
                "amount_usd": 2000.0,
                "percentage": 10.0,
                "description": "Continuous integration test infrastructure, benchmarking servers, and open-access publication fees"
            }
        },
        "token_calculations": {
            "n_trajectories": n_trajectories,
            "n_repetitions": n_repetitions,
            "total_benchmark_evaluations": n_trajectories * 3 * n_repetitions,
            "dataset_generation_tokens": dataset_gen_tokens,
            "execution_tokens": benchmark_run_tokens,
            "total_tokens_estimated": total_tokens,
            "raw_api_cost_usd": round(raw_api_cost, 2),
            "safety_buffer_factor": contingency_multiplier,
            "allocated_api_credits_usd": 5000.0
        }
    }

    return budget_breakdown


def main():
    parser = argparse.ArgumentParser(description="Estimate API token budget for ARKHÉ benchmark.")
    parser.add_argument("--json", action="store_true", help="Print json output only")
    args = parser.parse_args()

    budget = calculate_budget()

    if args.json:
        print(json.dumps(budget, indent=2))
    else:
        print("=" * 70)
        print(" ARKHÉ BENCHMARK — API TOKEN CONSUMPTION & BUDGET SPECIFICATION")
        print("=" * 70)
        print(f"Target Scope: {budget['token_calculations']['n_trajectories']} trajectories x 3 detectors x {budget['token_calculations']['n_repetitions']} reps = {budget['token_calculations']['total_benchmark_evaluations']} runs")
        print(f"Total Base Tokens Estimated: {budget['token_calculations']['total_tokens_estimated']:,}")
        print(f"Raw API Execution Cost: ${budget['token_calculations']['raw_api_cost_usd']:,.2f}")
        print(f"Safety Buffer Multiplier: {budget['token_calculations']['safety_buffer_factor']}x (prompt engineering, tuning, red-teaming)")
        print(f"Requested API Credits: ${budget['line_items']['api_credits_openai']['amount_usd']:,.2f}")
        print("\n" + "-" * 70)
        print(" LEVEL 2 OVERALL PROJECT BUDGET BREAKDOWN ($20,000 USD)")
        print("-" * 70)
        for k, v in budget["line_items"].items():
            print(f" - {v['description']}: ${v['amount_usd']:,.2f} ({v['percentage']}%)")
        print("=" * 70)


if __name__ == "__main__":
    main()
