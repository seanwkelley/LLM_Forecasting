"""
Composable Framework Pool
=========================

Defines four composable axes (Method × Lens × Focus × Bias) that combine
to create a large pool of unique analytical frameworks. Each axis contributes
a non-overlapping section to the prompt:

- Method:  reasoning structure (CoT steps)
- Lens:    interpretive bias (how ambiguity is read)
- Focus:   evidence attention (which signals dominate)
- Bias:    cognitive distortion (systematic reasoning flaw)

Usage:
    from forecasting.framework_pool import generate_pool, sample_frameworks

    pool = generate_pool()          # 5×5×5×8 = 1000 combinations
    frameworks = sample_frameworks(n=10, seed=42)  # reproducible sample
"""

import hashlib
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Axis 1: Method (reasoning structure)
# ---------------------------------------------------------------------------

METHODS = [
    {
        "id": "base_rate",
        "label": "Base Rate Anchoring",
        "system_description": (
            "ALWAYS start from historical base rates of government collapse "
            "in comparable crises, then adjust incrementally based on case-specific "
            "evidence. Resist the temptation to anchor on vivid details — ground "
            "your estimate in statistical frequencies of similar outcomes."
        ),
        "cot_steps": (
            "1. REFERENCE CLASS: Identify the most appropriate reference class for this "
            "crisis. What is the historical base rate of government collapse in such crises? "
            "Estimate a specific percentage.\n"
            "2. SIMILARITY ASSESSMENT: How closely does this case match the reference class? "
            "Note key similarities and differences.\n"
            "3. ADJUSTMENT FACTORS: Identify 2-3 factors that push the probability UP from the "
            "base rate and 2-3 that push it DOWN. Quantify each adjustment.\n"
            "4. ANCHORED ESTIMATE: Starting from your base rate, apply adjustments sequentially. "
            "Show your arithmetic.\n"
            "5. FINAL PROBABILITY: State your adjusted estimate. Ensure it hasn't drifted too far "
            "from the base rate without strong justification."
        ),
    },
    {
        "id": "scenario_tree",
        "label": "Scenario Tree",
        "system_description": (
            "Enumerate 3-5 distinct future paths (e.g., full invasion, negotiated "
            "settlement, frozen conflict, internal coup, economic capitulation), assign "
            "a probability to each path, then calculate the collapse probability as the "
            "weighted sum across paths."
        ),
        "cot_steps": (
            "1. ENUMERATE SCENARIOS: Define 3-5 mutually exclusive, collectively exhaustive "
            "paths forward. Name each scenario clearly.\n"
            "2. SCENARIO PROBABILITIES: Assign a probability to each scenario. They MUST sum "
            "to 1.0. Show the values.\n"
            "3. CONDITIONAL COLLAPSE: For each scenario, estimate P(collapse | scenario). "
            "Some scenarios may have high collapse probability; others may have near-zero.\n"
            "4. WEIGHTED CALCULATION: Calculate total P(collapse) = sum of "
            "P(scenario_i) * P(collapse | scenario_i). Show the arithmetic.\n"
            "5. FINAL PROBABILITY: State the calculated result. Cross-check it against "
            "your intuition — if they diverge, explain why."
        ),
    },
    {
        "id": "historical_analogy",
        "label": "Historical Analogy",
        "system_description": (
            "Identify the closest historical parallel to this crisis and use its outcome "
            "as your primary anchor. Adjust for key differences between the historical "
            "case and the current situation."
        ),
        "cot_steps": (
            "1. CANDIDATE ANALOGIES: Identify 2-3 historical cases that most closely resemble "
            "this crisis (consider: great-power vs. small-state conflicts, territorial disputes, "
            "military mobilizations, sanctions campaigns).\n"
            "2. BEST ANALOGY: Select the single best historical parallel. Explain why it is "
            "the most relevant.\n"
            "3. HISTORICAL OUTCOME: What happened in the analogous case? Did the smaller state's "
            "government collapse? Over what timeframe?\n"
            "4. KEY DIFFERENCES: Identify 2-3 important ways the current situation differs from "
            "the historical case. For each, state whether it makes collapse MORE or LESS likely.\n"
            "5. FINAL PROBABILITY: Anchor on the historical outcome and adjust for differences. "
            "State your estimate."
        ),
    },
    {
        "id": "key_indicator",
        "label": "Key Indicator",
        "system_description": (
            "Identify the SINGLE most diagnostic variable — the one indicator that "
            "historically has the strongest predictive power for government collapse — "
            "and weight it heavily in your estimate. Other factors matter, but one "
            "variable dominates."
        ),
        "cot_steps": (
            "1. INDICATOR SCAN: Review all available variables (territory, GDP, military balance, "
            "international support, sanctions, crisis level, events).\n"
            "2. KEY INDICATOR SELECTION: Choose the SINGLE most diagnostic variable. Justify why "
            "this indicator has the highest predictive validity for government collapse.\n"
            "3. INDICATOR READING: What does this key indicator currently show? Is it at a "
            "critical threshold? What direction is it trending?\n"
            "4. SECONDARY CHECK: Briefly check if other indicators contradict or reinforce the "
            "key indicator's signal. Note any major divergences.\n"
            "5. FINAL PROBABILITY: Derive your estimate primarily from the key indicator, "
            "with minor adjustments from secondary factors."
        ),
    },
    {
        "id": "structural",
        "label": "Structural Fundamentals",
        "system_description": (
            "Focus on deep structural factors — institutional resilience, geography, "
            "resource fundamentals, demographic cohesion, and governance capacity — "
            "rather than short-term events or tactical developments. Structures change "
            "slowly and constrain what is possible."
        ),
        "cot_steps": (
            "1. INSTITUTIONAL RESILIENCE: How robust are the governing institutions? "
            "Can they function under extreme pressure? Is there a professional military "
            "or civil service that persists regardless of leadership?\n"
            "2. GEOGRAPHIC FACTORS: Does geography favor defense or offense? Can the state "
            "sustain territorial integrity based on terrain, borders, and logistics?\n"
            "3. RESOURCE FUNDAMENTALS: Assess economic capacity for sustained conflict — "
            "GDP, energy access, trade routes, sanctions impact. Can the state sustain itself "
            "economically?\n"
            "4. EXTERNAL STRUCTURAL SUPPORT: Is international support structural (treaty "
            "alliances, institutional commitments) or contingent (political will, public "
            "opinion)? How durable is it?\n"
            "5. FINAL PROBABILITY: Base your estimate on structural factors. Short-term "
            "events should only matter if they threaten structural fundamentals."
        ),
    },
]

# ---------------------------------------------------------------------------
# Axis 2: Lens (interpretive bias)
# ---------------------------------------------------------------------------

LENSES = [
    {
        "id": "threat_focused",
        "label": "Threat-Focused",
        "description": (
            "You interpret ambiguous evidence through a THREAT-FOCUSED lens. When "
            "information is uncertain, assume the more dangerous interpretation. "
            "Potential threats are weighted more heavily than potential stabilizers. "
            "Your role is to ensure threats are not underestimated."
        ),
        "calibration_note": (
            "Your estimates should skew HIGHER than a neutral analyst's — you are "
            "systematically more concerned about collapse risks."
        ),
        "cot_modifier": (
            "INTERPRETIVE CALIBRATION: Before stating your final probability, review "
            "your reasoning. For every ambiguous piece of evidence, confirm you chose the "
            "more threatening interpretation. If your estimate feels moderate, push it HIGHER. "
            "Threats you might be underweighting: military escalation, economic fragility, "
            "alliance fatigue, internal fractures."
        ),
    },
    {
        "id": "resilience_focused",
        "label": "Resilience-Focused",
        "description": (
            "You interpret ambiguous evidence through a RESILIENCE-FOCUSED lens. When "
            "information is uncertain, assume the more stabilizing interpretation. "
            "Institutional strengths and adaptive capacity are weighted more heavily "
            "than vulnerabilities. Your role is to ensure resilience is not underestimated."
        ),
        "calibration_note": (
            "Your estimates should skew LOWER than a neutral analyst's — you are "
            "systematically more confident in government survival."
        ),
        "cot_modifier": (
            "INTERPRETIVE CALIBRATION: Before stating your final probability, review "
            "your reasoning. For every ambiguous piece of evidence, confirm you chose the "
            "more stabilizing interpretation. If your estimate feels moderate, push it LOWER. "
            "Resilience factors you might be underweighting: institutional depth, popular "
            "legitimacy, international commitment, economic adaptation."
        ),
    },
    {
        "id": "contrarian",
        "label": "Contrarian",
        "description": (
            "You interpret evidence through a CONTRARIAN lens. You systematically argue "
            "AGAINST the obvious reading of the situation. If the evidence suggests stability, "
            "you look for hidden fragility. If the evidence suggests collapse, you look for "
            "hidden resilience. Challenge every assumption and conventional narrative."
        ),
        "calibration_note": (
            "Your estimate should DIFFER meaningfully from what a conventional analyst would say."
        ),
        "cot_modifier": (
            "INTERPRETIVE CALIBRATION: Before stating your final probability, identify what a "
            "conventional analyst would likely conclude, then argue against it. What assumptions "
            "are they making that might be wrong? What evidence are they overweighting or "
            "underweighting? Your final estimate should be on the OPPOSITE SIDE of the "
            "conventional view."
        ),
    },
    {
        "id": "loss_averse",
        "label": "Loss-Averse",
        "description": (
            "You interpret evidence through a LOSS-AVERSE lens. Losses (territorial, "
            "economic, military) weigh approximately twice as heavily as equivalent gains "
            "in your assessment. A 10% territory loss is more significant than a 10% "
            "economic gain. Irreversible losses are especially alarming."
        ),
        "calibration_note": (
            "Your estimates should skew HIGHER than a neutral analyst's — because losses "
            "dominate your assessment and losses compound."
        ),
        "cot_modifier": (
            "INTERPRETIVE CALIBRATION: Before stating your final probability, review all "
            "losses vs. gains. Weight each loss 2x relative to each gain. Irreversible "
            "losses (territory, destroyed infrastructure, killed personnel) should weigh "
            "even more heavily. If your estimate feels moderate, consider whether accumulated "
            "losses are approaching a tipping point."
        ),
    },
    {
        "id": "detached",
        "label": "Detached/Calibrated",
        "description": (
            "You interpret evidence through a DETACHED, CALIBRATED lens. You have no "
            "systematic interpretive bias. You weigh positive and negative signals equally "
            "and let the evidence speak for itself. This is the control condition."
        ),
        "calibration_note": (
            "Aim for maximum calibration — your estimates should be neither systematically "
            "high nor systematically low."
        ),
        "cot_modifier": (
            "INTERPRETIVE CALIBRATION: Before stating your final probability, check for "
            "cognitive biases in your reasoning. Are you anchoring on a vivid detail? "
            "Are you being swayed by a narrative? Aim for a balanced, evidence-driven estimate."
        ),
    },
]

# ---------------------------------------------------------------------------
# Axis 3: Focus (evidence attention)
# ---------------------------------------------------------------------------

FOCUSES = [
    {
        "id": "military",
        "label": "Military-Dominant",
        "description": (
            "Your analytical focus is MILITARY-DOMINANT. Military factors — territorial "
            "control, force balance, military events, and combat outcomes — are the "
            "primary drivers of your assessment. Other factors matter only insofar as "
            "they affect military capacity."
        ),
        "instruction": (
            "Military factors are your PRIMARY evidence. Weight them 3x more heavily "
            "than other factors in your assessment."
        ),
        "evidence_list": (
            "territory controlled, military balance, military events, force deployments, "
            "combat outcomes, and defense capacity"
        ),
    },
    {
        "id": "economic",
        "label": "Economic-Dominant",
        "description": (
            "Your analytical focus is ECONOMIC-DOMINANT. Economic factors — GDP, sanctions "
            "impact, trade disruption, fiscal sustainability, and economic resilience — "
            "are the primary drivers of your assessment. A government that cannot fund "
            "itself cannot survive."
        ),
        "instruction": (
            "Economic factors are your PRIMARY evidence. Weight them 3x more heavily "
            "than other factors in your assessment."
        ),
        "evidence_list": (
            "GDP levels, sanctions severity, trade disruption, economic sustainability, "
            "fiscal capacity, and resource access"
        ),
    },
    {
        "id": "political",
        "label": "Political-Dominant",
        "description": (
            "Your analytical focus is POLITICAL-DOMINANT. Political factors — international "
            "support, alliance strength, diplomatic developments, and internal political "
            "cohesion — are the primary drivers of your assessment. Governments survive "
            "or fall based on political support."
        ),
        "instruction": (
            "Political factors are your PRIMARY evidence. Weight them 3x more heavily "
            "than other factors in your assessment."
        ),
        "evidence_list": (
            "international support levels, alliance commitments, diplomatic actions, "
            "internal political stability, and coalition dynamics"
        ),
    },
    {
        "id": "events",
        "label": "Event-Driven",
        "description": (
            "Your analytical focus is EVENT-DRIVEN. Recent events and actions — what "
            "actually happened in the most recent period — dominate your assessment. "
            "Structural factors and slow-moving variables are secondary to concrete "
            "developments on the ground."
        ),
        "instruction": (
            "Recent events are your PRIMARY evidence. Weight them 3x more heavily "
            "than structural or baseline factors in your assessment."
        ),
        "evidence_list": (
            "external events this period, actor actions this period, recent escalations "
            "or de-escalations, and concrete developments on the ground"
        ),
    },
    {
        "id": "holistic",
        "label": "Holistic",
        "description": (
            "Your analytical focus is HOLISTIC. All factors — military, economic, "
            "political, and event-driven — are weighted equally. No single domain "
            "dominates. This is the control condition."
        ),
        "instruction": (
            "All evidence categories are equally important. Weight military, economic, "
            "political, and event-driven factors equally."
        ),
        "evidence_list": (
            "all available factors equally: territory, GDP, military balance, "
            "international support, sanctions, crisis level, and recent events"
        ),
    },
]

# ---------------------------------------------------------------------------
# Axis 4: Bias (cognitive distortion)
# ---------------------------------------------------------------------------

BIASES = [
    {
        "id": "recency",
        "label": "Recency Bias",
        "description": (
            "COGNITIVE TENDENCY — RECENCY BIAS: You disproportionately weight the "
            "most recent period's events over longer-term trends and structural factors. "
            "What just happened feels more predictive than what has been true for months. "
            "Recent dramatic events dominate your reasoning."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Focus heavily on what happened MOST RECENTLY. "
            "The latest events are the best predictor of what comes next. Historical "
            "patterns and slow-moving structural factors are less reliable than the "
            "freshest signals. If recent events point toward collapse, weight that heavily. "
            "If recent events point toward stability, weight that heavily."
        ),
    },
    {
        "id": "anchoring",
        "label": "Anchoring Bias",
        "description": (
            "COGNITIVE TENDENCY — ANCHORING BIAS: You anchor heavily on the first "
            "concrete number you encounter in the data and adjust insufficiently from "
            "it. The crisis level, territory percentage, or GDP figure you notice first "
            "becomes your mental starting point, and subsequent reasoning barely moves "
            "you from that anchor."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Identify the single most salient number in the data "
            "(crisis level, territory %, GDP, military balance). Use that number directly "
            "as your starting anchor for collapse probability. Make only SMALL adjustments "
            "from this anchor — large deviations from your initial number require "
            "extraordinary justification."
        ),
    },
    {
        "id": "normalcy",
        "label": "Normalcy Bias",
        "description": (
            "COGNITIVE TENDENCY — NORMALCY BIAS: You believe that because something "
            "has not happened before, it is unlikely to happen now. Government collapse "
            "is rare and extreme — the system has survived crises before and will likely "
            "survive this one. You underestimate the probability of unprecedented outcomes."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Governments almost never collapse. The historical norm "
            "is survival — states are resilient, institutions adapt, crises get managed. "
            "Extraordinary claims (like imminent government collapse) require extraordinary "
            "evidence. Default to LOW probability unless the evidence is overwhelming "
            "and unambiguous."
        ),
    },
    {
        "id": "availability",
        "label": "Availability Bias",
        "description": (
            "COGNITIVE TENDENCY — AVAILABILITY BIAS: You overweight vivid, dramatic, "
            "and easily-imagined scenarios. Military invasions, coups, and dramatic "
            "collapses are more mentally available than quiet institutional erosion or "
            "muddling through. The more vivid the collapse scenario, the more probable "
            "it feels."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Think about the most vivid and dramatic ways this "
            "situation could unfold. Can you easily imagine a military breakthrough, "
            "a dramatic coup, an economic implosion? The easier it is to picture a "
            "collapse scenario in detail, the more likely it is. Vivid, concrete "
            "scenarios are more probable than abstract ones."
        ),
    },
    {
        "id": "overconfidence",
        "label": "Overconfidence",
        "description": (
            "COGNITIVE TENDENCY — OVERCONFIDENCE: You are highly confident in your "
            "ability to read the situation correctly. You do not hedge — your estimates "
            "are decisive and extreme. If collapse looks likely, it is VERY likely. "
            "If survival looks likely, it is VERY likely. You rarely assign moderate "
            "probabilities."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: You are an expert and your reading of the evidence is "
            "correct. Do NOT hedge with moderate probabilities near 0.3-0.7. If the "
            "evidence leans toward collapse, commit to a HIGH estimate (0.7+). If it "
            "leans toward survival, commit to a LOW estimate (below 0.3). Your "
            "confidence in your analysis is justified — be decisive."
        ),
    },
    {
        "id": "sunk_cost",
        "label": "Sunk Cost Fallacy",
        "description": (
            "COGNITIVE TENDENCY — SUNK COST FALLACY: You believe that the more a "
            "government and its allies have invested in survival (military aid, "
            "economic support, political capital, lives lost), the less likely they "
            "are to let it fail. Past investment makes future collapse feel wasteful "
            "and therefore unlikely."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Consider how much has already been invested in this "
            "government's survival — military aid, diplomatic effort, economic support, "
            "lives sacrificed. All of that investment would be WASTED if the government "
            "collapsed. The more that has been invested, the more all parties are "
            "committed to preventing collapse. Heavy prior investment makes collapse "
            "LESS likely."
        ),
    },
    {
        "id": "confirmation",
        "label": "Confirmation Bias",
        "description": (
            "COGNITIVE TENDENCY — CONFIRMATION BIAS: You form a quick initial "
            "impression from the first piece of evidence you process, then "
            "selectively seek and emphasize evidence that confirms that impression "
            "while downplaying contradictory signals."
        ),
        "cot_injection": (
            "COGNITIVE TENDENCY: Look at the FIRST data point presented (territory "
            "or crisis level). Form your initial impression of whether collapse is "
            "likely or unlikely. Then as you review remaining evidence, focus on "
            "signals that CONFIRM your initial impression. Evidence that contradicts "
            "your first read is probably misleading or less reliable. Trust your "
            "initial gut reaction."
        ),
    },
    {
        "id": "none",
        "label": "No Cognitive Bias",
        "description": (
            "NO COGNITIVE DISTORTION: You reason clearly without systematic cognitive "
            "biases. You weigh evidence proportionally, avoid anchoring on salient "
            "numbers, consider base rates appropriately, and are neither overconfident "
            "nor underconfident. This is the rational control condition."
        ),
        "cot_injection": (
            "COGNITIVE CHECK: Reason carefully and avoid common cognitive pitfalls. "
            "Do not anchor on salient numbers, do not overweight recent events, do not "
            "let vivid scenarios dominate, and do not be swayed by sunk costs. Aim for "
            "calibrated, evidence-proportional reasoning."
        ),
    },
]


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def compose_framework(method: Dict, lens: Dict, focus: Dict, bias: Dict = None) -> Dict:
    """
    Assemble a complete framework from one method, one lens, one focus,
    and optionally one cognitive bias.

    Returns a dict compatible with the existing experiment runner:
        - name: composite id string
        - system_prompt: assembled from all axes
        - cot_instructions: assembled from all axes
        - method / lens / focus / bias: individual axis ids
    """
    if bias is None:
        bias = BIASES[-1]  # "none" — rational control

    name = f"{method['id']}_{lens['id']}_{focus['id']}_{bias['id']}"

    # System prompt: method + lens + focus + bias (if not "none")
    bias_section = ""
    if bias["id"] != "none":
        bias_section = f"\n\n{bias['description']}"

    system_prompt = (
        f"You are a {method['label']} analyst specializing in government stability forecasting.\n\n"
        f"METHODOLOGY: {method['system_description']}\n\n"
        f"INTERPRETIVE LENS: {lens['description']}\n\n"
        f"ANALYTICAL FOCUS: {focus['description']}"
        f"{bias_section}\n\n"
        f"Apply your methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
        f"{lens['calibration_note']}\n\n"
        f"Output ONLY valid JSON in the exact format specified."
    )

    cot_instructions = (
        f"EVIDENCE PRIORITY: {focus['instruction']}\n"
        f"Pay primary attention to {focus['evidence_list']} when evaluating evidence below.\n\n"
        f"Think step-by-step using {method['label']}:\n"
        f"{method['cot_steps']}\n\n"
        f"{lens['cot_modifier']}\n\n"
        f"{bias['cot_injection']}"
    )

    return {
        "name": name,
        "system_prompt": system_prompt,
        "cot_instructions": cot_instructions,
        "method": method["id"],
        "lens": lens["id"],
        "focus": focus["id"],
        "bias": bias["id"],
    }


def generate_pool() -> List[Dict]:
    """Generate all 1000 (5×5×5×8) framework combinations."""
    pool = []
    for method in METHODS:
        for lens in LENSES:
            for focus in FOCUSES:
                for bias in BIASES:
                    pool.append(compose_framework(method, lens, focus, bias))
    return pool


def sample_frameworks(n: int, seed: Optional[str] = None) -> List[Dict]:
    """
    Draw n frameworks from the full combination pool.

    Uses a deterministic hash-based selection so the same seed always
    produces the same sample. This avoids importing random and keeps
    reproducibility transparent.

    Args:
        n: Number of frameworks to sample.
        seed: String seed for reproducibility (e.g., scenario_id + condition).
              If None, returns the first n from the pool.
    """
    pool = generate_pool()

    if seed is None:
        return pool[:n]

    # Deterministic shuffle via hash-based sort key
    def _sort_key(framework: Dict) -> str:
        raw = f"{seed}_{framework['name']}"
        return hashlib.sha256(raw.encode()).hexdigest()

    sorted_pool = sorted(pool, key=_sort_key)
    return sorted_pool[:n]


# ---------------------------------------------------------------------------
# Action Prediction variant
# ---------------------------------------------------------------------------

# Method-specific CoT steps adapted for action prediction
_ACTION_COT_STEPS = {
    "base_rate": (
        "1. BASE RATE: What fraction of crisis periods feature this type of action? "
        "Estimate a specific base rate (most individual actions are rare: ~10-15%).\n"
        "2. STRATEGIC FIT: Does this action align with the faction's strategic objectives "
        "given the current situation? Adjust up or down from the base rate.\n"
        "3. CAPABILITY CHECK: Does the faction have the resources, positioning, and "
        "capability to execute this action right now?\n"
        "4. EVIDENCE SIGNALS: Are there observable indicators (events, state variables) "
        "consistent with this action having been taken?\n"
        "5. FINAL PROBABILITY: Starting from the base rate, apply adjustments. "
        "Show your arithmetic."
    ),
    "scenario_tree": (
        "1. ENUMERATE STRATEGIES: Define 3-4 plausible strategy packages the faction "
        "could be pursuing (e.g., escalation, deterrence, negotiation, status quo).\n"
        "2. STRATEGY PROBABILITIES: Assign a probability to each strategy. They MUST "
        "sum to 1.0.\n"
        "3. ACTION LIKELIHOOD PER STRATEGY: For each strategy, estimate "
        "P(this action | strategy). Some strategies make this action likely; others don't.\n"
        "4. WEIGHTED CALCULATION: Calculate total P(action taken) = sum of "
        "P(strategy_i) * P(action | strategy_i). Show the arithmetic.\n"
        "5. FINAL PROBABILITY: State the calculated result."
    ),
    "historical_analogy": (
        "1. CANDIDATE ANALOGIES: Identify 2-3 historical crises that resemble this "
        "situation. Consider similar power dynamics, crisis levels, and faction postures.\n"
        "2. BEST ANALOGY: Select the closest historical parallel.\n"
        "3. HISTORICAL ACTIONS: In the analogous case, did factions in a similar "
        "position take this type of action? How frequently?\n"
        "4. KEY DIFFERENCES: What differs between the historical case and now? "
        "Does this make the action MORE or LESS likely?\n"
        "5. FINAL PROBABILITY: Anchor on the historical precedent and adjust."
    ),
    "key_indicator": (
        "1. INDICATOR SCAN: Review all available state variables and events.\n"
        "2. KEY INDICATOR: Choose the SINGLE most diagnostic indicator for whether "
        "this specific action was taken. Justify your choice.\n"
        "3. INDICATOR READING: What does this indicator currently show? Is it "
        "consistent with this action having been taken?\n"
        "4. SECONDARY CHECK: Do other indicators contradict or reinforce the signal?\n"
        "5. FINAL PROBABILITY: Derive your estimate primarily from the key indicator."
    ),
    "structural": (
        "1. FACTION POSTURE: What is this faction's structural position — resources, "
        "military capacity, alliances, institutional constraints?\n"
        "2. ACTION FEASIBILITY: Given structural constraints, is this action within "
        "the faction's operational capability?\n"
        "3. STRUCTURAL INCENTIVES: Do the faction's structural interests (territorial, "
        "economic, political) create a strong rationale for this action?\n"
        "4. INSTITUTIONAL CONSTRAINTS: Would institutional norms, alliance obligations, "
        "or resource limits prevent this action?\n"
        "5. FINAL PROBABILITY: Base your estimate on structural feasibility and incentives."
    ),
}


def compose_action_framework(method: Dict, lens: Dict, focus: Dict, bias: Dict = None) -> Dict:
    """
    Assemble a framework for action prediction (not collapse forecasting).

    Same 4-axis structure, but system prompt and CoT steps are adapted
    for predicting whether a faction took a specific action.
    """
    if bias is None:
        bias = BIASES[-1]

    name = f"{method['id']}_{lens['id']}_{focus['id']}_{bias['id']}"

    bias_section = ""
    if bias["id"] != "none":
        bias_section = f"\n\n{bias['description']}"

    system_prompt = (
        f"You are a {method['label']} analyst specializing in predicting state actor "
        f"behavior during geopolitical crises.\n\n"
        f"METHODOLOGY: {method['system_description']}\n\n"
        f"INTERPRETIVE LENS: {lens['description']}\n\n"
        f"ANALYTICAL FOCUS: {focus['description']}"
        f"{bias_section}\n\n"
        f"Apply your methodology rigorously. USE THE FULL PROBABILITY RANGE 0.0 to 1.0.\n"
        f"{lens['calibration_note']}\n\n"
        f"Output ONLY valid JSON in the exact format specified."
    )

    action_cot = _ACTION_COT_STEPS.get(method["id"], method["cot_steps"])

    cot_instructions = (
        f"EVIDENCE PRIORITY: {focus['instruction']}\n"
        f"Pay primary attention to {focus['evidence_list']} when evaluating evidence below.\n\n"
        f"Think step-by-step using {method['label']}:\n"
        f"{action_cot}\n\n"
        f"{lens['cot_modifier']}\n\n"
        f"{bias['cot_injection']}"
    )

    return {
        "name": name,
        "system_prompt": system_prompt,
        "cot_instructions": cot_instructions,
        "method": method["id"],
        "lens": lens["id"],
        "focus": focus["id"],
        "bias": bias["id"],
    }


def generate_action_pool() -> List[Dict]:
    """Generate all 1000 action-prediction framework combinations."""
    pool = []
    for method in METHODS:
        for lens in LENSES:
            for focus in FOCUSES:
                for bias in BIASES:
                    pool.append(compose_action_framework(method, lens, focus, bias))
    return pool


def sample_action_frameworks(n: int, seed: Optional[str] = None) -> List[Dict]:
    """Draw n action-prediction frameworks from the pool (deterministic)."""
    pool = generate_action_pool()

    if seed is None:
        return pool[:n]

    def _sort_key(framework: Dict) -> str:
        raw = f"{seed}_{framework['name']}"
        return hashlib.sha256(raw.encode()).hexdigest()

    sorted_pool = sorted(pool, key=_sort_key)
    return sorted_pool[:n]
