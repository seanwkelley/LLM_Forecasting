"""
Action Prediction Experiment
==============================

Tests whether information sharding and persona+CoT bridging help predict which
actions Novaris and Tethys took, using the same prompt context as the collapse
probability experiment (initial scenario + real events + state variables, all
faction actions withheld).

Design:
- 68-action pool: Full action space from the simulation
- 5 random actions per scenario (seeded by scenario index for reproducibility)
- Binary prediction: "What is the probability that [faction] took [action]?" -> P in [0,1]
- Binary ground truth: 1 if faction took the action, 0 if not
- Brier score: (predicted - actual)^2

4 conditions (2x2 factorial):
  - baseline (generic_baseline):    Generic system prompt, full info, generic CoT
  - shard_everything (generic_shard): Generic system prompt, sharded info, generic CoT
  - persona_baseline:               Persona system prompt, full info, persona-bridged CoT
  - persona_shard:                  Persona system prompt, sharded info, persona-bridged CoT

Usage:
    # Quick test (3 scenarios, 5 agents)
    python -u forecasting/run_action_prediction_experiment.py --test

    # Full run (all 4 conditions)
    python -u forecasting/run_action_prediction_experiment.py --n-scenarios 50 --n-agents 10

    # Persona conditions only (generic already exists)
    python -u forecasting/run_action_prediction_experiment.py --n-scenarios 50 --n-agents 10 --conditions persona_baseline persona_shard

    # Test persona conditions only
    python -u forecasting/run_action_prediction_experiment.py --test --conditions persona_baseline persona_shard
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

# Prediction model (same as collapse experiment)
PREDICTION_MODEL = "deepseek/deepseek-v3.2"

# Model pool for --multi-model: each agent gets a randomly assigned model
MODEL_POOL = [
    "deepseek/deepseek-v3.2",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.5-flash",
    "mistralai/mistral-small-3.2-24b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "google/gemma-3-27b-it",
]

# =============================================================================
# ACTION POOL — 68 actions from src/enhanced_action_space.R
# =============================================================================

ACTION_POOL = [
    # Diplomatic (14)
    "diplomatic_visit",
    "peace_talks",
    "formal_peace_talks",
    "backchannel_negotiations",
    "trade_negotiation",
    "cultural_exchange",
    "humanitarian_aid",
    "mediation_offer",
    "coalition_building",
    "prisoner_exchange",
    "humanitarian_corridors",
    "public_diplomatic_initiative",
    "formal_multilateral_engagement",
    "international_observers",
    # Intelligence (9)
    "intelligence_gathering",
    "enhanced_intelligence_gathering",
    "surveillance_operation",
    "enhanced_surveillance",
    "counterintelligence",
    "share_intelligence",
    "spread_disinformation",
    "propaganda_campaign",
    "information_campaign",
    # Economic (11)
    "trade_agreement",
    "economic_sanctions",
    "targeted_sanctions",
    "financial_aid",
    "resource_embargo",
    "trade_restrictions",
    "currency_manipulation",
    "cyber_theft",
    "asset_seizure",
    "strategic_stockpiling",
    "war_bonds",
    # Military Posture (14)
    "military_buildup",
    "defensive_fortification",
    "defensive_reinforcements",
    "naval_deployment",
    "naval_patrols",
    "naval_demonstration",
    "air_patrols",
    "troop_movements",
    "military_exercises",
    "enhanced_patrols",
    "show_of_force",
    "joint_exercises",
    "arms_development",
    "reconnaissance",
    # Covert Operations (9)
    "sabotage",
    "assassination_attempt",
    "leadership_targeting",
    "regime_destabilization",
    "political_warfare",
    "proxy_support",
    "false_flag_operation",
    "cyber_attack",
    "cyber_defense",
    # Open Conflict (6)
    "border_incursion",
    "limited_strike",
    "full_scale_attack",
    "occupation",
    "blockade",
    "siege_warfare",
    # WMD (5)
    "nuclear_development",
    "chemical_weapons",
    "biological_program",
    "tactical_nuclear_use",
    "strategic_nuclear_strike",
]

assert len(ACTION_POOL) == 68, f"Expected 68 actions, got {len(ACTION_POOL)}"

# Load scenario events (actual events from simulation)
_EVENTS_FILE = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario/scenario_events.json")
_SCENARIO_EVENTS = {}
if _EVENTS_FILE.exists():
    with open(_EVENTS_FILE, 'r') as f:
        _SCENARIO_EVENTS = json.load(f)
    print(f"Loaded events for {len(_SCENARIO_EVENTS)} scenarios")

SYSTEM_PROMPT = """You are an expert geopolitical analyst specializing in predicting state actor behavior during crises.

Your task is to estimate the probability that a specific faction took a specific action, based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and observable indicators

Apply rigorous analytical reasoning. Consider both the strategic incentives for the action
and the observable evidence that would be consistent with it having been taken.

USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

SYSTEM_PROMPT_CALIBRATED = """You are an expert geopolitical analyst specializing in predicting state actor behavior during crises.

Your task is to estimate the probability that a specific faction took a specific action, based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and observable indicators

Apply rigorous analytical reasoning. Consider both the strategic incentives for the action
and the observable evidence that would be consistent with it having been taken.

CRITICAL CALIBRATION NOTE: In geopolitical crises, factions typically take only a small
subset of all possible actions. For any given action, the prior probability it was taken
is LOW — roughly 10-15%. Most actions you are asked about were NOT taken.
Start from this low base rate and only increase substantially if the evidence strongly
supports it. Probabilities below 0.2 are common and appropriate for most actions.

Output ONLY valid JSON in the exact format specified."""

SYSTEM_PROMPT_PERSONA_CALIBRATED_TEMPLATE = """{persona_description}

You are participating in a geopolitical forecasting exercise. Your task is to estimate the probability that a specific faction took a specific action, based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and observable indicators

Apply your professional expertise and analytical perspective. Consider both the strategic incentives for the action and the observable evidence that would be consistent with it having been taken.

CRITICAL CALIBRATION NOTE: In geopolitical crises, factions typically take only a small
subset of all possible actions. For any given action, the prior probability it was taken
is LOW — roughly 10-15%. Most actions you are asked about were NOT taken.
Start from this low base rate and only increase substantially if the evidence strongly
supports it. Probabilities below 0.2 are common and appropriate for most actions.

Output ONLY valid JSON in the exact format specified."""

SYSTEM_PROMPT_PERSONA_TEMPLATE = """{persona_description}

You are participating in a geopolitical forecasting exercise. Your task is to estimate the probability that a specific faction took a specific action, based on:
- Strategic context and background
- Current military, economic, and political situation
- Recent events and observable indicators

Apply your professional expertise and analytical perspective. Consider both the strategic incentives for the action and the observable evidence that would be consistent with it having been taken.

USE THE FULL PROBABILITY RANGE 0.0 to 1.0.
Do NOT cluster around 0.5 - be decisive based on the evidence.

Output ONLY valid JSON in the exact format specified."""

PERSONA_ACTION_COT_TEMPLATE = """
ANALYTICAL APPROACH:
You are analyzing this action prediction through the lens of your professional
background and expertise. At each reasoning step below, apply your specific
knowledge and strategic orientation. Where your expertise is strongest, provide
deeper analysis. Where it is limited, acknowledge uncertainty. Let your risk
tolerance calibrate how decisive your probability estimate is.

Consider:
1. Does this action align with {faction_name}'s strategic objectives given the current situation?
   - Apply your geopolitical expertise to evaluate strategic alignment and faction incentives
2. Is this action consistent with the observable state variables and events?
   - Apply your military and economic expertise to assess whether the evidence supports this action
3. Would {faction_name} have the capability and incentive to take this action at this crisis level?
   - As a {strategic_orientation} analyst, assess capability and willingness through your strategic lens
4. How common is this type of action in scenarios like this one?
   - Calibrate your base-rate estimate consistent with your risk tolerance: higher risk tolerance means more willingness to assign confident probabilities when your analysis supports it"""


def select_actions_for_scenario(scenario_idx: int, n_actions: int = 5, seed: int = 42) -> List[str]:
    """
    Deterministically select n_actions from the action pool for a given scenario.
    Pure random sampling — no regard for ground truth.

    Args:
        scenario_idx: Scenario index (0-based)
        n_actions: Number of actions to sample
        seed: Base seed (combined with scenario_idx for reproducibility)

    Returns:
        Sorted list of action names
    """
    rng = random.Random(seed + scenario_idx)
    return sorted(rng.sample(ACTION_POOL, n_actions))


def select_actions_balanced(
    scenario_id: str,
    n_actions: int = 5,
    n_taken: int = 2,
    seed: int = 42
) -> List[str]:
    """
    Select a balanced mix of taken and not-taken actions for a scenario.

    Guarantees n_taken actions that were actually taken (by either faction)
    and (n_actions - n_taken) that were not, creating a balanced evaluation
    set that tests discrimination rather than base-rate knowledge.

    Args:
        scenario_id: Scenario identifier (e.g., "scenario_001")
        n_actions: Total actions to select
        n_taken: How many should be actions that were actually taken
        seed: Base seed for reproducibility

    Returns:
        Sorted list of action names
    """
    events_data = _SCENARIO_EVENTS.get(scenario_id, {})
    novaris_actions = set(events_data.get('novaris_actions', []))
    tethys_actions = set(events_data.get('tethys_actions', []))
    all_taken = (novaris_actions | tethys_actions) & set(ACTION_POOL)
    all_not_taken = set(ACTION_POOL) - all_taken

    scenario_num = int(scenario_id.split('_')[-1])
    rng = random.Random(seed + scenario_num)

    # Sample from taken and not-taken pools
    n_from_taken = min(n_taken, len(all_taken))
    n_from_not_taken = n_actions - n_from_taken

    taken_sample = rng.sample(sorted(all_taken), n_from_taken)
    not_taken_sample = rng.sample(sorted(all_not_taken), min(n_from_not_taken, len(all_not_taken)))

    return sorted(taken_sample + not_taken_sample)


def build_persona_action_system_prompt(persona: SimplifiedProfile) -> str:
    """Build a system prompt embedding the persona description for action prediction."""
    return SYSTEM_PROMPT_PERSONA_TEMPLATE.format(
        persona_description=persona.to_natural_language()
    )


def create_action_prompt_persona(
    scenario_params: pd.Series,
    action_name: str,
    faction_name: str,
    persona: SimplifiedProfile
) -> Tuple[str, str, str, str]:
    """
    Create prompt sections for a persona-bridged action prediction query.

    Same data sections as create_action_prompt(), but with persona-bridged CoT
    instructions that connect each reasoning step to the persona's expertise.

    Args:
        scenario_params: Row from merged scenarios+ground_truth DataFrame
        action_name: The action to predict (e.g., "military_buildup")
        faction_name: "Novaris" or "Tethys"
        persona: SimplifiedProfile for this agent

    Returns:
        (initial_scenario, historical_summary, current_period_data, instructions)
    """
    # Reuse the generic prompt builder for data sections
    initial_scenario, historical_summary, current_period_data, _ = \
        create_action_prompt(scenario_params, action_name, faction_name)

    # Build persona-bridged instructions
    action_display = action_name.replace('_', ' ').title()
    faction_full = ("The People's Federation of Novaris" if faction_name == "Novaris"
                    else "The Democratic Commonwealth of Tethys")

    persona_cot = PERSONA_ACTION_COT_TEMPLATE.format(
        faction_name=faction_name,
        strategic_orientation=persona.strategic_orientation
    )

    instructions = f"""
{'='*80}
YOUR PREDICTION TASK
{'='*80}

Based on the situation described above, estimate the probability that
{faction_full} ({faction_name}) took the following action during Period 1:

    ACTION: {action_display} ({action_name})

{persona_cot}

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "rationale": "2-3 sentence explanation of why {faction_name} would or would not have taken this action"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
- Probability must be between 0.0 and 1.0
- USE THE FULL RANGE: 0.0 means certainly did NOT take this action, 1.0 means certainly DID
- Don't default to 0.5 - use the evidence to form a decisive estimate
"""
    return initial_scenario, historical_summary, current_period_data, instructions


def create_action_prompt(
    scenario_params: pd.Series,
    action_name: str,
    faction_name: str
) -> Tuple[str, str, str, str]:
    """
    Create prompt sections for an action prediction query.

    Uses the same context as the collapse experiment (initial scenario + events +
    state variables, all faction actions withheld), but with action-prediction
    instructions instead of collapse-prediction instructions.

    Args:
        scenario_params: Row from merged scenarios+ground_truth DataFrame
        action_name: The action to predict (e.g., "military_buildup")
        faction_name: "Novaris" or "Tethys"

    Returns:
        (initial_scenario, historical_summary, current_period_data, instructions)
    """
    initial_scenario = INITIAL_SCENARIO
    historical_summary = ""

    # Build events section from actual scenario data (same as collapse experiment)
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

    # External actor actions (observable, not what we're predicting)
    ext_actor_text = ""
    ext_actions = events_data.get('external_actor_actions', [])
    if ext_actions:
        for ea in ext_actions:
            faction = ea.get('faction', 'unknown').replace('_', ' ').title()
            action = ea.get('action', 'unknown').replace('_', ' ')
            ext_actor_text += f"  - {faction}: {action}\n"
    else:
        ext_actor_text = "  (No external actor actions recorded)\n"

    # Current period data with state variables (same as collapse experiment)
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

    # Action-specific display name
    action_display = action_name.replace('_', ' ').title()
    faction_full = ("The People's Federation of Novaris" if faction_name == "Novaris"
                    else "The Democratic Commonwealth of Tethys")

    instructions = f"""
{'='*80}
YOUR PREDICTION TASK
{'='*80}

Based on the situation described above, estimate the probability that
{faction_full} ({faction_name}) took the following action during Period 1:

    ACTION: {action_display} ({action_name})

Consider:
1. Does this action align with {faction_name}'s strategic objectives given the current situation?
2. Is this action consistent with the observable state variables and events?
3. Would {faction_name} have the capability and incentive to take this action at this crisis level?
4. How common is this type of action in scenarios like this one?

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "rationale": "2-3 sentence explanation of why {faction_name} would or would not have taken this action"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
- Probability must be between 0.0 and 1.0
- USE THE FULL RANGE: 0.0 means certainly did NOT take this action, 1.0 means certainly DID
- Don't default to 0.5 - use the evidence to form a decisive estimate
"""

    return initial_scenario, historical_summary, current_period_data, instructions


CALIBRATED_COT_TEMPLATE = """Consider:
1. What is the base rate for this type of action? Most specific actions are NOT taken in any
   given crisis period — the prior probability is roughly 10-15%. Start here.
2. Does this action align with {faction_name}'s strategic objectives given the current situation?
   - Only adjust upward if there is STRONG, SPECIFIC evidence this action fits the faction's strategy
3. Is this action consistent with the observable state variables and events?
   - Look for concrete indicators. Absence of evidence should keep the probability low.
4. Would {faction_name} have the capability and incentive to take this action at this crisis level?
   - Even capable factions only execute a handful of actions per period
5. How common is this type of action in scenarios like this one?
   - Routine/defensive actions may be slightly more likely; escalatory/extreme actions are rare"""

CALIBRATED_PERSONA_COT_TEMPLATE = """
ANALYTICAL APPROACH:
You are analyzing this action prediction through the lens of your professional
background and expertise. At each reasoning step below, apply your specific
knowledge and strategic orientation. Where your expertise is strongest, provide
deeper analysis. Where it is limited, acknowledge uncertainty. Let your risk
tolerance calibrate how decisive your probability estimate is.

IMPORTANT: In geopolitical crises, factions take only a small subset of possible actions
each period. The base rate for any specific action being taken is roughly 10-15%.
Start from this low prior and adjust based on the strength of evidence.

Consider:
1. What is the base rate for this type of action? Start from the prior of ~10-15%.
   - Apply your geopolitical expertise: is this a common or rare action type?
2. Does this action align with {faction_name}'s strategic objectives given the current situation?
   - Apply your expertise to evaluate whether the evidence SPECIFICALLY supports this action
3. Is this action consistent with the observable state variables and events?
   - Apply your military and economic expertise to assess concrete indicators
4. Would {faction_name} have the capability and incentive to take this action at this crisis level?
   - As a {strategic_orientation} analyst, assess capability through your strategic lens
5. Synthesize: given the low base rate, does the cumulative evidence justify raising the probability?
   - Calibrate consistent with your risk tolerance, but remember most actions are NOT taken"""

CALIBRATED_OUTPUT_INSTRUCTIONS = """OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "rationale": "2-3 sentence explanation of why {faction_name} would or would not have taken this action"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
- Probability must be between 0.0 and 1.0
- Remember: most actions are NOT taken. Probabilities below 0.2 are common and appropriate.
- Only assign probabilities above 0.5 when there is strong, specific evidence for this action
- 0.0 means certainly did NOT take this action, 1.0 means certainly DID"""


def create_action_prompt_calibrated(
    scenario_params: pd.Series,
    action_name: str,
    faction_name: str
) -> Tuple[str, str, str, str]:
    """
    Create prompt sections for a calibrated generic action prediction query.
    Same data as create_action_prompt() but with base-rate-aware instructions.
    """
    # Reuse the generic prompt builder for data sections
    initial_scenario, historical_summary, current_period_data, _ = \
        create_action_prompt(scenario_params, action_name, faction_name)

    action_display = action_name.replace('_', ' ').title()
    faction_full = ("The People's Federation of Novaris" if faction_name == "Novaris"
                    else "The Democratic Commonwealth of Tethys")

    cot = CALIBRATED_COT_TEMPLATE.format(faction_name=faction_name)
    output_fmt = CALIBRATED_OUTPUT_INSTRUCTIONS.format(faction_name=faction_name)

    instructions = f"""
{'='*80}
YOUR PREDICTION TASK
{'='*80}

Based on the situation described above, estimate the probability that
{faction_full} ({faction_name}) took the following action during Period 1:

    ACTION: {action_display} ({action_name})

{cot}

{output_fmt}
"""
    return initial_scenario, historical_summary, current_period_data, instructions


def create_action_prompt_calibrated_persona(
    scenario_params: pd.Series,
    action_name: str,
    faction_name: str,
    persona: 'SimplifiedProfile'
) -> Tuple[str, str, str, str]:
    """
    Create prompt sections for a calibrated persona-bridged action prediction query.
    """
    # Reuse the generic prompt builder for data sections
    initial_scenario, historical_summary, current_period_data, _ = \
        create_action_prompt(scenario_params, action_name, faction_name)

    action_display = action_name.replace('_', ' ').title()
    faction_full = ("The People's Federation of Novaris" if faction_name == "Novaris"
                    else "The Democratic Commonwealth of Tethys")

    persona_cot = CALIBRATED_PERSONA_COT_TEMPLATE.format(
        faction_name=faction_name,
        strategic_orientation=persona.strategic_orientation
    )
    output_fmt = CALIBRATED_OUTPUT_INSTRUCTIONS.format(faction_name=faction_name)

    instructions = f"""
{'='*80}
YOUR PREDICTION TASK
{'='*80}

Based on the situation described above, estimate the probability that
{faction_full} ({faction_name}) took the following action during Period 1:

    ACTION: {action_display} ({action_name})

{persona_cot}

{output_fmt}
"""
    return initial_scenario, historical_summary, current_period_data, instructions


def build_calibrated_persona_system_prompt(persona: 'SimplifiedProfile') -> str:
    """Build a calibrated system prompt embedding the persona description."""
    return SYSTEM_PROMPT_PERSONA_CALIBRATED_TEMPLATE.format(
        persona_description=persona.to_natural_language()
    )


def run_single_action_prediction(
    initial_scenario: str,
    historical_summary: str,
    current_period_data: str,
    instructions: str,
    sharding_strategy: str,
    information_fraction: float,
    agent_id: int,
    model: str = PREDICTION_MODEL,
    system_prompt: str = None
) -> Dict:
    """Run a single agent's action prediction."""
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

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
            return {'probability': 0.5, 'rationale': 'Error', '_fallback': 'api_error'}

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
        return {'probability': 0.5, 'rationale': 'JSON parse error', '_fallback': 'json_error'}
    except Exception as e:
        return {'probability': 0.5, 'rationale': str(e), '_fallback': 'exception'}


def run_action_scenario(
    scenario_id: str,
    scenario_params: pd.Series,
    actions: List[str],
    condition_name: str,
    sharding_strategy: str,
    n_agents: int,
    ground_truth_actions: Dict[str, List[str]],
    max_workers: int = 5,
    model: str = PREDICTION_MODEL,
    all_personas: Optional[List[SimplifiedProfile]] = None,
    framework_pool: List[Dict] = None,
    model_pool: List[str] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Run N agents for one scenario/condition across all selected actions and factions.

    Args:
        scenario_id: Scenario identifier
        scenario_params: Row from merged DataFrame
        actions: List of action names to predict
        condition_name: Condition label (e.g., "baseline", "persona_baseline")
        sharding_strategy: Sharding strategy name
        n_agents: Number of agents per action/faction
        ground_truth_actions: Dict with 'novaris' and 'tethys' lists of actual actions
        max_workers: Max parallel API calls
        model: Model name
        all_personas: Full persona pool (required for persona conditions)

    Returns:
        (scenario_results, agent_details) where:
        - scenario_results: List of result dicts (one per action x faction)
        - agent_details: List of agent-level detail dicts (persona conditions only)
    """
    results = []
    agent_details = []

    is_persona = condition_name.startswith("persona") or condition_name == "calibrated_persona"
    is_calibrated = condition_name.startswith("calibrated")

    # Persona assignment: deterministic per (scenario_id, condition_name)
    # Same persona set for all actions x factions within this scenario-condition
    # For calibrated_persona, use same seed pattern as persona_baseline for comparability
    if is_persona and all_personas:
        persona_seed_key = condition_name
        if condition_name == "calibrated_persona":
            persona_seed_key = "persona_baseline"  # same personas as persona_baseline
        seed = hash(f"{scenario_id}_{persona_seed_key}") % (2**31)
        rng = random.Random(seed)
        selected_personas = rng.sample(all_personas, min(n_agents, len(all_personas)))
    else:
        selected_personas = [None] * n_agents

    import hashlib as _hashlib

    # Create information distribution (shared across all actions for this scenario-condition)
    info_fractions = create_information_distribution(n_agents)

    # Sample frameworks from pool if provided (one set per scenario-condition)
    if framework_pool is not None:
        from forecasting.framework_pool import sample_action_frameworks
        fw_seed = f"{scenario_id}_{condition_name}"
        sampled_frameworks = sample_action_frameworks(n=n_agents, seed=fw_seed)
    else:
        sampled_frameworks = None

    # Pre-assign per-agent models if model_pool provided
    agent_models = []
    for i in range(n_agents):
        if model_pool is not None:
            h = _hashlib.sha256(f"{scenario_id}_{condition_name}_{i}".encode()).hexdigest()
            idx = int(h, 16) % len(model_pool)
            agent_models.append(model_pool[idx])
        else:
            agent_models.append(model)

    for faction_name in ["Novaris", "Tethys"]:
        faction_key = faction_name.lower()
        actual_actions = ground_truth_actions.get(faction_key, [])

        for action in actions:
            # Build per-agent configs for this action/faction
            agent_configs = []
            for i in range(n_agents):
                persona = selected_personas[i]
                info_frac = info_fractions[i] if "shard" in condition_name else 1.0
                fw = sampled_frameworks[i] if sampled_frameworks else None

                if fw is not None:
                    # Framework pool mode: use composed system prompt + inject CoT
                    sys_prompt = fw['system_prompt']
                    # Get base data sections from generic prompt builder
                    init_scen, hist, cpd, base_instr = create_action_prompt(
                        scenario_params, action, faction_name)
                    # Replace the generic CoT with framework-composed CoT
                    action_display = action.replace('_', ' ').title()
                    faction_full = ("The People's Federation of Novaris" if faction_name == "Novaris"
                                    else "The Democratic Commonwealth of Tethys")
                    instr = f"""
{'='*80}
YOUR PREDICTION TASK
{'='*80}

Based on the situation described above, estimate the probability that
{faction_full} ({faction_name}) took the following action during Period 1:

    ACTION: {action_display} ({action})

{fw['cot_instructions']}

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "rationale": "2-3 sentence explanation of why {faction_name} would or would not have taken this action"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
- Probability must be between 0.0 and 1.0
- USE THE FULL RANGE: 0.0 means certainly did NOT take this action, 1.0 means certainly DID
- Don't default to 0.5 - use the evidence to form a decisive estimate
"""
                elif is_calibrated and is_persona and persona is not None:
                    # Calibrated + persona
                    sys_prompt = build_calibrated_persona_system_prompt(persona)
                    _, hist, cpd, instr = create_action_prompt_calibrated_persona(
                        scenario_params, action, faction_name, persona)
                    init_scen = INITIAL_SCENARIO
                elif is_calibrated and not is_persona:
                    # Calibrated generic
                    sys_prompt = SYSTEM_PROMPT_CALIBRATED
                    init_scen, hist, cpd, instr = create_action_prompt_calibrated(
                        scenario_params, action, faction_name)
                elif is_persona and persona is not None:
                    sys_prompt = build_persona_action_system_prompt(persona)
                    _, hist, cpd, instr = create_action_prompt_persona(
                        scenario_params, action, faction_name, persona)
                    # Get initial_scenario from generic (same data)
                    init_scen = INITIAL_SCENARIO
                else:
                    sys_prompt = SYSTEM_PROMPT
                    init_scen, hist, cpd, instr = create_action_prompt(
                        scenario_params, action, faction_name)

                agent_configs.append({
                    'agent_id': i,
                    'persona': persona,
                    'framework': fw,
                    'system_prompt': sys_prompt,
                    'initial_scenario': init_scen,
                    'historical_summary': hist,
                    'current_period_data': cpd,
                    'instructions': instr,
                    'information_fraction': info_frac,
                    'model': agent_models[i],
                })

            # Run predictions in parallel
            start_time = time.time()
            predictions = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for cfg in agent_configs:
                    if cfg['agent_id'] > 0 and cfg['agent_id'] % 10 == 0:
                        time.sleep(0.5)

                    future = executor.submit(
                        run_single_action_prediction,
                        cfg['initial_scenario'],
                        cfg['historical_summary'],
                        cfg['current_period_data'],
                        cfg['instructions'],
                        sharding_strategy,
                        cfg['information_fraction'],
                        cfg['agent_id'],
                        cfg['model'],
                        cfg['system_prompt']
                    )
                    futures[future] = cfg

                for future in concurrent.futures.as_completed(futures):
                    cfg = futures[future]
                    try:
                        pred = future.result()
                    except Exception:
                        pred = {'probability': 0.5, 'rationale': 'Error', '_fallback': 'future_exception'}
                    predictions.append(pred)

                    # Record agent-level details
                    fw = cfg.get('framework')
                    persona = cfg['persona']
                    detail = {
                        'scenario_id': scenario_id,
                        'condition': condition_name,
                        'faction': faction_name,
                        'action': action,
                        'agent_id': cfg['agent_id'],
                        'model': cfg['model'],
                        'framework_name': fw['name'] if fw else '',
                        'method': fw['method'] if fw else '',
                        'lens': fw['lens'] if fw else '',
                        'focus': fw['focus'] if fw else '',
                        'bias': fw['bias'] if fw else '',
                        'persona_id': persona.persona_id if persona else None,
                        'strategic_orientation': persona.strategic_orientation if persona else None,
                        'risk_tolerance': persona.risk_tolerance if persona else None,
                        'information_fraction': cfg['information_fraction'],
                        'probability': pred.get('probability', 0.5),
                        'rationale': pred.get('rationale', ''),
                        'fallback_type': pred.get('_fallback', None),
                    }
                    # Always record agent details when using pool/multi-model,
                    # or for persona conditions
                    if framework_pool is not None or model_pool is not None or is_persona:
                        agent_details.append(detail)

            duration = time.time() - start_time

            # Ensemble
            probabilities = [p.get('probability', 0.5) for p in predictions]
            ensemble_prob = np.mean(probabilities)

            # Binary ground truth
            ground_truth = 1 if action in actual_actions else 0

            # Brier score
            brier_score = (ensemble_prob - ground_truth) ** 2

            # Fallback tracking
            fallback_count = sum(1 for p in predictions if '_fallback' in p)

            results.append({
                'scenario_id': scenario_id,
                'condition': condition_name,
                'faction': faction_name,
                'action': action,
                'n_agents': n_agents,
                'ensemble_probability': ensemble_prob,
                'ground_truth': ground_truth,
                'brier_score': brier_score,
                'probability_std': np.std(probabilities),
                'duration_seconds': duration,
                'fallback_count': fallback_count,
            })

    return results, agent_details


def compute_action_base_rates(
    scenarios_data: pd.DataFrame,
    selected_actions_per_scenario: Dict[str, List[str]]
) -> Dict[str, float]:
    """
    Compute the base rate of each action across all scenarios where it was selected.

    Args:
        scenarios_data: Merged DataFrame with ground truth
        selected_actions_per_scenario: Dict mapping scenario_id -> list of selected actions

    Returns:
        Dict mapping action_name -> base rate (fraction of scenario/faction pairs where action was taken)
    """
    action_counts = {}   # action -> [taken_count, total_count]

    for _, row in scenarios_data.iterrows():
        scenario_id = row['scenario_id']
        if scenario_id not in selected_actions_per_scenario:
            continue

        actions = selected_actions_per_scenario[scenario_id]
        events_data = _SCENARIO_EVENTS.get(scenario_id, {})
        novaris_actions = events_data.get('novaris_actions', [])
        tethys_actions = events_data.get('tethys_actions', [])

        for action in actions:
            if action not in action_counts:
                action_counts[action] = [0, 0]

            # Novaris
            action_counts[action][1] += 1
            if action in novaris_actions:
                action_counts[action][0] += 1

            # Tethys
            action_counts[action][1] += 1
            if action in tethys_actions:
                action_counts[action][0] += 1

    return {a: counts[0] / counts[1] if counts[1] > 0 else 0.0
            for a, counts in action_counts.items()}


def run_statistical_tests(results_df: pd.DataFrame):
    """Run pairwise statistical tests and interaction test for action predictions."""
    from scipy import stats as scipy_stats

    print(f"\n{'='*70}")
    print("STATISTICAL SIGNIFICANCE TESTS")
    print(f"{'='*70}")

    # Define key comparison pairs (same structure as collapse experiment)
    comparisons = [
        ("baseline", "persona_baseline"),
        ("shard_everything", "persona_shard"),
        ("baseline", "shard_everything"),
        ("persona_baseline", "persona_shard"),
        ("baseline", "persona_shard"),
        ("shard_everything", "persona_baseline"),
    ]

    available_conditions = set(results_df['condition'].unique())

    for c1, c2 in comparisons:
        if c1 not in available_conditions or c2 not in available_conditions:
            continue

        df1 = results_df[results_df['condition'] == c1].copy()
        df2 = results_df[results_df['condition'] == c2].copy()

        # Create pairing key (scenario x action x faction)
        df1['pair_key'] = df1['scenario_id'] + '|' + df1['action'] + '|' + df1['faction']
        df2['pair_key'] = df2['scenario_id'] + '|' + df2['action'] + '|' + df2['faction']

        merged = df1[['pair_key', 'brier_score']].merge(
            df2[['pair_key', 'brier_score']],
            on='pair_key', suffixes=(f'_{c1}', f'_{c2}')
        )

        if len(merged) < 3:
            print(f"\n  {c1} vs {c2}: Too few paired observations ({len(merged)})")
            continue

        bs_1 = merged[f'brier_score_{c1}'].values
        bs_2 = merged[f'brier_score_{c2}'].values
        diff = bs_1 - bs_2

        # Paired t-test
        t_stat, t_pval = scipy_stats.ttest_rel(bs_1, bs_2)

        # Wilcoxon signed-rank test
        try:
            w_stat, w_pval = scipy_stats.wilcoxon(bs_1, bs_2)
        except ValueError:
            w_stat, w_pval = float('nan'), float('nan')

        # Cohen's d for paired samples
        d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0

        mean_1 = np.mean(bs_1)
        mean_2 = np.mean(bs_2)
        pct_change = ((mean_2 - mean_1) / mean_1) * 100 if mean_1 > 0 else 0

        sig_t = '***' if t_pval < 0.001 else '**' if t_pval < 0.01 else '*' if t_pval < 0.05 else 'ns'
        sig_w = '***' if w_pval < 0.001 else '**' if w_pval < 0.01 else '*' if w_pval < 0.05 else 'ns'
        d_label = 'large' if abs(d) > 0.8 else 'medium' if abs(d) > 0.5 else 'small' if abs(d) > 0.2 else 'negligible'

        print(f"\n  {c1} vs {c2} (N={len(merged)} paired observations)")
        print(f"    Mean Brier: {mean_1:.4f} vs {mean_2:.4f} ({pct_change:+.1f}%)")
        print(f"    Paired t-test:   t={t_stat:.3f}, p={t_pval:.4f} {sig_t}")
        print(f"    Wilcoxon test:   W={w_stat:.1f}, p={w_pval:.4f} {sig_w}")
        print(f"    Cohen's d:       {d:.3f} ({d_label})")
        print(f"    Obs where {c1} better: {np.sum(diff < 0)}/{len(merged)}")
        print(f"    Obs where {c2} better: {np.sum(diff > 0)}/{len(merged)}")

    # Interaction test: does persona improvement differ under sharding vs baseline?
    needed = {"baseline", "persona_baseline", "shard_everything", "persona_shard"}
    if needed.issubset(available_conditions):
        print(f"\n{'='*70}")
        print("INTERACTION TEST: Persona effect x Sharding")
        print(f"{'='*70}")

        # Build per-observation (scenario x action x faction) Brier scores
        def _get_brier_map(cond):
            sub = results_df[results_df['condition'] == cond].copy()
            sub['pair_key'] = sub['scenario_id'] + '|' + sub['action'] + '|' + sub['faction']
            return sub.set_index('pair_key')['brier_score']

        gb = _get_brier_map('baseline')
        pb = _get_brier_map('persona_baseline')
        gs = _get_brier_map('shard_everything')
        ps = _get_brier_map('persona_shard')

        common = gb.index.intersection(pb.index).intersection(gs.index).intersection(ps.index)

        if len(common) >= 3:
            # Persona improvement under baseline = (generic_baseline BS) - (persona_baseline BS)
            improvement_baseline = gb.loc[common].values - pb.loc[common].values
            # Persona improvement under sharding = (generic_shard BS) - (persona_shard BS)
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
            print(f"  Too few common observations ({len(common)}) for interaction test")


def main():
    parser = argparse.ArgumentParser(description="Action Prediction Experiment")
    parser.add_argument("--test", action="store_true", help="Quick test: 3 scenarios, 5 agents")
    parser.add_argument("--pool", action="store_true",
                        help="Use composable framework pool (1000 combinations) for agent diversity")
    parser.add_argument("--multi-model", action="store_true",
                        help="Assign each agent a randomly selected model from MODEL_POOL")
    parser.add_argument("--n-scenarios", type=int, default=None, help="Number of scenarios to process")
    parser.add_argument("--n-agents", type=int, default=None, help="Number of agents per action/faction/condition")
    parser.add_argument("--balanced", action="store_true",
                        help="Select balanced mix of taken/not-taken actions (2 taken + 3 not-taken per scenario)")
    parser.add_argument("--conditions", nargs="+", default=None,
                        help="Conditions to run (baseline, shard_everything, pool_baseline, pool_shard, persona_baseline, persona_shard, calibrated_baseline, calibrated_persona)")
    parser.add_argument("--start-scenario", type=int, default=1,
                        help="Scenario number to start from (1-based, default 1)")
    args = parser.parse_args()

    # Configuration
    data_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario")
    output_dir = Path("D:/Northeastern/LLM_Forecasting/experiment_results/action_prediction")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load composable pool if requested
    use_pool = args.pool
    pool = None
    if use_pool:
        from forecasting.framework_pool import generate_action_pool
        pool = generate_action_pool()

    # Multi-model setup
    use_multi_model = args.multi_model
    mpool = MODEL_POOL if use_multi_model else None

    # All condition definitions: (condition_name -> sharding_strategy)
    ALL_CONDITIONS = {
        "baseline": "none",
        "shard_everything": "shard_everything",
        "pool_baseline": "none",
        "pool_shard": "shard_everything",
        "persona_baseline": "none",
        "persona_shard": "shard_everything",
        "calibrated_baseline": "none",
        "calibrated_persona": "none",
    }

    if args.test:
        n_scenarios = 3
        n_agents = args.n_agents or 5
        if args.conditions:
            conditions = [(c, ALL_CONDITIONS[c]) for c in args.conditions]
        elif use_pool:
            conditions = [
                ("pool_baseline", "none"),
                ("pool_shard", "shard_everything"),
            ]
        else:
            conditions = [
                ("baseline", "none"),
                ("shard_everything", "shard_everything"),
            ]
    else:
        n_scenarios = args.n_scenarios or 50
        n_agents = args.n_agents or 10
        if args.conditions:
            conditions = [(name, ALL_CONDITIONS[name]) for name in args.conditions]
        else:
            conditions = list(ALL_CONDITIONS.items())

    n_actions_per_scenario = 5

    # Determine if we need personas
    has_persona_conditions = any(c[0].startswith("persona") or c[0] == "calibrated_persona" for c in conditions)

    print("=" * 70)
    print("ACTION PREDICTION EXPERIMENT")
    print("=" * 70)
    print(f"Scenarios: {n_scenarios}")
    print(f"Actions per scenario: {n_actions_per_scenario}" +
          (f" (BALANCED: 2 taken + 3 not-taken)" if use_balanced else " (random)"))
    print(f"Factions: Novaris, Tethys")
    print(f"Agents per action/faction/condition: {n_agents}")
    print(f"Conditions: {[c[0] for c in conditions]}")
    if use_pool:
        print(f"Frameworks: COMPOSABLE POOL ({len(pool)} combinations, sampling {n_agents} per scenario)")
    if use_multi_model:
        print(f"Models:     MULTI-MODEL POOL ({len(MODEL_POOL)} models, per-agent assignment)")
        for m in MODEL_POOL:
            print(f"              - {m}")
    else:
        print(f"Model: {PREDICTION_MODEL}")
    print(f"Total API calls: {n_scenarios} x {n_actions_per_scenario} x 2 x {len(conditions)} x {n_agents} = "
          f"{n_scenarios * n_actions_per_scenario * 2 * len(conditions) * n_agents}")
    if args.test:
        print("[TEST MODE]")
    print("=" * 70)

    # Load data
    print("\nLoading scenario data...")
    scenarios = pd.read_csv(data_dir / "scenarios.csv")
    ground_truth = pd.read_csv(data_dir / "ground_truth.csv")

    print(f"Loaded {len(scenarios)} scenarios")
    print(f"Ground truth for {len(ground_truth)} scenarios")

    # Merge
    data = scenarios.merge(ground_truth, on='scenario_id', how='inner')

    # Limit to requested number
    if n_scenarios < len(data):
        data = data.head(n_scenarios)
        print(f"Limited to first {n_scenarios} scenarios")

    # Skip scenarios before start-scenario
    start_idx = args.start_scenario - 1  # convert to 0-based
    if start_idx > 0:
        data = data.iloc[start_idx:]
        print(f"Starting from scenario {args.start_scenario} (skipping first {start_idx})")

    # Load persona pool if needed
    all_personas = None
    if has_persona_conditions:
        print("\nLoading persona pool...")
        all_personas = load_simplified_personas()
        orientations = [p.strategic_orientation for p in all_personas]
        risk_vals = [p.risk_tolerance for p in all_personas]
        print(f"  Orientations: hawkish={orientations.count('hawkish')}, "
              f"dovish={orientations.count('dovish')}, "
              f"pragmatic={orientations.count('pragmatic')}")
        print(f"  Risk tolerance: mean={np.mean(risk_vals):.1f}, "
              f"std={np.std(risk_vals):.1f}, "
              f"range=[{min(risk_vals)}, {max(risk_vals)}]")

    # Pre-select actions for all scenarios and compute base rates
    use_balanced = args.balanced
    selected_actions_per_scenario = {}
    for idx, row in data.iterrows():
        scenario_id = row['scenario_id']
        scenario_num = int(scenario_id.split('_')[-1])
        if use_balanced:
            actions = select_actions_balanced(scenario_id, n_actions_per_scenario, n_taken=2)
        else:
            actions = select_actions_for_scenario(scenario_num, n_actions_per_scenario)
        selected_actions_per_scenario[scenario_id] = actions

    base_rates = compute_action_base_rates(data, selected_actions_per_scenario)

    print(f"\nAction base rates (across selected scenarios):")
    for action, rate in sorted(base_rates.items(), key=lambda x: -x[1]):
        print(f"  {action:<40s} {rate:.3f}")

    # Run experiments
    print(f"\nRunning {len(data)} scenarios x {len(conditions)} conditions x "
          f"{n_actions_per_scenario} actions x 2 factions...")
    all_results = []
    all_agent_details = []

    # Set up incremental CSV save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"action_prediction_results_{timestamp}.csv"
    agent_file = output_dir / f"action_prediction_agent_details_{timestamp}.csv"
    csv_header_written = False
    agent_csv_header_written = False

    total_to_run = len(data)
    for run_num, (idx, row) in enumerate(data.iterrows(), 1):
        scenario_id = row['scenario_id']
        actions = selected_actions_per_scenario[scenario_id]

        # Get ground truth actions from scenario_events.json
        events_data = _SCENARIO_EVENTS.get(scenario_id, {})
        gt_actions = {
            'novaris': events_data.get('novaris_actions', []),
            'tethys': events_data.get('tethys_actions', []),
        }

        print(f"\n[{run_num}/{total_to_run}] {scenario_id}")
        print(f"  Actions: {actions}")
        print(f"  Novaris GT: {gt_actions['novaris']}")
        print(f"  Tethys GT:  {gt_actions['tethys']}")

        for cond_name, strategy in conditions:
            try:
                # Use pool for pool_* conditions or when --pool flag is set
                use_fw_pool = pool if (use_pool or cond_name.startswith("pool_")) else None

                results, agent_details = run_action_scenario(
                    scenario_id=scenario_id,
                    scenario_params=row,
                    actions=actions,
                    condition_name=cond_name,
                    sharding_strategy=strategy,
                    n_agents=n_agents,
                    ground_truth_actions=gt_actions,
                    max_workers=5,
                    model=PREDICTION_MODEL,
                    all_personas=all_personas,
                    framework_pool=use_fw_pool,
                    model_pool=mpool
                )

                # Add base rates to results
                for r in results:
                    r['action_base_rate'] = base_rates.get(r['action'], 0.0)

                all_results.extend(results)
                all_agent_details.extend(agent_details)

                # Incremental save: scenario-level
                batch_df = pd.DataFrame(results)
                batch_df.to_csv(results_file, mode='a', index=False,
                                header=not csv_header_written)
                csv_header_written = True

                # Incremental save: agent-level (persona conditions only)
                if agent_details:
                    agent_batch_df = pd.DataFrame(agent_details)
                    agent_batch_df.to_csv(agent_file, mode='a', index=False,
                                          header=not agent_csv_header_written)
                    agent_csv_header_written = True

                # Print per-condition summary
                brier_scores = [r['brier_score'] for r in results]
                fallbacks = sum(r['fallback_count'] for r in results)
                total_agents = sum(r['n_agents'] for r in results)
                print(f"  {cond_name:<20} Mean Brier: {np.mean(brier_scores):.4f} | "
                      f"Fallbacks: {fallbacks}/{total_agents}")

            except Exception as e:
                print(f"  [ERROR] {cond_name} failed: {e}")

    # Final full save (overwrites incremental file to ensure consistency)
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(results_file, index=False)

    if all_agent_details:
        agent_df = pd.DataFrame(all_agent_details)
        agent_df.to_csv(agent_file, index=False)

    # ==========================================================================
    # Summary statistics
    # ==========================================================================
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")
    print(f"Total rows: {len(results_df)}")
    print(f"Expected: {len(data)} scenarios x {n_actions_per_scenario} actions x 2 factions x {len(conditions)} conditions = "
          f"{len(data) * n_actions_per_scenario * 2 * len(conditions)}")

    # Mean Brier by condition
    print(f"\n--- Mean Brier Score by Condition ---")
    summary_condition = results_df.groupby('condition').agg({
        'brier_score': ['mean', 'std', 'min', 'max', 'count'],
        'ensemble_probability': 'mean',
        'ground_truth': 'mean',
        'fallback_count': 'sum',
    }).round(4)
    print(summary_condition)

    # Mean Brier by condition x faction
    print(f"\n--- Mean Brier Score by Condition x Faction ---")
    summary_faction = results_df.groupby(['condition', 'faction']).agg({
        'brier_score': ['mean', 'std', 'count'],
        'ground_truth': 'mean',
    }).round(4)
    print(summary_faction)

    # Base rate summary
    print(f"\n--- Ground Truth Base Rate ---")
    overall_base_rate = results_df['ground_truth'].mean()
    print(f"  Overall: {overall_base_rate:.3f}")
    for faction in ['Novaris', 'Tethys']:
        faction_rate = results_df[results_df['faction'] == faction]['ground_truth'].mean()
        print(f"  {faction}: {faction_rate:.3f}")

    # Prediction diversity summary
    if all_agent_details:
        agent_df = pd.DataFrame(all_agent_details)
        print(f"\n{'='*70}")
        print("PREDICTION DIVERSITY (agent-level, persona conditions)")
        print(f"{'='*70}")
        for cond in agent_df['condition'].unique():
            cond_agents = agent_df[agent_df['condition'] == cond]
            probs = cond_agents['probability'].values
            print(f"  {cond:<20} mean={np.mean(probs):.3f} std={np.std(probs):.3f} "
                  f"range=[{np.min(probs):.3f}, {np.max(probs):.3f}]")

        # Persona attribute distributions
        persona_agents = agent_df[agent_df['persona_id'].notna()]
        if len(persona_agents) > 0:
            print(f"\n{'='*70}")
            print("PERSONA ATTRIBUTE DISTRIBUTIONS (persona conditions only)")
            print(f"{'='*70}")
            orient_counts = persona_agents['strategic_orientation'].value_counts()
            print(f"  Orientations: {dict(orient_counts)}")
            rt = persona_agents['risk_tolerance'].dropna()
            print(f"  Risk tolerance: mean={rt.mean():.1f}, std={rt.std():.1f}")

    # ==========================================================================
    # Statistical significance tests
    # ==========================================================================
    condition_names = results_df['condition'].unique()
    if len(condition_names) >= 2:
        run_statistical_tests(results_df)

    # Save summary
    summary_file = output_dir / f"action_prediction_summary_{timestamp}.csv"
    summary_condition.to_csv(summary_file)

    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE")
    print(f"Results:       {results_file}")
    if all_agent_details:
        print(f"Agent details: {agent_file}")
    print(f"Summary:       {summary_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
