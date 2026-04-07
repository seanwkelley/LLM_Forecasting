---
name: Methods Section Review (2026-03-30)
description: Critical review of belief sensitivity paper methods section targeting EMNLP 2026. Key flaws identified: demand characteristics in probing prompt, circular probe generation, and statistical methodology gaps.
type: project
---

## Critical Flaws Identified

1. **Demand characteristics in Stage 3 prompt** — The probed forecast prompt explicitly tells the model "if a critical causal path is broken, update substantially. If a peripheral element is challenged, small or no update is fine." This directly instructs the behavior the paper claims to measure as an emergent property. Severity: Critical.

2. **Importance labels leaked into probe generation (Stage 2)** — Probe generation prompts include labels like "HIGH-IMPORTANCE factor" and "CRITICAL edge on the shortest path to the outcome." If the same model generates probes AND responds to them, it may encode importance-level signals into probe text. Severity: Major.

3. **Same model generates DAG, probes, AND responds** — Circularity risk: the model's own self-generated probe text may carry implicit importance cues detectable by the same model family.

4. **LME random effects structure** — The paper starts with random slopes but falls back to random intercepts on singularity. This fallback changes the model meaningfully and should be reported transparently.

5. **10 separate LME models without multiple comparison correction** — Running 10 univariate models inflates Type I error.

6. **Absolute shift as DV** — Using |Delta| throws away directional information and creates a floor effect at zero, violating normality assumptions for LME.

**Why:** These are the issues most likely to cause rejection at EMNLP/ARR.
**How to apply:** These should be addressed in order of severity before submission.
