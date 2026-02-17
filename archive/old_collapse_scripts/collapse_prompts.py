"""
Prompt templates for government collapse probability forecasting.

Forecasters predict the probability (0.0 to 1.0) that Tethys's government
will collapse or be removed from power by the end of the period.
"""

from typing import Dict, List


def create_collapse_forecast_prompt(
    period: int,
    state_before: Dict,
    external_events: List[str],
    novaris_actions: List[str],
    tethys_actions: List[str]
) -> str:
    """
    Create prompt for forecasting Tethys government collapse probability.

    Args:
        period: Period number (1-10)
        state_before: State dict from period-1
        external_events: List of external event descriptions
        novaris_actions: Novaris's approved actions this period
        tethys_actions: Tethys's approved actions this period

    Returns:
        Complete prompt string
    """

    prompt = f"""You are a geopolitical analyst forecasting the probability of government collapse.

{'='*80}
STRATEGIC SITUATION (Period {period-1} Final State)
{'='*80}

TETHYS POSITION:
- Territory Remaining: {(1-state_before.get('territory_controlled', 0))*100:.1f}%
- Military Balance: {state_before.get('military_balance', 0):.2f} (-1=Novaris advantage, +1=Tethys advantage)
- GDP: ${state_before.get('tethys_gdp', 30):.1f}B (started at $30B)
- International Support: {state_before.get('international_support', 0.5)*100:.0f}%
- Crisis Level: {state_before.get('crisis_level', 5):.1f}/10

NOVARIS POSITION:
- Territory Controlled: {state_before.get('territory_controlled', 0)*100:.1f}%
- GDP: ${state_before.get('novaris_gdp', 100):.1f}B (started at $100B)
- Sanctions Level: {state_before.get('sanctions_level', 0)*100:.0f}%

{'='*80}
EXTERNAL EVENTS THIS PERIOD
{'='*80}

{format_events(external_events)}

{'='*80}
ACTIONS TAKEN THIS PERIOD
{'='*80}

NOVARIS ACTIONS:
{format_actions(novaris_actions)}

TETHYS ACTIONS:
{format_actions(tethys_actions)}

{'='*80}
YOUR FORECASTING TASK
{'='*80}

Forecast the probability that Tethys's government will collapse or be removed
from power by the end of Period {period}.

Government collapse includes:
- Military defeat leading to regime change
- Internal coup or revolution
- Economic collapse forcing government resignation
- Loss of governing capacity due to territorial loss
- Capitulation or forced settlement removing current leadership

CRITICAL INSTRUCTIONS:
- Output a probability between 0.0 and 1.0 (not a percentage)
- USE THE FULL PROBABILITY RANGE - don't cluster around 0.5
- Be calibrated: 0.2 means 20% chance, 0.8 means 80% chance
- Consider ALL factors: military, economic, political, international
- Low probability (0.0-0.3): Government stable despite crisis
- Medium probability (0.3-0.7): Uncertain, could go either way
- High probability (0.7-1.0): Government likely to collapse

Think step-by-step:
1. Assess Tethys's current military/territorial position
2. Evaluate economic sustainability and internal stability
3. Consider external support and diplomatic situation
4. Analyze this period's events and actions
5. Estimate overall collapse probability

OUTPUT FORMAT (JSON):
{{
  "probability": 0.XX,
  "confidence": "low|medium|high",
  "rationale": "2-3 sentence explanation of key factors driving your probability estimate"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
Use the FULL range 0.0 to 1.0 based on the actual situation - don't default to middle values.
"""

    return prompt


def format_events(events: List[str]) -> str:
    """Format external events list."""
    if not events:
        return "  (No major external events this period)"

    formatted = []
    for i, event in enumerate(events, 1):
        formatted.append(f"  {i}. {event}")

    return '\n'.join(formatted)


def format_actions(actions: List[str]) -> str:
    """Format action list."""
    if not actions:
        return "  (No actions taken)"

    formatted = []
    for action in actions:
        formatted.append(f"  - {action}")

    return '\n'.join(formatted)


if __name__ == "__main__":
    # Test prompt generation
    print("Testing collapse forecast prompt...\n")

    test_state = {
        'territory_controlled': 0.05,
        'military_balance': -0.05,
        'crisis_level': 6.0,
        'novaris_gdp': 98.0,
        'tethys_gdp': 29.5,
        'international_support': 0.55,
        'sanctions_level': 0.15
    }

    test_events = [
        "Battlefield: Initial skirmishes along border",
        "Economic: International sanctions imposed on Novaris",
        "Diplomatic: Meridian reaffirms security commitment"
    ]

    test_novaris_actions = ['military_buildup', 'naval_deployment', 'strategic_stockpiling']
    test_tethys_actions = ['show_of_force', 'coalition_building', 'humanitarian_aid']

    prompt = create_collapse_forecast_prompt(
        period=1,
        state_before=test_state,
        external_events=test_events,
        novaris_actions=test_novaris_actions,
        tethys_actions=test_tethys_actions
    )

    print(prompt[:1000] + "\n...(truncated)")
    print("\n[OK] Collapse forecast prompt created successfully!")
