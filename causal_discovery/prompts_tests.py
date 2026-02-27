"""
Shared prompts and question generation for Oracle QA and Hidden Variable tests.

Provides:
1. Variable description dicts (extracted from system prompts)
2. build_hidden_variable_system_prompt() — template-based reconstruction
3. generate_question_battery() + 4 question type generators
4. QA prompt builders for the Oracle QA pipeline
5. mock_qa_response() for dry-run testing
"""

from __future__ import annotations

import json
from collections import deque

import numpy as np


# =============================================================================
# Variable descriptions (extracted from SYSTEM_PROMPT_MARKET / CONFLICT)
# =============================================================================

MARKET_VARIABLE_DESCRIPTIONS = {
    "shock": "exogenous market events (supply disruptions, demand changes, etc.)",
    "production_cost": "cost per unit for producers",
    "demand_per_period": "quantity consumers need per period",
    "demand_value": "maximum price consumers will pay",
    "storage_cost": "per-unit holding cost",
    "cash": "agent cash holdings",
    "inventory": "agent inventory holdings",
    "price_history": "recent price trajectory",
    "agent_orders": "submitted buy/sell orders (limit prices and quantities)",
    "clearing_price": "the market clearing price (determined by order matching)",
    "volume": "total units traded",
    "fundamental_price": "a computed reference price",
}

CONFLICT_VARIABLE_DESCRIPTIONS = {
    "shock": "exogenous events (border incidents, peace initiatives, economic crises, etc.)",
    "hawk_score": "agent disposition (0=dove, 1=hawk) — influences action recommendations",
    "escalation_index": "overall conflict intensity (0-10 scale, the main outcome)",
    "resources": "faction budget for actions",
    "gdp": "faction economic health",
    "military_strength": "faction military capability",
    "political_stability": "faction political stability",
    "military_balance": "relative military advantage between factions",
    "territory_controlled": "fraction of territory held by aggressor",
    "sanctions_level": "international sanctions on aggressor",
    "international_support": "international support for defender",
    "agent_recommendation": "individual agent's recommended action",
    "faction_action": "aggregated faction action (after internal weighting)",
}


# =============================================================================
# Hidden-variable system prompt reconstruction
# =============================================================================

_MARKET_INTRO = """\
You are a causal scientist analyzing a simulated commodity market. Your goal is \
to discover the causal structure — which variables cause which — through targeted \
interventional experiments.

The market has these variables:"""

_CONFLICT_INTRO = """\
You are a causal scientist analyzing a simulated geopolitical conflict between \
two factions (Novaris and Tethys). Your goal is to discover the causal structure \
— which variables cause which — through targeted interventional experiments.

The conflict simulation has these variables:"""

_CAUSAL_PRINCIPLES_MARKET = """
IMPORTANT CAUSAL REASONING PRINCIPLES:
- Correlation does not imply causation. Two variables may be correlated because \
they share a common cause.
- An intervention (do-operator) fixes a variable and lets everything else react. \
If changing X causes Y to change, there is a causal path from X to Y.
- If intervening on X does NOT change Y, there is no causal path from X to Y \
(or the effect is too small to detect).
- Some variables cannot be directly intervened on (they are computed outputs). \
Attempting to intervene on them will fail — this is informative.
- Feedback loops exist: A may cause B which causes A in the next period.
- Not all variables are equally informative to test. Prioritize interventions \
that distinguish between competing hypotheses.

You have a limited budget of interventions. Use them wisely."""

_CAUSAL_PRINCIPLES_CONFLICT = """
IMPORTANT CAUSAL REASONING PRINCIPLES:
- Correlation does not imply causation. Variables may correlate through common causes.
- Interventions fix a variable and let everything else react naturally.
- Some effects are NONLINEAR: the same action by both factions may amplify or \
dampen depending on whether they escalate together or diverge.
- Individual agent actions are AGGREGATED within factions using weighted voting. \
A single agent's override may have limited effect on the faction's action.
- Feedback loops exist: escalation affects agent behavior which affects escalation.
- Budget your interventions carefully — prioritize those that distinguish hypotheses."""


def build_hidden_variable_system_prompt(
    domain: str, visible_variables: list[str],
) -> str:
    """Reconstruct domain system prompt listing only visible variables.

    Uses a template approach with VARIABLE_DESCRIPTIONS dicts rather than
    string replacement on the original hardcoded prompts. Does NOT hint
    that variables have been removed.
    """
    if domain == "market":
        intro = _MARKET_INTRO
        descriptions = MARKET_VARIABLE_DESCRIPTIONS
        principles = _CAUSAL_PRINCIPLES_MARKET
    elif domain == "conflict":
        intro = _CONFLICT_INTRO
        descriptions = CONFLICT_VARIABLE_DESCRIPTIONS
        principles = _CAUSAL_PRINCIPLES_CONFLICT
    else:
        raise ValueError(f"Unknown domain: {domain}")

    var_lines = []
    for v in visible_variables:
        desc = descriptions.get(v, v)
        var_lines.append(f"- {v}: {desc}")

    var_block = "\n".join(var_lines)

    return f"""{intro}
{var_block}

Some of these variables CAUSE others. Your job is to figure out which causal \
edges exist by running interventions — fixing a variable at a specific value \
and observing what changes downstream.
{principles}
"""


# =============================================================================
# Question generation from ground truth
# =============================================================================

def generate_question_battery(
    domain: str,
    gt_matrix: np.ndarray,
    variables: list[str],
    n_per_type: int = 3,
    seed: int = 42,
) -> list[dict]:
    """Generate causal questions deterministically from ground truth.

    Returns list of dicts with keys:
        id, type, question, expected_answer, scoring_key, relevant_edges
    """
    rng = np.random.default_rng(seed)
    questions = []
    qid = 1

    generators = [
        ("counterfactual", _gen_counterfactual),
        ("mechanism", _gen_mechanism),
        ("robustness", _gen_robustness),
        ("direction", _gen_direction),
    ]

    for qtype, gen_fn in generators:
        generated = 0
        attempts = 0
        while generated < n_per_type and attempts < n_per_type * 20:
            attempts += 1
            q = gen_fn(gt_matrix, variables, rng, domain)
            if q is not None:
                # Check for duplicate questions
                dup = False
                for existing in questions:
                    if existing["question"] == q["question"]:
                        dup = True
                        break
                if dup:
                    continue
                q["id"] = f"q{qid:02d}"
                q["type"] = qtype
                questions.append(q)
                generated += 1
                qid += 1

    return questions


def _get_edges(gt: np.ndarray) -> list[tuple[int, int]]:
    """Return list of (i, j) where gt[i,j] == 1."""
    rows, cols = np.where(gt == 1)
    return list(zip(rows.tolist(), cols.tolist()))


def _find_paths(gt: np.ndarray, src: int, dst: int, max_len: int = 4) -> list[list[int]]:
    """Find all directed paths from src to dst up to max_len edges (BFS)."""
    paths = []
    queue: deque[list[int]] = deque([[src]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        if len(path) > max_len + 1:
            continue
        if node == dst and len(path) > 1:
            paths.append(path)
            continue
        for j in range(gt.shape[1]):
            if gt[node, j] == 1 and j not in path:
                queue.append(path + [j])
    return paths


def _gen_counterfactual(
    gt: np.ndarray, variables: list[str], rng: np.random.Generator, domain: str,
) -> dict | None:
    """Pick edge A->B, ask: 'If A were fixed at 0, would B change?'"""
    edges = _get_edges(gt)
    if not edges:
        return None
    i, j = edges[rng.integers(len(edges))]
    a, b = variables[i], variables[j]

    question = (
        f"If {a} were fixed at a constant value (held at 0), "
        f"would {b} change compared to normal operation?"
    )
    expected = "yes"

    return {
        "question": question,
        "expected_answer": expected,
        "scoring_key": {
            "correct_answer": "yes",
            "edge": (a, b),
            "explanation": f"{a} causes {b}, so fixing {a} would affect {b}.",
        },
        "relevant_edges": [(a, b)],
    }


def _gen_mechanism(
    gt: np.ndarray, variables: list[str], rng: np.random.Generator, domain: str,
) -> dict | None:
    """Find A->M->B path, ask: 'What mediates the effect of A on B?'"""
    edges = _get_edges(gt)
    if not edges:
        return None

    # Find 2-hop paths: A -> M -> B
    two_hop_paths = []
    for i in range(gt.shape[0]):
        for j in range(gt.shape[1]):
            if i == j:
                continue
            # Find paths of length exactly 2
            for m in range(gt.shape[0]):
                if m != i and m != j and gt[i, m] == 1 and gt[m, j] == 1:
                    two_hop_paths.append((i, m, j))

    if not two_hop_paths:
        return None

    idx = rng.integers(len(two_hop_paths))
    a_idx, m_idx, b_idx = two_hop_paths[idx]
    a, m, b = variables[a_idx], variables[m_idx], variables[b_idx]

    has_direct = bool(gt[a_idx, b_idx])

    question = f"What mediates the effect of {a} on {b}? Is the effect direct, indirect, or both?"

    if has_direct:
        expected = f"Both direct and indirect. {m} mediates an indirect path."
    else:
        expected = f"Indirect only. {m} mediates the effect."

    return {
        "question": question,
        "expected_answer": expected,
        "scoring_key": {
            "mediator": m,
            "has_direct_edge": has_direct,
            "path": [a, m, b],
        },
        "relevant_edges": [(a, m), (m, b)] + ([(a, b)] if has_direct else []),
    }


def _gen_robustness(
    gt: np.ndarray, variables: list[str], rng: np.random.Generator, domain: str,
) -> dict | None:
    """Find A->M->B with no A->B direct edge, ask if effect vanishes when M is held constant."""
    candidates = []
    for i in range(gt.shape[0]):
        for j in range(gt.shape[1]):
            if i == j or gt[i, j] == 1:
                continue  # skip if direct edge exists
            for m in range(gt.shape[0]):
                if m != i and m != j and gt[i, m] == 1 and gt[m, j] == 1:
                    candidates.append((i, m, j))

    if not candidates:
        return None

    idx = rng.integers(len(candidates))
    a_idx, m_idx, b_idx = candidates[idx]
    a, m, b = variables[a_idx], variables[m_idx], variables[b_idx]

    # Check if there are OTHER paths from a to b besides through m
    # Temporarily remove m from the graph
    gt_no_m = gt.copy()
    gt_no_m[m_idx, :] = 0
    gt_no_m[:, m_idx] = 0
    other_paths = _find_paths(gt_no_m, a_idx, b_idx)

    if other_paths:
        expected = "no"
        explanation = f"The effect would NOT vanish because alternative paths exist."
    else:
        expected = "yes"
        explanation = f"The effect would vanish because {m} is the only mediator."

    question = (
        f"Would the effect of {a} on {b} vanish if {m} were held constant?"
    )

    return {
        "question": question,
        "expected_answer": expected,
        "scoring_key": {
            "correct_answer": expected,
            "mediator": m,
            "vanishes": expected == "yes",
            "explanation": explanation,
        },
        "relevant_edges": [(a, m), (m, b)],
    }


def _gen_direction(
    gt: np.ndarray, variables: list[str], rng: np.random.Generator, domain: str,
) -> dict | None:
    """Pick a unidirectional edge, ask which direction."""
    edges = _get_edges(gt)
    # Filter to unidirectional edges (A->B but not B->A)
    unidirectional = [(i, j) for i, j in edges if gt[j, i] == 0]
    if not unidirectional:
        return None

    idx = rng.integers(len(unidirectional))
    i, j = unidirectional[idx]
    a, b = variables[i], variables[j]

    question = f"Does {a} cause {b}, or does {b} cause {a}?"
    expected = f"{a} causes {b}"

    return {
        "question": question,
        "expected_answer": expected,
        "scoring_key": {
            "correct_direction": (a, b),
            "wrong_direction": (b, a),
        },
        "relevant_edges": [(a, b)],
    }


# =============================================================================
# QA prompt builders
# =============================================================================

def build_qa_system_prompt(domain: str, variables: list[str]) -> str:
    """Domain system prompt with QA framing suffix."""
    if domain == "market":
        descriptions = MARKET_VARIABLE_DESCRIPTIONS
        intro = _MARKET_INTRO
        principles = _CAUSAL_PRINCIPLES_MARKET
    else:
        descriptions = CONFLICT_VARIABLE_DESCRIPTIONS
        intro = _CONFLICT_INTRO
        principles = _CAUSAL_PRINCIPLES_CONFLICT

    var_lines = "\n".join(f"- {v}: {descriptions.get(v, v)}" for v in variables)

    return f"""{intro}
{var_lines}

Some of these variables CAUSE others. You will be asked specific causal questions. \
You can run interventional experiments to gather evidence before answering.
{principles}

When asked a causal question, think carefully about what experiments would help \
answer it. Use your intervention budget wisely to gather the most relevant evidence."""


def build_qa_observation_prompt(
    domain: str,
    history_summary: str,
    variables: list[str],
    question: str,
) -> str:
    """Present question + history. Agent forms initial analysis."""
    return f"""\
You have been given observational data from a {domain} simulation and a specific \
causal question to answer.

SIMULATION HISTORY:
{history_summary}

VARIABLES: {', '.join(variables)}

YOUR QUESTION: {question}

Before running experiments, provide your initial analysis:
1. What is your initial hypothesis for the answer?
2. What experiments would help confirm or refute this hypothesis?
3. What key uncertainties need to be resolved?

Respond in JSON format:
```json
{{
    "initial_hypothesis": "Your best guess answer before experiments",
    "reasoning": "Why you think this",
    "key_uncertainties": ["What you're unsure about"],
    "planned_experiments": ["What interventions would help answer this"]
}}
```"""


def build_qa_intervention_prompt(
    domain: str,
    variables: list[str],
    question: str,
    budget_remaining: int,
    intervention_types: str,
    past_results_summary: str,
) -> str:
    """Ask agent to propose intervention relevant to the question."""
    return f"""\
You are investigating a specific causal question about a {domain} simulation.

YOUR QUESTION: {question}

PAST EXPERIMENT RESULTS:
{past_results_summary if past_results_summary else "None yet — this is your first experiment."}

BUDGET REMAINING: {budget_remaining} interventions

AVAILABLE INTERVENTION TYPES:
{intervention_types}

AVAILABLE VARIABLES: {', '.join(variables)}

Propose the most informative intervention to help answer your question. \
Focus on experiments that directly test the causal relationship in question.

Respond in JSON format:
```json
{{
    "intervention": {{
        "type": "action" or "trait" or "event",
        "target": {{...}},
        "run_periods": 3,
        "description": "Brief description of what this tests"
    }},
    "relevance_to_question": "How this experiment helps answer the question",
    "expected_if_yes": "What outcome would support a 'yes' answer",
    "expected_if_no": "What outcome would support a 'no' answer"
}}
```"""


def build_qa_answer_prompt(question: str, evidence_summary: str) -> str:
    """Ask for final answer after experiments."""
    return f"""\
You have completed your experiments. Now answer the causal question based on \
your evidence.

QUESTION: {question}

EVIDENCE FROM YOUR EXPERIMENTS:
{evidence_summary}

Provide your final answer. Be specific and justify with experimental evidence.

Respond in JSON format:
```json
{{
    "answer": "Your answer to the question",
    "reasoning": "Step-by-step reasoning using your experimental evidence",
    "confidence": "high/medium/low",
    "key_evidence": ["Most important findings that support your answer"]
}}
```"""


# =============================================================================
# Mock QA responses for dry-run
# =============================================================================

def mock_qa_response(
    prompt_type: str, question_type: str, step: int, domain: str,
) -> dict:
    """Return mock responses for QA dry-run testing."""
    if prompt_type == "observation":
        return {
            "initial_hypothesis": "Based on the observed correlations, I suspect there is a causal relationship.",
            "reasoning": "The variables show correlated movement patterns.",
            "key_uncertainties": ["Direction of causation", "Possible confounders"],
            "planned_experiments": ["Intervene on the suspected cause to test"],
        }

    elif prompt_type == "intervention":
        if domain == "market":
            from causal_discovery.run_pilot import MOCK_INTERVENTION_SEQUENCE
            idx = min(step, len(MOCK_INTERVENTION_SEQUENCE) - 1)
            mock = MOCK_INTERVENTION_SEQUENCE[idx].copy()
        else:
            from causal_discovery.run_pilot import MOCK_CONFLICT_INTERVENTION_SEQUENCE
            idx = min(step, len(MOCK_CONFLICT_INTERVENTION_SEQUENCE) - 1)
            mock = MOCK_CONFLICT_INTERVENTION_SEQUENCE[idx].copy()
        mock["relevance_to_question"] = "Tests the causal pathway in question"
        mock["expected_if_yes"] = "Effect should be visible"
        mock["expected_if_no"] = "No effect expected"
        return mock

    elif prompt_type == "answer":
        if question_type == "counterfactual":
            return {
                "answer": "Yes, the variable would change.",
                "reasoning": "Intervention experiments showed a clear downstream effect.",
                "confidence": "medium",
                "key_evidence": ["Observed change in target when cause was manipulated"],
            }
        elif question_type == "mechanism":
            return {
                "answer": "The effect is mediated through an intermediate variable. The path appears to be indirect.",
                "reasoning": "Intervening on the mediator blocked the downstream effect.",
                "confidence": "medium",
                "key_evidence": ["Blocking mediator eliminated downstream change"],
            }
        elif question_type == "robustness":
            return {
                "answer": "Yes, the effect would vanish when the mediator is held constant.",
                "reasoning": "The mediator is the sole pathway between cause and effect.",
                "confidence": "medium",
                "key_evidence": ["No alternative paths found in experiments"],
            }
        elif question_type == "direction":
            return {
                "answer": "The first variable causes the second.",
                "reasoning": "Intervening on the first variable changed the second, but not vice versa.",
                "confidence": "high",
                "key_evidence": ["Asymmetric intervention results"],
            }

    return {}
