"""
Analytical Framework Diversity Experiment
==========================================

Tests whether assigning each agent a distinct analytical methodology
(base rate analysis, worst-case reasoning, scenario tree, etc.) produces
meaningfully higher prediction diversity than persona-based approaches.

Hypothesis: Structurally different reasoning paths produce higher prediction
diversity than persona prompts that don't alter the model's actual reasoning.

2 conditions:
  - framework_baseline: 10 agents (1 per framework), full information
  - framework_shard:    10 agents (1 per framework), sharded information

Usage:
    # Fixed 10 frameworks (existing behavior, unchanged)
    python -u forecasting/run_framework_experiment.py --test
    python -u forecasting/run_framework_experiment.py --n-scenarios 50 --n-agents 10

    # Composable pool (125 combinations, sample 10 per scenario)
    python -u forecasting/run_framework_experiment.py --pool --test
    python -u forecasting/run_framework_experiment.py --pool --n-scenarios 50 --n-agents 10
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
import time
import argparse
import pandas as pd
import numpy as np
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.collapse_prompts_with_scenario import INITIAL_SCENARIO
from forecasting.information_sharding import create_information_distribution
from forecasting.sharding_strategies import apply_sharding_strategy

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
PREDICTION_MODEL = "deepseek/deepseek-v3.2"

# Model pool for --multi-model: each agent gets a randomly assigned model
# Diverse families, all reliable for structured JSON output via OpenRouter
MODEL_POOL = [
    "deepseek/deepseek-v3.2",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.5-flash",
    "mistralai/mistral-small-3.2-24b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "google/gemma-3-27b-it",
]

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
# 10 Analytical Frameworks
# ---------------------------------------------------------------------------
FRAMEWORKS = [
    {
        "name": "base_rate",
        "system_prompt": (
            "You are a Base Rate Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: ALWAYS start from historical base rates of government collapse "
            "in comparable crises, then adjust incrementally based on case-specific evidence. "
            "Resist the temptation to anchor on vivid details — ground your estimate in "
            "statistical frequencies of similar outcomes.\n\n"
            "Apply your base-rate methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - be decisive based on historical frequencies.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using BASE RATE ANALYSIS:\n"
            "1. REFERENCE CLASS: Identify the most appropriate reference class for this crisis "
            "(e.g., great-power pressure campaigns against smaller states, territorial disputes "
            "with military mobilization). What is the historical base rate of government collapse "
            "in such crises? Estimate a specific percentage.\n"
            "2. SIMILARITY ASSESSMENT: How closely does this case match the reference class? "
            "Note key similarities and differences.\n"
            "3. ADJUSTMENT FACTORS: Identify 2-3 factors that push the probability UP from the "
            "base rate and 2-3 that push it DOWN. Quantify each adjustment.\n"
            "4. ANCHORED ESTIMATE: Starting from your base rate, apply adjustments sequentially. "
            "Show your arithmetic.\n"
            "5. FINAL PROBABILITY: State your adjusted estimate. Ensure it hasn't drifted too far "
            "from the base rate without strong justification."
        ),
    },
    {
        "name": "key_indicator",
        "system_prompt": (
            "You are a Key Indicator Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Identify the SINGLE most diagnostic variable — the one indicator "
            "that historically has the strongest predictive power for government collapse — and "
            "weight it heavily in your estimate. Other factors matter, but one variable dominates.\n\n"
            "Apply your key-indicator methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - be decisive based on the key indicator.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using KEY INDICATOR ANALYSIS:\n"
            "1. INDICATOR SCAN: Review all available variables (territory, GDP, military balance, "
            "international support, sanctions, crisis level, events).\n"
            "2. KEY INDICATOR SELECTION: Choose the SINGLE most diagnostic variable. Justify why "
            "this indicator has the highest predictive validity for government collapse.\n"
            "3. INDICATOR READING: What does this key indicator currently show? Is it at a "
            "critical threshold? What direction is it trending?\n"
            "4. SECONDARY CHECK: Briefly check if other indicators contradict or reinforce the "
            "key indicator's signal. Note any major divergences.\n"
            "5. FINAL PROBABILITY: Derive your estimate primarily from the key indicator, "
            "with minor adjustments from secondary factors."
        ),
    },
    {
        "name": "scenario_tree",
        "system_prompt": (
            "You are a Scenario Tree Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Enumerate 3-5 distinct future paths (e.g., full invasion, "
            "negotiated settlement, frozen conflict, internal coup, economic capitulation), "
            "assign a probability to each path, then calculate the collapse probability as "
            "the weighted sum across paths.\n\n"
            "Apply your scenario-tree methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - let the scenario weights drive your estimate.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using SCENARIO TREE ANALYSIS:\n"
            "1. ENUMERATE SCENARIOS: Define 3-5 mutually exclusive, collectively exhaustive "
            "paths forward. Name each scenario clearly.\n"
            "2. SCENARIO PROBABILITIES: Assign a probability to each scenario. They MUST sum "
            "to 1.0. Show the values.\n"
            "3. CONDITIONAL COLLAPSE: For each scenario, estimate P(collapse | scenario). "
            "Some scenarios (e.g., full invasion) may have high collapse probability; others "
            "(e.g., negotiated settlement) may have near-zero.\n"
            "4. WEIGHTED CALCULATION: Calculate total P(collapse) = sum of "
            "P(scenario_i) * P(collapse | scenario_i). Show the arithmetic.\n"
            "5. FINAL PROBABILITY: State the calculated result. Cross-check it against "
            "your intuition — if they diverge, explain why."
        ),
    },
    {
        "name": "historical_analogy",
        "system_prompt": (
            "You are a Historical Analogy Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Identify the closest historical parallel to this crisis and use "
            "its outcome as your primary anchor. Adjust for key differences between the historical "
            "case and the current situation.\n\n"
            "Apply your historical-analogy methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - let the historical parallel guide your estimate.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using HISTORICAL ANALOGY ANALYSIS:\n"
            "1. CANDIDATE ANALOGIES: Identify 2-3 historical cases that most closely resemble "
            "this crisis (consider: great-power vs. small-state conflicts, territorial disputes, "
            "military mobilizations, sanctions campaigns).\n"
            "2. BEST ANALOGY: Select the single best historical parallel. Explain why it is "
            "the most relevant.\n"
            "3. HISTORICAL OUTCOME: What happened in the analogous case? Did the smaller state's "
            "government collapse? Over what timeframe?\n"
            "4. KEY DIFFERENCES: Identify 2-3 important ways the current situation differs from "
            "the historical case. For each, state whether it makes collapse MORE or LESS likely.\n"
            "5. FINAL PROBABILITY: Anchor on the historical outcome and adjust for differences. "
            "State your estimate."
        ),
    },
    {
        "name": "worst_case",
        "system_prompt": (
            "You are a Worst Case Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Systematically assume the most threatening interpretation of every "
            "ambiguous signal. Where information is uncertain, assume the worst. Your role is to "
            "identify the upper bound of collapse risk by stress-testing assumptions.\n\n"
            "Apply your worst-case methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Your estimates should be HIGHER than a neutral analyst's — that is your job.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using WORST CASE ANALYSIS:\n"
            "1. THREAT INVENTORY: List every factor that could contribute to government collapse. "
            "Be comprehensive — include low-probability but high-impact risks.\n"
            "2. PESSIMISTIC INTERPRETATION: For each ambiguous indicator (military balance, "
            "international support, economic trajectory), explain the most threatening "
            "plausible reading.\n"
            "3. CASCADE RISKS: Identify how negative developments could compound — e.g., "
            "military setback → economic panic → loss of international support → collapse.\n"
            "4. STABILIZING FACTORS: Briefly acknowledge factors that work against collapse, "
            "but assess whether they would hold under worst-case pressure.\n"
            "5. FINAL PROBABILITY: Given the worst plausible interpretation of the evidence, "
            "estimate collapse probability. This should be ABOVE what a neutral analyst would say."
        ),
    },
    {
        "name": "best_case",
        "system_prompt": (
            "You are a Best Case Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Systematically assume the most favorable interpretation of every "
            "ambiguous signal. Where information is uncertain, assume resilience. Your role is to "
            "identify the lower bound of collapse risk by highlighting stabilizing factors.\n\n"
            "Apply your best-case methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Your estimates should be LOWER than a neutral analyst's — that is your job.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using BEST CASE ANALYSIS:\n"
            "1. RESILIENCE INVENTORY: List every factor that supports government survival. "
            "Be comprehensive — include institutional strengths, external support, and "
            "defensive advantages.\n"
            "2. OPTIMISTIC INTERPRETATION: For each ambiguous indicator, explain the most "
            "favorable plausible reading.\n"
            "3. STABILIZING DYNAMICS: Identify how positive factors reinforce each other — "
            "e.g., international support → economic aid → military sustainability → deterrence.\n"
            "4. RISK FACTORS: Briefly acknowledge threats, but assess whether the government "
            "has adequate buffers and responses.\n"
            "5. FINAL PROBABILITY: Given the most favorable plausible interpretation, estimate "
            "collapse probability. This should be BELOW what a neutral analyst would say."
        ),
    },
    {
        "name": "trend",
        "system_prompt": (
            "You are a Trend Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Focus on the RATE OF CHANGE and momentum of key variables rather "
            "than their absolute levels. A deteriorating trend at a moderate level is more alarming "
            "than a bad-but-stable situation. Direction matters more than position.\n\n"
            "Apply your trend methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - let the momentum of change drive your estimate.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using TREND ANALYSIS:\n"
            "1. VARIABLE TRAJECTORIES: For each key variable (territory, GDP, military balance, "
            "international support, sanctions, crisis level), assess: Is it improving, stable, "
            "or deteriorating? How fast?\n"
            "2. MOMENTUM ASSESSMENT: Which variables show accelerating change (positive feedback "
            "loops)? Which show decelerating change (stabilizing)?  \n"
            "3. LEADING INDICATORS: Identify which current trends are likely to be leading "
            "indicators of future collapse or survival. Which trends have the most predictive "
            "power?\n"
            "4. TRAJECTORY PROJECTION: If current trends continue, where will key variables be "
            "in the near future? Are any approaching critical thresholds?\n"
            "5. FINAL PROBABILITY: Base your estimate primarily on the direction and speed of "
            "change, not on current absolute levels."
        ),
    },
    {
        "name": "structural",
        "system_prompt": (
            "You are a Structural Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Focus on deep structural factors — institutional resilience, "
            "geography, resource fundamentals, demographic cohesion, and governance capacity — "
            "rather than short-term events or tactical developments. Structures change slowly "
            "and constrain what is possible.\n\n"
            "Apply your structural methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - let structural fundamentals drive your estimate.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using STRUCTURAL ANALYSIS:\n"
            "1. INSTITUTIONAL RESILIENCE: How robust are Tethys's governing institutions? "
            "Can they function under extreme pressure? Is there a deep state, professional "
            "military, or civil service that persists regardless of leadership?\n"
            "2. GEOGRAPHIC FACTORS: Does geography favor defense or offense? Can Tethys "
            "sustain territorial integrity based on terrain, borders, and logistics?\n"
            "3. RESOURCE FUNDAMENTALS: Assess economic capacity for sustained conflict — "
            "GDP, energy access, trade routes, sanctions impact. Can Tethys sustain itself "
            "economically?\n"
            "4. EXTERNAL STRUCTURAL SUPPORT: Is international support structural (treaty "
            "alliances, institutional commitments) or contingent (political will, public "
            "opinion)? How durable is it?\n"
            "5. FINAL PROBABILITY: Base your estimate on structural factors. Short-term "
            "events should only matter if they threaten structural fundamentals."
        ),
    },
    {
        "name": "game_theoretic",
        "system_prompt": (
            "You are a Game Theoretic Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Model this crisis as a strategic interaction between rational "
            "actors with known payoffs. Analyze each actor's incentives, available strategies, "
            "and likely equilibrium outcomes. Focus on what rational actors WOULD do given "
            "their constraints.\n\n"
            "Apply your game-theoretic methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Do NOT cluster around 0.5 - let the equilibrium analysis drive your estimate.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using GAME THEORETIC ANALYSIS:\n"
            "1. PLAYERS AND PAYOFFS: Identify the key players (Novaris, Tethys, Meridian, "
            "Aurelia, Valkoria). For each, what are their key objectives and what outcomes "
            "do they most/least prefer?\n"
            "2. STRATEGIC OPTIONS: What are each player's available strategies? What are the "
            "costs and benefits of escalation vs. de-escalation for each actor?\n"
            "3. EQUILIBRIUM ANALYSIS: Given rational play, what is the most likely equilibrium "
            "outcome? Is there a dominant strategy for any player? Are there commitment "
            "problems or credibility issues?\n"
            "4. INFORMATION AND SIGNALING: What signals are players sending? Are they credible? "
            "Could bluffing or miscalculation lead to unintended escalation?\n"
            "5. FINAL PROBABILITY: Based on the equilibrium analysis, estimate the probability "
            "that the game resolves in Tethys government collapse."
        ),
    },
    {
        "name": "devils_advocate",
        "system_prompt": (
            "You are a Devil's Advocate Analyst specializing in government stability forecasting.\n\n"
            "Your methodology: Explicitly argue AGAINST the consensus or obvious reading of the "
            "situation. If most analysts would say collapse is unlikely, argue for why it might "
            "happen. If the situation looks dire, argue for why the government might survive. "
            "Challenge every assumption.\n\n"
            "Apply your contrarian methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
            "Your estimate should DIFFER from what a conventional analyst would say.\n\n"
            "Output ONLY valid JSON in the exact format specified."
        ),
        "cot_instructions": (
            "Think step-by-step using DEVIL'S ADVOCATE ANALYSIS:\n"
            "1. CONVENTIONAL READING: First, state what a conventional analyst would likely "
            "conclude from this evidence. What is the 'obvious' interpretation?\n"
            "2. CHALLENGE ASSUMPTIONS: Identify 3-4 key assumptions underlying the conventional "
            "view. For each, explain why it might be wrong.\n"
            "3. CONTRARIAN EVIDENCE: What evidence is being underweighted or ignored by the "
            "conventional view? What signals point in the opposite direction?\n"
            "4. ALTERNATIVE NARRATIVE: Construct a coherent alternative narrative that leads "
            "to a different outcome than the consensus expects.\n"
            "5. FINAL PROBABILITY: State an estimate that reflects your contrarian analysis. "
            "It should meaningfully differ from the conventional view — if the obvious answer "
            "is low collapse probability, yours should be higher, and vice versa."
        ),
    },
]

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_framework_instructions(framework: Dict) -> str:
    """Build the full instruction block with framework-specific CoT."""
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

{framework['cot_instructions']}

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
        Instructions are built separately via build_framework_instructions().
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
    max_workers: int = 5,
    model: str = PREDICTION_MODEL,
    framework_pool: List[Dict] = None,
    model_pool: List[str] = None
) -> Tuple[Dict, List[Dict]]:
    """
    Run N agents for one scenario/condition combination.

    Each agent is assigned a unique analytical framework. If framework_pool
    is provided, frameworks are sampled from the composable pool (seeded by
    scenario_id + condition_name). Otherwise falls back to the fixed
    FRAMEWORKS list.

    If model_pool is provided, each agent is assigned a model from the pool
    via deterministic hashing (seeded by scenario_id + condition + agent_id).

    Returns:
        (scenario_result_dict, list_of_agent_detail_dicts)
    """
    import hashlib

    # Create prompt sections (shared across agents for this scenario)
    initial_scenario, historical_summary, current_period_data = create_scenario_prompt(
        scenario_params
    )

    # Create information distribution for sharded conditions
    info_fractions = create_information_distribution(n_agents)

    # Select frameworks: composable pool or fixed list
    if framework_pool is not None:
        from forecasting.framework_pool import sample_frameworks
        seed = f"{scenario_id}_{condition_name}"
        frameworks = sample_frameworks(n=n_agents, seed=seed)
    else:
        frameworks = FRAMEWORKS

    # Build per-agent configs with framework assignments
    agent_configs = []
    for i in range(n_agents):
        framework = frameworks[i % len(frameworks)]
        info_frac = info_fractions[i] if "shard" in condition_name else 1.0

        # Assign model: per-agent from pool, or single model for all
        if model_pool is not None:
            hash_input = f"{scenario_id}_{condition_name}_{i}"
            idx = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16) % len(model_pool)
            agent_model = model_pool[idx]
        else:
            agent_model = model

        agent_configs.append({
            'agent_id': i,
            'framework': framework,
            'system_prompt': framework['system_prompt'],
            'instructions': build_framework_instructions(framework),
            'information_fraction': info_frac,
            'model': agent_model,
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
                cfg['model']
            )
            futures[future] = cfg

        for future in concurrent.futures.as_completed(futures):
            cfg = futures[future]
            try:
                result = future.result()
            except Exception:
                result = {'probability': 0.5, 'confidence': 'low', 'rationale': 'Error', '_fallback': 'future_exception'}
            results.append(result)

            framework = cfg['framework']
            agent_details.append({
                'scenario_id': scenario_id,
                'condition': condition_name,
                'agent_id': cfg['agent_id'],
                'framework_name': framework['name'],
                'method': framework.get('method', ''),
                'lens': framework.get('lens', ''),
                'focus': framework.get('focus', ''),
                'bias': framework.get('bias', ''),
                'model': cfg['model'],
                'information_fraction': cfg['information_fraction'],
                'probability': result.get('probability', 0.5),
                'confidence': result.get('confidence', ''),
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
    """Run pairwise statistical tests between conditions."""
    from scipy import stats as scipy_stats

    print(f"\n{'='*70}")
    print("STATISTICAL SIGNIFICANCE TESTS")
    print(f"{'='*70}")

    comparisons = [
        ("framework_baseline", "framework_shard"),
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


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Analytical Framework Diversity Experiment")
    parser.add_argument("--test", action="store_true",
                        help="Quick test: 3 scenarios, 10 agents, 2 conditions")
    parser.add_argument("--pool", action="store_true",
                        help="Use composable framework pool (1000 combinations) instead of fixed 10")
    parser.add_argument("--multi-model", action="store_true",
                        help="Assign each agent a randomly selected model from MODEL_POOL")
    parser.add_argument("--n-scenarios", type=int, default=None,
                        help="Number of scenarios to process")
    parser.add_argument("--n-agents", type=int, default=None,
                        help="Number of agents per condition")
    parser.add_argument("--conditions", nargs="+", default=None,
                        help="Conditions to run: framework_baseline framework_shard")
    parser.add_argument("--model", type=str, default=None,
                        help="Override prediction model (default: deepseek/deepseek-v3.2)")
    parser.add_argument("--frameworks", nargs="+", default=None,
                        help="Filter to specific frameworks (e.g., --frameworks base_rate worst_case)")
    parser.add_argument("--start-scenario", type=int, default=0,
                        help="Index to start from (for resuming)")
    args = parser.parse_args()

    # Override model if specified
    if args.model:
        global PREDICTION_MODEL
        PREDICTION_MODEL = args.model

    # Filter frameworks if specified
    global FRAMEWORKS
    if args.frameworks:
        FRAMEWORKS = [f for f in FRAMEWORKS if f['name'] in args.frameworks]
        if not FRAMEWORKS:
            print(f"ERROR: No frameworks matched {args.frameworks}")
            sys.exit(1)

    # --- Configuration ---
    data_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario")
    output_dir = Path("D:/Northeastern/LLM_Forecasting/experiment_results/framework_experiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Condition definitions: (condition_name, sharding_strategy)
    ALL_CONDITIONS = {
        "framework_baseline": "none",
        "framework_shard":    "shard_everything",
    }

    # Load composable pool if requested
    use_pool = args.pool
    pool = None
    if use_pool:
        from forecasting.framework_pool import generate_pool
        pool = generate_pool()

    # Multi-model setup
    use_multi_model = args.multi_model
    mpool = MODEL_POOL if use_multi_model else None

    if args.test:
        n_scenarios = 3
        n_agents = args.n_agents or 10
        conditions = list(ALL_CONDITIONS.items())
    else:
        n_scenarios = args.n_scenarios or 50
        n_agents = args.n_agents or 10
        if args.conditions:
            conditions = [(c, ALL_CONDITIONS[c]) for c in args.conditions]
        else:
            conditions = list(ALL_CONDITIONS.items())

    print("=" * 70)
    print("ANALYTICAL FRAMEWORK DIVERSITY EXPERIMENT")
    print("=" * 70)
    print(f"Scenarios:  {n_scenarios}")
    print(f"Agents:     {n_agents} per scenario/condition")
    print(f"Conditions: {[c[0] for c in conditions]}")
    if use_pool:
        print(f"Frameworks: COMPOSABLE POOL ({len(pool)} combinations, sampling {n_agents} per scenario)")
    else:
        print(f"Frameworks: {[f['name'] for f in FRAMEWORKS[:n_agents]]}")
    if use_multi_model:
        print(f"Models:     MULTI-MODEL POOL ({len(MODEL_POOL)} models, per-agent assignment)")
        for m in MODEL_POOL:
            print(f"              - {m}")
    else:
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

    # --- Show framework summary ---
    if use_pool:
        from forecasting.framework_pool import METHODS, LENSES, FOCUSES, BIASES
        print(f"\nComposable pool: {len(pool)} frameworks "
              f"({len(METHODS)} methods x {len(LENSES)} lenses x {len(FOCUSES)} focuses x {len(BIASES)} biases)")
        print(f"  Methods: {', '.join(m['id'] for m in METHODS)}")
        print(f"  Lenses:  {', '.join(l['id'] for l in LENSES)}")
        print(f"  Focuses: {', '.join(f['id'] for f in FOCUSES)}")
        print(f"  Biases:  {', '.join(b['id'] for b in BIASES)}")
    else:
        print(f"\nAnalytical frameworks ({len(FRAMEWORKS)} total):")
        for i, fw in enumerate(FRAMEWORKS):
            print(f"  {i+1:2d}. {fw['name']}")

    # --- Run experiment ---
    print(f"\nRunning {len(data)} scenarios x {len(conditions)} conditions x {n_agents} agents...")
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
                    max_workers=5,
                    model=PREDICTION_MODEL,
                    framework_pool=pool,
                    model_pool=mpool
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

                print(f"  {cond_name:<22} Ens: {scenario_result['ensemble_probability']:.3f} | "
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
        print(f"  {cond:<22} mean={np.mean(probs):.3f} std={np.std(probs):.3f} "
              f"range=[{np.min(probs):.3f}, {np.max(probs):.3f}]")

    # Framework-level diversity analysis
    print(f"\n{'='*70}")
    print("FRAMEWORK-LEVEL PREDICTION DISTRIBUTIONS")
    print(f"{'='*70}")
    for cond in results_df['condition'].unique():
        print(f"\n  {cond}:")
        cond_agents = agent_df[agent_df['condition'] == cond]
        fw_stats = cond_agents.groupby('framework_name')['probability'].agg(['mean', 'std', 'min', 'max'])
        fw_stats = fw_stats.sort_values('mean')
        for fw_name, row_stats in fw_stats.iterrows():
            print(f"    {fw_name:<22} mean={row_stats['mean']:.3f} std={row_stats['std']:.3f} "
                  f"range=[{row_stats['min']:.3f}, {row_stats['max']:.3f}]")

    # Cross-framework spread per scenario
    print(f"\n{'='*70}")
    print("CROSS-FRAMEWORK SPREAD (per-scenario std across frameworks)")
    print(f"{'='*70}")
    for cond in results_df['condition'].unique():
        cond_agents = agent_df[agent_df['condition'] == cond]
        scenario_stds = cond_agents.groupby('scenario_id')['probability'].std()
        print(f"  {cond:<22} mean_std={scenario_stds.mean():.3f} "
              f"min_std={scenario_stds.min():.3f} max_std={scenario_stds.max():.3f}")

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
