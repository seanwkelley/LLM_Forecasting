"""
Condition 2: Generic Debate Forecasters

N=50 generic agents split into 10 groups of 5.
Each group runs 2-round deliberation:
- Round 1: Independent forecasts
- Round 2: Revision after seeing others' forecasts

Tests whether debate improves generic agent performance.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forecasting.forecaster_base import BaseLLMForecaster, ForecastResponse
from forecasting.prompt_loader import load_period_prompt
from forecasting.config import (
    N_AGENTS_GENERIC_DEBATE,
    N_GROUPS_GENERIC_DEBATE,
    DEBATE_GROUP_SIZE,
    N_DEBATE_ROUNDS,
    GENERIC_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    get_output_dir
)


class GenericDebateForecaster:
    """
    Runs N=50 generic agents in 10 debate groups (5 agents each)
    """

    def __init__(
        self,
        n_agents: int = N_AGENTS_GENERIC_DEBATE,
        n_groups: int = N_GROUPS_GENERIC_DEBATE,
        group_size: int = DEBATE_GROUP_SIZE,
        model: str = DEFAULT_MODEL,
        parallel_groups: bool = True,
        max_workers: int = 5
    ):
        """
        Initialize condition

        Args:
            n_agents: Total number of agents (default 50)
            n_groups: Number of debate groups (default 10)
            group_size: Agents per group (default 5)
            model: LLM model to use
            parallel_groups: Run groups in parallel
            max_workers: Max parallel groups
        """
        assert n_agents == n_groups * group_size, \
            f"n_agents ({n_agents}) must equal n_groups ({n_groups}) × group_size ({group_size})"

        self.n_agents = n_agents
        self.n_groups = n_groups
        self.group_size = group_size
        self.model = model
        self.parallel_groups = parallel_groups
        self.max_workers = max_workers

        # Output directory
        self.output_dir = get_output_dir("condition_2_generic_debate")

        # Initialize base forecaster
        self.forecaster = BaseLLMForecaster(
            model=model,
            system_prompt=GENERIC_SYSTEM_PROMPT
        )

        print(f"[Condition 2] Initialized with {n_agents} generic agents")
        print(f"[Condition 2] {n_groups} groups of {group_size} agents")
        print(f"[Condition 2] Model: {model}")
        print(f"[Condition 2] Output: {self.output_dir}")

    def _create_deliberation_summary(
        self,
        forecasts: List[Dict],
        exclude_agent_id: str = None
    ) -> str:
        """
        Create summary of other agents' forecasts for deliberation

        Args:
            forecasts: List of forecast dictionaries from Round 1
            exclude_agent_id: Agent to exclude (don't show agent their own forecast)

        Returns:
            Formatted summary string
        """
        lines = ["OTHER ANALYSTS' FORECASTS:\n"]

        for f in forecasts:
            if exclude_agent_id and f['agent_id'] == exclude_agent_id:
                continue  # Skip this agent's own forecast

            prob_pct = f['probability'] * 100
            lines.append(
                f"• Analyst {f['agent_id']}: {prob_pct:.1f}% "
                f"(confidence: {f['confidence']})"
            )
            lines.append(f"  Reasoning: {f['reasoning'][:150]}...")
            lines.append("")

        return "\n".join(lines)

    def _build_revision_prompt(
        self,
        original_prompt: str,
        agent_round1_forecast: Dict,
        deliberation_summary: str
    ) -> str:
        """
        Build prompt for Round 2 (revision after seeing others)

        Args:
            original_prompt: Original forecasting prompt
            agent_round1_forecast: This agent's Round 1 forecast
            deliberation_summary: Summary of other agents' forecasts

        Returns:
            Revision prompt
        """
        revision_prompt = f"""You previously estimated a {agent_round1_forecast['probability']*100:.1f}% probability for this scenario.

{deliberation_summary}

Now, after reviewing other analysts' assessments:

1. Do you want to revise your probability estimate?
2. Did other analysts raise points you hadn't considered?
3. Do you still stand by your original reasoning, or should you adjust?

Please provide your REVISED forecast:

Probability: [your revised estimate as decimal 0.0-1.0 or percentage]
Confidence: [low/medium/high]
Reasoning: [Explain whether and why you revised your estimate, incorporating insights from the discussion]
"""
        return revision_prompt

    def forecast_group(
        self,
        group_id: int,
        period: int,
        prompt: str
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Run 2-round debate for a single group

        Args:
            group_id: Group identifier
            period: Period number
            prompt: Forecasting prompt

        Returns:
            Tuple of (DataFrame with all forecasts, aggregated results)
        """
        # Round 1: Independent forecasts
        round1_forecasts = []

        for agent_idx in range(self.group_size):
            agent_id = f"generic_g{group_id:02d}_a{agent_idx}"

            forecast = self.forecaster.generate_forecast(prompt)

            round1_forecasts.append({
                "condition": "generic_debate",
                "period": period,
                "group_id": group_id,
                "agent_id": agent_id,
                "persona_id": None,
                "round": 1,
                "probability": forecast.probability,
                "confidence": forecast.confidence,
                "reasoning": forecast.reasoning,
                "timestamp": forecast.timestamp,
                "success": forecast.success,
                "error": forecast.error
            })

        # Round 2: Revision after deliberation
        round2_forecasts = []

        for agent_idx, r1_forecast in enumerate(round1_forecasts):
            # Create deliberation summary (exclude this agent's own forecast)
            deliberation_summary = self._create_deliberation_summary(
                round1_forecasts,
                exclude_agent_id=r1_forecast['agent_id']
            )

            # Build revision prompt
            revision_prompt = self._build_revision_prompt(
                prompt,
                r1_forecast,
                deliberation_summary
            )

            # Get revised forecast
            forecast = self.forecaster.generate_forecast(revision_prompt)

            round2_forecasts.append({
                "condition": "generic_debate",
                "period": period,
                "group_id": group_id,
                "agent_id": r1_forecast['agent_id'],
                "persona_id": None,
                "round": 2,
                "probability": forecast.probability,
                "confidence": forecast.confidence,
                "reasoning": forecast.reasoning,
                "timestamp": forecast.timestamp,
                "success": forecast.success,
                "error": forecast.error
            })

        # Combine rounds
        all_forecasts = round1_forecasts + round2_forecasts
        df_group = pd.DataFrame(all_forecasts)

        # Aggregate Round 2 forecasts (final estimates)
        r2_successful = [f for f in round2_forecasts if f['success']]
        r2_probs = [f['probability'] for f in r2_successful]

        aggregated = {
            "group_id": group_id,
            "period": period,
            "n_agents": self.group_size,
            "mean_r1": np.mean([f['probability'] for f in round1_forecasts if f['success']]),
            "mean_r2": np.mean(r2_probs) if r2_probs else 0.5,
            "median_r2": np.median(r2_probs) if r2_probs else 0.5,
            "std_r2": np.std(r2_probs) if len(r2_probs) > 1 else 0.0,
            "convergence": abs(np.mean(r2_probs) - np.mean([f['probability'] for f in round1_forecasts if f['success']])) if r2_probs else 0.0
        }

        return df_group, aggregated

    def forecast_period(self, period: int) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Run all debate groups for a single period

        Args:
            period: Period number (1-10)

        Returns:
            Tuple of (DataFrame with all forecasts, list of group aggregations)
        """
        print(f"\n[Condition 2] Period {period}: Running {self.n_groups} debate groups...")

        # Load prompt
        prompt = load_period_prompt(period)

        group_results = []
        group_aggregations = []

        if self.parallel_groups:
            # Run groups in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self.forecast_group,
                        group_id,
                        period,
                        prompt
                    ): group_id
                    for group_id in range(self.n_groups)
                }

                completed = 0
                for future in as_completed(futures):
                    group_id = futures[future]
                    try:
                        df_group, agg = future.result()
                        group_results.append(df_group)
                        group_aggregations.append(agg)
                        completed += 1

                        if completed % 5 == 0 or completed == self.n_groups:
                            print(f"  Progress: {completed}/{self.n_groups} groups complete")

                    except Exception as e:
                        print(f"  [ERROR] Group {group_id} failed: {str(e)}")

        else:
            # Sequential execution
            for group_id in range(self.n_groups):
                df_group, agg = self.forecast_group(group_id, period, prompt)
                group_results.append(df_group)
                group_aggregations.append(agg)

                if (group_id + 1) % 5 == 0:
                    print(f"  Progress: {group_id + 1}/{self.n_groups} groups complete")

        # Combine all groups
        df_all = pd.concat(group_results, ignore_index=True)

        print(f"[Condition 2] Period {period}: Complete ({len(df_all)} total forecasts)")

        return df_all, group_aggregations

    def aggregate_across_groups(
        self,
        df: pd.DataFrame,
        group_aggregations: List[Dict]
    ) -> Dict:
        """
        Aggregate across all groups for a period

        Args:
            df: DataFrame with all forecasts
            group_aggregations: List of per-group aggregations

        Returns:
            Overall aggregated statistics
        """
        # Get Round 2 forecasts (final estimates)
        r2_forecasts = df[df['round'] == 2]
        r2_successful = r2_forecasts[r2_forecasts['success'] == True]

        if len(r2_successful) == 0:
            return {
                "mean_probability": 0.5,
                "median_probability": 0.5,
                "std_probability": 0.0,
                "n_groups": self.n_groups,
                "n_agents": 0,
                "mean_convergence": 0.0
            }

        probs = r2_successful['probability'].values

        aggregated = {
            "mean_probability": float(np.mean(probs)),
            "median_probability": float(np.median(probs)),
            "std_probability": float(np.std(probs)),
            "min_probability": float(np.min(probs)),
            "max_probability": float(np.max(probs)),
            "n_groups": self.n_groups,
            "n_agents": len(r2_successful),
            "success_rate": len(r2_successful) / len(r2_forecasts),
            "mean_convergence": float(np.mean([g['convergence'] for g in group_aggregations]))
        }

        return aggregated

    def run_all_periods(self, periods: List[int] = None) -> pd.DataFrame:
        """
        Run all periods (1-10)

        Args:
            periods: List of periods to run (default: all 10)

        Returns:
            DataFrame with all forecasts
        """
        if periods is None:
            periods = list(range(1, 11))

        print("=" * 80)
        print("CONDITION 2: GENERIC DEBATE FORECASTERS")
        print("=" * 80)
        print(f"Total agents: {self.n_agents}")
        print(f"Groups: {self.n_groups} groups of {self.group_size}")
        print(f"Periods: {periods}")
        print(f"Model: {self.model}")
        print()

        all_forecasts = []
        aggregated_results = []

        for period in periods:
            # Run all groups for this period
            df_period, group_aggs = self.forecast_period(period)

            # Aggregate across groups
            aggregated = self.aggregate_across_groups(df_period, group_aggs)
            aggregated['period'] = period

            # Store results
            all_forecasts.append(df_period)
            aggregated_results.append(aggregated)

            # Save period results
            self._save_period_results(period, df_period, aggregated, group_aggs)

            print(f"[Condition 2] Period {period} Aggregated: "
                  f"mean={aggregated['mean_probability']:.3f}, "
                  f"median={aggregated['median_probability']:.3f}, "
                  f"convergence={aggregated['mean_convergence']:.3f}")

        # Combine all forecasts
        df_all = pd.concat(all_forecasts, ignore_index=True)

        # Save final results
        self._save_final_results(df_all, aggregated_results)

        print()
        print("=" * 80)
        print("[OK] Condition 2 Complete!")
        print("=" * 80)
        print(f"Total forecasts: {len(df_all)}")
        print(f"Success rate: {df_all['success'].mean()*100:.1f}%")
        print(f"Output directory: {self.output_dir}")
        print()

        # Print API statistics
        stats = self.forecaster.get_statistics()
        print("API Statistics:")
        print(f"  Total calls: {stats['total_calls']}")
        print(f"  Successful: {stats['successful_calls']}")
        print(f"  Failed: {stats['failed_calls']}")
        print(f"  Success rate: {stats['success_rate']*100:.1f}%")

        return df_all

    def _save_period_results(
        self,
        period: int,
        df: pd.DataFrame,
        aggregated: Dict,
        group_aggs: List[Dict]
    ):
        """Save results for a single period"""

        # All forecasts (both rounds)
        csv_file = self.output_dir / f"period_{period:02d}_all_forecasts.csv"
        df.to_csv(csv_file, index=False)

        # Per-group aggregations
        df_groups = pd.DataFrame(group_aggs)
        csv_groups = self.output_dir / f"period_{period:02d}_by_group.csv"
        df_groups.to_csv(csv_groups, index=False)

        # Overall aggregated
        json_file = self.output_dir / f"period_{period:02d}_aggregated.json"
        with open(json_file, 'w') as f:
            json.dump(aggregated, f, indent=2)

    def _save_final_results(
        self,
        df_all: pd.DataFrame,
        aggregated_results: List[Dict]
    ):
        """Save combined results"""

        # All forecasts
        csv_all = self.output_dir / "all_forecasts.csv"
        df_all.to_csv(csv_all, index=False)

        # Aggregated by period
        df_agg = pd.DataFrame(aggregated_results)
        csv_agg = self.output_dir / "all_forecasts_aggregated.csv"
        df_agg.to_csv(csv_agg, index=False)

        # Summary
        summary = {
            "condition": "generic_debate",
            "n_agents": self.n_agents,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "model": self.model,
            "total_forecasts": len(df_all),
            "successful_forecasts": int(df_all['success'].sum()),
            "success_rate": float(df_all['success'].mean()),
            "periods": df_agg['period'].tolist(),
            "mean_probabilities": df_agg['mean_probability'].tolist(),
            "convergence": df_agg['mean_convergence'].tolist(),
            "timestamp": datetime.now().isoformat()
        }

        json_summary = self.output_dir / "summary.json"
        with open(json_summary, 'w') as f:
            json.dump(summary, f, indent=2)


def main():
    """Run Condition 2"""

    forecaster = GenericDebateForecaster(
        n_agents=50,
        n_groups=10,
        parallel_groups=True,
        max_workers=5
    )

    df = forecaster.run_all_periods()

    return df


if __name__ == "__main__":
    main()
