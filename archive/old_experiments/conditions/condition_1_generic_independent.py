"""
Condition 1: Generic Independent Forecasters

N=100 generic LLM agents make independent forecasts (no communication).
Provides baseline for comparing other conditions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forecasting.forecaster_base import BaseLLMForecaster, ForecastResponse
from forecasting.prompt_loader import load_period_prompt
from forecasting.config import (
    N_AGENTS_GENERIC_INDEPENDENT,
    GENERIC_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    get_output_dir
)


class GenericIndependentForecaster:
    """
    Runs N=100 generic independent forecasters on all periods
    """

    def __init__(
        self,
        n_agents: int = N_AGENTS_GENERIC_INDEPENDENT,
        model: str = DEFAULT_MODEL,
        parallel: bool = True,
        max_workers: int = 10
    ):
        """
        Initialize condition

        Args:
            n_agents: Number of independent agents (default 100)
            model: LLM model to use
            parallel: Run forecasts in parallel (faster)
            max_workers: Max parallel workers
        """
        self.n_agents = n_agents
        self.model = model
        self.parallel = parallel
        self.max_workers = max_workers

        # Output directory
        self.output_dir = get_output_dir("condition_1_generic_independent")

        # Initialize base forecaster (reused for all agents)
        self.forecaster = BaseLLMForecaster(
            model=model,
            system_prompt=GENERIC_SYSTEM_PROMPT
        )

        print(f"[Condition 1] Initialized with {n_agents} generic agents")
        print(f"[Condition 1] Model: {model}")
        print(f"[Condition 1] Output: {self.output_dir}")

    def forecast_single_agent(
        self,
        agent_id: int,
        period: int,
        prompt: str
    ) -> Dict:
        """
        Generate forecast for a single agent

        Args:
            agent_id: Agent identifier (0 to n_agents-1)
            period: Period number (1-10)
            prompt: Forecasting prompt

        Returns:
            Dictionary with forecast data
        """
        # Generate forecast
        forecast = self.forecaster.generate_forecast(prompt)

        # Package result
        result = {
            "condition": "generic_independent",
            "period": period,
            "agent_id": f"generic_{agent_id:03d}",
            "persona_id": None,  # No persona for generic agents
            "probability": forecast.probability,
            "confidence": forecast.confidence,
            "reasoning": forecast.reasoning,
            "timestamp": forecast.timestamp,
            "success": forecast.success,
            "error": forecast.error,
            "raw_response": forecast.raw_response
        }

        return result

    def forecast_period(self, period: int) -> pd.DataFrame:
        """
        Generate forecasts for all N agents for a single period

        Args:
            period: Period number (1-10)

        Returns:
            DataFrame with all forecasts
        """
        print(f"\n[Condition 1] Period {period}: Generating {self.n_agents} forecasts...")

        # Load prompt
        prompt = load_period_prompt(period)

        forecasts = []

        if self.parallel:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(
                        self.forecast_single_agent,
                        agent_id,
                        period,
                        prompt
                    ): agent_id
                    for agent_id in range(self.n_agents)
                }

                # Collect results with progress
                completed = 0
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        result = future.result()
                        forecasts.append(result)
                        completed += 1

                        # Progress indicator
                        if completed % 20 == 0 or completed == self.n_agents:
                            print(f"  Progress: {completed}/{self.n_agents} forecasts complete")

                    except Exception as e:
                        print(f"  [ERROR] Agent {agent_id} failed: {str(e)}")
                        # Add failed result
                        forecasts.append({
                            "condition": "generic_independent",
                            "period": period,
                            "agent_id": f"generic_{agent_id:03d}",
                            "persona_id": None,
                            "probability": 0.5,
                            "confidence": "low",
                            "reasoning": f"Forecast failed: {str(e)}",
                            "timestamp": datetime.now().isoformat(),
                            "success": False,
                            "error": str(e),
                            "raw_response": ""
                        })

        else:
            # Sequential execution (for debugging)
            for agent_id in range(self.n_agents):
                result = self.forecast_single_agent(agent_id, period, prompt)
                forecasts.append(result)

                if (agent_id + 1) % 20 == 0:
                    print(f"  Progress: {agent_id + 1}/{self.n_agents} forecasts complete")

        # Convert to DataFrame
        df = pd.DataFrame(forecasts)

        print(f"[Condition 1] Period {period}: Complete ({len(df)} forecasts)")

        return df

    def aggregate_forecasts(self, df: pd.DataFrame) -> Dict:
        """
        Aggregate individual forecasts using multiple methods

        Args:
            df: DataFrame with individual forecasts

        Returns:
            Dictionary with aggregated statistics
        """
        # Filter successful forecasts
        successful = df[df['success'] == True]

        if len(successful) == 0:
            return {
                "mean_probability": 0.5,
                "median_probability": 0.5,
                "std_probability": 0.0,
                "min_probability": 0.5,
                "max_probability": 0.5,
                "weighted_probability": 0.5,
                "n_forecasts": 0,
                "n_successful": 0,
                "success_rate": 0.0
            }

        probabilities = successful['probability'].values

        # Confidence weights: low=1, medium=2, high=3
        confidence_map = {"low": 1, "medium": 2, "high": 3}
        weights = successful['confidence'].map(confidence_map).values

        # Calculate aggregations
        aggregated = {
            "mean_probability": float(np.mean(probabilities)),
            "median_probability": float(np.median(probabilities)),
            "std_probability": float(np.std(probabilities)),
            "min_probability": float(np.min(probabilities)),
            "max_probability": float(np.max(probabilities)),
            "weighted_probability": float(np.average(probabilities, weights=weights)),
            "n_forecasts": len(df),
            "n_successful": len(successful),
            "success_rate": len(successful) / len(df)
        }

        return aggregated

    def run_all_periods(self, periods: List[int] = None) -> pd.DataFrame:
        """
        Run forecasts for all periods (1-10)

        Args:
            periods: List of periods to run (default: all 10)

        Returns:
            DataFrame with all individual forecasts
        """
        if periods is None:
            periods = list(range(1, 11))

        print("=" * 80)
        print("CONDITION 1: GENERIC INDEPENDENT FORECASTERS")
        print("=" * 80)
        print(f"N agents: {self.n_agents}")
        print(f"Periods: {periods}")
        print(f"Model: {self.model}")
        print()

        all_forecasts = []
        aggregated_results = []

        for period in periods:
            # Generate forecasts for this period
            df_period = self.forecast_period(period)

            # Aggregate
            aggregated = self.aggregate_forecasts(df_period)
            aggregated['period'] = period

            # Store results
            all_forecasts.append(df_period)
            aggregated_results.append(aggregated)

            # Save period results
            self._save_period_results(period, df_period, aggregated)

            print(f"[Condition 1] Period {period} Aggregated: "
                  f"mean={aggregated['mean_probability']:.3f}, "
                  f"median={aggregated['median_probability']:.3f}, "
                  f"std={aggregated['std_probability']:.3f}")

        # Combine all forecasts
        df_all = pd.concat(all_forecasts, ignore_index=True)

        # Save combined results
        self._save_final_results(df_all, aggregated_results)

        print()
        print("=" * 80)
        print("[OK] Condition 1 Complete!")
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
        aggregated: Dict
    ):
        """Save results for a single period"""

        # Individual forecasts
        csv_file = self.output_dir / f"period_{period:02d}_individual.csv"
        df.to_csv(csv_file, index=False)

        # Aggregated stats
        json_file = self.output_dir / f"period_{period:02d}_aggregated.json"
        with open(json_file, 'w') as f:
            json.dump(aggregated, f, indent=2)

    def _save_final_results(
        self,
        df_all: pd.DataFrame,
        aggregated_results: List[Dict]
    ):
        """Save combined results across all periods"""

        # All individual forecasts
        csv_all = self.output_dir / "all_forecasts_individual.csv"
        df_all.to_csv(csv_all, index=False)

        # All aggregated results
        df_agg = pd.DataFrame(aggregated_results)
        csv_agg = self.output_dir / "all_forecasts_aggregated.csv"
        df_agg.to_csv(csv_agg, index=False)

        # Summary statistics
        summary = {
            "condition": "generic_independent",
            "n_agents": self.n_agents,
            "model": self.model,
            "total_forecasts": len(df_all),
            "successful_forecasts": int(df_all['success'].sum()),
            "success_rate": float(df_all['success'].mean()),
            "periods": df_agg['period'].tolist(),
            "mean_probabilities": df_agg['mean_probability'].tolist(),
            "median_probabilities": df_agg['median_probability'].tolist(),
            "timestamp": datetime.now().isoformat()
        }

        json_summary = self.output_dir / "summary.json"
        with open(json_summary, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[Condition 1] Results saved to: {self.output_dir}")


def main():
    """Run Condition 1"""

    # Initialize
    forecaster = GenericIndependentForecaster(
        n_agents=100,
        parallel=True,
        max_workers=10
    )

    # Run all periods
    df = forecaster.run_all_periods()

    return df


if __name__ == "__main__":
    main()
