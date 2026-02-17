"""
Test single condition to verify the experiment script works.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import json
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.action_library import load_plausible_actions, format_plausible_actions_for_prompt
from forecasting.action_ground_truth import load_ground_truth
from forecasting.simulation_data import get_state_before, get_events
from forecasting.action_prompts import create_novaris_action_prediction_prompt

print("="*60)
print("SINGLE CONDITION TEST")
print("="*60)

# Load data
print("\nLoading data...")
plausible, descriptions = load_plausible_actions()
plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)
ground_truth = load_ground_truth()
state_before = get_state_before(1)
external_events = get_events(1)

print(f"  [OK] Data loaded")
print(f"  Actions: {sum(len(v) for v in plausible.values())}")
print(f"  Period 1 ground truth: Novaris={len(ground_truth[1]['major_power']['actions'])} actions")

# Create forecaster
forecaster = BaseLLMForecaster(model="deepseek/deepseek-v3.2")
print("\n[OK] Forecaster created")

# Create prompt
prompt = create_novaris_action_prediction_prompt(
    period=1,
    state_before=state_before,
    external_events=external_events,
    plausible_actions_text=plausible_text
)

system_prompt = """You are an expert strategic analyst specializing in geopolitical forecasting.

Your task is to predict which actions a faction will take based on strategic analysis of:
- Current military, economic, and diplomatic position
- External events and their implications
- Strategic objectives and constraints
- Available action options

Apply rigorous strategic reasoning to predict the most likely action set.
Output ONLY valid JSON in the exact format specified."""

print("\n[OK] Prompt created (length: {} chars)".format(len(prompt)))

# Make API call
print("\nMaking API call...")
response_text, success = forecaster.call_llm(
    user_prompt=prompt,
    system_prompt=system_prompt,
    response_format="json"
)

if not success:
    print("[FAIL] API call failed")
    sys.exit(1)

print(f"[OK] API call succeeded")
print(f"Response length: {len(response_text)} chars")

# Parse response
try:
    result = json.loads(response_text)
    predicted_actions = result.get('predicted_actions', [])
    rationale = result.get('rationale', 'N/A')
    confidence = result.get('confidence', 'N/A')

    print(f"\n[OK] Response parsed")
    print(f"Predicted actions: {predicted_actions}")
    print(f"Confidence: {confidence}")
    print(f"Rationale: {rationale}")

except Exception as e:
    print(f"[FAIL] Failed to parse response: {e}")
    print(f"Response: {response_text}")
    sys.exit(1)

print("\n" + "="*60)
print("TEST PASSED!")
print("="*60)
