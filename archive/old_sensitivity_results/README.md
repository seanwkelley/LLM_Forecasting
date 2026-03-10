# Archived Sensitivity Results

Moved here 2026-03-09. These are superseded by the causal-only pipeline.

## flat_reasons_forecasting/
Old flat-reasons pipeline results (one_turn + multi_turn). The flat-reasons mode
was removed entirely — we now only use causal network mode. Code deleted from
`forecast_bench/prompts.py` and `forecast_bench/analysis.py`.

## 70b_multi_turn/
Multi-turn condition results for Llama 70B. Dropped from the paper because
multi-turn probing has order effects and non-independence between probes,
making it a confounded comparison. We use one-turn (independent) probing only.
