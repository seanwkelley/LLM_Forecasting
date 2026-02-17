"""
Persona-Rewrite Experiment: 2x3 Factorial Design
==================================================

Factor 1: Context type (raw vs persona-rewritten)
Factor 2: Sharding (baseline, shard_everything, shard_initial_only)

6 conditions x 3 periods x 100 agents = 1,800 predictions + 3,000 rewrites (cached).

CLI flags:
  --test          Quick validation: 1 period, 2 conditions, N=5, 5 personas
  --skip-raw      Skip raw conditions (reuse existing results)
  --rewrite-only  Only generate rewrites, don't run predictions
  --n-rewrites N  Generate rewrites for first N personas only
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
import argparse
import random as random_module
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np

from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts_with_scenario import get_prompt_sections
from forecasting.action_ground_truth import load_ground_truth
from forecasting.simulation_data import get_state_before, get_events
from forecasting.information_sharding import create_information_distribution
from forecasting.sharding_strategies import apply_sharding_strategy
from forecasting.persona_generator import load_personas
from forecasting.persona_rewrite import (
    generate_all_rewrites,
    load_rewrite_cache,
    get_rewritten_sections,
    DEFAULT_CACHE_PATH,
    REWRITE_MODEL,
)
from forecasting.run_collapse_sharding_comparison import (
    create_historical_summary,
    calculate_brier_score,
    calculate_ensemble_statistics,
    load_collapse_ground_truth,
)


PREDICTION_MODEL = "deepseek/deepseek-v3.2"

SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in government stability forecasting.

Your task is to predict the probability of government collapse based on:
- Strategic context and background
- Historical developments
- Current military, economic, and political situation
- Recent events and actions

Apply rigorous analytical reasoning and USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""


def run_single_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fraction: float,
    agent_id: int,
    model: str = PREDICTION_MODEL
) -> Dict:
    """Run a single agent's collapse probability prediction."""
    forecaster = BaseLLMForecaster(model=model, temperature=1.0)

    prompt = apply_sharding_strategy(
        strategy=sharding_strategy,
        initial_scenario=initial_scenario,
        historical_summary=historical_summary,
        current_period_data=current_period_data,
        instructions=instructions,
        information_fraction=information_fraction,
        seed=agent_id
    )

    try:
        response_text, success = forecaster.call_llm(
            user_prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            response_format="json"
        )

        if not success or not response_text or response_text.strip() == "":
            return {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'api_error'}

        # Strip markdown fences
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        prob = result.get('probability', None)
        if prob is None:
            result['probability'] = 0.5
            result['_fallback'] = 'missing_probability_key'
        elif not (0.0 <= prob <= 1.0):
            result['probability'] = max(0.0, min(1.0, prob))
            result['_fallback'] = 'out_of_range'

        return result

    except json.JSONDecodeError:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': 'JSON parse error', '_fallback': 'json_error'}
    except Exception as e:
        return {'probability': 0.5, 'confidence': 'low', 'rationale': str(e), '_fallback': 'exception'}


def run_condition(
    period: int,
    condition_name: str,
    sharding_strategy: str,
    context_type: str,
    n_agents: int,
    ground_truth_actions: dict,
    collapse_ground_truth: float,
    rewrites_cache: Dict = None,
    personas: list = None,
    all_persona_ids: list = None,
    max_workers: int = 5,
    model: str = PREDICTION_MODEL
) -> Dict:
    """
    Run N agents for one condition/period.

    Args:
        period: Period number (1-3)
        condition_name: Human-readable condition name
        sharding_strategy: "none", "shard_everything", "shard_initial_only"
        context_type: "raw" or "persona"
        n_agents: Number of agents
        ground_truth_actions: From load_ground_truth()
        collapse_ground_truth: Ground truth collapse probability
        rewrites_cache: Loaded rewrite cache (required for persona conditions)
        personas: Full list of personas (required for persona conditions)
        all_persona_ids: Pre-selected persona IDs for this condition (required for persona)
        max_workers: Parallel workers
        model: Prediction model

    Returns:
        Result dict with statistics
    """
    print(f"\n  Condition: {condition_name} (context={context_type}, sharding={sharding_strategy})")

    # Get raw sections (needed for raw conditions and for instructions in all conditions)
    state_before = get_state_before(period)
    external_events = get_events(period)
    novaris_actions = ground_truth_actions[period]['major_power']['actions']
    tethys_actions = ground_truth_actions[period]['small_power']['actions']
    historical_summary = create_historical_summary(period, ground_truth_actions)

    raw_scenario, _, raw_current_data, instructions = get_prompt_sections(
        period=period,
        state_before=state_before,
        external_events=external_events,
        novaris_actions=novaris_actions,
        tethys_actions=tethys_actions,
        historical_summary=historical_summary
    )

    # Create information distribution
    info_fractions = create_information_distribution(n_agents)

    # Build per-agent sections
    agent_sections = []
    if context_type == "raw":
        # All agents get the same raw sections
        for i in range(n_agents):
            agent_sections.append((raw_scenario, historical_summary, raw_current_data))
    elif context_type == "persona":
        # Each agent gets their persona's rewritten sections
        for i in range(n_agents):
            pid = all_persona_ids[i]
            scenario_rw, history_rw, data_rw = get_rewritten_sections(pid, period, rewrites_cache)
            # Fallback to raw if rewrite is empty
            if not scenario_rw.strip():
                scenario_rw = raw_scenario
            if not data_rw.strip():
                data_rw = raw_current_data
            if period > 1 and not history_rw.strip():
                history_rw = historical_summary
            agent_sections.append((scenario_rw, history_rw, data_rw))
    else:
        raise ValueError(f"Unknown context_type: {context_type}")

    # Run predictions in parallel
    start_time = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(n_agents):
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

            scenario_i, history_i, data_i = agent_sections[i]
            future = executor.submit(
                run_single_prediction,
                scenario_i,
                history_i,
                data_i,
                instructions,
                sharding_strategy,
                info_fractions[i],
                i,
                model
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'future_exception'})

    duration = time.time() - start_time

    # Track fallbacks
    fallback_count = sum(1 for pred in results if '_fallback' in pred)
    fallback_types = {}
    for pred in results:
        if '_fallback' in pred:
            ft = pred['_fallback']
            fallback_types[ft] = fallback_types.get(ft, 0) + 1

    # Calculate statistics
    probabilities = [pred.get('probability', 0.5) for pred in results]
    stats = calculate_ensemble_statistics(probabilities, collapse_ground_truth)

    print(f"    Completed in {duration:.1f}s")
    print(f"    Ensemble: {stats['ensemble_probability']:.3f} (truth: {collapse_ground_truth:.3f})")
    print(f"    Brier: {stats['ensemble_brier_score']:.4f}")
    print(f"    Fallbacks: {fallback_count}/{n_agents}", end="")
    if fallback_types:
        print(f" ({fallback_types})", end="")
    print()

    return {
        'condition': condition_name,
        'context_type': context_type,
        'sharding_strategy': sharding_strategy,
        'period': period,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'statistics': stats,
        'fallback_count': fallback_count,
        'fallback_types': fallback_types,
        'persona_ids': all_persona_ids if context_type == "persona" else None
    }


def main():
    parser = argparse.ArgumentParser(description="Persona-Rewrite 2x3 Factorial Experiment")
    parser.add_argument("--test", action="store_true", help="Quick validation: 1 period, 2 conditions, N=5")
    parser.add_argument("--skip-raw", action="store_true", help="Skip raw conditions (reuse existing results)")
    parser.add_argument("--rewrite-only", action="store_true", help="Only generate rewrites, don't run predictions")
    parser.add_argument("--n-rewrites", type=int, default=None, help="Generate rewrites for first N personas only")
    args = parser.parse_args()

    # Configuration
    if args.test:
        n_agents = 5
        periods = [1]
        n_personas_for_rewrites = 5
    else:
        n_agents = 100
        periods = list(range(1, 11))  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        n_personas_for_rewrites = args.n_rewrites  # None means all 500

    output_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/persona_rewrite_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PERSONA-REWRITE EXPERIMENT: 2x3 Factorial Design")
    print("=" * 70)
    print(f"Periods: {periods}")
    print(f"Agents per condition: {n_agents}")
    print(f"Prediction model: {PREDICTION_MODEL}")
    print(f"Rewrite model: {REWRITE_MODEL}")
    if args.test:
        print("[TEST MODE]")
    if args.skip_raw:
        print("[SKIPPING RAW CONDITIONS]")
    if args.rewrite_only:
        print("[REWRITE-ONLY MODE]")
    print("=" * 70)

    # ===== PHASE 1: Load data =====
    print("\nPhase 1: Loading data...")
    ground_truth_actions = load_ground_truth()
    collapse_ground_truth_all = load_collapse_ground_truth()
    personas = load_personas()

    if n_personas_for_rewrites is not None:
        personas_for_rewrite = personas[:n_personas_for_rewrites]
        print(f"  Using first {n_personas_for_rewrites} personas for rewrites")
    else:
        personas_for_rewrite = personas
        print(f"  Using all {len(personas)} personas for rewrites")

    # ===== PHASE 2: Generate/load rewrites =====
    print("\nPhase 2: Generating/loading persona rewrites...")
    rewrites_cache = generate_all_rewrites(
        personas=personas_for_rewrite,
        periods=periods,
        model=REWRITE_MODEL,
        cache_path=DEFAULT_CACHE_PATH,
        max_workers=5
    )

    if args.rewrite_only:
        print(f"\n[OK] Rewrite-only mode complete. Cache saved to: {DEFAULT_CACHE_PATH}")
        return

    # ===== PHASE 3: Define conditions =====
    # 2x3 factorial: context_type x sharding_strategy
    all_conditions = [
        ("raw_baseline",            "raw",     "none"),
        ("raw_shard_everything",    "raw",     "shard_everything"),
        ("raw_shard_initial_only",  "raw",     "shard_initial_only"),
        ("persona_baseline",            "persona", "none"),
        ("persona_shard_everything",    "persona", "shard_everything"),
        ("persona_shard_initial_only",  "persona", "shard_initial_only"),
    ]

    if args.test:
        # Only raw baseline + persona baseline for quick test
        all_conditions = [
            ("raw_baseline",     "raw",     "none"),
            ("persona_baseline", "persona", "none"),
        ]

    if args.skip_raw:
        all_conditions = [c for c in all_conditions if c[1] != "raw"]

    # Pre-select personas for persona conditions (deterministic per condition/period)
    # Use all available persona IDs from the cache
    available_persona_ids = list(rewrites_cache.get("rewrites", {}).keys())
    if len(available_persona_ids) < n_agents:
        print(f"[WARNING] Only {len(available_persona_ids)} personas in cache, need {n_agents}. Using available.")
        n_agents_persona = len(available_persona_ids)
    else:
        n_agents_persona = n_agents

    # ===== PHASE 4: Run experiment =====
    print(f"\nPhase 3: Running {len(all_conditions)} conditions x {len(periods)} periods...")
    all_results = []

    for period in periods:
        print(f"\n{'='*70}")
        print(f"PERIOD {period}")
        print(f"{'='*70}")

        collapse_truth = collapse_ground_truth_all[period]
        print(f"  Ground truth: {collapse_truth:.3f}")

        for cond_name, context_type, strategy in all_conditions:
            # Determine persona selection for this condition/period
            persona_ids = None
            actual_n_agents = n_agents

            if context_type == "persona":
                actual_n_agents = n_agents_persona
                # Deterministic persona sampling per condition+period
                seed = hash(f"{cond_name}_{period}") % (2**31)
                rng = random_module.Random(seed)
                persona_ids = rng.sample(available_persona_ids, actual_n_agents)

            try:
                result = run_condition(
                    period=period,
                    condition_name=cond_name,
                    sharding_strategy=strategy,
                    context_type=context_type,
                    n_agents=actual_n_agents,
                    ground_truth_actions=ground_truth_actions,
                    collapse_ground_truth=collapse_truth,
                    rewrites_cache=rewrites_cache,
                    personas=personas,
                    all_persona_ids=persona_ids,
                    max_workers=5,
                    model=PREDICTION_MODEL
                )
                all_results.append(result)
            except Exception as e:
                print(f"\n[ERROR] {cond_name} failed: {e}")
                import traceback
                traceback.print_exc()

    # ===== PHASE 5: Summary =====
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")

    header = f"{'Period':<8} {'Condition':<30} {'Context':<8} {'Truth':<8} {'Ensemble':<10} {'Brier':<10} {'Fallbacks':<10}"
    print(f"\n{header}")
    print("-" * len(header))

    for result in all_results:
        p = result['period']
        cond = result['condition']
        ctx = result['context_type']
        truth = result['statistics']['ground_truth']
        ensemble = result['statistics']['ensemble_probability']
        brier = result['statistics']['ensemble_brier_score']
        fallbacks = result['fallback_count']
        print(f"{p:<8} {cond:<30} {ctx:<8} {truth:<8.3f} {ensemble:<10.3f} {brier:<10.4f} {fallbacks:<10}")

    # ===== Average by context type =====
    print(f"\n{'='*70}")
    print("MAIN EFFECT: Context Type (raw vs persona)")
    print(f"{'='*70}")

    for ctx in ["raw", "persona"]:
        ctx_results = [r for r in all_results if r['context_type'] == ctx]
        if ctx_results:
            avg_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in ctx_results])
            avg_ensemble = np.mean([r['statistics']['ensemble_probability'] for r in ctx_results])
            total_fallbacks = sum(r['fallback_count'] for r in ctx_results)
            print(f"  {ctx:<10} Avg Brier: {avg_brier:.4f}  Avg Ensemble: {avg_ensemble:.3f}  Fallbacks: {total_fallbacks}")

    # ===== Average by sharding strategy =====
    print(f"\n{'='*70}")
    print("MAIN EFFECT: Sharding Strategy")
    print(f"{'='*70}")

    for strategy in ["none", "shard_everything", "shard_initial_only"]:
        strat_results = [r for r in all_results if r['sharding_strategy'] == strategy]
        if strat_results:
            avg_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in strat_results])
            print(f"  {strategy:<20} Avg Brier: {avg_brier:.4f}")

    # ===== Interaction: persona vs raw within each sharding strategy =====
    print(f"\n{'='*70}")
    print("INTERACTION: Context x Sharding")
    print(f"{'='*70}")

    for strategy in ["none", "shard_everything", "shard_initial_only"]:
        raw_results = [r for r in all_results if r['context_type'] == "raw" and r['sharding_strategy'] == strategy]
        persona_results = [r for r in all_results if r['context_type'] == "persona" and r['sharding_strategy'] == strategy]
        if raw_results and persona_results:
            raw_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in raw_results])
            persona_brier = np.mean([r['statistics']['ensemble_brier_score'] for r in persona_results])
            diff = persona_brier - raw_brier
            direction = "BETTER" if diff < 0 else "WORSE"
            print(f"  {strategy:<20} Raw: {raw_brier:.4f}  Persona: {persona_brier:.4f}  Diff: {diff:+.4f} ({direction})")

    # ===== Statistical comparison (paired by period x sharding) =====
    if not args.skip_raw and len(all_results) >= 6:
        print(f"\n{'='*70}")
        print("STATISTICAL COMPARISON: Persona vs Raw (paired)")
        print(f"{'='*70}")

        raw_briers = []
        persona_briers = []

        for strategy in ["none", "shard_everything", "shard_initial_only"]:
            for period in periods:
                raw_r = [r for r in all_results
                         if r['context_type'] == "raw" and r['sharding_strategy'] == strategy and r['period'] == period]
                persona_r = [r for r in all_results
                             if r['context_type'] == "persona" and r['sharding_strategy'] == strategy and r['period'] == period]
                if raw_r and persona_r:
                    raw_briers.append(raw_r[0]['statistics']['ensemble_brier_score'])
                    persona_briers.append(persona_r[0]['statistics']['ensemble_brier_score'])

        if len(raw_briers) >= 2:
            from scipy import stats
            raw_arr = np.array(raw_briers)
            persona_arr = np.array(persona_briers)
            diff_arr = persona_arr - raw_arr

            t_stat, p_value = stats.ttest_rel(persona_arr, raw_arr)
            cohens_d = np.mean(diff_arr) / np.std(diff_arr, ddof=1) if np.std(diff_arr, ddof=1) > 0 else 0

            print(f"  N pairs: {len(raw_briers)}")
            print(f"  Raw mean Brier:     {np.mean(raw_arr):.4f}")
            print(f"  Persona mean Brier: {np.mean(persona_arr):.4f}")
            print(f"  Mean difference:    {np.mean(diff_arr):+.4f}")
            print(f"  Paired t-test:      t={t_stat:.3f}, p={p_value:.4f}")
            print(f"  Cohen's d:          {cohens_d:.3f}")
            print(f"  Directional consistency: {sum(d < 0 for d in diff_arr)}/{len(diff_arr)} persona better")
        else:
            print("  Insufficient pairs for statistical test")

    # ===== Save results =====
    # Convert persona_ids to serializable format
    serializable_results = []
    for r in all_results:
        r_copy = dict(r)
        if r_copy.get('persona_ids') is not None:
            r_copy['persona_ids'] = list(r_copy['persona_ids'])
        serializable_results.append(r_copy)

    summary_file = output_dir / "experiment_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'experiment': 'persona_rewrite_2x3_factorial',
            'periods': periods,
            'n_agents': n_agents,
            'prediction_model': PREDICTION_MODEL,
            'rewrite_model': REWRITE_MODEL,
            'temperature': 1.0,
            'test_mode': args.test,
            'conditions': [c[0] for c in all_conditions],
            'results': serializable_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n{'='*70}")
    print(f"EXPERIMENT COMPLETE")
    print(f"Results saved: {summary_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
