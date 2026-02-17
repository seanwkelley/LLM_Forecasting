"""
Generate Mock Multi-Scenario Data for Testing
==============================================

Creates synthetic scenario data and ground truth for testing the forecasting pipeline
without running the full R simulation (which has complex dependencies).

For production, you would use the full R simulation (generate_multiscenario_dataset.R).
"""

import pandas as pd
import numpy as np
from pathlib import Path

def generate_mock_scenarios(n_scenarios=3, seed=42):
    """Generate mock scenario parameters."""
    np.random.seed(seed)

    scenarios = []
    for i in range(n_scenarios):
        scenario = {
            'scenario_id': f'scenario_{i+1:03d}',
            'territory_controlled': np.random.uniform(0, 0.40),
            'military_balance': np.random.uniform(-0.30, 0.10),
            'sanctions_level': np.random.uniform(0, 0.80),
            'international_support': np.random.uniform(0.30, 0.90),
            'crisis_level': np.random.randint(3, 11),
            'novaris_gdp': np.random.uniform(70, 100),
            'tethys_gdp': np.random.uniform(15, 30),
        }
        scenario['gdp_ratio'] = scenario['tethys_gdp'] / scenario['novaris_gdp']
        scenario['momentum'] = 0.1 if scenario['territory_controlled'] > 0.1 else 0
        scenarios.append(scenario)

    return pd.DataFrame(scenarios)


def generate_mock_ground_truth(scenarios_df):
    """Generate mock ground truth data."""

    ground_truth = []
    for _, scenario in scenarios_df.iterrows():
        # Mock collapse probability based on scenario parameters
        # Higher territory loss, higher crisis, lower support → higher collapse prob
        base_prob = 0.3
        territory_effect = scenario['territory_controlled'] * 0.5  # +0 to +0.20
        crisis_effect = (scenario['crisis_level'] - 5) * 0.03      # -0.06 to +0.15
        support_effect = -(scenario['international_support'] - 0.6) * 0.3  # -0.09 to +0.09

        collapse_prob = base_prob + territory_effect + crisis_effect + support_effect
        collapse_prob = np.clip(collapse_prob, 0.05, 0.95)

        # Mock actions (randomly sample from common actions)
        novaris_actions_pool = [
            'military_buildup', 'precision_strike', 'artillery_barrage',
            'naval_blockade', 'cyber_attack', 'propaganda_campaign'
        ]
        tethys_actions_pool = [
            'show_of_force', 'coalition_building', 'targeted_sabotage',
            'defensive_fortification', 'cyber_defense', 'humanitarian_aid'
        ]

        n_novaris = np.random.randint(2, 5)
        n_tethys = np.random.randint(2, 5)

        novaris_actions = np.random.choice(novaris_actions_pool, n_novaris, replace=False).tolist()
        tethys_actions = np.random.choice(tethys_actions_pool, n_tethys, replace=False).tolist()

        # Mock final state (slight changes from initial)
        final_territory = scenario['territory_controlled'] + np.random.uniform(-0.05, 0.05)
        final_territory = np.clip(final_territory, 0, 0.5)

        ground_truth.append({
            'scenario_id': scenario['scenario_id'],
            'period': 1,
            'collapse_probability': collapse_prob,
            'novaris_actions': '|'.join(novaris_actions),
            'tethys_actions': '|'.join(tethys_actions),
            'n_novaris_actions': n_novaris,
            'n_tethys_actions': n_tethys,
            'final_territory': final_territory,
            'final_military_balance': scenario['military_balance'] + np.random.uniform(-0.05, 0.05),
            'final_crisis_level': min(10, scenario['crisis_level'] + np.random.randint(-1, 2)),
            'final_sanctions': scenario['sanctions_level'] + np.random.uniform(-0.05, 0.05),
            'final_support': scenario['international_support'] + np.random.uniform(-0.05, 0.05),
        })

    return pd.DataFrame(ground_truth)


def main():
    print("="*70)
    print("GENERATING MOCK MULTI-SCENARIO DATA")
    print("="*70)
    print("\nNOTE: This generates synthetic data for testing.")
    print("For production, use generate_multiscenario_dataset.R")
    print("="*70)

    # Create output directory
    output_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate scenarios
    print("\nGenerating 3 mock scenarios...")
    scenarios = generate_mock_scenarios(n_scenarios=3, seed=42)

    print("\nScenario parameters:")
    print(scenarios[['scenario_id', 'territory_controlled', 'military_balance',
                     'sanctions_level', 'international_support', 'crisis_level']].to_string())

    # Generate ground truth
    print("\nGenerating mock ground truth...")
    ground_truth = generate_mock_ground_truth(scenarios)

    print("\nGround truth:")
    print(ground_truth[['scenario_id', 'collapse_probability', 'n_novaris_actions',
                        'n_tethys_actions']].to_string())

    # Save files
    scenarios_file = output_dir / "scenarios.csv"
    ground_truth_file = output_dir / "ground_truth.csv"

    scenarios.to_csv(scenarios_file, index=False)
    ground_truth.to_csv(ground_truth_file, index=False)

    print("\n" + "="*70)
    print("MOCK DATA GENERATION COMPLETE")
    print("="*70)
    print(f"Scenarios: {scenarios_file}")
    print(f"Ground truth: {ground_truth_file}")
    print("\nYou can now run:")
    print("  python -u forecasting/run_multiscenario_experiment.py --test")
    print("="*70)


if __name__ == "__main__":
    main()
