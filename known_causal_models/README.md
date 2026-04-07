# Known Causal Models

LLM-based causal discovery and forecasting using simulation engines with known ground-truth causal structures. This code supports a planned paper on whether LLMs can actively discover causal structure through interventional queries.

## Directory Structure

### `causal_discovery/`
Core causal discovery framework. LLM agents observe simulation output and perform interventional rollouts (clamp-and-react) to recover causal structure. Scoring uses Structural Hamming Distance (SHD) against known ground truth.

**Runners (three variants):**
- `run_pilot.py` — **Full context**: model gets variable list + full conversation history every turn
- `run_pilot_windowed.py` — **Windowed**: model gets variable list + only last N turns as full messages (older turns summarized). Tests whether truncated context improves discipline.
- `run_pilot_open.py` — **Open-ended**: model discovers both variables AND edges (no variable list given). Embedding-based variable alignment for scoring.

**Key difference between full and windowed:**
- Full: all 60+ messages passed every turn. Model has complete history but may lose coherence or become noisy in later steps.
- Windowed: system prompt + observation + last N intervention steps (default N=3). Older interventions appear only in the compact past-intervention summary. Reduces context noise but may cause more duplicate proposals since model can't see detailed earlier results.

**Support files:**
- `prompts.py` — Prompts for closed variants (variable list provided)
- `prompts_open.py` — Prompts for open-ended variant (minimal context)
- `ground_truth.py` — Ground truth adjacency matrices: market (12 vars, 23 edges), conflict (13 vars)
- `intervention.py` — Interventional query system (clamp variable, run engine, observe deltas)
- `explorer.html` — **Causal Discovery Lab**: interactive web app for visualizing results
- `causal_discovery_procedure.{png,pdf}` — Pipeline diagram
- `intervention_types.{png,pdf}` — Intervention type reference
- `intervention_example.{png,pdf}` — Anatomy of a single intervention step (Gemini example)

### `conflict/`
Conflict domain simulation engine. LLM agents role-play as state actors making decisions that affect escalation dynamics.

### `market/`
Market domain simulation engine. LLM agents act as traders submitting orders to a clearing-price mechanism.

### `forecast_multi/`
Multi-agent forecasting framework. Tests whether multiple LLM agents (with different communication structures) can forecast simulation outcomes better than single agents.

**Note:** `llm_client.py` imports from `forecast_bench.llm_client` (the belief sensitivity paper's code).

### `simulation/`
R simulation code that powers the market and conflict engines.

**Note:** R files contain hardcoded `source("src/...")` paths from the original repo layout. To run, create a symlink from repo root: `mklink /D src known_causal_models\simulation`

## Causal Discovery Lab (explorer.html)

Interactive web app for visualizing the causal discovery process. Open in any browser.

**Tabs:**
1. **Causal Graph** — Evolving network: green=correct, red=false positive, orange=missing (highlighted at final step), pink dashed=hallucinated node. Ground truth shown first, then observation, then interventions.
2. **Intervention Effects** — Bar charts of variable deltas per intervention, colored by type.
3. **Simulations** — Preloaded 10 market scenarios (30 periods each) with overlaid time series. Upload a `scenario_*.json` for per-agent detail view (cash, inventory, order flow).

**Data:** Load `pilot_results.json` or `checkpoint.json`. Demo data available.

## Pipeline Design

### Phase 1: Observe
Model sees 10 warmup periods (price, volume, fundamental price) and forms initial graph.
- Closed variants: variable list provided
- Open variant: no variable list, minimal scenario description

### Phase 2: Intervene (× N)
Each step:
1. Model proposes intervention (informed by accumulated graph + past intervention summary)
2. Execute on simulation engine (clamp variable → run 3 periods → observe deltas)
3. Model outputs COMPLETE updated graph (full-graph-per-turn, not incremental)
4. Code replaces accumulated graph with model's response

Interventions are fixed at 3 rollout periods. Duplicates don't consume budget (max 5 consecutive before stopping). Checkpoints saved after each step.

### Phase 3: Declare
Model produces final causal graph with 8000 max_tokens.

### Phase 4: Score
SHD against ground truth adjacency matrix.

## Running

```bash
# Full context (default)
python -m known_causal_models.causal_discovery.run_pilot \
    --domain market --budget 30 --model openai/gpt-oss-120b:nitro

# Windowed context (window=3)
python -m known_causal_models.causal_discovery.run_pilot_windowed \
    --domain market --budget 30 --model deepseek/deepseek-chat-v3-0324:nitro --window 3

# Open-ended (no variable list)
python -m known_causal_models.causal_discovery.run_pilot_open \
    --domain market --budget 30 --model openai/gpt-oss-120b:nitro

# Dry-run (no API calls)
python -m known_causal_models.causal_discovery.run_pilot --dry-run --budget 5
```

## API Key

Scripts look for `OPENROUTER_API_KEY` environment variable, with fallback to `.Renviron` file at repo root.

## Results (as of 2026-04-05)

### Full context — accumulated graph scores

| Model | Steps | Edges | TP | FP | Precision | Recall | F1 |
|-------|-------|-------|----|----|-----------|--------|-----|
| Gemini 3.1 Pro | 30 | 22 | 15 | 7 | 0.682 | 0.652 | 0.667 |
| Qwen 397B | 30 | 16 | 10 | 6 | 0.625 | 0.435 | 0.513 |
| GPT-OSS 120B | 30 | 20 | 11 | 9 | 0.550 | 0.478 | 0.512 |
| GPT-5 Mini | 30 | 17 | 10 | 7 | 0.588 | 0.435 | 0.500 |
| Qwen 3.5 Flash | 20* | 49 | 16 | 33 | 0.327 | 0.696 | 0.444 |
| DeepSeek V3 | 30 | 31 | 3 | 28 | 0.097 | 0.130 | 0.111 |
| GLM-4.7 | 10* | 9 | 4 | 5 | 0.444 | 0.174 | 0.250 |
| Gemma 4 26B | 23* | 5 | 2 | 3 | 0.400 | 0.087 | 0.143 |

*Stopped early: Qwen Flash (API error), GLM (consecutive duplicates + format loss), Gemma (duplicates + JSON failures)

### Windowed context (w=3)

| Model | Steps | Edges | TP | FP | Precision | Recall | F1 |
|-------|-------|-------|----|----|-----------|--------|-----|
| DeepSeek V3 | 14* | 18 | 5 | 13 | 0.278 | 0.217 | 0.244 |

*Stopped on consecutive duplicates — windowed context loses track of past interventions

### GPT-OSS Ablations

| Variant | Accum F1 | Decl F1 | Notes |
|---------|----------|---------|-------|
| Soft pruning (main) | 0.512 | 0.508 | 1 edge pruned |
| No pruning prompt | 0.524 | 0.500 | 0 edges pruned |
| Hard pruning | — | 0.509 | 22 edges pruned, oscillating graph |
| 6-period rollouts | 0.444 | — | More pruning (4), but more indirect FPs |

### Key Findings

1. **Models plateau at ~10-15 interventions** — graph stops growing, duplicates increase
2. **Direct vs indirect confusion** — core failure mode across all models. Models add X→Y when they see Y change after intervening on X, even if mediated through Z
3. **No spontaneous pruning** — without prompting, models never remove edges. With prompting, they either ignore it (soft) or over-prune (hard)
4. **Exploration deficit** — models stop exploring once comfortable, never probing gaps in their graph
5. **Context degradation** — smaller models lose JSON compliance or semantic discipline in long conversations
6. **Declaration vs accumulation** — some models (DeepSeek) are noisy turn-by-turn but disciplined in final declaration; others (Gemini) are consistent throughout

### Model Compliance Issues

| Model | JSON Failures | Format Loss | Duplicates | Notes |
|-------|--------------|-------------|------------|-------|
| Gemini 3.1 Pro | 0 | None | 12 | Clean throughout |
| Qwen 397B | 0 | None | 2 | Clean throughout |
| GPT-OSS | 0 | 3 role confusions | 5 | Occasional proposal-as-update |
| GPT-5 Mini | 0 | None | 0 | Declaration API crash |
| DeepSeek V3 | 0 | None | 0 | Noisy accumulated graph |
| Qwen 3.5 Flash | 0 | None | — | API crash at step 20 |
| GLM-4.7 | 0 | Steps 8-10 empty | 5+ | Lost coherence late |
| Gemma 4 26B | 8 | N/A | 5+ | Can't produce valid JSON |

## Output Structure

```
outputs/causal_discovery/single_agent/
├── full/                          # Full conversation context
│   ├── gptoss/                    # GPT-OSS main run (soft pruning)
│   ├── gptoss_ablations/          # Prompt/rollout variants
│   │   ├── no_pruning/
│   │   ├── hard_pruning/
│   │   ├── soft_pruning/
│   │   └── 6periods/
│   ├── qwen397b/
│   ├── gemini31pro/
│   ├── gpt5mini/
│   ├── deepseek/
│   ├── qwen35flash/
│   ├── glm47/
│   └── gemma26b/
├── windowed/                      # Windowed conversation context
│   └── deepseek/                  # DeepSeek w=3
├── open_ended/                    # Open-ended (variable discovery)
├── archive_old_pipeline/          # Pre-fix results (broken accumulation)
└── archive_prompt_variants/       # GLM seed variants, dry-run tests
```

## To Do

### Data collection
- [ ] Complete GPT-OSS 6-period run (29/30, out of credits)
- [ ] More models with windowed approach (compare w=3 vs w=5)
- [ ] Multiple seeds per model for confidence intervals
- [ ] Open-ended variant with real models
- [ ] Conflict domain runs with updated pipeline

### Baselines
- [ ] **Random intervention baseline**: random type, target, value. Same budget + graph update. Tests whether LLM intervention choices add value.
- [ ] **Information-theoretic baseline**: pick intervention maximizing expected information gain. Upper bound for intervention selection quality.

### Analysis
- [ ] PC algorithm / GES baseline on observational data only
- [ ] Learning curves: F1/SHD as function of intervention budget
- [ ] Error analysis: which edge types are hardest (feedback loops, indirect effects, common causes)?
- [ ] Conversation truncation study: systematic comparison of window sizes

## Simulation Data

10 market + 10 conflict scenarios in `outputs/simulations/`. Each has 30 periods with per-period agent states, orders, clearing prices. The causal discovery warmup uses a fresh simulation (seed-based), not these stored scenarios.
