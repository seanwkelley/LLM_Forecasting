# Knowable Worlds — Next Steps

Single pickup point. Grouped by what blocks each. Literature tasks need no
credits and can go first.

## 1. Literature (pre-submission — no credits, do first)

Sweep RUN 2026-07-07 — full verdicts and new must-cites recorded in
`KNOWABLE_WORLDS_MOTIVATION_RELATED_WORK.md` Part IV-b. Summary: CLadder /
Turpin / CiK / ForecastBench-Sim forward-cites CLEAR; phrase searches all
empty (one vocabulary near-miss: PROPHET 2504.01509 — cite and
differentiate); claims (a)-(c) LOW risk, (d)/(e) LOW-MODERATE.

Still open (manual, before submission):
- [ ] Enumerate FoRLM @ NeurIPS 2025 accepted papers; van der Schaar Lab's
      ~7 ICLR 2026 papers; OpenReview ICML 2025/26
      "causal"+"calibration"+"forecast" (search-engine sweep was not
      exhaustive here).
- [ ] Re-run the 2604.16988 forward-citation check via a real citation graph
      within a week of submission (paper too recent for search indexing).
- [ ] **Verify every arXiv ID from 2025-09 onward** (number, title, venue) —
      several were surfaced from prior sessions and are unconfirmed.

## 2. Runs (blocked on OpenRouter credits)

Key at `known_causal_models/.Renviron`; launch with
`export $(grep OPENROUTER_API_KEY .Renviron)`; always `cd known_causal_models`
first. Ordered cheapest + sharpest first.

- [ ] **Confounder pilot (the causal core)** — the first causal-necessity run:
      `python -m knowable_worlds.run_confounder --model gpt-oss --seeds 300 301 302 --out-dir knowable_worlds/outputs/confounder_gptoss`
      (~144 calls, ~$0.50) → `python -m knowable_worlds.analyze_confounder --run confounder_gptoss`.
      The existing observational pilot is its matched no-confounding baseline.
- [x] **Qwen single-edge formation completion** — DONE 2026-07-07:
      discrimination +0.45 (true 0.77 vs non-edge 0.32; GPT-OSS +0.09).
      Registered verdict: the whole-graph floor is COMPUTE ALLOCATION, not
      detection inability (design doc 16.2 decision-rule outcome). Opens the
      registered follow-on decision: complete Qwen's whole-graph pass
      (81 items, ~$15-25) to sharpen the floor-vs-allocation contrast.
- [ ] **Changed-edge tracking, GPT-OSS** — now THE structure question of the
      main battery (design doc §16.2 add.3, 2026-07-06): `run_single_edge
      --mode tracking`, two probabilities per pair (present +
      positive-if-present), all four change types. Start with edge_add /
      edge_remove × seeds 301/302 (certified detectable), then sign_flip and
      weight_double (admit weight_double only if the printed rolling-20 |t|
      certification gap is clearly positive; seed 300 passes: 0.8 → 2.5).
      Then the k∈{1,3,6} multi-edge dose.
- [ ] **P1 self-carryover + I1 stakes** (design doc §16.1): `run_dynamic
      --carry-belief self` and `--stakes` reruns.
- [ ] **Static scale-up** resume from 771/4,800 (`run_calibration ... --resume`).
- [ ] Tier-1 multi-model replication of the core battery; more seeds.

## 3. Code / docs (no credits)

- [x] Propagate the hidden-confounder world into `explorer.html` as an
      interactive demo — DONE 2026-07-06 (page restructured as the dynamic
      study design: static sections removed, reduced-edge-set structure
      channel, k-dose and confounder extensions foregrounded with
      interactives).
- [x] `analyze_confounder.R` — DONE 2026-07-07: three two-condition mixed
      models (trap-vs-truth on set-X1; model vs required see/do divergence;
      set-X1 vs set-X3 error), scenario random intercepts; validated on
      synthetic causal/confounded agents (verdicts separate cleanly).
- [x] `analyze_tracking.py` — DONE 2026-07-07: per-scenario DiD on the
      change-appropriate field, weight_double certification (late-window
      rolling-|t| gap, bar 1.5), per-model pooling, track_master.csv for R;
      validated on synthetic tracker/flat agents (all four signatures).

## Session state (2026-07-05)

Design doc reordered to clean numerical order; naturalistic arm consolidated to
the current 2×3 prediction-only design; hidden-confounder causal core built +
MC-validated; multi-edge + single-edge tracking built; motivation/related-work
doc written (all core claims OPEN). All synced to
`github.com/seanwkelley/knowable_worlds`. Credits exhausted (last balance
negative) — everything in §2 waits on a top-up.
