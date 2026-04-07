# Classification Prompt (Version 8b) — Used to produce 116 HIGH complexity questions

**Date:** 2026-04-01 ~03:07 UTC  
**Model:** openai/gpt-5.4 via OpenRouter  
**Session:** 49de2a93-ff18-436a-88fd-9c060caa63d6  
**Input:** 500 ForecastBench questions (batched by 25)  
**Result:** 116 HIGH / 384 LOW  

---

## System Prompt

```
You are classifying forecasting questions by whether they have sufficient
causal complexity to support a large (12-16 node) directed acyclic graph
of interacting causal factors.

A question has HIGH causal complexity if ALL of the following are true:
1. A domain expert would naturally identify 12+ distinct, non-redundant
   causal factors that INTERACT with each other (not just a linear chain)
2. The factors span 3+ domains (e.g., Political, Economic, Social,
   Technological, Military/security, Regulatory/legal, Environmental,
   Organizational)
3. The factors form a genuine causal NETWORK — they influence each other,
   create indirect pathways, and have effects through mediating variables
4. The question is GROUNDED in real, identifiable actors, institutions,
   or measurable conditions with current observable evidence
5. The expert reasoning naturally involves understanding how factors
   interact to shape the outcome, not just checking a sequence of
   conditions

A question is LOW if ANY of these apply:

Ungrounded/speculative:
- The outcome is speculative with no historical precedent
- It depends on inventions or breakthroughs that do not yet exist
- The causal factors would be entirely hypothetical (sci-fi scenarios)

Simple reasoning structure:
- It is primarily time-series extrapolation ("will metric X increase?")
- The factors are mostly within a single domain
- The factors form a linear chain rather than an interacting network
- A reasonable analyst would rely on base rates, trends, or simple
  conditional reasoning

Expert methodology shortcuts (use these as guides, not hard rules):
- Statistical/actuarial: base rates, trend extrapolation, time series
- Tournament/competition: relative strength comparisons with variance
- Pipeline/stage-gate: linear progression through defined phases
- Market pricing: outcomes aggregated into asset prices

IMPORTANT: Some questions resolve as a single event (a decision, an
action) but the CONDITIONS that determine that event emerge from a
complex interacting network. If the context and drivers form a genuine
multi-domain causal network — even though the resolution is a discrete
event — classify as HIGH. The test is whether the DRIVERS interact in
a network, not whether the outcome is binary.

For each question, respond with a JSON array in the same order as the
input. Each element should be:
{"complex": true/false, "reason": "<1-2 sentences>"}
```

---

## Prompt Evolution (8 versions, ~50 minutes)

| Version | Time (UTC) | Key change | Result |
|---------|------------|------------|--------|
| V1 | 02:15 | 3-category (COMPLEX/MODERATE/SIMPLE), 5+ factors | Not run |
| V2 | 02:17 | Binary HIGH/LOW, 12+ factors, n_plausible_factors | Not run |
| V2b | 02:19 | Added domain taxonomy, domains output field | Not run |
| V3 | 02:20 | Simplified output to {complex, reason} | 49 HIGH / 51 LOW |
| V4 | 02:27 | Added "interacting network" criterion | 40 HIGH / 60 LOW |
| V5 | 02:34 | Added expert methodology criterion | 28 HIGH / 72 LOW |
| V6 | 02:40 | Added "grounded" criterion | Not separately counted |
| V7 | 02:49 | Restructured ALL/ANY; grounded necessary but not sufficient | 19 HIGH / 81 LOW (too aggressive) |
| V8 | 02:54 | Softened methodology to "guides not hard rules"; drivers-vs-outcome distinction | Final adopted |
| V8b | 03:07 | Removed inline examples, otherwise identical to V8 | **116 HIGH from 500 questions** |
