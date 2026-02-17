# Experiment Notes

**Last Updated:** February 18, 2026

## Market Experiment (Feb 15-16) — PRIMARY FOCUS

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Market engine | Complete | Double auction clearing, order validation, state management |
| 2. LLM agent integration | Complete | OpenRouter API, role prompts, 7 agents (2 prod, 3 cons, 2 spec) |
| 3. Multi-scenario generation | Complete | Seeded shock sequences, configurable parameters |
| 4. PID analysis | Complete | Williams-Beer Imin, permutation testing, 3 encodings |
| 5. Forecasting experiment | **Complete** | 2x2 factorial (demographic x ToM), Llama + Qwen |
| 6. Statistical analysis | **Complete** | LMM with period-within-scenario clustering |

### Completed Runs

**Baseline (rule-based, 10 scenarios x 30 periods):**
- Output: `outputs/market_sim_baseline_10s30p/`
- Mean return vol: 0.0946, mean price range: 38.3%
- PID: **EC = 0.041 bits, p = 0.000 (SIGNIFICANT)**
- 9 agent pairs significant at p < 0.05 (row-shuffle, 500 permutations)
- Strongest pairs: producer_A x speculator_A (syn=0.061, p=0.006), consumer_C x speculator_B (syn=0.061, p=0.018)

**LLM no-persona (Llama 8B, 10 scenarios x 30 periods):**
- Output: `outputs/market_sim_llama_10s30p/`
- 2,100 LLM calls, 100% success rate, 1.7M tokens, ~86 min
- Mean return vol: 0.0313, mean price range: 22.2%
- PID: **EC = 0.005 bits, p = 0.744 (NOT significant)**
- No pairs significant. Closest: speculator_A x speculator_B (syn=0.056, p=0.096)
- Problem: price stickiness (50% flat periods), consumers have only 2-level actions

**LLM with personas (Llama 8B, 10 scenarios x 30 periods):**
- Output: `outputs/market_sim_llama_10s30p_persona/`
- 2,100 LLM calls, 100% success rate, 2.08M tokens, ~112 min
- Mean return vol: 0.0656, mean price range: 56.5%, mean price std: $23.6
- PID: **EC = 0.032 bits, p = 0.002 (SIGNIFICANT)**
- 1 pair individually significant: consumer_B x producer_B (syn=0.038, p=0.020)
- Target distribution near-optimal: 41% DOWN / 24% FLAT / 35% UP, H(Y)=1.55 bits (97.9% efficiency)
- Highest synergy pairs: speculator_A x speculator_B (0.074, 76%), consumer_B x speculator_B (0.074, 79%)

**Three-condition PID comparison:**

| Condition | EC (bits) | p-value | H(Y) | Significant pairs |
|-----------|----------|---------|------|-------------------|
| Baseline (rule-based) | 0.041 | 0.000 | 1.39 bits | 9/21 |
| LLM no-persona | 0.005 | 0.744 | 0.81 bits | 0/21 |
| **LLM persona** | **0.032** | **0.002** | **1.55 bits** | **1/21** |

Personas recovered 79% of baseline EC (0.032 vs 0.041) and achieved statistical significance.

### Agent Trading Personas (Added Feb 16)

| Agent | Persona | Strategy |
|-------|---------|----------|
| producer_A | Volume Mover | Aggressive low asks, prioritizes fills over margin |
| producer_B | Margin Optimizer | Firm high asks, holds back when margins are thin |
| consumer_A | Security Stockpiler | Aggressive high bids, maintains 3-4 period buffer |
| consumer_B | Bargain Hunter | Conservative low bids, waits for dips, small quantities |
| consumer_C | Shock Anticipator | Swings aggressive/passive based on shock announcements |
| speculator_A | Momentum Rider | Buys uptrends, sells downtrends |
| speculator_B | Value Contrarian | Mean-reversion, fades extreme moves |

Key behavioral impact (scenario 001, persona vs no-persona):
- Consumer aggressiveness spread: -8% to +11% (was +-1%)
- Producer aggressiveness spread: -5% to +10% (was +-2%)
- Price std: $24.1 vs $10.3 (2.3x), flat periods: 6 vs 15

### Key Finding: Behavioral Entropy Trap

LLM agents without distinct personas converge to "bid near last price" behavior, producing:
- Low action entropy (consumers: 2 levels only)
- High price stickiness (50% flat periods)
- Skewed target distribution (75% DOWN, 25% UP)
- No detectable PID synergy

Rule-based agents with hard-coded different strategies show significant synergy (EC p=0.000) because their deterministic rules create genuine behavioral diversity. Personas are essential for LLM agents to match this.

### Forecasting Results (Phase 5, Feb 16-17)

**Design:** Demographic personas only, +/- ToM, Llama 8B + Qwen 235B. 4,800 total forecasts.

**LMM:** `sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`

| Effect | Estimate | p |
|--------|----------|---|
| tom | **-17.27** | **0.027 \*** |
| model (qwen) | +44.51 | < 1e-8 *** |
| tom:model | ns | 0.480 |

- Period clustering absorbs 11.3% of variance (LRT p < 2.2e-16)
- ToM helps: reduces MSE by 17 units, wins 7-8/10 scenarios
- Qwen substantially worse than Llama (same-model confound)
- Full details: `docs/RESULTS_FORECASTING_AND_PID.md`

### TODO
- [x] ~~Complete persona run~~ Done (Feb 16)
- [x] ~~Run PID on persona results~~ EC = 0.032, p = 0.002 (SIGNIFICANT)
- [x] ~~Phase 5: External LLM forecasters predicting market prices~~ Done (Feb 16-17)
- [x] ~~Statistical analysis with period clustering~~ Done (Feb 17)
- [ ] Generate visualization plots (price series, PID heatmaps)
- [ ] Consider scaling up: 20-50 scenarios for more statistical power

### Files
- `market/engine.py` — Market clearing, order book
- `market/agents_config.py` — Agent templates (7 agents)
- `market/llm_agent.py` — OpenRouter LLM wrapper
- `market/prompts.py` — Role prompts + trading personas
- `market/shocks.py` — Shock generation (6 types)
- `market/pid_extraction.py` — Order matrix extraction (3 encodings)
- `market/pid_analysis.py` — Williams-Beer PID (no external deps)
- `market/run_market_sim.py` — Simulation runner
- `market/run_market_pid.py` — PID analysis runner
- `market/test_engine.py` — Rule-based baseline
- `market/plot_prices.py` — Visualization

---

## Conflict Experiment (Feb 16-18) — COMPLETE

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Conflict engine | Complete | Escalation index tracking, state management, 7 agents |
| 2. LLM agent integration | Complete | OpenRouter API, 7 personas (4 Novaris + 3 Tethys) |
| 3. Multi-scenario generation | Complete | 10 scenarios x 30 periods |
| 4. PID analysis | **Complete** | Williams-Beer Imin, permutation testing, faction analysis |
| 5. Forecasting experiment | Complete | Demographic personas +/- ToM, Llama 8B |
| 6. Statistical analysis | Complete | LMM with period-within-scenario clustering |

### Forecasting Results

**Design:** Demographic personas only, +/- ToM, Llama 8B only. 2,400 total forecasts.

**LMM:** `sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`

| Effect | Estimate | p |
|--------|----------|---|
| tom | **+0.286** | **0.010 \*** |

- **ToM HURTS conflict forecasting** -- increases MSE by 0.286 (p = 0.010)
- ToM only wins 2/10 scenarios; every forecaster gets worse
- Period clustering absorbs 3.6% of variance (LRT p = 9.9e-10)
- Abs EI error confirms: tom = +0.154, p < 1e-10

**Per-forecaster impact (all worse with ToM):**

| Forecaster | MSE (no-ToM) | MSE (ToM) | Change |
|---|---|---|---|
| cautious_diplomat | 0.580 | 0.762 | +31% |
| contrarian_pundit | 1.049 | 1.692 | +61% |
| ir_professor | 0.769 | 1.141 | +48% |
| retired_general | 0.798 | 1.030 | +29% |
| young_analyst | 1.034 | 1.037 | +0.3% |

**Interpretation:** In conflict, agent personas describe dispositions (hawk/dove) but the mapping from disposition to action to escalation is stochastic and context-dependent. ToM causes forecasters to overfit to expected personality-driven behavior.

### PID Analysis Results (Phase 4, Feb 17-18)

**Design:** Williams-Beer Imin PID on 7 agents, 290 obs (10 scenarios x 29 periods). Action encoding: 5-level escalatory intensity scale (direction_aggr). Target: next-period EI change (tercile-binned). 500 permutations. Compared against rule-based baseline and no-persona LLM condition.

**Three-Condition Comparison:**

| Metric | Baseline (rule) | LLM No-Persona | LLM Persona |
|--------|----------------|----------------|-------------|
| Emergence Capacity | 0.012 | **0.115** (p=0.010) | 0.106 (p=0.000) |
| Higher-Order (G3) | 0.000 | **0.314** | 0.230 |
| Positive G3 % | 30% | 100% | 100% |
| Mean JSD | 0.601 | **0.016** | 0.196 |
| Action entropy | 0.92 bits | **2.09 bits** | 1.90 bits |
| Consistency | 0.014 | 0.012 | 0.011 |

**Faction analysis:**

| Group | Persona EC | No-Persona EC |
|-------|-----------|---------------|
| Novaris (4 agents) | 0.109 | 0.103 |
| Tethys (3 agents) | 0.087 | 0.093 |
| Cross-faction | 0.103 | **0.121** |

Cross-faction EC increases most without personas (+0.018) -- without persona-specific dispositions, agents are more collectively reactive across the faction boundary.

**Key findings:**
1. LLM agents show 8-9x more emergent coordination than rule-based baseline
2. No-persona agents show *slightly more* synergy (0.115) than persona agents (0.106) -- opposite of market
3. No-persona agents are nearly indistinguishable (JSD=0.016) -- all behave almost identically
4. Personas add differentiation (JSD 0.016 → 0.196) but slightly constrain synergy
5. 100% of triplets show positive G3 in both LLM conditions
6. Cross-faction EC (0.103) nearly equals within-faction -- escalation is a two-sided process
7. **Domain matters:** In market, personas are necessary for synergy; in conflict, the domain itself elicits coordination
8. Conflict EC (0.106-0.115) is 3.3x higher than market EC (0.032), yet ToM *hurts* conflict forecasting -- more coordination complexity makes persona knowledge less useful

### Files
- `conflict/engine.py` -- Conflict mechanics, state tracking
- `conflict/agents_config.py` -- 7 agent personas with backstories
- `conflict/run_conflict_sim.py` -- Simulation runner
- `conflict/run_conflict_forecast.py` -- Forecasting experiment
- `conflict/analyze_forecasts.R` -- LMM analysis
- `conflict/pid_extraction.py` -- Action matrix extraction (3 encodings)
- `conflict/run_conflict_pid.py` -- PID analysis runner
- `market/pid_analysis.py` -- Shared PID computation (reused from market)
- PID results (persona): `outputs/conflict_sim_llama/pid_analysis/`
- PID results (no-persona): `outputs/conflict_sim_llama_no_persona/pid_analysis/`
- No-persona sim: `outputs/conflict_sim_llama_no_persona/`
- Full details: `docs/RESULTS_FORECASTING_AND_PID.md`

---

## Cross-Domain Summary (Feb 17-18)

**Central finding: ToM has opposite effects by domain.**

| Domain | ToM Effect | Direction | p | Why |
|--------|-----------|-----------|---|-----|
| Market | -17.27 MSE | **Helps** | 0.027 | Agent strategies have direct, mechanistic link to prices |
| Conflict | +0.286 MSE | **Hurts** | 0.010 | Agent personas cause overfitting to expected behavior |

Both analyses use period-within-scenario clustering `(1|scenario_id:period)` to properly account for shared ground truth within scenario-periods. This correction was strongly justified by LRT in both domains.

**PID supports the asymmetry:** Conflict shows 3.3x more emergent coordination (EC = 0.106 vs 0.032) but ToM hurts. More coordination complexity = more ways to be wrong about agent intentions. Market's simpler coordination structure (mechanistic price formation) is easier for forecasters to leverage from persona descriptions.

**LLM vs baseline: mirror-image across domains.** In market, the rule-based baseline has the *highest* EC (0.041) and LLM personas only recover 79% of it. In conflict, LLM agents exceed the baseline by 8-9x (0.106-0.115 vs 0.012). Market coordination is *mechanistic* (structural role constraints create complementarity by construction). Conflict coordination is *reasoning-driven* (a single-scalar formula can't capture strategic complexity, but LLMs naturally produce rich, context-dependent actions).

**Persona role differs by domain:** In market, removing personas destroys synergy (EC 0.032 → 0.005). In conflict, removing personas *slightly increases* synergy (0.106 → 0.115) with near-zero differentiation (JSD = 0.016). The conflict domain is intrinsically strategic enough to elicit coordination from generic LLM advisors; market requires persona-driven behavioral diversity.

**The PID explains the ToM finding:** In market, knowing personas gives you the *source* of coordination (persona-driven strategies → prices). In conflict, personas are not the source of coordination (the domain drives it regardless), so static persona descriptions add noise rather than signal.

---

## Forecasting Experiments (Feb 12-14) — PAUSED

### TODO (Paused — Resuming After Market Experiment)

### Action Prediction
- [ ] Re-run scenarios 001-003 with `--n-agents 10` (original test run used n_agents=5)
  ```
  python -u forecasting/run_action_prediction_experiment.py --n-scenarios 3 --n-agents 10 --conditions baseline shard_everything
  ```
- [ ] Re-run scenarios 039-050 (credits ran out mid-039, 040-050 are all fallbacks)
  ```
  python -u forecasting/run_action_prediction_experiment.py --n-scenarios 50 --n-agents 10 --conditions baseline shard_everything --start-scenario 39
  ```
- **Clean data so far:** scenarios 004-038 (35 scenarios) across 3 CSV files:
  - `action_prediction_results_20260212_134919.csv` — scenarios 004-013 (partial 014 baseline only)
  - `action_prediction_results_20260212_153,csv` — scenarios 014-017
  - `action_prediction_results_20260212_180639.csv` — scenarios 018-038 clean, 039 partial, 040-050 bad
- Old test file `action_prediction_results_20260212_104548.csv` has n_agents=5, not compatible
- [ ] Re-run pool + multi-model + balanced test with corrected model pool (Qwen3-235B replaced with qwen-2.5-72b-instruct):
  ```
  python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --test
  ```
- [ ] Full pool + multi-model + balanced run (50 scenarios):
  ```
  python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --n-scenarios 50 --n-agents 10
  ```

### Persona + CoT Bridging
- [ ] Run persona conditions after action prediction finishes:
  ```
  python -u forecasting/run_persona_cot_experiment.py --n-scenarios 50 --n-agents 10 --conditions persona_baseline persona_shard
  ```
- Generic conditions (generic_baseline, generic_shard) already exist in `experiment_results/multiscenario_forecasting/experiment_results_20260212_093753.csv`

### Analytical Framework Diversity
- [x] Fixed 10-framework full run: 50 scenarios × 10 agents × 2 conditions (1,000 LLM calls)
  ```
  python -u forecasting/run_framework_experiment.py --n-scenarios 50 --n-agents 10
  ```
- **Results:** `experiment_results/framework_experiment/`
- **Early results (7 scenarios):** Baseline std ~0.21 (3x persona experiment's ~0.07). Zero fallbacks.
- [x] Composable pool implementation (4 axes, 1000 combinations) — `framework_pool.py`
- [x] Multi-model pool implementation (6 models, per-agent assignment)
- [x] 3-scenario pool test with DeepSeek, Llama, Gemini, multi-model
- [ ] Fix evidence-responsiveness problem (lenses as fixed multipliers — see below)
- [ ] Full composable pool run (50 scenarios):
  ```
  python -u forecasting/run_framework_experiment.py --pool --multi-model --n-scenarios 50 --n-agents 10
  ```
- [ ] Compare framework vs persona diversity once both full runs complete
- [ ] Analyze per-framework prediction distributions (worst_case vs best_case spread)

---

## Composable Framework Pool (Feb 13)

### Motivation

The fixed 10-framework experiment confirmed that analytical frameworks produce ~2.5x more prediction diversity than personas (std 0.184 vs 0.07). However, 6 of 10 frameworks converge to 0.12-0.25. Only worst_case (0.55), devils_advocate (0.58), and occasionally trend (0.25) break out. The "rational-but-different-method" frameworks (base_rate, historical_analogy, game_theoretic, structural, key_indicator) all reach similar conclusions because the method doesn't constrain the output direction.

### Design: 4 Composable Axes

**File:** `forecasting/framework_pool.py`

| Axis | Count | Purpose | Options |
|------|-------|---------|---------|
| **Method** | 5 | Reasoning structure (CoT steps) | base_rate, scenario_tree, historical_analogy, key_indicator, structural |
| **Lens** | 5 | Interpretive bias (how ambiguity is read) | threat_focused, resilience_focused, contrarian, loss_averse, detached |
| **Focus** | 5 | Evidence attention (which signals dominate) | military, economic, political, events, holistic |
| **Bias** | 8 | Cognitive distortion | recency, anchoring, normalcy, availability, overconfidence, sunk_cost, confirmation, none |

5 × 5 × 5 × 8 = **1,000 unique combinations**. Each scenario samples 10 from the pool (seeded by scenario_id for reproducibility via SHA-256 hash).

### Model Comparison (3-scenario pool test)

| Model | Fallback Rate | Prediction Range | Per-scenario Std | Baseline MSE |
|-------|--------------|-----------------|-----------------|-------------|
| DeepSeek V3.2 | 3% | 0.08–0.85 | 0.135 | 0.117 |
| Llama 3.3 70B | **0%** | 0.12–0.85 | **0.277** | **0.018** |
| Gemini 2.5 Flash | 0% | 0.04–0.94 | 0.271 | 0.028 |
| Multi-model (3) | 0% | 0.12–0.85 | 0.262 | 0.029 |

**Key takeaway:** Model instruction-following dominates framework design. DeepSeek ignores lens instructions (std 0.135), Llama/Gemini follow them (std 0.27+). Multi-model ensembles average model quality rather than improving it — Llama-only outperformed.

### Failed Models

- **moonshotai/kimi-k2.5**: 70% API error rate (42/60 calls). The 18 successful predictions showed good diversity (0.07-0.76), but too unreliable for production use.
- **qwen/qwen3-235b-a22b**: 100% failure rate (30/30 calls). Root cause: thinking/reasoning model generates `<think>...</think>` traces before JSON output, exceeding the 500 max_tokens budget. **Lesson: avoid reasoning/thinking models in multi-model pool. All pool models must be instruct-only.**

Qwen3-235B was replaced with `qwen/qwen-2.5-72b-instruct` in the model pool.

### Evidence-Responsiveness Problem

**Critical finding:** Lenses act as fixed multipliers, not evidence-responsive filters.

Analysis across 3 scenarios (ground truths: 0.327, 0.458, 0.677):

| Lens | scenario_001 (GT 0.327) | scenario_002 (GT 0.458) | scenario_003 (GT 0.677) | Spread |
|------|------------------------|------------------------|------------------------|--------|
| threat_focused | 0.75 | 0.82 | 0.82 | 0.07 |
| resilience_focused | 0.15 | 0.12 | 0.18 | 0.06 |
| contrarian | 0.82 | 0.82 | — | 0.00 |
| loss_averse | 0.72 | 0.75 | 0.78 | 0.06 |
| detached | 0.45 | 0.55 | 0.65 | 0.20 |

The "detached" (no bias) lens shows the most scenario-responsiveness (spread 0.20). Directional lenses produce near-identical outputs regardless of scenario severity. Threat-focused outputs ~0.75 whether ground truth is 0.327 or 0.677.

**Root cause:** Calibration notes like "Your estimates should skew HIGHER" tell the model what number to output rather than how to reason about evidence. The model shortcuts to the instructed direction.

**Proposed fix (not yet implemented):** Evidence-first, lens-second prompt structure:
1. Force evidence analysis before lens application (separate "what does the evidence say?" step before "how does your lens interpret this?")
2. Remove directional calibration notes ("skew HIGH/LOW") from system prompt
3. Require data anchoring: "Quote the specific data points that support your estimate"

Diversity still helps ensemble accuracy incidentally — the fixed bands bracket the ground truth, so the ensemble mean lands closer — but this is fragile and won't generalize to scenarios outside the bracketed range.

---

## Action Prediction with Framework Pool (Feb 13)

### Setup

Added `--pool`, `--multi-model`, and `--balanced` flags to `run_action_prediction_experiment.py`. Two new conditions: `pool_baseline` (full info) and `pool_shard` (sharded info). Adapted `framework_pool.py` with `compose_action_framework()` for action prediction prompts.

### Preliminary Results (3-scenario test, pool + multi-model)

| Condition | Mean Brier | Fallbacks |
|-----------|-----------|-----------|
| pool_baseline (scenario_001) | 0.286 | 1/50 |
| pool_shard (scenario_001) | 0.370 | 0/50 |
| pool_baseline (scenario_002) | 0.352 | 0/50 |
| pool_shard (scenario_002) | 0.294 | 10/50 |
| pool_baseline (scenario_003) | 0.214 | 20/50 |

**Worse than base-rate prediction:** Models assign ~0.54 probability to actions not taken. With ~84% negative class imbalance (random action sampling from 68-action pool), the naive "always predict 0.15" strategy (Brier 0.134) beats pool_baseline (Brier 0.284).

High fallback rates in scenario_003 (20/50) traced to Qwen3-235B's 100% failure rate.

### Balanced Action Selection

Implemented `select_actions_balanced()` with `--balanced` flag to guarantee 2 taken + 3 not-taken actions per scenario. This tests discrimination ability (can the model tell taken from not-taken?) rather than base-rate calibration (can it predict the overall action frequency?).

Without balanced selection, the 84% negative class imbalance means a model that assigns uniform ~0.5 probability to everything will have poor Brier scores purely from miscalibration, even if it has some discrimination ability.

---

## Completed Runs

### Collapse Probability (Feb 12)
- **Active results:** `experiment_results/multiscenario_forecasting/experiment_results_20260212_093753.csv`
- 50 scenarios, N=10 agents, baseline + shard_everything, with external events
- Baseline MSE: 0.1764, Shard MSE: 0.1489 (-15.6%)

### Archived Runs
- `experiment_results/multiscenario_forecasting/archived/experiment_results_20260211_191905.csv` — test run (3 scenarios, n_agents=5)
- `experiment_results/multiscenario_forecasting/archived/experiment_results_20260212_085406.csv` — full run but **without external events** in prompts (higher error: baseline 0.2011 vs 0.1764)

---

## Code Changes (Feb 12)

### Incremental CSV Saving
All three experiment scripts now save results after each scenario-condition completes (append mode). If killed mid-run, all completed scenarios are preserved. Final full overwrite on normal completion.
- `run_multiscenario_experiment.py`
- `run_action_prediction_experiment.py`
- `run_persona_cot_experiment.py`

### Persona System Updates
- Added `risk_tolerance: int` (0-100) to `SimplifiedProfile` in `persona_simplified.py`
- Updated `to_natural_language()` with risk tolerance section (LOW/MODERATE-LOW/MODERATE-HIGH/HIGH labels)
- Updated `generate_simplified_personas()`: risk_tolerance ~ normal(mean, 25) clamped [0,100], mean biased by orientation (hawkish=60, dovish=40, pragmatic=50)
- Regenerated `persona_profiles_simplified.json` (seed=42, n=500)

### Analytical Framework Experiment (Feb 13, early)
- New standalone script `forecasting/run_framework_experiment.py`
- 10 analytical frameworks replace persona system: base_rate, key_indicator, scenario_tree, historical_analogy, worst_case, best_case, trend, structural, game_theoretic, devils_advocate
- Each framework has a unique system prompt and CoT instructions that force structurally different reasoning paths
- 2 conditions: `framework_baseline` (full info) and `framework_shard` (shard_everything)
- No modifications to existing files — reuses `forecaster_base.py`, `collapse_prompts_with_scenario.py`, `sharding_strategies.py`, `information_sharding.py`

### Composable Framework Pool (Feb 13)
- **New file:** `forecasting/framework_pool.py` — 4 composable axes (Method × Lens × Focus × Bias = 1,000 combinations)
  - `compose_framework()` / `compose_action_framework()` — assemble system prompt + CoT from 4 axes
  - `generate_pool()` / `generate_action_pool()` — all 1,000 combinations
  - `sample_frameworks()` / `sample_action_frameworks()` — deterministic hash-based sampling
- **Modified:** `forecasting/run_framework_experiment.py`
  - Added `--pool` flag (composable pool vs fixed 10 frameworks)
  - Added `--multi-model` flag (per-agent model assignment from 6-model pool)
  - Added MODEL_POOL: deepseek/deepseek-v3.2, meta-llama/llama-3.3-70b-instruct, google/gemini-2.5-flash, mistralai/mistral-small-3.2-24b-instruct, qwen/qwen-2.5-72b-instruct, google/gemma-3-27b-it
  - Agent details CSV gains columns: method, lens, focus, bias, model
  - Per-agent model assignment via SHA-256 hash of `scenario_id + condition + agent_id`
- **Modified:** `forecasting/run_action_prediction_experiment.py`
  - Added `--pool`, `--multi-model`, `--balanced` flags
  - Added `pool_baseline` and `pool_shard` conditions
  - Added `select_actions_balanced()` — guarantees 2 taken + 3 not-taken per scenario
  - Framework/model pool integration with same hashing scheme
  - Agent details now recorded for pool/multi-model runs (not just persona conditions)

### Backstory Reframing & Parameter Sensitivity (Feb 14)

**Motivation:** Systematic downward bias in collapse probability forecasting (ensemble mean ~0.35 vs truth ~0.58). Root cause: backstory frames Tethys as resilient, anchoring all agents low.

**Python forecasting changes (`forecasting/run_multiscenario_experiment.py`):**
- Added 5 backstory variants: INITIAL_SCENARIO_AGGRESSOR, _VULNERABILITY, _ESCALATION, _DOMESTIC, _INERTIA
- Added `BACKSTORY_VARIANTS` list (6 total including original)
- Added "reframe" condition: agents cycle through variants (agent `i` gets `BACKSTORY_VARIANTS[i % 6]`)
- Added agent-level prediction logging (agent_id, model, backstory_variant/domain per prediction)
- Added `condition_map` entry: `"reframe": ("none", None, "reframe")`

**Results (50 scenarios, 10 agents, 4 models):**
| Condition | MSE | vs Baseline |
|-----------|-----|-------------|
| Baseline | 0.0550-0.0572 | — |
| Reframe | 0.0214-0.0229 | **-58% to -61%** |
| Domain shard | 0.1367 | +143% (worse) |

**Diagnostic findings:**
- Inertia variant is completely degenerate (std=0.000, always 0.42)
- Aggressor nearly degenerate (std=0.041, always ~0.56)
- Vulnerability is best — well-calibrated AND responsive (mean 0.478, std 0.110)
- Improvement is largely uniform upward shift, not scenario-adaptive debiasing
- Median slightly better than mean (MSE 0.0202 vs 0.0234)

**R simulation changes:**
- `src/agent_decision.R`: `format_situation_for_agent()` now shows exact numeric values alongside worldview-filtered descriptions; `international_support` added (was completely missing)
- `src/multi_action_system.R`: `build_proposal_prompt()` and `build_approval_prompt()` now include all 5 scenario parameters with exact values

**Sensitivity test (3 contrasting 1-period scenarios):**
- Novaris action overlap (low vs high): 33% (was near-100%)
- Tethys action overlap (low vs high): 25% (was near-100%)
- Collapse probability range: 0.385–0.635

**TODO:**
- [ ] Regenerate 100-scenario dataset with v3.9.0 parameter-sensitive agents
- [ ] Fix degenerate backstory variants (Inertia, Aggressor)
- [ ] Re-run reframe experiment on new dataset
- [ ] Test whether parameter-sensitive ground truth actions improve forecasting

### Archived Scripts (to `forecasting/archive/superseded_feb12/`)
- `run_collapse_sharding_comparison.py` — superseded by `run_multiscenario_experiment.py`
- `run_action_probability_experiment.py` — superseded by `run_action_prediction_experiment.py`
- `run_information_sharding_experiment.py` — superseded by `run_multiscenario_experiment.py`
- `run_persona_rewrite_experiment.py` — superseded by `run_persona_cot_experiment.py`
- `persona_rewrite.py` — rewrite engine replaced by inline bridging CoT
- `persona_generator.py` — 24-attribute CognitiveProfile replaced by 7-attribute SimplifiedProfile
- `action_probability_prompts.py` — prompts now inline in experiment script
- `persona_profiles.json` — complex persona pool replaced by simplified version
