"""
Prompt templates for action set prediction.

Creates prompts for Novaris and Tethys action predictions
with full strategic context.
"""

from typing import Dict, List, Optional


def interpret_military_balance(balance: float) -> str:
    """Interpret military balance score (-1 to +1)."""
    if balance < -0.2:
        return "Strong Novaris advantage"
    elif balance < -0.05:
        return "Moderate Novaris advantage"
    elif balance < 0.05:
        return "Balanced"
    elif balance < 0.2:
        return "Moderate Tethys advantage"
    else:
        return "Strong Tethys advantage"


def assess_strategic_posture(faction: str, state: Dict) -> str:
    """
    Assess faction's strategic posture based on state.

    Returns 2-3 sentence assessment.
    """
    if faction == 'novaris':
        territory = state.get('territory_controlled', 0) * 100
        gdp = state.get('novaris_gdp', 100)
        sanctions = state.get('sanctions_level', 0) * 100
        balance = state.get('military_balance', 0)

        if territory > 30:
            posture = f"Novaris has made significant territorial gains ({territory:.0f}%) and appears to be winning. "
        elif territory > 15:
            posture = f"Novaris holds {territory:.0f}% of Tethys territory, maintaining offensive pressure. "
        elif territory > 5:
            posture = f"Novaris has limited territorial gains ({territory:.0f}%), facing resistance. "
        else:
            posture = f"Novaris has failed to achieve substantial territorial control ({territory:.0f}%). "

        if gdp < 80:
            posture += f"Economic strain is severe (GDP: ${gdp:.0f}B, down {100-gdp:.0f}B). "
        elif gdp < 90:
            posture += f"Economic costs are mounting (GDP: ${gdp:.0f}B). "

        if sanctions > 60:
            posture += f"Heavy international sanctions ({sanctions:.0f}%) are impacting capabilities."
        elif sanctions > 30:
            posture += f"Moderate sanctions ({sanctions:.0f}%) are applied but manageable."

        return posture

    else:  # tethys
        territory = state.get('territory_controlled', 0) * 100
        gdp = state.get('tethys_gdp', 30)
        support = state.get('international_support', 0) * 100
        balance = state.get('military_balance', 0)

        remaining = 100 - territory

        if remaining < 70:
            posture = f"Tethys has lost {territory:.0f}% of territory and is under severe pressure. "
        elif remaining < 85:
            posture = f"Tethys retains {remaining:.0f}% of territory but faces ongoing offensive. "
        else:
            posture = f"Tethys has successfully defended most territory ({remaining:.0f}% retained). "

        if gdp < 20:
            posture += f"Economic situation is critical (GDP: ${gdp:.0f}B). "
        elif gdp < 25:
            posture += f"Economic strain from conflict (GDP: ${gdp:.0f}B). "

        if support > 70:
            posture += f"Strong international support ({support:.0f}%) provides resilience."
        elif support > 50:
            posture += f"Moderate international support ({support:.0f}%) continues."
        else:
            posture += f"Limited international support ({support:.0f}%) is a concern."

        return posture


def format_events(events: List[str]) -> str:
    """Format external events list."""
    if not events:
        return "  (No major external events this period)"

    formatted = []
    for i, event in enumerate(events, 1):
        formatted.append(f"  {i}. {event}")

    return '\n'.join(formatted)


def format_actions_with_implications(actions: List[str]) -> str:
    """
    Format action list with brief strategic implications.
    """
    action_implications = {
        'offensive_operation': 'Escalatory - aims to capture territory',
        'precision_strike': 'Targeted military action',
        'military_buildup': 'Force concentration - signals intent or deterrence',
        'defensive_posture': 'Defensive preparation',
        'intelligence_gathering': 'Information collection for strategic advantage',
        'sabotage': 'Covert destabilization attempt',
        'cyber_attack': 'Digital warfare targeting infrastructure',
        'strategic_stockpiling': 'Economic resilience preparation',
        'peace_talks': 'Diplomatic de-escalation attempt',
        'backchannel_negotiations': 'Secret diplomatic engagement',
        'sanctions': 'Economic pressure campaign',
        'embargo': 'Trade restrictions',
        'show_of_force': 'Military demonstration without engagement',
    }

    formatted = []
    for action in actions:
        implication = action_implications.get(action, 'Strategic action')
        formatted.append(f"  • {action}: {implication}")

    return '\n'.join(formatted)


def create_novaris_action_prediction_prompt(
    period: int,
    state_before: Dict,
    external_events: List[str],
    plausible_actions_text: str
) -> str:
    """
    Create prompt for predicting Novaris's action set.

    Args:
        period: Period number (1-10)
        state_before: State dict from period-1
        external_events: List of external event descriptions
        plausible_actions_text: Formatted plausible actions by domain

    Returns:
        Complete prompt string
    """

    prompt = f"""You are a strategic analyst tasked with predicting Novaris's complete action set for Period {period}.

{'='*80}
STRATEGIC SITUATION (Period {period-1} Final State)
{'='*80}

NOVARIS POSITION:
- Territory Controlled: {state_before.get('territory_controlled', 0)*100:.1f}%
- Military Balance: {state_before.get('military_balance', 0):.2f} ({interpret_military_balance(state_before.get('military_balance', 0))})
- GDP: ${state_before.get('novaris_gdp', 100):.1f}B (started at $100B, change: {state_before.get('novaris_gdp', 100)-100:+.1f}B)
- Crisis Level: {state_before.get('crisis_level', 5):.1f}/10

TETHYS POSITION:
- Territory Remaining: {(1-state_before.get('territory_controlled', 0))*100:.1f}%
- GDP: ${state_before.get('tethys_gdp', 30):.1f}B (started at $30B, change: {state_before.get('tethys_gdp', 30)-30:+.1f}B)
- International Support: {state_before.get('international_support', 0.5)*100:.0f}%
- Sanctions on Novaris: {state_before.get('sanctions_level', 0)*100:.0f}%

{'='*80}
EXTERNAL EVENTS THIS PERIOD
{'='*80}

{format_events(external_events)}

{'='*80}
NOVARIS'S STRATEGIC OBJECTIVES & CONSTRAINTS
{'='*80}

PRIMARY OBJECTIVES:
1. Control Tethys territory (Goal: 40%+, Current: {state_before.get('territory_controlled', 0)*100:.1f}%)
2. Minimize international isolation (Sanctions: {state_before.get('sanctions_level', 0)*100:.0f}%)
3. Maintain economic sustainability (GDP: ${state_before.get('novaris_gdp', 100):.1f}B)

STRATEGIC POSTURE:
{assess_strategic_posture('novaris', state_before)}

CAPABILITIES & CONSTRAINTS:
- Military: {interpret_military_balance(state_before.get('military_balance', 0))}
- Economic: {'Strained (GDP <$85B)' if state_before.get('novaris_gdp', 100) < 85 else 'Sustainable' if state_before.get('novaris_gdp', 100) < 95 else 'Strong'}
- Diplomatic: {'Isolated (>60% sanctions)' if state_before.get('sanctions_level', 0) > 0.6 else 'Pressured (30-60% sanctions)' if state_before.get('sanctions_level', 0) > 0.3 else 'Manageable (<30% sanctions)'}

{'='*80}
AVAILABLE ACTIONS BY DOMAIN
{'='*80}
{plausible_actions_text}

{'='*80}
YOUR TASK
{'='*80}

Predict the COMPLETE action set Novaris will approve this period.

GUIDANCE:
- Novaris can approve 0-12 actions this period (4 domain experts × up to 3 proposals each)
- The number of actions depends on strategic context and presidential decision-making
- Predict BOTH which actions AND how many actions based on:
  * Strategic objectives and current position
  * Resource constraints (GDP, sanctions, military balance)
  * External events and their implications
  * Escalation vs. consolidation trade-offs
  * Presidential risk tolerance and strategic judgment
- Consider multi-domain strategy: military + economic + intelligence + diplomatic
- More actions = more aggressive/comprehensive response; fewer = cautious/focused

OUTPUT FORMAT (JSON):
{{
  "predicted_actions": [
    "action_name_1",
    "action_name_2",
    "action_name_3",
    ...
  ],
  "rationale": "2-3 sentence explanation of Novaris's integrated strategy and why these actions make sense",
  "confidence": "low|medium|high"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""

    return prompt


def create_tethys_action_prediction_prompt(
    period: int,
    state_before: Dict,
    external_events: List[str],
    novaris_actions: List[str],
    plausible_actions_text: str
) -> str:
    """
    Create prompt for predicting Tethys's action set.

    Includes Novaris's actual actions (reactive prediction).

    Args:
        period: Period number (1-10)
        state_before: State dict from period-1
        external_events: List of external event descriptions
        novaris_actions: Novaris's actual approved actions this period
        plausible_actions_text: Formatted plausible actions by domain

    Returns:
        Complete prompt string
    """

    prompt = f"""You are a strategic analyst tasked with predicting Tethys's complete action set for Period {period}.

{'='*80}
STRATEGIC SITUATION (Period {period-1} Final State)
{'='*80}

TETHYS POSITION:
- Territory Remaining: {(1-state_before.get('territory_controlled', 0))*100:.1f}%
- Military Balance: {state_before.get('military_balance', 0):.2f} ({interpret_military_balance(state_before.get('military_balance', 0))})
- GDP: ${state_before.get('tethys_gdp', 30):.1f}B (started at $30B, change: {state_before.get('tethys_gdp', 30)-30:+.1f}B)
- International Support: {state_before.get('international_support', 0.5)*100:.0f}%
- Crisis Level: {state_before.get('crisis_level', 5):.1f}/10

NOVARIS POSITION:
- Territory Controlled: {state_before.get('territory_controlled', 0)*100:.1f}%
- GDP: ${state_before.get('novaris_gdp', 100):.1f}B
- Sanctions Level: {state_before.get('sanctions_level', 0)*100:.0f}%

{'='*80}
EXTERNAL EVENTS THIS PERIOD
{'='*80}

{format_events(external_events)}

{'='*80}
NOVARIS'S ACTIONS THIS PERIOD (JUST ANNOUNCED)
{'='*80}

Novaris has chosen the following actions:

{format_actions_with_implications(novaris_actions)}

IMMEDIATE IMPLICATIONS FOR TETHYS:
{assess_novaris_threat_level(novaris_actions)}

{'='*80}
TETHYS'S STRATEGIC OBJECTIVES & CONSTRAINTS
{'='*80}

PRIMARY OBJECTIVES:
1. Defend territory (Remaining: {(1-state_before.get('territory_controlled', 0))*100:.1f}%)
2. Maintain international support (Current: {state_before.get('international_support', 0.5)*100:.0f}%)
3. Preserve government stability (avoid collapse)

STRATEGIC POSTURE:
{assess_strategic_posture('tethys', state_before)}

CAPABILITIES & CONSTRAINTS:
- Military: {interpret_military_balance(state_before.get('military_balance', 0))}
- Economic: {'Critical (GDP <$20B)' if state_before.get('tethys_gdp', 30) < 20 else 'Strained (GDP <$25B)' if state_before.get('tethys_gdp', 30) < 25 else 'Sustainable'}
- Diplomatic: {'Strong support (>70%)' if state_before.get('international_support', 0.5) > 0.7 else 'Moderate support (50-70%)' if state_before.get('international_support', 0.5) > 0.5 else 'Weak support (<50%)'}

{'='*80}
AVAILABLE ACTIONS BY DOMAIN
{'='*80}
{plausible_actions_text}

{'='*80}
YOUR TASK
{'='*80}

Predict the COMPLETE action set Tethys will approve this period IN RESPONSE to external events and Novaris's actions.

GUIDANCE:
- Tethys can approve 0-12 actions this period (4 domain experts × up to 3 proposals each)
- The number of actions depends on threat level and defensive coordination needs
- Predict BOTH which actions AND how many actions based on:
  * Severity of Novaris's threat this period (observe their actions above)
  * Resource constraints and strategic priorities
  * International support levels and diplomatic opportunities
  * Need for multi-domain defensive coordination
  * Presidential judgment on how many fronts to engage
- More actions may indicate comprehensive defense; fewer may indicate focused response
- Consider appropriate counter-strategies:
  * Offensive operations → Defensive posture or asymmetric response
  * Economic pressure → Economic countermeasures or coalition-building
  * Intelligence operations → Counterintelligence
  * Military buildup → Mobilization or request for aid
- Balance military defense, diplomatic outreach, economic resilience
- Leverage international support advantage

OUTPUT FORMAT (JSON):
{{
  "predicted_actions": [
    "action_name_1",
    "action_name_2",
    "action_name_3",
    ...
  ],
  "rationale": "2-3 sentence explanation of Tethys's reactive strategy and how it responds to Novaris's moves",
  "confidence": "low|medium|high"
}}

IMPORTANT: Output ONLY valid JSON, no additional text before or after.
"""

    return prompt


def assess_novaris_threat_level(novaris_actions: List[str]) -> str:
    """Assess threat level from Novaris's action set."""
    offensive_actions = {
        'offensive_operation', 'strategic_bombing', 'precision_strike',
        'naval_blockade', 'special_forces_raid'
    }

    covert_actions = {
        'sabotage', 'assassination', 'cyber_attack', 'false_flag_operation',
        'support_insurgency'
    }

    has_offensive = any(a in offensive_actions for a in novaris_actions)
    has_covert = any(a in covert_actions for a in novaris_actions)

    if has_offensive and has_covert:
        return ("SEVERE THREAT: Novaris is conducting multi-domain offensive operations combining "
                "kinetic and covert actions. Immediate defensive response required.")
    elif has_offensive:
        return ("HIGH THREAT: Novaris has launched offensive military operations. "
                "Defensive mobilization and coalition support critical.")
    elif has_covert:
        return ("MODERATE THREAT: Novaris is conducting covert operations. "
                "Counterintelligence and defensive measures needed.")
    elif 'peace_talks' in novaris_actions or 'backchannel_negotiations' in novaris_actions:
        return ("DIPLOMATIC OPPORTUNITY: Novaris is pursuing negotiations. "
                "Consider combining defensive posture with diplomatic engagement.")
    else:
        return ("MONITORING: Novaris actions are primarily economic/intelligence gathering. "
                "Maintain defensive readiness while exploring diplomatic options.")


if __name__ == "__main__":
    # Test prompt generation
    print("Testing prompt templates...\n")

    test_state = {
        'territory_controlled': 0.15,
        'military_balance': -0.12,
        'crisis_level': 6.0,
        'novaris_gdp': 92.0,
        'tethys_gdp': 28.0,
        'international_support': 0.65,
        'sanctions_level': 0.35
    }

    test_events = [
        "Battlefield: Defensive success by Tethys - repelled Novaris offensive",
        "Economic: Sanctions enforcement increasing pressure on Novaris",
        "Diplomatic: Peace talks proposed by international mediators"
    ]

    test_novaris_actions = [
        'military_buildup',
        'precision_strike',
        'intelligence_gathering',
        'strategic_stockpiling'
    ]

    test_plausible = """
MILITARY:
  - military_buildup: Concentrate forces, increase readiness
  - offensive_operation: Launch ground offensive
  - defensive_posture: Fortify defensive positions

INTELLIGENCE:
  - intelligence_gathering: Collect adversary information
  - sabotage: Covertly damage infrastructure
  - counterintelligence: Protect against enemy intelligence

ECONOMIC:
  - strategic_stockpiling: Build reserves
  - sanctions: Impose economic restrictions
  - embargo: Block trade/exports
"""

    print("="*80)
    print("NOVARIS PROMPT SAMPLE:")
    print("="*80)
    novaris_prompt = create_novaris_action_prediction_prompt(
        period=5,
        state_before=test_state,
        external_events=test_events,
        plausible_actions_text=test_plausible
    )
    print(novaris_prompt[:1000] + "\n...(truncated)")

    print("\n" + "="*80)
    print("TETHYS PROMPT SAMPLE:")
    print("="*80)
    tethys_prompt = create_tethys_action_prediction_prompt(
        period=5,
        state_before=test_state,
        external_events=test_events,
        novaris_actions=test_novaris_actions,
        plausible_actions_text=test_plausible
    )
    print(tethys_prompt[:1000] + "\n...(truncated)")

    print("\n[OK] Prompt templates created successfully!")
