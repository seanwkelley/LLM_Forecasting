"""
Multi-agent prompt builders for causal discovery — persona injection,
specialist constraints, debate injection, and LLM aggregator prompts.
"""

from __future__ import annotations


def build_persona_system_prompt(base_prompt: str, persona: dict) -> str:
    """Prepend persona to domain system prompt.

    Parameters
    ----------
    base_prompt : str
        The domain system prompt (SYSTEM_PROMPT_MARKET or SYSTEM_PROMPT_CONFLICT).
    persona : dict
        Persona dict with 'name' and 'prompt' keys.

    Returns
    -------
    str
        Combined system prompt.
    """
    return f"ROLE: {persona['name']}\n{persona['prompt']}\n\n{base_prompt}"


def build_specialist_system_prompt(
    base_prompt: str,
    specialist: dict,
    allowed_vars: list[str],
) -> str:
    """Add specialist framing and variable constraint to system prompt.

    Parameters
    ----------
    base_prompt : str
        Domain system prompt.
    specialist : dict
        Specialist config with 'prompt' key.
    allowed_vars : list[str]
        Variables this specialist is responsible for.

    Returns
    -------
    str
        Combined system prompt.
    """
    var_list = ", ".join(allowed_vars)
    return (
        f"SPECIALIST ROLE:\n{specialist['prompt']}\n\n"
        f"YOUR ASSIGNED VARIABLES: {var_list}\n"
        f"You may only propose interventions targeting these variables. "
        f"You see the full system but focus your interventions on your assigned "
        f"variables to discover their causal relationships.\n\n"
        f"{base_prompt}"
    )


def build_debate_injection(
    other_name: str,
    other_hypothesis: str,
    other_last_intervention: str = "",
    other_last_result: str = "",
) -> str:
    """Build a short context injection with the other agent's latest findings.

    Parameters
    ----------
    other_name : str
        Display name of the other agent.
    other_hypothesis : str
        The other agent's current hypothesis (latest current_graph).
    other_last_intervention : str
        Description of the other agent's most recent intervention.
    other_last_result : str
        Summary of the other agent's most recent result.

    Returns
    -------
    str
        Context injection string (~200 tokens).
    """
    lines = [f"YOUR DEBATE PARTNER ({other_name}) reports:"]

    if other_hypothesis:
        lines.append(f"\nTheir current hypothesis:\n{other_hypothesis}")

    if other_last_intervention:
        lines.append(f"\nTheir last intervention: {other_last_intervention}")

    if other_last_result:
        lines.append(f"Result: {other_last_result}")

    lines.append(
        "\nConsider their findings when planning your next intervention. "
        "Do you agree or disagree with their hypothesis? What would you "
        "test to confirm or refute their claims?"
    )

    return "\n".join(lines)


def build_aggregator_prompt(
    specialist_results: list,
    variables: list[str],
    domain: str,
) -> str:
    """Build prompt for the LLM aggregator that merges specialist declarations.

    Parameters
    ----------
    specialist_results : list[AgentResult]
        Results from all specialist agents.
    variables : list[str]
        Full variable list for the domain.
    domain : str
        "market" or "conflict".

    Returns
    -------
    str
        Aggregator prompt.
    """
    var_list = "\n".join(f"  - {v}" for v in variables)

    specialist_sections = []
    for r in specialist_results:
        edges_str = "\n".join(
            f"    {src} -> {dst} ({r.edge_confidences.get((src, dst), '?')})"
            for src, dst in r.declared_edges
        )
        section = (
            f"--- Specialist: {r.agent_id} ---\n"
            f"Declared edges:\n{edges_str}\n\n"
            f"Evidence summary (excerpt):\n"
            f"{r.evidence_summary[:1000]}\n"
        )
        specialist_sections.append(section)

    specialists_text = "\n".join(specialist_sections)

    return f"""\
You are a causal graph aggregator for a {domain} simulation. Multiple specialist \
agents have each investigated a subset of the causal structure through interventional \
experiments. Your job is to merge their findings into a single unified causal graph.

VARIABLES:
{var_list}

SPECIALIST REPORTS:
{specialists_text}

INSTRUCTIONS:
1. Review each specialist's declared edges and evidence.
2. Where specialists agree on an edge, include it with high confidence.
3. Where specialists disagree, weigh their evidence carefully.
4. Add cross-domain edges that individual specialists may have missed — \
specialists only intervened on their assigned variables, but their evidence \
summaries show effects on ALL variables.
5. Look for edges between specialist domains (e.g., supply variables affecting \
demand variables) that no single specialist would have tested.

IMPORTANT:
- Include edges at "low" confidence if you have some evidence but are unsure.
- Err on inclusion — a missed real edge is worse than a spurious one.
- The agent_orders/agent_recommendation and clearing_price/faction_action variables \
are shared across all specialists — pay special attention to edges involving these.

Respond in JSON format:
```json
{{
    "per_variable": {{
        "variable_name": {{
            "parents": ["var_A", "var_B"],
            "children": ["var_C", "var_D"]
        }}
    }},
    "final_graph": [
        {{"from": "var_A", "to": "var_B", "confidence": "high/medium/low"}}
    ],
    "cross_domain_edges": [
        {{"from": "var_X", "to": "var_Y", "confidence": "medium", \
"reasoning": "Evidence from specialist Z showed..."}}
    ],
    "conflicts_resolved": [
        {{"edge": "var_A -> var_B", "resolution": "included/excluded", \
"reasoning": "..."}}
    ],
    "limitations": "What aspects of the causal structure are you least certain about?"
}}
```"""
