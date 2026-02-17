# Multi-Scenario Forecasting Experiment

Tests forecasting performance across 100 parametrically varied crisis scenarios.

## Overview

**Goal**: Test whether information sharding improves forecasting accuracy and robustness across diverse strategic situations.

**Design**:
- 100 scenarios with varied initial parameters (territory, sanctions, support, etc.)
- Same backstory (Tethys-Novaris), different strategic situations
- Each scenario simulated for 1 period → ground truth outcomes
- 3 forecasting conditions × N=100 agents per scenario

**Advantages over single-scenario design**:
- 100× more statistical power
- Tests robustness across scenario diversity
- Cleaner than different backstories (controlled variation)
- Independent observations (different parameters + stochastic events)

## Workflow

### Step 1: Generate Scenarios (R)

Generate 100 scenarios and run simulations:

```bash
cd D:\Northeastern\LLM_Forecasting
export OPENROUTER_API_KEY="your_key_here"
Rscript generate_multiscenario_dataset.R
```

**Duration**: ~10-15 hours (100 simulations × ~6-10 min each)

**Outputs**:
- `outputs/multiscenario/scenarios.csv` - Parameter configurations
- `outputs/multiscenario/ground_truth.csv` - Actions and collapse probabilities
- `outputs/multiscenario/scenario_*.rds` - Detailed simulation states

**Test first** (3 scenarios):
```r
# Edit generate_multiscenario_dataset.R line ~430:
scenarios <- generate_scenario_parameters(n_scenarios = 3, seed = 42)
```

### Step 2: Run Forecasting Experiments (Python)

Run forecasting across all scenarios and conditions:

```bash
export OPENROUTER_API_KEY="your_key_here"
cd D:\Northeastern\LLM_Forecasting
python -u forecasting/run_multiscenario_experiment.py
```

**Duration**: ~12-15 hours (100 scenarios × 3 conditions × 100 agents)

**Outputs**:
- `outputs/multiscenario_forecasting/experiment_results_YYYYMMDD_HHMMSS.csv`
- `outputs/multiscenario_forecasting/summary_YYYYMMDD_HHMMSS.csv`

**Test first** (3 scenarios, 2 conditions, N=5):
```bash
python -u forecasting/run_multiscenario_experiment.py --test
```

**Run subset**:
```bash
# First 20 scenarios only
python -u forecasting/run_multiscenario_experiment.py --n-scenarios 20

# Specific conditions only
python -u forecasting/run_multiscenario_experiment.py --conditions baseline shard_everything
```

### Step 3: Analyze Results (Python)

Analyze forecasting performance:

```bash
python forecasting/analyze_multiscenario_results.py outputs/multiscenario_forecasting/experiment_results_*.csv
```

**Outputs**:
- Console summary with statistics
- `multiscenario_main_effect.png` - Condition comparison
- `multiscenario_interaction.png` - Condition × scenario interaction
- `multiscenario_robustness.png` - Consistency across scenarios

## Scenario Generation

### Parameter Ranges

Scenarios vary across realistic ranges:

| Parameter | Min | Max | Description |
|-----------|-----|-----|-------------|
| `territory_controlled` | 0% | 40% | Territory under aggressor control |
| `military_balance` | -0.3 | 0.1 | -1=aggressor advantage, +1=defender |
| `sanctions_level` | 0% | 80% | Economic sanctions on aggressor |
| `international_support` | 30% | 90% | Diplomatic support for defender |
| `crisis_level` | 3 | 10 | Severity of crisis (1-10 scale) |
| `novaris_gdp` | $70B | $100B | Aggressor economic strength |
| `tethys_gdp` | $15B | $30B | Defender economic strength |

### Sampling Method

Uses **Latin Hypercube Sampling** (if `lhs` package available) for efficient coverage of parameter space. Fallback: simple random sampling.

### Why These Ranges?

- **Territory 0-40%**: Covers pre-invasion → critical phases
- **Military balance -0.3 to 0.1**: Aggressor advantage, but not overwhelming
- **Sanctions 0-80%**: From none to severe (but not complete isolation)
- **Support 30-90%**: From isolated to strongly backed
- **Crisis 3-10**: Elevated tension to imminent collapse

## Forecasting Conditions

### 1. Baseline
- **Info**: 100% of all sections, original backstory
- **Purpose**: Performance ceiling with full information

### 2. Shard Everything
- **Info**: 10-100% sampled from all data sections
- **Purpose**: Test ensemble wisdom across info levels

### 3. Shard Initial Only
- **Info**: 10-100% of initial scenario, 100% of current data
- **Purpose**: Test whether backstory detail matters

### 4. Reframe (v3.9.0)
- **Info**: 100% of all sections, but backstory varies per agent
- **Backstory variants**: 6 framings of same facts (original, aggressor, vulnerability, escalation, domestic, inertia)
- **Assignment**: Agent `i` gets `BACKSTORY_VARIANTS[i % 6]`
- **Purpose**: Break shared anchoring bias from Tethys-resilient backstory
- **Results**: MSE 0.021-0.023 vs baseline 0.055-0.057 (**-58% to -61%**)

### 5. Domain Shard
- **Info**: Each agent sees only one domain (military, economic, diplomatic, crisis, intelligence)
- **Purpose**: Test information asymmetry as source of diversity
- **Results**: MSE 0.137 (+143% vs baseline) — partial info causes agents to default to low predictions

## Metrics

### Primary: Collapse Probability
- **Brier score**: (predicted_prob - true_prob)²
- **Lower = better** (perfect = 0, random = 0.25)
- Aggregated across 100 scenarios

### Secondary: Action Prediction
*(Future implementation)*
- Novaris action accuracy
- Tethys action accuracy
- F1 score for multi-action prediction

## Key Research Questions

1. **Does backstory reframing reduce anchoring bias?**
   - Finding: YES — reframe MSE 0.021-0.023 vs baseline 0.055-0.057 (58-61% reduction)
   - Mechanism: Different editorial framings break shared low-probability anchor

2. **Does information sharding improve forecasts?**
   - Finding: NO — domain sharding MSE 0.137 (+143% vs baseline)
   - Agents with partial information default to low predictions

3. **Does information sharding (shard_everything) improve forecasts?**
   - Hypothesis: Shard_everything < Baseline (ensemble wisdom)

4. **Robustness**: Does reframe improvement hold across scenarios?
   - Finding: 50/50 win rate between reframe and baseline, but much lower MSE on average

5. **Mechanism**: Why does reframing help?
   - The backstory is ~80% of the prompt and frames Tethys as resilient
   - Vulnerability and escalation variants pull predictions upward
   - Ensemble mean shifts closer to ground truth (~0.58)
   - Limitation: Most improvement comes as uniform upward shift, not scenario-adaptive debiasing
   - Limitation: Inertia variant is degenerate (always outputs 0.42); Aggressor is nearly degenerate (std=0.041)

## Experimental Results (February 2026)

### Condition Comparison (50 scenarios, 10 agents, 4 models)

| Condition | MSE | vs Baseline | p-value |
|-----------|-----|-------------|---------|
| Baseline | 0.0550-0.0572 | — | — |
| **Reframe** | **0.0214-0.0229** | **-58% to -61%** | **<0.0001** |
| Domain shard | 0.1367 | +143% | <0.0001 |

### Per-Variant Diagnostics (Reframe condition)

| Variant | Mean Prob | Std | Responsiveness |
|---------|----------|-----|----------------|
| Original | 0.363 | 0.082 | Moderate |
| Aggressor | 0.560 | 0.041 | Nearly degenerate |
| Vulnerability | 0.478 | 0.110 | **Best — well calibrated** |
| Escalation | 0.386 | 0.096 | Moderate |
| Domestic | 0.418 | 0.084 | Moderate |
| Inertia | 0.420 | 0.000 | **Completely degenerate** |

### Key Insights
- Reframe works by pulling ensemble mean from ~0.35 toward truth (~0.58)
- The improvement is largely a **uniform upward shift** rather than scenario-adaptive
- Vulnerability is the only variant that is both well-calibrated AND responsive to scenario data
- Median aggregation slightly better than mean (MSE 0.0202 vs 0.0234)
- Domain sharding makes things substantially worse — agents with partial info default to low probabilities

## Computational Cost

### Scenario Generation (R)
- **API calls**: ~600-800 per scenario (action decisions, coordination, assessment)
- **Total**: ~60,000-80,000 calls for 100 scenarios
- **Cost**: ~$200-300 (using Llama 3.1 8B)
- **Duration**: ~10-15 hours

### Forecasting (Python)
- **API calls**: 100 scenarios × 3 conditions × 100 agents = 30,000 calls
- **Cost**: ~$15-20 (using DeepSeek v3.2)
- **Duration**: ~12-15 hours

### Total
- **Cost**: ~$215-320
- **Duration**: ~22-30 hours (can run sequentially overnight + next day)

## Optimization Strategies

### For Development
1. **Test subset**: 5 scenarios, 2 conditions, N=10 agents (~30 min, $2)
2. **Partial run**: 20 scenarios, all conditions, N=50 agents (~3 hours, $30)
3. **Sequential**: Generate 10 scenarios, forecast, analyze, then continue

### For Production
1. **Parallel**: Run scenario generation and previous scenario forecasting simultaneously
2. **Checkpointing**: Save after each scenario (resume-safe)
3. **Batch processing**: Process scenarios in batches of 10

## File Structure

```
D:\Northeastern\LLM_Forecasting\
├── generate_multiscenario_dataset.R     # Scenario generation + simulation
├── forecasting/
│   ├── run_multiscenario_experiment.py  # Forecasting experiments
│   └── analyze_multiscenario_results.py # Analysis
├── outputs/
│   ├── multiscenario/                   # Scenario data + ground truth
│   │   ├── scenarios.csv
│   │   ├── ground_truth.csv
│   │   └── scenario_*.rds
│   └── multiscenario_forecasting/       # Forecasting results
│       ├── experiment_results_*.csv
│       └── summary_*.csv
└── MULTISCENARIO_EXPERIMENT.md          # This file
```

## Troubleshooting

### R simulation fails
- Check API key: `Sys.getenv("OPENROUTER_API_KEY")`
- Check package installations: `jsonlite`, `uuid`, `lhs` (optional)
- Review error in scenario RDS files

### Python forecasting fails
- Check API key: `echo $OPENROUTER_API_KEY`
- Verify ground truth exists: `outputs/multiscenario/ground_truth.csv`
- Check for high fallback rates (>20% suggests API issues)

### Low diversity across scenarios
- Check scenario parameters: `outputs/multiscenario/scenarios.csv`
- Verify parameter ranges in `generate_scenario_parameters()`
- Consider increasing parameter ranges

## R Simulation: Parameter Sensitivity (v3.9.0)

The R simulation agents were insensitive to scenario parameters because:
1. `format_situation_for_agent()` converted numbers to categories, hiding fine-grained differences
2. `international_support` was completely invisible to agents
3. Proposal/approval prompts only received `crisis_level` + 200 chars of narrative

**Fix (v3.9.0):** Added exact numeric values alongside worldview-filtered interpretations, added `international_support`, and passed all 5 parameters to proposal and approval prompts.

**Sensitivity test results (3 contrasting 1-period scenarios):**
- Novaris action overlap (low vs high): **33%** (was near-100%)
- Tethys action overlap (low vs high): **25%** (was near-100%)
- Collapse probability range: 0.385–0.635

## Future Extensions

1. **More scenarios**: Increase to 200-500 for even higher power
2. **Action prediction**: Forecast Novaris/Tethys actions, not just collapse
3. **Temporal**: Multi-period forecasting with updating
4. **Cross-domain**: Different conflict types (not just Tethys-Novaris)
5. **Persona variation**: Test persona-rewrite approach on multi-scenario design
6. **Fix degenerate backstory variants**: Inertia and Aggressor need reworking to be scenario-responsive
7. **Regenerate ground truth dataset**: Re-run 100-scenario dataset with v3.9.0 parameter-sensitive agents
