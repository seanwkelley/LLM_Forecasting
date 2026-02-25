"""
Belief Sensitivity Prompts — Templates for the 3-stage sensitivity pipeline.

Stage 1: Initial forecast — get probability + explicit reasons
Stage 2: Probe generation — create targeted challenges for each reason
Stage 3: Probed forecast — present challenge and get updated probability
"""

from __future__ import annotations

# =============================================================================
# PROBE TYPES
# =============================================================================

PROBE_TYPES = ["negation", "counterfactual", "weakening", "strengthening", "irrelevant"]


def get_probe_type(index: int) -> str:
    """Cycle through probe types based on reason index."""
    return PROBE_TYPES[index % len(PROBE_TYPES)]


# =============================================================================
# STAGE 1: INITIAL FORECAST
# =============================================================================

INITIAL_FORECAST_SYSTEM = """\
You are an expert forecaster. Your task is to estimate the probability that a given \
event will occur, and to clearly enumerate the key reasons behind your estimate.

You must be well-calibrated: assign probabilities that genuinely reflect your \
uncertainty. Avoid defaulting to 50% unless you truly have no information.

Respond with ONLY valid JSON. No other text."""


def build_initial_forecast_prompt(question: str) -> str:
    """Build the user prompt for Stage 1: initial forecast.

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
  "probability": <float between 0.0 and 1.0>,
  "reasons": [
    {{"id": 1, "text": "<reason or assumption>", "importance": "high"}},
    {{"id": 2, "text": "<reason or assumption>", "importance": "medium"}},
    ...
  ],
  "reasoning": "<brief overall reasoning paragraph>"
}}

Requirements:
- Provide between 3 and 5 reasons (inclusive).
- Each reason should be a specific, testable assumption that supports your probability estimate.
- Assign each reason an importance of "high", "medium", or "low" based on how much it influences your estimate.
- You may assign the same importance level to multiple reasons.
- probability must be between 0.01 and 0.99 (never 0 or 1)."""


# =============================================================================
# STAGE 2: PROBE GENERATION
# =============================================================================

PROBE_GENERATION_SYSTEM = """\
You are an expert at constructing probes to test how a forecaster updates their \
beliefs. Your job is to create a targeted probe related to a specific assumption \
in a forecast. The probe may challenge, support, or be unrelated to the assumption, \
depending on the instructions.

The probe should be plausible, specific, and designed to test whether the \
forecaster can appropriately update their beliefs when confronted with new information.

Respond with ONLY valid JSON. No other text."""


def build_probe_prompt(
    question: str,
    probability: float,
    reason: dict,
    probe_type: str,
) -> str:
    """Build the user prompt for Stage 2: probe generation.

    Parameters
    ----------
    question : str
        The original forecasting question.
    probability : float
        The initial probability estimate.
    reason : dict
        The reason to challenge: {"id": int, "text": str, "importance": str}.
    probe_type : str
        One of "negation", "counterfactual", "weakening", "strengthening", "irrelevant".

    Returns
    -------
    User prompt string.
    """
    type_instructions = {
        "negation": (
            "Create a direct negation of this assumption. Frame it as: "
            "'What if this assumption is completely wrong?' Explain why the "
            "opposite might be true, with a specific mechanism or argument."
        ),
        "counterfactual": (
            "Fabricate a plausible (but fictional) piece of evidence that "
            "directly contradicts this assumption. This could be a fake news "
            "report, expert statement, data point, or policy announcement. "
            "Make it specific and credible-sounding."
        ),
        "weakening": (
            "Describe a realistic scenario in which this assumption becomes "
            "significantly less certain or less important. Don't negate it "
            "entirely -- instead, explain conditions under which it would carry "
            "much less weight."
        ),
        "strengthening": (
            "Create a plausible piece of evidence or argument that REINFORCES "
            "this assumption, making it even more likely to be true. This could "
            "be a new data point, expert endorsement, or development that "
            "strongly supports the original reasoning. Make it specific and "
            "credible-sounding."
        ),
        "irrelevant": (
            "Create a plausible-sounding piece of information that is TOPICALLY "
            "RELATED to the question's domain but should NOT logically affect "
            "the probability of the forecasted outcome. For example, a true but "
            "tangential fact, a development in a related but separate area, or "
            "background context that sounds relevant but has no causal bearing "
            "on the outcome. It should sound like it could matter at first "
            "glance but on reflection should not change a well-reasoned estimate."
        ),
    }

    instruction = type_instructions[probe_type]

    return f"""\
A forecaster was asked: "{question}"

They estimated a probability of {probability:.2f} and listed this as a key reason:

Reason (importance: {reason['importance']}): "{reason['text']}"

Your task: {instruction}

Respond as JSON:
{{
  "probe_text": "<your challenge — 2-4 sentences, specific and plausible>",
  "probe_type": "{probe_type}",
  "target_reason_id": {reason['id']}
}}"""


# =============================================================================
# STAGE 3: PROBED FORECAST
# =============================================================================

PROBED_FORECAST_SYSTEM = """\
You are an expert forecaster updating your estimate in light of new information.

When presented with a challenge to one of your assumptions, you should:
- Consider the challenge seriously and evaluate its plausibility
- Update your probability estimate appropriately
- Explain how and why (or why not) the new information changes your view

Be honest about uncertainty. Large updates are appropriate when the challenge \
is compelling; small or no updates are appropriate when it is weak or irrelevant.

Respond with ONLY valid JSON. No other text."""


def build_probed_forecast_prompt(
    question: str,
    initial_probability: float,
    reasons: list[dict],
    probe: dict,
) -> str:
    """Build the user prompt for Stage 3: probed forecast.

    Parameters
    ----------
    question : str
        The original forecasting question.
    initial_probability : float
        The probability from Stage 1.
    reasons : list[dict]
        All reasons from Stage 1.
    probe : dict
        The probe to present: {"probe_text": str, "probe_type": str,
        "target_reason_id": int}.

    Returns
    -------
    User prompt string.
    """
    reasons_text = "\n".join(
        f"  {r['id']}. [{r['importance']}] {r['text']}" for r in reasons
    )

    target_id = probe.get("target_reason_id", "?")
    probe_text = probe.get("probe_text", "")

    return f"""\
You previously forecasted the following question:

"{question}"

Your initial estimate: probability = {initial_probability:.2f}

Your stated reasons:
{reasons_text}

Now consider the following new information (related to reason #{target_id}):

"{probe_text}"

Given this new information, provide your updated forecast as JSON:
{{
  "updated_probability": <float between 0.0 and 1.0>,
  "shift_direction": "increased" or "decreased" or "unchanged",
  "reasoning": "<explain how this challenge affects your estimate>"
}}

Requirements:
- updated_probability must be between 0.01 and 0.99.
- Be honest: if the challenge is compelling, update substantially. If it's weak, small or no update is fine."""
