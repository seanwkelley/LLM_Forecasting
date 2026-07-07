# Known Causal Models

LLM-based causal discovery and forecasting using simulation engines with known ground-truth causal structures. This code supports a planned paper on whether LLMs can actively discover causal structure through interventional queries.

See `docs/` for the current causal discovery design (`CAUSAL_DISCOVERY_DESIGN.md`, motivation/methods, related work, and the testbed/sandbox design recommendations). Material from the original simulation/PID project — the research log, the original writeups, and the retired code — lives in `docs/archive/` and `archive/`.

## Directory Structure

### `causal_discovery/`
Core causal discovery framework. LLM agents observe simulation output and perform interventional rollouts (clamp-and-react) to recover causal structure. Scoring uses Structural Hamming Distance (SHD) against known ground truth.

**Runners (five variants):**
- `run_pilot.py` — **Transcript (full context)**: variable list given + full conversation history re-sent every turn. Context grows unboundedly. `--domain market|conflict`.
- `run_pilot_statebased.py` — **State-based (constant context)**: variable list given, but each LLM call is a fresh `[system, prompt]` — the only carried memory is the hypothesized graph + a compact evidence ledger (raw observed associations, no transcript). Prompt size stays flat. Logs `context_trace` (per-call prompt size). `--domain market|conflict`. The counterpart to transcript for testing whether the discovery plateau is a reasoning ceiling vs a context-length artifact.
- `run_pilot_windowed.py` — **Windowed**: full messages for only the last N turns; older turns summarized.
- `run_pilot_seeded.py` — **Seeded (market)**: a few KNOWN variables given (observable outputs + controllable knobs); the model must HYPOTHESIZE the unobserved mediators (`agent_orders`, `inventory`, `cash`), which are stripped from both the observation channel (`OBSERVABLE_VARS_MARKET`) and the intervention menu. Scored against the full GT with variable recall split into seed (anchored) vs hidden (the real metric). The middle rung between closed and open.
- `run_pilot_open.py` — **Open-ended**: model discovers both variables AND edges (no variable list). Embedding-based variable alignment for scoring.

**Difficulty ladder:** closed/transcript (all vars given) → seeded (a few vars) → open (no vars). The first tests *structure learning*; the last two test *hypothesis generation* of latent factors.

**Memory architectures (transcript vs state-based):** Transcript passes all 60+ messages every turn — complete history, but context balloons (can saturate the model's window) and weak models depend on it. State-based keeps a flat compact summary. Finding: for capable models the two give equal F1 (state-based ~25× cheaper); for weak models state-based degrades exploration (see Current Status).

**Support files:**
- `prompts.py` — Prompts for closed variants (variable list provided)
- `prompts_open.py` — Prompts for open-ended variant (minimal context)
- `ground_truth.py` — Ground truth adjacency matrices: market (13 vars, 24 edges; `production_capacity` promoted to a node 2026-06-14), conflict (13 vars, 26 edges; audited 2026-06-23 — verified clean, every edge maps to an engine mechanism)
- `intervention.py` — Interventional query system (clamp variable, run engine, observe deltas)
- `explorer.html` — **Causal Discovery Lab**: interactive web app for visualizing results
- `causal_discovery_procedure.{png,pdf}` — Pipeline diagram
- `intervention_types.{png,pdf}` — Intervention type reference
- `intervention_example.{png,pdf}` — Anatomy of a single intervention step (Gemini example)

**Conditions & analyses (added 2026-06-25):**
- `run_held_out_prediction.py` — **Held-out interventional prediction**: after discovery, the model predicts the *sign of change* for a battery of held-out interventions (built on a fresh scenario seed) under three conditions — its **discovered** graph, the **ground-truth** graph (ceiling), and **no graph** (floor) — so any accuracy difference isolates the marginal value of structure. Scores directional accuracy (overall + movement-only); flags `novel` (never-probed) targets. Tests *propagation*, the behavioral counterpart to edge recovery. Market + conflict. *Finding so far: the graph (even the correct one) barely helps → propagation, not discovery, is the bottleneck.*
- `run_adjudication.py` — **Model adjudication** (market): the model is handed two competing causal models that differ on one contested mechanism (mediation / confound / reversal / shadowed / direct) and must design interventions to decide which is correct. Truth derived from the GT matrix (balanced A/B). Scores verdict accuracy (overall + per contrast) + diagnostics (did it run a controlled experiment? probe the key variables? is its confidence calibrated?). `--no-compound` toggles the controlled-experiment affordance — a direct test of how much performance leans on prescriptive scaffolding.
- `analyze_shd_attribution.py` — **SHD attribution** (post-hoc, no API): decomposes a discovery run's SHD trajectory — per-step ΔSHD tied to the chosen probe ("intervention informativeness"), per-edge add/remove contributions, per-GT-edge resolution step, plateau quantification (% of total SHD reduction achieved by step k), and the wasted-intervention fraction. Runs on any `pilot_results.json`. `--batch`, `--plot`.

**Compound (controlled) interventions:** `run_pilot --flexible` (market only) lets the model apply up to **two simultaneous clamps** in one intervention — the clean way to separate a direct edge from a mediated one (pin the mediator while perturbing the cause). Opt-in; single-lever remains the default so existing runs stay comparable. Implemented in `intervention.py` (`type="compound"`, max 2 clamps). *Note: market trait clamps pin parameters (production_cost, demand, capacity) but not endogenous state levels (cash/inventory/clearing_price), which the engine recomputes each period.*

### `scm/` — Synthetic SCM testbed (added 2026-06-25)
Random structural causal models over **abstract** variables `X1..Xn` — the clean, prior-free complement to the market/conflict engines. Variable names carry no meaning, so the only path to the graph is the interventional data; ground truth is the generating DAG itself (exact, not inferred from code); and size/density/functional-form/noise are knobs, so you get sweeps and free replication.
- `scm/engine.py` — random DAG + linear/nonlinear structural equations, i.i.d. sampling, multi-node `do()` interventions (any subset of nodes — a controlled experiment holds the others fixed), observational summary (means/SDs/correlations).
- `causal_discovery/run_pilot_scm.py` — the observe→intervene→declare→score loop on an SCM; scored on **directed AND skeleton** F1/SHD; runs all baselines inline so each LLM result is stored next to its references. `--max-clamps` (default `0` = auto = `n_nodes-1`) sets how many variables the agent may clamp at once — by default the **full-control affordance `oracle_controlled` uses**, so the agent *can* run a fully-controlled experiment whenever it chooses. Each run records `clamp_usage` (how many k-clamp interventions it actually issued), so a `--max-clamps` sweep reads "raise the cap → do they use it?" — the capability-vs-propensity signal — straight from the results. `--prompt-mode {neutral,describe,prescribe}` (default `describe`) is the **scaffolding knob for the capability-vs-propensity experiment**: `neutral` makes the multi-clamp affordance visible but withholds the controlled-experiment technique (measures *propensity* — do they invent control unprompted?), `describe` explains it (default), `prescribe` mandates it before asserting any edge (measures the *capability* ceiling). The neutral prompt is deliberately scrubbed of the technique in **both** the system and intervention prompts — that scrub is what makes the propensity number valid.
- `causal_discovery/scm_baselines.py` — `oracle_controlled` (clamp-all-others → recovers the true DAG; upper bound), `naive_single` (single-`do` → over-asserts transitive shortcuts; the LLM failure mode as an algorithm), and observational **PC**/**GES** (via `causal-learn`). Also exposes `transitive_fp_analysis`: of all mediated-only `(A,C)` pairs (`A⇝C` exists, `A→C` does not), what fraction did a method assert as direct edges? This `transitive_fp_rate` is the **mechanism DV** — `naive_single ≈ 1.0`, `oracle_controlled = 0.0` by construction, so the LLM's rate reads directly against those anchors. Recorded for the LLM (declared + working) and both interventional baselines in every `scm_results.json`. Note: sparse graphs can have **zero** traps (no signal) — pre-screen seeds for `n_transitive_traps`.

**Baseline reference (n=8, edge_prob 0.3, linear, 3 seeds):** `oracle_controlled` directed-F1 **1.00** (controlled experiments fully recover the DAG — the data contains the answer), `naive_single` **0.92** (over-asserts; precision drops), PC/GES skeleton-F1 **1.00** but directed-F1 **0.73** (observational orientation ceiling). The `oracle − naive` gap *is* the value of controlled experiments.

### `knowable_worlds/` — LLM forecasts against knowable probabilities (paper 3)
Self-contained study (renamed from `calibration/`, 2026-07-06): LLM forecasts scored against *exactly computable* event probabilities in built linear-Gaussian worlds, static and dynamic (regime-shift) arms plus a hidden-confounder arm. Core question: does predictive updating couple to causal-structural updating when the regime shifts? Docs, code, figures, and outputs all live inside the folder — see `knowable_worlds/README.md` and `knowable_worlds/docs/KNOWABLE_WORLDS_DESIGN.md`. Depends on the shared `scm/engine.py` and `forecast_bench/llm_client.py`.

### `conflict/`
Conflict domain simulation engine. LLM agents role-play as state actors making decisions that affect escalation dynamics.

### `market/`
Market domain simulation engine. LLM agents act as traders submitting orders to a clearing-price mechanism.

### `archive/`
Code and docs from the original simulation/forecasting project (2026 Q1), predating the causal discovery paper: `forecast_multi/` (multi-agent forecasting framework) and `simulation/` (the original R engines, superseded by the Python `market/` and `conflict/` engines). Nothing here is imported by current code — see `archive/README.md`.

## Causal Discovery Lab (explorer.html)

Interactive web app for visualizing the causal discovery process. Open in any browser.

**Tabs:**
1. **Causal Graph** — Evolving network: green=correct, red=false positive, orange=missing (highlighted at final step), pink dashed=hallucinated node. Ground truth shown first, then observation, then interventions. **Domain-aware** (added 2026-06-23): scores against the market (24-edge) or conflict (26-edge) GT based on `data.config.domain`.
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

Interventions default to 3 rollout periods (**configurable via `--rollout-periods`** — longer rollouts surface slow/feedback effects but also more indirect cascade, which can be mis-read as direct edges). With `--flexible` (market), a single intervention may be a **compound** of up to two simultaneous clamps (a controlled experiment). Duplicates don't consume budget; the intervention phase stops after N consecutive duplicate/invalid proposals (**configurable via `--max-duplicates`, default 5**). Checkpoints saved after each step.

### Phase 3: Declare
Model re-synthesises a final causal graph from the accumulated evidence (8000 max_tokens). For **reasoning models** (e.g. GLM 5.x) reasoning is disabled on this call (`reasoning_enabled=False`): otherwise the hidden reasoning trace exhausts the token budget and content comes back empty. Declaration is mechanical formatting — the actual reasoning happened during the interventions. (If an endpoint *requires* reasoning — e.g. gpt-oss `:nitro` rejects a disabled trace with a `400 "Reasoning is mandatory"` — `call_llm` automatically drops the disable flag and retries with reasoning on.)

### Phase 4: Score
SHD + precision/recall/F1 against the ground-truth adjacency matrix. Both the **declared** graph and the **working** graph (the accumulated hypothesis before the declaration call) are scored and reported (`working_f1`, etc.) — a large declared-vs-working gap means the declaration step is doing work orthogonal to discovery quality.

## Running

```bash
# Transcript / full context (default)
python -m known_causal_models.causal_discovery.run_pilot \
    --domain market --budget 30 --model openai/gpt-oss-120b:nitro

# State-based / constant context (market or conflict)
python -m known_causal_models.causal_discovery.run_pilot_statebased \
    --domain market --budget 30 --model openai/gpt-oss-120b:nitro

# Seeded (hypothesise unobserved mediators; market only)
python -m known_causal_models.causal_discovery.run_pilot_seeded \
    --budget 30 --model openai/gpt-oss-120b:nitro

# Open-ended (no variable list)
python -m known_causal_models.causal_discovery.run_pilot_open \
    --domain market --budget 30 --model openai/gpt-oss-120b:nitro

# Relax the duplicate-stop (e.g. for weak models that need more attempts)
python -m known_causal_models.causal_discovery.run_pilot \
    --domain market --budget 30 --model <m> --max-duplicates 10

# State-vs-transcript orchestrator (both conditions × seeds, writes summary.json)
python -m known_causal_models.causal_discovery.run_market_state_vs_transcript \
    --seeds 42 43 44 --model openai/gpt-oss-120b:nitro

# Compound (controlled) experiments available + longer rollout (market)
python -m known_causal_models.causal_discovery.run_pilot \
    --domain market --budget 30 --model <m> --flexible --rollout-periods 6

# Held-out interventional prediction (discovered vs ground-truth vs no-graph)
python -m known_causal_models.causal_discovery.run_held_out_prediction \
    --domain market --model <m> \
    --graph-source outputs/causal_discovery/single_agent/full/gptoss/pilot_results.json

# Model adjudication (with vs without the controlled-experiment affordance)
python -m known_causal_models.causal_discovery.run_adjudication --model <m>
python -m known_causal_models.causal_discovery.run_adjudication --model <m> --no-compound

# SHD attribution on an existing run (post-hoc, no API)
python -m known_causal_models.causal_discovery.analyze_shd_attribution \
    --input outputs/causal_discovery/single_agent/full/gptoss --plot

# Synthetic SCM — algorithmic baselines only (no API)
python -m known_causal_models.causal_discovery.scm_baselines \
    --n-nodes 8 --edge-prob 0.3 --seeds 0 1 2

# Synthetic SCM — LLM discovery (abstract variables; baselines computed inline)
# Default --max-clamps is auto (n_nodes-1): the agent may run a fully-controlled experiment.
python -m known_causal_models.causal_discovery.run_pilot_scm \
    --model <m> --n-nodes 8 --edge-prob 0.3 --seed 0 --budget 20

# Capability-vs-propensity sweep: vary the clamp cap, read clamp_usage from each result
for k in 1 2 4 7; do
  python -m known_causal_models.causal_discovery.run_pilot_scm \
      --model <m> --n-nodes 8 --seed 0 --budget 20 --max-clamps $k \
      --output-dir outputs/causal_discovery/scm/sweep_k$k
done

# C2 core: the propensity gap = prescribe - neutral (paired across the SAME seeds).
# floor (no control) anchors to naive_single; oracle_controlled (inline) is the ceiling.
for seed in 0 1 2 3 4 5 6 7; do
  python -m known_causal_models.causal_discovery.run_pilot_scm --model <m> \
      --n-nodes 8 --edge-prob 0.4 --seed $seed --budget 20 --max-clamps 1 --prompt-mode neutral   # floor
  python -m known_causal_models.causal_discovery.run_pilot_scm --model <m> \
      --n-nodes 8 --edge-prob 0.4 --seed $seed --budget 20 --prompt-mode neutral                   # propensity
  python -m known_causal_models.causal_discovery.run_pilot_scm --model <m> \
      --n-nodes 8 --edge-prob 0.4 --seed $seed --budget 20 --prompt-mode prescribe                 # capability
done

# Dry-run (no API calls)
python -m known_causal_models.causal_discovery.run_pilot --dry-run --budget 5
```

## API Key

Scripts look for `OPENROUTER_API_KEY` environment variable, with fallback to `.Renviron` file at repo root.

## Results

> **⚠️ The 2026-04-05 tables below are PRE-AUDIT** (old rule-agent code, 23-edge market GT). They are **not directly comparable** to post-2026-06-14 runs (24-edge GT) or post-2026-06-23 runs (fixed prompts, configurable duplicate-stop, GLM reasoning fix). See *Current Status* for the current results.

### Current Status (2026-06-23)

**Memory architecture (state-vs-transcript), market, budget 30, seeds 42/43/44:**

| Model | Transcript F1 | State-based F1 | Note |
|-------|---------------|----------------|------|
| GPT-OSS 120B | 0.487 | 0.483 | state ≈ transcript → plateau is a **reasoning ceiling**, not context length (transcript saturated the 131k window; state-based ~5k tokens, ~25× cheaper) |
| Qwen 2.5 7B | 0.257 | 0.142* | state-based collapses; weak model leans on the full transcript |

*Qwen state-based was 0.076 before the prompt fixes (it stalled at 1 intervention via a duplicate-loop). The fixes — structured `ALREADY TRIED` list, neutralised menu-example bait, carried duplicate-feedback — lifted it to 0.142 (2–3 interventions), but still far below transcript: **part fixable presentation gap, part genuine 7B limit**. GLM 5.1 sweep abandoned (impractically slow + would need re-running on the fixed prompts).

**Robustness controls added (2026-06-23):** working-graph F1 reported alongside declared F1 (declaration is a confound); `--max-duplicates` exposes the previously hard-coded stop. Conflict domain audited (GT clean; faction-state clamp no-op fixed so all 26 edges are interventionally identifiable). See `memory/project_conflict_domain_audit_2026_06_23.md`.

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

*Rollout length re-tested on the current pipeline (2026-06-25, GPT-OSS, seed 42, `--rollout-periods 6`): declared F1 **0.476** vs **0.492** at 3 periods — no gain, slight dip (recall 0.625 vs 0.667; precision/SHD ~unchanged). Longer observation of each effect did not surface more recoverable structure here. N=1 — within run-to-run noise; needs replicates.*

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
- [x] Multiple seeds (GPT-OSS, Qwen done at 3 seeds for state-vs-transcript)
- [x] Conflict domain audited (GT clean, clamp fix) — runs with the fixed pipeline still pending
- [ ] **Re-run all models on the fixed prompts** (the cross-model rankings were partly prompt-fragility artifacts — GLM declaration starvation, Qwen duplicate-loop). Treat the prompt as a controlled, reported variable.
- [ ] Seeded variant with real models (expect low hidden-var recall — that's the result)
- [ ] Open-ended variant with real models
- [ ] More scenarios per condition (currently 1 scenario/run, so "seed" conflates scenario difficulty with model ability)

### Baselines
- [ ] **Random intervention baseline**: random type, target, value. Same budget + graph update. Tests whether LLM intervention choices add value.
- [ ] **Information-theoretic baseline**: pick intervention maximizing expected information gain. Upper bound for intervention selection quality.

### Analysis
- [ ] PC algorithm / GES baseline on observational data only
- [ ] Learning curves: F1/SHD as function of intervention budget
- [ ] Error analysis: which edge types are hardest (feedback loops, indirect effects, common causes)?
- [ ] Conversation truncation study: systematic comparison of window sizes
- [ ] **Declaration-vs-working-graph gap** across models (now reported as `working_f1`) — quantify how much the declaration step swings F1
- [ ] **Duplicate-stop sensitivity** (now `--max-duplicates`) — does relaxing it recover weak-model exploration?

## Simulation Data

10 market + 10 conflict scenarios in `outputs/simulations/`. Each has 30 periods with per-period agent states, orders, clearing prices. The causal discovery warmup uses a fresh simulation (seed-based), not these stored scenarios.
