# Knowable Worlds: LLM Forecasts Against Knowable Probabilities

Status: design draft (2026-07-03). Chapter of the known_causal_models program
(paper 3 of the arc: belief sensitivity → structure discovery → **forecasting
under a changing causal structure**).

Full motivation + related work: `KNOWABLE_WORLDS_MOTIVATION_RELATED_WORK.md`.

---

## 1. Thesis: does predictive updating couple to causal-structural updating?

Forecasting in a world that changes demands two abilities — **updating the
predictive model when the regime shifts**, and **relating that update to the
change in the underlying causal structure**. This study asks whether LLMs
*couple* these or *dissociate* them: when the causal structure generating a
series changes, does a model update its forecasts *and* its stated causal
structure, or does prediction adapt while causal understanding stays frozen?
(Pilot evidence: dissociation — forecasts adapt slowly, the stated graph never
tracks the change.)

We can ask this exactly because we build worlds where BOTH the true predictive
distribution and the true causal structure are known — before and after a change
we set — so predictive updating and causal-structural updating are measured
separately, per item, against optimal. The original one-line framing is a
special case of this: how far LLM forecasts sit from optimal, and whether
mechanism knowledge or environmental stochasticity moves them.

## 2. Why this setting is epistemically privileged

The exact-truth setting is what lets us capture the coupling question — it is
unavailable in any real-world evaluation. Every real-world forecasting eval
scores against realized 0/1 outcomes; the true probability is unknowable, so
"calibration" is always a binned proxy (ECE), and "didn't know" is never
separable from "couldn't compute". Here:

- **True p\*** per question: analytic for linear-Gaussian SCMs (covariance
  propagation through the DAG); cheap simulation (10k draws) for tanh/market/conflict.
- **Known aleatoric floor**: the irreducible uncertainty of each event is exactly
  p\*(1−p\*), and the noise scale is an engine dial.
- **The knowledge excuse is removable**: with the full mechanism in context, p\* is
  in-principle computable from the prompt — any residual miscalibration is a PURE
  reasoning/computation failure. No real-world study can make that separation.

## 2.1 FRAMING COMMITMENT (user, 2026-07-03): value-of-information, not ability

Within the coupling frame, the STATIC arm's specific contribution is a
value-of-information measurement: it prices what causal knowledge is worth to a
forecast (the coupling question asked as a dose, in a still world), and the
computation-vs-understanding results it yields are the lens the dynamic coupling
results are read through. This study measures **how causal knowledge informs
PREDICTION** — not causal-reasoning ability per se. Causality is the INPUT; forecast calibration vs exact p\* is the DV;
the headline quantity is the **marginal predictive value of each knowledge increment**
(VOI = delta optimality-gap per rung/cell), including where it is NEGATIVE (the
confounded cells: the true graph, structure-only, worsens forecasts). Competence
claims (Pearl-rung mastery, severing, calculator-vs-statistician) are the MECHANISM
section — they explain the VOI curve's shape, they are not the point. This framing
also separates the paper from ability benchmarks (CLadder etc.): they score causal
answers; we price causal knowledge in forecast currency. Analysis deliverable: the
VOI ladder figure (marginal gap reduction per increment, with the negative-VOI
confounded cells highlighted) + VOI-over-data-informativeness curves (Sec 6.x dials).

## 3. Research questions (ordered so the paper survives any single null)

- **RQ1 (measurement — always answerable):** How far are LLM forecasts from optimal
  (|p − p\*| per item), and where does the error live: bias, poor discrimination
  (slope of p on p\*), or noise?
- **RQ2 (ceiling test):** Given the COMPLETE mechanism (structure + equations +
  parameters + noise), can the model recover the true predictive distribution?
  Deviation = pure propagation failure.
- **RQ3 (dose-response over mechanism knowledge):** Does calibration improve
  monotonically along the information ladder (observational samples → +structure →
  +signs → +full equations)? *Registered caution:* the held-out prediction analysis
  found GT structure gives NO directional-accuracy lift — structure-only may be flat
  here too; that is a finding, not a failure ("knowledge without computation doesn't
  help").
- **RQ4 (aleatoric sensitivity — the sleeper):** Dial the engine's noise scale on a
  fixed SCM (p\* slides toward 0.5). Does stated model uncertainty MOVE with true
  stochasticity? *Registered prediction* (from the ensemble pilot's
  vocabulary-anchoring and locals-pinned-at-0.5 findings): largely NO — LLM
  "uncertainty" behaves like a fixed stylistic register, insensitive to actual
  randomness. If confirmed, this is the memorable result.
- **RQ5 (decomposition — elicit-vs-compose, reusing the compiled-forecast system):**
  When the model's own declared SCM is executed by the engine, is the resulting
  forecast better than its direct forecast? Uniquely scoreable here because TRUE
  parameters are known: elicitation error (declared params vs GT params) and
  composition error (direct p vs executed-own-model p) separate for the first time.
  (The causal_ensemble pilot could not tell whether locals were bad or unknowable —
  here we can.)

## 4. Environments

1. **Synthetic SCM testbed (primary)** — `scm/engine.py` + `run_pilot_scm.py`
   machinery. Random DAGs over abstract X1..Xn; linear (analytic p\*) first,
   tanh (simulated p\*) for robustness. Prior-free → pure computation test; free
   replication; complexity (n_nodes, edge_prob) and noise sweepable.
2. **Market + conflict engines (secondary, naturalistic)** — same battery logic on
   named-variable domains; checks whether world-knowledge priors help or hurt
   relative to the abstract setting (bridges to the discovery paper's domains).

## 5. Question battery

Binary events over engine states: `P(X_k > τ)` observational and
`P(X_k > τ | do(X_i = v))` interventional, at horizon h.

- **Stratify τ by true probability**: choose thresholds so p\* covers
  {.05,.1,.2,.35,.5,.65,.8,.9,.95} — full calibration-curve coverage by
  construction (real benchmarks can never guarantee this).
- Tag each item: aleatoric level p\*(1−p\*), #hops from intervention to outcome
  (propagation depth), observational vs interventional.
- Per SCM ~10-15 items; ~30-50 SCMs; 3+ seeds per cell. Exact p\* for linear;
  10k-draw simulation otherwise (MC error on p\* ≪ effects of interest).

## 6. Conditions

**Information ladder (between-item, the RQ3 axis):**
| rung | context given | interpretation of miscalibration |
|---|---|---|
| L0 | observational samples only (n=50 draws) | inference + computation |
| L1 | L0 + DAG structure | + structural knowledge |
| L2 | L1 + edge signs | + qualitative mechanism |
| L3 | full equations + noise scales (p\* computable in principle) | PURE computation (ceiling test, RQ2) |

**Response mode (the RQ5 axis, reusing the DAG→probability system):**
- **direct**: model states p.
- **declared-SCM / compiled**: model outputs its SCM estimate (structure +
  coefficients + noise) as JSON → OUR engine executes it → p̂. For market/conflict
  binary events the noisy-OR `bayes_compile.py` variant applies; for the SCM
  testbed the scm engine itself executes declared models (cleaner — same
  functional family as GT).
- (optional ceiling-tool arm: model + code execution, to bound what "could compute"
  means for a tool-using system.)

**Ecological framing of the ladder (user, 2026-07-03).** L0-L2 are the ECOLOGICAL
rungs — the actual epistemic menu of a real forecaster (data; data+structure;
data+directional theory). **L3 is a DIAGNOSTIC CEILING, not a realistic condition**:
kept because (a) it is the identification anchor (only rung where p\* is computable
from the prompt -> splits couldn't-know from couldn't-compute everywhere else),
(b) the computation>>estimation cliff and the severing proof both require it,
(c) the VOI curve needs its endpoint. Paper's ecological claims live on L0-L2 +
quality axes; L3 framed as laboratory control. **Planned rung L2.5 — coarse
quantitative knowledge** (equations with ranged/rounded coefficients, e.g. "X raises
Y by roughly 1-2 per unit"): the realistic upper-middle cell experts actually occupy.
Key question: does computation/severing switch on at realistic precision, or does
causal competence require an exactness the world never supplies?

**Quality rungs IMPLEMENTED (2026-07-03; user prioritized over L2.5):**
- **L1w** — wrong structure: every edge reversed (still a DAG, certified false).
  Post-trap-attraction prediction: the model follows what it's given, so L1w should
  steer estimation wrongly; analysis adds the **wrong-model oracle** (what a rational
  agent faithfully believing the reversed graph would answer, computable exactly) —
  triangulating truth / trap / followed-wrong-model tells us HOW structure is consumed.
- **L1r / L1i** — partial structure, query-relevant vs equal-count irrelevant edges
  (header flags partiality). Same information quantity, different relevance: does the
  model know WHICH knowledge matters? L1r ~ L1 would mean only the relevant subgraph
  ever mattered; L1i ~ L0 would mean irrelevant structure is correctly ignored.
- **L1b** — relevant subgraph + BACK-DOOR pathway (edges into the do-node and from
  its ancestors to the outcome; verified on dc_0: {X7->X3, X2->X7, X2->X4, X4->X3},
  4/7 edges). THE decisive quality cell post-trap-attraction: does seeing the
  confounding pathway explicitly trigger severing where the full graph did not —
  attentional vs conceptual failure.
L2.5 (coarse coefficients) DEPRIORITIZED per user — queued behind the quality axes.
Hidden-variable partial observability (dropping a confounder COLUMN from the samples —
latent confounding, the canonical real-world hardness) noted as the phase-2 extension
of this axis.

**Sample-provision critique + two added rungs (user, 2026-07-03).** Observational
items are answerable BY COUNTING at every rung (error pinned at the binomial floor
~0.05) — they are the data-reading CONTROL, never the headline; the do/confounded
cells are where counting fails or misleads by construction. To close the "too
leading" concern empirically, add: **L-null** (event only — no samples, no structure:
measures the pure prior / anchoring vocabulary, the true ladder floor) and **L3-pure**
(equations only, no samples: prediction from theory alone; L3-pure vs L3 tests whether
data aids, distracts, or is inert once the mechanism is known).

**Identifiability gradient (L0 subtlety, added 2026-07-03):** all rungs see the SAME
50 observational draws (fixed seed per SCM); higher rungs only ADD mechanism info.
This partitions the battery: OBSERVATIONAL items are answerable at L0 in principle
(count exceedances in the table; binomial SE ~7pp) — a pure distribution-reading
test; INTERVENTIONAL items are mathematically UNDERDETERMINED at L0 (do() effects
not identified from observational data) and only become identified at L1+ (structure
+ regression) and exact at L3. Consequences: (a) the kind x rung interaction is
diagnostic — interventional items should gain far more from the ladder, else the
model isn't using structure; (b) do-at-L0 is a free rationality probe: does the
model hedge on unknowable items? Registered prediction: no hedge — same confidence
as knowable items (uncertainty-as-style).

**Knowledge quality & scope axes (user, 2026-07-03).** The ladder manipulates
knowledge QUANTITY; two further axes at the L1 rung:
- **L1-partial** — show only PART of the DAG. Key manipulation: same amount of
  structure, but either the query-relevant subgraph (paths from the do-node to the
  outcome) or an equal-sized query-IRRELEVANT subgraph. Tests whether the model knows
  WHICH knowledge matters, separately from having it.
- **L1-wrong** — incorrect structure: reversed edges, permuted DAG, or flipped signs.
  The scrambled control reborn at the knowledge level. Diagnostic either way:
  wrong-DAG harmless (vs L0) replicates structure-as-decoration in direct mode;
  wrong-DAG HARMFUL means the model defers to supplied structure (misinformation
  sensitivity — connects to the belief-sensitivity paper's probe findings).
Full design becomes quantity (L0-L3) x quality (correct/partial-relevant/
partial-irrelevant/wrong); phase the quality arms after the quantity pilot.

**SNR clarification + value-of-information dials (user, 2026-07-03).** Current
noise: sigma=1.0 vs weights 0.5-2.0 -> non-root R^2 mean .70 (range .21-.93) —
moderately clean systems. KEY SUBTLETY: uniform sigma-scaling leaves ALL correlations
invariant (corr^2 = w^2/(w^2+1); sigma cancels) — so the RQ4 dial changes pure
aleatoric randomness WITHOUT changing data informativeness (a feature: clean
separation). The "noisy data -> causal knowledge worth more" hypothesis needs its own
dials: (a) weight_range shrink (true SNR), (b) sample count 50 -> 10 (data quantity).
**Registered prediction: the mechanism premium (L3/L3p minus L0/L1 error) GROWS as
data informativeness falls** — L3 is data-immune while data-dependent rungs degrade;
figure = error vs informativeness, one line per rung, fanning apart.

**Noise dial (RQ4):** same SCM, σ ∈ {0.25, 0.5, 1, 2} × the battery. DV: slope of
stated p on p\* within item across σ (per-model aleatoric-sensitivity index).

## 6.1 Pilot lessons (2026-07-03, GPT-OSS sanity run, n~270)

**Results (per-kind slopes):** obs flat at ~0.97/err .05 at L0-L2 (counting floor),
exactly 1.00/err .000 at L3. Do(): L0 0.62/.26 -> L1 0.85/.15-.19 -> L2 1.01/.13 ->
L3 1.00/.000. Registered predictions 1-3 REFUTED (no anchoring at L3; no computation
gap; structure helps); 4 confirmed (no hedging); 5 untested.

**Normative-baseline reinterpretation (critical):**
- ALL pilot interventions hit ROOT nodes -> conditioning == intervening -> the
  observational-analog oracle scores 0.000. L0-do was identified all along; the model's
  .26 error is a failure of implicit regression + extrapolation (do-value at ±2SD,
  no nearby rows), not of answering the unanswerable.
- OLS-on-same-data rational floor at L1-do = 0.059; model = 0.186 (3x floor).
- Revised capability gradient: **computation (L3) flawless >> estimation (L1) 3x floor
  >> implicit regression (L0) rough.** The model is a perfect calculator and a
  mediocre statistician; accuracy is lost wherever numbers must be extracted from data
  rather than read from text.

**Confounded-cell results (2026-07-03, n=8-11/cell, PILOT SCALE): the headline
finding.** Trap-vs-truth on certified confounded items (ident_gap >= .15):
L0 ~coin-flip | **L1 err-vs-trap .286 < err-vs-truth .342 (44% truth) | L2 .199 <
.287 (33% truth) — GIVEN THE TRUE GRAPH, THE MODEL BECOMES MORE CORRELATIONAL** —
structure organizes estimation but do-semantics are not triggered; it propagates
along back-door paths without severing | L3 perfect severing (err 0.000, 100% truth).
One-liner: **the model knows how to intervene on equations, but not on graphs** —
do-calculus as computational skill, absent as conceptual one. Needs replication
(more SCMs, more models) before leaning on it.

**RQ4 noise-sweep results (2026-07-03, n=491, cf items excluded — sweep truth-
recompute invalid for rung 3; runner guard added):** registered prediction 5
("uncertainty as style, insensitive to true randomness") **REFUTED, with a twist**:
- L0 observational: within-item slope of p on p* across sigma = **0.93 median** —
  the model tracks true randomness nearly 1:1 WHEN IT IS VISIBLE IN THE DATA
  (the table's spread widens; it counts). Aleatoric sensitivity via the counting
  channel is essentially perfect.
- L3: slope ~**0.6** and |p-p*| = .049/.035/**.000**/.055 at sigma .25/.5/1/2 — the
  perfect calculator is EXACT AT SIGMA=1 ONLY and degrades away from it,
  under-responding to the printed noise scale. **Perfect mean propagation, attenuated
  variance rescaling** — the sigma term is the one part of the equations it doesn't
  fully use.
Refined finding: aleatoric sensitivity is CHANNEL-DEPENDENT — full through data,
~0.6 through stated parameters. Scoreboard: predictions 1,2,5 refuted, 3 partial,
4 confirmed.

**Battery revision required:** add NON-ROOT interventions with active back-door paths
(conditioning != do), stratify root/non-root. Only that cell tests causal NECESSITY
(truly unidentified at L0) vs causal convenience — currently empty. Also add the
baseline computations (observational-analog oracle + OLS floor) to the standard
analysis outputs; model error means nothing without them.

## 6.2 Counterfactual rung (Pearl rung 3 — added 2026-07-03)

`cf_*` items complete the causal hierarchy: one FACTUAL realization is shown in full;
the query is what WOULD have happened had node j been set to v ON THAT OCCASION
(same background noise). Exact ground truth via abduct -> act -> predict
(`analytic.counterfactual_value`, verified: replay identity, manual forward pass,
descendant-locality). With full factual evidence the counterfactual is DETERMINISTIC
(p* in {0,1}); tau is placed at the MIDPOINT of the factual and counterfactual
outcome values so that neither "reuse the factual" nor "ignore the intervention"
scores — only genuine noise-replay does. 18 items across the 5 pilot SCMs (root and
confounded sources); rational answer is extreme (0.99/0.01) — anchored mid-range
answers are the failure signature. v2 option: partial factual evidence (twin-network
Gaussian conditioning) for continuous p* strata. Ladder status: rung 1 ~perfect,
rung 2 calculator-only (trap-bound at L1/L2, severs at L3), rung 3 QUEUED.

## 7. Metrics

- **True calibration error**: mean |p − p\*|; signed bias (p − p\*).
- **Discrimination on the true scale**: regression slope of p on p\* (1 = perfect;
  the pilot's anchoring predicts ≪1 with intercept pulled to ~0.4-0.5).
- **Optimality gap**: Brier(p) − Brier(p\*) — expected excess loss vs the optimal
  forecaster (exactly computable; nobody else can report this).
- **Aleatoric-sensitivity slope** (RQ4).
- **Parameter recovery** (RQ5): per-edge coefficient error of declared SCMs vs GT;
  then forecast error of executed-declared-model vs direct — the
  elicitation/composition decomposition.
- Stats in R (nlme/lme4), mixed models with SCM and item random effects, paired
  contrasts across rungs/modes — house conventions apply (two-sample only, split
  or preregistered analyses).

## 8. Registered predictions (from prior findings, 2026-07-03)

1. Slope of p on p\* well below 1 everywhere; heavy anchoring mass at canonical
   values (0.2/0.5/0.6-0.7) even at L3.
2. L3 (full mechanism) ≠ optimal: substantial pure-computation gap, growing with
   propagation depth (belief-sensitivity propagation-decay finding transfers).
3. L1 ≈ L0 (structure-only adds little) — consistent with held-out prediction null.
4. RQ4 slope ≈ 0 for direct forecasts (uncertainty as style, not measurement);
   executed-declared-SCM arm mechanically inherits sensitivity (engine propagates
   noise) → the contrast is the paper's sharpest figure.
5. Declared-SCM parameter recovery will be mid-range-anchored (ensemble-pilot v2
   lesson: instructions shift anchors, not discrimination) — but HERE that is
   directly measurable against GT parameters instead of inferred.

## 9. What transfers vs what must be built

**Transfers (≈70%):** scm engine + GT machinery, market/conflict engines + batteries
(`run_held_out_prediction.py` battery logic), hardened `call_llm`, 7-model OpenRouter
roster, `bayes_compile.py` (market/conflict compiled arm), R analysis stack,
contamination-free by construction (no real-world outcomes at all).

**To build:** event/threshold battery generator with p\*-stratification; analytic p\*
for linear-Gaussian (covariance propagation — small, testable); declared-SCM JSON
schema + executor (scm engine accepts arbitrary coefficient matrices already);
elicitation prompts per rung; analysis scripts.

## 10. Literature review verdicts (adversarial review completed 2026-07-03)

**Per-element novelty:**
| Element | Verdict | Closest threat |
|---|---|---|
| E1 true-p\* calibration | **OPEN** | ForecastBench-Sim *names it as future work, doesn't do it* |
| E2 mechanism ladder | **OPEN** | no precedent found |
| E3 aleatoric sensitivity | **OPEN** (forecasting) | BayesBench (2512.02719) partial, psychophysics only |
| E4 declared-model-executed | **CLOSE CALL** | Linear-LLM-SCM (2602.10282) elicits+scores params; LLM-BI (2508.08300) executes; **neither closes the loop** (declared → executed → vs true p\* AND vs direct forecast) |

**The gift quote** — ForecastBench-Sim §5 (Future Work), verbatim: "the same starting
world can be rolled out N times under different RNG seeds and forecasts resolved
against the empirical event frequency across rollouts. This converts resolution from
a single noisy realization into a target close to the simulator's true generating
probability." The field's most relevant group POINTS AT E1 without doing it — cite as
motivation, not competitor.

**Framing (adopted):** lead with E1 (the measurement problem); E2 = the diagnostic
engine; E3 = the most surprising empirical claim; E4 = the cleanest decomposition.
Paper identity: *"the first study to measure LLM calibration against true
probabilities — and to diagnose where the errors come from."*

**E4 differentiation requirement:** always report the triple {p_direct, p_declared-
executed, p\*} per item — the closed loop is what Linear-LLM-SCM and LLM-BI each
lack half of.

**Must-cites (core):** ForecastBench-Sim 2606.18686; BayesBench 2512.02719;
Linear-LLM-SCM 2602.10282; LLM-BI 2508.08300; KalshiBench 2512.16030 (reasoning
worsens calibration — motivates RQ1); verbalized-confidence / semantic-entropy UQ
line; held-out prediction null (in-house); full list in review transcript.

**Pilot sizing:** 5 linear SCMs × 12 items × L0/L3 × direct-only × 1 model ≈ 120
calls (~$0.25) sanity pass before the full grid.

## 10.1 Delta scoop-check (2026-07-03): confounded/counterfactual/factorial cells

Verdicts: **C1 traps CLOSE CALL** (CLadder rung-2 is the structural neighbor; ours
differs on: continuous trap-vs-truth index vs binary accuracy, certified >=.15 gaps,
numeric SCMs with data, and the trap-ATTRACTION finding is unmeasurable under binary
scoring -> finding itself OPEN). **C2 numeric rung-3 OPEN** (abduct->sever->replay
with exact truth + midpoint-tau design: no counterpart). **C3 knowledge x data
factorial OPEN** (in-context estimation -> do() computation: nothing crosses these;
nearest is Garg et al. 2022 in-context regression, no causal side).

**Most threatened by: CLadder (2312.04350)** — reviewers will cite it against all
three; the VOI framing (Sec 2.1) is the primary wedge: they SCORE causal answers, we
PRICE causal knowledge in forecast currency. Forward-citation sweep (2026-07-03):
2024-26 descendants (CausalBench, CausalEval, CauSciBench, InterveneBench 2026,
CausalT5K, Caliper) all accuracy-scored reasoning benchmarks by description — READ
before submission: InterveneBench (closest by name) and "When Helpfulness Overrides
Causal Caution" (2606.24370; adjacent to our ignored-severing-instruction
observation). Must-cite cluster: CLadder, Corr2Cause, causal parrots (Zecevic),
Kiciman et al., CRASS, Garg et al. 2022, Linear-LLM-SCM 2602.10282, LLM-BI
2508.08300, + fallacies 2406.12158.

## 11. Relation to the causal_ensemble postmortem

This design inherits the ensemble pilot's instruments (anchoring diagnostics,
displacement/decomposition logic, compiled-forecast machinery) and answers the
question that killed it from the safe side: instead of asking self-generated
structure to improve real-world forecasts (impossible by total expectation), it asks
whether TRUE exogenous structure improves forecasts against TRUE probabilities —
the only quadrant of that 2×2 that was never testable outside a simulator.

## 13. AUDIT (2026-07-03, pre-scale-up)

**A. Data integrity — PASSED.** 1,350 rows / 5 append passes: zero duplicate
successful keys; zero p\* drift across three battery expansions (1,038 rows checked);
L3-do error <= .0003 in each of the 5 SCMs separately (not driven by one system).

**B. Design caveats (document, don't fix):** (1) tau leaks answer-extremity —
corr(|tau|, |p\*-.5|) = .63 across obs items; GPT-OSS did not exploit it (Lnull flat)
but a scale-savvy model could -> Lnull = "prior given the question", not pure prior.
(2) The "severed" hint makes trap-attraction conservative. (3) Root-do at ±2sd is
extrapolation by construction — L0-do failure partly measures extrapolation.

**C. Action items before ANY claim:**
1. **n=5 SCM clusters is the replication unit** — everything so far is descriptive.
   Scale to 30-50 SCMs; inference in R (mixed models, SCM random effects).
2. Confounded cells n=6-9 (quality x cf cells n=1) — more SCMs largely fixes.
3. Token-era mixture: 90 surviving rows from the max_tokens=1200 era (systematically
   the easier items) — rerun uniformly or drop era-1 for the final dataset.
4. Post-chain null-retry sweep (L1r 27/49, L1b 22/48 parse-failure history).
5. Wrong-model oracle required before L1w is interpretable — now in
   analyze_calibration.py.
6. Committed analysis scripts (this audit's deliverable): `analyze_calibration.py`
   (descriptives + 4 oracles + master CSV) and `analyze_calibration.R` (inference).

**Fixed-bug log:** runner loop nesting (only-L3 bug); np.bool_ serialization; resume
treating nulls as done; cf items in noise-sweep truth recompute; figure class
conflation (cf lumped into do/conf); Agg backend; L1i index-order truncation bias.

## 14. SCALE-UP DESIGN (confirmatory run, registered 2026-07-03)

**Battery per SCM:** rungs {L0, L1, L2, **L3p**, L1w, L1r, L1i, L1b} x full item set.
Retired: Lnull (established floor; kept as a 1-SCM canary per new model — the tau-
leakage check), L1p/L2p (established nulls), L3-with-data (redundant with L3p; the
source-switching demo already established). **30 fresh SCMs (seeds 200-229)** —
disjoint from the pilot's 100-104: pilot = exploratory, this run = confirmatory.
Uniform max_tokens=4000 (kills the token-era confound). Output:
`knowable_worlds/outputs/scaleup_gptoss`.

**Confirmatory hypotheses (registered before the run):**
H1 computation cliff: L3p interventional error ~0, far below L0/L1/L2.
H2 trap-attraction: trap_pull positive at L1 and L2 on confounded items (pilot:
   +0.12/+0.16 n.s.); release (negative) at L3p.
H3 wrong-graph obedience at L1w: intercept < 0 (pilot: -0.185, p=.001).
H4 L1b rescue: back-door visibility cuts confounded error vs L1 (pilot hint:
   0.072 vs 0.23, n=6 — attentional-vs-conceptual test).
H5 estimation gap: L1 error above the OLS floor (pilot: +0.143, p=.008).
H6 counterfactuals: anti-slope at L0 (factual-reuse signature, pilot -0.24);
   near-perfect at L3p (pilot 0.91-0.93).
**Why-structure-doesn't-help thesis (2026-07-03):** information is only worth what
the complementary skill can extract — structure demands estimation + severing (the
model's weakest skills); equations demand only arithmetic (its strongest).
Inference: analyze_calibration.R, SCM random intercepts, 30 clusters.

## 15. DYNAMIC ARM: tracking a changing causal world (registered 2026-07-03)

**User's reframe (verbatim intent):** the observational data becomes a TIME
SERIES with an evolving structure — regime 1 generates periods 1..t*, a
structurally different regime 2 generates t*+1..T, and the question is whether
the model can TRACK the change. This addresses the static design's two
weaknesses: the model is handed the answer (here it must earn structure from
data and notice when it breaks), and the world never changes (here
non-stationarity is the object of study — the forecasting-relevant skill).

**Why lag-1 dynamics make this fair:** with X_t = c + B_r^T x_{t-1} + eps,
temporal precedence removes Markov-equivalence ambiguity — the cross-lag
structure is FULLY identifiable from observation alone, so structure recovery
is a legitimate ask (unlike the static observational case). Truth stays exact:
one-step-ahead is Gaussian given the observed current state, so every forecast
item has an analytic p* — and an analytic STALE answer p_stale (the regime-1
mechanism applied to the same state), the perseveration oracle.

**One-step control property:** given the fully observed current state, a change
to edge i->j alters the next-period distribution of j ONLY. Every other node is
an automatic within-checkpoint control — any post-change error jump on
controls would indict general confusion, not the change.

**Design (pilot):** 8 nodes (matches the static arm's world size; upgraded from 6 on 2026-07-03 review), edge_prob .2 (median 12 cross-lag edges of 56 possible slots), self-persistence diag U(.25,.5),
cross weights ±U(.5,1) (spectral radius stabilized <.9; change candidates
rejected if radius >=.95; strong-edge preference |w|>=.35 for remove/flip/
double). T=100, t*=60, burn-in 80. 4 change types (edge_add, edge_remove,
sign_flip, weight_double) x 3 seeds (300-302) = 12 scenarios (scenario =
replication unit). Checkpoints t in {30,40,55 | 62,66,70,80,95} (three pure-regime-1 checkpoints = within-regime learning curve; user directive 2026-07-03: the model must get the chance to estimate the causal model inside ONE regime first): model sees
periods 1..t, answers 3 items — (1) affected-node forecast, tau = midpoint of
stale and true conditional means post-change (maximally separates "updated"
from "still stale"; same trick as the counterfactual midpoint-tau), stratified
tau pre-change; (2) control-node forecast, stratified tau; (3) SIGNED cross-lag
edge list ("X1->X2:+"), F1-scored against both regimes' graphs. 288 calls.
Prompt is NEUTRAL — no mention a change may occur (detection unprompted is the
headline); --hint flag = informed arm, registered follow-up, not in the pilot.

**Baselines (attached at analysis, sigma from residuals):** p_stale (exact old
mechanism — pure perseverer), p_never (OLS on periods 1..40, never refit),
p_window (OLS on last 20 periods — the recency strategy), p_full (OLS on all
periods — the change-blind statistician). Window vs full brackets the
adapt-fast/adapt-never tradeoff; an ideal change-point detector would beat
both.

**Registered hypotheses:**
D1 disruption: post x affected interaction > 0 in abs_err ~ phase*affected,
   (1|scenario) — the change disrupts the affected node specifically.
D2 perseveration with release: persev = d(truth)-d(stale) intercept > 0 early
   post-change (gap>=0.5 items), rel_time slope < 0 (letting go with
   evidence). Latency = where the perseveration curve crosses zero.
D3 vs recency floor: model error exceeds the 20-period-window refit
   post-change (the static L1 estimation-gap analog: +0.14 there).
D4 structure channel: unsigned F1 tracks edge_add/edge_remove; SIGNED F1
   Sensitivity note (2026-07-03): whole-graph F1 is dominated by the ~17
   shared edges (old/new separation bounded at ~1 edge in 18). Registered
   secondary DV: the changed SLOT's stated state (old/new/neither) per
   checkpoint; structural latency = first checkpoint the slot flips to new.
   additionally tracks sign_flip; weight_double is invisible to any
   qualitative report (registered: forecast channel only).
D5 dissociation (the headline RQ): forecast recovery and structure-report
   updating can have different latencies — predictive adaptation without
   structural insight (recency pattern-matching) or the reverse (stated
   change, unmoved forecasts). Static-arm results predict the former: the
   model extracts predictive value from data far better than from structure.

**Known limitations (registered):** regime_gap depends on the realized state
(tagged per item; perseveration analysis filters >=0.5 sigma; ~71% of
post-change affected items pass at pilot settings). One change per scenario.
Detectability differs by change type (sign_flip loudest, weight_double
quietest) — change_type is a covariate, not a confound, since truth is exact
per item.

**Files:** dyn_engine.py (VAR + regime shift + exact truth, MC-verified 2.02
SE worst), dyn_battery.py, dyn_prompts.py, run_dynamic.py,
analyze_dynamic.py, analyze_dynamic.R, gen_dynamic_figures.py. Full chain
smoke-tested on a synthetic recency agent before any API call (recovered the
designed signatures: D1 interaction +0.31 p<.0001, D2 intercept +0.34 slope
-0.025 p<.0001).

**Relation to the static arm:** the ladder is the interpretive key — a
dynamic-tracking failure with data-only context is expected from L0/L1
results; the diagnostic question is which channel (prediction vs stated
structure) moves first. Static rungs for the dynamic arm (revealing the
regime-1 mechanism at L3 and asking the model to notice it broke) are a
registered future knob, not in the pilot.

**Change-magnitude axis (registered 2026-07-03; BUILT 2026-07-05 — see §16.2
addendum 2 for the multi-edge implementation and nested-dose k∈{1,3,6}):** the pilot
changes exactly ONE edge per scenario — deliberately the hardest, cleanest
case (one-step controls stay surgical; one slot for the perseveration and
changed-slot metrics). Escalation knob for v2: scenarios where k in {1, 3, 6}
edges change at t* -> dose-response of detection latency vs change magnitude
("how big does a regime change have to be before the model notices?").
Decision rule: if the pilot shows ANY post-change movement on affected items,
magnitude is a supplement; if the model is at floor everywhere, magnitude
becomes the primary axis. Implementation cost is small (tag children of all
changed edges as affected; controls = untouched nodes).

**Dynamic information ladder (registered 2026-07-04; user insight: the
experimenter CHOOSES how much the agent knows about the boundary):** what the
prompt reveals about the change is an axis, mirroring the static L0-L3 ladder.
D-L0 none (pilot default: non-stationarity never mentioned — spontaneous
detection); D-L1 "may have changed" (hypothesis space opened); D-L2 "did
change, unknown when" (detection given); D-L3 "changed after period 60"
(boundary given — tests pure USE: can it discard rows it is TOLD are stale);
D-L4 "changed after period 60, affecting how Xj is influenced by Xi"
(diagnostic ceiling: only re-estimation remains). Adjacent-rung deltas price
single skills in forecast currency: hypothesis generation / detection /
temporal localization / structural localization. Implemented as
run_dynamic.py --info-level {none,possible,occurred,when,what} (one out-dir
per level); truth identical at every rung, so the VOI framing carries over.
Sequencing decision tree: pilot at D-L0; if no detection -> D-L1 (hypothesis
problem?); if still none -> D-L3 (use-vs-detection dissociation — the dynamic
twin of the static trap-attraction test). At D-L4 the structure item becomes
a manipulation check (the slot is named in the prompt).

**Yardstick hierarchy note (2026-07-04):** the |t|>2 rolling-OLS statistician
is a PRACTICAL reference (fixed window, fixed alpha), not the optimum. The
true detectability ceiling is an exact-likelihood change-point analysis
(compare "one VAR" vs "VAR changed at tau" over all tau; family and sigma
known). Registered upgrade, implemented only if the LLM matches or beats the
rolling statistician — below that tier the optimal bound cannot change any
conclusion. Roles kept distinct: truth oracle = scoring; statistician =
attribution (model-vs-achievable split) + per-series detectability
certification (LLM latency is judged against certified-detectable latency,
not against t*).

## 15.1 Dynamic-arm scoop-check (adversarial lit review, 2026-07-04)

**Overall verdict: NOVEL, not scooped.** Seven threads searched (arXiv, ACL,
OpenReview, Semantic Scholar, Google Scholar, through 2026-07).

Thread verdicts: LLM causal discovery from time series OPEN (all static
graphs); LLM change-point detection CLOSE CALL; LLM belief
updating/perseveration CLOSE CALL; synthetic-truth forecasting benchmarks
OPEN; ICL of dynamical systems OPEN (trained transformers, not LLMs);
classical non-stationary CD = background cites only; LLM agents +
non-stationary world models OPEN.

**Biggest threat — arXiv:2604.16988 "In-Context Learning Under Regime
Change" (2026-04):** regime change in linear dynamical systems + adaptation
measurement, BUT trained time-series transformers (not prompted LLMs), only
forecast accuracy (no stated causal model, no dissociation, no exact-p*
dual scoring). Must cite and position against explicitly.
**Second threat — arXiv:2512.18489 "LLMs as Discounted Bayesian Filters"
(2024-12):** LLMs + exact synthetic truth + shifting parameters; fits a
forgetting discount factor. No causal structure ever elicited; parameter
shift, not structural change. (Their discount-factor fit is a natural
supplementary analysis for our forecast channel.)

**The wedge:** first design to score an LLM simultaneously on predictive
output (vs analytically exact regime-specific p*) AND stated structural
output (F1 vs both regimes' graphs + changed-slot state) — making the
forecasts-adapt-while-stated-graph-perseverates dissociation (D5)
measurable at all; the info ladder then attributes failures to structural
inertia vs change-unawareness.

**Must-cite (12):** 2604.16988 (closest prior); 2512.18489; 2509.23936
EvolveCast; 2601.02957 LLM-augmented changepoint; 2605.06527 STALE;
2410.16546 transformers-as-state-estimators; 2502.08136 ICL of LDS
(NeurIPS'25); CD-NOD (Huang, NeurIPS'20); DYNOTEARS (Pamfil'20); BOCPD
(Adams & MacKay'07); SPACETIME (2501.10235, AAAI'25); 2602.10282
Linear-LLM-SCM.

**Review caveat:** hand-search NeurIPS'25 / ICML'26 / ICLR'26 proceedings
before submission (very recent workshop papers may not be indexed).

## 15.2 Naturalistic transfer arm: real series, three context levels (parked pending the sandbox pilot)

The real-world counterpart of the dynamic arm, and the external-validity
bridge for the coupling question (§1). On real series a model's "causal
structure" is its LATENT world knowledge of the named quantity, so the
question becomes: is that stored knowledge coupled to the data — updated when
the series changes — or clung to when it is stale? The three context levels
instantiate this: L1 anonymous numbers = pattern extrapolation with no
structural knowledge engaged; L2 + identity = the model's stored structural
understanding activated; L3 + news = the information about what changed. The
sharp test is L2 on a post-cutoff-changed series: naming it should HELP if
prediction couples to an updated understanding, and HURT (drag toward the old
regime) if stored structure is stale and clung to — the real-world echo of the
sandbox's perseveration. All exact-truth causal claims still stay in the
sandbox; this arm is forecasts only, no graph elicitation (there is no ground
truth for the causal structure behind a real series, so a stated graph could
not be scored) — it tests the coupling question's shadow, not a second
exact-truth measurement.

**Design: 2 rows x 3 context levels (six situations).**
Rows — did the series change? Decided from the numbers alone (change-point
tests), never from the news. The no-change row is the modal state of the world
(most series most of the time do not change, and much news changes nothing),
and the two facts vary independently: a break can arrive without a clean story,
a big story without a break.
Columns — three context levels, each adding exactly one thing, so each
adjacent comparison prices one kind of knowledge in forecast accuracy:
- L1 numbers only (series unnamed) -> pure pattern extrapolation, read against
  simple statistical baselines we compute (full-history fit, recent-window
  fit); also the bridge to the sandbox, where series arrive as anonymous
  numbers, so sandbox-to-reality transfer of extrapolation is measured here.
- L2 + what the series is -> the value of the model's stored world knowledge
  about the named quantity.
- L3 + recent dated news -> the value of recent information on top of stored
  knowledge.
Two cells of note: no-change x L2 ("pulled by its priors") — the name
activates domain beliefs against numbers showing nothing changed; and the star
cell no-change x L3 — consequential-sounding news over unchanged data, i.e.
believing the story over the numbers.

**Sampling frame.** ForecastBench is a sampling frame only: keep the dataset
each question points to, drop the question. ~1,060 curated exogenous datasets
across five series-backed sources (yfinance 447 market prices, Wikipedia 338
page views, FRED 165 macro, ACLED 60 conflict counts, DBnomics 53 intl macro),
with qualitatively different break types (policy pivots, crashes, viral spikes,
escalations); domain is a covariate. The frame predates the hypothesis, which
kills the cherry-picked-series objection. We define our own events: tau at the
midpoint of the stale and updated reference forecasts (the sandbox
midpoint-tau trick), so each event maximally separates the two worlds. Scoring
is against realized values and the reference forecasts.

**Safeguards, both load-bearing.**
- Memorization: forecast targets are strictly post-cutoff — otherwise L2
  measures recall, not knowledge.
- Self-recognition: a famous series can be identifiable from raw values, so
  after every L1 answer the model is asked what it thinks the series was;
  recognized-series questions are analysed separately (their L1 was never
  anonymous). Recognition rates are themselves reportable.

**Novelty.** Neither numbers-only forecasting (Gruver et al. 2310.07820) nor
"does news improve accuracy" (AutoCast 2206.15474, Halawi 2402.18563, From News
to Forecast 2409.17515, EvolveCast 2509.23936, FutureSim 2605.15188) is new.
This arm's novelty: (a) the certified no-change row and star cell — absent
everywhere, because news benchmarks contain only events that happened; (b) the
within-model three-level decomposition, pricing the value of identity
separately from the value of news, under the post-cutoff and recognition
guards; (c) the paired-diagnostic transfer claim (sandbox behaviour predicts
real-data behaviour). Scoop-check on (b), anonymous-vs-named forecasting on raw
numeric series (2026-07-05): OPEN. No paper isolates series identity on raw
numbers; the closest, 2402.10835, bundles identity with descriptions and units
on pre-cutoff benchmarks with no recognition check (position against it);
named-vs-anonymous exists only on financial text (2511.15364, Entity Neutering
SSRN 5182756 — cite as precedent, not scoop); 2504.14765 motivates the
post-cutoff rule (LLMs reproduce exact pre-cutoff values of named indicators),
and 2505.10213 explicitly declined the naming comparison over leakage; the
self-recognition check appears novel. Must-cites: 2310.07820, 2410.18959 (CiK
context benchmark), 2402.10835, 2504.14765, 2511.15364, 2512.23847
(lookahead-bias vocabulary), SSRN 5182756, plus the six news-forecasting
papers.

**Interactive page:** knowable_worlds/explorer_news.html — the 2x3 grid, a
three-level live demo (with the self-recognition follow-up in the draft
prompt), a worked FRED effective-funds-rate example, the procedure, and the
literature positioning. Status: parked pending the sandbox pilot conclusions.

**Registered sandbox-presentation knobs (K1/K2)** — robustness checks for
the SANDBOX arm, listed here with the registered extensions. Each moves one
thing while keeping the exact truth oracle: (K1) semantic naming — replace
X1..X8 with plausible economic names (tests whether familiar vocabulary pulls
the model toward its priors; bridge to the discovery paper's
semantic-contamination finding); (K2) realistic texture — seasonality and
heavy-tailed noise in the generator (truth via Monte Carlo where non-Gaussian).

**Hierarchy decision (user, 2026-07-04): the dynamic arm IS the main
experiment.** The static ladder is retained as the supporting/mechanism
layer, not a co-equal experiment: (1) it is the interpretive key — dynamic
failures are ambiguous between can't-detect and can't-use without the static
use-results (perfect calculator at L3; cannot cash bare structure into
forecasts; trap-attraction); (2) the exactness claim ("remaining error is
reasoning, not arithmetic") is established there; (3) its data is already
paid for. Explorer restructured to match: dynamic arm = §1 ("The main
experiment"), static sections renumbered 2-7 behind a bridge card stating
their supporting role. Paper structure to mirror this: dynamic spine,
static mechanism section, real-world study (§15.2) as the transfer arm.

**Explorer restructured again 2026-07-06 (user directive): the page is now a
coherent dynamic study design, not an idea log.** Static sections removed from
explorer.html entirely (their registry stays here, §§5-14; the page closes
with a one-sentence pointer). New page structure: §1 the world that changes +
forecast channel (interactive demo, design-at-a-glance table, residual
monitor, yardstick tiers) · §2 the structure channel read through the REDUCED
EDGE SET — the changed slot + strength-matched controls; whole-graph F1
demoted to the "wrong lens" exhibit; the three v2 instruments (per-edge
probabilities, single-edge queries, changed-slot tracking) presented as the
primary measure, with first data · §3 multi-edge extension foregrounded
(k ∈ {1,3,6} interactive: detection-vs-attribution split, per-variable
residual-inflation bars) · §4 hidden-confounder world with a motivating
interactive (same value a asked three ways — see X1 / set X1 / set X3
gauges; natural-vs-intervened scatter showing the decoupling fingerprint) ·
§5 controls as a single what-it-rules-out table with run/partial/queued
status · §6 results (pilot D1-D5 registered predictions and verdicts merged
into one table; v2 unified sentence) · §7 ordered run queue. JS verified via
node stub DOM (all change types x checkpoints, k tabs, slider sweeps).

## 15.3 DYNAMIC PILOT RESULTS (GPT-OSS 120B, 12 scenarios, run 2026-07-04)

288/288 answers (zero parse failures after retries; ~2.5M tokens). Inference:
analyze_dynamic.R, scenario random intercepts; PROVISIONAL at n=12.

**D1 disruption — SUPPORTED.** post x affected interaction +0.177 (p=.0096);
controls flat (0.245 pre -> 0.290 post).
**D2 clinging then release — SUPPORTED.** Post-change answers sit closer to
the old rules than to truth (+0.378, p=.0003), releasing at -0.012/period
(p=.037) -> ~30 periods to break even; the |t|>2 statistician needs ~15.
At +2 the model is nearly ON the old-rules answer (d=0.104 vs d(truth)=0.486).
**D3 trails recency — SUPPORTED.** Post-change error exceeds the rolling-20
fit by +0.196 (p<.0001). Recovery curve: model 0.36/0.45/0.58/0.40/0.28 at
+2/+6/+10/+20/+35 vs rolling 0.32/0.35/0.18/0.13/0.12.
**D4 — MOOT (floor).** The stated graph is near-chance EVERYWHERE, including
pre-change with pure single-regime data: signed F1 ~0.15 flat, 5-7 edges
asserted of which ~1.5 correct and ~5 false (over-assertion, exactly the
discovery-paper signature). F1(new)-F1(old) post: +0.004 n.s.; changed-slot
migration n.s.; statistician on the same rows migrates 0.92 old -> 0.58-0.67
new by +20/+35 while the model stays flat at chance.
**D5 dissociation — CONFIRMED, predicted direction.** Forecasts adapt
(slowly); the stated causal model never moves because there is nothing there
to move: prediction without understanding. Coheres with the static arm
(cannot form/use structure, only execute it) and the discovery paper
(cannot build a graph from data; over-asserts).

Artifacts: outputs/dynamic_gptoss (results.jsonl, dyn_master.csv,
dyn_structure.csv, dynamic_tracking.png via gen_dynamic_figures.py); pilot
results card embedded in explorer.html §1. Next decisions per registered
rules: forecasts DID move post-change -> change-magnitude axis stays a
supplement; structure floor -> the informative escalation is the info ladder
(D-L1: does "may have changed" unlock anything?) and/or more capable models.

**§15.3 addendum — graph churn (2026-07-04).** The stated network is not a
stable wrong model; there is NO persistent model: mean edge overlap between
consecutive answers (Jaccard) = 0.09 run-wide, despite only 5-15 new rows
arriving between checkpoints (sign_flip_300: 27 distinct edges asserted
across 8 answers averaging 5.6 each). The model redraws a fresh
typical-density graph every time it is asked. Consequence: cross-checkpoint
change metrics are floor-bound not because beliefs fail to update but
because there are no beliefs to update — strengthens the "graph-shaped
answer, not inference" reading. Figure: gen_network_evolution.py ->
outputs/dynamic_gptoss/network_evolution_sign_flip_300.png (per-checkpoint
mini-graphs + edge-persistence stripes).

**§15.3 addendum 2 — churn interpretation + registered controls.** Honest
framing: checkpoints are independent calls (the model never sees its prior
graph), so persistence could only arrive THROUGH the data — consecutive
checkpoints share 80-95% of rows, so any evidence-driven procedure answers
nearly identically twice (the statistician does). Jaccard 0.09 therefore
means the stated graphs are barely functions of the data (kills the
stable-but-wrong-beliefs alternative; converts "F1 low" into "nothing
there"). External value = methods warning: single-sample LLM
causal-discovery benchmarks substantially measure decoding noise.
Registered controls (cheap, not yet run): (C-a) resample the SAME checkpoint
k times — same-prompt Jaccard vs cross-checkpoint Jaccard splits sampling
noise from data-driven change; (C-b) temperature 0 across checkpoints — if a
stable graph appears, deterministic "beliefs" exist and D4 can be re-asked
of them.

**§15.3 addendum 3 (user, 2026-07-05) — control C-c registered: no-change
scenarios.** Distinction clarified: C-a (same-prompt resampling) and C-b
(temperature 0) measure RELIABILITY — does the instrument return the same
graph under identical conditions — which must precede any validity claim
("its causal model did not update"). C-c is the user's reading, a separate
missing control: scenarios with NO change at all (full 95 periods of one
regime, all 8 checkpoints, 3 seeds). Buys (1) asymptotic structure accuracy
— with maximal stable data, does the stated graph ever converge (pilot hint:
F1 flat 30->55 rows; 95 is the fair test) — and (2) the forecast channel's
false-alarm floor over a full-length quiet world — the sandbox analog of
the real-world design's no-break row, same logic, same necessity. Current
design has zero change-free scenarios; every scenario changes at t*=60.

## 15.4 Third scoop-check (2026-07-05): direction re-verified + v2 elements

**JOB A — comparative claim RE-CONFIRMED as of 2026-07:** LLM tracking of
non-stationary causal structure from numeric series with dual
forecast+structure scoring remains effectively empty. Strongest new
counterexample: arXiv:2605.30363 (regime-shift detection via LLM reasoning
over central-bank TEXT + macro panel; F1 vs an empirical anchor list) —
does not cross the key lines (numeric-only data, analytical truth,
structure scoring). Also new & must-position: arXiv:2603.11090
CausalTimePrior (regime-switching synthetic TSCM used to TRAIN causal
foundation models — PFNs, not prompted LLMs).

**JOB B — v2 elements:**
B1 per-edge probabilities: CLOSE CALL — Sekulovski et al. (BJMSP 2026)
elicit per-edge inclusion probabilities from LLMs as Bayesian PRIORS for
static psychological networks. Our wedge: posterior beliefs scored as
probabilities against exact truth, in a dynamic world, tracked across
checkpoints. Position explicitly.
B2 belief carryover: OPEN — closest (arXiv:2506.16234) has the statistical
engine, not the LLM, do the revising; the hand-back design (state G1 ->
new data -> revise -> score vs exact G2, latency measured) is absent.
B3 hidden confounder + natural experiments: OPEN — all prior work is
domain-knowledge or text-based (VIGOR+ 2512.19349, ProCI, IV Co-Scientist
2602.07943, InterveneBench); nobody hands LLMs numeric data with labeled
interventions and tests exploitation.
B4 policy-rule change / Lucas critique: OPEN — entirely absent from LLM
evaluation.
Must-cite additions: Sekulovski BJMSP'26; 2506.16234; 2603.11090;
2605.30363; 2512.19349; 2602.07943.

## 16. CAUSAL-NECESSITY FOCUS (user directive, 2026-07-04)

**"Focus on questions that REQUIRE knowing causal structure. If the answer
can be reached by extrapolating data trends, it is less interesting."**

Static arm — PRIMARY outcome redefined as the causal-required subset, where
the best data-only answer is certifiably wrong: (a) confounded interventional
items (admitted only with ident_gap >= 0.15: the conditioning answer provably
differs from truth) and (b) counterfactual items (midpoint-tau design:
reusing the factual outcome is provably wrong). DEMOTED to ability controls:
observational items (answerable by counting rows) and root-do items (for
roots, conditioning EQUALS intervening — no causal knowledge required). The
controls stay in the battery: they establish the model can read data, which
is what makes primary-cell failures attributable. analyze_calibration.py
gains a CAUSAL-REQUIRED primary table; scale-up hypotheses H2/H6 are the
primary hypotheses, H1/H5 supporting.

Dynamic arm — honesty note: in a fully-observed lag-1 world, every one-step
forecast is answerable in principle by regression (the rolling-window
baseline solves the task with zero causal knowledge). The observational
dynamic arm therefore measures TRACKING/UPDATING, not causal necessity. The
fix — a hidden variable that confounds the observed ones so data-only fits
are systematically wrong on intervention items — is BUILT as the
hidden-confounder world (§16.3), realized via see-vs-do forecasts; it is the
causal core of the paper.

Real-world arm — the analogous split: trend questions are extrapolation;
causally-required real questions are intervention-conditional ("given the
Fed cuts in March, P(...)"), resolvable only when the condition realizes
(Metaculus-style conditional questions). Noted for the parked design.

**§16 addendum — K3 verbal encoding (user question, 2026-07-04).** Registered
knob: re-encode the table as text. DISCIPLINE: the variant must be
information-equivalent — level (b) row narration ("In period 37, X1 was 2.1,
X2 was -0.4, ...") only. Excluded: change narration ("X5 rose, then X2
fell") = preprocessing; relationship narration = handing over the answer.
Prediction (registered): (b) does NOT rescue structure F1 — the pilot
failure is conditional inference, not perception (static arm: counts tables
to 0.003 of empirical frequency; tracks shown noise at 0.93; GPT-OSS
already narrates internally via hidden CoT). Value = kills the
"LLMs can't read number grids" reviewer objection; ~24 calls/encoding on a
3-scenario structure-item subset. FRAMING: encoding (numeric|verbal) x
semantics (abstract|named, =K1) is a 2x2 of presentation; pilot = (numeric,
abstract) -> nothing; paper 1 = (verbal, semantic) -> plausible DAGs. The
off-diagonal cells identify which factor manufactures apparent LLM causal
competence.

**§16 addendum 2 — incentivized structure elicitation (user question,
2026-07-05).** The pilot's structure channel has no stakes, so F1=0.15 is
ambiguous between no-beliefs and liberal-reporting. Three registered
payoff variants, in order of value:
(I1) scoring rule in the prompt: +1 correct signed edge, -1 false, 0
omitted, empty list allowed -> defines the optimal report (assert iff
P>0.5). Outcomes both informative: pruning/abstention = meta-knowledge
without knowledge (floor partly policy); continued spraying = no beliefs
AND no self-calibration.
(I2) PER-EDGE PROBABILITIES scored by Brier — the preferred variant:
structure recovery becomes true calibration itself (each edge-belief is a
probability with exact 0/1 truth; no thresholds, maximal sensitivity;
change-tracking = P(changed edge) migrating after t*). If all pairs sit at
~base rate, no-beliefs is established with full authority.
(I3) feedback arm: model sees its previous graph's score each checkpoint —
the only variant where payoff can drive LEARNING; sequential conversation,
own arm (context-growth confounds; directly probes the discovery paper's
never-prunes finding under scoring).
Registered prediction: I1/I2 do not raise accuracy (churn shows beliefs are
re-invented per call — you cannot report calibrated beliefs you do not
retain); they characterize the floor. I3 open.

**§16 addendum 3 (user, 2026-07-05) — I3 RETIRED; prediction-sufficient
incentive registered.** I3 (graph-score feedback) retired: ecologically
invalid — reality never grades causal models directly, only forecasts. I2
(per-edge probabilities, Brier-scored) promoted to planned.

> The hidden-confounder world sketched in this addendum and addendum 4 is
> **now BUILT (§16.3)**, in a cleaner see-vs-do form (a forecast is asked
> under "you observe A=a" vs "A is set to a"; the two diverge only for a
> model with the causal structure). The S1/S2/S3 learn-from-intervened-rows
> account below is the mechanism it operationalizes; the exogeneity ladder
> (addendum 5) and policy-rule-change synthesis (addendum 6) remain the
> future extensions.

NEW REGISTERED VARIANT — hidden-confounder world with announced
interventions ("forecast payoff is the only incentive"):
(1) one variable is generated but never shown (hidden column); it drives
two or more observed variables (a genuine unobserved common cause).
(2) Ordinary forecasting stays statistically solvable (a fit to observed
history absorbs the latent traces) — honesty note: passive prediction never
forces causal reasoning, observed or not.
(3) The causal necessity enters through INTERVENTION EVENTS EMBEDDED IN THE
WORLD: at announced periods the series shows an external control action
("period 71: X3 set to 4.0"); the model forecasts the consequences; the
simulated outcome realizes; Brier vs the realized value is the ENTIRE
payoff. For confounded pairs the conditioning answer is certifiably wrong
(ident-gap certification transplanted to the dynamic setting; oracle pair =
best-observational-fit answer vs true interventional answer), so the only
route to forecast payoff runs through the causal model — including positing
the unseen variable.
(4) Pairs with I2: add one elicited probability "P(an unobserved common
cause links Xi and Xj)" — exact truth exists.
Ecological rationale (user): real forecasters get outcome feedback only;
this design makes that feedback sufficient to demand causal reasoning.

**§16 addendum 4 — how the causal reasoning is actually testable in the
hidden-confounder world (mechanism spec).** The agent's only valid path:
(S1) notice the history contains two kinds of rows — natural and announced
control events (natural experiments); (S2) detect confounding as the
signature "the X3-X5 association holds in natural rows and evaporates in
intervened rows" (an unobserved common cause, testified by the world's own
history); (S3) answer do-questions from the intervened subset, refusing to
import the natural co-movement. Each step measured separately: oracle pair
= pooled-fit (observational) vs intervened-rows-only fit (experimental) vs
exact truth — the model's answer locates its epistemology; the elicited
"P(unobserved common cause linking Xi,Xj)" (exact 0/1 truth) tests S2
explicitly; S1 failure is detectable as tracking the pooled fit even where
the row types disagree loudly. DESIGN PARAMETER: history must contain
enough past control events (~5-10 on the relevant variable) that the
experimental oracle is competent and the pooled-vs-experimental gap is
certifiable per item — otherwise the data, not the model, is being
measured. Parallel: paper 2 made the model CHOOSE experiments; this makes
it USE experiments history already ran — the natural-experiments skill of
real forecasters.

**§16 addendum 5 (user question, 2026-07-05) — how does the model know what
is exogenous? The exogeneity ladder.** In the registered design it is TOLD:
control events are announced in the series (deliberate rung choice —
separates USING exogeneity from DETECTING it; static-arm evidence shows
labels often are not operationalized, e.g. "severed" stated in the prompt
yet the conditioning answer given, so labeled-first is the right order).
Registered harder rungs:
(E-1) labeled interventions (the base design).
(E-2) unlabeled interventions — detectable in principle as extreme one-step
residuals (set values break the usual dynamics; same change-point
machinery); tests FINDING natural experiments.
(E-3) announced-but-ENDOGENOUS interventions — the identification problem:
two event types, policy SHOCKS (values set at random; truly exogenous) vs
policy RULES (controller sets X3 as a function of observed state; announced,
external, still confounded because the assignment inherits the state's
confounding). Correctness requires reasoning about the assignment
mechanism, not the label. Exact truth computable for both event types.
Real-world relevance: actual announced interventions (Fed cuts) are
rule-like, not shock-like — E-3 measures in advance whether a model that
passes E-1 would still be wrong about reality.

**§16 addendum 6 (user cohesion question, 2026-07-05) — the synthesis
variant (v2-S, the POLICY-RULE-CHANGE world; provenance: the Lucas
critique — fitted relationships are partly products of the policy in force,
and break when the policy changes even though the mechanisms do not).** Honest tension acknowledged: tracking
(the study's origin — non-stationarity) and necessity (hidden confounding /
identification) are separable axes sharing an engine. The synthesis fuses
them: THE THING THAT CHANGES AT t* IS THE ASSIGNMENT MECHANISM. Pre-change,
X3 is set by a policy rule responding to the state (observational
association reliable; pattern-matching forecasts well). At t* the rule
changes (or becomes shocks). Every reduced-form fit learned pre-change
breaks — not the physics, but WHY values take their values — and only an
agent holding the causal decomposition forecasts correctly post-change;
the recency-fitter relearns slowly, the pooled fitter never recovers. This
is the Lucas critique with exact truth attached, and it makes detection and
necessity the same act: what changed is exactly the thing only a causal
model represents. Status: the natural flagship if the separate v2 pieces
(per-edge probabilities; hidden-confounder E-1) both behave; run the pieces
first, synthesize second.

**§16 addendum 7 (user, 2026-07-05) — belief carryover registered (P1/P2).**
The pilot's independent calls gave persistence no channel except the data;
carrying the stated model forward ("here is your current causal model +
data incl. N new periods; restate or revise") gives beliefs an existence
and converts the floored structure channel into a REVISION channel.
(P1) self-seeded: initial belief = the model's own first elicitation;
measures persistence/updating of its own beliefs.
(P2) TRUE-PRIOR seeded: initial belief = the correct regime-1 graph —
removes formation (known-failed) and isolates maintenance/revision: "you
hold a correct model; the world changes; do you notice and repair?" — the
study's original question, deconfounded, and the dynamic continuation of
static L1/L2 (given structure).
Measures: edit operations vs own prior (keep/drop/add), revision timing vs
t*, changed-slot repair, stickiness (copying under no evidence) vs
responsiveness (revision under evidence). With per-edge probabilities as
the carried belief, the exact Bayesian update per checkpoint is COMPUTABLE
-> over/under-updating scored against truth. Known risk: prompt-deference
(parroting the prior) — self-identifying post-change as belief-level
clinging via the D2 machinery. Supersedes churn ambiguity: consistency
becomes trivially available, so the measurement flips to appropriateness
of revision.

## 16.1 V2 RESULTS (GPT-OSS, run 2026-07-05; I2/P2/C-c complete, C-b 62/96,
C-a 13/160 — credits exhausted; scale-up at 771/4800)

**I2 (probabilities, no prior): the no-beliefs verdict, with full
authority.** Brier 0.22-0.24 at every checkpoint — WORSE than answering the
base rate (0.19) everywhere; discrimination (mean p on true edges minus
non-edges) ~= 0 (+-0.01). The registered prediction held: edge beliefs
carry zero information about the graph.

**P2 (true-prior carryover): it can HOLD a causal model, but cannot REVISE
one.** (1) Persistence works when scaffolded: Brier 0.009 at first
checkpoint, discrimination +0.81; departure from prior grows only 0.016 ->
0.102 across 8 sequential revisions. (2) But the drift is INDISCRIMINATE
EROSION, not updating: Brier worsens monotonically (0.009 -> 0.049)
INCLUDING pre-change; the prior blurs uniformly toward the middle. (3) The
changed slot is never repaired: should-rise slots go 0.07 -> 0.10;
should-fall slots 0.90 -> 0.77; still-present slots also drift down 0.89 ->
0.75 — the same gentle erosion in all three cases REGARDLESS of what the
data says. Zero evidence contact. (4) Forecasts improved somewhat with the
carried prior (d(truth) 0.479 -> 0.374) but remain closer to the old rules
(0.341) — unsurprising: the carried prior IS the old-rules graph.

**C-c (no-change worlds): no convergence, ever.** Signed F1 wobbles
0.06-0.28 with no trend across 95 stable periods; quiet-world forecast
error 0.227 (the noise floor).

**C-b (T=0): the churn is NOT sampling temperature.** Deterministic
decoding still gives consecutive-checkpoint Jaccard 0.11 (vs 0.09 at
T=0.7): 5-15 new rows completely rewire the deterministic output. No stable
beliefs exist even without sampling noise.

**C-a (partial, 13/160): same prompt, different graphs** — within-prompt
Jaccard 0.08.

**The unified sentence:** LLM causal "beliefs" are prompt-echoes — they
persist only if handed back, decay uniformly when they are, and never touch
the data. Formation fails (I2, C-c), retention fails without scaffolding
(C-a, C-b), and revision fails even with a correct scaffold (P2). The one
positive: the scaffold is respected (P2 Brier 0.009-0.049 vs 0.22 without),
so downstream USE of a maintained model is possible — consistent with the
static arm (executes given knowledge; cannot form or revise it).

**§16.1 addendum — clarification (user, 2026-07-05): the carryover idea as
originally intended is P1 (carry the model's OWN estimate forward); P2
(true prior) was the experimenter's addition, run first to isolate revision
from formation. P1 implemented (--carry-belief self: first structure answer
becomes the first belief) and QUEUED as the first run on next credit
top-up. Sharp predictions from I2+P2: the self-carried belief will be
respected (persistence of its own noise — scaffolded self-consistency
should collapse the churn) but will not move toward the truth with data
(P2 showed zero evidence contact even from a correct prior). P1 completes
the prior-quality axis: none (I2) / own (P1) / true (P2).**

**§16.1 addendum 2 — dynamic use-ceiling registered (2026-07-05).** Missing
attribution link exposed by P2: hand the model the full CURRENT equations at
each checkpoint (the moving-world analog of static L3). Static arm shows
perfect execution of given equations in a still world; confirming it
mid-regime-change completes the chain — every dynamic failure then provably
lives in detection/revision, never in use. Cheap (existing info-ladder
machinery extended one rung: info-level "equations"). Priority tiers for
remaining work recorded in session notes: T1 multi-model replication of the
core battery + P1 + scale-up completion + more seeds; T2 K1/K3/D-L1 +
use-ceiling (the three deflationary objections + attribution); T3 E-1 ->
policy-rule-change + I1; T4 naturalistic 2x3. Human baseline: default
position = the statistician yardstick IS the idealized human-with-tools;
small human pilot optional.

**§16.1 addendum 3 — incentives: status + I1 implemented (2026-07-05).**
User question: has incentivized causal inference been tested? NO — all
completed runs were stakes-free. I1 now implemented (run_dynamic --stakes):
list format gets +1/-1/0 scoring language with abstention allowed; probs
format gets an explicit squared-error scoring statement. QUEUED with P1 for
next credits (structure-only rerun, ~96 calls per format). Registered
prediction: stakes shift the REPORTING POLICY (fewer asserted edges /
probabilities pulled toward honest uncertainty), not accuracy — incentives
cannot create inference, only honest reporting of what exists. Outcomes
both informative: pruning under penalty = knows-it-doesn't-know; continued
spraying = no beliefs and no self-knowledge. The deep incentive test
(forecast-payoff-only, hidden-confounder world) remains Tier 3.

## 16.2 REASONING-MODEL PROBE + SINGLE-EDGE QUERIES (2026-07-05, partial — credits)

**Question (user)**: is the structure-formation floor a model-specific
limitation? Test with an open reasoning model. Chosen:
qwen/qwen3-235b-a22b-thinking-2507 — matched pair with the paper-1 roster's
qwen3-235b-a22b-2507 (same weights family, thinking on vs off, one
manipulated variable). Runner support added: run_dynamic --max-tokens
(thinking counts against the OpenRouter cap; 16k truncates — forecast items
alone think ~15.8k tokens) and --timeout.

**Structure pass, 15/96 items before credits ran out**
(knowable_worlds/outputs/dynamic_qwen_thinking, seeds/scenarios identical to the
GPT-OSS pilot):
- Signed F1 ~0.19 (0.09–0.29, no trend) vs GPT-OSS 0.15 — the floor SURVIVES
  ~16k+ tokens of chain-of-thought per answer.
- Consecutive-checkpoint Jaccard 0.13 vs 0.09 — the churn survives too.
- One real difference: asserts 6.5 edges/answer vs ~10 (conservatism, not
  competence — the fewer edges are barely more correct).
- Cost: ~$0.18–0.28/item vs ~$0.003 (GPT-OSS): ~100x compute, no floor move.

**Single-edge queries (user idea, same day): one call, one candidate
influence** — the decomposition test. Whole-graph elicitation asks the model
to manage 56 hypotheses at once; a single-edge call spends its entire budget
on ONE pair, exactly the statistician's decomposition (one t-test per pair).
Separates two readings of the floor: task-management failure (single-edge
discrimination > 0) vs inability to extract a lagged pairwise association at
all (single-edge ~ 0 too). Implemented: knowable_worlds/run_single_edge.py.
Deck stacked pro-model: the 5 true edges asked are the MOST detectable on
the shown window (OLS |t| 3.6–5.3), the 5 non-edges the most cleanly absent
(|t| 0.1–0.2); an idealized analyst scores 10/10. Scenario edge_add_300,
checkpoint 55 (single-regime formation, most data).

**GPT-OSS result (complete)**: mean p(true edges) 0.46 vs p(non-edges) 0.37
— discrimination +0.09, ~chance. Gave |t|=3.7 and 3.6 true edges p=0.15 and
a |t|=0.2 noise pair p=0.75. VERDICT for GPT-OSS: the floor is NOT
task management — it cannot detect even one maximally detectable lagged
association with its entire answer devoted to it. Strongest form yet of the
formation failure; slots directly into the prompt-echoes account (beliefs
never touch the data because the data is never actually computed on).

**Qwen-thinking result (2/10 before 402)**: X6->X8 (strongest true, |t|=5.3)
p=0.95 — correct and confident (GPT-OSS: 0.78); X6->X1 (true, |t|=4.8)
p=0.25 — miss. Too few to score. RESUME-SAFE: rerun the same command to
finish the remaining 8 pairs (~$0.5).

**Registered interpretation rule (set before completing Qwen)**: if
Qwen-thinking discriminates (>= +0.3) on single edges while its whole-graph
F1 stays at the floor, the story is compute-allocation (reasoning can run
the mini-regression when pointed at one pair, but cannot budget 56 of them
in one answer). If it fails single edges too, formation is dead even at
maximal focus and compute, for both model classes.

**Queue effect**: single-edge completion (Qwen 8 pairs) jumps to the FRONT
of the next-credits queue (cheapest, sharpest); then P1 + I1, then the
Qwen-thinking structure pass (81 items, ~$15–25 at observed burn — decide
after single-edge verdict whether it is worth it), then the rest of T1.

## 16.2 DECISION-RULE OUTCOME (Qwen single-edge completed 2026-07-07)

Qwen3-235B-thinking, all 10 formation pairs (8 new + 2 from 2026-07-05):
mean p on true edges 0.77 vs 0.32 on non-edges — **discrimination +0.45**
(GPT-OSS on the identical pairs: +0.09, chance). Four of five true edges at
0.85-0.95; errors were one true-edge miss (0.25) and one false alarm (0.85).

Per the registered rule, the whole-graph structure floor is a
**compute-allocation story**: a reasoning model with its entire budget on
one pair CAN extract a lagged pairwise association from the rendered
series; its whole-graph answers sit at the same floor as GPT-OSS
(F1 0.19 vs 0.15) because the capability does not survive being spread
across 56 hypotheses. For the non-reasoning class, formation is dead even
at maximal focus. Consequences: (1) the "revision dead" claim narrows to
"revision does not survive hypothesis load; at single-pair focus reasoning
models form and GPT-OSS partially tracks (add.4)"; (2) the registered
follow-on decision — completing Qwen's whole-graph structure pass (81
items, ~$15-25) — is now live, since the floor-vs-allocation contrast is
the story it would sharpen. Caveat: this run predates the json_repairs
counter; any 4o-mini involvement would have been extraction-only (verified
deterministic {} on empty input, which cannot pass validation).

## 16.2 addendum — single-edge TRACKING mode (user idea, 2026-07-05)

Formation mode (above) probes ONE pre-change checkpoint with the most-
detectable edges — it asks "can the model form the association at all?" User
proposal sharpens it to the change-tracking question: ask about the ONE edge
that changes at t*, across every checkpoint spanning the change, next to a
few controls that never change. Read = difference-in-differences at the
single-edge level: does the changed edge's stated existence-probability move
across t* while controls stay flat, with the whole answer budget on one pair
per call (no "56 hypotheses" excuse)?

Implemented: run_single_edge.py --mode tracking. Per scenario, 4 edges x 8
checkpoints = 32 calls:
  changed edge  (the add/remove slot; add -> p should RISE, remove -> FALL)
  2x ctrl_true  (present in BOTH regimes, strength-matched to the changed
                 edge so "strong => high p" cannot masquerade as tracking)
  1x ctrl_false (absent in both regimes -> p should stay low, flat)
Restricted to edge_add / edge_remove: the probe asks about EXISTENCE, so
sign_flip / weight_double leave the answer unchanged (they are existence-null
and make natural whole-graph-only tests). Runner prints pre/post means, per-
role delta, and the changed-minus-control DiD with the expected direction.
(Restriction removed 2026-07-06 — addendum 3 below: the probe now elicits
present + positive-if-present, covering all four change types.)

Detectability gate (offline check, seeds 300-302): the changed edge must be
statistically visible post-change or the model can't be blamed. Post-change
|t| on the late window:
  edge_add:    301 |t|=2.8, 302 |t|=3.3  DETECTABLE;  300 |t|=1.7 (weak)
  edge_remove: 301 |t|=4.1, 302 |t|=3.0  DETECTABLE;  300 |t|=1.0 (weak)
Headline scenarios = {edge_add, edge_remove} x {301, 302} (4 scenarios, 128
calls, ~$0.40 GPT-OSS / ~$3-15 Qwen-thinking). The two weak (300) scenarios
double as over-claim controls: an undetectable change SHOULD produce no
movement; if the model moves the "changed" edge there, that is fabrication,
not tracking.

Predicted outcomes and their readings:
  DiD ~ 0 (changed edge flat like controls)  -> no tracking even at maximal
    single-pair focus: revision is dead, matching P2 (uniform erosion,
    changed slot never repaired) and the prompt-echoes account.
  DiD clearly signed the right way, controls flat -> single-edge tracking
    EXISTS; the whole-graph revision failure is a capacity/attention limit,
    not an inability to detect a change per se. Would meaningfully soften the
    "revision dead" claim and reframe it as "revision doesn't survive the
    56-hypothesis load."
Either way it pins down where in the pipeline revision breaks. QUEUED
alongside formation-completion (Qwen 8 pairs) as the cheapest, sharpest next
runs.

## 16.2 addendum 2 — multi-edge simultaneous change IMPLEMENTED (user, 2026-07-05)

The change-magnitude axis (§ above, "Change-magnitude axis", registered
2026-07-03 as k in {1,3,6}) is now built. User re-raised it; its value is
reframed by the pilot findings from a bare magnitude dose to a
DETECTION-vs-ATTRIBUTION dissociation dose:
- more edges changing at once -> LARGER aggregate perturbation of the series
  -> "something changed" is EASIER to detect (forecast DV moves more);
- BUT the model must localize WHICH of k relationships moved -> attribution
  HARDER. The registered D5 dissociation (forecasts adapt, structure never
  does) should therefore WIDEN with k. That is a dose-response on the
  dissociation itself, not just on detection latency — a sharper use of the
  axis, and the realistic case (real regime shifts / policy changes move
  several coefficients at once; single-edge is the clean lab idealization,
  cf. the Lucas / policy-rule-change synthesis).

Implementation:
- dyn_engine.DynSCM(n_changes=k): applies k changes sequentially onto B2,
  each rejecting spectral destabilizers (radius >= 0.95). Exposes
  changed_edges (list); changed_edge = changed_edges[0] kept for back-compat
  so every existing single-edge consumer is untouched.
- REPRODUCIBILITY GUARANTEE (verified): n_changes=1 consumes rng in the same
  order as the old single-change code, so B2 is byte-identical for all change
  types x seeds 300-302. All prior single-edge outputs remain valid.
- NESTED sets (verified): because selection uses one shuffled permutation and
  takes the first k stable candidates, the k=1 set ⊂ k=3 set ⊂ k=6 set. k is
  a clean nested dose — each larger k adds edges on top of the smaller set,
  no confound from a different draw.
- Stability (verified): k=3 and k=6 stay < 0.95 for edge_add/edge_remove on
  seeds 301/302 (removes actually LOWER radius; adds raise it, k=6 edge_add
  ~0.91-0.94 — near the ceiling but accepted).
- dyn_battery: affected = union of changed children (one forecast item per
  changed child; controls = the rest; guard for the no-controls edge case).
  k=1 reproduces the single-affected-node battery exactly.
- run_dynamic --n-changes k (scenario tag "{ct}x{k}_{seed}"); n_changes
  stored per row. run_single_edge --mode tracking --n-changes k: every
  changed edge becomes a 'changed' probe, controls strength-matched to the
  MEAN changed magnitude; the DiD pools all changed edges vs controls, and
  PARTIAL attribution (tracks some changed edges, misses others) is newly
  visible per-edge.
- All world-reconstruction sites (analyze_dynamic, analyze_v2,
  gen_network_evolution) now read n_changes from the row (default 1).

Restricted like single-edge tracking to edge_add/edge_remove for the
existence probe; the forecast battery accepts all change types at any k.
Detectability caveat carries over: with k edges, some may be individually
undetectable even if the aggregate is obvious — per-edge post-change |t|
should be reported so misses on undetectable members are not counted as
attribution failures.

Predicted reads:
- forecast disruption rises with k (bigger perturbation) AND per-edge changed
  recovery stays at floor -> the dissociation widens: "detects more, explains
  no better". The cleanest single demonstration of prediction-without-
  understanding scaling with the size of the change.
- if instead changed-edge tracking IMPROVES with k (aggregate signal lifts
  attribution) -> revision is signal-limited, not absent; would refine the
  prompt-echoes account.
QUEUED after the k=1 formation/tracking runs (establish the single-edge
baseline first, then the k dose): edge_add/remove x seeds 301/302 x k in
{1,3,6}. Cheap on GPT-OSS (each k=3 tracking scenario = 6 edges x 8 ckpts =
48 calls; k=6 = 9 edges x 8 = 72).

## 16.2 addendum 3 — structure question COLLAPSED to tracked per-edge
## probabilities (user decision, 2026-07-06)

The three structure formats (whole-graph per-edge probabilities, single-edge
formation queries, changed-edge tracking) are one question at three scopes.
Collapsed: **tracking IS the structure question of the main battery.** At
every checkpoint, for the changed edge(s) + strength-matched controls, one
pair per call, the model states TWO probabilities: that the influence is
PRESENT, and that it is POSITIVE if present. Implemented in
run_single_edge.py --mode tracking (SYSTEM_TRACK, render_question_track,
ask_two); rows record truth_present, truth_positive, and t_roll20 (the
rolling-20 |t| on the pair — the statistician's confidence, free to compute).

This covers ALL FOUR change types — the key insight (user): a doubled weight
does not change the edge's 0/1 truth, but it doubles the evidence, so a
calibrated P(present) should CLIMB after t*. Predicted signatures:
  edge_add       P(present) low -> high
  edge_remove    P(present) high -> low
  sign_flip      P(present) stays high; P(positive) crosses 0.5
  weight_double  P(present) rises (same truth, sharper evidence)
D4's "a doubled weight is invisible to qualitative reports" was a limitation
of the edge-LIST format, not of the question; forecasts remain the primary
magnitude channel, tracking adds a confidence read on it.

Caveats registered: (1) ceiling — no headroom if pre-change P(present) is
already ~1; mitigated because pre-change weights (0.25-0.45) are only
moderately supported by a 20-row window (seed 300 weight_double: roll-20 |t|
0.8 pre -> 2.5 post — ample headroom). (2) Admission rule for weight_double
scenarios: the statistician's own confidence gap (mean post-t* minus pre-t*
rolling-20 |t| on the changed edge) must be clearly positive (>= 1.5);
runner prints the certification line. (3) The "you asked about this pair"
hint is neutralized by the matched controls receiving the identical hint —
DiD nets it out.

Roles of the other two formats, going forward:
  - whole-graph per-edge probabilities: retained ONLY as the belief object
    the carryover/revision experiments hand back (uniform-erosion measurement
    needs many should-stay edges); no longer part of the main battery.
  - single-edge formation: a diagnostic, retiring after the queued Qwen run
    resolves its registered decision rule (discriminates -> floor is compute
    allocation; fails -> formation dead at maximal focus).
Churn and false-alarm rates, previously read off whole-graph answers, are
now read as instability of stated probabilities on control edges, pooled
across scenarios.

## 16.2 addendum 4 — first live tracking runs; parser + prompt hardening
## (2026-07-07)

First four certified tracking scenarios ran live (GPT-OSS, edge_add/
edge_remove x seeds 301/302; 100% call success). FIRST DATA, pre-fix prompt
(archived at outputs/single_edge/pre_promptfix_20260707/): the changed edge
moved the RIGHT way in 3/4 scenarios — pooled DiD edge_add +0.15,
edge_remove -0.18, controls ~flat. Per the registered decision rule this
reads as: single-edge belief revision EXISTS at maximal focus; the
whole-graph failure is a capacity/attention limit, not detection inability.
Provisional (n=2 per type; magnitudes small vs the statistician's ~0->1).

Serving quirk found and fixed: GPT-OSS sometimes returns an EMPTY content
field (answer never leaves the reasoning channel; ~20-60% of calls depending
on provider). The old parser then sent the empty string to the GPT-4o-mini
JSON-repair fallback — which deterministically returns {} for empty input,
so the recorded data is CLEAN (verified: repairs logged, all on empty input;
{} lacks "present" so every such call was retried and only genuine answers
were recorded). Fixes: (1) parse_json_response no longer invokes repair on
empty text and now tries every balanced-brace candidate (last first) before
falling back; repair invocations are counted in every run's printed API
stats ("json_repairs"). (2) SYSTEM_TRACK v2 appends: "Keep any deliberation
brief, and always end your reply with the JSON object — never send an empty
reply." All four scenarios re-run under the v2 prompt so the tracking
dataset is prompt-uniform; other runners' prompts left unchanged
(comparability with completed data; retries absorb empties there).

## 16.2 addendum 5 — Qwen tracking, first scenario (2026-07-07)

Qwen3-235B-thinking, tracking mode, edge_remove seed 302 (GPT-OSS's cleanest
scenario). Changed-edge trajectory: P(present) 0.95/0.85/0.95 pre-change ->
0.85 at ck62 and PINNED at 0.85 through ck80 (20 periods of contradicting
data) -> 0.65 at ck95. Right-signed DiD -0.16, but dominated by perseverance;
ctrl_true beliefs simultaneously DRIFTED UP +0.20. Reading: the reasoning
model FORMS confident correct edge beliefs (unlike GPT-OSS) and then barely
revises them — the same slow-release profile as the forecast channel's D2
(release ~2x slower than the statistician). The dissociation therefore does
not reduce to "no beliefs to revise": revision lags evidence even when the
belief demonstrably exists, at maximal single-pair focus. n=1 scenario,
provisional; remaining three certified scenarios are the obvious extension
(~$20 at thinking budgets). Zero json_repairs across 21 reasoning-heavy
calls — the 16.2-add.4 parser fix fully absorbs reasoning-wrapped output.

Llama-3.1-8B on the identical scenario completes the ladder downward: ~0.1-0.25
on EVERYTHING (including 0.10 on always-present real controls), sawtooth
churn between calls, DiD +0.03 (null). Three tiers on one scenario:
no beliefs (8B) -> weak directional beliefs (GPT-OSS 120B) -> strong correct
beliefs, barely revised (Qwen-235B thinking). Figure:
outputs/single_edge/qwen_perseverance.png (gen_single_edge_figures.py).

Llama-8B FULL FORECAST battery (192 calls, outputs/dynamic_llama,
2026-07-08): corr(p, p*) = -0.05 overall (post-change -0.16); answers
cluster ~0.62 regardless of item. Its apparent post-change advantage over
the stale reference is an artifact (uninformative mid-range noise vs a
confidently wrong reference). Reading: at the bottom tier BOTH channels are
absent together — the forecast/structure dissociation is a MID-TIER
phenomenon, visible only once forecasting works at all (GPT-OSS). Makes the
Qwen forecast battery the highest-value missing cell.

## 16.3 HIDDEN-CONFOUNDER DYNAMIC WORLD (the causal core; built 2026-07-05)

Motivation (user challenge "is this strong enough on causality?"): the
observational-VAR dynamic arm is a strong belief-updating test but a WEAK
causal one, because lag-1 temporal precedence makes the structure identifiable
from observation alone -> the idealized statistician (rolling OLS) IS the
ceiling and causality adds nothing beyond it. This world removes that ceiling
so that forecast accuracy ALONE requires causal reasoning.

Structure (one latent confounder U, never shown):
    U -> A   U -> B   C -> B
- A, B both driven by hidden U -> they co-move; OBSERVING A is evidence about
  B. But A does NOT cause B. C genuinely causes B.
- In intervention periods A is set exogenously (do(A)); this severs U->A, so A
  carries no information about B. ~25% of periods are labeled interventions in
  the shown series, so the confound signature (A-B decouple under intervention)
  is LEARNABLE from data (the S1/S2/S3 path).

Why it is causal, not statistical: the see-vs-do forecast pair on the SAME
value a diverges only if the model has the causal structure right.
  see(A=a): correct answer USES a   (a is evidence about U, hence about B)
  do(A=a):  correct answer IGNORES a (the intervention severs U->A)
A model without causal structure answers both identically and fails one. A
pooled-OLS statistician fits a biased A->B slope and mis-forecasts the do
rows -> the statistician ceiling drops BELOW the truth. do(C) (C a real cause,
intervened value MUST be used) blocks the "ignore all interventions" shortcut;
only the correct causal graph passes do(A) AND do(C).

Kept closed-form (i.i.d. U, contemporaneous confound + contemporaneous cause,
lag-1 VAR texture) so every query has an exact p*. MC-validated: all five
oracles match Monte Carlo (worst 2.2 SE; see_A confirmed by bandwidth
convergence). Battery: 48 items/scenario, 25 intervention rows, confound gaps
0.30-0.55 (all >= the 0.15 certification), true see_A-vs-do_A divergence
0.35-0.47. Invariant do_A p* == obs p* holds exactly (the intervened value is
causally irrelevant to B).

Files: dyn_confounder.py (ConfoundedDynSCM + oracles p_star/p_spurious/
confound_gap + MC self-test), confounder_battery.py (5 queries + structure),
confounder_prompts.py (series marks intervention rows; crisp see/do wording;
confounder never named), run_confounder.py (resume-safe runner),
analyze_confounder.py (see/do divergence; do_A vs correct/confounded; do_C
control; spurious A->B edge rate; conf_master.csv). Analysis VALIDATED on
synthetic agents: a causal agent shows divergence 0.41 / do_A error 0.00 ->
"CORRECT"; a confounded agent shows divergence 0.00 / do_A error 0.41 ->
"CONFOUNDED". The instrument separates them cleanly.

Dynamic/cohesion knob: --intervene-from t* makes interventions BEGIN at the
change point (the assignment mechanism for A changes at t* = the policy-rule-
change / Lucas framing) instead of running throughout; default = throughout
(maximizes learnable examples). The multi-edge and tracking machinery compose
here (a confounder-strength shift is itself a coordinated change), registered
as v2 along with a persistent-latent (AR) confounder scored by exact Kalman
filtering (spurious LAGGED edges in structure too).

Predicted reads (from the arm's findings): forecasts will move on do(A) the
way see(A) moves (the confound error) -> "prediction requires causal reasoning
and the models don't have it", now a CAUSAL claim, not a statistical one. do(C)
handled correctly would show the failure is specific to confounding, not a
blanket intervention-blindness. QUEUED: GPT-OSS pilot (144 calls, 3 seeds x 48
items, ~$0.50) as the first causal-core run once credits return; then the
matched observational-arm baseline is the existing pilot (no-confounding
control already in hand). Propagated to explorer.html 2026-07-06 as §4 with
an interactive demo (see/set gauges + decoupling scatter). Still TODO: add an
R model in analyze_confounder.R.

## 16.4 CODE AUDIT AND FIXES (2026-07-07)

Three independent verified-repro reviews (engines/math, runners/prompts,
analysis/figures) before the next credit spend. Everything already collected
and every cited number survived: closed forms MC re-verified with fresh code
(worst 2.6 SE), pilot headline numbers (D2 +0.38/-0.012, F1~0.15, 9% overlap)
reproduced from raw jsonl, world/battery reconstruction exact.

WORLD-CHANGING fixes (confounder arm; safe — never run):
- dyn_confounder stabilized the WRONG matrix: B1 alone, not the effective
  transition (column B += gamma * column C from the contemporaneous
  injection). ~10/60 seeds explosive, incl. default seed 300 (|X|max 9.2e6).
  Now stabilizes the effective matrix; 56/56 seeds bounded; MC self-test and
  certified gaps (0.30-0.55 on seeds 300-302) re-validated.
- Intervention schedule was deterministic (every 4th period): a sharp model
  could PREDICT the next period is intervened, contradicting see_A's "arises
  naturally" stipulation (and ck 55/95 landed exactly on schedule).
  Now seeded-random at intervene_frac (~25%, min 5 in the first 30 periods);
  intervene_frac is a live parameter. GAP_MIN=0.15 is now ENFORCED at
  battery generation (raises on violation).

Runner fixes: --carry-belief self never stored the first answer (fresh runs
silently ran the none condition; resumed runs did carry — one label, two
protocols); resume keys now carry condition fields (model, info_level,
structure_format, carry_belief, stakes; intervene_from for the confounder;
model+noise_scale for calibration) so cross-condition resumes re-run instead
of silently skipping; --noise-scale != 1 without --noise-sweep now recomputes
p_star on the shown world (was scored against sigma=1 truth); tracking
--change-type none no longer crashes at summary; ask_two records
p_positive=None (never a fabricated 0.5) when the model omits the sign and
rejects out-of-range values, as do all runners' probability parsers (75 no
longer clamps to 0.999); formation-mode truth now uses the regime active at
the checkpoint; info_text("what") enumerates ALL changed edges at n_changes>1.

Analysis fixes: analyze_calibration infers SCM seeds from the data (hardcoded
100-104 made the scale-up unanalyzable — now runs end-to-end and its
confounded-items table is visible for the first time); analyze_confounder's
see_A/do_A guard mismatch (crash on partial data) fixed, model and true
divergence now averaged over the SAME items; analyze_v2 P2 now reports
|p-seed| (cumulative drift) AND |p-carried| (per-step revision) separately —
the single old column was labeled as the second but computed the first; on
the real P2 data per-step revision is ~0.01-0.03 and flat, sharpening the
uniform-erosion reading; analyze_dynamic dedup includes rep (resample runs no
longer collapse); two inverted/stale docstrings corrected.

Explorer: the embedded verbatim confounder prompt + ideal-reasoner
walkthrough regenerated from the FIXED world (now seed 300 ck55: a=6.13
set->0.50 vs seen->0.90, certified gap 0.40; natural corr +0.42 vs starred
-0.03).

## 16.5 PARKED — code execution as an affordance rung (discussed 2026-07-08,
## not prioritized)

Idea (user): let the model write and run analysis code — extended cognition.
Does a tool unlock latent causal understanding in models that cannot do the
estimation in-context?

Why it discriminates rather than trivializes (the memorization worry): the
worlds are built so the MOST-RETRIEVABLE analysis is the wrong one — pooled
correlation lands on the confounder world's certified trap; fit-on-all-data
fails on the changed edge. Boilerplate recall supplies the recipes; the
measured object is recipe SELECTION (window vs pool; filter labeled
intervention rows vs pool) and belief updating after the tool's output.
Anonymized X1..Xn variables block name-based retrieval (cf. Caliper
2606.04915).

Three graded probes, cheapest first:
  1. Script adjudication (no execution): hand two finished scripts (pooled
     vs intervention-filtered) — which is right for this question, and why?
     Transplant of the discovery paper's adjudication design; also a
     wrong-script objection probe mirroring the static arm's L1w rung.
  2. Write-only: model writes the analysis; WE run it; score the choice
     (windowed? filtered?) separately from the arithmetic.
  3. Full sandbox loop (machinery sketched in the discovery paper's
     CAUSAL_SANDBOX_DESIGN.md).
Sharp prediction from add.5: tool-assisted perseverance — the model's own
correct script reports the edge is gone and its stated P(present) stays
~0.85. Either outcome localizes the revision failure.

Framing caution if ever run: this changes the measurand from "can the
model's own inference track a changing world" to "can it direct an analysis
of one" — report as an extension, not blended into the main design.

## 17. MAINTENANCE RULE (user, 2026-07-04)

Any design change registered in this document MUST be propagated to the
interactive pages in the same working session:
knowable_worlds/explorer.html and knowable_worlds/explorer_news.html — prose, cell
labels, draft prompts, live-demo JS, and cross-page links. After propagating:
verify both pages render, and grep them for the retired term/format to
confirm nothing stale remains. The doc and the pages are one artifact set;
a stale page silently misrepresents the design.
