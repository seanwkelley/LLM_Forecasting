# Experiment Handover - February 11, 2026

## Project Overview

LLM-based forecasting in a geopolitical simulation (Novaris vs Tethys crisis). Two forecasting tasks:

1. **Action Prediction**: Which actions will each faction take? (binary probability per action, Brier score)
2. **Collapse Probability Forecasting**: What is the probability Tethys government collapses? (calibration)

Key innovation: **Information Sharding** - giving each agent a different random subset of context to create genuine ensemble diversity.

---

## Current State (Feb 11)

### In Progress

#### Multi-Scenario Experiment
- **Data generation:** `generate_multiscenario_dataset.R` - 100 parametrically varied scenarios (Latin Hypercube Sampling), currently running (~25 hours, resume-capable)
- **Forecasting:** `run_multiscenario_experiment.py` - N=10 agents x 100 scenarios, paired baseline vs sharding
- **Analysis:** `analyze_multiscenario_results.py` - Statistical tests, parameter analysis, visualization
- **Design doc:** `docs/MULTISCENARIO_EXPERIMENT.md`
- **Power:** 97% power to detect d=0.42 with N=100 scenarios (from real data estimate)

#### Persona-Rewrite Experiment
- **Script:** `run_persona_rewrite_experiment.py` - 2x3 factorial (context type x sharding strategy)
- **Cache:** 1,974 persona rewrites pre-generated in `outputs/persona_rewrite_cache/`
- **Status:** Ready to run

### Completed Experiments

#### 1. Action Prediction (Period 1)
- **Script**: `run_experiment_periods_1_3.py` (archived)
- **Results** (Period 1, Ensemble F1): Generic 0.444, Simplified 0.444, Complex 0.444 (Novaris)

#### 2. Action Prediction with Information Sharding (Period 1)
- **Script**: `run_information_sharding_experiment.py`
- **Results**: Novaris F1 improved 0.444 -> 0.600 (+35%)

#### 3. Action Probability Prediction with Sharding (Periods 1-3)
- **Script**: `run_action_probability_experiment.py`
- **Results**: N=1,800 predictions, 3-10% improvement (p=0.128, suggestive)

#### 4. Collapse Probability with Sharding (Periods 1-3)
- **Script**: `run_collapse_sharding_comparison.py`
- **Three conditions**: Baseline, Shard Everything, Shard Initial Only
- **Results**:

| Period | Truth | Baseline Brier | Shard Everything Brier | Shard Initial Brier |
|--------|-------|----------------|----------------------|---------------------|
| 1      | 0.220 | 0.0055         | **0.0026**           | 0.0040              |
| 2      | 0.280 | 0.0126         | **0.0000**           | 0.0114              |
| 3      | 0.360 | 0.0286         | **0.0040**           | 0.0231              |
| **Avg**|       | 0.0156         | **0.0022**           | 0.0128              |

- **Winner: Shard Everything** (+85.9% better than baseline)

---

## Key Finding: Information Sharding

**Insight**: When all agents see the same prompt, they converge on the same (potentially wrong) answer. Information sharding creates genuine cognitive diversity.

**How it works**:
1. Split context into atomic chunks (hybrid: line-based for structured data, sentence-based for prose)
2. Each agent draws an information fraction from Uniform(0.05, 0.95)
3. That fraction of chunks is randomly sampled (order preserved)
4. Instructions are NEVER sharded - always complete
5. Ensemble average of all predictions

**Why it works**:
- Prevents overconfident consensus
- Different agents focus on different aspects of the scenario
- Agents with partial information are less anchored to surface-level cues
- Ensemble averaging recovers signal, cancels noise

**Two sharding strategies**:
- **Shard Everything**: Mix all prompt sections, sample randomly. Best performer.
- **Shard Initial Only**: Shard the backstory, keep factual history intact. Moderate improvement.

---

## Active Code Files

### Core Infrastructure
```
forecasting/
  config.py                          # API keys (OPENROUTER_API_KEY), model config
  forecaster_base.py                 # LLM API calls via OpenRouter (deepseek/deepseek-v3.2)
  action_library.py                  # 69-action library, 7 domains
  action_ground_truth.py             # Load ground truth actions from CSVs
  ensemble_aggregation.py            # threshold_capped_ensemble(), adaptive_threshold_ensemble()
  simulation_data.py                 # State/events data for periods 1-5
```

### Information Sharding
```
forecasting/
  information_sharding.py            # Core: split_into_chunks(), shard_information(), create_information_distribution()
  sharding_strategies.py             # shard_everything_strategy(), shard_initial_only_strategy(), apply_sharding_strategy()
  collapse_prompts_with_scenario.py  # INITIAL_SCENARIO constant + get_prompt_sections()
  action_probability_prompts.py      # Action probability prediction prompts
```

### Experiment Scripts
```
forecasting/
  run_multiscenario_experiment.py       # Multi-scenario experiment (N=10 x 100 scenarios)
  run_persona_rewrite_experiment.py     # 2x3 factorial persona-rewrite experiment
  run_collapse_sharding_comparison.py   # 3-condition collapse probability comparison
  run_action_probability_experiment.py  # Action probability with sharding
  run_information_sharding_experiment.py # Action prediction with sharding
  analyze_multiscenario_results.py      # Multi-scenario statistical analysis
```

### Persona & Rewriting
```
forecasting/
  persona_rewrite.py                 # Context rewriting through persona lens (disk-cached)
  persona_generator.py               # CognitiveProfile (24 attributes), 500 personas
  persona_simplified.py              # SimplifiedProfile (6 attributes), 500 personas
  persona_profiles.json              # 500 complex persona profiles
  persona_profiles_simplified.json   # 500 simplified persona profiles
```

### R Data Generation
```
(top level)
  generate_multiscenario_dataset.R   # 100 parametric scenarios (LHS, resume-capable)
  run_simulation_with_actions.R      # 10-period simulation
  config.R                           # R simulation configuration
```

---

## Data & Ground Truth

### Ground Truth Sources
- **Actions**: `ground_truth_actions.json` - approved actions per period per faction
- **Collapse probability**: `outputs/assessments.csv` - P(collapse) by period
  - P1=0.220, P2=0.280, P3=0.360, P4=0.420, P5=0.320

### Simulation Data
- **State variables**: territory, GDP (both), military_balance, international_support, sanctions_level
- **Events**: External events per period
- **Initial scenario**: Rich backstory in `collapse_prompts_with_scenario.py::INITIAL_SCENARIO`
  - Extracted from `outputs/human_forecasting/TRUE/period_01.txt`
  - Contains: crisis description, timeline, military/economic/diplomatic situation, key actors

### Important: Data Leakage Prevention
Historical summaries shown to agents include ONLY observable variables:
- Territory controlled, GDP, military balance, international support, sanctions
- Events and actions taken
- **NOT included**: collapse probability (target variable), crisis level (meta-evaluation)

---

## Output Directories

```
outputs/
  multiscenario/                     # 100-scenario ground truth & per-scenario interactions
    scenarios.csv                      # Parameter sets
    ground_truth.csv                   # Collapse probabilities (incremental)
    scenario_001/ ... scenario_100/    # Per-scenario interaction files
  multiscenario_forecasting/         # Multi-scenario forecasting results
  persona_rewrite_cache/             # Cached persona rewrites (1,974)
  persona_rewrite_experiment/        # Persona-rewrite experiment results
  collapse_sharding_comparison/      # 3-condition sharding results
  action_probability_experiment/     # Action probability results
  collapse_sharding_periods_1_5/     # 5-period results
```

## Archived Code

```
archive/
  analysis_scripts/                  # One-off analysis & power analysis utilities
  old_experiment_runners/            # Superseded experiment scripts
  r_utilities/                       # R validation & extraction tools
  session_notes/                     # Session summaries & cleanup logs
  old_tests/                         # Early test scripts
  old_experiments/                   # Old experiment runners
```

---

## Running Experiments

### Prerequisites
```bash
# Set API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# Verify
cd D:/Northeastern/LLM_Forecasting
python -c "from forecasting.config import OPENROUTER_API_KEY; print('OK' if OPENROUTER_API_KEY else 'MISSING')"
```

### Run Collapse Sharding Comparison (MAIN experiment)
```bash
cd D:/Northeastern/LLM_Forecasting
python -u forecasting/run_collapse_sharding_comparison.py
```
- Runs 3 conditions x 3 periods = 9 debates
- N=100 agents per condition
- Duration: ~25-30 minutes
- Model: DeepSeek V3.2 via OpenRouter
- Cost: ~$0.50-1.00

### Run Action Prediction
```bash
python -u forecasting/run_experiment_periods_1_3.py
```

---

## Known Issues

1. **`action_prompts.py` stale action names** (LOW priority): References old action names in threat assessment text. Won't crash but threat assessment less accurate.

2. **Shard Initial Only underperforms**: Despite the hypothesis that shared factual history + diverse framing would help, sharding everything works better. Suggests the diversity benefit outweighs the continuity benefit.

3. **Period 5 ground truth anomaly**: Collapse probability DECREASES from 0.42 to 0.32 despite worsening conditions. All agents overpredict for P5.

---

## Next Steps

### Immediate
1. **Complete 100-scenario generation** (~25 hours, running now)
2. **Run multi-scenario forecasting experiment** (N=10 agents x 100 scenarios)
3. **Run persona-rewrite 2x3 factorial experiment**
4. **Analyze interaction effects** (persona rewriting x sharding)

### Research Questions Still Open
1. Does sharding advantage persist across diverse scenarios? (multi-scenario experiment)
2. Does persona rewriting add orthogonal diversity to sharding? (persona-rewrite experiment)
3. Which persona traits correlate with forecast accuracy?
4. Cross-model validation: Does sharding help with other LLMs?
5. How does ensemble size (N) affect sharding benefit?

### Paper-Ready Analysis Needed
1. Statistical significance across 100 scenarios (paired t-test, effect sizes)
2. Parameter sensitivity analysis (which scenario parameters moderate sharding benefit?)
3. Persona trait analysis (Big Five x accuracy correlation)
4. Calibration plots (predicted vs actual collapse probability)

---

## Key Methodological Insights

1. **Ensemble aggregation vs individual averaging**: Produces 3x different performance estimates. Always aggregate predictions first, then score.
2. **Personas hurt individual performance** (-35% to -42%) but create diversity for ensemble benefit.
3. **Information sharding** creates genuine cognitive diversity without persona complexity.
4. **Hybrid chunk splitting** (line-based for structured data, sentence-based for prose) ensures fine-grained sharding across all content types.
