# Archive

Code from the original simulation/forecasting project (2026 Q1) that predates
the causal discovery paper. Kept for the record; nothing here is imported by
current code.

- `forecast_multi/` — multi-agent forecasting framework (independent /
  debate / specialization conditions over the simulation engines). The
  writeups it produced are in `../docs/archive/RESULTS_FORECASTING_AND_PID.md`.
- `simulation/` — the original R simulation engines. Superseded by the
  Python engines in `../market/` and `../conflict/`. The R files carry
  hardcoded `source("src/...")` paths from the original repo layout.

Old documentation lives in `../docs/archive/`:
- `EXPERIMENT_NOTES.md` — the historical research log
- `MARKET_EXPERIMENT.md`, `RESULTS_FORECASTING_AND_PID.md` — original
  simulation/PID writeups
- `MOTIVATION.md` — the original umbrella motivation ("three domains of LLM
  forecasting reliability"), superseded by the per-paper motivation docs
