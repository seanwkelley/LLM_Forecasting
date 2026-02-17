"""
Multi-Scenario Experiment Analysis
===================================

Analyzes results from multi-scenario forecasting experiment.

Key analyses:
1. Overall condition comparison (main effect of sharding)
2. Performance by scenario characteristics
3. Interaction: sharding × scenario parameters
4. Robustness: does sharding help more in certain conditions?

Usage:
    python forecasting/analyze_multiscenario_results.py <results_file>
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


def load_results(results_path: Path, scenarios_path: Path = None) -> pd.DataFrame:
    """Load experiment results and merge with scenario parameters."""
    results = pd.read_csv(results_path)
    print(f"Loaded {len(results)} result rows")
    print(f"Scenarios: {results['scenario_id'].nunique()}")
    print(f"Conditions: {results['condition'].unique()}")

    # Load scenario parameters if available
    if scenarios_path and scenarios_path.exists():
        scenarios = pd.read_csv(scenarios_path)
        results = results.merge(scenarios, on='scenario_id', how='left')
        print(f"Merged with scenario parameters")

    return results


def main_effect_analysis(results: pd.DataFrame):
    """Analyze main effect of condition (sharding strategy)."""
    print("\n" + "="*70)
    print("MAIN EFFECT: Condition (Sharding Strategy)")
    print("="*70)

    # Overall means
    condition_means = results.groupby('condition').agg({
        'brier_score': ['mean', 'std', 'sem'],
        'probability_std': 'mean',
        'fallback_rate': 'mean'
    }).round(4)

    print("\nCondition Means:")
    print(condition_means)

    # Statistical tests
    conditions = results['condition'].unique()
    if len(conditions) >= 2:
        print("\n--- Pairwise Comparisons (t-tests) ---")
        for i, cond1 in enumerate(conditions):
            for cond2 in conditions[i+1:]:
                data1 = results[results['condition'] == cond1]['brier_score']
                data2 = results[results['condition'] == cond2]['brier_score']

                t_stat, p_val = stats.ttest_ind(data1, data2)
                cohens_d = (data1.mean() - data2.mean()) / np.sqrt((data1.var() + data2.var()) / 2)

                print(f"\n{cond1} vs {cond2}:")
                print(f"  Mean diff: {data1.mean() - data2.mean():.4f}")
                print(f"  t = {t_stat:.3f}, p = {p_val:.4f}")
                print(f"  Cohen's d = {cohens_d:.3f}")

                if p_val < 0.05:
                    winner = cond1 if data1.mean() < data2.mean() else cond2
                    print(f"  ** {winner} significantly better (p < 0.05)")

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Brier scores
    results.boxplot(column='brier_score', by='condition', ax=axes[0])
    axes[0].set_title('Brier Score by Condition')
    axes[0].set_xlabel('Condition')
    axes[0].set_ylabel('Brier Score (lower = better)')
    plt.sca(axes[0])
    plt.xticks(rotation=45)

    # Ensemble variance
    results.boxplot(column='probability_std', by='condition', ax=axes[1])
    axes[1].set_title('Prediction Diversity by Condition')
    axes[1].set_xlabel('Condition')
    axes[1].set_ylabel('Probability Std Dev')
    plt.sca(axes[1])
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('multiscenario_main_effect.png', dpi=300, bbox_inches='tight')
    print("\nSaved plot: multiscenario_main_effect.png")


def scenario_parameter_analysis(results: pd.DataFrame):
    """Analyze how performance varies by scenario characteristics."""
    print("\n" + "="*70)
    print("PERFORMANCE BY SCENARIO PARAMETERS")
    print("="*70)

    # Check if we have scenario parameters
    param_cols = ['territory_controlled', 'military_balance', 'sanctions_level',
                  'international_support', 'crisis_level']
    if not all(col in results.columns for col in param_cols):
        print("Scenario parameters not available in results. Skipping.")
        return

    # Binned analysis
    results['territory_bin'] = pd.cut(results['territory_controlled'],
                                      bins=[0, 0.1, 0.25, 1.0],
                                      labels=['Early (0-10%)', 'Mid (10-25%)', 'Late (25%+)'])

    results['sanctions_bin'] = pd.cut(results['sanctions_level'],
                                      bins=[0, 0.3, 0.6, 1.0],
                                      labels=['Low (0-30%)', 'Med (30-60%)', 'High (60%+)'])

    # Performance by territory phase
    print("\n--- Brier Score by War Phase ---")
    territory_perf = results.groupby(['territory_bin', 'condition'])['brier_score'].mean().unstack()
    print(territory_perf.round(4))

    # Performance by sanctions level
    print("\n--- Brier Score by Sanctions Level ---")
    sanctions_perf = results.groupby(['sanctions_bin', 'condition'])['brier_score'].mean().unstack()
    print(sanctions_perf.round(4))

    # Correlations
    print("\n--- Correlations: Brier Score vs Parameters ---")
    for condition in results['condition'].unique():
        cond_data = results[results['condition'] == condition]
        print(f"\n{condition}:")
        for param in param_cols:
            if param in cond_data.columns:
                corr = cond_data['brier_score'].corr(cond_data[param])
                print(f"  {param}: r = {corr:.3f}")


def interaction_analysis(results: pd.DataFrame):
    """Test for interactions between condition and scenario parameters."""
    print("\n" + "="*70)
    print("INTERACTION ANALYSIS: Condition × Scenario Parameters")
    print("="*70)

    # Check if we have parameters
    if 'territory_controlled' not in results.columns:
        print("Scenario parameters not available. Skipping.")
        return

    # Create bins
    results['territory_bin'] = pd.cut(results['territory_controlled'],
                                      bins=[0, 0.15, 0.3, 1.0],
                                      labels=['Low', 'Medium', 'High'])

    # 2-way ANOVA: condition × territory
    baseline_data = results[results['condition'] == 'baseline']
    shard_data = results[results['condition'] != 'baseline']

    if len(baseline_data) > 0 and len(shard_data) > 0:
        print("\n--- Does sharding help more in certain scenarios? ---")

        for territory_level in ['Low', 'Medium', 'High']:
            baseline_territory = baseline_data[baseline_data['territory_bin'] == territory_level]['brier_score']
            shard_territory = shard_data[shard_data['territory_bin'] == territory_level]['brier_score']

            if len(baseline_territory) > 0 and len(shard_territory) > 0:
                improvement = baseline_territory.mean() - shard_territory.mean()
                t_stat, p_val = stats.ttest_ind(baseline_territory, shard_territory)

                print(f"\nTerritory {territory_level} ({territory_level} controlled):")
                print(f"  Baseline Brier: {baseline_territory.mean():.4f}")
                print(f"  Sharding Brier: {shard_territory.mean():.4f}")
                print(f"  Improvement: {improvement:.4f}")
                print(f"  t = {t_stat:.3f}, p = {p_val:.4f}")

    # Visualize interaction
    fig, ax = plt.subplots(figsize=(10, 6))

    for condition in results['condition'].unique():
        cond_data = results[results['condition'] == condition]
        means = cond_data.groupby('territory_bin')['brier_score'].mean()
        ax.plot(means.index, means.values, marker='o', label=condition, linewidth=2)

    ax.set_xlabel('Territory Controlled (War Phase)')
    ax.set_ylabel('Mean Brier Score')
    ax.set_title('Condition × War Phase Interaction')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('multiscenario_interaction.png', dpi=300, bbox_inches='tight')
    print("\nSaved plot: multiscenario_interaction.png")


def robustness_analysis(results: pd.DataFrame):
    """Analyze consistency of condition effects across scenarios."""
    print("\n" + "="*70)
    print("ROBUSTNESS ANALYSIS: Consistency Across Scenarios")
    print("="*70)

    # For each scenario, calculate improvement of sharding over baseline
    baseline = results[results['condition'] == 'baseline'].set_index('scenario_id')['brier_score']
    shard_everything = results[results['condition'] == 'shard_everything'].set_index('scenario_id')['brier_score']

    if len(baseline) > 0 and len(shard_everything) > 0:
        # Align scenarios
        common_scenarios = baseline.index.intersection(shard_everything.index)
        baseline_aligned = baseline[common_scenarios]
        shard_aligned = shard_everything[common_scenarios]

        improvements = baseline_aligned - shard_aligned

        print(f"\nSharding improvement (baseline - shard_everything):")
        print(f"  Mean: {improvements.mean():.4f}")
        print(f"  Std: {improvements.std():.4f}")
        print(f"  Min: {improvements.min():.4f}")
        print(f"  Max: {improvements.max():.4f}")
        print(f"  % scenarios improved: {(improvements > 0).sum() / len(improvements) * 100:.1f}%")

        # Test against zero
        t_stat, p_val = stats.ttest_1samp(improvements, 0)
        print(f"\nOne-sample t-test (H0: improvement = 0):")
        print(f"  t = {t_stat:.3f}, p = {p_val:.4f}")

        # Plot distribution
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(improvements, bins=30, edgecolor='black', alpha=0.7)
        ax.axvline(0, color='red', linestyle='--', linewidth=2, label='No improvement')
        ax.axvline(improvements.mean(), color='green', linestyle='--', linewidth=2,
                  label=f'Mean = {improvements.mean():.4f}')
        ax.set_xlabel('Improvement (Baseline - Sharding)')
        ax.set_ylabel('Count')
        ax.set_title('Distribution of Sharding Improvement Across Scenarios')
        ax.legend()

        plt.tight_layout()
        plt.savefig('multiscenario_robustness.png', dpi=300, bbox_inches='tight')
        print("\nSaved plot: multiscenario_robustness.png")


def main():
    parser = argparse.ArgumentParser(description="Analyze multi-scenario experiment results")
    parser.add_argument("results_file", type=str, help="Path to results CSV file")
    parser.add_argument("--scenarios", type=str, default=None,
                       help="Path to scenarios CSV file (optional, for parameter analysis)")
    args = parser.parse_args()

    results_path = Path(args.results_file)
    scenarios_path = Path(args.scenarios) if args.scenarios else Path("D:/Northeastern/LLM_Forecasting/outputs/multiscenario/scenarios.csv")

    print("="*70)
    print("MULTI-SCENARIO EXPERIMENT ANALYSIS")
    print("="*70)

    # Load data
    results = load_results(results_path, scenarios_path)

    # Run analyses
    main_effect_analysis(results)
    scenario_parameter_analysis(results)
    interaction_analysis(results)
    robustness_analysis(results)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
