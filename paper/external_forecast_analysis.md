# External Forecasting Analysis

A follow-on experiment that asks whether the structural faithfulness documented in the main paper translates into better predictive accuracy when the elicited causal topology is used to guide evidence gathering.

## Motivation

The main paper establishes that LLM forecasters update internally consistently with their own elicited causal DAGs. Central factors move the probability more than peripheral ones, the pattern holds across models, and it survives ablation, rewiring, and persuasiveness controls. Those results speak to coherence, not correctness. A natural next question is whether the same topology that governs how a model revises its beliefs can be used to improve what it revises toward. If high-betweenness factors are the elements the model weights most heavily in its own reasoning, then directing an evidence-gathering agent to those factors should produce more useful updates than free-form retrieval of the same size.

## Research question

Does topology-targeted evidence retrieval, guided by the high-betweenness factors of a model's own elicited DAG, yield better-calibrated forecasts than equal-budget untargeted retrieval on the same questions, and does the benefit come from the topological centrality of the targeted factors rather than from the act of decomposing the search?

We operationalize the question as a Brier-scored comparison across four conditions on future-resolving ForecastBench questions, paired within question and model so each question-model observation contributes a matched quadruple.

## Design

Each question is forecast under four conditions, all starting from the same Stage 1 DAG and initial probability $p_0$ produced by the main pipeline.

The `no_search` condition produces no evidence and sets $p_1 = p_0$. It anchors accuracy of the pure elicited forecast and serves as a reference point for how much any retrieval helps.

The `untargeted` condition allows the model to author free-form web-search queries against the question, up to a budget of eight queries with five results each, and then integrate the returned snippets to produce $p_1$.

The `topology_targeted` condition uses the same total budget but partitions it across the top-three factors ranked by betweenness centrality in the model's own DAG. The query-generation prompt is identical except that each query is conditioned on a specific target factor.

The `peripheral_targeted` condition mirrors `topology_targeted` exactly but targets the three lowest-betweenness factor nodes instead of the three highest. Budget, prompt structure, number of factors targeted, queries per factor, search provider, and integration prompt are all held equal. The only difference between the two targeted conditions is whether the selected factors are structurally central or peripheral within the model's own DAG.

This four-arm design isolates the centrality effect from a potential decomposition confound. Free-form queries authored under `untargeted` tend to be paraphrases of the main question and return overlapping snippets; any factor-scoped decomposition breaks that redundancy and may win for that reason alone, regardless of which factors are targeted. The `peripheral_targeted` arm decomposes the search identically to `topology_targeted`, so if topology beats peripheral, the centrality signal is doing real work. If the two targeted conditions tie while both beat untargeted, decomposition rather than centrality was the operative mechanism.

### Primary and secondary contrasts

The primary statistical comparison is `topology_targeted` versus `peripheral_targeted`, paired within (question, model). This isolates the centrality effect from decomposition. The secondary contrast is `topology_targeted` versus `untargeted`, which tests the combined benefit of decomposition plus centrality. The `no_search` baseline is reported for context.

## Question selection

We draw from the rolling ForecastBench question sets published on the forecasting-research GitHub. Questions are restricted to the eligible sources yfinance, dbnomics, fred, acled, and wikipedia. Prediction-market sources (Metaculus, Polymarket, Manifold, INFER) are excluded because their freeze-time market prices leak the consensus forecast.

The resolution window is widened to seven to ninety days so that fast-resolving sources (yfinance, daily FRED series, Wikipedia) contribute early results while slower sources (monthly FRED macro series, ACLED aggregations) catch up later. Stratified sampling holds counts roughly balanced across sources. The default selection is approximately 500 question instances, a ~2x oversample over the minimum needed for power.

### Tiered resolution strategy

Because resolution speed varies across sources, we plan the experiment as a rolling release with three milestones.

The **Week-2 preliminary** milestone captures same-day and next-day resolutions. yfinance stock questions resolve within hours of market close on the resolution date, daily FRED series (treasury yields, federal funds rate, credit spreads) within one to two business days, Wikipedia questions on the resolution date itself, and daily dbnomics indicators same-day. This milestone should yield a few dozen to one hundred resolved trials per model, enough for a directional signal and a first look at effect direction but underpowered for a definitive test.

The **Week-4 interim** milestone adds ACLED weekly conflict counts, FRED weekly series (initial jobless claims, money supply), and short-horizon dbnomics indicators. Expected cumulative coverage is roughly one hundred to two hundred resolved pairs per model, sufficient for an interim test that is suggestive but not publication-grade. This milestone also serves as a quality check on the pipeline before the final release.

The **Week-8-to-12 final** milestone adds monthly FRED macro series (CPI, unemployment, non-farm payrolls) once their 4-6 week publication lag has cleared. Target final coverage is at least two hundred resolved pairs per model, comfortably powered for the primary and secondary contrasts.

The `resolve` step is idempotent and can be re-run at each milestone without overwriting earlier results. ForecastBench's nightly resolution sets mean re-running costs nothing beyond the minute it takes to pull the latest JSON.

## Models

Five of the seven models from the main paper: Llama 3.3 70B, DeepSeek V3, Qwen3 235B, GPT-OSS 120B, and Gemini 2.5 Flash Lite. The smaller models (Llama 3.1 8B, Qwen3 32B) are excluded by default because agentic tool-use is unreliable at their scale; query generation produces malformed output often enough to contaminate the budget-equalized comparison. They can be opted in if needed, though results should be treated separately.

## Pipeline

Stage 1 elicits the same DAG and $p_0$ used in the main paper, via the same prompt and validation. Stage 2 applies network analysis to rank factors by betweenness and selects both the top three (for `topology_targeted`) and the bottom three (for `peripheral_targeted`). Stage 3 gathers evidence under the condition-specific policy, producing a list of query-result pairs. Stage 4 presents the original question, $p_0$, the DAG's factor list, and the gathered evidence to the model with a standardized integration prompt that returns an updated probability $p_1$ and two to four sentences of reasoning.

Web search uses Tavily as the primary provider with Serper as a fallback; snippet length is capped so that both providers return comparable evidence density.

## Ground truth

Resolutions come from ForecastBench's own nightly resolution sets, matched on `(question_id, resolution_date)`. This avoids per-source API integration and guarantees consistency with how the benchmark itself resolves its questions. The resolve step is idempotent and is executed at each milestone.

## Scoring and analysis

Brier score $(p_1 - y)^2$ is computed per trial. The primary test is the paired delta $B_{\text{peripheral}} - B_{\text{topology}}$ within each (question, model) pair, evaluated with Wilcoxon signed-rank. A positive mean delta indicates centrality is load-bearing beyond decomposition. The secondary test is the paired delta $B_{\text{untargeted}} - B_{\text{topology}}$, interpreted as the combined effect of decomposition and centrality.

Supplementary reporting includes per-condition mean Brier with standard error, the fraction of pairs where topology wins each pairwise contrast, and an LME with condition as a four-level fixed effect and crossed random intercepts for question and model. The LME is fit in R via `lme4`, matching the main paper's analytic conventions.

Power is governed by the number of resolved pairs, not the number of trials, since unresolved or same-outcome questions contribute no signal to the paired test. Target coverage is at least two hundred resolved pairs per model at the final milestone.

## Pre-registration notes

Several design choices are committed before scoring begins. The primary contrast is fixed as `topology_targeted` versus `peripheral_targeted`, paired within question and model, with Wilcoxon as the primary test and a two-sided significance threshold of $\alpha = .05$. The secondary contrast is `topology_targeted` versus `untargeted`. Search budgets, top-k and bottom-k values, queries-per-factor, model set, eligible sources, and the resolution window are set in `config.py` and will not be re-tuned after outcomes are known. Interim results at the Week-2 and Week-4 milestones are labeled exploratory and are reported but not used to justify design changes. Trials that fail at any stage (malformed DAG, empty search results, integration parse error) are excluded from the paired comparison and reported separately.

To guard against search-provider confounds, we will report the distribution of snippet counts, snippet length, and recency per condition at the final milestone. If these differ systematically between `topology_targeted` and `peripheral_targeted`, we will include them as covariates in a sensitivity LME and report whether the primary contrast survives that adjustment.

## What each outcome would show

If `topology_targeted` reliably beats `peripheral_targeted`, the centrality signal transfers from coherence to accuracy. The same DAG topology that governs how a model revises its beliefs under probing also identifies the factors where new evidence most improves calibration. This is the strongest possible extension of the main paper's claim and gives forecasting systems a concrete handle on where agentic search effort should be spent.

If `topology_targeted` and `peripheral_targeted` tie but both beat `untargeted`, decomposition rather than centrality was the operative mechanism. This is still useful methodologically, but it narrows the main paper's contribution to coherence and reasoning transparency rather than accuracy improvement. We would report it honestly and discuss what distinguishes it from the stronger claim.

If neither targeted condition beats `untargeted`, the coherence-to-accuracy transfer does not hold under this operationalization. The main paper's scope narrows further, and the extension becomes a cautionary data point rather than a capability demonstration. Either of the three outcomes sharpens how the paper positions itself.
