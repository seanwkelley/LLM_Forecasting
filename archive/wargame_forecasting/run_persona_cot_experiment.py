"""
Persona + Chain-of-Thought Bridging Experiment
===============================================

Tests whether bridging instructions that connect persona attributes to each
CoT reasoning step can produce meaningful prediction diversity.

4 conditions (2x2 factorial):
  - generic_baseline:  Generic system prompt, full info, generic CoT
  - persona_baseline:  Persona system prompt, full info, persona-bridged CoT
  - generic_shard:     Generic system prompt, sharded info, generic CoT
  - persona_shard:     Persona system prompt, sharded info, persona-bridged CoT

Usage:
    python -u forecasting/run_persona_cot_experiment.py --test
    python -u forecasting/run_persona_cot_experiment.py --n-scenarios 50 --n-agents 10
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
import random
import argparse
import pandas as pd
import numpy as np
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts_with_scenario import INITIAL_SCENARIO
from forecasting.information_sharding import create_information_distribution
from forecasting.sharding_strategies import apply_sharding_strategy
from forecasting.persona_simplified import SimplifiedProfile, load_simplified_personas

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
PREDICTION_MODEL = "deepseek/deepseek-v3.2"

# ---------------------------------------------------------------------------
# Scenario events (loaded once at import)
# ---------------------------------------------------------------------------
_EVENTS_FILE = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario/scenario_events.json")
_SCENARIO_EVENTS: Dict = {}
if _EVENTS_FILE.exists():
    with open(_EVENTS_FILE, 'r') as f:
        _SCENARIO_EVENTS = json.load(f)
    print(f"Loaded events for {len(_SCENARIO_EVENTS)} scenarios")

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_GENERIC = """You are an expert geopolitical analyst specializing in government stability forecasting.

Your task is to predict the probability of government collapse based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and actions

Apply rigorous analytical reasoning and USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

SYSTEM_PROMPT_PERSONA_TEMPLATE = """{persona_description}

You are participating in a geopolitical forecasting exercise. Your task is to predict the probability of government collapse based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and actions

Apply your professional expertise and analytical perspective. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

# ---------------------------------------------------------------------------
# CoT instructions
# ---------------------------------------------------------------------------
GENERIC_COT_INSTRUCTIONS = """
Think step-by-step:
1. Assess Tethys's current military/territorial position
2. Evaluate economic sustainability and internal stability
3. Consider external support and diplomatic situation
4. Analyze crisis level and momentum
5. Estimate overall collapse probability"""

PERSONA_COT_INSTRUCTIONS_TEMPLATE = """
ANALYTICAL APPROACH:
You are analyzing this scenario through the lens of your professional background
and expertise. At each reasoning step below, apply your specific knowledge and
strategic orientation. Where your expertise is strongest, provide deeper analysis.
Where it is limited, acknowledge uncertainty. Let your risk tolerance calibrate
how much weight you give to threatening vs. stabilizing indicators.

Think step-by-step:
1. Assess Tethys's current military/territorial position
   - Apply your military expertise to gauge the significance of territorial and force balance data
2. Evaluate economic sustainability and internal stability
   - Apply your economic expertise to assess GDP trajectories and sanctions impact
3. Consider external support and diplomatic situation
   - Apply your geopolitical expertise to evaluate alliance dynamics and diplomatic momentum
4. Analyze crisis level and momentum
   - As a {strategic_orientation} analyst, weigh escalatory vs. de-escalatory signals accordingly
5. Estimate overall collapse probability
   - Calibrate your final estimate consistent with your risk tolerance: higher risk tolerance means more willingness to deviate from base-rate estimates when your analysis supports it"""


# ===================================================================
# Prompt builders
# ===================================================================

def build_persona_system_prompt(persona: SimplifiedProfile) -> str:
    """Build a system prompt embedding the persona description."""
    return SYSTEM_PROMPT_PERSONA_TEMPLATE.format(
        persona_description=persona.to_natural_language()
    )


def build_instructions(condition_type: str, persona: Optional[SimplifiedProfile] = None) -> str:
    """
    Build the full instructions block (task framing + CoT + output format).

    condition_type: 'generic' or 'persona'
    """
    if condition_type == "persona" and persona is not None:
        cot = PERSONA_COT_INSTRUCTIONS_TEMPLATE.format(
            strategic_orientation=persona.strategic_orientation
        )
    else:
        cot = GENERIC_COT_INSTRUCTIONS

    instructions = f"""
{'='*80}
YOUR FORECASTING TASK
{'='*80}

Forecast the probability that Tethys's government will collapse or be removed
from power by the end of Period 1.

Government collapse includes:
- Military defeat leading to regime change
- Internal coup or revolution
- Economic collapse forcing government resignation
- Loss of governing capacity due to territorial loss
- Capitulation or forced settlement removing current leadership

CRITICAL INSTRUCTIONS:
- Output a probability between 0.0 and 1.0 (not a percentage)
- USE THE FULL PROBABILITY RANGE - don't cluster around 0.5
- Be calibrated: 0.2 means 20% chance, 0.8 means 80% chance
- Consider ALL factors: military, economic, political, international
{cot}

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key factors driving your probability estimate"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Use the FULL range 0.0 to 1.0 based on the actual situation - don't default to middle values.
"""
    return instructions


def create_scenario_prompt(scenario_params: pd.Series) -> Tuple[str, str, str]:
    """
    Create prompt sections for a single scenario.

    Returns:
        (initial_scenario, historical_summary, current_period_data)
        Instructions are built separately via build_instructions().
    """
    initial_scenario = INITIAL_SCENARIO
    historical_summary = ""

    # Build events section from actual scenario data
    scenario_id = scenario_params['scenario_id']
    events_data = _SCENARIO_EVENTS.get(scenario_id, {})

    events_text = ""
    external_events = events_data.get('external_events', [])
    if external_events:
        for i, evt in enumerate(external_events, 1):
            evt_type = evt.get('type', 'unknown').replace('_', ' ').title()
            evt_name = evt.get('name', '')
            evt_desc = evt.get('description', '')
            events_text += f"  {i}. [{evt_type}] {evt_name}: {evt_desc}\n"
    else:
        events_text = "  (No external events recorded this period)\n"

    ext_actor_text = ""
    ext_actions = events_data.get('external_actor_actions', [])
    if ext_actions:
        for ea in ext_actions:
            faction = ea.get('faction', 'unknown').replace('_', ' ').title()
            action = ea.get('action', 'unknown').replace('_', ' ')
            ext_actor_text += f"  - {faction}: {action}\n"
    else:
        ext_actor_text = "  (No external actor actions recorded)\n"

    current_period_data = f"""
{'='*80}
PERIOD 1 SITUATION UPDATE
{'='*80}

CURRENT STATE:
- Tethys Territory Remaining: {(1 - scenario_params['territory_controlled']) * 100:.1f}%
- Tethys GDP: ${scenario_params['tethys_gdp']:.1f}B (baseline: $30B)
- Novaris GDP: ${scenario_params['novaris_gdp']:.1f}B (baseline: $100B)
- Military Balance: {scenario_params['military_balance']:.2f} (-1=Novaris advantage, +1=Tethys advantage)
- International Support for Tethys: {scenario_params['international_support'] * 100:.0f}%
- Sanctions on Novaris: {scenario_params['sanctions_level'] * 100:.0f}%
- Crisis Level: {scenario_params['crisis_level']:.0f}/10

EXTERNAL EVENTS THIS PERIOD:
{events_text}
EXTERNAL ACTOR ACTIONS THIS PERIOD:
{ext_actor_text}
ACTIONS TAKEN BY NOVARIS AND TETHYS THIS PERIOD:
(Forecaster must predict these - actual actions withheld)
"""
    return initial_scenario, historical_summary, current_period_data


# ===================================================================
# Single prediction
# ===================================================================

def run_single_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fraction: float,
    agent_id: int,
    system_prompt: str,
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
            system_prompt=system_prompt,
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


# ===================================================================
# Scenario-condition runner
# ===================================================================

def run_scenario_condition(
    scenario_id: str,
    scenario_params: pd.Series,
    ground_truth: pd.Series,
    condition_name: str,
    sharding_strategy: str,
    n_agents: int,
    all_personas: List[SimplifiedProfile],
    max_workers: int = 5,
    model: str = PREDICTION_MODEL
) -> Tuple[Dict, List[Dict]]:
    """
    Run N agents for one scenario/condition combination.

    Returns:
        (scenario_result_dict, list_of_agent_detail_dicts)
    """
    # Determine condition type
    is_persona = condition_name.startswith("persona")

    # Create prompt sections (shared across agents for this scenario)
    initial_scenario, historical_summary, current_period_data = create_scenario_prompt(
        scenario_params
    )

    # Persona assignment: deterministic per (scenario_id, condition_name)
    if is_persona:
        seed = hash(f"{scenario_id}_{condition_name}") % (2**31)
        rng = random.Random(seed)
        selected_personas = rng.sample(all_personas, min(n_agents, len(all_personas)))
    else:
        selected_personas = [None] * n_agents

    # Create information distribution for sharded conditions
    info_fractions = create_information_distribution(n_agents)

    # Build per-agent instructions and system prompts
    agent_configs = []
    for i in range(n_agents):
        persona = selected_personas[i] if is_persona else None

        if is_persona and persona is not None:
            sys_prompt = build_persona_system_prompt(persona)
            instr = build_instructions("persona", persona)
        else:
            sys_prompt = SYSTEM_PROMPT_GENERIC
            instr = build_instructions("generic")

        info_frac = info_fractions[i] if "shard" in condition_name else 1.0

        agent_configs.append({
            'agent_id': i,
            'persona': persona,
            'system_prompt': sys_prompt,
            'instructions': instr,
            'information_fraction': info_frac,
        })

    # Run predictions in parallel
    start_time = time.time()
    results = []
    agent_details = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for cfg in agent_configs:
            if cfg['agent_id'] > 0 and cfg['agent_id'] % 10 == 0:
                time.sleep(0.5)

            future = executor.submit(
                run_single_prediction,
                initial_scenario,
                historical_summary,
                current_period_data,
                cfg['instructions'],
                sharding_strategy,
                cfg['information_fraction'],
                cfg['agent_id'],
                cfg['system_prompt'],
                model
            )
            futures[future] = cfg

        for future in concurrent.futures.as_completed(futures):
            cfg = futures[future]
            try:
                result = future.result()
            except Exception:
                result = {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'future_exception'}
            results.append(result)

            persona = cfg['persona']
            agent_details.append({
                'scenario_id': scenario_id,
                'condition': condition_name,
                'agent_id': cfg['agent_id'],
                'persona_id': persona.persona_id if persona else None,
                'strategic_orientation': persona.strategic_orientation if persona else None,
                'risk_tolerance': persona.risk_tolerance if persona else None,
                'military_expertise': persona.military_expertise if persona else None,
                'economic_expertise': persona.economic_expertise if persona else None,
                'geopolitical_expertise': persona.geopolitical_expertise if persona else None,
                'information_fraction': cfg['information_fraction'],
                'probability': result.get('probability', 0.5),
                'rationale': result.get('rationale', ''),
                'fallback_type': result.get('_fallback', None),
            })

    duration = time.time() - start_time

    # Aggregate
    probabilities = [r.get('probability', 0.5) for r in results]
    ensemble_prob = np.mean(probabilities)
    true_prob = ground_truth['collapse_probability']
    squared_error = (ensemble_prob - true_prob) ** 2
    fallback_count = sum(1 for r in results if '_fallback' in r)

    scenario_result = {
        'scenario_id': scenario_id,
        'condition': condition_name,
        'sharding_strategy': sharding_strategy,
        'n_agents': n_agents,
        'duration_seconds': duration,
        'ensemble_probability': ensemble_prob,
        'ground_truth_probability': true_prob,
        'squared_error': squared_error,
        'probability_mean': np.mean(probabilities),
        'probability_std': np.std(probabilities),
        'probability_min': np.min(probabilities),
        'probability_max': np.max(probabilities),
        'fallback_count': fallback_count,
        'fallback_rate': fallback_count / n_agents,
    }

    return scenario_result, agent_details


# ===================================================================
# Statistical tests
# ===================================================================

def run_statistical_tests(results_df: pd.DataFrame):
    """Run pairwise statistical tests and interaction test."""
    from scipy import stats as scipy_stats

    print(f"\n{'='*70}")
    print("STATISTICAL SIGNIFICANCE TESTS")
    print(f"{'='*70}")

    # Define comparison pairs
    comparisons = [
        ("generic_baseline", "persona_baseline"),
        ("generic_shard", "persona_shard"),
        ("generic_baseline", "generic_shard"),
        ("persona_baseline", "persona_shard"),
    ]

    available_conditions = set(results_df['condition'].unique())

    for c1, c2 in comparisons:
        if c1 not in available_conditions or c2 not in available_conditions:
            continue

        df1 = results_df[results_df['condition'] == c1].sort_values('scenario_id')
        df2 = results_df[results_df['condition'] == c2].sort_values('scenario_id')

        merged = df1[['scenario_id', 'squared_error']].merge(
            df2[['scenario_id', 'squared_error']],
            on='scenario_id', suffixes=(f'_{c1}', f'_{c2}')
        )

        if len(merged) < 3:
            print(f"\n  {c1} vs {c2}: Too few paired observations ({len(merged)})")
            continue

        se_1 = merged[f'squared_error_{c1}'].values
        se_2 = merged[f'squared_error_{c2}'].values
        diff = se_1 - se_2

        # Paired t-test
        t_stat, t_pval = scipy_stats.ttest_rel(se_1, se_2)

        # Wilcoxon signed-rank test
        try:
            w_stat, w_pval = scipy_stats.wilcoxon(se_1, se_2)
        except ValueError:
            w_stat, w_pval = float('nan'), float('nan')

        # Cohen's d for paired samples
        d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0

        mean_1, mean_2 = np.mean(se_1), np.mean(se_2)
        pct_change = ((mean_2 - mean_1) / mean_1) * 100 if mean_1 > 0 else 0

        sig_t = '***' if t_pval < 0.001 else '**' if t_pval < 0.01 else '*' if t_pval < 0.05 else 'ns'
        sig_w = '***' if w_pval < 0.001 else '**' if w_pval < 0.01 else '*' if w_pval < 0.05 else 'ns'
        d_label = 'large' if abs(d) > 0.8 else 'medium' if abs(d) > 0.5 else 'small' if abs(d) > 0.2 else 'negligible'

        print(f"\n  {c1} vs {c2} (N={len(merged)} paired scenarios)")
        print(f"    Mean SE: {mean_1:.4f} vs {mean_2:.4f} ({pct_change:+.1f}%)")
        print(f"    Paired t-test:   t={t_stat:.3f}, p={t_pval:.4f} {sig_t}")
        print(f"    Wilcoxon test:   W={w_stat:.1f}, p={w_pval:.4f} {sig_w}")
        print(f"    Cohen's d:       {d:.3f} ({d_label})")
        print(f"    Scenarios where {c1} better: {np.sum(diff < 0)}/{len(merged)}")
        print(f"    Scenarios where {c2} better: {np.sum(diff > 0)}/{len(merged)}")

    # Interaction test: does persona improvement differ under sharding vs baseline?
    needed = {"generic_baseline", "persona_baseline", "generic_shard", "persona_shard"}
    if needed.issubset(available_conditions):
        print(f"\n{'='*70}")
        print("INTERACTION TEST: Persona effect x Sharding")
        print(f"{'='*70}")

        gb = results_df[results_df['condition'] == 'generic_baseline'].set_index('scenario_id')['squared_error']
        pb = results_df[results_df['condition'] == 'persona_baseline'].set_index('scenario_id')['squared_error']
        gs = results_df[results_df['condition'] == 'generic_shard'].set_index('scenario_id')['squared_error']
        ps = results_df[results_df['condition'] == 'persona_shard'].set_index('scenario_id')['squared_error']

        common = gb.index.intersection(pb.index).intersection(gs.index).intersection(ps.index)

        if len(common) >= 3:
            # Persona improvement under baseline = (generic_baseline SE) - (persona_baseline SE)
            improvement_baseline = gb.loc[common].values - pb.loc[common].values
            # Persona improvement under sharding = (generic_shard SE) - (persona_shard SE)
            improvement_shard = gs.loc[common].values - ps.loc[common].values

            interaction = improvement_shard - improvement_baseline

            t_stat_int, p_int = scipy_stats.ttest_rel(improvement_shard, improvement_baseline)
            try:
                w_stat_int, wp_int = scipy_stats.wilcoxon(improvement_shard, improvement_baseline)
            except ValueError:
                w_stat_int, wp_int = float('nan'), float('nan')

            print(f"  Persona improvement under baseline: {np.mean(improvement_baseline):.4f} (positive = persona better)")
            print(f"  Persona improvement under sharding: {np.mean(improvement_shard):.4f}")
            print(f"  Interaction (shard - baseline):     {np.mean(interaction):.4f}")
            sig_int = '***' if p_int < 0.001 else '**' if p_int < 0.01 else '*' if p_int < 0.05 else 'ns'
            print(f"  Paired t-test on interaction:  t={t_stat_int:.3f}, p={p_int:.4f} {sig_int}")
            wp_sig = '***' if wp_int < 0.001 else '**' if wp_int < 0.01 else '*' if wp_int < 0.05 else 'ns'
            print(f"  Wilcoxon on interaction:       W={w_stat_int:.1f}, p={wp_int:.4f} {wp_sig}")
        else:
            print(f"  Too few common scenarios ({len(common)}) for interaction test")


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Persona + CoT Bridging Experiment")
    parser.add_argument("--test", action="store_true",
                        help="Quick test: 3 scenarios, 5 agents, 2 conditions")
    parser.add_argument("--n-scenarios", type=int, default=None,
                        help="Number of scenarios to process")
    parser.add_argument("--n-agents", type=int, default=None,
                        help="Number of agents per condition")
    parser.add_argument("--conditions", nargs="+", default=None,
                        help="Conditions to run: generic_baseline persona_baseline generic_shard persona_shard")
    parser.add_argument("--start-scenario", type=int, default=0,
                        help="Index to start from (for resuming)")
    args = parser.parse_args()

    # --- Configuration ---
    data_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario")
    output_dir = Path("D:/Northeastern/LLM_Forecasting/experiment_results/persona_cot_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Condition definitions: (condition_name, sharding_strategy)
    ALL_CONDITIONS = {
        "generic_baseline":  "none",
        "persona_baseline":  "none",
        "generic_shard":     "shard_everything",
        "persona_shard":     "shard_everything",
    }

    if args.test:
        n_scenarios = 3
        n_agents = args.n_agents or 5
        conditions = [
            ("generic_baseline", "none"),
            ("persona_baseline", "none"),
        ]
    else:
        n_scenarios = args.n_scenarios or 50
        n_agents = args.n_agents or 10
        if args.conditions:
            conditions = [(c, ALL_CONDITIONS[c]) for c in args.conditions]
        else:
            conditions = list(ALL_CONDITIONS.items())

    print("=" * 70)
    print("PERSONA + CoT BRIDGING EXPERIMENT")
    print("=" * 70)
    print(f"Scenarios:  {n_scenarios}")
    print(f"Agents:     {n_agents} per scenario/condition")
    print(f"Conditions: {[c[0] for c in conditions]}")
    print(f"Model:      {PREDICTION_MODEL}")
    if args.test:
        print("[TEST MODE]")
    print("=" * 70)

    # --- Load data ---
    print("\nLoading scenario data...")
    scenarios = pd.read_csv(data_dir / "scenarios.csv")
    ground_truth = pd.read_csv(data_dir / "ground_truth.csv")
    data = scenarios.merge(ground_truth, on='scenario_id', how='inner')

    # Apply start and limit
    data = data.iloc[args.start_scenario:]
    if n_scenarios < len(data):
        data = data.head(n_scenarios)

    print(f"Processing scenarios {args.start_scenario} to {args.start_scenario + len(data) - 1} "
          f"({len(data)} total)")

    # --- Load personas ---
    print("\nLoading persona pool...")
    all_personas = load_simplified_personas()

    # Show persona pool stats
    orientations = [p.strategic_orientation for p in all_personas]
    risk_vals = [p.risk_tolerance for p in all_personas]
    print(f"  Orientations: hawkish={orientations.count('hawkish')}, "
          f"dovish={orientations.count('dovish')}, "
          f"pragmatic={orientations.count('pragmatic')}")
    print(f"  Risk tolerance: mean={np.mean(risk_vals):.1f}, "
          f"std={np.std(risk_vals):.1f}, "
          f"range=[{min(risk_vals)}, {max(risk_vals)}]")

    # --- Run experiment ---
    print(f"\nRunning {len(data)} scenarios x {len(conditions)} conditions...")
    all_scenario_results = []
    all_agent_details = []

    # Set up incremental CSV save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"scenario_results_{timestamp}.csv"
    agent_file = output_dir / f"agent_details_{timestamp}.csv"
    scenario_csv_header_written = False
    agent_csv_header_written = False

    for idx, row in data.iterrows():
        scenario_id = row['scenario_id']
        scenario_num = idx - args.start_scenario + 1
        print(f"\n[{scenario_num}/{len(data)}] {scenario_id}")
        print(f"  Territory: {row['territory_controlled']*100:.1f}% | "
              f"Balance: {row['military_balance']:.2f} | "
              f"Sanctions: {row['sanctions_level']*100:.0f}% | "
              f"Truth: {row['collapse_probability']:.3f}")

        for cond_name, strategy in conditions:
            try:
                scenario_result, agent_details = run_scenario_condition(
                    scenario_id=scenario_id,
                    scenario_params=row,
                    ground_truth=row,
                    condition_name=cond_name,
                    sharding_strategy=strategy,
                    n_agents=n_agents,
                    all_personas=all_personas,
                    max_workers=5,
                    model=PREDICTION_MODEL
                )
                all_scenario_results.append(scenario_result)
                all_agent_details.extend(agent_details)

                # Incremental save: scenario-level
                pd.DataFrame([scenario_result]).to_csv(
                    results_file, mode='a', index=False,
                    header=not scenario_csv_header_written)
                scenario_csv_header_written = True

                # Incremental save: agent-level
                pd.DataFrame(agent_details).to_csv(
                    agent_file, mode='a', index=False,
                    header=not agent_csv_header_written)
                agent_csv_header_written = True

                print(f"  {cond_name:<20} Ens: {scenario_result['ensemble_probability']:.3f} | "
                      f"SE: {scenario_result['squared_error']:.4f} | "
                      f"Std: {scenario_result['probability_std']:.3f} | "
                      f"Fallbacks: {scenario_result['fallback_count']}/{n_agents}")

            except Exception as e:
                print(f"  [ERROR] {cond_name} failed: {e}")

    # Final full save (overwrites incremental file to ensure consistency)
    results_df = pd.DataFrame(all_scenario_results)
    results_df.to_csv(results_file, index=False)

    agent_df = pd.DataFrame(all_agent_details)
    agent_df.to_csv(agent_file, index=False)

    # --- Summary ---
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")

    summary = results_df.groupby('condition').agg({
        'squared_error': ['mean', 'std', 'min', 'max'],
        'probability_std': 'mean',
        'fallback_rate': 'mean'
    }).round(4)
    print(summary)

    # Diversity summary per condition
    print(f"\n{'='*70}")
    print("PREDICTION DIVERSITY (agent-level)")
    print(f"{'='*70}")
    for cond in results_df['condition'].unique():
        cond_agents = agent_df[agent_df['condition'] == cond]
        probs = cond_agents['probability'].values
        print(f"  {cond:<20} mean={np.mean(probs):.3f} std={np.std(probs):.3f} "
              f"range=[{np.min(probs):.3f}, {np.max(probs):.3f}]")

    # Persona attribute distributions for persona conditions
    persona_agents = agent_df[agent_df['persona_id'].notna()]
    if len(persona_agents) > 0:
        print(f"\n{'='*70}")
        print("PERSONA ATTRIBUTE DISTRIBUTIONS (persona conditions only)")
        print(f"{'='*70}")
        orient_counts = persona_agents['strategic_orientation'].value_counts()
        print(f"  Orientations: {dict(orient_counts)}")
        rt = persona_agents['risk_tolerance'].dropna()
        print(f"  Risk tolerance: mean={rt.mean():.1f}, std={rt.std():.1f}")

    # --- Statistical tests ---
    if len(results_df['condition'].unique()) >= 2:
        run_statistical_tests(results_df)

    # Save summary
    summary_file = output_dir / f"summary_{timestamp}.csv"
    summary.to_csv(summary_file)

    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE")
    print(f"Scenario results: {results_file}")
    print(f"Agent details:    {agent_file}")
    print(f"Summary:          {summary_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
