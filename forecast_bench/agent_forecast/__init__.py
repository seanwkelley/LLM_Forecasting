"""DAG-guided agentic forecasting pipeline (paper extension).

Tests whether topology-targeted evidence gathering improves forecast accuracy
(Brier score) beyond a decomposition-only control (peripheral_targeted),
free-form untargeted search, and a no-search baseline, on quantitative
ForecastBench questions with future resolution dates.

The primary contrast is topology_targeted vs peripheral_targeted, which
isolates the centrality effect from the benefit of decomposing search into
factor-scoped queries.
"""
