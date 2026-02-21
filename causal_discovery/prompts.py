"""
Causal Modeler Agent Prompts — LLM prompts for causal discovery.

Designed for Llama 3.3 70B. Supports:
1. Initial observation and hypothesis formation
2. Intervention proposal (structured JSON output)
3. Hypothesis update after receiving intervention results
4. Final graph declaration
"""

from __future__ import annotations


# =============================================================================
# System Prompts
# =============================================================================

SYSTEM_PROMPT_MARKET = """\
You are a causal scientist analyzing a simulated commodity market. Your goal is \
to discover the causal structure — which variables cause which — through targeted \
interventional experiments.

The market has these variables:
- shock: exogenous market events (supply disruptions, demand changes, etc.)
- production_cost: cost per unit for producers
- demand_per_period: quantity consumers need per period
- demand_value: maximum price consumers will pay
- storage_cost: per-unit holding cost
- cash: agent cash holdings
- inventory: agent inventory holdings
- price_history: recent price trajectory
- agent_orders: submitted buy/sell orders (limit prices and quantities)
- clearing_price: the market clearing price (determined by order matching)
- volume: total units traded
- fundamental_price: a computed reference price

Some of these variables CAUSE others. Your job is to figure out which causal \
edges exist by running interventions — fixing a variable at a specific value \
and observing what changes downstream.

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

You have a limited budget of interventions. Use them wisely.
"""

SYSTEM_PROMPT_CONFLICT = """\
You are a causal scientist analyzing a simulated geopolitical conflict between \
two factions (Novaris and Tethys). Your goal is to discover the causal structure \
— which variables cause which — through targeted interventional experiments.

The conflict simulation has these variables:
- shock: exogenous events (border incidents, peace initiatives, economic crises, etc.)
- hawk_score: agent disposition (0=dove, 1=hawk) — influences action recommendations
- escalation_index: overall conflict intensity (0-10 scale, the main outcome)
- resources: faction budget for actions
- gdp: faction economic health
- military_strength: faction military capability
- political_stability: faction political stability
- military_balance: relative military advantage between factions
- territory_controlled: fraction of territory held by aggressor
- sanctions_level: international sanctions on aggressor
- international_support: international support for defender
- agent_recommendation: individual agent's recommended action
- faction_action: aggregated faction action (after internal weighting)

Some of these variables CAUSE others. Your job is to figure out which causal \
edges exist by running interventions — fixing a variable at a specific value \
and observing what changes downstream.

IMPORTANT CAUSAL REASONING PRINCIPLES:
- Correlation does not imply causation. Variables may correlate through common causes.
- Interventions fix a variable and let everything else react naturally.
- Some effects are NONLINEAR: the same action by both factions may amplify or \
dampen depending on whether they escalate together or diverge.
- Individual agent actions are AGGREGATED within factions using weighted voting. \
A single agent's override may have limited effect on the faction's action.
- Feedback loops exist: escalation affects agent behavior which affects escalation.
- Budget your interventions carefully — prioritize those that distinguish hypotheses.
"""


# =============================================================================
# Observation Prompt (Phase 0: initial data analysis)
# =============================================================================

def build_observation_prompt(
    domain: str,
    history_summary: str,
    variables: list[str],
) -> str:
    """Build prompt for initial observation and hypothesis formation.

    The agent receives a summary of the simulation history and forms
    initial hypotheses about which causal edges exist.
    """
    return f"""\
You have been given observational data from a {domain} simulation. Analyze the \
correlations and patterns to form an initial hypothesis about the causal structure.

SIMULATION HISTORY:
{history_summary}

VARIABLES: {', '.join(variables)}

Based on the observational data, identify:
1. Which pairs of variables appear correlated?
2. For each correlation, what are the possible causal explanations? \
(A causes B, B causes A, or common cause C causes both)
3. Which edges are you most confident about from observation alone?
4. Which edges are most uncertain and would benefit from interventional testing?

Respond in JSON format:
```json
{{
    "confident_edges": [
        {{"from": "variable_A", "to": "variable_B", "confidence": "high", "reasoning": "..."}},
        ...
    ],
    "uncertain_edges": [
        {{"from": "variable_X", "to": "variable_Y", "confidence": "low", "reasoning": "..."}},
        ...
    ],
    "candidate_common_causes": [
        {{"variables": ["var_A", "var_B"], "possible_cause": "var_C", "reasoning": "..."}},
        ...
    ],
    "priority_interventions": [
        {{"description": "...", "rationale": "..."}}
    ]
}}
```"""


# =============================================================================
# Intervention Proposal Prompt
# =============================================================================

def build_intervention_prompt(
    domain: str,
    variables: list[str],
    current_hypothesis: str,
    past_interventions: str,
    budget_remaining: int,
    intervention_types: str,
) -> str:
    """Build prompt for proposing the next intervention.

    The agent reviews its current hypothesis and past intervention results
    to propose the most informative next intervention.
    """
    return f"""\
You are conducting causal discovery on a {domain} simulation.

YOUR CURRENT CAUSAL HYPOTHESIS:
{current_hypothesis}

PAST INTERVENTIONS AND RESULTS:
{past_interventions if past_interventions else "None yet — this is your first intervention."}

BUDGET REMAINING: {budget_remaining} interventions

AVAILABLE INTERVENTION TYPES:
{intervention_types}

AVAILABLE VARIABLES: {', '.join(variables)}

CRITICAL RULES:
1. NEVER repeat an intervention you already ran. If the same variable was already tested \
with the same type of intervention, you MUST choose a DIFFERENT variable or type.
2. Use ALL THREE intervention types (action, trait, event). If you haven't used events yet, \
use one now. If you haven't used action overrides, use one now.
3. Use EXTREME values to maximize detectable effects. For traits, try 0 or 10x the normal \
value, not small changes. For events, use magnitude >= 2.0.
4. If an intervention showed "No detectable effect", do NOT retry the same thing. Either \
try a different variable or try a much more extreme value.
5. Distinguish DIRECT from INDIRECT causation. If X -> Y -> Z, intervening on X changes Z \
but X does not DIRECTLY cause Z. To test whether X directly causes Z, you must also \
intervene on the mediator Y.
6. Remember: correlation between two variables may be due to a COMMON CAUSE, not direct \
causation. Intervene on the suspected cause to test this.

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

For EVENT targets, use this exact format:
{{"type": "event", "target": {{"shock_type": "supply_disruption", "magnitude": 2.0}}, ...}}

For TRAIT targets (single agent), use this exact format:
{{"type": "trait", "target": {{"agent_id": "producer_A", "param": "production_cost", "value": 0}}, ...}}

For TRAIT targets (all agents of a role), use this exact format:
{{"type": "trait", "target": {{"role": "producer", "param": "production_cost", "value": 200}}, ...}}

For ACTION targets, use this exact format:
{{"type": "action", "target": {{"agent_id": "speculator_A", "param": "quantity", "value": 0}}, ...}}"""


# =============================================================================
# Hypothesis Update Prompt
# =============================================================================

def build_update_prompt(
    domain: str,
    variables: list[str],
    current_hypothesis: str,
    intervention_description: str,
    intervention_result: str,
) -> str:
    """Build prompt for updating the causal hypothesis after an intervention.

    The agent interprets the intervention result and updates its edge
    confidence matrix.
    """
    return f"""\
You just ran an intervention on a {domain} simulation. Update your causal hypothesis \
based on the results.

YOUR CURRENT HYPOTHESIS:
{current_hypothesis}

INTERVENTION:
{intervention_description}

RESULT:
{intervention_result}

Analyze the result:
1. Did the intervention change the expected downstream variables?
2. Does this confirm or disconfirm specific causal edges?
3. Are there surprising effects that suggest edges you hadn't considered?
4. Should any edge confidences be upgraded or downgraded?

Respond in JSON format:
```json
{{
    "analysis": "Your interpretation of what the intervention result means causally",
    "edge_updates": [
        {{"from": "var_A", "to": "var_B", "old_confidence": "low/medium/high/absent", "new_confidence": "low/medium/high/absent", "reasoning": "..."}},
        ...
    ],
    "current_graph": [
        {{"from": "var_A", "to": "var_B", "confidence": "high"}},
        ...
    ],
    "key_uncertainties": ["What edges are still uncertain after this intervention?"]
}}
```"""


# =============================================================================
# Evidence Summary (programmatic, no LLM calls)
# =============================================================================

def build_evidence_summary(
    all_results: list,
    variables: list[str],
    delta_threshold: float = 0.01,
) -> str:
    """Build a per-variable evidence summary from intervention results.

    For each variable, lists which interventions caused it to change
    and which variables changed when it was the target of an intervention.
    No LLM calls — pure computation over InterventionResult objects.
    """
    # Track: when variable X was intervened on, which other variables changed?
    # This gives evidence for X -> Y edges.
    caused_by = {}   # {target_var: [(intervened_var, delta, intervention_desc), ...]}
    effects_of = {}  # {intervened_var: [(affected_var, delta, intervention_desc), ...]}

    for result in all_results:
        intervention = result.intervention
        desc = intervention.description or f"{intervention.type} intervention"

        # Determine which variable was intervened on
        target = intervention.target
        if intervention.type == "trait":
            intervened_var = target.get("param", "unknown")
        elif intervention.type == "action":
            intervened_var = "agent_orders" if "param" in target else "agent_recommendation"
        elif intervention.type == "event":
            intervened_var = "shock"
        else:
            intervened_var = "unknown"

        # Compute deltas for each returned variable
        for var in result.variables_returned:
            baseline_vals = [
                p.get(var) for p in result.baseline_trajectory
                if p.get(var) is not None
            ]
            int_vals = [
                p.get(var) for p in result.intervention_trajectory
                if p.get(var) is not None
            ]
            if not baseline_vals or not int_vals:
                continue

            b_mean = sum(baseline_vals) / len(baseline_vals)
            i_mean = sum(int_vals) / len(int_vals)
            delta = i_mean - b_mean

            if abs(delta) > delta_threshold:
                # Map faction-prefixed vars to generic names for grouping
                generic_var = _to_generic_var(var)

                entry = (intervened_var, delta, desc)
                caused_by.setdefault(generic_var, []).append(entry)

                entry2 = (generic_var, delta, desc)
                effects_of.setdefault(intervened_var, []).append(entry2)

    # Format the summary
    lines = ["EVIDENCE SUMMARY FROM INTERVENTIONS", "=" * 40, ""]

    # Section 1: What each intervention target affected
    lines.append("EFFECTS OF EACH INTERVENTION:")
    for var in sorted(effects_of.keys()):
        entries = effects_of[var]
        affected = {}
        for affected_var, delta, desc in entries:
            if affected_var not in affected:
                affected[affected_var] = []
            affected[affected_var].append(delta)

        lines.append(f"  Intervening on {var}:")
        for av in sorted(affected.keys()):
            deltas = affected[av]
            avg_delta = sum(deltas) / len(deltas)
            lines.append(f"    -> {av} changed (avg delta={avg_delta:+.4f}, {len(deltas)} obs)")
        lines.append("")

    # Section 2: For each variable, what interventions caused it to change
    lines.append("WHAT CAUSED EACH VARIABLE TO CHANGE:")
    for var in sorted(variables):
        if var in caused_by:
            entries = caused_by[var]
            sources = {}
            for src_var, delta, desc in entries:
                if src_var not in sources:
                    sources[src_var] = []
                sources[src_var].append(delta)

            lines.append(f"  {var} changed when:")
            for sv in sorted(sources.keys()):
                deltas = sources[sv]
                avg_delta = sum(deltas) / len(deltas)
                lines.append(f"    <- {sv} was intervened on (avg delta={avg_delta:+.4f}, {len(deltas)} obs)")
        else:
            lines.append(f"  {var}: no observed changes from interventions")
        lines.append("")

    return "\n".join(lines)


def _to_generic_var(var: str) -> str:
    """Map aggregate/prefixed variable names to ground truth variable names.

    Faction-prefixed: 'novaris_gdp' -> 'gdp'
    Market aggregates: 'avg_bid_price' -> 'agent_orders', 'total_cash' -> 'cash'
    Conflict aggregates: 'novaris_rec_escalation' -> 'agent_recommendation'
    """
    # Explicit aggregate mappings (check before prefix stripping)
    _AGG_MAP = {
        # Market
        "avg_bid_price": "agent_orders",
        "avg_ask_price": "agent_orders",
        "total_bid_qty": "agent_orders",
        "total_ask_qty": "agent_orders",
        "total_cash": "cash",
        "total_inventory": "inventory",
        # Conflict
        "novaris_rec_escalation": "agent_recommendation",
        "tethys_rec_escalation": "agent_recommendation",
        "novaris_action_delta": "faction_action",
        "tethys_action_delta": "faction_action",
    }
    if var in _AGG_MAP:
        return _AGG_MAP[var]

    # Faction prefixes (conflict domain)
    for prefix in ("novaris_", "tethys_"):
        if var.startswith(prefix):
            return var[len(prefix):]

    return var


# =============================================================================
# Final Declaration Prompt
# =============================================================================

def build_declaration_prompt(
    domain: str,
    variables: list[str],
    current_hypothesis: str,
    all_interventions_summary: str,
    evidence_summary: str = "",
) -> str:
    """Build prompt for the final causal graph declaration.

    The agent reviews all evidence and declares its best estimate of
    the causal graph. Uses per-variable enumeration to reduce omissions.
    """
    evidence_block = ""
    if evidence_summary:
        evidence_block = f"""
PROGRAMMATIC EVIDENCE SUMMARY:
The following was computed automatically from your intervention results. Use it \
to remind yourself what you observed — do not rely solely on memory.

{evidence_summary}
"""

    var_list = "\n".join(f"  - {v}" for v in variables)

    return f"""\
You have completed all your interventions on a {domain} simulation. Now declare \
your final causal graph.

VARIABLES:
{var_list}
{evidence_block}
YOUR RUNNING HYPOTHESIS:
{current_hypothesis}

INTERVENTION HISTORY:
{all_interventions_summary}

INSTRUCTIONS — Per-variable enumeration:
Go through EACH variable listed above and determine:
1. What are its PARENTS (direct causes)? Which variables, when intervened on, \
caused this variable to change?
2. What are its CHILDREN (direct effects)? When this variable was intervened on, \
which other variables changed?

IMPORTANT GUIDANCE:
- Err on the side of INCLUSION. Include edges you have moderate evidence for. \
A false negative (missing a real edge) is WORSE than a false positive (including \
a spurious edge) for this task.
- If a variable changed when another was intervened on, that is evidence of a \
causal edge — include it unless you have strong reason to believe it is purely \
indirect.
- Only exclude edges you are confident do NOT exist (i.e., you tested the \
intervention and saw NO effect).
- Include edges at "low" confidence if you have some evidence but are unsure.

Respond in JSON format:
```json
{{
    "per_variable": {{
        "variable_name": {{
            "parents": ["var_A", "var_B"],
            "children": ["var_C", "var_D"]
        }},
        ...
    }},
    "final_graph": [
        {{"from": "var_A", "to": "var_B", "confidence": "high/medium/low"}},
        ...
    ],
    "absent_edges": [
        {{"from": "var_X", "to": "var_Y", "reasoning": "Why this edge does not exist"}},
        ...
    ],
    "feedback_loops": [
        {{"cycle": ["var_A", "var_B", "var_C", "var_A"], "reasoning": "..."}},
        ...
    ],
    "common_causes": [
        {{"effect_1": "var_X", "effect_2": "var_Y", "cause": "var_Z", "reasoning": "..."}},
        ...
    ],
    "limitations": "What aspects of the causal structure are you least certain about?"
}}
```"""


# =============================================================================
# Intervention type descriptions for each domain
# =============================================================================

MARKET_INTERVENTION_TYPES = """\
1. ACTION OVERRIDE: Force a specific agent's order.
   - target: {agent_id, param, value}
   - agent_id: one of [producer_A, producer_B, consumer_A, consumer_B, consumer_C, speculator_A, speculator_B]
   - param: "limit_price" (the price in the order) or "quantity" (number of units)
   - value: the forced value (e.g., limit_price=50.0 or quantity=0)
   - Example: {"type": "action", "target": {"agent_id": "producer_A", "param": "limit_price", "value": 50.0}}

2. TRAIT OVERRIDE: Change an agent's fundamental parameter.
   - Single agent: target: {agent_id, param, value}
   - ALL agents of a role: target: {role, param, value}
     IMPORTANT: Single-agent trait overrides on infra-marginal agents often produce
     zero effect because that agent is not the marginal price-setter. Use role-level
     overrides to change ALL agents of a role for a detectable signal.
   - param options by role:
     - producer: "production_cost", "production_capacity"
     - consumer: "demand_per_period", "demand_value"
     - any agent: "storage_cost", "cash", "inventory"
   - role: one of ["producer", "consumer", "speculator"]
   - Single-agent example: {"type": "trait", "target": {"agent_id": "consumer_A", "param": "demand_per_period", "value": 50}}
   - Role-level example: {"type": "trait", "target": {"role": "producer", "param": "production_cost", "value": 200}}

3. EVENT OVERRIDE: Inject or suppress a market shock.
   - target: {shock_type, magnitude} or {shock_type, suppress: true}
   - shock_type: one of [supply_disruption, demand_surge, demand_drop, cost_reduction, storage_crisis, subsidy]
   - magnitude: the shock strength (e.g., 1.5 for 50% cost increase)
   - Example: {"type": "event", "target": {"shock_type": "supply_disruption", "magnitude": 1.5}}
"""

CONFLICT_INTERVENTION_TYPES = """\
1. ACTION OVERRIDE: Force a specific agent's recommendation.
   - target: {agent_id, value}
   - agent_id: one of [krasnov, volkov, petrova, morozov, marchetti, bondar, kovalenko]
   - value: one of [peace_talks, ceasefire_offer, humanitarian_aid, trade_agreement, \
troop_withdrawal, intelligence_gathering, economic_sanctions, propaganda_campaign, \
military_buildup, cyber_attack, proxy_support, naval_blockade, border_incursion, \
limited_strike, full_scale_attack]
   - Example: {"type": "action", "target": {"agent_id": "krasnov", "value": "peace_talks"}}

2. TRAIT OVERRIDE: Change an agent's disposition.
   - Single agent: target: {agent_id, param, value}
   - ALL agents in a faction: target: {faction, param, value}
     IMPORTANT: Single-agent trait overrides may have limited effect because
     individual recommendations are aggregated within factions using weighted
     voting. Use faction-level overrides to change ALL agents in a faction
     for a stronger, more detectable signal.
   - param: "hawk_dove" (0.0 = dove, 1.0 = hawk)
   - faction: one of ["novaris", "tethys"]
   - Single-agent example: {"type": "trait", "target": {"agent_id": "krasnov", "param": "hawk_dove", "value": 0.1}}
   - Faction-level example: {"type": "trait", "target": {"faction": "novaris", "param": "hawk_dove", "value": 0.1}}

3. EVENT OVERRIDE: Inject or suppress an external event.
   - target: {shock_type, magnitude} or {shock_type, suppress: true}
   - shock_type: one of [border_incident, diplomatic_crisis, peace_initiative, \
economic_crisis, military_incident, international_pressure]
   - magnitude: effect size (e.g., 1.0 for +1.0 to escalation index)
   - Example: {"type": "event", "target": {"shock_type": "border_incident", "magnitude": 1.2}}
"""


# =============================================================================
# History formatting helpers
# =============================================================================

def format_market_history(history_data: dict, n_periods: int = 10) -> str:
    """Format market simulation history for the observation prompt."""
    lines = []

    prices = history_data.get("price_history", [])
    volumes = history_data.get("volume_history", [])
    fundamentals = history_data.get("fundamental_history", [])

    # Show last n_periods
    start = max(0, len(prices) - n_periods)

    lines.append("Period | Clearing Price | Volume | Fundamental Price")
    lines.append("-------|---------------|--------|------------------")
    for i in range(start, len(prices)):
        p = prices[i]
        v = volumes[i] if i < len(volumes) else "?"
        f = fundamentals[i] if i < len(fundamentals) else "?"
        lines.append(f"  {i+1:4d} | ${p:>12.2f} | {v:>6} | ${f:>12.2f}" if isinstance(f, (int, float)) else
                     f"  {i+1:4d} | ${p:>12.2f} | {v:>6} | {f}")

    # Add summary stats
    if prices:
        import numpy as np
        p_arr = np.array(prices[start:])
        lines.append(f"\nSummary (last {len(p_arr)} periods):")
        lines.append(f"  Mean price: ${np.mean(p_arr):.2f}")
        lines.append(f"  Std price: ${np.std(p_arr):.2f}")
        lines.append(f"  Price range: ${np.min(p_arr):.2f} - ${np.max(p_arr):.2f}")
        if len(p_arr) > 1:
            returns = np.diff(p_arr) / p_arr[:-1]
            lines.append(f"  Return volatility: {np.std(returns):.4f}")

    # Add order log summary if available
    orders_log = history_data.get("orders_log", [])
    if orders_log:
        last_period = orders_log[-1] if orders_log else {}
        orders = last_period.get("orders", [])
        if orders:
            lines.append(f"\nLast period orders:")
            for o in orders:
                lines.append(f"  {o['agent_id']:15s} | {o['side']:4s} | qty={o['quantity']:3d} | "
                           f"price=${o['limit_price']:.2f}")

    return "\n".join(lines)


def format_conflict_history(history_data: dict, n_periods: int = 10) -> str:
    """Format conflict simulation history for the observation prompt."""
    lines = []

    ei_history = history_data.get("escalation_history", [])
    actions_log = history_data.get("actions_log", [])

    start = max(0, len(ei_history) - n_periods)

    lines.append("Period | EI    | Novaris Action       | Tethys Action")
    lines.append("-------|-------|---------------------|--------------------")
    for i in range(start, len(ei_history)):
        ei = ei_history[i]
        if i < len(actions_log):
            nov = actions_log[i].get("novaris_action", "?")
            teth = actions_log[i].get("tethys_action", "?")
        else:
            nov, teth = "?", "?"
        lines.append(f"  {i+1:4d} | {ei:5.2f} | {nov:20s} | {teth:20s}")

    if ei_history:
        import numpy as np
        ei_arr = np.array(ei_history[start:])
        lines.append(f"\nSummary (last {len(ei_arr)} periods):")
        lines.append(f"  Mean EI: {np.mean(ei_arr):.2f}")
        lines.append(f"  Std EI: {np.std(ei_arr):.2f}")
        lines.append(f"  EI range: {np.min(ei_arr):.2f} - {np.max(ei_arr):.2f}")

    return "\n".join(lines)
