# Knowable Worlds

Paper 3 of the arc (belief sensitivity → structure discovery → **forecasting under a changing causal structure**). LLM forecasts are scored against *exactly knowable* probabilities: we build worlds (linear-Gaussian SCMs) where both the true event probability and the true causal structure are known before and after a change we set, so predictive updating and causal-structural updating can be measured separately, per item, against optimal. Core question: when the causal structure generating a series changes, does the model update its forecasts *and* its stated causal structure, or does prediction adapt while causal understanding stays frozen?

Renamed from `calibration/` (2026-07-06); docs were previously named `TRUE_CALIBRATION_*.md`.

## Documentation (`docs/`)

- `KNOWABLE_WORLDS_DESIGN.md` — full study design (section numbers cited throughout the code)
- `KNOWABLE_WORLDS_MOTIVATION_RELATED_WORK.md` — motivation + related-work sweep
- `KNOWABLE_WORLDS_NEXT_STEPS.md` — single pickup point, grouped by blocker

## Arms

### Static arm — information ladder (design §§5–7)
Does more mechanism knowledge move stated probabilities toward exact ones?

- `analytic.py` — exact event probabilities for linear-Gaussian SCMs (§5)
- `battery.py` — event battery generator; full calibration-curve coverage by construction (§5)
- `prompts.py` — elicitation prompts per information rung (§6); deliberately neutral
- `run_calibration.py` — runner, direct mode (§§5–7)
- `analyze_calibration.py` — dedupe + descriptives; writes `master_long.csv` for the R layer
- `analyze_calibration.R` — inference layer
- `gen_calibration_plot.py` — stated p vs exact p* scatter per rung (the defining figure)
- `gen_noise_sensitivity.py` — RQ4: does confidence track how random the world actually is?

### Dynamic arm — regime shift (design §15, addenda §16)
A lag-1 linear-Gaussian dynamic SCM whose structure changes mid-series.

- `dyn_engine.py` — dynamic SCM engine + change types (edge add/remove, sign flip, weight double)
- `dyn_battery.py` — item battery + checkpoints
- `dyn_prompts.py` — neutral prompts for the dynamic arm
- `run_dynamic.py` — runner (forecast + structure items, info-level and carry-belief knobs)
- `run_single_edge.py` — the structure question: `--mode tracking` asks two probabilities (present + positive-if-present) about the changed edge and matched control edges at every checkpoint, all four change types (§16.2 add.3); `--mode formation` is the one-snapshot diagnostic, retiring after the queued Qwen run
- `analyze_dynamic.py` / `analyze_dynamic.R` — analysis + inference
- `analyze_tracking.py` — changed-edge tracking analysis: per-scenario difference-in-differences, weight-double admission check, `track_master.csv` for R
- `analyze_v2.py` — committed descriptives for the v2 runs (§16 addenda)
- `gen_dynamic_figures.py` — recovery-curve figure (3 panels)
- `gen_network_evolution.py` — how the stated network evolves across checkpoints

### Hidden-confounder arm (design §16.3)
A confounded dynamic world: observational and interventional answers diverge.

- `dyn_confounder.py` — confounded dynamic SCM
- `confounder_battery.py` — checkpoint battery
- `confounder_prompts.py` — neutral prompts (the confounder is never named)
- `run_confounder.py` — runner
- `analyze_confounder.py` — causal-reads analysis
- `analyze_confounder.R` — inference layer (see/do divergence, set-X1 vs set-X3 contrasts)

## Explorers

- `explorer.html` — interactive study design (restructured 2026-07-06): the dynamic world, structure questions asked about specific edges, multi-edge (k ∈ {1,3,6}) and hidden-confounder extensions with live demos, controls table, results, run queue. The static arm was removed from the page and lives in `docs/KNOWABLE_WORLDS_DESIGN.md` §§5–14.
- `explorer_news.html` — news-shock variant (§15.2) — registered, PARKED, not yet run

## Figures

- `gen_design_diagram.py` — study-design figure → `knowable_worlds_design.{png,pdf}`
- `gen_single_edge_figures.py` — formation discrimination, pooled tracking trajectories, three-model perseverance → `outputs/single_edge/*.png`
- `gen_slides.py` — academic motivation/methods deck → `slides/knowable_worlds_motivation_methods.pptx` (14 slides, 16:9; its two figures are generated from the real study worlds, seed 300)

## Outputs (`outputs/`)

One directory per run: `pilot_gptoss`, `noise_gptoss`, `scaleup_gptoss` (static arm); `dynamic_gptoss*`, `dynamic_qwen_thinking`, `dynamic_llama` (dynamic arm variants); `single_edge` (formation + `*_track_*` tracking files, per model).

## Running

From `known_causal_models/`:

```
python -m knowable_worlds.run_calibration --model gpt-oss ...
python -m knowable_worlds.run_dynamic --model gpt-oss ...
```

Each script's docstring carries exact invocations. Shared code lives outside this folder by design: `forecast_bench/llm_client.py` (LLM client), `forecast_bench/run_sensitivity.py` (`MODEL_MAP`), and `scm/engine.py` (static SCM engine) — the scripts add the repo root and `known_causal_models/` to `sys.path` themselves.
