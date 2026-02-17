"""
Run Condition 3 (Personalized Independent) with ENHANCED prompts

Tests if better information leads to better tracking
"""

import sys
sys.path.insert(0, 'D:/Northeastern/LLM_Forecasting')

import pandas as pd
import numpy as np
from pathlib import Path
from forecasting.forecaster_base import BaseLLMForecaster
from forecasting.prompt_loader import load_period_prompt
from forecasting.persona_generator import load_personas
from forecasting.config import (
    N_AGENTS_PERSONALIZED_INDEPENDENT,
    PERSONA_SYSTEM_PROMPT_PREFIX,
    PERSONA_SYSTEM_PROMPT_SUFFIX,
    DEFAULT_MODEL,
    RANDOM_SEED
)
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

print("=" * 80)
print("CONDITION 3 WITH ENHANCED PROMPTS")
print("=" * 80)
print("Using enhanced prompts with KEY_FACTORS analysis")
print(f"N=100 personalized agents, all 10 periods")
print()

# Setup
ENHANCED_PROMPTS_DIR = "D:/Northeastern/LLM_Forecasting/outputs/human_forecasting/ENHANCED"
output_dir = Path("D:/Northeastern/LLM_Forecasting/outputs/forecasting_results/condition_3_personalized_independent_ENHANCED")
output_dir.mkdir(parents=True, exist_ok=True)

# Load personas
all_personas = load_personas()
random.seed(RANDOM_SEED)
personas = random.sample(all_personas, 100)
random.seed()

# Initialize forecaster
forecaster = BaseLLMForecaster(model=DEFAULT_MODEL)

print(f"Sampled {len(personas)} diverse personas")
print(f"Model: {DEFAULT_MODEL}")
print(f"Output: {output_dir}")
print()

all_forecasts = []
aggregated_results = []

for period in range(1, 11):
    print(f"\n[Condition 3 Enhanced] Period {period}: Generating 100 personalized forecasts...")

    # Load enhanced prompt
    prompt = load_period_prompt(period, prompts_dir=ENHANCED_PROMPTS_DIR)

    forecasts = []

    # Parallel execution
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for agent_idx in range(100):
            persona = personas[agent_idx]

            # Build persona system prompt
            persona_desc = persona.to_natural_language()
            system_prompt = (
                PERSONA_SYSTEM_PROMPT_PREFIX +
                persona_desc +
                PERSONA_SYSTEM_PROMPT_SUFFIX
            )

            # Submit forecast task
            future = executor.submit(forecaster.generate_forecast, prompt, system_prompt)
            futures[future] = (agent_idx, persona)

        # Collect results
        completed = 0
        for future in as_completed(futures):
            agent_idx, persona = futures[future]
            try:
                forecast = future.result()
                forecasts.append({
                    "condition": "personalized_independent_enhanced",
                    "period": period,
                    "agent_id": f"personalized_{agent_idx:03d}",
                    "persona_id": persona.persona_id,
                    "persona_name": persona.name,
                    "probability": forecast.probability,
                    "confidence": forecast.confidence,
                    "reasoning": forecast.reasoning,
                    "timestamp": forecast.timestamp,
                    "success": forecast.success,
                    "error": forecast.error,
                    # Persona attributes
                    "age": persona.age,
                    "gender": persona.gender,
                    "education": persona.education,
                    "occupation": persona.occupation,
                    "geopolitical_expertise": persona.geopolitical_expertise,
                    "bayesian_updating_skill": persona.bayesian_updating_skill,
                    "general_intelligence": persona.general_intelligence,
                    "risk_tolerance": persona.risk_tolerance
                })
                completed += 1

                if completed % 20 == 0 or completed == 100:
                    print(f"  Progress: {completed}/100 forecasts complete")

            except Exception as e:
                print(f"  [ERROR] Agent {agent_idx} failed: {str(e)}")

    # Convert to DataFrame
    df_period = pd.DataFrame(forecasts)
    all_forecasts.append(df_period)

    # Aggregate
    successful = df_period[df_period['success'] == True]
    probabilities = successful['probability'].values

    aggregated = {
        "period": period,
        "mean_probability": float(np.mean(probabilities)),
        "median_probability": float(np.median(probabilities)),
        "std_probability": float(np.std(probabilities)),
        "n_successful": len(successful),
        "success_rate": len(successful) / len(df_period)
    }
    aggregated_results.append(aggregated)

    # Save period results
    csv_file = output_dir / f"period_{period:02d}_individual.csv"
    df_period.to_csv(csv_file, index=False)

    json_file = output_dir / f"period_{period:02d}_aggregated.json"
    with open(json_file, 'w') as f:
        json.dump(aggregated, f, indent=2)

    print(f"[Condition 3 Enhanced] Period {period} Aggregated: "
          f"mean={aggregated['mean_probability']:.3f}, "
          f"median={aggregated['median_probability']:.3f}, "
          f"std={aggregated['std_probability']:.3f}")

# Combine all forecasts
df_all = pd.concat(all_forecasts, ignore_index=True)

# Save final results
csv_all = output_dir / "all_forecasts_individual.csv"
df_all.to_csv(csv_all, index=False)

df_agg = pd.DataFrame(aggregated_results)
csv_agg = output_dir / "all_forecasts_aggregated.csv"
df_agg.to_csv(csv_agg, index=False)

print()
print("=" * 80)
print("[OK] Condition 3 with enhanced prompts complete!")
print("=" * 80)
print(f"Total forecasts: {len(df_all)}")
print(f"Success rate: {df_all['success'].mean()*100:.1f}%")
print(f"Output directory: {output_dir}")
print()

# Print API statistics
stats = forecaster.get_statistics()
print("API Statistics:")
print(f"  Total calls: {stats['total_calls']}")
print(f"  Successful: {stats['successful_calls']}")
print(f"  Failed: {stats['failed_calls']}")
print(f"  Success rate: {stats['success_rate']*100:.1f}%")
print()
print("=" * 80)
