# LLM Forecasting Research

**Last Updated:** February 13, 2026
**Status:** Active Research

Python-based forecasting research infrastructure for the multi-agent wargame simulation. Tests whether information sharding, persona-based chain-of-thought bridging, analytical framework diversity, and multi-model ensembles improve ensemble forecast accuracy and prediction diversity.

---

## Current Experiments

### 1. Multi-Scenario Collapse Probability (COMPLETE)

Predicts the probability that the Tethys government collapses, across 50 parametrically varied crisis scenarios.

- **Design:** N=10 agents per scenario, paired baseline vs shard_everything
- **Model:** deepseek/deepseek-v3.2, temperature=1.0
- **Script:** `run_multiscenario_experiment.py`
- **Results:** `experiment_results/multiscenario_forecasting/experiment_results_20260212_093753.csv`

| Condition | Mean MSE | Std | Improvement |
|-----------|----------|-----|-------------|
| Baseline (full info) | 0.1764 | 0.059 | -- |
| Shard Everything | 0.1489 | 0.048 | **-15.6%** |

### 2. Action Prediction (IN PROGRESS)

Predicts whether each faction took specific actions (binary), using 5 sampled actions per scenario from a 68-action pool.

- **Design:** N=10 agents per action/faction/condition, 50 scenarios, multiple conditions
- **Model:** deepseek/deepseek-v3.2 (default), or multi-model pool
- **Script:** `run_action_prediction_experiment.py`
- **Output:** `experiment_results/action_prediction/`

**Conditions:**

| Condition | Sharding | Framework | Description |
|-----------|----------|-----------|-------------|
| `baseline` | none | generic | Generic system prompt, full info |
| `shard_everything` | shard | generic | Generic system prompt, sharded info |
| `pool_baseline` | none | composable pool | Framework pool, full info |
| `pool_shard` | shard | composable pool | Framework pool, sharded info |
| `persona_baseline` | none | persona | Persona-bridged CoT, full info |
| `persona_shard` | shard | persona | Persona-bridged CoT, sharded info |
| `calibrated_baseline` | none | calibrated | Base-rate-aware generic, full info |
| `calibrated_persona` | none | calibrated+persona | Base-rate-aware persona, full info |

**Action selection modes:**
- `--balanced`: Guarantees 2 taken + 3 not-taken actions per scenario (tests discrimination)
- Default: Pure random sampling from 68-action pool (creates ~84% negative class imbalance)

```bash
# Standard test
python -u forecasting/run_action_prediction_experiment.py --test

# Pool + multi-model + balanced
python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --test

# Full run
python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --n-scenarios 50 --n-agents 10
```

### 3. Persona + CoT Bridging (READY)

Tests whether connecting persona attributes to each chain-of-thought reasoning step produces meaningful prediction diversity. 2x2 factorial design.

- **Design:** N=10 agents, 50 scenarios, 4 conditions (2x2: generic/persona x baseline/shard)
- **Script:** `run_persona_cot_experiment.py`
- **Status:** Code complete and tested. Run persona conditions after action prediction finishes.

**Core innovation — bridging instruction:** Same 5 CoT steps as generic, but with a preamble instructing the model to filter each step through its persona's expertise and risk tolerance.

```bash
python -u forecasting/run_persona_cot_experiment.py --n-scenarios 50 --n-agents 10 --conditions persona_baseline persona_shard
```

### 4. Analytical Framework Diversity (IN PROGRESS)

Tests whether assigning each agent a distinct *analytical methodology* produces higher prediction diversity than persona-based approaches.

**Two modes:**

#### Fixed 10 Frameworks (original)

10 hardcoded analytical frameworks:
base_rate, key_indicator, scenario_tree, historical_analogy, worst_case, best_case, trend, structural, game_theoretic, devils_advocate

```bash
python -u forecasting/run_framework_experiment.py --test
python -u forecasting/run_framework_experiment.py --n-scenarios 50 --n-agents 10
```

#### Composable Framework Pool (new)

4 composable axes generating 1,000 unique combinations:

| Axis | Options | Purpose |
|------|---------|---------|
| **Method** (5) | base_rate, scenario_tree, historical_analogy, key_indicator, structural | Reasoning structure (CoT steps) |
| **Lens** (5) | threat_focused, resilience_focused, contrarian, loss_averse, detached | Interpretive bias (how ambiguity is read) |
| **Focus** (5) | military, economic, political, events, holistic | Evidence attention (which signals dominate) |
| **Bias** (8) | recency, anchoring, normalcy, availability, overconfidence, sunk_cost, confirmation, none | Cognitive distortion |

5 × 5 × 5 × 8 = **1,000 unique combinations**. Each scenario samples 10 from the pool (seeded by scenario_id for reproducibility).

**Defined in:** `framework_pool.py`

```bash
# Pool mode
python -u forecasting/run_framework_experiment.py --pool --test

# Pool + multi-model
python -u forecasting/run_framework_experiment.py --pool --multi-model --test

# Full run
python -u forecasting/run_framework_experiment.py --pool --multi-model --n-scenarios 50 --n-agents 10
```

**Multi-model pool** (6 models, `--multi-model` flag):
- `deepseek/deepseek-v3.2`
- `meta-llama/llama-3.3-70b-instruct`
- `google/gemini-2.5-flash`
- `mistralai/mistral-small-3.2-24b-instruct`
- `qwen/qwen-2.5-72b-instruct`
- `google/gemma-3-27b-it`

**Model comparison results (3-scenario pool test, Feb 13):**

| Model | Fallback Rate | Prediction Range | Per-scenario Std | Baseline MSE |
|-------|--------------|-----------------|-----------------|-------------|
| DeepSeek V3.2 | 3% | 0.08–0.85 | 0.135 | 0.117 |
| Llama 3.3 70B | **0%** | 0.12–0.85 | **0.277** | **0.018** |
| Gemini 3 Flash | 0% | 0.04–0.94 | 0.271 | 0.028 |
| Multi-model (3) | 0% | 0.12–0.85 | 0.262 | 0.029 |

**Key findings (Feb 13):**
- Framework diversity produces 2x the prediction spread of fixed-10 frameworks
- Lens axis is the primary diversity driver: resilience_focused clusters 0.12-0.18, threat_focused 0.72-0.82
- Model instruction-following is critical: DeepSeek ignores lens instructions, Llama/Gemini follow them
- Multi-model ensembles average model quality rather than improving it — Llama-only outperformed
- **Known limitation:** Lenses currently act as fixed multipliers rather than evidence-responsive filters. Threat-focused always outputs ~0.75 regardless of scenario data. See EXPERIMENT_NOTES.md for planned fix (evidence-first, lens-second prompt structure).

---

## Architecture

### Prompt Structure

All experiments use the same 4-section prompt structure:

1. **Initial Scenario** (`INITIAL_SCENARIO` in `collapse_prompts_with_scenario.py`): Rich backstory of the Tethys-Novaris crisis (~4K chars). Describes the geopolitical situation, military posture, economic factors, diplomatic context, key actors.

2. **Historical Summary**: Prior period context (empty for Period 1 experiments).

3. **Current Period Data**: Built from `outputs/multiscenario/scenario_events.json` and `scenarios.csv`. Includes:
   - Territory remaining, GDP (both factions), military balance, international support, sanctions level, crisis level
   - External events (from simulation)
   - External actor actions (from simulation)
   - Faction actions withheld (for prediction)

4. **Instructions**: Task framing + CoT steps + JSON output format. Variants:
   - **Generic CoT**: 5 reasoning steps (military, economic, diplomatic, crisis, probability)
   - **Persona-bridged CoT**: Same 5 steps + bridging preamble + per-step sub-bullets linking persona attributes
   - **Framework CoT**: Method-specific reasoning steps + lens calibration + focus priority + bias injection

**Instructions are NEVER sharded** — always delivered in full regardless of condition.

### Composable Framework Pool

**File:** `framework_pool.py`

Each agent's prompt is assembled from 4 non-overlapping axes:

```
System prompt = method identity + method description + lens description + focus description + [bias description]
CoT instructions = focus priority + method-specific steps + lens calibration + bias injection
```

**Key functions:**
- `compose_framework(method, lens, focus, bias)` — collapse probability variant
- `compose_action_framework(method, lens, focus, bias)` — action prediction variant (adapted CoT steps)
- `generate_pool()` / `generate_action_pool()` — all 1,000 combinations
- `sample_frameworks(n, seed)` / `sample_action_frameworks(n, seed)` — deterministic hash-based sampling

### Information Sharding

**What it is:** Each agent sees a random subset of context (5%-95%) to create genuine ensemble diversity.

**How it works:**
1. Combine data sections (scenario + history + current period data)
2. Split into atomic chunks using hybrid approach:
   - Line-based splitting for structured data (bullets, numbered lists, key:value pairs)
   - Sentence-based splitting for prose paragraphs
3. Each agent draws an information fraction from Uniform(0.05, 0.95)
4. That fraction of chunks is randomly sampled (order preserved)
5. Instructions appended in full (never sharded)
6. Ensemble average of all agent predictions

**Implementation:** `information_sharding.py` (splitting), `sharding_strategies.py` (strategy application)

**Strategy used:** `shard_everything` — all data sections combined and sharded together. Outperforms `shard_initial_only` (shard backstory, keep current data intact).

### Persona System

**Profile:** `SimplifiedProfile` in `persona_simplified.py` with 7 attributes:
- `name`, `occupation`
- `geopolitical_expertise` (0-100), `military_expertise` (0-100), `economic_expertise` (0-100)
- `strategic_orientation`: hawkish / dovish / pragmatic
- `risk_tolerance` (0-100): normal distribution with orientation-dependent mean (hawkish=60, dovish=40, pragmatic=50), sd=25, clamped [0,100]

**Pool:** 500 personas generated with seed=42. Stored in `persona_profiles_simplified.json`.

### Evaluation

- **Collapse probability:** Squared error (ensemble mean vs ground truth continuous probability)
- **Action prediction:** Brier score (ensemble mean probability vs binary ground truth)
- **Statistical tests:** Paired t-test, Wilcoxon signed-rank, Cohen's d (paired by scenario)
- **All results use incremental CSV saving** — safe to kill mid-run without data loss

---

## Active Files

### Core Infrastructure
| File | Purpose |
|------|---------|
| `config.py` | API keys (OpenRouter), model config, experimental parameters |
| `forecaster_base.py` | Base LLM forecaster class, API calls via OpenRouter |
| `information_sharding.py` | Chunk splitting, sharding, information distribution |
| `sharding_strategies.py` | `shard_everything`, `shard_initial_only`, `apply_sharding_strategy()` |
| `collapse_prompts_with_scenario.py` | `INITIAL_SCENARIO` constant, `get_prompt_sections()` |
| `framework_pool.py` | **NEW** — Composable framework pool (4 axes, 1000 combinations, collapse + action variants) |

### Persona System
| File | Purpose |
|------|---------|
| `persona_simplified.py` | `SimplifiedProfile` (7 attributes), generation, load/save |
| `persona_profiles_simplified.json` | 500 generated personas (seed=42) |

### Experiment Runners
| File | Purpose | Status |
|------|---------|--------|
| `run_multiscenario_experiment.py` | Collapse probability: baseline vs shard_everything | Complete |
| `run_action_prediction_experiment.py` | Action prediction: 8 conditions + pool + multi-model + balanced | In progress |
| `run_persona_cot_experiment.py` | Persona+CoT bridging: 2x2 factorial | Ready |
| `run_framework_experiment.py` | Framework diversity: fixed-10 or composable pool + multi-model | In progress |

### Analysis & Support
| File | Purpose |
|------|---------|
| `analyze_multiscenario_results.py` | Statistical analysis and visualization |
| `action_library.py` | 68-action space with descriptions |
| `action_ground_truth.py` | Extract ground truth actions from simulation CSVs |
| `simulation_data.py` | State and events data for periods 1-5 |
| `ensemble_aggregation.py` | Ensemble aggregation methods |
| `prompt_loader.py` | Load prompts from text files |

---

## Data Sources

### Ground Truth
- **Scenarios:** `outputs/multiscenario/scenarios.csv` — 100 parametric scenarios (Latin Hypercube Sampling over territory, GDP, military balance, international support, sanctions, crisis level)
- **Collapse probability:** `outputs/multiscenario/ground_truth.csv` — continuous P(collapse) per scenario, generated by weighted formula in R aggregator (6 components: military pressure, economic strain, political instability, external protection, institutional resilience, crisis momentum)
- **Actions:** `outputs/multiscenario/scenario_events.json` — actual faction actions and external events per scenario

### Generation
- **R simulation:** `generate_multiscenario_dataset.R` generates scenarios with `run_simulation_with_actions.R`
- **Aggregator model:** `google/gemini-3-flash-preview` scores 6 components (0-100), weighted formula produces P(collapse)
- **50 scenarios** currently have ground truth (of 100 total parameter sets)

---

## Output Structure

```
outputs/                                   # Simulation data (R-generated)
  multiscenario/                           # Ground truth & scenario data
    scenarios.csv                            # 100 parameter sets
    ground_truth.csv                         # Collapse probabilities
    scenario_events.json                     # Actions & events per scenario
    scenario_001/ ... scenario_050/          # Per-scenario interaction files

experiment_results/                        # Prediction experiment results
  multiscenario_forecasting/               # Collapse probability results
  action_prediction/                       # Action prediction results
  persona_cot_experiment/                  # Persona+CoT experiment results
  framework_experiment/                    # Framework diversity results
    scenario_results_YYYYMMDD_HHMMSS.csv     # Per-scenario ensemble metrics
    agent_details_YYYYMMDD_HHMMSS.csv        # Per-agent predictions + framework/model metadata
    summary_YYYYMMDD_HHMMSS.csv              # Condition-level summary stats
```

**Agent details CSV columns (framework pool mode):**
`scenario_id, condition, agent_id, framework_name, method, lens, focus, bias, model, information_fraction, probability, confidence, rationale, fallback_type`

---

## Quick Start

```bash
cd D:/Northeastern/LLM_Forecasting

# 1. Collapse probability (already complete)
python -u forecasting/run_multiscenario_experiment.py --test

# 2. Action prediction — pool + multi-model + balanced selection
python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --test

# 3. Persona+CoT bridging
python -u forecasting/run_persona_cot_experiment.py --n-scenarios 50 --n-agents 10 --conditions persona_baseline persona_shard

# 4. Framework diversity — composable pool + multi-model
python -u forecasting/run_framework_experiment.py --pool --multi-model --test

# 5. Verify framework pool
python -c "from forecasting.framework_pool import generate_pool; print(len(generate_pool()))"  # -> 1000
```

All scripts support `--test` for quick validation, `--start-scenario` for resuming, and incremental CSV saving.

---

## Key Findings So Far

1. **Information sharding improves collapse probability forecasting** by 15-18% (MSE), consistent across two independent replications over 50 scenarios.

2. **Sharding effect on action prediction is near-neutral** — early results show ~2-3% difference, not clearly favoring either direction. Hypothesis: binary action calls benefit less from diversity than continuous probability estimates.

3. **Personas alone hurt accuracy** (-35% to -42% in prior experiments). The CoT bridging approach is designed to fix this by making persona attributes task-relevant rather than decorative.

4. **Ensemble aggregation methodology matters** — average predictions first, then score (not individual scores then average). Up to 3x difference in performance estimates.

5. **Analytical frameworks produce 2-3x more prediction diversity than personas** (Feb 13). Per-scenario std ~0.28 for frameworks vs ~0.07 for personas.

6. **Model choice dominates framework design** (Feb 13). Llama 3.3 70B (MSE 0.018) dramatically outperformed DeepSeek V3.2 (MSE 0.117) on the same framework pool — because Llama actually follows framework instructions while DeepSeek ignores them.

7. **Composable framework lenses act as fixed multipliers, not evidence-responsive filters** (Feb 13). Threat-focused always outputs ~0.75, resilience-focused always ~0.15, regardless of scenario severity. Diversity helps ensemble accuracy only because the fixed bands happen to bracket the ground truth. Planned fix: evidence-first, lens-second prompt structure.

8. **Action prediction with framework pool is worse than base-rate prediction** (preliminary, Feb 13). Models assign ~0.54 probability to actions not taken. The "always predict 0.15" strategy (Brier 0.13) beats pool_baseline (Brier 0.28). Balanced action selection (2 taken + 3 not-taken) introduced to test discrimination vs base-rate calibration.

9. **Avoid reasoning/thinking models in multi-model pool.** Qwen3-235B (thinking model) had 100% failure rate due to `<think>` traces exceeding the 500 max_tokens budget. All pool models must be instruct-only.

---

## Archive

| Directory | Contents |
|-----------|----------|
| `archive/action_set_prediction_old/` | Old full action set prediction (hard classification) |
| `archive/superseded_feb12/` | Superseded experiment runners, persona systems, and documentation |
