# Revision TODOs — Reviewer Feedback

Consolidates asks from both rounds of reviewer feedback. Grouped by effort and tagged with which reviewer raised each item (R1 = first review, R2 = second review, B = both). Addressed items already completed this session are at the bottom for reference.

---

## Quick wins (~hours)

### 1. Directional coherence analysis [R2, R1 hinted]
Report signed shift direction, not just absolute magnitude:
- % of negate probes that decrease p
- % of strengthen probes that increase p
- Breakdown by node importance tier (high/medium/low)
- Breakdown by model

One supplementary table + one paragraph in Results §Topology. ~2 hours including the analysis script.

### 2. Release reproducibility artifacts [R2]
Add a GitHub URL in the paper pointing at the forecast_bench repo. Include:
- All prompts (already in Appendix A)
- Seeds, model IDs, OpenRouter timestamps
- Analysis code
- The 116-question set
~30 min.

### 3. Practical-significance framing [B — partially done]
Already added the "~0.15-0.2 pp per SD" translation in Results §Topology. Consider also adding:
- One concrete example translating top-tier vs peripheral tier into percentage-point difference
- Pulling it up into the Abstract/Introduction so reviewers see it before they hit the modest R²m number

### 4. Complexity-filter human validation [R2]
GPT-5.4 classifies question complexity. Validate on a random sample of 30-50 questions with a second human-coded pass and report precision/recall for HIGH/LOW labels.
- Can do yourself in ~2-3 hours
- Add a single paragraph to §Questions or an Appendix note
- Strengthens the claim that the 116 set is a fair sample

### 5. Cosine-threshold sensitivity (already done)
Sweep at 0.6 / 0.7 / 0.8 is in the Results intro. No further action.

---

## Moderate effort (~days)

### 6. Cross-model probing [B — biggest leverage on reviewer concerns]
**Highest-impact addition by far.** Both reviewers explicitly requested this.
Design:
- Take Model A's DAG for a question
- Generate probes using Model B
- Present (Model A's DAG + Model B's probes) back to Model A
- Measure: does topology→shift still hold when probes come from a different source?

Directly addresses the self-referential architecture concern, which is the #1 critique in both reviews. 5-7 days of work including a subset of 50-100 questions and writeup. Could replace or supplement the forced-ignore ablation as the headline self-reference control.

### 7. Edge-weight / semantics analysis [R2]
Edges are annotated with causal mechanisms but treated as unweighted in the current LME. R2 asks: does incorporating edge weight/polarity (from the annotation text) improve explanatory power?
- Add an edge-strength score (LLM-rated or embedding-similarity-based)
- Refit the LME with edge strength as an additional predictor
- Compare R²m
~2-3 days. If positive, adds a clean "topology + semantics" story.

### 8. Alternative centrality metrics [B]
Test whether PageRank, closeness, in/out-degree, k-core, or directed edge betweenness improve over betweenness/outcome mediation alone. Supplementary LME table.
- Networkx computes all of these in one pass
- Rerun the existing LME with each as a replacement predictor
~1-2 days including writeup.

### 9. Multi-model debate quantification [R2]
Currently described but not evaluated. Add:
- Probability convergence metric across 5 rounds (final |p_A - p_B| vs initial)
- Whether DAG revisions concentrate on high-centrality nodes
- Any accuracy delta (hard without ground-truth; possible if using market-anchored subset)
~3-5 days. Can be done on a smaller sample (20-30 questions × 3-5 model pairs).

### 10. Edge-probe engagement analysis [R2]
R2 asks: what fraction of edge-target probes actually engage with the edge mechanism vs drift to node-level arguments? Could explain the node > edge effect.
- Sample 100-200 edge probes
- GPT-4o-mini (or human) judge: does the reasoning reference the edge mechanism?
- Report engagement rate and correlate with |Δ|
~1-2 days.

### 11. Qualitative case studies of low-nGED pairs [R2]
R2 notes the nGED of 0.88 is "statistically detectable but semantically shallow." Counter with:
- Pick 3-5 question pairs with the lowest nGED
- Show their aligned DAGs side-by-side (similar to `exemplar_networks` figure)
- Narrate which parts of the graph agree (core vs periphery)
~4-6 hours including figure regeneration.

---

## Larger analyses (~week+)

### 12. Agent-forecast extension (Option B — task win)
Task-win experiment we built the pipeline for:
- ~500 ForecastBench questions × 5 models × 4 conditions (no_search / untargeted / topology_targeted / peripheral_targeted)
- 7–90 day resolution window, tiered milestones at Weeks 2, 4, 8–12
- Score Brier against ForecastBench's own resolution sets
- Primary contrast: topology_targeted vs peripheral_targeted (isolates centrality from decomposition)
- Secondary: topology_targeted vs untargeted (combined effect)
- Location: `forecast_bench/agent_forecast/`
- Design doc: `paper/external_forecast_analysis.md`

Directly addresses "no task win" critique. If topology-targeted beats untargeted, adds a strong application section. Timeline: ~3 weeks from today, tight but viable.

### 13. Signed/weighted LME with edge polarity [R2]
More ambitious version of #7. Rather than just scalar edge strength, encode:
- Edge polarity (positive / negative mechanism)
- Edge strength
- Propagation through multi-hop paths
Refit the full LME with these as additional predictors. ~1-2 weeks.

### 14. Human-expert DAGs for external validity [R1]
Have domain experts draw causal maps for a subset of questions. Compare structure and probe sensitivity to model-elicited. The cleanest response to "are the elicited DAGs capturing something real?"
- Expensive (expert time) and slow
- Future work, not this revision

---

## Related work and discussion additions [R2]

R2 names specific papers to position against. These exist in the Discussion TODOs already but worth explicit framing:

- **CaPE** — Bayesian active-query framework for causal discovery. Our probe selection is heuristic (importance tiers); CaPE formalizes via expected information gain. Mention as future direction.
- **CDCR-SFT** — trains models to construct and reason with DAGs. We work with off-the-shelf models; distinguish broadly applicable diagnostic vs training-time intervention.
- **Prophet Arena** — live-market forecasting accuracy. Our work is complementary (internal coherence vs external accuracy).
- **TruthTensor** — similar calibration/accuracy framing. Same complementarity framing.
- **EVOLVECAST** — belief revision under time-anchored news. Our probes are synthetic/structure-targeted. Future work: combine.
- **GEDAN** — learned-cost graph edit distance. Already flagged in first-review framing; one line in discussion.

Wire into the existing Discussion §Related-work sub-paragraph. ~2-3 hours to draft cleanly.

---

## Already done this session

Addressed during this revision round:

- ✅ **nGED bug fix** — namespaced IDs, null now 0.998 (< 1); observed 0.881.
- ✅ **Cosine-threshold sensitivity** — ran at 0.6 / 0.7 / 0.8, all p < .001.
- ✅ **Practical-significance translation** — added probability-space interpretation in §Topology.
- ✅ **Node vs edge full stats** — pooled means, Welch t, Cohen's d, per-model gaps added to §Topology.
- ✅ **Limitations section drafted** — self-referential architecture, LLM-judge bias, modest effect sizes, alternative centrality.
- ✅ **Discussion section drafted** — AI-agent context, structural faithfulness framing (your original text preserved).
- ✅ **"is_directDirect" label cleanup** in tables.
- ✅ **Coef → β** across all tables and the R script.
- ✅ **Sig-fig standardization** — 3 dp default, 4 dp when value < 0.01; no leading zeros in p-values.
- ✅ **Within-question τ, shortest-path premium, SSR, asymmetry index removed** from the Elo table.
- ✅ **Cross-model agreement table dropped** — headline now inline in prose.
- ✅ **Superforecasting method text** — Jaccard → nGED.
- ✅ **Structural ablation paragraph** — replaced legacy "after dropping edge betweenness" aside.
- ✅ **Agent-forecast pipeline built** — in `forecast_bench/agent_forecast/`, ready to run once API keys are set.

---

## Suggested prioritization

If time is tight, do in this order:

1. **Directional coherence** (Q1, Q7 from quick wins) — cheap, directly answers R2 Q1
2. **Release artifacts** (Q2) — 30 min, answers R2 Q8
3. **Cross-model probing** (#6) — highest single-issue leverage, addresses both reviewers' #1 concern
4. **Complexity-filter validation** (#4) — cheap, defensive
5. Everything else as time allows

If the deadline is 4+ weeks out: add the agent-forecast extension (#12) — it's the task win and directly addresses the "what's the payoff" concern that underlies the modest-effect-sizes criticism.
