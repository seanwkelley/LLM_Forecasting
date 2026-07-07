# Knowable Worlds — Motivation and Related Work

Companion to `KNOWABLE_WORLDS_DESIGN.md` (the design registry). This document
gives the standalone motivation narrative and the consolidated related-work
positioning, drawn from the design doc's framing (§1–2) and a fresh
three-cluster adversarial literature sweep (2026-07-05). Every core novelty
claim came back OPEN.

> Citation caveat: arXiv IDs from 2025-09 onward are past the reviewers'
> reliable knowledge and several were surfaced from prior research sessions —
> verify each ID and venue against the live listing before submission. A
> pre-submission search checklist is at the end.

---

## Part I — Motivation

### 1. The theoretical question

Forecasting in a world that changes is not one ability but two. A forecaster
must (i) **update its predictive model when the regime shifts** — notice that
the data no longer behave as before and adapt its probabilities — and (ii)
**relate that update to a change in the underlying causal structure** —
recognize *what* changed, which relationship broke or appeared, and why the old
predictions stopped working. A system with a genuine causal model of the world
couples these: it revises its forecasts *because* it inferred a structural
change. A system that is only pattern-matching can do the first without the
second — tracking the new numbers while its account of the world's mechanism
stays frozen or drifts at random.

The central question of this study is whether large language models **couple or
dissociate** these two abilities. When the causal structure generating a time
series changes, does an LLM update its forecasting model *and* relate that
update to the structural change — or does prediction adapt while the model's
representation of the causal structure does not? This is a question about
whether LLM forecasting is causal in any meaningful sense: whether prediction
and explanation move together, or whether the appearance of adaptive
forecasting hides the absence of any updated causal understanding. (Our own
pilot evidence points to dissociation — forecasts adapt slowly while the stated
causal graph never tracks the change — which is what makes the question worth a
paper rather than a footnote.)

### 2. Why the question is hard, and why a simulated causal world answers it

This cannot be asked with real data. To see whether predictive updating is
coupled to causal-structural updating you need two things that reality never
provides: (a) the **true forecast at each moment**, so predictive adaptation is
measured against a target rather than a single noisy outcome, and (b) the
**true causal structure before and after the change**, so a stated structure
can be scored for whether it tracked the real change. Real forecasting data
gives neither — the true probability is unknowable, so calibration is only a
binned proxy and "didn't know" can never be separated from "couldn't compute,"
and there is no ground-truth causal graph to score against.

A structural causal model we build makes both exact:

- **The true probability p\*** of each event — analytic for linear-Gaussian
  systems, cheap simulation otherwise — so forecast error is `|p − p*|`, a real
  number per item, and predictive adaptation across a change-point is a
  measurable trajectory rather than a guess.
- **The true causal graph in each regime**, and — because we set the
  change-point — exactly which relationship changed and when, so predictive
  updating and causal-structural updating can be measured separately and their
  coupling tested directly.
- **A removable knowledge excuse**: with the full mechanism placed in the
  prompt, p\* is computable from the prompt alone, so any residual error is a
  pure reasoning failure, not missing information.

The field's closest work names the exact-probability target as future work
(ForecastBench-Sim, 2606.18686) and never touches the causal-structure side at
all; no benchmark scores an LLM's forecast and its stated causal model against
exact truth as a world changes.

### 3. From coupling to necessity: when prediction *requires* the causal update

A skeptic can object that predictive updating need not involve causal
understanding at all: in a fully observed world a good pattern-matcher forecasts
perfectly with no causal model, so a dissociation between prediction and
structure would merely show that the causal question is beside the point. The
study meets this objection with a world where it fails. A hidden common cause
makes the observational pattern misleading, so forecasting the effect of an
intervention *requires* the correct causal structure — posed as a see-versus-do
probe ("suppose you *observe* A = a" vs "suppose A is *set* to a," where a
pattern-matcher's forecast is provably wrong). There, predictive success and
causal understanding cannot be separated even in principle. This is exactly the
situation real forecasters face when the thing that changes is a policy or a
mechanism rather than a surface trend — and it converts the coupling question
from something a pattern-matcher could sidestep into a demand that forecast
accuracy alone can only meet through causal reasoning.

### 4. What each arm contributes to the question

- **Dynamic regime-shift arm (the main experiment).** The direct test: a lag-1
  causal system whose structure changes at a change-point; the model, shown only
  the numeric series, is scored at checkpoints on *both* its forecast (against
  exact p\*) and its stated causal structure (against the true graph) — so
  whether the two update together is measured head-on.
- **Hidden-confounder world (the causal core).** The necessity case:
  forecasting that cannot succeed without the causal update, which removes the
  "causality is beside the point" escape and makes forecast accuracy alone
  diagnostic of causal reasoning.
- **Static causal-necessity ladder (the mechanism layer).** Prices what each
  increment of causal knowledge — the graph, the signs, the full equations — is
  worth to a forecast, including where it is *negative*, and establishes the
  computation-versus-understanding distinction through which the dynamic results
  are read (given full equations the model is a near-perfect calculator; given
  only structure, barely helped).
- **Naturalistic transfer arm.** The synthetic arms test the coupling question
  where we can score both sides; this arm asks whether the same failure appears
  on real series, where a model's "causal structure" is its *latent world
  knowledge* of the named quantity. The three-level context ladder instantiates
  the question: L1 (anonymous numbers) is pure pattern extrapolation with no
  structural knowledge engaged; L2 (naming the series) activates the model's
  stored understanding of how that quantity behaves; L3 adds the news about what
  changed. The sharp test is **L2 on a series that has changed after the model's
  cutoff**: if prediction is coupled to an *updated* causal understanding, naming
  the series helps; if the model's stored structure is stale and clung to, naming
  it drags the forecast toward the old regime — the real-world echo of the
  sandbox's perseveration. The no-change × news cell is the real-world form of
  "causal beliefs are prompt-echoes": does a consequential-sounding story move
  the forecast when the numbers show nothing changed? Honest scope: with no
  ground-truth graph for real series, this arm tests the coupling question's
  *shadow* — whether latent structural knowledge helps or hurts prediction under
  change — not the direct structure-scoring version; it is the external-validity
  bridge, not a second exact-truth measurement.

---

## Part II — Related work

Four clusters. For each: what exists, the single closest paper, and our wedge.

### A. Scoring LLM forecasts against knowable probabilities

The core measurement idea (E1) has no prior instance. **ForecastBench-Sim
(2606.18686)** is the immediate predecessor and names exact-p\* scoring as
future work — cite as motivation, not competitor. **BayesBench (2512.02719)**
is the closest on exact analytic truth: it compares LLM judgments to the
Bayesian-optimal posterior under controlled noise, but in perceptual
cue-combination tasks, with no causal structure and no time series (it is the
one to differentiate for the aleatoric-sensitivity claim). **KalshiBench
(2512.16030)** reports that reasoning can *worsen* calibration — useful
motivation for the measurement question. The verbalized-confidence /
uncertainty-quantification line (Kadavath et al. 2207.05221; semantic
uncertainty, Kuhn et al.) is the calibration-measurement backdrop.

**Verdict:** true-p\* calibration scoring — **OPEN**.

### B. LLM causal reasoning and the do-operator

The primary neighbour is **CLadder (2312.04350)** — a do-calculus /
rung-2 / rung-3 question-answering benchmark with engine-generated ground
truth. A reviewer will cite it against the static and hidden-confounder arms
at once, so the wedge must be explicit: CLadder scores *binary accuracy on
verbally described* SCMs; we score *continuous calibration against exact
numeric p\**, admit confounded items only above a certified identification
gap, use a continuous trap-versus-truth index (under which the "graph-only
makes confounded forecasts worse" finding is even measurable), and pose
see-versus-do as *paired probability queries on the same value* — which CLadder
does not. Related reasoning benchmarks: Corr2Cause (2306.05836; rung-2
failure, contamination argument), Kıcıman et al. (2305.00050; LLMs encode
causal knowledge from *text-described* relations), CRASS (verbal rung-3
plausibility), the Willig et al. three-level taxonomy, CausalGraph2LLM
(2410.15939; LLMs are sensitive to graph encoding — supports the
numeric-vs-verbal wedge), and Yang et al.'s critical review of causal
benchmarks (2407.08029), which explicitly endorses exactly this direction.

Two framing anchors: **"Causal Parrots" (Zečević et al., 2308.13067)** — the
argument that LLM causal ability is recited correlational knowledge — is our
null hypothesis, and the trap-attraction and prompt-echo findings are evidence
*for* it; and **Wu et al. "LLMs Cannot Discover Causality" (2506.00844)** is
recent theoretical grounding (verify ID/venue).

On the specific probes: no paper presents **see(A=a) vs do(A=a) as paired
probability forecasts** scored against certified-different exact answers, and
the do(C)-on-a-true-cause anti-shortcut control has no prior instance. Work on
confounding from *text* (IV Co-Scientist 2602.07943; VIGOR+ 2512.19349) does
not touch numeric probability calibration. Causal inference from *data tables*
by LLMs (the knowledge × data factorial) is also open: Garg et al. (2022)
covers in-context estimation only; Linear-LLM-SCM (2602.10282) elicits
coefficients from priors, not tables, and never computes an interventional
p\*; LLM-BI (2508.08300) executes an elicited model but has no SCM event with
a computable true p\*; Nafar et al. (2505.15918) elicits conditional
probability tables with no data input. The value-of-information framing has
theoretical backing in the causal-bandits result that graph recovery ≠ reward
maximization (2510.16811).

**Verdicts:** exact-SCM scoring of interventional/counterfactual forecasts —
**OPEN**; the see-versus-do forecast probe — **OPEN**; the value-of-causal-
knowledge (including negative) framing — **OPEN**. Closest single threats:
2312.04350 (reasoning), 2308.13067 (see/do concept), 2606.18686 (value framing).

### C. LLM time-series forecasting and context

Numbers-only forecasting by prompted LLMs is established (**LLMTime /
Gruver et al. 2310.07820**), as is the sceptical reading ("Are LLMs Useful for
Time Series?", 2406.16964); these set the L1 anonymous-numbers baseline.
Time-series *foundation* models (Chronos, TimesFM, Moirai, MOMENT) are a
contrast class, not prompted LLMs. Context-aided forecasting is where the
naturalistic arm lives, and the closest paradigm is **"Context is Key" / CiK
(2410.18959)**: it tests full context vs no context but never isolates series
*identity* alone (its context is whole background paragraphs), has no
no-change control, and forecasts continuous trajectories rather than binary
events. **"Understanding and Enhancing..." (2402.10835)** ablates external
knowledge but bundles identity with domain description, units, and statistics,
on pre-cutoff benchmarks. The nearest three-level design is **"From News to
Forecast" (2409.17515)** — a reviewer will cite it — but its intermediate
condition bundles weather, calendar, and region metadata rather than the
series name alone, it forecasts trajectories not threshold events, has no
no-change row, no post-cutoff guarantee, and no self-recognition check.

News-augmented event forecasting is a mature line — **AutoCast (2206.15474)**,
**Halawi et al. (2402.18563)**, EvolveCast (2509.23936), FutureSim
(2605.15188), LEAF (2605.16358) — and every one of them draws questions that
eventually resolve; **none has a certified no-event stratum**, which makes the
no-change row the cleanest open claim in the arm. The memorization /
contamination literature motivates the design: Lopez-Lira "Memorization
Problem" (2504.14765) and Look-Ahead-Bench (2601.13770) show LLMs recall
named pre-cutoff series almost exactly (hence strictly post-cutoff targets and
anonymous L1), and the LAP lookahead metric (2512.23847) plus financial
entity-neutering (Engelberg et al., SSRN 5182756) show named-vs-anonymous
manipulations only on *text*, never on raw numeric series. Presenting raw
numbers and asking the model to identify the series (the self-recognition
check) has no antecedent.

**Verdicts:** isolating the value of series identity, L2−L1, with post-cutoff
and recognition guards — **OPEN**; the certified no-change row / narrative
over-reaction cell — **OPEN** (strongest); the three-level within-model context
decomposition — **OPEN** (address 2409.17515 directly). Closest: 2410.18959,
2409.17515.

### D. Regime change, belief updating, and the dissociation

**Belief updating.** The closest is **"LLMs as Discounted Bayesian Filters"
(2512.18489)**: exact synthetic truth, sequential observations, a fitted
forgetting rate — but it measures *symmetric* forgetting in a stationary
process, whereas perseveration is *asymmetric* resistance to a structural
step-change, and it never elicits causal structure. Adjacent: a martingale
test of sequential rationality (2512.02914), the STALE finding that models
fail to override stale context (2605.06527), and the sycophancy line (Sharma
2310.13548; Perez 2212.09251; Wei 2308.03188), which is a different failure
mode (social pressure, not evidential updating).

**Regime-change detection and dynamical-system ICL.** The biggest *design*
threat is **"In-Context Learning Under Regime Change" (2604.16988)** — regime
change in a linear dynamical system with near-optimal adaptation — but it uses
*trained* time-series transformers, scores forecast accuracy only, and elicits
no causal structure. The same "trained, not prompted, no structure" gap
applies to transformer-as-Kalman-filter (2410.16546), the ICL-of-linear-
dynamical-systems analysis (2502.08136), and SPACETIME (2501.10235). LLM-based
change-point work either makes the LLM a downstream *explainer* of breaks a
classical detector found (2601.02957) or feeds it central-bank *text*, not
numbers (2605.30363). Classical non-stationary causal discovery (CD-NOD,
DYNOTEARS) is the correct statistical comparator, not a scoop.

**Causal discovery from a numeric series.** No paper shows a prompted LLM a raw
(anonymous) numeric series, elicits a signed causal edge list as its belief,
and scores it against the exact graph across a break. Kıcıman et al. use
text-described relations; RealTCD (2404.14786) is a hybrid needing named
variables; the sequential hybrid 2506.16234 has the *statistical engine*, not
the LLM, do the revising.

**The dissociation (the strongest claim).** The nearest predecessor is
**Turpin et al. (2305.04388)** — injected anchors make an LLM's stated chain-of-
thought diverge from the driver of its answer. But that is a single-prompt,
verbal-reasoning-versus-forced-choice divergence; ours is two independently
scored *quantitative* outputs (a probability and a signed graph), both scored
against exact truth, measured as *adaptation rates across time*, which is
architecturally impossible in Turpin's paradigm.

**Prompt-echoes / graph churn.** The finding that LLM causal "beliefs" persist
only when handed back and otherwise decay to ~9% consecutive overlap has no
prior operationalization. The consistency literature (Elazar et al. 2021)
documents 50–70% consistency on *facts*; self-consistency sampling (Wang et al.
2022) is a *remedy*, not a characterization. The ~9% overlap is a
qualitatively more extreme phenomenon. Per-edge probability elicitation
(Sekulovski et al., BJMSP 2026) elicits LLM graph *priors* (model not shown
data, static graph, not scored as beliefs against exact truth); no one tests
handing an LLM its own prior graph across an evidence boundary.

**Verdicts:** dual forecast+structure tracking of a changing causal world
against exact truth — **OPEN**; the forecast-adapts-while-structure-
perseverates dissociation — **OPEN (strongest)**; the causal-beliefs-as-prompt-
echoes characterization — **OPEN (most novel behavioural finding)**. Closest:
2604.16988, 2305.04388, 2512.18489, Elazar 2021.

---

## Part III — Positioning at a glance

| Claim | Verdict | Closest prior | Our wedge |
|---|---|---|---|
| Score LLM forecasts against exact p\* | OPEN | ForecastBench-Sim 2606.18686 | They name it as future work; we do it |
| Value of causal knowledge (incl. negative) | OPEN | — | Ability benchmarks score answers; we price knowledge in forecast currency |
| Confounded-intervention + counterfactual calibration | OPEN / close call | CLadder 2312.04350 | Continuous calibration vs binary accuracy; numeric SCMs; certified gaps |
| See-vs-do forecast on the same value | OPEN | Causal Parrots 2308.13067 (concept only) | Paired probability queries vs certified-different exact answers |
| Track a *changing* causal structure (dual scoring) | OPEN | ICL-under-regime-change 2604.16988 | Prompted LLM, numeric series, forecast + stated structure |
| Forecast-vs-structure dissociation | OPEN (strongest) | Turpin 2305.04388 | Two quantitative outputs, exact truth, adaptation rates over time |
| Causal beliefs as prompt-echoes / churn | OPEN | Elazar 2021 consistency | Structured causal output, exact GT, carry-forward manipulation |
| Value of series identity (L2−L1) on raw numbers | OPEN | CiK 2410.18959 | Identity isolated; post-cutoff + self-recognition guards |
| Certified no-change row / narrative over-reaction | OPEN (cleanest) | — | No event-forecasting benchmark has a no-event stratum |
| Three-level context decomposition | OPEN | From News to Forecast 2409.17515 | Identity-only middle rung; binary events; no-change row |

---

## Part IV — Pre-submission live-search checklist

Consolidated from the three sweeps. Run before finalizing related work; the
narrowest genuine scoop surfaces are the CLadder follow-ups and any 2026
structured-output faithfulness paper.

1. Forward-citation search on **CLadder (2312.04350)**, filtered 2024–2026 —
   a follow-up adding *calibration* scoring would threaten the static-arm and
   value-of-knowledge claims at once (the single highest-risk surface).
2. Forward-citation search on **Turpin (2305.04388)** for structured-output
   faithfulness extensions through 2026 (cluster D is the most likely to have
   acquired a direct competitor).
3. Forward-citation search on **CiK (2410.18959)** and **ForecastBench
   (2409.19839)** for any context-ladder or identity-isolation study on the
   same sampling frame.
4. Phrase searches predicted to return nothing (confirm): "interventional LLM
   calibration", "do-operator probability forecast", "see-vs-do language
   model", "identification gap LLM", "causal graph stability LLM",
   "series identity time series LLM forecast".
5. Hand-check NeurIPS 2025 / ICML 2025 / ICLR 2026 proceedings and recent
   workshops for "causal" + "calibration" + "probability" and for numeric
   time-series causal-structure elicitation — these post-date reliable indexing.
6. Verify every arXiv ID from 2025-09 onward (several were surfaced from prior
   sessions and need confirmation of number, title, and venue).

---

## Part IV-b — Scoop-check results (run 2026-07-07)

Live web-search sweep of the Part IV checklist (search-engine approximation;
no citation-graph API access — the one methodological caveat). Verdicts:

1. CLadder forward-cites: **CLEAR.** Post-CLadder work went to lexical
   ablations (Caliper 2606.04915), post-training (CauGym 2602.06337), and
   symbolic verification (DoVerifier 2601.21210 — explicitly avoids numeric
   probability substitution by design). Nobody added calibration scoring.
2. Turpin forward-cites: **CLEAR.** The faithfulness literature is
   mediation-style (intervene on the stated reasoning, watch the answer:
   Project Ariadne 2601.02314, Breaking the Chain 2603.16475, Why Models
   Know But Don't Say 2603.26410) — none scores a forecast against one
   exact truth AND a stated structure against a second, over time. State
   this contrast explicitly; it is the likely reviewer objection.
3. CiK / ForecastBench / ForecastBench-Sim: **CLEAR.** Dr-CiK (2605.27904)
   is not a context ladder; ForecastBench-Sim still names exact-p* scoring
   as future work and nobody has executed it.
4. Phrase searches: **all confirmed empty**, with one vocabulary near-miss:
   PROPHET (2504.01509) — "Causal Intervened Likelihood" is a question-
   FILTERING metric on real Polymarket resolutions, not a scored output
   against exact truth. Must-cite and differentiate explicitly.
5. Proceedings check: **INCOMPLETE** — searched, not enumerated. Before
   submission, manually check: (a) FoRLM @ NeurIPS 2025 accepted list,
   (b) van der Schaar Lab's ~7 ICLR 2026 papers, (c) OpenReview for
   ICML 2025/26 "causal"+"calibration"+"forecast".
6. 2604.16988 (ICL under regime change) follow-ups: **CLEAR**, but the
   paper is ~3 months old — re-run this one check via a citation graph
   within a week of submission.

Risk after sweep: claims (a)-(c) LOW; (d) dissociation and (e) prompt-echo
LOW-MODERATE (two adjacent literatures could combine; BeliefShift 2603.23848
tracks verbal-opinion consistency over time — the closest 2026 precedent for
(e), closer than Elazar 2021, though it has no causal graphs or exact truth).

New must-cites from this sweep: PROPHET 2504.01509 (differentiate),
DoVerifier 2601.21210 (metric-choice contrast), Caliper 2606.04915
(supports numeric/anonymized design), ERM/Rung Collapse 2602.11675
(theoretical motivation for the obs-vs-interventional gap), Project Ariadne
2601.02314 + Breaking the Chain 2603.16475 (mediation-vs-dual-scoring
contrast), BeliefShift 2603.23848 (belief-consistency precedent), CauScien
position paper 2510.16530 (field-needs-this motivation).

---

## Consolidated must-cite list

Calibration / exact-truth: 2606.18686 (ForecastBench-Sim), 2512.02719
(BayesBench), 2512.16030 (KalshiBench), 2207.05221 (Kadavath).
Causal reasoning: 2312.04350 (CLadder), 2306.05836 (Corr2Cause), 2308.13067
(Causal Parrots), 2305.00050 (Kıcıman), 2407.08029 (Yang review), 2410.15939
(CausalGraph2LLM), 2506.00844 (Wu), 2602.10282 (Linear-LLM-SCM), 2508.08300
(LLM-BI), 2510.16811 (causal bandits / VOI); Pearl (2009), Peters-Janzing-
Schölkopf (2017) as foundations.
Time series / context / news: 2310.07820 (LLMTime), 2406.16964 (Are LLMs
Useful for TS), 2410.18959 (CiK), 2409.17515 (From News to Forecast),
2402.10835, 2206.15474 (AutoCast), 2402.18563 (Halawi), 2509.23936
(EvolveCast), 2605.15188 (FutureSim), 2504.14765 (Memorization Problem),
2601.13770 (Look-Ahead-Bench), 2512.23847 (LAP).
Regime change / updating / dissociation: 2604.16988 (ICL under regime change),
2512.18489 (Discounted Bayesian Filters), 2601.02957 (LLM changepoint),
2410.16546 (transformer Kalman), 2502.08136 (ICL of LDS), 2305.04388 (Turpin),
Elazar et al. 2021 (consistency), Sekulovski et al. BJMSP 2026 (per-edge
priors); CD-NOD (Huang 2020), DYNOTEARS (Pamfil 2020) as classical comparators.
