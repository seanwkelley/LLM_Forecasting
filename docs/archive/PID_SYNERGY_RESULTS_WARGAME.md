# Emergent Coordination in Multi-Agent Crisis Simulation (Wargame): PID Analysis Results

**Date:** February 15, 2026
**Dataset:** v3.11 (50 crisis scenarios, parameter-sensitive agents)
**Analysis:** Partial Information Decomposition with permutation significance testing
**Binning:** Tercile (equal-frequency) — corrected from earlier fixed-bin analysis

---

## 1. Research Question

Do LLM-based agents in a multi-agent wargame simulation exhibit **genuine emergent coordination** — that is, do pairs of domain experts produce synergistic information about crisis outcomes that neither expert provides alone? Or is apparent coordination merely redundant (cosmetic diversity) or attributable to chance?

We apply Partial Information Decomposition (PID) to decompose the mutual information between agent action proposals and crisis outcomes into four non-overlapping atoms: **synergy**, **redundancy**, **unique information from agent i**, and **unique information from agent j**. We then use permutation testing to determine whether observed synergy exceeds what random chance would produce.

---

## 2. The Entropy Trap: A Methodological Cautionary Tale

### 2.1 What Happened

Our initial analysis used **fixed bins** to discretize the target variable (collapse probability):

| Bin | Range | N scenarios | Percentage |
|-----|-------|-------------|------------|
| LOW | [0, 0.45) | 3 | 6% |
| MEDIUM | [0.45, 0.65) | 44 | 88% |
| HIGH | [0.65, 1.0] | 3 | 6% |

This produced a highly imbalanced distribution with H(Y) = 0.63 bits (max possible = 1.58 bits, efficiency = 40%). The 88% concentration in a single bin meant tiny fluctuations in the sparse bins could appear statistically significant.

The fixed-bin analysis reported **Novaris EC p < 0.001** — seemingly highly significant emergent coordination. This was wrong.

### 2.2 The Fix: Tercile Binning

We switched to **tercile** (equal-frequency) binning via `pd.qcut()`:

| Bin | Range | N scenarios | Percentage |
|-----|-------|-------------|------------|
| LOW | (0.348, 0.520] | 17 | 34% |
| MEDIUM | (0.520, 0.571] | 16 | 32% |
| HIGH | (0.571, 0.768] | 17 | 34% |

This produces H(Y) = 1.58 bits (near-maximum entropy), giving PID the best possible signal to work with.

### 2.3 The Impact

| Metric | Fixed bins (WRONG) | Tercile bins (CORRECT) |
|--------|-------------------|----------------------|
| Novaris EC | 0.115 bits | 0.075 bits |
| Novaris EC p-value | **0.000** | **0.765** |
| Tethys EC | 0.028 bits | 0.045 bits |
| Tethys EC p-value | 0.064 | 0.234 |
| Novaris Synergy % | 51.6% | 47.5% |
| Tethys Synergy % | 44.1% | 35.6% |

**The entropy trap completely invalidated the old results.** With proper binning, NO synergy is statistically significant.

### 2.4 Lesson

Low-entropy targets are a trap for information-theoretic analysis. When one target bin dominates (88%), random permutations produce *lower* synergy than observed because the permutation destroys even the small structure needed to distinguish the sparse bins. This creates false significance — the observed synergy isn't high, the null distribution is artificially low.

**Rule:** Always use equal-frequency (quantile) binning for PID targets, never fixed thresholds, unless the thresholds have strong domain justification and produce balanced classes.

---

## 3. Methods

### 3.1 Simulation Environment

The Tethys-Novaris wargame simulation models a geopolitical crisis between two fictionalized nations. Each faction has domain expert agents (military, economic, intelligence, diplomatic) who independently propose actions, which are then approved or vetoed by a leader agent. 50 scenarios were generated with parametrically varied initial conditions using Latin Hypercube Sampling:

| Parameter | Range | Description |
|-----------|-------|-------------|
| Territory controlled | 0-40% | Territory under aggressor control |
| Military balance | -0.3 to +0.1 | Novaris advantage to Tethys advantage |
| Sanctions level | 0-80% | Economic sanctions on Novaris |
| International support | 30-90% | Diplomatic support for Tethys |
| Crisis level | 3-10 | Severity (1-10 scale) |

Each scenario was simulated for 1 period, producing ground truth outcomes including collapse probability (continuous, 0-1).

**Novaris agents:** Economic Advisor, Intelligence Director, Military General (3 agents)
**Tethys agents:** Diplomat, Economic Advisor, Intelligence Director, Military General (4 agents)

### 3.2 Action-to-Escalation Encoding

Each agent's proposed action was mapped to a 5-level ordinal escalation scale:

| Level | Label | Example Actions |
|-------|-------|-----------------|
| -1 | De-escalatory | Peace talks, humanitarian aid, prisoner exchange |
| 0 | Neutral/Defensive | Surveillance, cyber defense, enhanced patrols |
| +1 | Assertive | Sanctions, coalition building, military buildup |
| +2 | Aggressive | Cyber attack, sabotage, disinformation |
| +3 | Extreme | Military strike, blockade, occupation |

43 distinct actions were mapped across these levels. When agents proposed multiple actions, only the **primary** (highest-priority) proposal was used.

### 3.3 Target Discretization (Tercile)

Collapse probability was discretized into 3 equal-frequency bins using `pd.qcut()`:

| Bin | Range | N | Label |
|-----|-------|---|-------|
| 0 | (0.348, 0.520] | 17 | LOW |
| 1 | (0.520, 0.571] | 16 | MEDIUM |
| 2 | (0.571, 0.768] | 17 | HIGH |

This ensures near-maximum target entropy H(Y) ~ 1.58 bits, avoiding the entropy trap described in Section 2.

### 3.4 PID Computation

We used the **BROJA** (Bertschinger-Rauh-Olbrich-Jost-Ay) bivariate PID decomposition implemented in the `dit` Python library. For each pair of agents (i, j) and the target variable Y (discretized collapse probability):

```
MI(X_i, X_j ; Y) = Synergy + Redundancy + Unique_i + Unique_j
```

Where:
- **Synergy**: Information about Y that requires observing *both* agents jointly
- **Redundancy**: Information about Y that *both* agents provide individually
- **Unique_i / Unique_j**: Information about Y provided by one agent but not the other

### 3.5 Emergence Capacity

Following Riedl's S_macro metric, we define **Emergence Capacity (EC)** as the median pairwise synergy across all agent pairs within a faction:

```
EC = median({synergy(i,j) : all pairs i,j})
```

### 3.6 Permutation Significance Testing

To test H_0: "observed synergy is consistent with independent agent behavior," we applied two complementary surrogate generation methods with **1,000 permutations** each:

#### Row-Shuffle Surrogate (Primary)

For each permutation: independently shuffle each agent column's values, compute PID on the surrogate matrix, extract pairwise synergies and EC.

**Null preserved:** Marginal distributions of each agent's actions
**Null broken:** Inter-agent correlations and agent-outcome alignment

#### Column-Shift Surrogate (Secondary)

For each permutation: circularly shift each agent column by a random offset in [1, N), compute PID.

**Null preserved:** Autocorrelation structure within each agent
**Null broken:** Temporal alignment between agents and outcomes

#### P-value Calculation

```
p = (# surrogates with synergy >= observed) / (total surrogates)
```

One-sided test: we are interested in whether observed synergy exceeds chance levels.

---

## 4. Results

### 4.1 Summary Statistics

| Metric | Novaris (3 agents) | Tethys (4 agents) |
|--------|-------------------|-------------------|
| N scenarios | 50 | 50 |
| N agent pairs | 3 | 6 |
| Mean Mutual Information | 0.164 bits | 0.179 bits |
| Mean Synergy | 0.078 bits | 0.064 bits |
| Mean Redundancy | 0.003 bits | 0.023 bits |
| Synergy % of MI | 47.5% | 35.6% |
| Redundancy % of MI | 1.8% | 12.6% |
| Emergence Capacity | 0.075 bits | 0.045 bits |
| EC p-value (row-shuffle) | **0.765** | **0.234** |
| EC p-value (column-shift) | **0.793** | incomplete* |
| Interpretation | NOT SIGNIFICANT | NOT SIGNIFICANT |

*Tethys column-shift terminated at ~700/1000 permutations. Row-shuffle is the primary test.

**Neither faction shows statistically significant emergent coordination** at any conventional significance level (alpha = 0.05 or 0.10).

### 4.2 Pairwise PID Decomposition

#### Novaris (Proposed Actions)

| Agent Pair | MI | Synergy | Syn% | Red | Unique_i | Unique_j |
|------------|-----|---------|------|-----|----------|----------|
| Economic x Intelligence | 0.214 | 0.097 | 45.6% | 0.005 | 0.111 | ~0.000 |
| Economic x Military | 0.200 | 0.075 | 37.5% | 0.004 | 0.113 | 0.009 |
| Intelligence x Military | 0.079 | 0.062 | 78.1% | ~0.000 | 0.005 | 0.012 |

The Economic agent dominates unique information (0.111-0.113 bits). Intelligence-Military shows the highest synergy *percentage* (78.1%) but on a very small MI base (0.079 bits). All synergy values are well within chance levels (p > 0.23 for all pairs).

#### Novaris (Final Actions, post-leader)

| Agent Pair | MI | Synergy | Syn% | Red | Unique_i | Unique_j |
|------------|-----|---------|------|-----|----------|----------|
| Economic x Intelligence | 0.205 | 0.096 | 47.0% | 0.005 | 0.103 | ~0.000 |
| Economic x Military | 0.183 | 0.069 | 37.7% | 0.007 | 0.102 | 0.006 |
| Intelligence x Military | 0.079 | 0.062 | 78.1% | ~0.000 | 0.005 | 0.012 |

Leader filtering slightly reduces MI and synergy for Economic pairs but leaves Intelligence-Military unchanged. The leader does not meaningfully alter the information structure.

#### Tethys (Proposed Actions)

| Agent Pair | MI | Synergy | Syn% | Red | Unique_i | Unique_j |
|------------|-----|---------|------|-----|----------|----------|
| Diplomatic x Economic | 0.291 | **0.172** | 59.2% | 0.035 | 0.006 | 0.078 |
| Diplomatic x Military | 0.219 | **0.117** | 53.2% | 0.028 | 0.013 | 0.062 |
| Economic x Military | 0.231 | 0.083 | 36.0% | 0.056 | 0.058 | 0.034 |
| Economic x Intelligence | 0.144 | 0.008 | 5.5% | 0.009 | 0.105 | 0.023 |
| Intelligence x Military | 0.116 | ~0.000 | 0.0% | 0.006 | 0.026 | 0.084 |
| Diplomatic x Intelligence | 0.074 | 0.004 | 4.8% | 0.002 | 0.039 | 0.030 |

Two Diplomatic pairs show the highest raw synergy: Diplomatic-Economic (0.172 bits, p=0.100) and Diplomatic-Military (0.117 bits, p=0.093). These approach but do not reach significance at alpha=0.05.

Economic-Military shows the highest redundancy (0.056 bits, 24.1% of MI), indicating overlapping rather than complementary information.

Intelligence has near-zero synergy with Military (0.000 bits) and Economic (0.008 bits) — it operates as an independent channel.

#### Tethys (Final Actions, post-leader)

| Agent Pair | MI | Synergy | Syn% | Red | Unique_i | Unique_j |
|------------|-----|---------|------|-----|----------|----------|
| Diplomatic x Economic | 0.326 | **0.184** | 56.6% | 0.036 | 0.005 | 0.101 |
| Diplomatic x Military | 0.219 | 0.115 | 52.4% | 0.027 | 0.015 | 0.063 |
| Economic x Military | 0.248 | 0.080 | 32.3% | 0.059 | 0.078 | 0.031 |
| Economic x Intelligence | 0.168 | 0.010 | 5.7% | 0.010 | 0.127 | 0.022 |
| Intelligence x Military | 0.116 | ~0.000 | 0.0% | 0.006 | 0.026 | 0.084 |
| Diplomatic x Intelligence | 0.074 | 0.004 | 4.8% | 0.002 | 0.039 | 0.030 |

Leader filtering increases Diplomatic-Economic synergy (0.172 -> 0.184) and Economic unique info (0.105 -> 0.127). The Tethys leader slightly amplifies the information structure.

### 4.3 Permutation Test Results

#### Novaris — Row-Shuffle (1,000 permutations)

| Metric | Observed | p-value | Significance |
|--------|----------|---------|--------------|
| **Emergence Capacity** | 0.075 bits | **0.765** | n.s. |
| Economic x Intelligence | 0.097 | 0.715 | n.s. |
| Economic x Military | 0.075 | 0.858 | n.s. |
| Intelligence x Military | 0.062 | 0.230 | n.s. |

#### Novaris — Column-Shift (1,000 permutations)

| Metric | Observed | p-value | Significance |
|--------|----------|---------|--------------|
| **Emergence Capacity** | 0.075 bits | **0.793** | n.s. |
| Economic x Intelligence | 0.097 | 0.683 | n.s. |
| Economic x Military | 0.075 | 0.887 | n.s. |
| Intelligence x Military | 0.062 | 0.250 | n.s. |

Both surrogate methods agree: Novaris synergy is entirely consistent with chance (p > 0.23 for all pairs).

#### Tethys — Row-Shuffle (1,000 permutations)

| Metric | Observed | p-value | Significance |
|--------|----------|---------|--------------|
| **Emergence Capacity** | 0.045 bits | **0.234** | n.s. |
| Diplomatic x Economic | 0.172 | 0.100 | n.s. |
| Diplomatic x Intelligence | 0.004 | 0.380 | n.s. |
| Diplomatic x Military | 0.117 | 0.093 | n.s. |
| Economic x Intelligence | 0.008 | 0.511 | n.s. |
| Economic x Military | 0.083 | 0.818 | n.s. |
| Intelligence x Military | ~0.000 | 0.868 | n.s. |

Tethys shows somewhat lower p-values for Diplomatic pairs (0.093-0.100), suggesting a possible weak signal, but nothing reaches conventional significance.

---

## 5. Interpretation

### 5.1 No Statistically Significant Emergence

The central finding is negative: **we cannot reject the null hypothesis that observed synergy arises by chance**. This holds for all agent pairs in both factions, across both surrogate methods.

This does NOT mean agents aren't coordinating. It means:
1. With N=50 scenarios, PID lacks statistical power to detect coordination
2. The 5-level escalation encoding may be too coarse to capture meaningful variation
3. Or the coordination signal is genuinely weak in this simulation architecture

### 5.2 Descriptive Patterns (Non-Significant)

While no results are statistically significant, the descriptive patterns are still informative:

**Diplomatic-Economic synergy (Tethys):** The highest raw synergy (0.172 bits, 59.2% of MI) with the lowest p-value (0.100). If any pair has genuine coordination, this is the best candidate. Substantively, the interaction between diplomatic posture and economic policy may carry information about outcomes that neither domain provides alone.

**Economic uniqueness:** The Economic agent consistently carries the most unique information across both factions (0.105-0.113 bits). Economic policy choices are the most individually informative about crisis outcomes.

**Intelligence independence:** Intelligence agents show near-zero synergy with all other agents. Their information about outcomes is independent of what other agents do.

### 5.3 Why the Fixed-Bin Results Were Wrong

The old fixed-bin analysis (Section 2) reported p < 0.001 for Novaris EC. This was an artifact of low target entropy:

- With 88% of scenarios in one bin, the PID had very little signal to decompose
- Random permutations destroyed even the small structure distinguishing the 6% tails
- This made the null distribution artificially low, inflating significance
- Tercile binning maximizes target entropy, giving the permutation test a fair baseline

### 5.4 Implications for the Market Experiment

These null results motivate a complementary approach: the **market simulation experiment** (see `docs/MARKET_EXPERIMENT_DESIGN.md`). The market design addresses the limitations that may explain null results here:

| Limitation (Wargame PID) | Market Experiment Solution |
|---------------------------|---------------------------|
| N=50 scenarios | N=hundreds of periods per scenario, pooled across scenarios |
| Coarse 5-level encoding | Continuous price/quantity actions |
| Single-shot simulation | Repeated interactions with feedback |
| Agents don't see each other | Market price aggregates all agent info |
| No incentive structure | Profit/loss from trading |

---

## 6. Limitations

1. **Small sample size (N=50):** PID estimation from empirical distributions is noisy. The 5-level escalation scale and 3-level target create sparse contingency tables. A power analysis suggests N > 200 may be needed for reliable synergy detection.

2. **Discretization dependency:** Even with tercile binning, PID results depend on the number of bins and the target variable chosen. Different target variables (casualty count, escalation index) might yield different conclusions.

3. **Single simulation system:** Results reflect one specific wargame simulation. Other multi-agent architectures or task domains may show different coordination patterns.

4. **BROJA limitations:** The bivariate BROJA decomposition only examines pairs. Higher-order synergies (requiring 3+ agents simultaneously) are not captured.

5. **Action aggregation:** Using only the primary proposed action discards information from secondary proposals. Richer encodings might reveal coordination that the coarse escalation scale misses.

---

## 7. Conclusion

Partial Information Decomposition with proper tercile binning reveals **no statistically significant emergent coordination** in the multi-agent wargame simulation. While descriptive synergy percentages are non-trivial (35-48% of MI), permutation testing shows these levels are consistent with chance given the sample size and encoding resolution.

The strongest candidate signal is the Tethys Diplomatic-Economic pair (synergy = 0.172 bits, p = 0.100), but this does not reach conventional significance.

Key takeaways:

1. **Target entropy matters critically** — fixed bins created an entropy trap that produced false significance
2. **N=50 is likely insufficient** for reliable PID-based coordination detection with coarse action encodings
3. **The market experiment** provides a complementary approach with more observations, richer action spaces, and repeated interactions

---

## Appendix A: Comparison to Previous (Incorrect) Analysis

| Metric | Fixed-bin (WRONG) | Tercile (CORRECT) | Change |
|--------|-------------------|-------------------|--------|
| Novaris EC | 0.115 | 0.075 | -35% |
| Novaris EC p | **0.000** | 0.765 | Completely reversed |
| Tethys EC | 0.028 | 0.045 | +61% |
| Tethys EC p | 0.064 | 0.234 | Weakened further |
| Novaris Syn% | 51.6% | 47.5% | -4.1pp |
| Tethys Syn% | 44.1% | 35.6% | -8.5pp |

The tercile analysis is authoritative. All prior results using fixed bins `[0, 0.45, 0.65, 1.0]` are superseded.

## Appendix B: File Locations

| Item | Path |
|------|------|
| PID analysis engine | `forecasting/pid_analysis.py` |
| Data extraction | `forecasting/pid_data_extraction.py` |
| Visualization | `forecasting/pid_visualization.py` |
| Orchestration script | `forecasting/run_pid_emergence_analysis.py` |
| v3.11 dataset | `outputs/multiscenario_v311/` |
| Results (tercile, authoritative) | `experiment_results/pid_analysis_v311_tercile/` |
| Results (fixed-bin, SUPERSEDED) | `experiment_results/pid_analysis_v311_crisis_full/` |
| Summary JSON | `experiment_results/pid_analysis_v311_tercile/pid_summary.json` |
| Pairwise CSVs | `experiment_results/pid_analysis_v311_tercile/{faction}_pairwise_pid.csv` |

## Appendix C: Reproduction

```bash
cd D:\Northeastern\LLM_Forecasting

# Correct analysis (tercile binning)
python forecasting/run_pid_emergence_analysis.py \
  --data-dir outputs/multiscenario_v311 \
  --output-dir experiment_results/pid_analysis_v311_tercile \
  --n-permutations 1000 \
  --target collapse_probability \
  --collapse-bins tercile \
  --aggregation primary \
  --collapse-levels 5 \
  --seed 42
```

Runtime: ~10 minutes (50 scenarios, 2 factions, 1000 permutations per method)

---

## 8. Market Experiment

The wargame's null PID results motivated a complementary market simulation experiment with a deterministic clearing mechanism (no LLM aggregator). Full market PID results, higher-order synergies, identity differentiation, and forecasting results are documented in the dedicated market doc:

**See: `docs/MARKET_EXPERIMENT_DESIGN.md`** — Sections 9 (PID results) and 11 (forecasting results).

### Key cross-system comparison

| Metric | Wargame (this doc) | Market Baseline | Market LLM (persona) |
|--------|-------------------|----------------|---------------------|
| N observations | 50 | 290 | 290 |
| Target entropy H(Y) | 1.58 bits | 1.39 bits | **1.55 bits** |
| Emergence Capacity | 0.075 bits | **0.041 bits** | **0.032 bits** |
| EC p-value | 0.765 | **0.000** | **0.002** |
| Interpretation | Not significant | **SIGNIFICANT** | **SIGNIFICANT** |

The market experiment succeeded where the wargame did not — the mechanistic outcome (price), larger sample (290 obs), and persona-driven behavioral diversity enabled statistically significant PID synergy detection.
