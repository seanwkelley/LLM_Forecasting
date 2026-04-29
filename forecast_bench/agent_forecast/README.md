# Agent-forecast pipeline

DAG-guided agentic forecasting extension. Tests whether topology-targeted
evidence gathering (focus search on high-betweenness factors) improves
Brier-scored forecast accuracy beyond a decomposition-only control, free-form
untargeted search, and a no-search baseline.

## Design

Four conditions, all starting from the same Stage 1 DAG and initial
probability `p0`:

| Condition | Evidence gathering | What it tests |
|---|---|---|
| `no_search` | None; `p1 = p0` | Baseline — accuracy of pure elicited forecast |
| `untargeted` | Agent free-searches the question, budget = `MAX_SEARCH_QUERIES` | Does any retrieval help? |
| `topology_targeted` | Agent searches focused on top-k **high-betweenness** factors, same budget | Does centrality-guided search help? |
| `peripheral_targeted` | Agent searches focused on bottom-k **low-betweenness** factors, same budget | Decomposition-only control for `topology_targeted` |

Budgets are held **equal** across all three search conditions so the
comparisons isolate the effect of *where* the search is aimed rather than
*how much* is retrieved.

**Primary contrast**: `topology_targeted` vs `peripheral_targeted`. Both
decompose the search into three factor-scoped queries; only the factor
selection differs. A topology win here proves centrality is load-bearing, not
just the act of decomposing. A tie means decomposition alone was the
operative mechanism.

**Secondary contrast**: `topology_targeted` vs `untargeted`. Tests the
combined effect of decomposition plus centrality.

**Tertiary**: `topology_targeted` vs `no_search`. Reference for overall
retrieval value.

## Why future-resolving only

The experiment requires zero training-data contamination of outcomes. Using
already-resolved questions would let an agent Google the answer (for event
questions) or read it off a database (for time-series). So we restrict to
questions whose **resolution dates are in the future at run time** —
ForecastBench publishes rolling sets for exactly this purpose. Pull the
latest release before each run.

## Setup

```bash
# 1. Drop a fresh ForecastBench snapshot
mkdir -p outputs/forecastbench_snapshots
# Download the latest questions JSON from:
#   https://github.com/forecastingresearch/forecastbench/tree/main/datasets
# Save as e.g. outputs/forecastbench_snapshots/questions_2026-04-23.json

# 2. Set API keys
export OPENROUTER_API_KEY=sk-or-...
export TAVILY_API_KEY=tvly-...          # preferred web search
export SERPER_API_KEY=...                # optional fallback

# Source-specific resolution (only needed for the --resolve step)
export FRED_API_KEY=...
export ACLED_EMAIL=...
export ACLED_KEY=...
# yfinance + dbnomics work without keys

# 3. Install extras
pip install tavily-python yfinance dbnomics scipy pandas
```

## Run

```bash
# 1. Select eligible questions (future resolution, data-anchored sources)
python -m forecast_bench.agent_forecast.run_experiment select --max-n 50

# 2. Run all trials (questions × models × conditions)
python -m forecast_bench.agent_forecast.run_experiment run
# Resumable: re-running skips trials already in trials.jsonl

# ── Wait for resolutions (4-8 weeks depending on question mix) ──

# 3. Resolve ground truth as questions resolve
python -m forecast_bench.agent_forecast.run_experiment resolve

# 4. Score Brier and compare conditions
python -m forecast_bench.agent_forecast.run_experiment score
```

## Outputs

Everything lands in `outputs/agent_forecast/`:

| File | Contents |
|---|---|
| `selected_questions.json` | Selection of eligible questions with metadata |
| `trials.jsonl` | One row per trial (question × model × condition) |
| `resolutions.json` | Ground-truth outcomes keyed by question_id |
| `scored_trials.csv` | Merged trials + outcomes + Brier, ready for R/Python analysis |

## Budgets and tuning

Key knobs in `config.py`:

- `MAX_SEARCH_QUERIES`: total search budget per trial (default 8)
- `TOP_K_FACTORS`: how many high-betweenness factors to target (default 3)
- `QUERIES_PER_FACTOR`: queries per targeted factor (default 3)
- `RESOLUTION_WINDOW_DAYS_*`: when questions must resolve (default 14-56 days)
- `MODELS`: which of the paper's 7 models to include (default 5 stronger ones)

## Integration with the main paper

The Stage 1 DAG elicitation reuses `forecast_bench.prompts_causal` and the
same LLM client. Topology metrics come from `forecast_bench.network_analysis`.
No duplicated code — if the main pipeline changes, this extension inherits
the update.

## What the analysis reports

`run_experiment.py score` produces:

1. Per-condition mean Brier (lower = better) with SEM and n
2. **Primary** paired comparison: `topology_targeted` vs `peripheral_targeted`
   - Mean and median delta (peripheral Brier − topology Brier)
   - Wilcoxon signed-rank test
   - % of pairs where topology wins
3. **Secondary** paired comparison: `topology_targeted` vs `untargeted`
4. **Tertiary** paired comparison: `topology_targeted` vs `no_search`

For a fuller LME with random intercepts for question and model, export
`scored_trials.csv` and run in R:

```r
library(lme4)
library(lmerTest)
d <- read.csv("outputs/agent_forecast/scored_trials.csv")
m <- lmer(brier ~ condition + (1|question_id) + (1|model), data = d)
summary(m)
```

## Caveats

- **Tool-use fragility**: smaller models (Llama 8B, Qwen3 32B) may
  generate malformed search queries. The default model set excludes them;
  opt in with `--models Llama-3.1-8B Qwen3-32B` if needed.
- **Search API coverage**: Tavily and Serper differ in recency and coverage.
  Try both in parallel if results look thin.
- **Resolution coverage**: The resolution skeleton only fills FRED, yfinance,
  dbnomics, and ACLED. Wikipedia is stubbed out — fill in if your selection
  includes Wikipedia questions.
- **Prediction-market questions are excluded** by default (`ELIGIBLE_SOURCES`)
  because the market price itself leaks forecast information as it moves.
