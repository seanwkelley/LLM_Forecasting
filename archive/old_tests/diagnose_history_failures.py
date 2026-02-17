"""
Diagnose why Period 7 and 10 failed catastrophically with history.

Run just these two periods with history and examine what was predicted.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
from collections import Counter

from forecasting.action_ground_truth import load_ground_truth
from forecasting.action_library import load_plausible_actions, format_plausible_actions_for_prompt
from forecasting.forecaster_base import BaseLLMForecaster

# Initial scenario
INITIAL_SCENARIO = """
BACKGROUND (Observable Intelligence):
Novaris (major regional power) has engaged in military operations against Tethys (smaller state).
Stated objective: Territorial control. Current status: Active military conflict with international
involvement. You are analyzing observable actions, state changes, and external events to predict
what strategic actions each side will take next.
"""

def create_historical_summary(ground_truth: dict, period: int) -> str:
    """Create summary of observable actions."""
    if period <= 1:
        return ""

    history_lines = ["="*80, "OBSERVED ACTION HISTORY (Intelligence Assessment)", "="*80, ""]

    for p in range(1, period):
        novaris_actions = ground_truth[p]['major_power']['actions']
        tethys_actions = ground_truth[p]['small_power']['actions']

        history_lines.append(f"PERIOD {p} - Observed Actions:")
        history_lines.append(f"  Novaris executed: {', '.join(novaris_actions)}")
        history_lines.append(f"  Tethys executed: {', '.join(tethys_actions)}")
        history_lines.append("")

    history_lines.append("Based on observed patterns, predict what actions will be taken in the current period.")
    history_lines.append("")

    return '\n'.join(history_lines)


def diagnose_period(period: int):
    """Diagnose what went wrong in a specific period."""

    print(f"\n{'='*80}")
    print(f"DIAGNOSING PERIOD {period}")
    print('='*80)

    ground_truth = load_ground_truth()
    plausible, descriptions = load_plausible_actions()
    plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)

    novaris_actual = ground_truth[period]['major_power']['actions']
    tethys_actual = ground_truth[period]['small_power']['actions']

    print(f"\nGROUND TRUTH:")
    print(f"  Novaris: {novaris_actual}")
    print(f"  Tethys: {tethys_actual}")

    # Create prompt with history
    historical_summary = create_historical_summary(ground_truth, period)

    prompt = f"""You are a strategic analyst tasked with predicting NOVARIS's action set for Period {period}.

{INITIAL_SCENARIO}

{historical_summary}

{'='*80}
YOUR TASK
{'='*80}

Given the background and history above, predict the COMPLETE action set NOVARIS will take in Period {period}.

AVAILABLE ACTIONS:
{plausible_text}

Output ONLY a JSON object with this structure:
{{
  "predicted_actions": ["action1", "action2", ...]
}}

Select 3-9 actions that NOVARIS will most likely take this period.
"""

    print(f"\n{'='*80}")
    print(f"PROMPT LENGTH: {len(prompt)} characters ({len(prompt.split())} words)")
    print('='*80)

    # Sample 10 predictions to see what's happening
    forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")

    system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis.
Apply rigorous strategic reasoning. Output ONLY valid JSON in the exact format specified."""

    print(f"\nSAMPLING 10 PREDICTIONS:")
    predictions = []

    for i in range(10):
        try:
            response_text, success = forecaster.call_llm(
                user_prompt=prompt,
                system_prompt=system_prompt,
                response_format="json"
            )

            if success:
                result = json.loads(response_text)
                pred_actions = result.get('predicted_actions', [])
                predictions.append(pred_actions)
                print(f"  {i+1}. {pred_actions}")
            else:
                print(f"  {i+1}. [FAILED]")
                predictions.append([])
        except Exception as e:
            print(f"  {i+1}. [ERROR: {str(e)[:50]}]")
            predictions.append([])

    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print('='*80)

    # Count all predicted actions
    all_predicted = []
    for pred in predictions:
        all_predicted.extend(pred)

    if all_predicted:
        action_counts = Counter(all_predicted)
        print(f"\nMost commonly predicted actions:")
        for action, count in action_counts.most_common(10):
            in_ground_truth = "✓" if action in novaris_actual else "✗"
            print(f"  {action}: {count}/10 predictions {in_ground_truth}")
    else:
        print("\n[CRITICAL] NO ACTIONS PREDICTED AT ALL!")

    # Check if predicted actions are even plausible
    plausible_set = set(plausible)
    invalid_actions = []
    for pred in predictions:
        for action in pred:
            if action not in plausible_set:
                invalid_actions.append(action)

    if invalid_actions:
        print(f"\n[WARNING] Invalid actions predicted (not in plausible set):")
        for action, count in Counter(invalid_actions).most_common():
            print(f"  {action}: {count} times")

    # Check overlap with ground truth
    correct_predictions = 0
    for pred in predictions:
        overlap = set(pred) & set(novaris_actual)
        if overlap:
            correct_predictions += 1

    print(f"\nPredictions with at least 1 correct action: {correct_predictions}/10")

    if correct_predictions == 0:
        print("\n[CRITICAL] ZERO CORRECT PREDICTIONS - Complete failure to predict any ground truth actions!")


# Diagnose both failure periods
diagnose_period(7)
diagnose_period(10)

print(f"\n{'='*80}")
print("SUMMARY")
print('='*80)
print("\nKey questions answered:")
print("1. How long are the prompts with history?")
print("2. What actions are the models predicting?")
print("3. Are they predicting invalid actions?")
print("4. Why is there zero overlap with ground truth?")
print()
