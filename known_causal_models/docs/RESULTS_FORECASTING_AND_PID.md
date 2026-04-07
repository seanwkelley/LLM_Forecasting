# Statistical Analysis: Forecasting Experiments

**Last Updated:** February 18, 2026

This document details the statistical methods and results for the forecasting experiments across both the **market** and **conflict** simulation domains. The core question is whether Theory of Mind (ToM) -- providing forecasters with descriptions of the simulation agents' personas and strategies -- improves or impairs forecasting accuracy.

---

## 1. Study Design

### 1.1 Overview

External LLM forecasters observe simulation history (prices or escalation indices) and predict the next-period outcome. The key manipulation is whether forecasters receive Theory of Mind context describing the simulation agents.

| Aspect | Market | Conflict |
|--------|--------|----------|
| Simulation | 7 LLM trading agents (double auction) | 7 LLM geopolitical agents (escalation dynamics) |
| Target variable | Next-period clearing price | Next-period escalation index (EI) |
| Scenarios | 10 | 10 |
| Periods per scenario | 24 (periods 6-29) | 24 (periods 6-29) |
| Forecasters per condition | 5 (demographic personas) | 5 (demographic personas) |
| Models tested | Llama 3.1 8B, Qwen3 235B | Llama 3.1 8B |
| ToM manipulation | Agent persona descriptions appended to prompt | Agent persona descriptions appended to prompt |

### 1.2 Conditions

**Market** (4 conditions):
- Llama demographic, no ToM (1,200 forecasts)
- Llama demographic, with ToM (1,200 forecasts)
- Qwen demographic, no ToM (1,200 forecasts)
- Qwen demographic, with ToM (1,200 forecasts)

**Conflict** (2 conditions):
- Llama demographic, no ToM (1,200 forecasts)
- Llama demographic, with ToM (1,200 forecasts)

### 1.3 Dependent Variables

We focus exclusively on **prediction error** terms rather than Brier scores:

- **Squared price error** (market): `(predicted_price - actual_price)^2`
- **Squared EI error** (conflict): `(predicted_ei - actual_ei)^2`
- **Absolute error** (supplementary): `|predicted - actual|`
- **Squared percentage error** (market supplementary): `((predicted - actual) / actual * 100)^2`

Rationale: The continuous prediction errors contain more information than the discretized directional classification (UP/DOWN/FLAT) underlying Brier scores. Price/EI point predictions directly measure forecasting quality without information loss from categorization.

### 1.4 Theory of Mind Content

**Market ToM** describes the 7 trading agent personas:
- 2 producers (Volume Mover, Margin Optimizer) with pricing strategies
- 3 consumers (Security Stockpiler, Bargain Hunter, Shock Anticipator) with buying strategies
- 2 speculators (Momentum Rider, Value Contrarian) with directional strategies
- Key interaction dynamics (e.g., "when both speculators agree, expect a strong move")

**Conflict ToM** describes the 7 geopolitical agent personas:
- 4 Novaris agents (Krasnov, Volkov, Petrova, Morozov) with hawk/dove scores, backstory summaries, personality traits
- 3 Tethys agents (Marchetti, Bondar, Kovalenko) with same detail
- Key inter-agent dynamics (alliances, rivalries, swing votes)

---

## 2. Statistical Methods

### 2.1 Linear Mixed-Effects Models (LMM)

We use LMMs (R `lme4` + `lmerTest`) to account for the nested, repeated-measures structure of the data. All models use REML estimation with Satterthwaite degrees of freedom.

### 2.2 Random Effects Structure

#### The Period-Clustering Problem

Each of the 240 unique scenario-periods (10 scenarios x 24 periods) has a **single ground truth outcome**. All forecasters within the same scenario-period predict the same actual value. Predictions within a scenario-period share:
- The same ground truth difficulty
- The same market regime / escalation state
- The same recent history context

A model with only `(1|scenario_id)` captures that some scenarios are harder *on average* but not that some *periods within scenarios* are harder. With ~98% of variance in the residual (as in initial models), much of it is likely period-level variance that should be absorbed.

#### Solution: Nested Random Intercepts

We add a period-within-scenario random intercept:

```
(1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

This is equivalent to `(1|scenario_id/period) + (1|forecaster_id)`. The `scenario_id:period` term creates 240 unique random intercepts (one per scenario-period), absorbing the shared difficulty that all forecasters face at that time point.

**Effective sample size:** With this structure, the effective N for the ToM fixed effect is closer to ~240 period-clusters than the raw ~4,800 individual forecasts. Standard errors become more honest (less anticonservative).

### 2.3 Model Specifications

**Market (primary):**
```
sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

- `tom` (0/1): Theory of Mind manipulation
- `model` (llama/qwen): Forecaster LLM model (fixed effect)
- `scenario_id`: 10 scenarios (random intercept)
- `scenario_id:period`: 240 scenario-period clusters (random intercept)
- `forecaster_id`: 5 forecaster personas (random intercept)

**Conflict (primary):**
```
sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

- `tom` (0/1): Theory of Mind manipulation
- No model fixed effect (single model only)
- Same random effects structure

### 2.4 Interaction Testing

For market (which has a model factor), we first fit the interaction model:

```
sq_error ~ tom * model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

If the `tom:model` interaction is non-significant, we drop it and report the additive main-effects model.

### 2.5 Model Validation

We validate the period-clustering decision via:
1. **Likelihood ratio test (LRT):** Compare models with and without `(1|scenario_id:period)` (both fit with ML, not REML)
2. **Variance decomposition:** Compare residual percentage before and after adding the period term
3. **AIC/BIC comparison**

---

## 3. Results: Market Forecasting

### 3.1 Descriptive Statistics

| Model | ToM | N | Accuracy | MAE ($) | MSE | RMSE ($) |
|-------|-----|---|----------|---------|-----|----------|
| Llama | No | 1,200 | 49.2% | 8.39 | 110.03 | 10.49 |
| Llama | Yes | 1,200 | 50.3% | 7.97 | 98.26 | 9.91 |
| Qwen | No | 1,200 | 38.4% | 9.75 | 160.05 | 12.65 |
| Qwen | Yes | 1,200 | 40.8% | 9.31 | 137.26 | 11.72 |

Total N = 4,800 (10 scenarios x 24 periods x 5 forecasters x 2 models x 2 ToM conditions).

### 3.2 Interaction Test

```
sq_error ~ tom * model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

| Fixed Effect | Estimate | SE | t | p |
|---|---|---|---|---|
| Intercept (Llama, no-ToM) | 110.03 | 18.59 | 5.92 | 0.0002 |
| tom | -11.76 | 11.04 | -1.07 | 0.287 |
| model (qwen) | +50.02 | 11.04 | 4.53 | 6.0e-06 |
| **tom:model** | **-11.02** | **15.62** | **-0.71** | **0.480** |

The `tom:model` interaction is non-significant (p = 0.480), meaning **ToM has a similar effect on both models**. We drop the interaction.

### 3.3 Main Effects Model (Primary)

```
sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

| Fixed Effect | Estimate | SE | df | t | p |
|---|---|---|---|---|---|
| Intercept | 112.78 | 18.18 | 8.8 | 6.20 | 0.0002 *** |
| **tom** | **-17.27** | **7.81** | **4554** | **-2.21** | **0.027 \*** |
| **model (qwen)** | **+44.51** | **7.81** | **4554** | **5.70** | **1.3e-08 \*\*\*** |

**Interpretation:**
- **ToM reduces squared price error by 17.27 units** (p = 0.027). Knowing agent personas helps market forecasters.
- **Qwen has 44.51 higher MSE than Llama** (p < 1e-8). The smaller Llama 8B outperforms Qwen 235B, likely due to same-model advantage (Llama forecasters predict Llama-generated simulations).

**ANOVA (Type III, Satterthwaite):**

| Effect | Sum Sq | F | p |
|---|---|---|---|
| tom | 358,076 | 4.90 | 0.027 * |
| model | 2,377,334 | 32.50 | 1.3e-08 *** |

### 3.4 Period Clustering Validation

**Likelihood ratio test:**

| Model | AIC | BIC | logLik | Deviance |
|---|---|---|---|---|
| Without period term | 68,481 | 68,520 | -34,235 | 68,469 |
| **With period term** | **67,842** | **67,887** | **-33,914** | **67,828** |

Chi-sq = 641.49, df = 1, **p < 2.2e-16**. The period-within-scenario intercept is overwhelmingly justified.

### 3.5 Random Effects Decomposition

| Component | Variance | SD | % of Total |
|---|---|---|---|
| scenario_id:period | 18,846 | 137.3 | **11.3%** |
| scenario_id | 103 | 10.1 | 0.1% |
| forecaster_id | 980 | 31.3 | 0.6% |
| Residual | 73,138 | 270.4 | 44.0% |

**Key finding:** The period-within-scenario term absorbs **11.3%** of total variance that was previously lumped in the residual. Without this term, the residual was 49.6%; with it, 44.0%. This represents substantial period-level variation in prediction difficulty.

The scenario-level intercept (0.1%) is negligible -- scenarios don't differ much *on average*, but they differ substantially *period by period* (11.3%). Forecaster identity explains only 0.6%, indicating demographic personas produce relatively homogeneous forecasters.

### 3.6 Supplementary Models

**Absolute price error:**
```
abs_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

| Effect | Estimate | SE | t | p |
|---|---|---|---|---|
| tom | -0.430 | 0.130 | -3.30 | **0.001 \*\*\*** |
| model (qwen) | +1.351 | 0.130 | 10.36 | **< 2e-16 \*\*\*** |

Note: convergence warning (max gradient = 0.006, tolerance = 0.002). Results should be interpreted cautiously but are consistent with the squared error model.

**Squared percentage error:**

| Effect | Estimate | SE | t | p |
|---|---|---|---|---|
| tom | -7.40 | 4.48 | -1.65 | 0.099 . |
| model (qwen) | +32.89 | 4.48 | 7.34 | **2.6e-13 \*\*\*** |

ToM effect is marginal for percentage error (p = 0.099), likely because percentage errors are noisier with extreme outliers from low-price periods.

### 3.7 Effect Sizes

| Model | no-ToM MSE | ToM MSE | Diff | Cohen's d | ToM wins |
|---|---|---|---|---|---|
| Llama | 110.03 | 98.26 | -11.76 | -0.082 | 7/10 scenarios |
| Qwen | 160.05 | 137.26 | -22.78 | -0.056 | 8/10 scenarios |
| **Overall** | **135.04** | **117.76** | **-17.27** | **-0.057** | — |

Cohen's d is small (-0.057) but the effect is consistent: ToM wins in 7-8 out of 10 scenarios for both models.

---

## 4. Results: Conflict Forecasting

### 4.1 Descriptive Statistics

| ToM | N | Accuracy | EI MAE | EI MSE | EI RMSE |
|-----|---|----------|--------|--------|---------|
| No | 1,200 | 43.3% | 0.645 | 0.846 | 0.920 |
| Yes | 1,200 | 32.4% | 0.799 | 1.132 | 1.064 |

Total N = 2,400 (10 scenarios x 24 periods x 5 forecasters x 2 ToM conditions).

### 4.2 Main Model

```
sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

| Fixed Effect | Estimate | SE | df | t | p |
|---|---|---|---|---|---|
| Intercept | 0.846 | 0.139 | 8.3 | 6.07 | 0.0003 *** |
| **tom** | **+0.286** | **0.112** | **2155** | **2.56** | **0.010 \*** |

**Interpretation: ToM INCREASES squared EI error by 0.286 units** (p = 0.010). Knowing conflict agent personas **hurts** forecasting accuracy.

**ANOVA (Type III, Satterthwaite):**

| Effect | Sum Sq | F | p |
|---|---|---|---|
| tom | 49.23 | 6.57 | 0.010 * |

### 4.3 Period Clustering Validation

| Model | AIC | BIC | logLik | Deviance |
|---|---|---|---|---|
| Without period term | 11,830 | 11,859 | -5,910 | 11,820 |
| **With period term** | **11,795** | **11,830** | **-5,892** | **11,783** |

Chi-sq = 37.34, df = 1, **p = 9.9e-10**. Period clustering is strongly justified.

### 4.4 Random Effects Decomposition

| Component | Variance | SD | % of Total |
|---|---|---|---|
| scenario_id:period | 0.557 | 0.746 | **3.6%** |
| scenario_id | 0.012 | 0.110 | 0.1% |
| forecaster_id | 0.048 | 0.220 | 0.3% |
| Residual | 7.489 | 2.737 | 48.0% |

The period-within-scenario term absorbs 3.6% of variance (less than market's 11.3%, but still significant at p < 1e-9). Without it, residual was 49.8%; with it, 48.0%.

### 4.5 Supplementary: Absolute EI Error

```
abs_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)
```

| Effect | Estimate | SE | t | p |
|---|---|---|---|---|
| **tom** | **+0.154** | **0.024** | **6.38** | **2.1e-10 \*\*\*** |

The absolute error model shows an even stronger ToM harm effect (p < 1e-10), indicating the result is robust across error metrics.

### 4.6 Effect Sizes

| Metric | no-ToM | ToM | Diff | Cohen's d | ToM wins |
|---|---|---|---|---|---|
| Sq EI error | 0.846 | 1.132 | +0.286 | 0.101 | 2/10 scenarios |
| Abs EI error | 0.645 | 0.799 | +0.154 | 0.227 | — |

### 4.7 Per-Forecaster Breakdown

**Every single forecaster gets worse with ToM:**

| Forecaster | MSE (no-ToM) | MSE (ToM) | Change |
|---|---|---|---|
| cautious_diplomat | 0.580 | 0.762 | +31% |
| contrarian_pundit | 1.049 | 1.692 | +61% |
| ir_professor | 0.769 | 1.141 | +48% |
| retired_general | 0.798 | 1.030 | +29% |
| young_analyst | 1.034 | 1.037 | +0.3% |

The contrarian_pundit shows the largest degradation (+61%). The young_analyst is barely affected. The pattern suggests that more opinionated personas overfit more strongly to expected agent behavior when given ToM.

---

## 5. PID Analysis: Conflict Simulation (Feb 17-18)

> **Note:** Market PID analysis (3 conditions, higher-order synergies, identity differentiation) is documented in detail in [`MARKET_EXPERIMENT.md` Section 9](MARKET_EXPERIMENT.md#9-pid-analysis-results-feb-16). This section covers conflict PID, with cross-domain comparison in Section 5.9.

### 5.1 Overview and Methods

Partial Information Decomposition (PID) measures emergent coordination between simulation agents. We use the Williams-Beer Imin framework to decompose the joint mutual information MI(X_i, X_j; Y) into four non-negative components:

- **Synergy:** Information the pair carries *jointly* but neither carries alone -- the signature of emergent coordination
- **Redundancy:** Information both agents carry independently (shared signal)
- **Unique_1, Unique_2:** Information only one agent carries

**Key metrics:**

- **Emergence Capacity (EC):** Median pairwise synergy across all C(n,2) agent pairs. For 7 agents, this is the median of 21 pairwise synergy values.
- **Faction-level EC:** Same computation restricted to within-faction pairs (e.g., 6 Novaris-Novaris pairs, 3 Tethys-Tethys pairs).
- **Cross-faction EC:** Median synergy of only cross-faction pairs (4 Novaris x 3 Tethys = 12 pairs). Within-faction pairs are excluded, isolating coordination that spans the faction boundary.
- **Higher-Order Capacity (G3):** For each agent triplet, G3 = MI(A,B,C; Y) - max(MI over all pairs). Positive G3 means the triplet carries information beyond the best pair. Median G3 across all C(n,3) triplets.
- **Identity-linked differentiation:** Jensen-Shannon Divergence (JSD) between each pair's action distributions. High JSD = behaviorally distinct agents.
- **Temporal consistency:** Split-half JSD within each agent (odd vs even periods). Low values = stable behavioral identity.

**Permutation tests (500 permutations each):**

- **Row-shuffle:** Randomly permute rows of the action matrix, destroying temporal alignment between agents while preserving marginal distributions. Tests whether synergy requires temporal coordination.
- **Column-shift:** Circularly shift each agent's column independently, preserving autocorrelation but destroying cross-agent alignment. Tests whether synergy requires inter-agent coordination beyond shared temporal trends.

**Variables:** Agent actions are discretized to a 5-level escalatory intensity scale (see 5.2). The target variable Y is the next-period change in escalation index, tercile-binned (DOWN / FLAT / UP).

**Three simulation conditions:**

We ran PID across three conditions to isolate what drives emergent coordination: the LLM itself, the persona prompts, or the domain structure.

| Condition | Agent decision-making | System prompt content | Motivation |
|-----------|----------------------|----------------------|------------|
| **Rule-based baseline** | Deterministic formula: `target_delta = (hawk_score - 0.5) * 3.0`, pick affordable action closest to target | None (no LLM) | Establishes floor: how much synergy arises from the simulation mechanics alone (shared state, resource constraints, escalation dynamics) without any intelligent reasoning. Any synergy above this is attributable to LLM reasoning. |
| **LLM no-persona** | Llama 3.1 8B via OpenRouter, temperature 0.7 | Role title + faction identity + faction context (grievances, objectives) + conflict history + task instructions | Isolates LLM contribution: agents reason about the scenario but lack individual identity. Tests whether the domain itself is rich enough to elicit coordination from generic advisors. |
| **LLM persona** | Same LLM configuration | All of the above + personal name, backstory, personality traits, speech patterns, key relationships, hawk/dove score, worldview description | Full condition: agents have both LLM reasoning and distinct identities. Tests whether persona-driven behavioral differentiation adds to or detracts from coordination. |

**Baseline formula walkthrough:**

The baseline uses each agent's hawk/dove score (a fixed numerical trait, 0 = pure dove, 1 = pure hawk) to compute a target escalation delta, then selects the most affordable action closest to that target. The formula has three regimes based on the current escalation index (EI):

```
Normal (EI 2.0-8.0):  target_delta = (hawk_score - 0.5) * 3.0
High   (EI > 8.0):    target_delta = (hawk_score - 0.5) * 1.0  (compressed: even hawks moderate)
Low    (EI < 2.0):    target_delta = (hawk_score - 0.3) * 1.0  (shifted: prevents over-de-escalation)
```

Applied to the 7 agents in the normal range:

| Agent | Faction | Hawk Score | target_delta | Closest Action (delta) |
|-------|---------|-----------|-------------|----------------------|
| Krasnov | Novaris | 0.85 | +1.05 | border_incursion (+1.2) |
| Bondar | Tethys | 0.75 | +0.75 | naval_blockade (+0.8) |
| Volkov | Novaris | 0.55 | +0.15 | intelligence_gathering (+0.1) |
| Morozov | Novaris | 0.50 | +0.00 | intelligence_gathering (+0.1) |
| Marchetti | Tethys | 0.45 | -0.15 | humanitarian_aid (-0.3) |
| Kovalenko | Tethys | 0.30 | -0.60 | ceasefire_offer (-0.6) |
| Petrova | Novaris | 0.25 | -0.75 | peace_talks (-0.8) |

The 0.5 offset centers the scale: scores above 0.5 escalate, below 0.5 de-escalate. The `* 3.0` multiplier stretches the range to cover the action space (deltas from -1.0 to +2.5). At EI extremes, the multiplier drops to 1.0, compressing all agents toward the center -- even Krasnov (0.85) only targets +0.35 at high EI instead of +1.05.

**Key limitation:** Volkov (0.55) and Morozov (0.50) produce nearly identical target deltas in all regimes, mapping to the same action. Morozov had zero action entropy (chose the same action every period) and was excluded from baseline PID. This illustrates why the baseline establishes a *floor* -- deterministic formulas create limited behavioral diversity, especially for agents near the center of the hawk/dove scale.

**Motivation:** The baseline isolates synergy from simulation mechanics alone (shared state, resource constraints, escalation dynamics) without any intelligent reasoning. In the market experiment, the equivalent baseline uses role-specific rules (producers sell at cost+margin, consumers buy at value-discount, speculators mean-revert) and showed significant synergy (EC = 0.041, p = 0.000), confirming the market mechanism can detect coordination. The conflict baseline plays the same role: any synergy above it is attributable to LLM reasoning rather than structural coupling.

All three conditions use the same 7 agents, same 10 scenario configurations (initial conditions, shock sequences), and same 30-period simulation engine. The only difference is how action recommendations are generated.

### 5.2 Action Encoding

Agent actions (13 types) are encoded on a 5-level escalatory intensity scale:

| Level | Actions | Interpretation |
|-------|---------|----------------|
| +2 (strong escalatory) | limited_strike, border_incursion, naval_blockade | Kinetic / territorial |
| +1 (mild escalatory) | cyber_attack, military_buildup, proxy_support, propaganda_campaign | Non-kinetic / preparatory |
| 0 (neutral) | intelligence_gathering, economic_sanctions | Information / economic pressure |
| -1 (mild de-escalatory) | ceasefire_offer, humanitarian_aid | Diplomatic gestures |
| -2 (strong de-escalatory) | peace_talks, trade_agreement | Commitment to resolution |

Target: next-period escalation index change, tercile-binned (DOWN / FLAT / UP).

### 5.3 Baseline Results (Rule-Based Agents)

**EC = 0.012 bits (not significant)**

The rule-based baseline produces minimal synergy. With Morozov excluded (zero action entropy), 6 agents yield 15 pairwise comparisons across 230 observations.

| Pair | MI | Synergy | Syn % | Note |
|------|-----|---------|-------|------|
| bondar x krasnov | 0.085 | 0.036 | 42.7% | Highest -- both hawks, opposite factions |
| bondar x petrova | 0.080 | 0.031 | 39.0% | |
| bondar x volkov | 0.080 | 0.031 | 39.0% | |
| krasnov x marchetti | 0.079 | 0.020 | 25.7% | |
| kovalenko x krasnov | 0.055 | 0.015 | 28.0% | |
| krasnov x petrova | 0.035 | 0.000 | 0.0% | Zero synergy |
| krasnov x volkov | 0.035 | 0.000 | 0.0% | Zero synergy |
| kovalenko x marchetti | 0.058 | 0.000 | 0.0% | Zero synergy |
| petrova x volkov | 0.028 | 0.000 | 0.0% | Zero synergy |

4 of 15 pairs have zero synergy. The formula's limited behavioral diversity (Volkov ≈ Morozov ≈ neutral, Petrova and Kovalenko both dove) means many agents select similar or identical actions each period. Synergy that does exist comes from the strongest hawks (Krasnov 0.85, Bondar 0.75) paired across factions -- their extreme actions create some joint signal about escalation direction.

**Comparison to market baseline:** The market baseline shows much stronger synergy (EC = 0.041, p = 0.000, 9/21 pairs significant). This is because market rules create structurally diverse agents -- producers *only sell*, consumers *only buy*, speculators do both -- generating cross-role complementarity by construction. The conflict baseline has no such structural constraint: all agents choose from the same 13 actions, differentiated only by a single scalar (hawk/dove score).

Critically, the relationship between LLM and baseline is *inverted* across domains. In market, the baseline has the highest EC and LLM personas only recover 79% of it. In conflict, LLM agents exceed the baseline by 8-9x (0.106-0.115 vs 0.012). Market coordination is mechanistic (structural role constraints), while conflict coordination is reasoning-driven (requires the strategic depth that LLMs provide). See Section 5.9 for full cross-domain comparison.

### 5.4 LLM Persona Results (Pairwise Detail)

All LLM conditions use Llama 3.1 8B (via OpenRouter, temperature 0.7), 10 scenarios, 30 periods, seed 42, yielding **290 observations** (10 scenarios x 29 usable periods). Target entropy H(Y) = 1.563 bits (98.6% efficiency).

**Persona condition -- EC = 0.106 bits, p = 0.000 (row-shuffle), p = 0.100 (column-shift)**

| Pair | MI | Synergy | Syn % | p (row) |
|------|-----|---------|-------|---------|
| krasnov x marchetti | 0.297 | 0.141 | 47.4% | **0.006** |
| kovalenko x volkov | 0.188 | 0.124 | 66.1% | **0.004** |
| morozov x petrova | 0.195 | 0.123 | 63.2% | **0.040** |
| bondar x marchetti | 0.312 | 0.123 | 39.5% | 0.084 |
| krasnov x volkov | 0.239 | 0.113 | 47.0% | **0.022** |
| krasnov x petrova | 0.233 | 0.111 | 47.7% | **0.020** |
| kovalenko x petrova | 0.176 | 0.107 | 60.8% | **0.012** |
| kovalenko x krasnov | 0.218 | 0.106 | 48.3% | **0.018** |

7 pairs individually significant at p < 0.05 (row-shuffle). Cross-faction pairs (e.g., krasnov x marchetti) show the highest absolute synergy, while within-Novaris pairs involving kovalenko show the highest synergy proportions (60-66%).

**No-persona condition -- EC = 0.115 bits, p = 0.010 (row-shuffle), p = 0.286 (column-shift)**

No-persona pairwise synergies are more uniformly distributed (range: 0.066-0.156) than persona (range: 0.076-0.141). Only 2 pairs are individually significant (bondar x morozov, kovalenko x morozov), compared to 7 for persona. This mirrors the market finding: without personas, synergy is more diffuse and harder to localize to specific pairs. The higher EC despite fewer significant pairs reflects a uniformly elevated synergy floor rather than a few strong pair-specific signals.

### 5.5 Faction-Level Analysis

| Faction Group | Persona EC | No-Persona EC | Delta |
|---------------|-----------|---------------|-------|
| Novaris (4 agents) | 0.109 | 0.103 | -0.006 |
| Tethys (3 agents) | 0.087 | 0.093 | +0.006 |
| **Cross-faction** | **0.103** | **0.121** | **+0.018** |

Cross-faction EC is the most affected by persona removal. Without personas anchoring agents to faction-specific dispositions (hawk/dove scores, worldviews), agents become more *collectively reactive* across the faction boundary (0.121 vs 0.103). Within-faction EC barely changes. This suggests personas primarily differentiate agents *within* a faction (hawk vs dove, realist vs institutionalist), and removing that differentiation allows agents to coordinate more freely across factions.

Escalation dynamics are inherently two-sided -- both factions' actions jointly determine the next EI change. The higher cross-faction EC without personas indicates that generic advisors respond more uniformly to the shared conflict state.

### 5.6 Three-Condition Comparison (Baseline / No-Persona / Persona)

| Metric | Baseline (rule) | LLM No-Persona | LLM Persona |
|--------|----------------|----------------|-------------|
| **Emergence Capacity** | 0.012 | **0.115** (p=0.010 row, 0.286 col) | 0.106 (p=0.000 row, 0.100 col) |
| Higher-Order Capacity (G3) | 0.000 | **0.314** | 0.230 |
| Positive G3 triplets | 6/20 (30%) | 35/35 (100%) | 35/35 (100%) |
| Mean pairwise JSD | 0.601 | **0.016** | 0.196 |
| Temporal consistency | 0.014 | 0.012 | 0.011 |
| Mean action entropy | 0.92 bits | **2.09 bits** | 1.90 bits |

**Key finding: Opposite pattern from market.** In market, removing personas destroyed synergy (EC dropped from 0.032 to 0.005, p=0.744). In conflict, removing personas *slightly increases* synergy (0.106 → 0.115) while collapsing differentiation to near-zero (JSD = 0.016).

**Permutation test note:** Both LLM conditions are significant under row-shuffle (persona p=0.000, no-persona p=0.010) but not column-shift (persona p=0.100, no-persona p=0.286). The column-shift test preserves each agent's autocorrelation, so it tests a stronger null: whether synergy exceeds what would arise from agents independently responding to shared temporal trends. The non-significant column-shift results suggest that much of the measured synergy reflects coordinated responses to the shared escalation trajectory rather than direct inter-agent coupling. This is expected -- agents don't communicate directly; they coordinate indirectly through the shared state.

**Baseline:** Rule-based agents (deterministic hawk/dove formula, no LLM). Morozov had zero action entropy (chose the same action every period) and was excluded from PID, reducing the baseline to 6 agents and 230 observations. Four baseline pairs had zero synergy.

**No-persona:** LLM agents with role/faction context but no personal name, backstory, personality traits, hawk/dove score, or worldview description. All 7 agents behave almost identically (JSD = 0.016) yet produce the highest synergy of any condition.

**Interpretation:** The conflict domain is inherently more strategic than market trading. Even generic LLM advisors produce rich, coordinated behavior because the geopolitical scenario naturally elicits diverse actions (2.09 bits entropy). Personas add identity differentiation (JSD 0.016 → 0.196) but slightly constrain synergy -- hawk/dove biases may reduce the flexibility that drives coordination.

### 5.7 Higher-Order Synergies (Triplet G3)

**100% of LLM triplets show positive G3** in both persona and no-persona conditions -- every 3-agent coalition carries information beyond the best pair.

| Metric | Persona | No-Persona |
|--------|---------|------------|
| Median G3 | 0.230 bits | **0.314 bits** |
| Mean G3 | 0.226 bits | **0.308 bits** |
| Positive G3 % | 100% (35/35) | 100% (35/35) |

No-persona agents show **37% higher triplet synergy** (median G3 = 0.314 vs 0.230). Because all agents behave nearly identically (JSD = 0.016), each additional agent in a coalition adds new information about the *shared conflict state response* rather than about individual identity. With personas, some of the triplet information is "used up" encoding persona-specific behavioral patterns.

Top triplets (persona condition):

| Triplet | G3 | MI_triplet | Best pair MI |
|---------|-----|-----------|-------------|
| kovalenko x marchetti x volkov | +0.319 | 0.557 | 0.238 |
| bondar x marchetti x volkov | +0.293 | 0.605 | 0.312 |
| marchetti x morozov x volkov | +0.289 | 0.547 | 0.259 |

All top triplets include at least one agent from each faction, confirming that the richest information structure spans the faction boundary.

### 5.8 Identity-Linked Differentiation

| Metric | Baseline (rule) | LLM No-Persona | LLM Persona |
|--------|----------------|----------------|-------------|
| **Mean pairwise JSD** | 0.601 | **0.016** | 0.196 |
| **Temporal consistency** | 0.014 | 0.012 | 0.011 |
| **Mean action entropy** | 0.92 bits | **2.09 bits** | 1.90 bits |

**Differentiation spectrum:** The three conditions span the full range of agent differentiation:
- **Baseline (JSD = 0.601):** Rigidly locked into narrow behavioral niches. Four pairs hit JSD = 1.0 (maximum). High differentiation but brittle.
- **Persona (JSD = 0.196):** Moderate differentiation with overlapping repertoires. Distinguishable but flexible -- *structured variety*.
- **No-persona (JSD = 0.016):** Near-zero differentiation. All 7 agents behave almost identically despite having different role titles. Role alone (e.g., "Military Commander" vs "Intelligence Director") is insufficient to create behavioral diversity without supporting persona context.

**Temporal consistency:** All conditions show high temporal consistency (split-half JSD < 0.025). LLM agents are slightly more consistent than baseline despite richer behavioral repertoires.

**Action entropy:** No-persona agents show the highest entropy (2.09 bits), slightly exceeding persona agents (1.90 bits). The geopolitical scenario elicits a wide behavioral repertoire from generic advisors. Personas slightly constrain this repertoire by anchoring agents to disposition-consistent actions (hawks escalate more, doves de-escalate more).

### 5.9 Cross-Domain PID Comparison (Market vs Conflict)

| Metric | Market Baseline | Market Persona | Market No-Persona | Conflict Baseline | Conflict Persona | Conflict No-Persona |
|--------|----------------|---------------|-------------------|-------------------|-----------------|-------------------|
| **EC** | 0.041 (p=0.000) | 0.032 (p=0.002) | 0.005 (p=0.744) | 0.012 | 0.106 (p=0.000) | **0.115** (p=0.010) |
| **G3** | 0.050 | 0.065 | 0.001 | 0.000 | 0.230 | **0.314** |
| **Mean JSD** | 0.478 | 0.450 | 0.012 | 0.601 | 0.196 | 0.016 |
| **Entropy** | 1.095 | 1.252 | 1.365 | 0.918 | 1.900 | **2.090** |
| **Agents** | 7 | 7 | 7 | 6 | 7 | 7 |
| **Obs** | 290 | 290 | 290 | 230 | 290 | 290 |

**Key cross-domain patterns:**

1. **LLM vs. baseline: mirror-image results across domains.** In market, the rule-based baseline has the *highest* EC (0.041) and LLM personas only recover 79% of it (0.032). In conflict, both LLM conditions far exceed the baseline (0.106-0.115 vs 0.012, an 8-9x increase). The domains are inverted:

    | | Market | Conflict |
    |---|---|---|
    | Baseline EC | **0.041** (highest) | 0.012 (lowest) |
    | LLM no-persona EC | 0.005 (lowest) | **0.115** (highest) |
    | LLM persona EC | 0.032 (middle) | 0.106 (middle) |
    | LLM > baseline? | **No** | **Yes (8-9x)** |

    This reveals two fundamentally different coordination regimes. Market coordination is *mechanistic* -- simple rules that structurally constrain agents to different sides of the market (producers only sell, consumers only buy) create complementarity by construction. LLMs struggle to match this because generic prompting converges to "bid near last price" regardless of role. Conflict coordination is *reasoning-driven* -- a single-scalar formula can't capture the strategic complexity of geopolitical decision-making, but LLMs naturally produce rich, context-dependent actions that generate coordination even without persona differentiation.

2. **Personas have opposite effects:** In market, personas are *necessary* for synergy (EC collapses from 0.032 to 0.005 without them). In conflict, personas are *unnecessary* and slightly reduce synergy (0.106 vs 0.115). Persona-driven strategies (momentum, contrarian, etc.) create the behavioral diversity that market coordination requires. The geopolitical scenario itself elicits coordination from generic advisors.

3. **No-persona convergence is universal:** No-persona agents show near-zero differentiation in both domains (JSD ≈ 0.012-0.016). What differs is whether the domain provides enough intrinsic strategic structure to generate synergy *without* identity-linked behavioral diversity.

4. **Conflict coordination is domain-driven, market coordination is persona-driven:** This explains the forecasting asymmetry. Static ToM descriptions capture persona-driven coordination (market) but cannot capture domain-driven coordination (conflict), where agent dynamics are complex regardless of personas.

**Implications for forecasting:** ToM *helps* market forecasting (p = 0.027) because it describes the personas that drive coordination. ToM *hurts* conflict forecasting (p = 0.010) because it provides static persona descriptions for a domain where coordination arises from the scenario dynamics, not from persona-specific behavior. The PID results explain *why*: in market, knowing personas gives you the source of coordination; in conflict, personas are not the source.

---

## 6. Cross-Domain Comparison

### 6.1 Opposite ToM Effects

| Domain | ToM Effect | Direction | p | Interpretation |
|--------|-----------|-----------|---|----------------|
| **Market** | -17.27 MSE | **Helps** | 0.027 | Agent strategies are predictive of price direction |
| **Conflict** | +0.286 MSE | **Hurts** | 0.010 | Agent personas cause overfitting to expected behavior |

This is the central finding: **ToM's value depends on the domain and the predictability of the mapping from agent personas to outcomes.**

### 6.2 Why the Difference?

**Market:** Agent strategies have a *direct, mechanistic* link to prices. If you know the Momentum Rider buys after uptrends, you can predict buying pressure after a price increase. The double-auction clearing mechanism makes agent behavior -> price a transparent, near-deterministic mapping.

**Conflict:** Agent personas describe dispositions (hawk/dove scores, personality traits) but the mapping from disposition to action to escalation is *stochastic and context-dependent*. A hawk doesn't always escalate; a dove doesn't always de-escalate. Knowing that Krasnov is a hawk may lead forecasters to overpredict escalation in periods where even Krasnov de-escalates due to resource constraints.

### 6.3 Period Clustering Comparison

| Domain | Period-cluster variance | % of total | LRT p-value |
|--------|----------------------|-----------|-------------|
| Market | 18,846 | 11.3% | < 2.2e-16 |
| Conflict | 0.557 | 3.6% | 9.9e-10 |

Period clustering is justified in both domains but captures more variance in market (11.3% vs 3.6%). This makes sense: market prices are more volatile period-to-period (price shocks create sharp difficulty spikes), while escalation indices change more smoothly.

---

## 7. Methodological Notes

### 7.1 Satterthwaite vs. Kenward-Roger

We use Satterthwaite degrees of freedom rather than Kenward-Roger. With 240 nested random intercept groups and N = 2,400-4,800, the Kenward-Roger correction is computationally prohibitive (hours per model) while producing near-identical results. Satterthwaite is the default in `lmerTest` and is well-validated for these sample sizes.

### 7.2 Same-Model Confound (Market)

The market simulation was generated by Llama 8B agents. Llama 8B forecasters are therefore predicting agents that share their weights and reasoning patterns, while Qwen forecasters are predicting "foreign" agents. The model fixed effect (Qwen = +44.51, p < 1e-8) is confounded with this same-model advantage. However, the **ToM effect is valid within both models** (no significant interaction), so the ToM finding is not affected.

### 7.3 Multiple Comparisons

We report all models fit (primary + supplementary) without formal multiple comparison correction. The primary model is pre-specified; supplementary models (absolute error, percentage error) serve as robustness checks. All three error metrics for market and both for conflict point in the same direction.

### 7.4 Residual Variance

Even with period clustering, residual variance remains high (44-48% of total). This reflects:
1. Irreducible noise in LLM forecasting
2. Within-period variation across forecasters facing the same data
3. Possible unmodeled structure (e.g., interactions between forecaster type and scenario difficulty)

---

## 8. Reproduction

### Running the Analyses

```bash
cd D:/Northeastern/LLM_Forecasting

# Market LMM analysis
Rscript market/analyze_forecasts.R

# Conflict LMM analysis
Rscript conflict/analyze_forecasts.R

# --- Conflict simulations (to regenerate data) ---

# Baseline (rule-based, no LLM)
python conflict/run_conflict_sim.py --n_scenarios 10 --n_periods 30 --baseline --seed 42

# LLM no-persona (Llama 8B, roles + faction only)
python conflict/run_conflict_sim.py --n_scenarios 10 --n_periods 30 --model llama --no-persona --seed 42

# LLM persona (Llama 8B, full persona prompts)
python conflict/run_conflict_sim.py --n_scenarios 10 --n_periods 30 --model llama --seed 42

# --- PID analyses ---

# Conflict PID -- persona (with baseline comparison)
python conflict/run_conflict_pid.py \
    --results-dir outputs/conflict_llama_persona \
    --baseline-dir outputs/conflict_baseline \
    --n-permutations 500 --encoding direction_aggr

# Conflict PID -- no-persona (with baseline comparison)
python conflict/run_conflict_pid.py \
    --results-dir outputs/conflict_llama_no_persona \
    --baseline-dir outputs/conflict_baseline \
    --n-permutations 500 --encoding direction_aggr
```

### Dependencies

- R 4.2+ with `lme4`, `lmerTest`, `dplyr`
- Data in `outputs/market_llama_persona/` and `outputs/conflict_llama_persona/`

### Data Locations

**Market forecasting data:**

| Condition | Path |
|-----------|------|
| Llama demographic, no ToM | `outputs/market_llama_persona/forecasting_demographic/forecast_results.csv` |
| Llama demographic, ToM | `outputs/market_llama_persona/forecasting_demographic_tom/forecast_results.csv` |
| Qwen demographic, no ToM | `outputs/market_llama_persona/forecasting_qwen_demographic/forecast_results.csv` |
| Qwen demographic, ToM | `outputs/market_llama_persona/forecasting_qwen_demographic_tom/forecast_results.csv` |

**Conflict forecasting data:**

| Condition | Path |
|-----------|------|
| Llama demographic, no ToM | `outputs/conflict_llama_persona/forecasting_demographic/forecast_results.csv` |
| Llama demographic, ToM | `outputs/conflict_llama_persona/forecasting_demographic_tom/forecast_results.csv` |

**PID analysis data:**

| Condition | Path |
|-----------|------|
| Conflict LLM persona (simulation) | `outputs/conflict_llama_persona/scenario_*.json` |
| Conflict LLM no-persona (simulation) | `outputs/conflict_llama_no_persona/scenario_*.json` |
| Conflict baseline (simulation) | `outputs/conflict_baseline/scenario_*.json` |
| Conflict PID results (persona) | `outputs/conflict_llama_persona/pid_analysis/` |
| Conflict PID results (no-persona) | `outputs/conflict_llama_no_persona/pid_analysis/` |
| Market LLM persona (simulation) | `outputs/market_llama_persona/scenario_*.json` |
| Market PID results | `outputs/market_llama_persona/pid_analysis_v2/` |

**Analysis scripts:**

| Script | Description |
|--------|-------------|
| `market/analyze_forecasts.R` | Market LMM analysis |
| `conflict/analyze_forecasts.R` | Conflict LMM analysis |
| `conflict/run_conflict_pid.py` | Conflict PID analysis |
| `market/run_market_pid.py` | Market PID analysis |
| `market/pid_analysis.py` | Shared PID computation (Williams-Beer Imin) |

---

## 9. Summary Table

### 9.1 Forecasting

| | Market | Conflict |
|---|---|---|
| **N (observations)** | 4,800 | 2,400 |
| **Scenario-period clusters** | 240 | 240 |
| **Primary DV** | Squared price error | Squared EI error |
| **Fixed effects** | tom + model | tom |
| **Random effects** | (1\|scenario_id) + (1\|scenario_id:period) + (1\|forecaster_id) | (1\|scenario_id) + (1\|scenario_id:period) + (1\|forecaster_id) |
| **ToM effect** | -17.27 (p = 0.027) | +0.286 (p = 0.010) |
| **ToM direction** | Helps | Hurts |
| **Model effect** | Qwen +44.51 (p < 1e-8) | N/A |
| **tom:model interaction** | ns (p = 0.480) | N/A |
| **Period clustering LRT** | p < 2.2e-16 | p = 9.9e-10 |
| **Period variance absorbed** | 11.3% | 3.6% |
| **Cohen's d (ToM)** | -0.057 | +0.101 |

### 9.2 PID (Emergent Coordination)

| | Market Persona | Market No-Persona | Conflict Persona | Conflict No-Persona | Conflict Baseline |
|---|---|---|---|---|---|
| **Observations** | 290 | 290 | 290 | 290 | 230 |
| **Agents** | 7 | 7 | 7 | 7 | 6 (1 dropped) |
| **Emergence Capacity** | 0.032 (p=0.002) | 0.005 (p=0.744) | 0.106 (p=0.000) | **0.115** (p=0.010) | 0.012 |
| **Higher-Order (G3)** | 0.065 | 0.001 | 0.230 | **0.314** | 0.000 |
| **Positive G3 %** | 100% | -- | 100% | 100% | 30% |
| **Mean JSD** | 0.450 | 0.012 | 0.196 | 0.016 | 0.601 |
| **Consistency** | 0.006 | -- | 0.011 | 0.012 | 0.014 |
| **Action entropy** | 1.252 | 1.365 | 1.900 | **2.090** | 0.918 |
| **Encoding** | dir_aggr (5) | dir_aggr (5) | dir_aggr (5) | dir_aggr (5) | dir_aggr (5) |
