"""
Pilot Experiment: Run all 4 conditions on Periods 1-3

Tests the complete forecasting pipeline before running full 10-period experiment.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
from forecasting.conditions.condition_1_generic_independent import GenericIndependentForecaster
from forecasting.conditions.condition_2_generic_debate import GenericDebateForecaster
from forecasting.conditions.condition_3_personalized_independent import PersonalizedIndependentForecaster
from forecasting.conditions.condition_4_personalized_debate import PersonalizedDebateForecaster


def run_pilot_experiment():
    """
    Run all 4 conditions on periods 1-3

    Conditions:
    1. Generic Independent (N=10)
    2. Generic Debate (N=50, 10 groups of 5)
    3. Personalized Independent (N=100)
    4. Personalized Debate (N=100, 20 groups of 5)
    """

    pilot_periods = [1, 2, 3]

    print("=" * 80)
    print("PILOT EXPERIMENT: PERIODS 1-3")
    print("=" * 80)
    print(f"Testing all 4 conditions on periods: {pilot_periods}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {}

    # =========================================================================
    # CONDITION 1: Generic Independent (N=10)
    # =========================================================================
    print("\n" + "=" * 80)
    print("CONDITION 1: GENERIC INDEPENDENT")
    print("=" * 80)

    try:
        c1 = GenericIndependentForecaster(
            n_agents=10,
            parallel=True,
            max_workers=5
        )
        df_c1 = c1.run_all_periods(periods=pilot_periods)
        results['condition_1'] = df_c1

        print(f"\n[OK] Condition 1 complete: {len(df_c1)} forecasts")
        print(f"     Mean probability: {df_c1['probability'].mean():.3f}")
        print(f"     Std probability: {df_c1['probability'].std():.3f}")

    except Exception as e:
        print(f"\n[ERROR] Condition 1 failed: {str(e)}")
        results['condition_1'] = None

    # =========================================================================
    # CONDITION 2: Generic Debate (N=50, 10 groups)
    # =========================================================================
    print("\n" + "=" * 80)
    print("CONDITION 2: GENERIC DEBATE")
    print("=" * 80)

    try:
        c2 = GenericDebateForecaster(
            n_agents=50,
            n_groups=10,
            parallel_groups=True,
            max_workers=5
        )
        df_c2 = c2.run_all_periods(periods=pilot_periods)
        results['condition_2'] = df_c2

        # Get Round 2 forecasts
        r2 = df_c2[df_c2['round'] == 2]
        print(f"\n[OK] Condition 2 complete: {len(df_c2)} forecasts ({len(r2)} Round 2)")
        print(f"     Mean probability (R2): {r2['probability'].mean():.3f}")
        print(f"     Std probability (R2): {r2['probability'].std():.3f}")

    except Exception as e:
        print(f"\n[ERROR] Condition 2 failed: {str(e)}")
        results['condition_2'] = None

    # =========================================================================
    # CONDITION 3: Personalized Independent (N=100)
    # =========================================================================
    print("\n" + "=" * 80)
    print("CONDITION 3: PERSONALIZED INDEPENDENT")
    print("=" * 80)

    try:
        c3 = PersonalizedIndependentForecaster(
            n_agents=100,
            parallel=True,
            max_workers=10
        )
        df_c3 = c3.run_all_periods(periods=pilot_periods)
        results['condition_3'] = df_c3

        print(f"\n[OK] Condition 3 complete: {len(df_c3)} forecasts")
        print(f"     Mean probability: {df_c3['probability'].mean():.3f}")
        print(f"     Std probability: {df_c3['probability'].std():.3f}")

    except Exception as e:
        print(f"\n[ERROR] Condition 3 failed: {str(e)}")
        results['condition_3'] = None

    # =========================================================================
    # CONDITION 4: Personalized Debate (N=100, 20 groups)
    # =========================================================================
    print("\n" + "=" * 80)
    print("CONDITION 4: PERSONALIZED DEBATE")
    print("=" * 80)

    try:
        c4 = PersonalizedDebateForecaster(
            n_agents=100,
            n_groups=20,
            parallel_groups=True,
            max_workers=5
        )
        df_c4 = c4.run_all_periods(periods=pilot_periods)
        results['condition_4'] = df_c4

        # Get Round 2 forecasts
        r2 = df_c4[df_c4['round'] == 2]
        print(f"\n[OK] Condition 4 complete: {len(df_c4)} forecasts ({len(r2)} Round 2)")
        print(f"     Mean probability (R2): {r2['probability'].mean():.3f}")
        print(f"     Std probability (R2): {r2['probability'].std():.3f}")

    except Exception as e:
        print(f"\n[ERROR] Condition 4 failed: {str(e)}")
        results['condition_4'] = None

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("PILOT EXPERIMENT SUMMARY")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create comparison table
    comparison_data = []

    for condition_name, df in results.items():
        if df is not None:
            # Handle debate conditions (use Round 2 only)
            if 'round' in df.columns:
                df_final = df[df['round'] == 2]
            else:
                df_final = df

            comparison_data.append({
                'Condition': condition_name.replace('_', ' ').title(),
                'N': len(df_final),
                'Mean': f"{df_final['probability'].mean():.3f}",
                'Median': f"{df_final['probability'].median():.3f}",
                'Std': f"{df_final['probability'].std():.3f}",
                'Min': f"{df_final['probability'].min():.3f}",
                'Max': f"{df_final['probability'].max():.3f}",
                'Success Rate': f"{df_final['success'].mean()*100:.1f}%"
            })

    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)
        print("\nFORECAST COMPARISON (Periods 1-3):")
        print(df_comparison.to_string(index=False))

        # Save comparison
        output_dir = Path("outputs/forecasting_results/pilot_comparison")
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / "pilot_comparison.csv"
        df_comparison.to_csv(csv_path, index=False)
        print(f"\nComparison saved to: {csv_path}")

    print("\n" + "=" * 80)
    print("[OK] Pilot experiment complete!")
    print("=" * 80)

    return results


if __name__ == "__main__":
    results = run_pilot_experiment()
