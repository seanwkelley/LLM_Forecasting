"""
Evaluation Module: Compare LLM Forecasts vs Ground Truth

Calculates performance metrics:
- Brier Score (calibration)
- Mean Absolute Error (accuracy)
- Root Mean Squared Error
- Directional Accuracy (did forecast track trend?)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json


def load_ground_truth(assessments_path: str = None) -> pd.DataFrame:
    """
    Load ground truth collapse probabilities from R simulation

    Args:
        assessments_path: Path to assessments.csv (default: outputs/assessments.csv)

    Returns:
        DataFrame with period and true_probability columns
    """
    if assessments_path is None:
        assessments_path = Path(__file__).parent.parent / "outputs" / "assessments.csv"

    df = pd.read_csv(assessments_path)
    df = df.rename(columns={'probability': 'true_probability'})

    return df[['period', 'true_probability', 'trend', 'confidence']]


def calculate_brier_score(forecasts: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Calculate Brier Score (lower is better, 0 = perfect, 0.25 = random)

    BS = mean((forecast - outcome)^2)

    Args:
        forecasts: Array of forecast probabilities (0-1)
        ground_truth: Array of true probabilities (0-1)

    Returns:
        Brier score
    """
    return np.mean((forecasts - ground_truth) ** 2)


def calculate_mae(forecasts: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Calculate Mean Absolute Error

    Args:
        forecasts: Array of forecast probabilities (0-1)
        ground_truth: Array of true probabilities (0-1)

    Returns:
        MAE
    """
    return np.mean(np.abs(forecasts - ground_truth))


def calculate_rmse(forecasts: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Calculate Root Mean Squared Error

    Args:
        forecasts: Array of forecast probabilities (0-1)
        ground_truth: Array of true probabilities (0-1)

    Returns:
        RMSE
    """
    return np.sqrt(np.mean((forecasts - ground_truth) ** 2))


def calculate_directional_accuracy(
    forecasts: pd.DataFrame,
    ground_truth: pd.DataFrame
) -> float:
    """
    Calculate directional accuracy: did forecast correctly predict trend?

    Args:
        forecasts: DataFrame with period and probability columns
        ground_truth: DataFrame with period and true_probability columns

    Returns:
        Proportion of periods where forecast trend matched ground truth trend
    """
    # Merge and sort by period
    merged = forecasts.merge(ground_truth, on='period').sort_values('period')

    if len(merged) < 2:
        return np.nan

    # Calculate period-to-period changes
    merged['forecast_change'] = merged['probability'].diff()
    merged['true_change'] = merged['true_probability'].diff()

    # Check if signs match (both increasing, both decreasing, or both stable)
    merged['direction_match'] = (
        (merged['forecast_change'] * merged['true_change'] > 0) |  # Same direction
        ((merged['forecast_change'] == 0) & (merged['true_change'] == 0))  # Both stable
    )

    # Calculate accuracy (exclude first period which has no change)
    return merged['direction_match'].iloc[1:].mean()


def calculate_bias(forecasts: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Calculate forecast bias (negative = under-forecasting, positive = over-forecasting)

    Args:
        forecasts: Array of forecast probabilities (0-1)
        ground_truth: Array of true probabilities (0-1)

    Returns:
        Mean bias
    """
    return np.mean(forecasts - ground_truth)


def evaluate_condition(
    condition_name: str,
    forecasts_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    use_round_2: bool = False
) -> Dict:
    """
    Evaluate a single condition against ground truth

    Args:
        condition_name: Name of condition (e.g., "condition_1")
        forecasts_df: DataFrame with forecasts
        ground_truth_df: DataFrame with ground truth
        use_round_2: For debate conditions, use only Round 2 forecasts

    Returns:
        Dictionary with evaluation metrics
    """
    # Filter to Round 2 if debate condition
    if use_round_2 and 'round' in forecasts_df.columns:
        forecasts_df = forecasts_df[forecasts_df['round'] == 2]

    # Aggregate forecasts by period (mean)
    period_forecasts = forecasts_df.groupby('period')['probability'].mean().reset_index()

    # Merge with ground truth
    merged = period_forecasts.merge(ground_truth_df, on='period', how='inner')

    if len(merged) == 0:
        return {
            'condition': condition_name,
            'n_periods': 0,
            'error': 'No matching periods found'
        }

    # Calculate metrics
    forecasts = merged['probability'].values
    ground_truth = merged['true_probability'].values

    metrics = {
        'condition': condition_name,
        'n_periods': len(merged),
        'periods': merged['period'].tolist(),

        # Primary metrics
        'brier_score': float(calculate_brier_score(forecasts, ground_truth)),
        'mae': float(calculate_mae(forecasts, ground_truth)),
        'rmse': float(calculate_rmse(forecasts, ground_truth)),
        'bias': float(calculate_bias(forecasts, ground_truth)),

        # Directional accuracy
        'directional_accuracy': float(calculate_directional_accuracy(
            period_forecasts, ground_truth_df
        )),

        # Summary statistics
        'mean_forecast': float(np.mean(forecasts)),
        'mean_ground_truth': float(np.mean(ground_truth)),
        'correlation': float(np.corrcoef(forecasts, ground_truth)[0, 1]),

        # Period-by-period comparison
        'period_comparison': [
            {
                'period': int(row['period']),
                'forecast': float(row['probability']),
                'ground_truth': float(row['true_probability']),
                'error': float(row['probability'] - row['true_probability'])
            }
            for _, row in merged.iterrows()
        ]
    }

    return metrics


def evaluate_all_conditions(
    results_dir: str = None,
    ground_truth_path: str = None
) -> pd.DataFrame:
    """
    Evaluate all 4 conditions against ground truth

    Args:
        results_dir: Path to forecasting_results directory
        ground_truth_path: Path to assessments.csv

    Returns:
        DataFrame with comparison across all conditions
    """
    if results_dir is None:
        results_dir = Path(__file__).parent.parent / "outputs" / "forecasting_results"
    else:
        results_dir = Path(results_dir)

    # Load ground truth
    ground_truth_df = load_ground_truth(ground_truth_path)

    # Evaluate each condition
    all_metrics = []

    # Condition 1: Generic Independent
    try:
        c1_path = results_dir / "condition_1_generic_independent" / "all_forecasts_individual.csv"
        if c1_path.exists():
            df_c1 = pd.read_csv(c1_path)
            metrics_c1 = evaluate_condition("Condition 1: Generic Independent", df_c1, ground_truth_df)
            all_metrics.append(metrics_c1)
    except Exception as e:
        print(f"[WARNING] Failed to evaluate Condition 1: {e}")

    # Condition 2: Generic Debate
    try:
        c2_path = results_dir / "condition_2_generic_debate" / "all_forecasts.csv"
        if c2_path.exists():
            df_c2 = pd.read_csv(c2_path)
            metrics_c2 = evaluate_condition("Condition 2: Generic Debate", df_c2, ground_truth_df, use_round_2=True)
            all_metrics.append(metrics_c2)
    except Exception as e:
        print(f"[WARNING] Failed to evaluate Condition 2: {e}")

    # Condition 3: Personalized Independent
    try:
        c3_path = results_dir / "condition_3_personalized_independent" / "all_forecasts_individual.csv"
        if c3_path.exists():
            df_c3 = pd.read_csv(c3_path)
            metrics_c3 = evaluate_condition("Condition 3: Personalized Independent", df_c3, ground_truth_df)
            all_metrics.append(metrics_c3)
    except Exception as e:
        print(f"[WARNING] Failed to evaluate Condition 3: {e}")

    # Condition 4: Personalized Debate
    try:
        c4_path = results_dir / "condition_4_personalized_debate" / "all_forecasts.csv"
        if c4_path.exists():
            df_c4 = pd.read_csv(c4_path)
            metrics_c4 = evaluate_condition("Condition 4: Personalized Debate", df_c4, ground_truth_df, use_round_2=True)
            all_metrics.append(metrics_c4)
    except Exception as e:
        print(f"[WARNING] Failed to evaluate Condition 4: {e}")

    # Create comparison DataFrame
    comparison_data = []
    for metrics in all_metrics:
        if 'error' not in metrics:
            comparison_data.append({
                'Condition': metrics['condition'],
                'N Periods': metrics['n_periods'],
                'Brier Score': f"{metrics['brier_score']:.4f}",
                'MAE': f"{metrics['mae']:.4f}",
                'RMSE': f"{metrics['rmse']:.4f}",
                'Bias': f"{metrics['bias']:.4f}",
                'Directional Acc': f"{metrics['directional_accuracy']:.2%}",
                'Correlation': f"{metrics['correlation']:.3f}",
                'Mean Forecast': f"{metrics['mean_forecast']:.3f}",
                'Mean Truth': f"{metrics['mean_ground_truth']:.3f}"
            })

    df_comparison = pd.DataFrame(comparison_data)

    return df_comparison, all_metrics, ground_truth_df


def print_evaluation_report(
    comparison_df: pd.DataFrame,
    all_metrics: List[Dict],
    ground_truth_df: pd.DataFrame
):
    """
    Print detailed evaluation report
    """
    print("=" * 80)
    print("FORECASTING EVALUATION REPORT")
    print("=" * 80)
    print()

    print("GROUND TRUTH (True Collapse Probabilities):")
    print("-" * 80)
    for _, row in ground_truth_df.iterrows():
        print(f"  Period {int(row['period'])}: {row['true_probability']:.1%} "
              f"(trend: {row['trend']}, confidence: {row['confidence']})")
    print()

    print("PERFORMANCE COMPARISON:")
    print("-" * 80)
    print(comparison_df.to_string(index=False))
    print()

    print("INTERPRETATION:")
    print("-" * 80)
    print("• Brier Score: Lower is better (0=perfect, 0.25=random)")
    print("• MAE: Mean Absolute Error (lower is better)")
    print("• Bias: Negative = under-forecasting, Positive = over-forecasting")
    print("• Directional Accuracy: % of periods where trend matched ground truth")
    print("• Correlation: Pearson correlation between forecast and truth (1=perfect)")
    print()

    # Find best condition
    best_brier = min(all_metrics, key=lambda x: x.get('brier_score', float('inf')))
    best_mae = min(all_metrics, key=lambda x: x.get('mae', float('inf')))
    best_directional = max(all_metrics, key=lambda x: x.get('directional_accuracy', 0))

    print("BEST PERFORMERS:")
    print("-" * 80)
    print(f"• Best Brier Score: {best_brier['condition']} ({best_brier['brier_score']:.4f})")
    print(f"• Best MAE: {best_mae['condition']} ({best_mae['mae']:.4f})")
    print(f"• Best Directional Accuracy: {best_directional['condition']} "
          f"({best_directional['directional_accuracy']:.1%})")
    print()

    print("=" * 80)


if __name__ == "__main__":
    # Run evaluation
    comparison_df, all_metrics, ground_truth_df = evaluate_all_conditions()

    # Print report
    print_evaluation_report(comparison_df, all_metrics, ground_truth_df)

    # Save results
    output_dir = Path(__file__).parent.parent / "outputs" / "forecasting_results" / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save comparison table
    comparison_df.to_csv(output_dir / "comparison.csv", index=False)

    # Save detailed metrics
    with open(output_dir / "detailed_metrics.json", 'w') as f:
        json.dump(all_metrics, f, indent=2)

    print(f"Results saved to: {output_dir}")
