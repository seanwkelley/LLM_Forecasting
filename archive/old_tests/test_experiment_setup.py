"""
Quick test to verify experiment setup is correct.
Tests all imports and data loading before running the full experiment.
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

print("="*60)
print("EXPERIMENT SETUP TEST")
print("="*60)

# Test 1: Import all modules
print("\n[1/6] Testing imports...")
try:
    from forecasting.forecaster_base import BaseLLMForecaster
    from forecasting.action_library import load_plausible_actions, get_all_valid_actions, format_plausible_actions_for_prompt
    from forecasting.action_ground_truth import load_ground_truth
    from forecasting.action_evaluation import evaluate_action_set_prediction, evaluate_aggregate_predictions, validate_predictions
    from forecasting.ensemble_aggregation import adaptive_threshold_ensemble
    from forecasting.action_prompts import create_novaris_action_prediction_prompt, create_tethys_action_prediction_prompt
    from forecasting.persona_simplified import load_simplified_personas
    from forecasting.persona_generator import CognitiveProfile
    from forecasting.simulation_data import get_state_before, get_events
    from forecasting.config import OPENROUTER_API_KEY
    print("  [OK] All imports successful")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Check API key
print("\n[2/6] Checking API key...")
if OPENROUTER_API_KEY:
    print(f"  [OK] API key set (length: {len(OPENROUTER_API_KEY)})")
else:
    print("  [FAIL] API key not set! Set OPENROUTER_API_KEY environment variable")
    sys.exit(1)

# Test 3: Load action library
print("\n[3/6] Loading action library...")
try:
    plausible, descriptions = load_plausible_actions()
    plausible_text = format_plausible_actions_for_prompt(plausible, descriptions)
    valid_actions = get_all_valid_actions()
    print(f"  [OK] Loaded {len(valid_actions)} valid actions")
    print(f"  Domains: {', '.join(plausible.keys())}")
except Exception as e:
    print(f"  [FAIL] Error loading action library: {e}")
    sys.exit(1)

# Test 4: Load ground truth
print("\n[4/6] Loading ground truth...")
try:
    ground_truth = load_ground_truth()
    print(f"  [OK] Loaded {len(ground_truth)} periods")
    period_1 = ground_truth[1]
    print(f"  Period 1: Novaris={len(period_1['major_power']['actions'])} actions, Tethys={len(period_1['small_power']['actions'])} actions")
except Exception as e:
    print(f"  [FAIL] Error loading ground truth: {e}")
    sys.exit(1)

# Test 5: Load simulation data
print("\n[5/6] Loading simulation data...")
try:
    state_1 = get_state_before(1)
    events_1 = get_events(1)
    print(f"  [OK] Loaded state for period 1")
    print(f"  Crisis level: {state_1['crisis_level']}")
    print(f"  Events: {len(events_1)}")
except Exception as e:
    print(f"  [FAIL] Error loading simulation data: {e}")
    sys.exit(1)

# Test 6: Load personas
print("\n[6/6] Loading personas...")
try:
    # Test simplified personas
    simplified = load_simplified_personas()
    print(f"  [OK] Loaded {len(simplified)} simplified personas")

    # Test complex personas
    import json
    with open("forecasting/persona_profiles.json") as f:
        data = json.load(f)
    complex_personas = [CognitiveProfile(**p) for p in data['personas'][:5]]
    print(f"  [OK] Loaded {len(complex_personas)} complex personas (test)")
except Exception as e:
    print(f"  [FAIL] Error loading personas: {e}")
    sys.exit(1)

# Test 7: Test prompt generation
print("\n[7/7] Testing prompt generation...")
try:
    test_prompt = create_novaris_action_prediction_prompt(
        period=1,
        state_before=state_1,
        external_events=events_1,
        plausible_actions_text=plausible_text[:500] + "..."
    )
    print(f"  [OK] Generated Novaris prompt ({len(test_prompt)} chars)")

    novaris_actions = ground_truth[1]['major_power']['actions']
    test_prompt_2 = create_tethys_action_prediction_prompt(
        period=1,
        state_before=state_1,
        external_events=events_1,
        novaris_actions=novaris_actions,
        plausible_actions_text=plausible_text[:500] + "..."
    )
    print(f"  [OK] Generated Tethys prompt ({len(test_prompt_2)} chars)")
except Exception as e:
    print(f"  [FAIL] Error generating prompts: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("\nReady to run experiment:")
print("  python forecasting/run_experiment_periods_1_3.py")
print("\nEstimated duration:")
print("  Period 1: 3 conditions x 2 factions x 100 agents = ~15-20 minutes")
print("  Period 2: 3 conditions x 2 factions x 100 agents = ~15-20 minutes")
print("  Period 3: 6 conditions x 2 factions x 100 agents = ~30-40 minutes")
print("  TOTAL: ~60-80 minutes")
print("="*60)
