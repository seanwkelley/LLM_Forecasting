"""
Condition 3: Personalized Independent Forecasters

N=100 personalized LLM agents (diverse personas) make independent forecasts.
Each agent has unique cognitive profile (demographics, personality, expertise, etc.)

Tests whether persona diversity improves forecasting without deliberation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import random

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forecasting.forecaster_base import BaseLLMForecaster, ForecastResponse
from forecasting.prompt_loader import load_period_prompt
from forecasting.persona_generator import load_personas, CognitiveProfile
from forecasting.config import (
    N_AGENTS_PERSONALIZED_INDEPENDENT,
    PERSONA_SYSTEM_PROMPT_PREFIX,
    PERSONA_SYSTEM_PROMPT_SUFFIX,
    DEFAULT_MODEL,
    RANDOM_SEED,
    get_output_dir
)


class PersonalizedIndependentForecaster:
    """
    Runs N=100 personalized independent forecasters
    """

    def __init__(
        self,
        n_agents: int = N_AGENTS_PERSONALIZED_INDEPENDENT,
        model: str = DEFAULT_MODEL,
        parallel: bool = True,
        max_workers: int = 10,
        random_seed: int = RANDOM_SEED
    ):
        """
        Initialize condition

        Args:
            n_agents: Number of personalized agents (default 100)
            model: LLM model to use
            parallel: Run forecasts in parallel
            max_workers: Max parallel workers
            random_seed: Seed for persona sampling (reproducibility)
        """
        self.n_agents = n_agents
        self.model = model
        self.parallel = parallel
        self.max_workers = max_workers
        self.random_seed = random_seed

        # Output directory
        self.output_dir = get_output_dir("condition_3_personalized_independent")

        # Load and sample personas
        print(f"[Condition 3] Loading personas...")
        all_personas = load_personas()

        # Sample N personas reproducibly
        random.seed(random_seed)
        self.personas = random.sample(all_personas, n_agents)
        random.seed()  # Reset seed

        print(f"[Condition 3] Sampled {len(self.personas)} diverse personas")

        # Base forecaster (will use different system prompts per agent)
        self.forecaster = BaseLLMForecaster(model=model)

        print(f"[Condition 3] Initialized with {n_agents} personalized agents")
        print(f"[Condition 3] Model: {model}")
        print(f"[Condition 3] Output: {self.output_dir}")

    def _build_persona_system_prompt(self, persona: CognitiveProfile) -> str:
        """
        Build system prompt incorporating persona description

        Args:
            persona: CognitiveProfile object

        Returns:
            Complete system prompt with persona
        """
        persona_desc = persona.to_natural_language()

        system_prompt = (
            PERSONA_SYSTEM_PROMPT_PREFIX +
            persona_desc +
            PERSONA_SYSTEM_PROMPT_SUFFIX
        )

        return system_prompt

    def forecast_single_agent(
        self,
        agent_idx: int,
        period: int,
        prompt: str
    ) -> Dict:
        """
        Generate forecast for a single personalized agent

        Args:
            agent_idx: Index into self.personas (0 to n_agents-1)
            period: Period number (1-10)
            prompt: Forecasting prompt

        Returns:
            Dictionary with forecast data
        """
        persona = self.personas[agent_idx]

        # Build persona-specific system prompt
        system_prompt = self._build_persona_system_prompt(persona)

        # Generate forecast
        forecast = self.forecaster.generate_forecast(prompt, system_prompt)

        # Package result with persona information
        result = {
            "condition": "personalized_independent",
            "period": period,
            "agent_id": f"personalized_{agent_idx:03d}",
            "persona_id": persona.persona_id,
            "persona_name": persona.name,

            # Demographics
            "age": persona.age,
            "gender": persona.gender,
            "education": persona.education,
            "occupation": persona.occupation,

            # Expertise
            "geopolitical_expertise": persona.geopolitical_expertise,
            "economic_expertise": persona.economic_expertise,
            "military_expertise": persona.military_expertise,
            "statistical_expertise": persona.statistical_expertise,

            # Cognitive measures
            "general_intelligence": persona.general_intelligence,
            "bayesian_updating_skill": persona.bayesian_updating_skill,
            "coherence_forecasting": persona.coherence_forecasting,
            "cognitive_reflection_test": persona.cognitive_reflection_test,
            "denominator_neglect": persona.denominator_neglect,
            "decision_rule_competence": persona.decision_rule_competence,

            # Preferences
            "risk_tolerance": persona.risk_tolerance,
            "political_leaning": persona.political_leaning,

            # Styles
            "thinking_style": persona.thinking_style,
            "information_processing": persona.information_processing,

            # Forecast
            "probability": forecast.probability,
            "confidence": forecast.confidence,
            "reasoning": forecast.reasoning,
            "timestamp": forecast.timestamp,
            "success": forecast.success,
            "error": forecast.error
        }

        return result

    def forecast_period(self, period: int) -> pd.DataFrame:
        """
        Generate forecasts for all N personalized agents for a single period

        Args:
            period: Period number (1-10)

        Returns:
            DataFrame with all forecasts
        """
        print(f"\n[Condition 3] Period {period}: Generating {self.n_agents} personalized forecasts...")

        # Load prompt
        prompt = load_period_prompt(period)

        forecasts = []

        if self.parallel:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self.forecast_single_agent,
                        agent_idx,
                        period,
                        prompt
                    ): agent_idx
                    for agent_idx in range(self.n_agents)
                }

                completed = 0
                for future in as_completed(futures):
                    agent_idx = futures[future]
                    try:
                        result = future.result()
                        forecasts.append(result)
                        completed += 1

                        if completed % 20 == 0 or completed == self.n_agents:
                            print(f"  Progress: {completed}/{self.n_agents} forecasts complete")

                    except Exception as e:
                        print(f"  [ERROR] Agent {agent_idx} failed: {str(e)}")
                        # Add failed result
                        persona = self.personas[agent_idx]
                        forecasts.append({
                            "condition": "personalized_independent",
                            "period": period,
                            "agent_id": f"personalized_{agent_idx:03d}",
                            "persona_id": persona.persona_id,
                            "probability": 0.5,
                            "confidence": "low",
                            "reasoning": f"Forecast failed: {str(e)}",
                            "timestamp": datetime.now().isoformat(),
                            "success": False,
                            "error": str(e)
                        })

        else:
            # Sequential execution
            for agent_idx in range(self.n_agents):
                result = self.forecast_single_agent(agent_idx, period, prompt)
                forecasts.append(result)

                if (agent_idx + 1) % 20 == 0:
                    print(f"  Progress: {agent_idx + 1}/{self.n_agents} forecasts complete")

        # Convert to DataFrame
        df = pd.DataFrame(forecasts)

        print(f"[Condition 3] Period {period}: Complete ({len(df)} forecasts)")

        return df

    def aggregate_forecasts(self, df: pd.DataFrame) -> Dict:
        """
        Aggregate individual forecasts using multiple methods

        Args:
            df: DataFrame with individual forecasts

        Returns:
            Dictionary with aggregated statistics
        """
        successful = df[df['success'] == True]

        if len(successful) == 0:
            return {
                "mean_probability": 0.5,
                "median_probability": 0.5,
                "std_probability": 0.0,
                "n_forecasts": 0,
                "n_successful": 0,
                "success_rate": 0.0
            }

        probabilities = successful['probability'].values

        # Confidence weights
        confidence_map = {"low": 1, "medium": 2, "high": 3}
        weights = successful['confidence'].map(confidence_map).values

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
            DataFrame with all forecasts
        """
        if periods is None:
            periods = list(range(1, 11))

        print("=" * 80)
        print("CONDITION 3: PERSONALIZED INDEPENDENT FORECASTERS")
        print("=" * 80)
        print(f"N agents: {self.n_agents} (diverse personas)")
        print(f"Periods: {periods}")
        print(f"Model: {self.model}")
        print(f"Random seed: {self.random_seed}")
        print()

        all_forecasts = []
        aggregated_results = []

        for period in periods:
            # Generate forecasts
            df_period = self.forecast_period(period)

            # Aggregate
            aggregated = self.aggregate_forecasts(df_period)
            aggregated['period'] = period

            # Store results
            all_forecasts.append(df_period)
            aggregated_results.append(aggregated)

            # Save period results
            self._save_period_results(period, df_period, aggregated)

            print(f"[Condition 3] Period {period} Aggregated: "
                  f"mean={aggregated['mean_probability']:.3f}, "
                  f"median={aggregated['median_probability']:.3f}, "
                  f"std={aggregated['std_probability']:.3f}")

        # Combine all forecasts
        df_all = pd.concat(all_forecasts, ignore_index=True)

        # Save combined results
        self._save_final_results(df_all, aggregated_results)

        print()
        print("=" * 80)
        print("[OK] Condition 3 Complete!")
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

        # Individual forecasts (with persona attributes)
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
        """Save combined results"""

        # All individual forecasts
        csv_all = self.output_dir / "all_forecasts_individual.csv"
        df_all.to_csv(csv_all, index=False)

        # Aggregated by period
        df_agg = pd.DataFrame(aggregated_results)
        csv_agg = self.output_dir / "all_forecasts_aggregated.csv"
        df_agg.to_csv(csv_agg, index=False)

        # Summary
        summary = {
            "condition": "personalized_independent",
            "n_agents": self.n_agents,
            "model": self.model,
            "random_seed": self.random_seed,
            "total_forecasts": len(df_all),
            "successful_forecasts": int(df_all['success'].sum()),
            "success_rate": float(df_all['success'].mean()),
            "periods": df_agg['period'].tolist(),
            "mean_probabilities": df_agg['mean_probability'].tolist(),
            "std_probabilities": df_agg['std_probability'].tolist(),
            "timestamp": datetime.now().isoformat()
        }

        json_summary = self.output_dir / "summary.json"
        with open(json_summary, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[Condition 3] Results saved to: {self.output_dir}")


def main():
    """Run Condition 3"""

    forecaster = PersonalizedIndependentForecaster(
        n_agents=100,
        parallel=True,
        max_workers=10
    )

    df = forecaster.run_all_periods()

    return df


if __name__ == "__main__":
    main()
