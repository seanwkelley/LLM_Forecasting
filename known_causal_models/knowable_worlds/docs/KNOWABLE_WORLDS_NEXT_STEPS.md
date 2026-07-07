# Knowable Worlds — Next Steps

Single pickup point. Grouped by what blocks each. Literature tasks need no
credits and can go first.

## 1. Literature (pre-submission — no credits, do first)

From the motivation/related-work sweep (`KNOWABLE_WORLDS_MOTIVATION_RELATED_WORK.md`,
Part IV). The narrowest genuine scoop surface is a CLadder follow-up.

- [ ] Forward-citation search on **CLadder (2312.04350)**, filtered 2024–2026 —
      flag any follow-up that adds *calibration* scoring (would threaten the
      static-arm and value-of-knowledge claims at once). Highest priority.
- [ ] Forward-citation search on **Turpin (2305.04388)** for structured-output
      faithfulness extensions through 2026 (the dissociation claim's competitor
      surface).
- [ ] Forward-citation search on **CiK (2410.18959)** and **ForecastBench
      (2409.19839)** for any context-ladder / identity-isolation study on the
      same sampling frame.
- [ ] Phrase searches, expected empty — confirm: "interventional LLM
      calibration", "do-operator probability forecast", "see-vs-do language
      model", "identification gap LLM", "causal graph stability LLM",
      "series identity time series LLM forecast".
- [ ] Hand-check NeurIPS'25 / ICML'25 / ICLR'26 proceedings + recent workshops
      for "causal" + "calibration" + "probability" and for numeric-time-series
      causal-structure elicitation (post-dates reliable indexing).
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
- [ ] **Qwen single-edge formation completion** (8 pairs, ~$0.50):
      `python -m knowable_worlds.run_single_edge --model qwen/qwen3-235b-a22b-thinking-2507 --max-tokens 49152 --resume`
      (registered rule: discriminates → compute-allocation story; fails →
      formation dead for both model classes).
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
- [ ] `analyze_confounder.R` — mixed model for the see/do divergence and the
      do_A / do_C contrasts (Python descriptives exist).

## Session state (2026-07-05)

Design doc reordered to clean numerical order; naturalistic arm consolidated to
the current 2×3 prediction-only design; hidden-confounder causal core built +
MC-validated; multi-edge + single-edge tracking built; motivation/related-work
doc written (all core claims OPEN). All synced to
`github.com/seanwkelley/knowable_worlds`. Credits exhausted (last balance
negative) — everything in §2 waits on a top-up.
