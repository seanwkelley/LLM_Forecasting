# Motivation: Three Domains of LLM Forecasting Reliability

## Overview

This project investigates LLM reliability for high-stakes forecasting and decision support through three complementary experimental domains. Each domain isolates a different failure mode, and together they build a layered argument about when and why LLMs can (or cannot) be trusted as reasoning tools.

## The Three Domains

### Belief Sensitivity: Individual Reasoning Stability

The belief sensitivity experiment isolates the most fundamental question: can a single LLM maintain coherent beliefs under pressure?

**Flat-reasons mode** elicits explicit reasons behind a probability forecast, then systematically challenges each reason with adversarial probes (negation, counterfactual, weakening), supportive probes (strengthening), and controls (irrelevant information), measuring whether the model updates rationally or is simply suggestible.

**Causal network mode** goes deeper: instead of flat reasons, the LLM constructs a directed causal graph (factor nodes + edges with mechanisms + one outcome node). Probes then target specific structural elements — high-centrality nodes, critical-path edges, spurious connections, missing factors. This ties belief sensitivity to network theory: does the model's sensitivity to a challenge correlate with that challenge's structural importance in its own causal model?

Key findings (flat-reasons mode):
- **One-turn (stateless) calls produce rational updating**: adversarial probes decrease probability, strengthening increases it, irrelevant probes have near-zero effect. This is what a well-calibrated reasoner should do.
- **Multi-turn (conversational) calls degrade discriminative ability**: accumulated context causes upward drift regardless of probe type. The model loses the ability to distinguish adversarial from irrelevant information over extended conversation.
- **Even in the best case, the model is somewhat suggestible**: irrelevant probes still produce a mean absolute shift of ~0.08 in one-turn mode. Simply presenting information changes the estimate, even when that information shouldn't matter.

Early causal-mode findings (smoke test, n=2 questions):
- **Slight structural calibration**: Structural sensitivity ratio of 1.10 — high-importance probes produce somewhat larger shifts than low-importance probes.
- **High spurious acceptance**: 85.7% of spurious causal links are accepted (produce |shift| ≥ 0.05), suggesting vulnerability to invented structure.
- **Connection to causal discovery**: The same LLM that constructs a causal graph fails to defend it against spurious edges, paralleling the path-collapse failures observed in the causal discovery experiments.

### Market Simulations: Structured Multi-Agent Dynamics

Market simulations test LLM behavior in a structured multi-agent environment with clear feedback signals -- prices, supply, demand, quantifiable outcomes. This domain reveals coordination and emergence patterns: do LLMs herd, converge to equilibria, or exhibit systematic biases when interacting with each other?

Markets provide a controlled setting where "correct" behavior is relatively well-defined, making it possible to measure deviations from rational expectations.

### Conflict Simulations: Unstructured Strategic Complexity

Conflict simulations represent the hardest test. Unlike markets, conflict scenarios have:
- **Strategic ambiguity**: no clear equilibrium or optimal strategy
- **Competing objectives**: multiple stakeholders with incompatible goals
- **Qualitative judgment**: outcomes that resist quantification
- **Escalation dynamics**: small decisions can cascade into large consequences

This domain tests whether LLMs can reason coherently in environments where the reasoning demands are highest and feedback is most ambiguous. It goes beyond just testing persona effects -- it probes whether models can maintain strategic consistency, weigh competing priorities, and avoid reactive behavior over extended multi-agent interactions.

## Why Three Domains Form a Progression

The domains are ordered by complexity, and each builds on the findings of the last:

1. **Belief sensitivity** isolates the individual reasoning mechanism. If the model can't resist irrelevant probes in a simple single-agent forecasting task, that fragility will compound in more complex settings. The causal network mode adds a structural dimension: if the model can't defend the graph it just constructed against spurious edges, its causal reasoning is shallow rather than principled.

2. **Markets** test that same mechanism in a structured multi-agent setting. The biases identified in belief sensitivity -- anchoring, suggestibility, conversational drift -- manifest as coordination failures, herding, or mispricing when multiple LLM agents interact.

3. **Conflict** tests it in an unstructured multi-agent setting where "correct" behavior is ambiguous and stakes are highest. The multi-turn drift observed in belief sensitivity -- where accumulated context degrades discriminative ability -- could be the same mechanism driving escalation patterns in conflict scenarios. If the model becomes reactive rather than deliberative under sustained conversational pressure, that's a manageable nuisance in forecasting but a critical failure mode in conflict simulation.

## Practical Implications

### Architecture Matters More Than Model Scale

The belief sensitivity results show that **how** you query a model matters as much as **which** model you use. Stateless (one-turn) calls produce more rational belief updating than conversational (multi-turn) calls. This is counterintuitive -- more context is usually assumed to mean better reasoning -- but the data shows that accumulated context introduces drift and reduces the model's ability to discriminate between relevant and irrelevant information.

For deployed forecasting systems, this suggests:
- Use stateless per-query architectures for probability estimation
- If conversational interfaces are needed, periodically reset context or re-anchor to baseline estimates
- Treat extended LLM conversations as degrading, not improving, reasoning quality

### Suggestibility as a Baseline Concern

Even under ideal conditions (one-turn, irrelevant probes), presenting information to the model changes its estimate. This baseline suggestibility compounds across all three domains:
- In belief sensitivity, it means forecasts are not stable under questioning
- In markets, it means agents are influenced by noise in price signals
- In conflict, it means strategic reasoning is perturbed by irrelevant developments

Any system using LLMs for decision support should account for this inherent fragility.

### The Multi-Turn Paradox

Multi-turn conversation produces one clear benefit: better importance discrimination. When challenged, the model shifts more on high-importance reasons than low-importance ones -- a sign of appropriate prioritization. One-turn mode barely distinguishes by importance.

But this comes at the cost of cumulative drift and reduced ability to resist irrelevant influence. The tradeoff is nuanced: multi-turn understands *which* challenges matter but can't resist *cumulative* pressure. Designing systems that capture the first benefit while mitigating the second is an open problem.
