"""
Open-Ended Causal Discovery Prompts — model must discover both variables AND edges.

Unlike the standard prompts (prompts.py), these do NOT provide the variable list.
The model observes raw simulation output and must identify the relevant causal
variables, then discover edges through interventional experiments.

This is the harder, more realistic variant of the causal discovery task.
"""

from __future__ import annotations


# =============================================================================
# System Prompts (no variable list provided)
# =============================================================================

SYSTEM_PROMPT_MARKET_OPEN = """\
You are a causal scientist analyzing a simulated multi-agent market. Agents \
trade a commodity each period. Your goal is to discover the causal structure — \
which variables exist and which cause which — through targeted interventional \
experiments.

You will observe raw simulation output after each intervention. From this data, \
you must:
1. IDENTIFY the key causal variables in the system
2. DISCOVER which variables cause which through interventional experiments

You can run three types of interventions:
- **event**: Inject an exogenous shock (supply disruption, demand surge, etc.)
- **trait**: Override an agent parameter (production cost, demand, cash, etc.)
- **action**: Force a specific agent to take a specific action (set order price/quantity)

After each intervention, you will see how the market responds compared to a \
no-intervention baseline. Use the differences to infer causal edges.

IMPORTANT CAUSAL REASONING PRINCIPLES:
- Correlation does not imply causation. Two variables may correlate because \
they share a common cause.
- An intervention fixes a variable and lets everything else react. If changing \
X causes Y to change, there is a causal path from X to Y.
- Distinguish DIRECT from INDIRECT effects. If X -> Y -> Z, intervening on X \
changes Z, but X does not directly cause Z.
- Feedback loops exist: A may cause B which causes A in the next period.
- Not all variables are equally informative to test. Prioritize interventions \
that distinguish between competing hypotheses.

You have a limited budget of interventions. Use them wisely.
"""

SYSTEM_PROMPT_CONFLICT_OPEN = """\
You are a causal scientist analyzing a simulated geopolitical conflict between \
two factions. Your goal is to discover the causal structure — which variables \
exist and which cause which — through targeted interventional experiments.

You will observe raw simulation output after each intervention. From this data, \
you must:
1. IDENTIFY the key causal variables in the system
2. DISCOVER which variables cause which through interventional experiments

You can run three types of interventions:
- **event**: Inject an exogenous shock (border incident, peace initiative, etc.)
- **trait**: Override an agent parameter (hawk/dove disposition, resources, etc.)
- **action**: Force a specific agent to take a specific action

After each intervention, you will see how the conflict state changes compared \
to a no-intervention baseline. Use the differences to infer causal edges.

IMPORTANT CAUSAL REASONING PRINCIPLES:
- Correlation does not imply causation. Variables may correlate through common causes.
- Interventions fix a variable and let everything else react naturally.
- Some effects are NONLINEAR: the same action by both factions may amplify or \
dampen depending on context.
- Distinguish DIRECT from INDIRECT effects through targeted interventions.
- Feedback loops exist: escalation affects agent behavior which affects escalation.
- Budget your interventions carefully — prioritize those that distinguish hypotheses.

You have a limited budget of interventions. Use them wisely.
"""


# =============================================================================
# Observation Prompt (no variable list — model discovers variables)
# =============================================================================

def build_observation_prompt_open(
    domain: str,
    history_summary: str,
) -> str:
    """Build prompt for initial observation — model must identify variables."""
    return f"""\
You have been given observational data from a {domain} simulation. Analyze the \
data to identify the key causal variables and form an initial hypothesis about \
the causal structure.

SIMULATION HISTORY:
{history_summary}

Your task:
1. IDENTIFY the key causal variables in this system. Name each variable with a \
short, descriptive identifier (e.g., "production_cost", "clearing_price").
2. For each pair of variables that appear related, hypothesize the causal direction.
3. Identify which relationships are most uncertain and would benefit from \
interventional testing.

Respond in JSON format:
```json
{{
    "identified_variables": [
        {{"id": "variable_name", "description": "What this variable represents"}},
        ...
    ],
    "confident_edges": [
        {{"from": "var_A", "to": "var_B", "confidence": "high", "reasoning": "..."}},
        ...
    ],
    "uncertain_edges": [
        {{"from": "var_X", "to": "var_Y", "confidence": "low", "reasoning": "..."}},
        ...
    ],
    "priority_interventions": [
        {{"description": "...", "rationale": "..."}}
    ]
}}
```"""


# =============================================================================
# Intervention Proposal Prompt (open-ended)
# =============================================================================

def build_intervention_prompt_open(
    domain: str,
    current_hypothesis: str,
    budget_remaining: int,
    intervention_types: str,
) -> str:
    """Build prompt for proposing the next intervention — no variable list given."""
    return f"""\
You are conducting causal discovery on a {domain} simulation.

YOUR CURRENT CAUSAL MODEL:
{current_hypothesis}

BUDGET REMAINING: {budget_remaining} interventions

AVAILABLE INTERVENTION TYPES:
{intervention_types}

CRITICAL RULES:
1. NEVER repeat an intervention you already ran.
2. Use ALL THREE intervention types (action, trait, event).
3. Use EXTREME values to maximize detectable effects.
4. Distinguish DIRECT from INDIRECT causation.
5. If you've identified new variables from previous results, update your model.

Propose the single most informative intervention to run next.

Respond in JSON format:
```json
{{
    "intervention": {{
        "type": "action" or "trait" or "event",
        "target": {{...}},
        "run_periods": 3,
        "description": "Brief description of what this tests"
    }},
    "hypothesis_being_tested": "What causal edge or structure does this intervention test?",
    "expected_if_edge_exists": "What outcome would confirm the causal edge?",
    "expected_if_no_edge": "What outcome would disconfirm the causal edge?"
}}
```

For EVENT targets: {{"type": "event", "target": {{"shock_type": "supply_disruption", "magnitude": 2.0}}, ...}}
For TRAIT targets: {{"type": "trait", "target": {{"role": "producer", "param": "production_cost", "value": 200}}, ...}}
For ACTION targets: {{"type": "action", "target": {{"agent_id": "speculator_A", "param": "quantity", "value": 0}}, ...}}"""


# =============================================================================
# Update Prompt (full graph, open-ended — model may add new variables)
# =============================================================================

def build_update_prompt_open(
    domain: str,
    current_graph: str,
    intervention_result: str,
) -> str:
    """Build prompt for updating the causal model — model can add/remove variables."""
    return f"""\
INTERVENTION RESULT:
{intervention_result}

YOUR CURRENT CAUSAL MODEL:
{current_graph}

Based on this result, output your COMPLETE updated causal model. You may:
- Add NEW variables you've discovered from the intervention results
- Add or remove edges based on the evidence
- Update confidence levels

IMPORTANT: If this intervention showed that a variable did NOT change when your \
graph predicts it should have, REMOVE that edge. Your graph should only contain \
edges with active supporting evidence. Do not keep edges just because they were \
in your previous graph — re-evaluate each one.

Respond in JSON with:
{{
    "analysis": "Brief interpretation of this result",
    "identified_variables": [
        {{"id": "variable_name", "description": "What this variable represents"}},
        ...
    ],
    "current_graph": [
        {{"from": "var1", "to": "var2", "confidence": "high/medium/low"}},
        ...
    ],
    "key_uncertainties": ["..."]
}}"""


# =============================================================================
# Final Declaration Prompt (open-ended)
# =============================================================================

def build_declaration_prompt_open(
    domain: str,
    current_hypothesis: str,
    all_interventions_summary: str,
    evidence_summary: str = "",
) -> str:
    """Build prompt for final declaration — model declares variables AND edges."""
    evidence_block = ""
    if evidence_summary:
        evidence_block = f"""
PROGRAMMATIC EVIDENCE SUMMARY:
{evidence_summary}
"""

    return f"""\
You have completed all your interventions on a {domain} simulation. Now declare \
your final causal model — both the VARIABLES and the EDGES.

{evidence_block}
YOUR RUNNING HYPOTHESIS:
{current_hypothesis}

INTERVENTION HISTORY:
{all_interventions_summary}

INSTRUCTIONS:
1. List ALL causal variables you've identified in the system.
2. For each variable, list its direct parents (causes) and children (effects).
3. Include edges at "low" confidence if you have some evidence but are unsure.
4. Err on the side of INCLUSION — a false negative is worse than a false positive.

Respond in JSON format:
```json
{{
    "identified_variables": [
        {{"id": "variable_name", "description": "What this variable represents"}},
        ...
    ],
    "final_graph": [
        {{"from": "var_A", "to": "var_B", "confidence": "high/medium/low"}},
        ...
    ],
    "feedback_loops": [
        {{"cycle": ["var_A", "var_B", "var_A"], "reasoning": "..."}},
        ...
    ],
    "limitations": "What aspects of the causal structure are you least certain about?"
}}
```"""
