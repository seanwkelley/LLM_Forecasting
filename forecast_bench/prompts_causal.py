"""
Causal Network Prompts — Templates for the causal belief sensitivity pipeline.

Stage 1: Causal forecast — get probability + directed causal graph
Stage 2: Network-targeted probe generation — create probes for structural elements
Stage 3: Causal probed forecast — present probe with network context
"""

from __future__ import annotations

import json


# =============================================================================
# PROBE TYPES (causal mode)
# =============================================================================

CAUSAL_PROBE_TYPES = [
    "node_negate_high",
    "node_negate_medium",
    "node_negate_low",
    "node_strengthen",
    "edge_negate_critical",
    "edge_negate_peripheral",
    "edge_reverse",
    "edge_spurious",
    "missing_node",
    "irrelevant",
]

PROBE_CATEGORIES = {
    "node_negate_high": "node",
    "node_negate_medium": "node",
    "node_negate_low": "node",
    "node_strengthen": "node",
    "edge_negate_critical": "edge",
    "edge_negate_peripheral": "edge",
    "edge_reverse": "edge",
    "edge_spurious": "edge",
    "missing_node": "structural",
    "irrelevant": "structural",
}


# =============================================================================
# STAGE 1: CAUSAL FORECAST
# =============================================================================

CAUSAL_FORECAST_SYSTEM = """\
You are an expert forecaster. Your task is to estimate the probability that a given \
event will occur, and to represent your reasoning as a directed causal graph.

Build a causal network where:
- Nodes are factors that influence the outcome
- Directed edges represent causal mechanisms (A -> B means A causally influences B)
- One node is the "outcome" node representing the forecasted event
- All other nodes are "factor" nodes representing causal drivers

You must be well-calibrated: assign probabilities that genuinely reflect your \
uncertainty. Avoid defaulting to 50% unless you truly have no information.

Respond with ONLY valid JSON. No other text."""


def build_causal_forecast_prompt(question: str) -> str:
    """Build the user prompt for Stage 1: causal forecast.

    Parameters
    ----------
    question : str
        The binary forecasting question.

    Returns
    -------
    User prompt string.
    """
    return f"""\
Forecast the following question:

"{question}"

Provide your response as JSON with exactly this structure:
{{
  "probability": <float between 0.01 and 0.99>,
  "nodes": [
    {{"id": "short_snake_case_id", "description": "What this factor represents", "role": "factor"}},
    {{"id": "another_factor", "description": "Description", "role": "factor"}},
    {{"id": "outcome", "description": "The forecasted event", "role": "outcome"}}
  ],
  "edges": [
    {{"from": "short_snake_case_id", "to": "another_factor", "mechanism": "How A causes B"}},
    {{"from": "another_factor", "to": "outcome", "mechanism": "How this factor affects the outcome"}}
  ],
  "reasoning": "<brief overall reasoning paragraph>"
}}

Requirements:
- Provide between 4 and 8 factor nodes, plus exactly 1 outcome node.
- Each factor node must have at least 1 outgoing edge.
- The outcome node must have at least 1 incoming edge.
- All edge endpoints ("from" and "to") must reference valid node IDs.
- Edges represent causal influence: "from" causes or influences "to".
- Include indirect causal chains (A -> B -> outcome), not just direct links.
- probability must be between 0.01 and 0.99 (never 0 or 1).
- Node IDs must be short_snake_case (e.g., "economic_growth", "fed_policy")."""


# =============================================================================
# STAGE 2: NETWORK-TARGETED PROBE GENERATION
# =============================================================================

CAUSAL_PROBE_GENERATION_SYSTEM = """\
You are an expert at constructing probes to test how a forecaster updates their \
beliefs when elements of their causal reasoning are challenged. You will be given \
a causal network (nodes and edges) and asked to create a targeted probe that \
challenges a specific structural element of that network.

The probe should be plausible, specific, and designed to test whether the \
forecaster can appropriately update their beliefs when confronted with new \
information about their causal model.

Respond with ONLY valid JSON. No other text."""


def _format_network_context(nodes: list[dict], edges: list[dict]) -> str:
    """Format the causal network as readable text for prompt inclusion."""
    node_lines = []
    for n in nodes:
        role_tag = f" [{n['role'].upper()}]" if n.get("role") == "outcome" else ""
        node_lines.append(f"  - {n['id']}: {n.get('description', '')}{role_tag}")

    edge_lines = []
    for e in edges:
        edge_lines.append(f"  - {e['from']} -> {e['to']}: {e.get('mechanism', '')}")

    return (
        "Causal Network:\n"
        "Nodes:\n" + "\n".join(node_lines) + "\n\n"
        "Edges (causal links):\n" + "\n".join(edge_lines)
    )


def build_causal_probe_prompt(
    question: str,
    probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe_target: dict,
) -> str:
    """Build the user prompt for Stage 2: causal probe generation.

    Parameters
    ----------
    question : str
        The original forecasting question.
    probability : float
        The initial probability estimate.
    nodes : list[dict]
        The causal network nodes.
    edges : list[dict]
        The causal network edges.
    probe_target : dict
        The probe target from network analysis: {target_type, target_id,
        description, probe_type, ...}.

    Returns
    -------
    User prompt string.
    """
    network_context = _format_network_context(nodes, edges)
    probe_type = probe_target["probe_type"]
    target_id = probe_target["target_id"]
    target_desc = probe_target["description"]

    type_instructions = {
        "node_negate_high": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). This is a HIGH-IMPORTANCE factor in the network. "
            f"Frame it as: 'What if this factor is completely wrong or irrelevant?' "
            f"Provide a specific, plausible argument for why this factor might not "
            f"matter or why the opposite might be true."
        ),
        "node_negate_medium": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). This is a MEDIUM-IMPORTANCE factor. "
            f"Argue why this factor might be wrong or irrelevant, with a specific "
            f"mechanism or piece of evidence."
        ),
        "node_negate_low": (
            f"Create a direct negation of the causal factor '{target_id}' "
            f"({target_desc}). This is a LOW-IMPORTANCE factor. "
            f"Argue why this factor might be wrong or irrelevant."
        ),
        "node_strengthen": (
            f"Create a plausible piece of evidence or argument that REINFORCES "
            f"the causal factor '{target_id}' ({target_desc}), making it even "
            f"more likely to be true and more causally important. This could be "
            f"a new data point, expert endorsement, or development that strongly "
            f"supports this factor's role in the causal network."
        ),
        "edge_negate_critical": (
            f"Challenge the causal link '{target_id}' ({target_desc}). "
            f"This is a CRITICAL edge on the shortest path to the outcome. "
            f"Argue why this causal mechanism might be broken, spurious, or "
            f"much weaker than assumed. Provide a specific counter-mechanism "
            f"or piece of evidence."
        ),
        "edge_negate_peripheral": (
            f"Challenge the causal link '{target_id}' ({target_desc}). "
            f"This is a PERIPHERAL edge not on the main causal path. "
            f"Argue why this causal mechanism might not hold."
        ),
        "edge_reverse": (
            f"Argue that the causal link '{target_id}' ({target_desc}) "
            f"actually runs in the OPPOSITE DIRECTION. Instead of "
            f"{target_id.replace('->', ' causing ')}, argue that the causal "
            f"arrow should be reversed. Provide a specific mechanism for "
            f"reverse causation."
        ),
        "edge_spurious": (
            f"The forecaster's causal network does NOT include a direct link "
            f"'{target_id}'. Argue that this missing causal link DOES exist "
            f"and is important. Describe a specific causal mechanism connecting "
            f"these factors: {target_desc}."
        ),
        "missing_node": (
            "Identify an important causal factor that is MISSING from the "
            "forecaster's network. This should be a plausible factor that could "
            "significantly influence the outcome but was not included. Describe "
            "the factor and explain the causal mechanism by which it would "
            "affect the outcome."
        ),
        "irrelevant": (
            "Create a plausible-sounding piece of information that is TOPICALLY "
            "RELATED to the question's domain but should NOT logically affect "
            "any of the causal paths in the network. It should sound like it "
            "could matter at first glance but on reflection has no causal "
            "bearing on the outcome."
        ),
    }

    instruction = type_instructions[probe_type]

    return f"""\
A forecaster was asked: "{question}"

They estimated a probability of {probability:.2f} and constructed this causal network:

{network_context}

Your task: {instruction}

Respond as JSON:
{{
  "probe_text": "<your challenge — 2-4 sentences, specific and plausible>",
  "probe_type": "{probe_type}",
  "target_id": "{target_id}"
}}"""


# =============================================================================
# STAGE 3: CAUSAL PROBED FORECAST
# =============================================================================

CAUSAL_PROBED_FORECAST_SYSTEM = """\
You are an expert forecaster updating your estimate in light of new information \
about your causal model.

When presented with a challenge to an element of your causal network, you should:
- Consider how the challenge affects the causal paths leading to the outcome
- Evaluate whether the challenged element is structurally important to your reasoning
- Update your probability estimate appropriately
- Explain which causal paths are affected and why

Be honest about uncertainty. Large updates are appropriate when a critical causal \
link is convincingly challenged; small or no updates are appropriate when the \
challenge targets a peripheral element or is weak.

Respond with ONLY valid JSON. No other text."""


def build_causal_probed_forecast_prompt(
    question: str,
    initial_probability: float,
    nodes: list[dict],
    edges: list[dict],
    probe: dict,
    probe_target: dict,
) -> str:
    """Build the user prompt for Stage 3: causal probed forecast.

    Parameters
    ----------
    question : str
        The original forecasting question.
    initial_probability : float
        The probability from Stage 1.
    nodes : list[dict]
        Causal network nodes.
    edges : list[dict]
        Causal network edges.
    probe : dict
        The generated probe: {"probe_text": str, "probe_type": str, "target_id": str}.
    probe_target : dict
        The original probe target with structural metadata.

    Returns
    -------
    User prompt string.
    """
    network_context = _format_network_context(nodes, edges)
    probe_type = probe.get("probe_type", "")
    target_id = probe.get("target_id", "")
    probe_text = probe.get("probe_text", "")

    # Describe the challenge type
    category = PROBE_CATEGORIES.get(probe_type, "structural")
    if category == "node":
        challenge_desc = f"a challenge to the causal factor '{target_id}'"
    elif category == "edge":
        challenge_desc = f"a challenge to the causal link '{target_id}'"
    else:
        challenge_desc = "a structural challenge to your causal model"

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your causal network:
{network_context}

Now consider the following ({challenge_desc}):

"{probe_text}"

Think about how this would change the causal paths leading to the outcome.

Provide your updated forecast as JSON:
{{
  "updated_probability": <float between 0.01 and 0.99>,
  "shift_direction": "increased" or "decreased" or "unchanged",
  "reasoning": "<explain which causal paths are affected and how this changes your estimate>"
}}

Requirements:
- updated_probability must be between 0.01 and 0.99.
- Be honest: if a critical causal path is broken, update substantially. If a peripheral element is challenged, small or no update is fine."""


def build_causal_conversational_probe_message(
    probe: dict,
    probe_target: dict,
    current_prob: float,
) -> str:
    """Build the user message for a probe in conversational (multi-turn) mode.

    Parameters
    ----------
    probe : dict
        The generated probe.
    probe_target : dict
        The probe target with structural metadata.
    current_prob : float
        Current probability estimate.

    Returns
    -------
    User message string.
    """
    probe_type = probe.get("probe_type", "")
    target_id = probe.get("target_id", "")
    probe_text = probe.get("probe_text", "")

    category = PROBE_CATEGORIES.get(probe_type, "structural")
    if category == "node":
        challenge_desc = f"a challenge to the causal factor '{target_id}'"
    elif category == "edge":
        challenge_desc = f"a challenge to the causal link '{target_id}'"
    else:
        challenge_desc = "a structural challenge to your causal model"

    return (
        f"New information ({challenge_desc}):\n\n"
        f'"{probe_text}"\n\n'
        f"Think about how this affects the causal paths in your network. "
        f"Your current estimate is {current_prob:.2f}.\n\n"
        f"Respond as JSON: "
        f'{{"updated_probability": <float>, "shift_direction": "increased"|"decreased"|"unchanged", '
        f'"reasoning": "<explanation>"}}'
    )
